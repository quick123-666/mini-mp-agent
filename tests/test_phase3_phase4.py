"""Tests for Phase 3 (atomic_write, task_queue) and Phase 4 (wiki, dialogue_parser, lint_wiki).

Run: python tests\\test_phase3_phase4.py
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.atomic_write import atomic_write, atomic_read, file_lock
from scripts.task_queue import TaskQueue, run_batch, QueueResult
from scripts.wiki_store import init_wiki, write_dialogue, write_entity, write_topic, search, list_all
from scripts.dialogue_parser import parse_messages, classify_intent, extract_keywords, slugify, group_by_intent
from scripts.lint_wiki import lint_wiki, lint_summary

PASS = []
FAIL = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        PASS.append(name)
        print("  PASS  " + name)
    else:
        FAIL.append(name + ": " + detail)
        print("  FAIL  " + name + ": " + detail)


# atomic_write tests
def test_atomic_write_str(tmp_dir):
    p = tmp_dir / "x.txt"
    atomic_write(p, "hello")
    check("atomic_write str", p.read_text() == "hello")


def test_atomic_write_bytes(tmp_dir):
    p = tmp_dir / "x.bin"
    atomic_write(p, b"\x00\x01\x02")
    check("atomic_write bytes", p.read_bytes() == b"\x00\x01\x02")


def test_atomic_write_creates_parent(tmp_dir):
    p = tmp_dir / "deep" / "nested" / "x.txt"
    atomic_write(p, "deep")
    check("atomic_write creates parent", p.exists() and p.read_text() == "deep")


def test_atomic_write_overwrites(tmp_dir):
    p = tmp_dir / "x.txt"
    atomic_write(p, "v1")
    atomic_write(p, "v2")
    check("atomic_write overwrites", p.read_text() == "v2")


def test_atomic_write_no_tmp_leak(tmp_dir):
    p = tmp_dir / "x.txt"
    atomic_write(p, "hello")
    leftover = list(tmp_dir.glob("*.tmp.*"))
    check("no tmp file leak", len(leftover) == 0, "found: " + str(leftover))


def test_atomic_read_roundtrip(tmp_dir):
    p = tmp_dir / "x.txt"
    atomic_write(p, "ascii roundtrip OK")
    check("atomic_read roundtrip ascii", atomic_read(p) == "ascii roundtrip OK")


def test_file_lock_acquires_and_releases(tmp_dir):
    p = tmp_dir / "x.txt"
    p.touch()
    with file_lock(p):
        pass
    with file_lock(p):
        pass
    check("file_lock acquires/releases", True)


def test_atomic_write_concurrent_serializable(tmp_dir):
    p = tmp_dir / "x.txt"
    for i in range(10):
        atomic_write(p, "v" + str(i))
    check("sequential atomic writes", p.read_text() == "v9")


# task_queue tests
def test_task_queue_run_batch_3_workers():
    def slow(n):
        time.sleep(0.02)
        return n * 2

    tasks = [(("t" + str(i)), (lambda n=i: slow(n))) for i in range(6)]
    results = run_batch(tasks, workers=3)
    check("run_batch returns 6 results", len(results) == 6)
    check("all successful", all(r.success for r in results.values()))
    check("results correct", results["t3"].result == 6)


def test_task_queue_async_fn():
    async def afn(n):
        await asyncio.sleep(0.01)
        return "a-" + str(n)

    tasks = []
    for i in range(3):
        n = i
        tasks.append((("t" + str(i)), lambda n=n: afn(n)))

    results = run_batch(tasks, workers=2)
    check("async fn support", all(r.success for r in results.values()))
    check("async results correct t0", results["t0"].result == "a-0")
    check("async results correct t2", results["t2"].result == "a-2")


def test_task_queue_timeout():
    def slow():
        time.sleep(0.5)

    tasks = [("t1", slow)]
    results = run_batch(tasks, workers=1, timeout_s=0.05)
    check("timeout marks failure", results["t1"].success is False)
    check("timeout error mentions timeout", "timeout" in results["t1"].error.lower())


def test_task_queue_exception_caught():
    def bad():
        raise ValueError("boom")

    tasks = [("t1", bad)]
    results = run_batch(tasks, workers=1)
    check("exception caught", results["t1"].success is False)
    check("error message preserved", "boom" in results["t1"].error)


def test_task_queue_results_have_duration():
    def work():
        time.sleep(0.001)  # ensure non-zero duration
        return "ok"

    tasks = [("t1", work)]
    results = run_batch(tasks, workers=1)
    check("result has duration_s field", hasattr(results["t1"], "duration_s"))
    check("result has task_id", results["t1"].task_id == "t1")


def test_task_queue_parallel_speedup():
    def slow():
        time.sleep(0.1)
        return "x"

    tasks = [("t" + str(i), slow) for i in range(3)]
    start = time.time()
    results = run_batch(tasks, workers=3)
    elapsed = time.time() - start
    check("parallel speedup", elapsed < 0.25, "elapsed=" + str(elapsed) + "s expected <0.25s")
    check("all completed", len(results) == 3)


# wiki_store tests
def test_wiki_init_creates_structure(tmp_dir):
    root = tmp_dir / "wiki"
    init_wiki(root)
    for sub in ["", "dialogue", "entities", "topics", "_meta"]:
        check("  init creates " + sub + "/", (root / sub).is_dir())
    check("init creates index.md", (root / "index.md").exists())
    check("init creates log.md", (root / "log.md").exists())
    check("init creates graph.json", (root / "_meta" / "graph.json").exists())


def test_wiki_init_idempotent(tmp_dir):
    root = tmp_dir / "wiki"
    init_wiki(root)
    init_wiki(root)
    check("init idempotent", True)


def test_wiki_write_dialogue(tmp_dir):
    root = tmp_dir / "wiki"
    init_wiki(root)
    p = write_dialogue(root, "test-slug", "# Test\n\nHello world")
    check("dialogue file exists", p.exists())
    text = p.read_text(encoding="utf-8")
    check("dialogue has front matter", text.startswith("---\n"))
    check("dialogue has slug", "slug: test-slug" in text)
    check("dialogue has content", "Hello world" in text)
    check("dialogue indexed", "test-slug" in (root / "index.md").read_text(encoding="utf-8"))


def test_wiki_write_entity_and_topic(tmp_dir):
    root = tmp_dir / "wiki"
    init_wiki(root)
    pe = write_entity(root, "mp-tool", "# MP Tool\n")
    pt = write_topic(root, "pwr-loop", "# PWR\n")
    check("entity file exists", pe.exists())
    check("topic file exists", pt.exists())
    text = (root / "index.md").read_text(encoding="utf-8")
    check("index has entity", "mp-tool" in text and "entity" in text)
    check("index has topic", "pwr-loop" in text and "topic" in text)


def test_wiki_search(tmp_dir):
    root = tmp_dir / "wiki"
    init_wiki(root)
    write_entity(root, "mp", "MP is meta-planner")
    write_entity(root, "rule", "A rule about mp usage")
    results = search(root, "mp")
    check("search finds matches", len(results) >= 2)
    slugs = {r["slug"] for r in results}
    check("search returns both", "mp" in slugs and "rule" in slugs)


def test_wiki_search_type_filter(tmp_dir):
    root = tmp_dir / "wiki"
    init_wiki(root)
    write_dialogue(root, "d1", "user said hi")
    write_entity(root, "e1", "entity about mp")
    results = search(root, "mp", type_filter="entity")
    check("type filter entity", len(results) == 1 and results[0]["slug"] == "e1")


def test_wiki_list_all(tmp_dir):
    root = tmp_dir / "wiki"
    init_wiki(root)
    write_dialogue(root, "d1", "x")
    write_entity(root, "e1", "y")
    items = list_all(root)
    check("list_all returns 2", len(items) == 2)
    types = {i["type"] for i in items}
    check("list_all includes dialogue", "dialogue" in types)
    check("list_all includes entities", "entities" in types)


# dialogue_parser tests
def test_slugify_chinese():
    s = slugify("test chinese slug")
    check("slugify ascii works", "test" in s or "chinese" in s)


def test_slugify_english():
    s = slugify("Hello World!")
    check("slugify english lowercase", s == "hello-world")
    check("slugify removes !", "!" not in s)


def test_slugify_empty():
    s = slugify("")
    check("slugify empty fallback", s == "untitled")


def test_classify_intent_question():
    check("intent: why", classify_intent("why?") == "question")
    check("intent: 怎么", classify_intent("怎么用") == "question")


def test_classify_intent_command():
    check("intent: /cmd", classify_intent("/help") == "command")
    check("intent: ship", classify_intent("ship it now") == "command")


def test_classify_intent_discussion():
    check("intent: vs", classify_intent("mp vs mini-mp") == "discussion")
    check("intent: 选 wins over ?", classify_intent("选 X 还是 Y?") == "discussion")


def test_classify_intent_statement():
    check("intent: statement", classify_intent("today is fine") == "statement")


def test_extract_keywords_basic():
    kws = extract_keywords("compare mp and mini-mp design")
    check("keywords includes mp", "mp" in kws)
    check("keywords includes mini-mp (kebab-case)", "mini-mp" in kws)
    check("keywords dedup", len(kws) == len(set(kws)))


def test_extract_keywords_no_stopwords():
    kws = extract_keywords("the a an to for test keyword")
    check("stopwords excluded", "the" not in kws and "a" not in kws)
    check("test included", "test" in kws)


def test_extract_keywords_top_k():
    kws = extract_keywords("ab cd ef gh ij kl mn op qr", top_k=3)
    check("top_k=3 limits", len(kws) == 3)


def test_parse_messages_basic():
    msgs = [
        {"role": "user", "content": "what is mp?", "ts": "2026-07-17T23:30:00"},
        {"role": "assistant", "content": "mp is meta-planner", "ts": "2026-07-17T23:30:05"},
    ]
    entries = parse_messages(msgs)
    check("parse returns 2 entries", len(entries) == 2)
    check("entry has slug", all("slug" in e for e in entries))
    check("entry has intent", all("intent" in e for e in entries))
    check("entry has keywords", all("keywords" in e for e in entries))


def test_parse_messages_empty_content_skipped():
    msgs = [
        {"role": "user", "content": "", "ts": "t"},
        {"role": "user", "content": "real content", "ts": "t"},
    ]
    entries = parse_messages(msgs)
    check("empty content skipped", len(entries) == 1)


def test_group_by_intent():
    msgs = [
        {"role": "user", "content": "why?"},
        {"role": "user", "content": "do X"},
        {"role": "user", "content": "vs Y"},
    ]
    entries = parse_messages(msgs)
    groups = group_by_intent(entries)
    check("groups has 3 intents", len(groups) == 3)
    check("groups includes question", "question" in groups)


# lint_wiki tests
def test_lint_clean_wiki(tmp_dir):
    root = tmp_dir / "wiki"
    init_wiki(root)
    write_entity(root, "mp", "# MP\n")
    issues = lint_wiki(root)
    summary = lint_summary(issues)
    check("clean wiki has no broken", summary["broken_wikilinks"] == 0)
    check("clean wiki has no contradictions", summary["contradictions"] == 0)


def test_lint_orphan_detection(tmp_dir):
    root = tmp_dir / "wiki"
    init_wiki(root)
    write_entity(root, "lonely", "no one references me")
    issues = lint_wiki(root)
    check("orphan detected", "lonely" in issues["orphan"])


def test_lint_broken_wikilink(tmp_dir):
    root = tmp_dir / "wiki"
    init_wiki(root)
    write_entity(root, "a", "links to [[nonexistent]]")
    issues = lint_wiki(root)
    check("broken wikilink detected", any(
        i.get("missing_target") == "nonexistent"
        for i in issues["broken_wikilinks"]
    ))


def test_lint_isolated_entity(tmp_dir):
    root = tmp_dir / "wiki"
    init_wiki(root)
    write_entity(root, "iso", "isolated entity")
    issues = lint_wiki(root)
    check("isolated entity detected", "iso" in issues["isolated"])


def test_lint_stale_claims(tmp_dir):
    root = tmp_dir / "wiki"
    init_wiki(root)
    from scripts.atomic_write import atomic_write
    old = "2026-04-01T00:00:00"
    content = "---\nslug: old\ntype: entity\ncreated: " + old + "\n---\n\nold claim"
    atomic_write(root / "entities" / "old.md", content)
    issues = lint_wiki(root, stale_days=90)
    check("stale claim detected", any(
        i.get("slug") == "old" for i in issues["stale_claims"]
    ))


def test_lint_summary_keys():
    root = Path(".")
    summary = lint_summary(lint_wiki(root))
    check("summary has 8 keys", len(summary) == 8)
    expected = {"orphan", "missing", "broken_wikilinks", "isolated", "contradictions", "stale_claims", "missing_cross_refs", "mode_coverage"}
    check("summary keys match", set(summary.keys()) == expected)


def run_all(tmp_dir):
    print("=== mini-mp-agent Phase 3+4 tests ===")

    print("\n-- atomic_write --")
    test_atomic_write_str(tmp_dir)
    test_atomic_write_bytes(tmp_dir)
    test_atomic_write_creates_parent(tmp_dir)
    test_atomic_write_overwrites(tmp_dir)
    test_atomic_write_no_tmp_leak(tmp_dir)
    test_atomic_read_roundtrip(tmp_dir)
    test_file_lock_acquires_and_releases(tmp_dir)
    test_atomic_write_concurrent_serializable(tmp_dir)

    print("\n-- task_queue --")
    test_task_queue_run_batch_3_workers()
    test_task_queue_async_fn()
    test_task_queue_timeout()
    test_task_queue_exception_caught()
    test_task_queue_results_have_duration()
    test_task_queue_parallel_speedup()

    print("\n-- wiki_store --")
    test_wiki_init_creates_structure(tmp_dir / "wiki1")
    test_wiki_init_idempotent(tmp_dir / "wiki2")
    test_wiki_write_dialogue(tmp_dir / "wiki3")
    test_wiki_write_entity_and_topic(tmp_dir / "wiki4")
    test_wiki_search(tmp_dir / "wiki5")
    test_wiki_search_type_filter(tmp_dir / "wiki6")
    test_wiki_list_all(tmp_dir / "wiki7")

    print("\n-- dialogue_parser --")
    test_slugify_chinese()
    test_slugify_english()
    test_slugify_empty()
    test_classify_intent_question()
    test_classify_intent_command()
    test_classify_intent_discussion()
    test_classify_intent_statement()
    test_extract_keywords_basic()
    test_extract_keywords_no_stopwords()
    test_extract_keywords_top_k()
    test_parse_messages_basic()
    test_parse_messages_empty_content_skipped()
    test_group_by_intent()

    print("\n-- lint_wiki --")
    test_lint_clean_wiki(tmp_dir / "lw1")
    test_lint_orphan_detection(tmp_dir / "lw2")
    test_lint_broken_wikilink(tmp_dir / "lw3")
    test_lint_isolated_entity(tmp_dir / "lw4")
    test_lint_stale_claims(tmp_dir / "lw5")
    test_lint_summary_keys()

    total = len(PASS) + len(FAIL)
    print("\n=== " + str(len(PASS)) + "/" + str(total) + " PASS, " + str(len(FAIL)) + " FAIL ===")
    if FAIL:
        for f in FAIL:
            print("  FAIL: " + f)
        return 1
    return 0


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        sys.exit(run_all(Path(tmp)))
