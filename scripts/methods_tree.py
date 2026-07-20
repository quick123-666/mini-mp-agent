"""mini-mp-agent Method Tree API.

Independent work method tree system (15 methods, 4 levels L0-L3).
Designed to be self-contained — no external mp dependency.

Usage:
    from mini_mp_agent.scripts.methods_tree import MethodsTree
    tree = MethodsTree()                          # load from default location
    tree = MethodsTree(root="path/to/methods")     # explicit path

    # 4 API:
    tree.search("parallel execute", top_k=3)       # keyword match
    tree.get("execute_task")                       # full method definition
    tree.get_children("m_auto", depth=2)           # expand tree downward
    tree.find_path("m_sprint", "atomic_write")     # dependency path

    # Validation:
    tree.validate()                                 # check consistency
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any

# Default location: ../methods relative to scripts/
DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "methods"


@dataclass
class MethodNode:
    """One method in the tree."""
    node_id: str
    name: str
    level: int
    purpose: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    failure_modes: List[str] = field(default_factory=list)
    agent_role: str = "shared"
    selector_keywords: List[str] = field(default_factory=list)
    maturity: str = "experimental"
    evidence: str = ""
    parents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "level": self.level,
            "purpose": self.purpose,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "dependencies": self.dependencies,
            "failure_modes": self.failure_modes,
            "agent_role": self.agent_role,
            "selector_keywords": self.selector_keywords,
            "maturity": self.maturity,
            "evidence": self.evidence,
            "parents": self.parents,
        }


class MethodsTree:
    """Hierarchical work method tree (15 methods, 4 levels).

    Levels:
        L0 = mode entry (m_qa, m_task, m_discuss, m_auto, m_sprint)
        L1 = high-level recipe (decompose_task, plan_task, execute_task, ...)
        L2 = sub-step (wiki_recall, score_output, extract_entities, ...)
        L3 = primitive (atomic_write, parallel_execute, early_stop)

    Loaded from methods/_index.json + recipes/*.yaml.
    """

    def __init__(self, root: Path | str = DEFAULT_ROOT):
        self.root = Path(root)
        self._nodes: Dict[str, MethodNode] = {}
        self._edges: List[Dict[str, str]] = []
        self._load()

    # ---------- Public API ----------

    def search(self, query: str, top_k: int = 3) -> List[MethodNode]:
        """Keyword search across purpose, name, and selector_keywords.

        Returns top_k MethodNode ranked by score (simple keyword overlap).
        """
        query_lower = query.lower()
        query_tokens = set(query_lower.split())

        scored: List[tuple] = []
        for node in self._nodes.values():
            score = 0
            for kw in node.selector_keywords:
                if kw.lower() in query_lower:
                    score += 2
            for token in query_tokens:
                if token in node.purpose.lower():
                    score += 1
                if token in node.name.lower():
                    score += 2
            if score > 0:
                scored.append((score, node))

        scored.sort(key=lambda x: (-x[0], x[1].node_id))
        return [n for _, n in scored[:top_k]]

    def get(self, node_id: str) -> Optional[MethodNode]:
        """Look up a method by node_id. Returns None if missing."""
        return self._nodes.get(node_id)

    def get_children(self, node_id: str, depth: int = 1) -> List[MethodNode]:
        """Expand a node's children recursively up to `depth` levels.

        For L0 nodes, returns direct L1 children.
        For L1 nodes, returns direct L2/L3 children.
        For L2/L3 nodes, returns empty list.
        """
        start = self._nodes.get(node_id)
        if not start:
            return []

        # Find all nodes where this node_id is a parent (i.e. children)
        direct_children_ids = set()
        for edge in self._edges:
            if edge["from"] == node_id:
                direct_children_ids.add(edge["to"])

        result: List[MethodNode] = []
        seen = set()
        frontier = direct_children_ids
        for _ in range(depth):
            next_frontier = set()
            for child_id in frontier:
                if child_id in seen:
                    continue
                seen.add(child_id)
                node = self._nodes.get(child_id)
                if node:
                    result.append(node)
                    # expand further via graph edges
                    for edge in self._edges:
                        if edge["from"] == child_id:
                            next_frontier.add(edge["to"])
            frontier = next_frontier
        return result

    def find_path(self, from_id: str, to_id: str) -> Optional[List[str]]:
        """Find shortest path from `from_id` to `to_id` via dependencies/edges.

        BFS. Returns list of node_ids, or None if unreachable.
        """
        if from_id == to_id:
            return [from_id]
        if from_id not in self._nodes or to_id not in self._nodes:
            return None

        # Build adjacency
        adj: Dict[str, List[str]] = {nid: [] for nid in self._nodes}
        for edge in self._edges:
            adj[edge["from"]].append(edge["to"])

        # BFS
        from collections import deque
        visited = {from_id}
        queue = deque([(from_id, [from_id])])
        while queue:
            cur, path = queue.popleft()
            for nxt in adj.get(cur, []):
                if nxt == to_id:
                    return path + [nxt]
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, path + [nxt]))
        return None

    def validate(self) -> Dict[str, Any]:
        """Validate tree consistency.

        Returns: {valid: bool, errors: list[str], stats: dict}
        """
        errors = []

        # Check all edges reference real nodes
        node_ids = set(self._nodes.keys())
        for edge in self._edges:
            if edge["from"] not in node_ids:
                errors.append(f"edge from unknown: {edge['from']}")
            if edge["to"] not in node_ids:
                errors.append(f"edge to unknown: {edge['to']}")

        # Check level transitions. Edges represent 'uses' (not strict parent-child),
        # so we allow:
        #   - same level (L0→L0 like m_sprint→m_auto)
        #   - +1 level (L0→L1, L1→L2, L2→L3) for direct expansion
        #   - +2 levels (L0→L2, L1→L3) for 'uses' relationships that skip intermediates
        # Disallow going UP in level (would be a cycle).
        for edge in self._edges:
            f, t = edge["from"], edge["to"]
            if f in self._nodes and t in self._nodes:
                lvl_from = self._nodes[f].level
                lvl_to = self._nodes[t].level
                diff = lvl_to - lvl_from
                if diff < 0:
                    errors.append(
                        f"upward transition {f}(L{lvl_from}) -> {t}(L{lvl_to})"
                    )
                elif diff > 3:
                    errors.append(
                        f"level jump too large {f}(L{lvl_from}) -> {t}(L{lvl_to})"
                    )

        # Stats
        by_level = {0: 0, 1: 0, 2: 0, 3: 0}
        by_role: Dict[str, int] = {}
        for node in self._nodes.values():
            by_level[node.level] = by_level.get(node.level, 0) + 1
            by_role[node.agent_role] = by_role.get(node.agent_role, 0) + 1

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "stats": {
                "total_nodes": len(self._nodes),
                "total_edges": len(self._edges),
                "by_level": by_level,
                "by_role": by_role,
            },
        }

    def __len__(self) -> int:
        return len(self._nodes)

    def __iter__(self):
        return iter(self._nodes.values())

    # ---------- Private ----------

    def _load(self) -> None:
        """Load _index.json + recipes/*.yaml into self._nodes and self._edges."""
        index_path = self.root / "_index.json"
        if not index_path.exists():
            raise FileNotFoundError(f"method index not found: {index_path}")

        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)

        # Load recipes
        recipes_dir = self.root / "recipes"
        for entry in index["nodes"]:
            recipe_path = recipes_dir / f"{entry['id']}.yaml"
            if not recipe_path.exists():
                continue
            node = self._parse_yaml_recipe(recipe_path)
            if node:
                self._nodes[node.node_id] = node

        # Edges
        self._edges = list(index.get("edges", []))

        # Backfill parents (reverse edges)
        for edge in self._edges:
            parent = self._nodes.get(edge["from"])
            child = self._nodes.get(edge["to"])
            if parent and child:
                if edge["to"] not in parent.parents:
                    pass  # parent.parents populated by reverse map below
        # Build parents from edges
        parent_map: Dict[str, List[str]] = {nid: [] for nid in self._nodes}
        for edge in self._edges:
            if edge["to"] in parent_map:
                parent_map[edge["to"]].append(edge["from"])
        for nid, parents in parent_map.items():
            self._nodes[nid].parents = parents

    def _parse_yaml_recipe(self, path: Path) -> Optional[MethodNode]:
        """Parse a YAML recipe file into a MethodNode.

        Uses a minimal parser to avoid pulling in PyYAML.
        Supports: key: value, key: [list], - item
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None

        data: Dict[str, Any] = {}
        current_key: Optional[str] = None
        current_list: Optional[List[str]] = None

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- "):
                # List item
                if current_list is not None:
                    current_list.append(stripped[2:].strip().strip('"').strip("'"))
                continue
            if ":" in stripped:
                # Flush previous list
                if current_key and current_list is not None:
                    data[current_key] = current_list
                    current_list = None
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()
                if val == "":
                    # List starts on next lines
                    current_key = key
                    current_list = []
                elif val.startswith("[") and val.endswith("]"):
                    # Inline list
                    items = val[1:-1].split(",")
                    data[key] = [i.strip().strip('"').strip("'") for i in items if i.strip()]
                else:
                    data[key] = val.strip('"').strip("'")
                    current_key = None
                    current_list = None

        # Flush trailing list
        if current_key and current_list is not None:
            data[current_key] = current_list

        # Coerce numeric/string fields. Accept both '1' and 'L1' forms.
        if "level" in data:
            raw = data["level"]
            if isinstance(raw, str):
                # Strip optional 'L' / 'l' prefix; fall back to 0 only if neither parses.
                stripped = raw.strip().lstrip("Ll")
                try:
                    data["level"] = int(stripped)
                except (ValueError, TypeError):
                    data["level"] = 0
            else:
                try:
                    data["level"] = int(raw)
                except (ValueError, TypeError):
                    data["level"] = 0

        return MethodNode(
            node_id=data.get("node_id", path.stem),
            name=data.get("name", path.stem),
            level=data.get("level", 0),
            purpose=data.get("purpose", ""),
            inputs=data.get("inputs", []) if isinstance(data.get("inputs"), list) else [],
            outputs=data.get("outputs", []) if isinstance(data.get("outputs"), list) else [],
            dependencies=data.get("dependencies", []) if isinstance(data.get("dependencies"), list) else [],
            failure_modes=data.get("failure_modes", []) if isinstance(data.get("failure_modes"), list) else [],
            agent_role=data.get("agent_role", "shared"),
            selector_keywords=data.get("selector_keywords", []) if isinstance(data.get("selector_keywords"), list) else [],
            maturity=data.get("maturity", "experimental"),
            evidence=data.get("evidence", ""),
        )


# ---------- CLI ----------

def main():
    """CLI: validate tree, list nodes, search."""
    import sys

    tree = MethodsTree()

    if len(sys.argv) < 2:
        # Default: print validation report
        report = tree.validate()
        print("=== Method Tree Validation ===")
        print(f"valid: {report['valid']}")
        print(f"errors: {report['errors']}")
        print(f"stats: {report['stats']}")
        return 0 if report["valid"] else 1

    cmd = sys.argv[1]
    if cmd == "list":
        for node in sorted(tree, key=lambda n: (n.level, n.node_id)):
            print(f"  L{node.level} [{node.agent_role:10}] {node.node_id:20} {node.name}")
    elif cmd == "search" and len(sys.argv) >= 3:
        results = tree.search(" ".join(sys.argv[2:]))
        for r in results:
            print(f"  {r.node_id}: {r.purpose}")
    elif cmd == "get" and len(sys.argv) >= 3:
        node = tree.get(sys.argv[2])
        if node:
            import json
            print(json.dumps(node.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(f"  not found: {sys.argv[2]}")
    elif cmd == "children" and len(sys.argv) >= 3:
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        for c in tree.get_children(sys.argv[2], depth=depth):
            print(f"  L{c.level} {c.node_id}: {c.purpose}")
    elif cmd == "path" and len(sys.argv) >= 4:
        path = tree.find_path(sys.argv[2], sys.argv[3])
        if path:
            print(" -> ".join(path))
        else:
            print(f"  no path: {sys.argv[2]} -> {sys.argv[3]}")
    else:
        print(f"  unknown command: {cmd}")
        print(f"  usage: methods_tree.py [list|search <q>|get <id>|children <id> [depth]|path <from> <to>]")
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
