"""End-to-end demo: sprint mode with REAL MiniMax-M3 LLM + wiki persist.

Run: python _e2e_demo.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scripts.handlers import handle_sprint

WIKI_ROOT = ROOT / "_demo_wiki"
TASK = "design a clean exit-mode for active cron jobs when user says stop"

# Wipe demo wiki
if WIKI_ROOT.exists():
    shutil.rmtree(WIKI_ROOT)
WIKI_ROOT.mkdir(parents=True, exist_ok=True)


def section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main():
    section("END-TO-END: sprint mode + real MiniMax-M3 + wiki persist")
    print("task: " + TASK)
    print("wiki: " + str(WIKI_ROOT))
    print()

    section("[1/4] LLM check (must be real, not mock)")
    from scripts.llm_client import get_default_llm, has_real_llm
    print("has_real_llm = " + str(has_real_llm()))
    if not has_real_llm():
        print("ERROR: no real LLM available; cannot run end-to-end demo.")
        return 1
    llm = get_default_llm()
    sample = llm("You are an analyst. Reply in 1 sentence.", "say hi")
    print("sample reply: " + sample[:100])

    section("[2/4] Run sprint handler (PWR + wiki)")
    t0 = time.time()
    result = handle_sprint(TASK, wiki_root=WIKI_ROOT)
    elapsed = time.time() - t0

    print("phase = " + str(result["phase"]))
    print("mode = " + result["mode"])
    print("success = " + str(result["pwr"]["success"]))
    print("total_iters = " + str(result["pwr"]["total_iters"]))
    print("iters run = " + str(len(result["pwr"]["iterations"])))
    print("elapsed = " + f"{elapsed:.1f}s")
    print("final_result preview: " + result["pwr"]["final_result"][:200].replace("\n", " "))
    print()

    section("[3/4] PWR iteration flow")
    for i, it in enumerate(result["pwr"]["iterations"]):
        print("--- iter " + str(i + 1) + " ---")
        for k in ("planner", "worker", "reviewer"):
            v = it.get(k, "")
            if v:
                v_short = v.replace("\n", " ")[:120]
                print("  " + k + ": " + v_short)
        if it.get("reflection"):
            r_short = it["reflection"].replace("\n", " ")[:120]
            print("  reflection: " + r_short)
    print()

    section("[4/4] Wiki files written")
    wiki_files = sorted(WIKI_ROOT.rglob("*"))
    print("root: " + str(WIKI_ROOT))
    print("total files: " + str(len([f for f in wiki_files if f.is_file()])))
    for f in wiki_files:
        if f.is_file():
            sz = f.stat().st_size
            rel = f.relative_to(WIKI_ROOT)
            print(f"  {rel}  ({sz}B)")

    if "wiki" in result:
        ws = result["wiki"]
        print()
        print("wiki_summary:")
        print("  dialogue_written = " + str(ws["dialogue_written"]))
        print("  entities_written = " + str(ws["entities_written"]))
        print("  topic_written = " + str(ws["topic_written"]))
        print("  lint_summary:")
        for k, v in ws["lint_summary"].items():
            print(f"    {k} = {v}")

    if result["pwr"].get("failure_reason"):
        print()
        print("failure_reason: " + result["pwr"]["failure_reason"])

    print()
    print("DEMO OK: sprint + real LLM + wiki persist all worked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
