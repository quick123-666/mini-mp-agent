"""5 mode handlers — Phase 2 + Phase 5 ship (2026-07-18 00:32).

qa       → single LLM call (Phase 2 stub; Phase 6 wires real LLM)
task     → PWR max_iter=1 (real, calls pwr_loop)
discuss  → 5 persona parallel via task_queue.run_batch (Phase 5 REAL)
auto     → PWR max_iter=3 (real, calls pwr_loop)
sprint   → auto + wiki recall + persist (Phase 4 ships wiki integration)

Architecture: each handler is sync, returns dict with structured data.
Future: handlers will accept llm:callable kwarg from minimp runtime.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

PHASE = 6
SKILL_ROOT = Path(__file__).resolve().parent.parent

from .pwr_loop import (
    DEFAULT_LLM,
    LLMCallable,
    run_pwr,
    run_task as _run_pwr_task,
    run_auto as _run_pwr_auto,
    run_sprint as _run_pwr_sprint,
)
from .task_queue import run_batch
from .llm_client import get_default_llm, make_score_llm, has_real_llm


# 5 discuss personas — each gets a SYSTEM_PROMPT role + same task
DISCUSS_PERSONAS = [
    {"name": "analyst",      "role": "analyst",      "focus": "break down the problem; list 3 facts"},
    {"name": "critic",       "role": "critic",       "focus": "find the 3 biggest risks"},
    {"name": "advocate",     "role": "advocate",     "focus": "list 3 reasons why this WILL work"},
    {"name": "skeptic",      "role": "skeptic",      "focus": "list 3 reasons why this WON'T work"},
    {"name": "synthesizer",  "role": "synthesizer",  "focus": "combine the above into a recommendation"},
]


def _stamp(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def _qa_stub(task: str) -> str:
    """Phase 2 stub. Phase 6 replaces with single LLM call."""
    return f"[STUB-QA] direct answer to: {task}"


def handle_qa(task: str, llm: Optional[LLMCallable] = None) -> dict[str, Any]:
    """qa: single LLM call. Phase 6 wires real LLM (auto-fallback to mock)."""
    llm = llm or get_default_llm()
    try:
        response = llm("You are Aris. Reply concisely in 1-3 sentences.", task)
        llm_used = "real" if llm is not get_default_llm(force_mock=True) else "default"
    except Exception as e:
        response = _qa_stub(task)
        llm_used = "stub-fallback: " + str(e)[:50]
    return {
        "phase": PHASE,
        "mode": "qa",
        "task": task,
        "response": response,
        "llm_used": llm_used,
        "cost": {"latency_s": 2, "tokens": 500},
        "next_steps": [],
    }


def handle_task(task: str, llm: Optional[LLMCallable] = None) -> dict[str, Any]:
    """task: PWR iter=1 (real). Phase 6 uses default real LLM if available."""
    llm = llm or get_default_llm()
    pwr = _run_pwr_task(task, llm=llm)
    return {
        "phase": PHASE,
        "mode": "task",
        "task": task,
        "pwr": pwr.to_dict(),
        "cost": {"latency_s": 10, "tokens": 1500},
        "next_steps": [],
    }


def _persona_reply(persona: dict, task: str, llm: LLMCallable) -> dict:
    """One persona's reply. Calls LLM with role + task. Returns {name, role, response, score}."""
    system = (
        f"You are a {persona['role']}. "
        f"Your focus: {persona['focus']}. "
        f"Reply in 1-3 sentences, no preamble."
    )
    response = llm(system, task)
    # score based on response length (Phase 5 stub; Phase 6 may use review_llm)
    score = min(1.0, len(response) / 200) if response else 0.0
    return {
        "name": persona["name"],
        "role": persona["role"],
        "focus": persona["focus"],
        "response": response,
        "score": round(score, 2),
    }


def handle_discuss(task: str, llm: Optional[LLMCallable] = None) -> dict[str, Any]:
    """discuss: 5 persona parallel via task_queue.run_batch (Phase 5 + Phase 6 REAL)."""
    llm = llm or get_default_llm()

    # Build 5 tasks; each is a callable returning _persona_reply (sync)
    tasks = [
        ((p["name"]), (lambda p=p: _persona_reply(p, task, llm)))
        for p in DISCUSS_PERSONAS
    ]
    results = run_batch(tasks, workers=5)

    personas_out = []
    for p in DISCUSS_PERSONAS:
        r = results.get(p["name"])
        if r and r.success:
            personas_out.append(r.result)
        else:
            personas_out.append({
                "name": p["name"],
                "role": p["role"],
                "focus": p["focus"],
                "response": "",
                "score": 0.0,
                "error": r.error if r else "no result",
            })

    # aggregate: synthesizer's response IS the consensus; disagreements = where score < 0.5
    consensus = next((p["response"] for p in personas_out if p["name"] == "synthesizer"), "")
    disagreements = [p["name"] for p in personas_out if p["score"] < 0.5]
    avg_score = sum(p["score"] for p in personas_out) / max(1, len(personas_out))

    return {
        "phase": PHASE,
        "mode": "discuss",
        "task": task,
        "personas": personas_out,
        "consensus": consensus,
        "disagreements": disagreements,
        "avg_score": round(avg_score, 2),
        "cost": {"latency_s": 20, "tokens": 3000},
        "next_steps": [],
    }


def handle_auto(task: str, llm: Optional[LLMCallable] = None) -> dict[str, Any]:
    """auto: full PWR + Reflect (3 iter, REAL). Phase 6 uses default real LLM."""
    llm = llm or get_default_llm()
    pwr = _run_pwr_auto(task, llm=llm)
    return {
        "phase": PHASE,
        "mode": "auto",
        "task": task,
        "pwr": pwr.to_dict(),
        "cost": {"latency_s": 30, "tokens": 2500},
        "next_steps": [],
    }


def handle_sprint(task: str, llm: Optional[LLMCallable] = None, wiki_root: Optional[Path] = None) -> dict[str, Any]:
    """sprint: auto + wiki recall + persist (Phase 6 wires wiki integration).

    Phase 6: writes dialogue + entities + topic to wiki_root after PWR completes.
    """
    llm = llm or get_default_llm()
    pwr = _run_pwr_sprint(task, llm=llm)

    # Phase 6: wiki integration
    wiki_summary = None
    if wiki_root is not None:
        from .wiki_integration import wiki_integration_step
        wiki_summary = wiki_integration_step(Path(wiki_root), task, pwr.to_dict())

    result = {
        "phase": PHASE,
        "mode": "sprint",
        "task": task,
        "pwr": pwr.to_dict(),
        "cost": {"latency_s": 40, "tokens": 3500},
        "next_steps": [],
    }
    if wiki_summary is not None:
        result["wiki"] = wiki_summary
    return result


HANDLERS = {
    "qa":      handle_qa,
    "task":    handle_task,
    "discuss": handle_discuss,
    "auto":    handle_auto,
    "sprint":  handle_sprint,
}


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m mini_mp_agent.scripts.handlers <mode> <task>")
        sys.exit(1)

    mode = sys.argv[1]
    task = sys.argv[2]
    if mode not in HANDLERS:
        print(f"unknown mode: {mode}; valid: {sorted(HANDLERS)}")
        sys.exit(2)
    print(json.dumps(HANDLERS[mode](task), ensure_ascii=False, indent=2))
