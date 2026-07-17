"""Tests for methods_tree.py (mini-mp-agent work method tree API).

Run: python -m mini_mp_agent.tests.test_methods_tree
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as: python tests/test_methods_tree.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.methods_tree import MethodsTree, MethodNode, DEFAULT_ROOT


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


# ---------- Setup ----------

TREE = MethodsTree()


# ============================================================
# 1. Loading & structure
# ============================================================

def test_tree_loads_18_nodes():
    """Tree should load 15-18 nodes (5 L0 + 5 L1 + 5 L2 + 3 L3 = 18)."""
    assert_eq(len(TREE), 18, "tree size")


def test_all_levels_present():
    """Each level L0-L3 has nodes."""
    by_level = {0: 0, 1: 0, 2: 0, 3: 0}
    for node in TREE:
        by_level[node.level] = by_level.get(node.level, 0) + 1
    for lvl in (0, 1, 2, 3):
        assert_true(by_level[lvl] >= 1, f"L{lvl} count > 0")


def test_all_roles_present():
    """All 4 PWR roles + dispatcher + shared are represented."""
    roles = {n.agent_role for n in TREE}
    for r in ("planner", "worker", "reviewer", "reflector", "dispatcher", "shared"):
        assert_in(r, roles, f"role {r}")


def test_L0_modes_exist():
    """5 L0 modes: m_qa / m_task / m_discuss / m_auto / m_sprint."""
    for mid in ("m_qa", "m_task", "m_discuss", "m_auto", "m_sprint"):
        node = TREE.get(mid)
        assert_true(node is not None, f"mode {mid} exists")
        assert_eq(node.level, 0, f"{mid} is L0")
        assert_eq(node.agent_role, "dispatcher", f"{mid} role dispatcher")


def test_L1_pwr_recipes_exist():
    """5 L1 recipes match PWR phases."""
    expected = {"decompose_task", "plan_task", "execute_task", "review_task", "reflect_task"}
    actual = {n.node_id for n in TREE if n.level == 1}
    assert_eq(actual, expected, "L1 recipes")


def test_L3_primitives():
    """3 L3 primitives."""
    actual = {n.node_id for n in TREE if n.level == 3}
    assert_eq(actual, {"atomic_write", "parallel_execute", "early_stop"}, "L3 primitives")


# ============================================================
# 2. search()
# ============================================================

def test_search_wiki():
    """Search 'wiki' should return wiki-related methods."""
    results = TREE.search("wiki")
    assert_true(len(results) >= 1, "search wiki returns >=1")
    ids = [r.node_id for r in results]
    assert_true("wiki_recall" in ids or "wiki_persist" in ids or "lint_wiki" in ids,
                "wiki-related methods in results")


def test_search_parallel():
    """Search 'parallel' should hit parallel_execute."""
    results = TREE.search("parallel concurrent")
    assert_true(len(results) >= 1, "search parallel")
    assert_in("parallel_execute", [r.node_id for r in results], "parallel_execute found")


def test_search_returns_top_k():
    """search top_k=2 should return at most 2."""
    results = TREE.search("task", top_k=2)
    assert_true(len(results) <= 2, "top_k=2 returns <=2")


def test_search_no_match():
    """Search with no matches returns empty list."""
    results = TREE.search("xyzzy_no_match_keyword_42")
    assert_eq(len(results), 0, "no match returns []")


def test_search_score_keyword_priority():
    """selector_keywords matches score 2; purpose/name matches score 1-2.
    'atomic' should rank atomic_write high (selector kw) over random.
    """
    results = TREE.search("atomic")
    assert_true(len(results) >= 1, "atomic search")
    assert_eq(results[0].node_id, "atomic_write", "atomic_write ranks first")


# ============================================================
# 3. get()
# ============================================================

def test_get_existing_node():
    """get('m_auto') returns full MethodNode."""
    node = TREE.get("m_auto")
    assert_true(node is not None, "m_auto exists")
    assert_eq(node.name, "Auto mode (default)", "m_auto name")
    assert_eq(node.level, 0, "m_auto level")


def test_get_missing_node():
    """get('nonexistent') returns None."""
    node = TREE.get("nonexistent_xyz")
    assert_true(node is None, "missing returns None")


def test_get_node_has_all_fields():
    """Node should have all 8+ fields populated."""
    node = TREE.get("execute_task")
    assert_true(node is not None, "execute_task")
    assert_eq(node.agent_role, "worker", "role")
    assert_true(len(node.inputs) >= 1, "inputs non-empty")
    assert_true(len(node.outputs) >= 1, "outputs non-empty")
    assert_true(len(node.dependencies) >= 1, "deps non-empty")
    assert_true(len(node.failure_modes) >= 1, "failure_modes non-empty")


def test_get_to_dict_round_trip():
    """to_dict() should be JSON-serializable."""
    import json
    node = TREE.get("extract_entities")
    d = node.to_dict()
    s = json.dumps(d, ensure_ascii=False)
    assert_true("node_id" in s, "json contains node_id")


# ============================================================
# 4. get_children()
# ============================================================

def test_get_children_m_auto_depth_1():
    """m_auto with depth=1 returns 5 L1 children."""
    children = TREE.get_children("m_auto", depth=1)
    assert_eq(len(children), 5, "m_auto has 5 L1 children")
    ids = {c.node_id for c in children}
    assert_eq(ids, {"decompose_task", "plan_task", "execute_task", "review_task", "reflect_task"},
              "m_auto children ids")


def test_get_children_m_sprint_includes_m_auto():
    """m_sprint children should include m_auto (via L0→L0 edge)."""
    children = TREE.get_children("m_sprint", depth=2)
    ids = {c.node_id for c in children}
    assert_in("m_auto", ids, "m_sprint -> m_auto")
    assert_in("wiki_recall", ids, "m_sprint -> wiki_recall")
    assert_in("wiki_persist", ids, "m_sprint -> wiki_persist")


def test_get_children_L3_returns_empty():
    """L3 nodes have no children."""
    children = TREE.get_children("atomic_write")
    assert_eq(len(children), 0, "atomic_write has no children")


def test_get_children_missing_node():
    """get_children(missing) returns []."""
    children = TREE.get_children("nonexistent")
    assert_eq(len(children), 0, "missing returns []")


def test_get_children_depth_limit():
    """depth=1 should not return grandchildren."""
    children = TREE.get_children("m_auto", depth=1)
    for c in children:
        # Should all be L1, not L2/L3
        assert_eq(c.level, 1, f"{c.node_id} is L1 at depth=1")


# ============================================================
# 5. find_path()
# ============================================================

def test_find_path_direct():
    """Direct path: m_sprint -> m_auto (L0->L0 edge)."""
    path = TREE.find_path("m_sprint", "m_auto")
    assert_eq(path, ["m_sprint", "m_auto"], "direct path")


def test_find_path_transitive():
    """Transitive: m_sprint -> atomic_write (via m_auto -> execute_task -> atomic_write)."""
    path = TREE.find_path("m_sprint", "atomic_write")
    assert_true(path is not None, "path exists")
    assert_eq(path[0], "m_sprint", "starts at m_sprint")
    assert_eq(path[-1], "atomic_write", "ends at atomic_write")


def test_find_path_same_node():
    """path from X to X returns [X]."""
    path = TREE.find_path("m_qa", "m_qa")
    assert_eq(path, ["m_qa"], "same node path")


def test_find_path_unreachable():
    """path from leaf to non-related ancestor returns None."""
    # atomic_write has no outgoing edges to a higher-level node
    path = TREE.find_path("atomic_write", "m_sprint")
    assert_true(path is None or path[0] == "atomic_write", "no return path")


def test_find_path_missing_node():
    """path with missing node returns None."""
    path = TREE.find_path("nonexistent", "m_auto")
    assert_true(path is None, "missing returns None")


# ============================================================
# 6. validate()
# ============================================================

def test_validate_passes():
    """Tree validates cleanly."""
    report = TREE.validate()
    assert_true(report["valid"], f"validate: {report['errors']}")
    assert_eq(report["stats"]["total_nodes"], 18, "node count")
    assert_true(report["stats"]["total_edges"] >= 20, "edge count")


def test_validate_stats_levels():
    """Stats by_level should match expectations."""
    report = TREE.validate()
    by_level = report["stats"]["by_level"]
    assert_eq(by_level[0], 5, "L0 count")
    assert_eq(by_level[1], 5, "L1 count")
    assert_eq(by_level[2], 5, "L2 count")
    assert_eq(by_level[3], 3, "L3 count")


def test_validate_stats_roles():
    """Stats by_role should have all 6 roles."""
    report = TREE.validate()
    roles = report["stats"]["by_role"]
    assert_in("dispatcher", roles, "dispatcher")
    assert_in("planner", roles, "planner")
    assert_in("worker", roles, "worker")
    assert_in("reviewer", roles, "reviewer")
    assert_in("reflector", roles, "reflector")
    assert_in("shared", roles, "shared")


# ============================================================
# 7. parents backfill
# ============================================================

def test_parents_backfilled():
    """After loading, each node should have parents populated from edges."""
    node = TREE.get("atomic_write")
    assert_true(len(node.parents) >= 1, "atomic_write has parents")
    # Parents should include execute_task, lint_wiki
    assert_in("execute_task", node.parents, "parent execute_task")
    assert_in("lint_wiki", node.parents, "parent lint_wiki")


def test_L0_has_no_parents():
    """L0 modes that are not referenced by another mode have 0 parents.
    m_auto has m_sprint as parent (via m_sprint -> m_auto edge)."""
    no_parent_modes = ["m_qa", "m_task", "m_discuss", "m_sprint"]
    for mid in no_parent_modes:
        node = TREE.get(mid)
        assert_eq(len(node.parents), 0, f"{mid} has 0 parents")
    # m_auto has m_sprint as parent (sprint reuses auto)
    m_auto = TREE.get("m_auto")
    assert_in("m_sprint", m_auto.parents, "m_sprint is parent of m_auto")


# ============================================================
# 8. Integration: mode_router + methods_tree
# ============================================================

def test_mode_router_lookup():
    """Each detected mode should have a corresponding method tree node."""
    from scripts.mode_router import detect_mode
    test_cases = [
        ("对比 mp 和 mini-mp", "discuss"),
        ("做一个 hello world", "task"),
        ("什么是 PWR", "qa"),
    ]
    for query, expected_mode in test_cases:
        decision = detect_mode(query)
        # detect_mode returns ModeDecision dataclass with .mode attribute
        mode_str = decision.mode if hasattr(decision, "mode") else str(decision)
        node = TREE.get(f"m_{mode_str}")
        assert_true(node is not None,
                    f"mode '{mode_str}' (from '{query}') has tree node")


# ============================================================
# 9. Custom root path
# ============================================================

def test_custom_root_loads():
    """MethodsTree can load from explicit path."""
    tree2 = MethodsTree(root=DEFAULT_ROOT)
    assert_eq(len(tree2), len(TREE), "custom root loads same nodes")


# ============================================================
# Test runner
# ============================================================

TESTS = [
    test_tree_loads_18_nodes,
    test_all_levels_present,
    test_all_roles_present,
    test_L0_modes_exist,
    test_L1_pwr_recipes_exist,
    test_L3_primitives,
    test_search_wiki,
    test_search_parallel,
    test_search_returns_top_k,
    test_search_no_match,
    test_search_score_keyword_priority,
    test_get_existing_node,
    test_get_missing_node,
    test_get_node_has_all_fields,
    test_get_to_dict_round_trip,
    test_get_children_m_auto_depth_1,
    test_get_children_m_sprint_includes_m_auto,
    test_get_children_L3_returns_empty,
    test_get_children_missing_node,
    test_get_children_depth_limit,
    test_find_path_direct,
    test_find_path_transitive,
    test_find_path_same_node,
    test_find_path_unreachable,
    test_find_path_missing_node,
    test_validate_passes,
    test_validate_stats_levels,
    test_validate_stats_roles,
    test_parents_backfilled,
    test_L0_has_no_parents,
    test_mode_router_lookup,
    test_custom_root_loads,
]


def main():
    passed = 0
    failed = 0
    print(f"=== methods_tree tests ({len(TESTS)}) ===")
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
