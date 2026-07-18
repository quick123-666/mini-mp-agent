"""Tests for wiki_store classification APIs (Phase 7+ ship v1.0.1).

Run: python -m tests.test_phase8_wiki_classification
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.wiki_store import (
    init_wiki,
    write_dialogue,
    write_entity,
    write_topic,
    wiki_by_mode,
    wiki_by_role,
    wiki_by_l1_recipe,
    wiki_by_failure_category,
    wiki_mode_coverage,
    render_coverage_md,
    generate_coverage_report,
    _refresh_cache,
)
from scripts.methods_tree import MethodsTree
from scripts.lint_wiki import lint_wiki, lint_summary


# ---------- Helpers ----------

def assert_eq(actual, expected, label=""):
    if actual != expected:
        raise AssertionError(f"[{label}] expected {expected!r}, got {actual!r}")


def assert_true(cond, label=""):
    if not cond:
        raise AssertionError(f"[{label}] expected truthy, got {cond!r}")


def assert_in(needle, haystack, label=""):
    if needle not in haystack:
        raise AssertionError(f"[{label}] {needle!r} not in {haystack!r}")


def setup_wiki(tmpdir: str):
    root = Path(tmpdir) / "wiki"
    init_wiki(root)
    return root


# ============================================================
# 1. Front-matter with classification fields
# ============================================================

def test_front_matter_has_classification():
    """write_dialogue with modes writes front-matter with modes field."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(
            root, "foo-bar",
            "content here",
            modes=["m_sprint"],
            l1_recipes=["plan_task"],
            roles=["planner"],
        )
        text = (root / "dialogue" / "foo-bar.md").read_text(encoding="utf-8")
        assert_true("modes: [m_sprint]" in text or "modes:" in text,
                    "front-matter has modes")
        assert_in("plan_task", text, "l1_recipes visible")
        assert_in("planner", text, "roles visible")


def test_front_matter_without_classification():
    """write_dialogue without kwargs still works (backward compat)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "old-style", "legacy content")
        text = (root / "dialogue" / "old-style.md").read_text(encoding="utf-8")
        assert_true(text.startswith("---"), "still has YAML fm")
        assert_true("slug: old-style" in text, "old fm format preserved")
        assert_true("modes:" not in text or "l1_recipes:" not in text,
                    "no spurious classification fields")


def test_multiple_modes():
    """write_entity with multiple modes writes them all to front-matter."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_entity(
            root, "mini-mp",
            "an entity",
            modes=["m_task", "m_auto"],
            roles=["planner", "worker"],
        )
        text = (root / "entities" / "mini-mp.md").read_text(encoding="utf-8")
        assert_in("m_task", text, "first mode")
        assert_in("m_auto", text, "second mode")
        assert_in("planner", text, "first role")
        assert_in("worker", text, "second role")


# ============================================================
# 2. Cache maintenance
# ============================================================

def test_cache_updated_after_write():
    """After write_dialogue, .frontmatter_cache.json contains entry."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "cached-1", "hi",
                       modes=["m_sprint"], l1_recipes=["plan_task"], roles=["planner"])
        cache_path = root / "_meta" / ".frontmatter_cache.json"
        assert_true(cache_path.exists(), "cache file exists")
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        assert_in("cached-1", cache, "entry in cache")
        assert_eq(cache["cached-1"]["modes"], ["m_sprint"], "modes in cache")
        assert_eq(cache["cached-1"]["l1_recipes"], ["plan_task"], "recipes in cache")
        assert_eq(cache["cached-1"]["roles"], ["planner"], "roles in cache")


def test_cache_refresh_rebuild():
    """_refresh_cache rebuilds from disk files (useful after manual edits)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        # Write 2 entries (cache populated incrementally)
        write_dialogue(root, "x1", "a", modes=["m_qa"])
        write_dialogue(root, "x2", "b", roles=["worker"])
        # Delete cache
        (root / "_meta" / ".frontmatter_cache.json").unlink()
        # Refresh
        cache = _refresh_cache(root)
        assert_eq(len(cache), 2, "cache rebuilt with 2")
        assert_in("x1", cache, "x1 in cache")
        assert_in("x2", cache, "x2 in cache")


# ============================================================
# 3. Query APIs
# ============================================================

def test_wiki_by_mode_returns_correct_entries():
    """wiki_by_mode('m_sprint') returns entries tagged with that mode."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "d1", "x", modes=["m_sprint"])
        write_dialogue(root, "d2", "y", modes=["m_task"])
        write_entity(root, "e1", "z", modes=["m_sprint"])

        results = wiki_by_mode(root, "m_sprint")
        slugs = {e.slug for e in results}
        assert_eq(slugs, {"d1", "e1"}, "m_sprint returns d1 + e1")


def test_wiki_by_role_returns_correct_entries():
    """wiki_by_role('planner') returns entries involving planner."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "p1", "x", roles=["planner"])
        write_dialogue(root, "w1", "y", roles=["worker"])
        write_entity(root, "e1", "z", roles=["planner", "worker"])

        results = wiki_by_role(root, "planner")
        slugs = {e.slug for e in results}
        assert_eq(slugs, {"p1", "e1"}, "planner returns p1 + e1")


def test_wiki_by_l1_recipe():
    """wiki_by_l1_recipe returns entries produced by a recipe."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "d1", "x", l1_recipes=["decompose_task", "plan_task"])
        write_dialogue(root, "d2", "y", l1_recipes=["execute_task"])

        results = wiki_by_l1_recipe(root, "decompose_task")
        slugs = {e.slug for e in results}
        assert_eq(slugs, {"d1"}, "decompose_task returns d1 only")


def test_wiki_by_failure_category():
    """wiki_by_failure_category returns reflection entries."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "r1", "x", failure_categories=["loop_stuck"])
        write_dialogue(root, "r2", "y", failure_categories=["score_plateau"])
        write_dialogue(root, "ok", "z", failure_categories=None)

        results = wiki_by_failure_category(root, "loop_stuck")
        slugs = {e.slug for e in results}
        assert_eq(slugs, {"r1"}, "loop_stuck returns r1 only")


def test_query_returns_empty_for_no_match():
    """wiki_by_* returns empty list when no entries match."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "d1", "x", modes=["m_qa"])
        results = wiki_by_mode(root, "m_xyz_nope")
        assert_eq(len(results), 0, "no match returns []")


def test_entry_has_path_attribute():
    """WikiEntry has .path pointing at the actual file location."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "path-test", "x", modes=["m_qa"])
        results = wiki_by_mode(root, "m_qa")
        assert_eq(len(results), 1, "1 entry")
        entry = results[0]
        # Windows path; check with forward-slash separator
        normalized = entry.path.replace("\\", "/")
        assert_true(normalized.endswith("dialogue/path-test.md"),
                    f"path correct (got {entry.path})")


# ============================================================
# 4. Coverage report
# ============================================================

def test_coverage_basic_stats():
    """wiki_mode_coverage returns total_entries and by_method counts."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "a", "x", modes=["m_sprint"], l1_recipes=["plan_task"],
                       roles=["planner"])
        write_dialogue(root, "b", "y", modes=["m_sprint"], roles=["worker"])
        write_entity(root, "e", "z", l1_recipes=["plan_task"], roles=["planner"])

        tree = MethodsTree()
        cov = wiki_mode_coverage(root, tree)
        assert_eq(cov["total_entries"], 3, "total entries")
        assert_eq(cov["by_method"].get("m_sprint"), 2, "m_sprint count")
        assert_eq(cov["by_method"].get("plan_task"), 2, "plan_task count")
        assert_eq(cov["by_method"].get("m_task", 0), 0, "m_task not present")
        assert_eq(cov["by_role"].get("planner"), 2, "planner count")
        assert_eq(cov["by_role"].get("worker"), 1, "worker count")


def test_coverage_untagged_entries():
    """Entries without classification show up in untagged_entries."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "tagged", "x", modes=["m_qa"])
        write_dialogue(root, "untagged", "y")  # No classification
        cov = wiki_mode_coverage(root, MethodsTree())
        assert_eq(cov["untagged_entries"], ["untagged"], "untagged list correct")


def test_coverage_unused_methods():
    """Methods in tree with 0 wiki entries show as unused."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "only-m-task", "x", modes=["m_task"])
        tree = MethodsTree()
        cov = wiki_mode_coverage(root, tree)
        # m_task is used; many methods are NOT used
        assert_in("m_task", cov["by_method"], "m_task used")
        assert_in("atomic_write", cov["unused_methods"], "atomic_write unused")
        assert_in("parallel_execute", cov["unused_methods"], "parallel_execute unused")


def test_coverage_without_methods_tree():
    """Without methods_tree, unused_methods is empty (don't claim gaps)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "x", "y", modes=["m_qa"])
        cov = wiki_mode_coverage(root, methods_tree=None)
        assert_eq(cov["unused_methods"], [], "no method_tree means no gaps reported")


def test_render_coverage_md():
    """render_coverage_md produces a human-readable Markdown string."""
    cov = {
        "total_entries": 5,
        "by_method": {"m_sprint": 3, "plan_task": 2},
        "by_role": {"planner": 4, "worker": 1},
        "by_mode": {"m_sprint": 3},
        "untagged_entries": [],
        "unused_methods": ["atomic_write"],
    }
    md = render_coverage_md(cov)
    assert_in("Wiki Method Coverage", md, "title")
    assert_in("m_sprint", md, "m_sprint in body")
    assert_in("plan_task", md, "plan_task in body")
    assert_in("planner", md, "planner in body")
    assert_in("atomic_write", md, "unused method noted")


def test_generate_coverage_report_writes_file():
    """generate_coverage_report writes to wiki/coverage.md."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "x", "y", modes=["m_sprint"])
        p = generate_coverage_report(root, MethodsTree())
        assert_eq(p.name, "coverage.md", "filename")
        assert_true(p.exists(), "file exists")
        text = p.read_text(encoding="utf-8")
        assert_in("Wiki Method Coverage", text, "title in file")


# ============================================================
# 5. Lint 8th step: mode_coverage
# ============================================================

def test_lint_includes_mode_coverage():
    """lint_wiki with methods_tree adds 'mode_coverage' to issues."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "x", "y", modes=["m_qa"])
        tree = MethodsTree()
        issues = lint_wiki(root, methods_tree=tree)
        assert_in("mode_coverage", issues, "8th step present")
        # m_qa is used; atomic_write is not
        kinds = {iss.get("kind") for iss in issues["mode_coverage"]}
        assert_in("method_unused", kinds, "method_unused kind recorded")


def test_lint_without_methods_tree_empty_mode_coverage():
    """lint_wiki without methods_tree has empty mode_coverage list."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "x", "y", modes=["m_qa"])
        issues = lint_wiki(root)
        assert_in("mode_coverage", issues, "key present")
        assert_eq(issues["mode_coverage"], [], "no issues without tree")


def test_lint_summary_8_keys():
    """lint_summary returns 8 keys (mode_coverage now included)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        summary = lint_summary(lint_wiki(root))
        assert_eq(len(summary), 8, "8 keys")
        assert_in("mode_coverage", summary, "mode_coverage key")


def test_lint_summary_includes_unused_method_count():
    """If methods_tree given, mode_coverage count > 0 reflects unused methods."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        write_dialogue(root, "x", "y", modes=["m_qa"])  # only m_qa used
        tree = MethodsTree()
        issues = lint_wiki(root, methods_tree=tree)
        # Most methods unused -> mode_coverage non-empty
        assert_true(len(issues["mode_coverage"]) > 0, "many unused methods reported")


# ============================================================
# 6. End-to-end: classify when persisting PWR
# ============================================================

def test_persist_to_wiki_classifies_entries():
    """When persist_to_wiki called with classification, wiki entries have it.

    v1.1.0: persist_to_wiki now writes 1 topic page (no dialogue/entity
    pages). With write_topic_for=None, no entries are written, so the
    wiki_by_mode query returns 0. With write_topic_for set, the topic
    page is the entry tagged with classification.
    """
    from scripts.wiki_integration import persist_to_wiki as pi_persist
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_wiki(tmp)
        pwr = {
            "status": "success",
            "iterations": [
                {"planner": "do thing 1", "worker": "did it", "reviewer": "ok"}
            ],
        }
        result = pi_persist(
            root, "ship Plan F v8.1", pwr,
            write_topic_for="mp-test-classify",
            modes=["m_sprint"],
            l1_recipes=["plan_task", "execute_task"],
            roles=["planner", "worker"],
        )
        # Now query the wiki
        by_mode = wiki_by_mode(root, "m_sprint")
        assert_true(len(by_mode) >= 1, "at least 1 entry tagged m_sprint (topic page)")
        # Verify cache has classification
        cache = json.loads((root / "_meta" / ".frontmatter_cache.json").read_text())
        first_slug = next(iter(cache.keys()))
        assert_in("m_sprint", cache[first_slug]["modes"], "modes in cache")


# ============================================================
# Test runner
# ============================================================

TESTS = [
    test_front_matter_has_classification,
    test_front_matter_without_classification,
    test_multiple_modes,
    test_cache_updated_after_write,
    test_cache_refresh_rebuild,
    test_wiki_by_mode_returns_correct_entries,
    test_wiki_by_role_returns_correct_entries,
    test_wiki_by_l1_recipe,
    test_wiki_by_failure_category,
    test_query_returns_empty_for_no_match,
    test_entry_has_path_attribute,
    test_coverage_basic_stats,
    test_coverage_untagged_entries,
    test_coverage_unused_methods,
    test_coverage_without_methods_tree,
    test_render_coverage_md,
    test_generate_coverage_report_writes_file,
    test_lint_includes_mode_coverage,
    test_lint_without_methods_tree_empty_mode_coverage,
    test_lint_summary_8_keys,
    test_lint_summary_includes_unused_method_count,
    test_persist_to_wiki_classifies_entries,
]


def main():
    passed = 0
    failed = 0
    print(f"=== wiki classification tests (v1.0.1) ({len(TESTS)}) ===")
    for t in TESTS:
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERR]  {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed+failed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
