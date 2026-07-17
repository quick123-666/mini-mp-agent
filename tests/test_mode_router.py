"""Tests for mode_router (Phase 1 ship).

Run: python -m mini_mp_agent.tests.test_mode_router
Or:  cd tests && python test_mode_router.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow direct execution: prepend parent to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.mode_router import (
    detect_mode,
    route,
    MODE_KEYWORDS,
    MODE_COST,
    VALID_MODES,
)
from scripts.handlers import HANDLERS, PHASE


PASS = []
FAIL = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append(f"{name}: {detail}")
        print(f"  FAIL  {name}: {detail}")


# -------- detect_mode tests --------

def test_detect_qa():
    """QA keywords trigger qa mode."""
    for kw in ["什么是 mp", "explain PWR", "how to do X", "为什么"]:
        d = detect_mode(kw)
        check(f"detect qa: {kw!r}", d.mode == "qa", f"got {d.mode}, scores={d.scores}")


def test_detect_task():
    """Task keywords trigger task mode.

    Note: "ship it" ties with sprint (both score 1); sprint priority wins by design.
    """
    for kw in ["做一个 script", "fix 这个 bug", "build X"]:
        d = detect_mode(kw)
        check(f"detect task: {kw!r}", d.mode == "task", f"got {d.mode}")


def test_ship_it_goes_sprint():
    """"ship it" ties with sprint; priority picks sprint (more ambitious)."""
    d = detect_mode("ship it")
    check("ship it → sprint (priority wins tie)", d.mode == "sprint")


def test_detect_discuss():
    """Discussion keywords trigger discuss mode."""
    for kw in ["对比 X 和 Y", "vs", "选哪个"]:
        d = detect_mode(kw)
        check(f"detect discuss: {kw!r}", d.mode == "discuss", f"got {d.mode}")


def test_detect_sprint():
    """Sprint keywords trigger sprint mode."""
    for kw in ["全栈 ship", "多步实现", "一整套"]:
        d = detect_mode(kw)
        check(f"detect sprint: {kw!r}", d.mode == "sprint", f"got {d.mode}")


def test_detect_default():
    """No keywords → default auto."""
    d = detect_mode("一个普通任务")
    check("detect default auto", d.mode == "auto", f"got {d.mode}")


def test_detect_english_default():
    """English no keywords → default auto."""
    d = detect_mode("hello world")
    check("detect english default auto", d.mode == "auto", f"got {d.mode}")


# -------- explicit mode tests --------

def test_route_explicit_qa():
    r = route("any task", mode="qa")
    check("route explicit qa", r["mode"] == "qa")
    check("route qa has cost", r["cost"]["latency_s"] == 2)
    # Phase 2: qa handler returns response (not stub_marker)
    check("route qa has response", "response" in r["result"])


def test_route_explicit_task():
    r = route("any task", mode="task")
    check("route explicit task", r["mode"] == "task")
    check("route task has cost", r["cost"]["latency_s"] == 10)


def test_route_invalid_mode():
    try:
        route("foo", mode="unknown_mode")
        check("route rejects unknown mode", False, "did not raise")
    except ValueError as e:
        check("route rejects unknown mode", True, str(e))


# -------- auto-detect routing --------

def test_route_autodetect_routes_qa():
    r = route("why is X")  # "why" → qa
    check("auto-route qa via why", r["mode"] == "qa")


def test_route_autodetect_routes_task():
    r = route("做一个 chat bot")  # "做" → task
    check("auto-route task via 做一个", r["mode"] == "task")


# -------- decision metadata --------

def test_decision_has_scores():
    d = detect_mode("fix the bug")
    check("decision has scores", "qa" in d.scores and "task" in d.scores)
    check("decision has reason", len(d.reason) > 0)


def test_to_dict_serializable():
    """detect_mode result is JSON-serializable."""
    d = detect_mode("对比 X vs Y")
    json.dumps(d.to_dict())  # raises if not
    check("decision json-serializable", True)


# -------- cost catalog --------

def test_mode_cost_5_entries():
    check("5 mode cost entries", len(MODE_COST) == 5)


def test_valid_modes():
    check("5 valid modes", len(VALID_MODES) == 5)
    check("valid includes auto", "auto" in VALID_MODES)
    check("valid includes qa", "qa" in VALID_MODES)


# -------- handlers --------

def test_handlers_5_entries():
    check("5 handlers", len(HANDLERS) == 5)


def test_handler_phase_marker():
    """All handlers return phase-tagged dict (Phase 6 = 6).

    Uses mock LLM to avoid network calls during unit test.
    """
    expected_phase = 6
    pwr_modes = {"task", "auto", "sprint"}
    # Inject mock LLM so handler calls don't hit network
    from scripts.llm_client import _mock_llm
    for mode, fn in HANDLERS.items():
        if mode == "sprint":
            r = fn("test task", llm=_mock_llm, wiki_root=None)
        else:
            r = fn("test task", llm=_mock_llm)
        check(f"  handler {mode} phase=6", r.get("phase") == expected_phase)
        if mode in pwr_modes:
            check(f"  handler {mode} has pwr", "pwr" in r)


# -------- main --------

def run_all():
    print(f"=== mini-mp-agent mode_router tests (Phase {PHASE}) ===")
    tests = [
        test_detect_qa, test_detect_task, test_detect_discuss, test_detect_sprint,
        test_detect_default, test_detect_english_default,
        test_route_explicit_qa, test_route_explicit_task, test_route_invalid_mode,
        test_route_autodetect_routes_qa, test_route_autodetect_routes_task,
        test_decision_has_scores, test_to_dict_serializable,
        test_mode_cost_5_entries, test_valid_modes,
        test_handlers_5_entries, test_handler_phase_marker,
    ]
    for t in tests:
        print(f"\n-- {t.__name__} --")
        t()

    total = len(PASS) + len(FAIL)
    print(f"\n=== {len(PASS)}/{total} PASS, {len(FAIL)} FAIL ===")
    if FAIL:
        for f in FAIL:
            print(f"  FAIL: {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_all())
