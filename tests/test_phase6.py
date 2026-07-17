"""Phase 6 tests: real LLM injection + wiki integration.

Run: python tests\\test_phase6.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.llm_client import (
    get_default_llm,
    make_score_llm,
    has_real_llm,
    _mock_llm,
    _read_openclaw_api_key,
)
from scripts.wiki_integration import (
    build_messages_from_pwr,
    persist_to_wiki,
    wiki_integration_step,
)
from scripts.handlers import (
    handle_qa,
    handle_task,
    handle_discuss,
    handle_auto,
    handle_sprint,
)

PASS = []
FAIL = []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print("  PASS  " + name)
    else:
        FAIL.append(name + ": " + detail)
        print("  FAIL  " + name + ": " + detail)


# llm_client tests
def test_mock_llm_signature():
    r = _mock_llm("You are an analyst.", "hello")
    check("mock echoes role", "[STUB-analyst]" in r)
    check("mock includes input", "hello" in r)


def test_mock_llm_long_role_extraction():
    r = _mock_llm("You are a critic. Focus on risks.", "test")
    check("mock extracts critic", "[STUB-critic]" in r)


def test_mock_llm_empty_msg():
    r = _mock_llm("You are an analyst.", "")
    check("mock handles empty msg", "[STUB-analyst]" in r)


def test_score_llm_parses_decimal():
    score = make_score_llm(_mock_llm)("Review: 0.85 quality", "")
    check("score 0.85 parsed", abs(score - 0.85) < 0.01, "got " + str(score))


def test_score_llm_parses_percentage():
    score = make_score_llm(lambda s, m: "90%")("anything", "")
    check("score 90% parsed as 0.9", abs(score - 0.90) < 0.01, "got " + str(score))


def test_score_llm_fallback_on_garbage():
    score = make_score_llm(lambda s, m: "no number here")("anything", "")
    check("score fallback 0.5", score == 0.5)


def test_score_llm_clamps():
    score = make_score_llm(lambda s, m: "1.5")("anything", "")
    check("score clamps high to 1.0", score == 1.0, "got " + str(score))
    # -0.5: regex doesn't match negatives → returns 0.5 fallback
    score = make_score_llm(lambda s, m: "-0.5")("anything", "")
    check("score negative falls back to 0.5", score == 0.5, "got " + str(score))
    # 0.0 explicit
    score = make_score_llm(lambda s, m: "0")("anything", "")
    check("score 0.0 explicit", score == 0.0)
    # 1.0 explicit
    score = make_score_llm(lambda s, m: "1.0")("anything", "")
    check("score 1.0 explicit", score == 1.0)


def test_get_default_llm_force_mock():
    llm = get_default_llm(force_mock=True)
    check("force_mock returns mock", llm is _mock_llm)


def test_has_real_llm_returns_bool():
    result = has_real_llm()
    check("has_real_llm is bool", isinstance(result, bool))


# wiki_integration tests
def test_build_messages_from_pwr_empty():
    msgs = build_messages_from_pwr("test task", {})
    check("always has user message", len(msgs) >= 1)
    check("first is user", msgs[0]["role"] == "user")
    check("first is task", msgs[0]["content"] == "test task")


def test_build_messages_from_pwr_one_iter():
    pwr = {"iterations": [{"planner": "P", "worker": "W", "reviewer": "R"}]}
    msgs = build_messages_from_pwr("task", pwr)
    check("user + 3 iter msgs", len(msgs) == 4)


def test_build_messages_from_pwr_with_reflection():
    pwr = {"iterations": [{"planner": "P", "worker": "W", "reviewer": "R", "reflection": "fail"}]}
    msgs = build_messages_from_pwr("task", pwr)
    check("user + 4 iter msgs", len(msgs) == 5)


def test_persist_to_wiki_minimal():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "wiki"
        pwr = {"status": "success", "iterations": [{"planner": "analyze", "worker": "build", "reviewer": "ok"}]}
        result = persist_to_wiki(root, "ship Plan F v8.1", pwr)
        check("returns dict", isinstance(result, dict))
        check("dialogue_written > 0", result["dialogue_written"] > 0, "got " + str(result["dialogue_written"]))
        check("entities_written >= 0", result["entities_written"] >= 0)
        check("lint_summary has 8 keys", len(result["lint_summary"]) == 8)


def test_persist_to_wiki_with_topic():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "wiki"
        pwr = {"status": "success", "iterations": [{"planner": "p", "worker": "w", "reviewer": "r"}]}
        result = persist_to_wiki(root, "test task about mp", pwr, write_topic_for="mp-test-topic")
        check("topic_written=True", result["topic_written"] is True)
        check("topic exists", (root / "topics" / "mp-test-topic.md").exists())


def test_persist_to_wiki_idempotent_init():
    """If wiki already initialized, persist shouldn't re-init badly."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "wiki"
        from scripts.wiki_store import init_wiki
        init_wiki(root)
        pwr = {"status": "success", "iterations": []}
        result = persist_to_wiki(root, "second run", pwr)
        check("idempotent", result["dialogue_written"] >= 1)


def test_wiki_integration_step_handles_error():
    """If wiki_root is invalid (e.g., permission denied), should not crash."""
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "x" / "y" / "z"
        # do NOT create parent dirs — but our code calls init_wiki which mkdirs.
        # Test with a path that exists as a FILE (so dir create fails).
        bad_file = Path(tmp) / "is_a_file"
        bad_file.write_text("blocking")
        result = wiki_integration_step(bad_file, "task", {"iterations": []})
        # result should be either successful (auto-init) or contain 'error'
        check("does not raise", isinstance(result, dict))


# handler integration tests
def test_handle_qa_uses_llm():
    r = handle_qa("hello world")
    check("qa has response", "response" in r)
    check("qa has llm_used", "llm_used" in r)
    check("qa phase=6", r["phase"] == 6)


def test_handle_qa_with_custom_llm():
    def my_llm(system, msg):
        return "custom qa reply"
    r = handle_qa("task", llm=my_llm)
    check("qa custom response", "custom qa reply" in r["response"])


def test_handle_discuss_real_or_mock():
    r = handle_discuss("test integration")
    check("discuss 5 personas", len(r["personas"]) == 5)
    check("discuss has consensus", "consensus" in r)


def test_handle_sprint_with_wiki():
    with tempfile.TemporaryDirectory() as tmp:
        wiki_root = Path(tmp) / "wiki"
        r = handle_sprint("ship Plan F v8 to prod", wiki_root=wiki_root)
        check("sprint has wiki", "wiki" in r)
        check("wiki has dialogue count", "dialogue_written" in r["wiki"])


def test_handle_sprint_no_wiki():
    r = handle_sprint("test task")
    check("sprint no wiki key", "wiki" not in r)


def run_all():
    print("=== mini-mp-agent Phase 6 tests ===")

    print("\n-- llm_client --")
    test_mock_llm_signature()
    test_mock_llm_long_role_extraction()
    test_mock_llm_empty_msg()
    test_score_llm_parses_decimal()
    test_score_llm_parses_percentage()
    test_score_llm_fallback_on_garbage()
    test_score_llm_clamps()
    test_get_default_llm_force_mock()
    test_has_real_llm_returns_bool()

    print("\n-- wiki_integration --")
    test_build_messages_from_pwr_empty()
    test_build_messages_from_pwr_one_iter()
    test_build_messages_from_pwr_with_reflection()
    test_persist_to_wiki_minimal()
    test_persist_to_wiki_with_topic()
    test_persist_to_wiki_idempotent_init()
    test_wiki_integration_step_handles_error()

    print("\n-- handler integration --")
    test_handle_qa_uses_llm()
    test_handle_qa_with_custom_llm()
    test_handle_discuss_real_or_mock()
    test_handle_sprint_with_wiki()
    test_handle_sprint_no_wiki()

    total = len(PASS) + len(FAIL)
    print("\n=== " + str(len(PASS)) + "/" + str(total) + " PASS, " + str(len(FAIL)) + " FAIL ===")
    if FAIL:
        for f in FAIL:
            print("  FAIL: " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_all())
