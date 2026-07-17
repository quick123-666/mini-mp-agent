"""Phase 5 tests: entity_extractor + discuss handler 5-persona parallel.

Run: python tests\\test_phase5.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.entity_extractor import extract_entities, group_by_type
from scripts.handlers import handle_discuss, DISCUSS_PERSONAS
from scripts.pwr_loop import DEFAULT_LLM

PASS = []
FAIL = []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print("  PASS  " + name)
    else:
        FAIL.append(name + ": " + detail)
        print("  FAIL  " + name + ": " + detail)


# entity_extractor tests
def test_extract_empty():
    e = extract_entities("")
    check("empty text", e == [])


def test_extract_known_alias():
    e = extract_entities("we shipped mini-mp today")
    slugs = [x["entity"] for x in e]
    check("alias mini-mp detected", "mini-mp" in slugs)
    check("type=tool", any(x["type"] == "tool" for x in e))


def test_extract_file_path():
    e = extract_entities("see scripts/handlers.py for code")
    files = [x["entity"] for x in e if x["type"] == "file"]
    check("file detected", any("handlers.py" in f for f in files))


def test_extract_url():
    e = extract_entities("read https://github.com/x/y for details")
    urls = [x["entity"] for x in e if x["type"] == "url"]
    check("URL detected", len(urls) == 1)
    check("URL exact", urls[0] == "https://github.com/x/y")


def test_extract_chinese_phrase():
    e = extract_entities("讨论了 PWR Loop 的实现细节")
    names = [x["entity"] for x in e]
    check("PWR alias", "PWR Loop" in names)
    check("Chinese phrase extracted", any(len(n) >= 2 and not n.isascii() for n in names))


def test_extract_dedup():
    e = extract_entities("mp mp mp meta-planner")
    mp_hits = [x for x in e if x["entity"].lower() == "mp"]
    check("dedup", len(mp_hits) == 1)


def test_extract_confidence_filter():
    e = extract_entities("hello world", min_confidence=0.99)
    check("high threshold filters", all(x["confidence"] >= 0.99 for x in e))


def test_group_by_type():
    text = "shipped mini-mp from handlers.py and talked with user about PWR"
    e = extract_entities(text)
    g = group_by_type(e)
    check("group has tool", "tool" in g)
    check("group has file", "file" in g)
    check("group has person", "person" in g)
    check("group has concept", "concept" in g)


def test_extract_sort_by_confidence():
    e = extract_entities("user wrote MEMORY.md about mp")
    if len(e) >= 2:
        check("sorted by confidence desc", e[0]["confidence"] >= e[-1]["confidence"])


def test_extract_word_boundary():
    """Don't match alias inside a longer word."""
    e = extract_entities("implementing xyz mp-system")
    mp_hits = [x for x in e if x["entity"] == "mp"]
    check("boundary check rejects mp-system", len(mp_hits) == 0)


# discuss handler tests
def test_discuss_returns_5_personas():
    r = handle_discuss("test task")
    check("discuss returns 5 personas", len(r["personas"]) == 5)
    check("phase=6", r["phase"] == 6)
    check("mode=discuss", r["mode"] == "discuss")


def test_discuss_persona_names():
    r = handle_discuss("test task")
    names = {p["name"] for p in r["personas"]}
    expected = {"analyst", "critic", "advocate", "skeptic", "synthesizer"}
    check("all 5 personas present", names == expected)


def test_discuss_each_has_response_score():
    r = handle_discuss("ship Plan F v8.1 to prod")
    for p in r["personas"]:
        check("  persona " + p["name"] + " has response", "response" in p)
        check("  persona " + p["name"] + " has score", "score" in p and 0 <= p["score"] <= 1)


def test_discuss_consensus_field():
    r = handle_discuss("ship v8.1")
    check("has consensus", "consensus" in r)
    check("has disagreements", "disagreements" in r)
    check("has avg_score", "avg_score" in r)


def test_discuss_consensus_from_synthesizer():
    r = handle_discuss("test")
    synth = next((p for p in r["personas"] if p["name"] == "synthesizer"), None)
    check("synthesizer present", synth is not None)
    if synth:
        check("consensus matches synthesizer", r["consensus"] == synth["response"])


def test_discuss_runs_in_parallel():
    """All 5 personas finish; total wall time ~1 persona, not 5.

    Uses mock LLM so 5 personas run in true parallel via run_batch (no network).
    """
    import time
    from scripts.llm_client import _mock_llm
    start = time.time()
    r = handle_discuss("test parallel speedup", llm=_mock_llm)
    elapsed = time.time() - start
    check("5 personas complete", len(r["personas"]) == 5)
    check("parallel timing under 2s", elapsed < 2.0, "elapsed=" + str(elapsed))


def test_discuss_with_custom_llm():
    """Custom LLM callable is used for all 5 personas."""
    calls = []
    def my_llm(system, msg):
        calls.append((system, msg))
        return "custom response " + str(len(calls))

    r = handle_discuss("test custom llm", llm=my_llm)
    check("custom llm called 5 times", len(calls) == 5)
    check("all responses custom", all("custom response" in p["response"] for p in r["personas"]))


def test_discuss_disagreement_detection():
    """When a persona scores low (0), it's a disagreement."""
    def bad_llm(system, msg):
        # very short reply → low score
        return ""

    r = handle_discuss("test bad llm", llm=bad_llm)
    check("all in disagreements when empty", len(r["disagreements"]) == 5)
    check("avg_score near 0", r["avg_score"] < 0.1)


def test_discuss_persona_definitions_constant():
    """DISCUSS_PERSONAS is module-level and well-formed."""
    check("5 personas constant", len(DISCUSS_PERSONAS) == 5)
    for p in DISCUSS_PERSONAS:
        check("  " + p["name"] + " has focus", "focus" in p and len(p["focus"]) > 0)


def test_discuss_cost_estimate():
    r = handle_discuss("test")
    check("has cost field", "cost" in r)
    check("cost has tokens", "tokens" in r["cost"])
    check("cost has latency", "latency_s" in r["cost"])


def run_all():
    print("=== mini-mp-agent Phase 5 tests ===")

    print("\n-- entity_extractor --")
    test_extract_empty()
    test_extract_known_alias()
    test_extract_file_path()
    test_extract_url()
    test_extract_chinese_phrase()
    test_extract_dedup()
    test_extract_confidence_filter()
    test_group_by_type()
    test_extract_sort_by_confidence()
    test_extract_word_boundary()

    print("\n-- discuss handler --")
    test_discuss_returns_5_personas()
    test_discuss_persona_names()
    test_discuss_each_has_response_score()
    test_discuss_consensus_field()
    test_discuss_consensus_from_synthesizer()
    test_discuss_runs_in_parallel()
    test_discuss_with_custom_llm()
    test_discuss_disagreement_detection()
    test_discuss_persona_definitions_constant()
    test_discuss_cost_estimate()

    total = len(PASS) + len(FAIL)
    print("\n=== " + str(len(PASS)) + "/" + str(total) + " PASS, " + str(len(FAIL)) + " FAIL ===")
    if FAIL:
        for f in FAIL:
            print("  FAIL: " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_all())
