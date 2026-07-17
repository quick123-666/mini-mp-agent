"""Tests for PWR Loop state machine (Phase 2 ship).

Run: python tests\\test_pwr_loop.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.pwr_loop import (
    DEFAULT_LLM,
    PWRResult,
    PWRIteration,
    parse_review_score,
    run_auto,
    run_pwr,
    run_sprint,
    run_task,
    stub_llm,
    make_score_llm,
)
from scripts.roles import (
    PLANNER_SYSTEM, WORKER_SYSTEM, REVIEWER_SYSTEM, REFLECTOR_SYSTEM,
    ROLE_REGISTRY, get_role,
)

PASS = []
FAIL = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append(f"{name}: {detail}")
        print(f"  FAIL  {name}: {detail}")


# -------- roles tests --------

def test_roles_4_entries():
    check("4 roles registered", len(ROLE_REGISTRY) == 4)
    for r in ("planner", "worker", "reviewer", "reflector"):
        check(f"  role {r} present", r in ROLE_REGISTRY)


def test_get_role_valid():
    s = get_role("planner")
    check("get_role planner returns non-empty", len(s) > 100)
    check("get_role planner mentions Planner", "Planner" in s)


def test_get_role_invalid_raises():
    try:
        get_role("unknown_role")
        check("get_role rejects unknown", False, "did not raise")
    except ValueError:
        check("get_role rejects unknown", True)


# -------- parse_review_score tests --------

def test_parse_score_explicit():
    s = "syntax: pass\nlength: pass\nrelevance: pass\ncoherence: pass\n\nScore: 0.85\nNotes: ok"
    check("parse explicit Score: 0.85", parse_review_score(s) == 0.85, f"got {parse_review_score(s)}")


def test_parse_score_lowercase():
    s = "score: 0.45"
    check("parse lowercase score: 0.45", parse_review_score(s) == 0.45)


def test_parse_score_no_match_default():
    check("parse default 0.5 when no match", parse_review_score("random text") == 0.5)


def test_parse_score_empty():
    check("parse empty → 0.5", parse_review_score("") == 0.5)


def test_parse_score_out_of_range_clamp():
    """Score > 1 → if <=100 treat as percent; if > 100 reject and fall through."""
    s = "Score: 85"  # → 0.85
    check("parse 85 → 0.85 (percent)", parse_review_score(s) == 0.85)
    s2 = "Score: 200"  # > 100, fall to fallback 0.5
    check("parse 200 → fallback 0.5", parse_review_score(s2) == 0.5)


def test_parse_score_fallback_decimal():
    s = "result is 0.7 good"
    check("parse fallback decimal 0.7", parse_review_score(s) == 0.7)


# -------- run_pwr with stub_llm tests --------

def test_run_pwr_returns_pwrresult():
    r = run_pwr("test task", max_iter=1, llm=stub_llm)
    check("run_pwr returns PWRResult", isinstance(r, PWRResult))
    check("  total_iters == 1", r.total_iters == 1)
    check("  task preserved", r.task == "test task")
    check("  mode set", r.mode == "auto")


def test_run_pwr_max_iter_3():
    r = run_pwr("test", max_iter=3, llm=stub_llm)
    # stub_llm returns "[STUB-...]" without "Score:" — parse_review_score defaults 0.5
    # threshold=0.8 default → fails all 3 iters
    check("max_iter=3 runs 3 iters with stub", r.total_iters == 3)
    check("stub returns failure", r.success is False)
    check("failure_reason set", "score" in r.failure_reason)


def test_run_pwr_early_success_high_score():
    """Mock llm returns 0.95 score → 1 iter success."""
    r = run_pwr("test", max_iter=3, llm=make_score_llm(0.95))
    check("early success on high score", r.success is True)
    check("  stops at iter 1", r.total_iters == 1)


def test_run_pwr_threshold_param():
    """threshold=0.5, score=0.7 (from stub? no, stub → 0.5) — test with mock."""
    r = run_pwr("test", max_iter=3, threshold=0.5, llm=make_score_llm(0.7))
    check("threshold=0.5 + score=0.7 success", r.success is True)


def test_run_pwr_rejects_invalid_max_iter():
    try:
        run_pwr("test", max_iter=0)
        check("rejects max_iter=0", False, "did not raise")
    except ValueError:
        check("rejects max_iter=0", True)


def test_run_pwr_rejects_invalid_threshold():
    try:
        run_pwr("test", threshold=1.5)
        check("rejects threshold=1.5", False, "did not raise")
    except ValueError:
        check("rejects threshold=1.5", True)


# -------- mode wrappers --------

def test_run_task_mode_1_iter():
    r = run_task("test", llm=stub_llm)
    check("task mode runs 1 iter", r.total_iters == 1)
    check("task mode marker", r.mode == "task")


def test_run_auto_mode_default_3_iters():
    r = run_auto("test", llm=stub_llm)
    check("auto mode default 3 iters", r.total_iters == 3)
    check("auto mode marker", r.mode == "auto")


def test_run_sprint_mode_marker():
    r = run_sprint("test", llm=stub_llm)
    check("sprint mode marker", r.mode == "sprint")
    check("sprint runs 3 iters", r.total_iters == 3)


# -------- iteration roles tracked --------

def test_iter_role_history():
    """Success iter (1st) should track planner+worker+reviewer."""
    r = run_pwr("test", max_iter=3, llm=make_score_llm(0.95))
    hist = r.iterations[0].role_history
    check("iter1 history includes planner", "planner" in hist)
    check("iter1 history includes worker", "worker" in hist)
    check("iter1 history includes reviewer", "reviewer" in hist)
    check("iter1 no reflector (success)", "reflector" not in hist)


def test_iter_role_history_with_reflection():
    """Failed iter should track planner+worker+reviewer+reflector."""
    r = run_pwr("test", max_iter=2, llm=stub_llm)  # stub → score 0.5 → fail
    it1 = r.iterations[0]
    check("iter1 history has reflector", "reflector" in it1.role_history)
    check("iter1 needs_replan", it1.needs_replan is True)


def test_iter_score_field():
    it = PWRIteration(iter=1, review_score=0.75)
    check("PWRIteration score field", it.review_score == 0.75)


def test_to_dict_serializable():
    r = run_pwr("test", max_iter=1, llm=stub_llm)
    import json
    json.dumps(r.to_dict())  # raises if not
    check("PWRResult.to_dict json-serializable", True)


def test_final_result_set_on_success():
    r = run_pwr("test", max_iter=3, llm=make_score_llm(0.9))
    check("final_result set on success", "[STUB-worker]" in r.final_result or len(r.final_result) > 0)


# -------- handlers integration --------

def test_handler_task_returns_pwr():
    from scripts.handlers import handle_task
    from scripts.llm_client import _mock_llm
    r = handle_task("test task", llm=_mock_llm)
    check("handle_task has pwr key", "pwr" in r)
    check("handle_task pwr is dict", isinstance(r["pwr"], dict))
    check("handle_task pwr has iterations", "iterations" in r["pwr"])


def test_handler_auto_returns_pwr():
    from scripts.handlers import handle_auto
    from scripts.llm_client import _mock_llm
    r = handle_auto("test task", llm=_mock_llm)
    check("handle_auto has pwr", "pwr" in r)
    check("handle_auto mode=auto", r["mode"] == "auto")


def test_handler_sprint_returns_pwr():
    from scripts.handlers import handle_sprint
    from scripts.llm_client import _mock_llm
    r = handle_sprint("test task", llm=_mock_llm, wiki_root=None)
    check("handle_sprint has pwr", "pwr" in r)
    check("handle_sprint mode=sprint", r["mode"] == "sprint")


def test_handler_qa_no_pwr():
    from scripts.handlers import handle_qa
    r = handle_qa("test task")
    check("handle_qa has no pwr", "pwr" not in r)
    check("handle_qa has response", "response" in r)


# -------- main --------

def run_all():
    print("=== mini-mp-agent PWR Loop tests (Phase 2) ===")
    tests = [
        test_roles_4_entries, test_get_role_valid, test_get_role_invalid_raises,
        test_parse_score_explicit, test_parse_score_lowercase, test_parse_score_no_match_default,
        test_parse_score_empty, test_parse_score_out_of_range_clamp, test_parse_score_fallback_decimal,
        test_run_pwr_returns_pwrresult, test_run_pwr_max_iter_3,
        test_run_pwr_early_success_high_score, test_run_pwr_threshold_param,
        test_run_pwr_rejects_invalid_max_iter, test_run_pwr_rejects_invalid_threshold,
        test_run_task_mode_1_iter, test_run_auto_mode_default_3_iters, test_run_sprint_mode_marker,
        test_iter_role_history, test_iter_role_history_with_reflection,
        test_iter_score_field, test_to_dict_serializable, test_final_result_set_on_success,
        test_handler_task_returns_pwr, test_handler_auto_returns_pwr, test_handler_sprint_returns_pwr,
        test_handler_qa_no_pwr,
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
