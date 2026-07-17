"""Karpathy LLM Wiki fork for mini-mp-agent.

Phase 4 ship (2026-07-17 23:30). Phase 7+: method-tree classification.

File structure:
  wiki/
    index.md              # table of contents
    log.md                # append-only history
    contradictions.md     # flagged inconsistencies
    coverage.md           # NEW Phase 7+: which methods have wiki coverage
    _meta/
      graph.json              # entity relationships
      .frontmatter_cache.json # NEW Phase 7+: slug → frontmatter (O(1) query)
    dialogue/<slug>.md    # one per dialogue entry
    entities/<slug>.md    # entity pages
    topics/<slug>.md      # topic synthesis pages
    by_mode/<mode_id>/    # NEW Phase 7+: generated subdirs (read-only)

Philosophy: "LLM writes, Python handles bookkeeping"

Phase 7+ classification:
  Each entry's front-matter now includes:
    modes: [m_task]              # L0 modes
    l1_recipes: [plan_task]      # L1 recipes used
    roles: [planner, worker]     # roles involved
    failure_categories: [...]   # if entry is a reflection

  New query APIs:
    wiki_by_mode(root, mode_id)
    wiki_by_role(root, role)
    wiki_by_failure_category(root, cat)
    wiki_mode_coverage(root, methods_tree)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .atomic_write import atomic_write


DEFAULT_WIKI_ROOT = Path("wiki")


# ---------- Data structures ----------

@dataclass
class WikiEntry:
    """One entry in the wiki."""
    slug: str
    type: str  # "dialogue" / "entity" / "topic"
    created: str
    modes: List[str] = field(default_factory=list)
    l1_recipes: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    failure_categories: List[str] = field(default_factory=list)
    path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slug": self.slug,
            "type": self.type,
            "created": self.created,
            "modes": self.modes,
            "l1_recipes": self.l1_recipes,
            "roles": self.roles,
            "failure_categories": self.failure_categories,
            "path": self.path,
        }


# ---------- Init ----------

def init_wiki(root: Path = DEFAULT_WIKI_ROOT) -> Path:
    """Create wiki/ structure. Returns root. Idempotent."""
    root = Path(root)
    for sub in ["", "dialogue", "entities", "topics", "_meta", "by_mode"]:
        (root / sub).mkdir(parents=True, exist_ok=True)
    if not (root / "index.md").exists():
        atomic_write(root / "index.md", "# Wiki Index\n\n| slug | type | created | modes |\n|------|------|---------|-------|\n")
    if not (root / "log.md").exists():
        atomic_write(root / "log.md", "# Wiki Log\n\n")
    if not (root / "_meta" / "graph.json").exists():
        atomic_write(root / "_meta" / "graph.json", "{}")
    if not (root / "_meta" / ".frontmatter_cache.json").exists():
        atomic_write(root / "_meta" / ".frontmatter_cache.json", "{}")
    if not (root / "contradictions.md").exists():
        atomic_write(root / "contradictions.md", "# Contradictions\n\n")
    if not (root / "coverage.md").exists():
        atomic_write(root / "coverage.md", _coverage_md_template())
    return root


# ---------- Front-matter helpers ----------

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _format_list_field(values: List[str], field_name: str) -> str:
    """Format a YAML list for front-matter."""
    if not values:
        return ""
    if len(values) == 1:
        return f"{field_name}: [{values[0]}]"
    # Multi-line form
    lines = [f"{field_name}:"]
    for v in values:
        lines.append(f"  - {v}")
    return "\n".join(lines)


def _front_matter(slug: str, type_: str, ts: str, extra: Optional[dict] = None,
                  modes=None, l1_recipes=None, roles=None, failure_categories=None) -> str:
    """Build YAML front-matter with classification fields."""
    parts = [f"slug: {slug}", f"type: {type_}", f"created: {ts}"]
    # Classification fields (Phase 7+)
    if modes:
        parts.append(_format_list_field(modes, "modes"))
    if l1_recipes:
        parts.append(_format_list_field(l1_recipes, "l1_recipes"))
    if roles:
        parts.append(_format_list_field(roles, "roles"))
    if failure_categories:
        parts.append(_format_list_field(failure_categories, "failure_categories"))
    if extra:
        for k, v in extra.items():
            parts.append(f"{k}: {v}")
    return "---\n" + "\n".join(parts) + "\n---\n\n"


def _parse_front_matter(text: str) -> Dict[str, Any]:
    """Parse YAML front-matter from entry text. Returns dict."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = parts[1].strip()
    result: Dict[str, Any] = {}
    list_key: Optional[str] = None
    for line in fm.split("\n"):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if list_key and line.startswith("  - "):
            item = line[4:].strip()
            if list_key not in result:
                result[list_key] = []
            result[list_key].append(item)
            continue
        if ":" in s:
            key, _, val = s.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                # List starts next lines
                list_key = key
                result.setdefault(key, [])
                continue
            list_key = None
            # Inline list
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                if inner:
                    result[key] = [x.strip() for x in inner.split(",")]
                else:
                    result[key] = []
            elif val.lower() in ("true", "false"):
                result[key] = val.lower() == "true"
            else:
                result[key] = val
    return result


def _extract_classification(meta: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extract classification fields from front-matter dict."""
    return {
        "modes": list(meta.get("modes", []) or []),
        "l1_recipes": list(meta.get("l1_recipes", []) or []),
        "roles": list(meta.get("roles", []) or []),
        "failure_categories": list(meta.get("failure_categories", []) or []),
    }


# ---------- Cache maintenance ----------

def _cache_path(root: Path) -> Path:
    return root / "_meta" / ".frontmatter_cache.json"


def _load_cache(root: Path) -> Dict[str, Dict[str, Any]]:
    """Load front-matter cache. Returns {slug: meta-dict}."""
    p = _cache_path(root)
    if not p.exists():
        return {}
    try:
        text = p.read_text(encoding="utf-8")
        if not text.strip():
            return {}
        return json.loads(text)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(root: Path, cache: Dict[str, Dict[str, Any]]) -> None:
    """Save front-matter cache atomically."""
    atomic_write(_cache_path(root), json.dumps(cache, indent=2, ensure_ascii=False))


def _update_cache(root: Path, slug: str, entry_type: str, ts: str,
                  modes=None, l1_recipes=None, roles=None, failure_categories=None,
                  extra: Optional[dict] = None) -> None:
    """Add or update one entry in the cache."""
    cache = _load_cache(root)
    cache[slug] = {
        "type": entry_type,
        "created": ts,
        "modes": modes or [],
        "l1_recipes": l1_recipes or [],
        "roles": roles or [],
        "failure_categories": failure_categories or [],
    }
    if extra:
        cache[slug].update({"extra": extra})
    _save_cache(root, cache)


def _refresh_cache(root: Path) -> Dict[str, Dict[str, Any]]:
    """Rebuild cache from disk (one-time, slow). Returns fresh cache."""
    cache: Dict[str, Dict[str, Any]] = {}
    for sub in ["dialogue", "entities", "topics"]:
        for p in (root / sub).glob("*.md"):
            text = p.read_text(encoding="utf-8", errors="replace")
            meta = _parse_front_matter(text)
            cls = _extract_classification(meta)
            cache[p.stem] = {
                "type": sub,
                "created": str(meta.get("created", "")),
                "modes": cls["modes"],
                "l1_recipes": cls["l1_recipes"],
                "roles": cls["roles"],
                "failure_categories": cls["failure_categories"],
            }
    _save_cache(root, cache)
    return cache


# ---------- Index / log ----------

def _append_index(root: Path, slug: str, type_: str, ts: str, modes=None):
    """Append to index.md table."""
    index_path = root / "index.md"
    modes_str = ", ".join(modes or []) if modes else "-"
    # If line already exists, replace it. Simpler: just append a new row.
    line = f"| {slug} | {type_} | {ts} | {modes_str} |\n"
    try:
        existing = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    except OSError:
        existing = ""
    if line.strip() not in existing:
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(line)


def _append_log(root: Path, msg: str):
    log_path = root / "log.md"
    ts = _now()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"- {ts}: {msg}\n")


# ---------- Write (Phase 7+ extends with classification) ----------

def write_dialogue(
    root: Path,
    slug: str,
    content: str,
    metadata: Optional[dict] = None,
    modes: Optional[List[str]] = None,
    l1_recipes: Optional[List[str]] = None,
    roles: Optional[List[str]] = None,
    failure_categories: Optional[List[str]] = None,
) -> Path:
    """Create a dialogue entry with optional method-tree classification.

    All 4 classification fields are optional. If provided, they propagate to:
    - YAML front-matter (readable)
    - .frontmatter_cache.json (machine-readable O(1) lookups)
    - index.md (table column)
    """
    root = Path(root)
    meta = dict(metadata or {})
    ts = meta.pop("ts", None) or _now()
    path = root / "dialogue" / f"{slug}.md"
    fm = _front_matter(slug, "dialogue", ts, meta, modes, l1_recipes, roles, failure_categories)
    atomic_write(path, fm + content)
    _append_index(root, slug, "dialogue", ts, modes)
    _append_log(root, f"dialogue/{slug} created at {ts} (modes={modes or []})")
    _update_cache(root, slug, "dialogue", ts, modes, l1_recipes, roles, failure_categories, meta)
    return path


def write_entity(
    root: Path,
    slug: str,
    content: str,
    metadata: Optional[dict] = None,
    modes: Optional[List[str]] = None,
    l1_recipes: Optional[List[str]] = None,
    roles: Optional[List[str]] = None,
    failure_categories: Optional[List[str]] = None,
) -> Path:
    """Create an entity page with optional classification."""
    root = Path(root)
    meta = dict(metadata or {})
    ts = meta.pop("ts", None) or _now()
    path = root / "entities" / f"{slug}.md"
    fm = _front_matter(slug, "entity", ts, meta, modes, l1_recipes, roles, failure_categories)
    atomic_write(path, fm + content)
    _append_index(root, slug, "entity", ts, modes)
    _append_log(root, f"entity/{slug} created at {ts} (modes={modes or []})")
    _update_cache(root, slug, "entity", ts, modes, l1_recipes, roles, failure_categories, meta)
    return path


def write_topic(
    root: Path,
    slug: str,
    content: str,
    metadata: Optional[dict] = None,
    modes: Optional[List[str]] = None,
    l1_recipes: Optional[List[str]] = None,
    roles: Optional[List[str]] = None,
    failure_categories: Optional[List[str]] = None,
) -> Path:
    """Create a topic synthesis page with optional classification."""
    root = Path(root)
    meta = dict(metadata or {})
    ts = meta.pop("ts", None) or _now()
    path = root / "topics" / f"{slug}.md"
    fm = _front_matter(slug, "topic", ts, meta, modes, l1_recipes, roles, failure_categories)
    atomic_write(path, fm + content)
    _append_index(root, slug, "topic", ts, modes)
    _append_log(root, f"topic/{slug} created at {ts} (modes={modes or []})")
    _update_cache(root, slug, "topic", ts, modes, l1_recipes, roles, failure_categories, meta)
    return path


# ---------- Search (existing) ----------

def search(
    root: Path,
    query: str,
    type_filter: Optional[str] = None,
) -> list[dict]:
    """Search wiki for query. Returns [{slug, type, snippet, path}]."""
    root = Path(root)
    results: list[dict] = []
    paths: list[Path] = []
    if type_filter == "dialogue":
        paths = list((root / "dialogue").glob("*.md"))
    elif type_filter == "entity":
        paths = list((root / "entities").glob("*.md"))
    elif type_filter == "topic":
        paths = list((root / "topics").glob("*.md"))
    else:
        for sub in ["dialogue", "entities", "topics"]:
            paths.extend((root / sub).glob("*.md"))

    q_lower = query.lower()
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if q_lower in text.lower():
            idx = text.lower().find(q_lower)
            start = max(0, idx - 50)
            end = min(len(text), idx + 100)
            snippet = text[start:end].replace("\n", " ")
            results.append({
                "slug": p.stem,
                "type": p.parent.name,
                "snippet": snippet,
                "path": str(p),
            })
    return results


def list_all(root: Path) -> list[dict]:
    """List all entries with metadata."""
    root = Path(root)
    items: list[dict] = []
    for sub in ["dialogue", "entities", "topics"]:
        for p in (root / sub).glob("*.md"):
            text = p.read_text(encoding="utf-8", errors="replace")
            ts = ""
            for line in text.split("\n")[:10]:
                if line.startswith("created:"):
                    ts = line.split(":", 1)[1].strip()
                    break
            items.append({"slug": p.stem, "type": sub, "created": ts, "path": str(p)})
    return items


# ---------- Phase 7+: classification queries ----------

def _entry_from_cache(root: Path, slug: str, cache_data: Dict[str, Any]) -> WikiEntry:
    """Build a WikiEntry from cache data."""
    return WikiEntry(
        slug=slug,
        type=cache_data.get("type", "unknown"),
        created=cache_data.get("created", ""),
        modes=list(cache_data.get("modes", []) or []),
        l1_recipes=list(cache_data.get("l1_recipes", []) or []),
        roles=list(cache_data.get("roles", []) or []),
        failure_categories=list(cache_data.get("failure_categories", []) or []),
        path=str(root / cache_data.get("type", "dialogue") / f"{slug}.md"),
    )


def wiki_by_mode(root: Path, mode_id: str) -> List[WikiEntry]:
    """Return all entries tagged with a given L0 mode (e.g. 'm_sprint')."""
    cache = _load_cache(root)
    return [
        _entry_from_cache(root, slug, data)
        for slug, data in cache.items()
        if mode_id in (data.get("modes") or [])
    ]


def wiki_by_role(root: Path, role: str) -> List[WikiEntry]:
    """Return all entries involving a given role (planner/worker/reviewer/reflector)."""
    cache = _load_cache(root)
    return [
        _entry_from_cache(root, slug, data)
        for slug, data in cache.items()
        if role in (data.get("roles") or [])
    ]


def wiki_by_failure_category(root: Path, category: str) -> List[WikiEntry]:
    """Return all entries tagged with a given failure category."""
    cache = _load_cache(root)
    return [
        _entry_from_cache(root, slug, data)
        for slug, data in cache.items()
        if category in (data.get("failure_categories") or [])
    ]


def wiki_by_l1_recipe(root: Path, recipe_id: str) -> List[WikiEntry]:
    """Return all entries produced by a given L1 recipe."""
    cache = _load_cache(root)
    return [
        _entry_from_cache(root, slug, data)
        for slug, data in cache.items()
        if recipe_id in (data.get("l1_recipes") or [])
    ]


def wiki_mode_coverage(root: Path, methods_tree=None) -> Dict[str, Any]:
    """Coverage report: for each method, how many wiki entries reference it.

    Args:
        root: wiki root path
        methods_tree: optional MethodsTree instance; if None, only methods that
            appear in cache are reported (no usage gaps).

    Returns:
        {
            'total_entries': int,
            'by_method': {method_id: count},
            'by_role': {role: count},
            'by_mode': {mode_id: count},
            'untagged_entries': [slug, ...],   # entries with no classification
            'unused_methods': [method_id, ...]  # methods with 0 entries (if methods_tree provided)
        }
    """
    cache = _load_cache(root)
    by_method: Dict[str, int] = {}
    by_role: Dict[str, int] = {}
    by_mode: Dict[str, int] = {}
    untagged: List[str] = []

    for slug, data in cache.items():
        modes = data.get("modes") or []
        recipes = data.get("l1_recipes") or []
        roles = data.get("roles") or []

        # count mode + recipe occurrences (called "methods")
        for m in modes + recipes:
            by_method[m] = by_method.get(m, 0) + 1
        for r in roles:
            by_role[r] = by_role.get(r, 0) + 1
        for mode in modes:
            by_mode[mode] = by_mode.get(mode, 0) + 1

        if not modes and not recipes and not roles:
            untagged.append(slug)

    result = {
        "total_entries": len(cache),
        "by_method": by_method,
        "by_role": by_role,
        "by_mode": by_mode,
        "untagged_entries": untagged,
        "unused_methods": [],
    }

    # If methods_tree provided, identify methods with 0 references
    if methods_tree is not None:
        all_method_ids = {n.node_id for n in methods_tree}
        used = set(by_method.keys())
        result["unused_methods"] = sorted(all_method_ids - used)

    return result


def render_coverage_md(coverage: Dict[str, Any]) -> str:
    """Render coverage dict as Markdown (for wiki/coverage.md)."""
    lines = ["# Wiki Method Coverage\n"]
    lines.append(f"_Total entries: **{coverage['total_entries']}**_\n")
    lines.append("\n## By method (mode + L1 recipe)\n")
    lines.append("| method | count |\n|--------|------:|\n")
    if not coverage["by_method"]:
        lines.append("| (none) | 0 |\n")
    for m, c in sorted(coverage["by_method"].items(), key=lambda x: -x[1]):
        lines.append(f"| {m} | {c} |\n")
    lines.append("\n## By role\n")
    lines.append("| role | count |\n|------|------:|\n")
    if not coverage["by_role"]:
        lines.append("| (none) | 0 |\n")
    for r, c in sorted(coverage["by_role"].items(), key=lambda x: -x[1]):
        lines.append(f"| {r} | {c} |\n")
    lines.append("\n## By mode (L0)\n")
    lines.append("| mode | count |\n|------|------:|\n")
    if not coverage["by_mode"]:
        lines.append("| (none) | 0 |\n")
    for m, c in sorted(coverage["by_mode"].items(), key=lambda x: -x[1]):
        lines.append(f"| {m} | {c} |\n")

    if coverage.get("unused_methods"):
        lines.append("\n## ⚠ Unused methods (0 wiki coverage)\n")
        for m in coverage["unused_methods"]:
            lines.append(f"- {m}\n")

    if coverage.get("untagged_entries"):
        lines.append("\n## ⚠ Untagged entries (no classification)\n")
        for s in coverage["untagged_entries"]:
            lines.append(f"- {s}\n")

    return "".join(lines)


def generate_coverage_report(root: Path, methods_tree=None) -> Path:
    """Compute coverage + write to wiki/coverage.md. Returns coverage.md path."""
    coverage = wiki_mode_coverage(root, methods_tree)
    md = render_coverage_md(coverage)
    p = root / "coverage.md"
    atomic_write(p, md)
    _append_log(root, f"coverage report generated")
    return p


def _coverage_md_template() -> str:
    return (
        "# Wiki Method Coverage\n\n"
        "_Auto-generated by `wiki_mode_coverage()`._\n\n"
        "Run `python -m scripts.wiki_store coverage` to refresh.\n"
    )


# ---------- CLI ----------

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.wiki_store <command> [args]")
        print("Commands:")
        print("  init [root]                - initialize wiki structure")
        print("  refresh-cache [root]       - rebuild frontmatter cache from disk")
        print("  coverage [root]            - generate coverage.md report")
        print("  by-mode <id> [root]        - list entries with that mode")
        print("  by-role <role> [root]      - list entries with that role")
        print("  by-recipe <id> [root]      - list entries with that L1 recipe")
        sys.exit(1)

    cmd = sys.argv[1]
    root = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_WIKI_ROOT

    if cmd == "init":
        init_wiki(root)
        print(f"Wiki initialized at {root}")
    elif cmd == "refresh-cache":
        cache = _refresh_cache(root)
        print(f"Refreshed cache: {len(cache)} entries")
    elif cmd == "coverage":
        from .methods_tree import MethodsTree
        tree = MethodsTree()
        p = generate_coverage_report(root, tree)
        print(f"Coverage report: {p}")
    elif cmd == "by-mode" and len(sys.argv) >= 3:
        entries = wiki_by_mode(root, sys.argv[2])
        for e in entries:
            print(f"  [{e.type}] {e.slug} (modes={e.modes}, recipes={e.l1_recipes})")
    elif cmd == "by-role" and len(sys.argv) >= 3:
        entries = wiki_by_role(root, sys.argv[2])
        for e in entries:
            print(f"  [{e.type}] {e.slug} (roles={e.roles})")
    elif cmd == "by-recipe" and len(sys.argv) >= 3:
        entries = wiki_by_l1_recipe(root, sys.argv[2])
        for e in entries:
            print(f"  [{e.type}] {e.slug} (recipes={e.l1_recipes})")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
