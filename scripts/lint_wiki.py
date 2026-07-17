"""7+1 step wiki linter (Karpathy fork).

Phase 4 ship (2026-07-17 23:30). Phase 7+ added `mode_coverage` (8th step).

Steps:
  1. orphan             - dialogue/entry not referenced anywhere
  2. missing            - (alias of broken_wikilinks)
  3. broken_wikilinks   - [[X]] X has no entry
  4. isolated           - entity has 0 inbound links
  5. contradictions     - (Phase 5 stub: simple text-dup check)
  6. stale_claims       - claim older than 90 days, no update
  7. missing_cross_refs - (Phase 5 stub)
  8. mode_coverage      - (Phase 7+ NEW) methods in tree with 0 wiki entries,
                          or entries with no classification tags
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
CREATED_RE = re.compile(r"created:\s*([\d\-T:.]+)")
DEFAULT_STALE_DAYS = 90
RESERVED_SLUGS = {"index", "log", "contradictions"}


def _all_slugs(root: Path) -> set[str]:
    slugs: set[str] = set()
    for sub in ["dialogue", "entities", "topics"]:
        for p in (root / sub).glob("*.md"):
            slugs.add(p.stem)
    return slugs


def _collect_wikilinks(root: Path) -> dict[str, list[str]]:
    """Walk all .md files, extract [[target]] references. Returns {source: [targets]}."""
    links: dict[str, list[str]] = {}
    for path in root.rglob("*.md"):
        if path.stem in RESERVED_SLUGS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        targets = WIKILINK_RE.findall(text)
        if targets:
            links[path.stem] = targets
    return links


def lint_wiki(root: Path, stale_days: int = DEFAULT_STALE_DAYS,
              methods_tree=None) -> dict[str, list[Any]]:
    """Run 7+1 step lint. Returns {step_name: [issues]}.

    Args:
        root: wiki root path
        stale_days: threshold for stale claims (default 90)
        methods_tree: optional MethodsTree; if provided, runs 8th step
            `mode_coverage` which identifies methods with 0 wiki entries
            and entries with no classification.
    """
    root = Path(root)
    all_slugs = _all_slugs(root)
    wikilinks = _collect_wikilinks(root)

    issues: dict[str, list[Any]] = {
        "orphan": [],
        "missing": [],
        "broken_wikilinks": [],
        "isolated": [],
        "contradictions": [],
        "stale_claims": [],
        "missing_cross_refs": [],
        "mode_coverage": [],
    }

    # 1+3. broken wikilinks
    for source, targets in wikilinks.items():
        for t in targets:
            if t not in all_slugs:
                issues["broken_wikilinks"].append({"source": source, "missing_target": t})
                issues["missing"].append({"source": source, "missing_target": t})

    # 2. orphan (entry not referenced by any other; skip reserved)
    referenced: set[str] = set()
    for targets in wikilinks.values():
        referenced.update(targets)
    for slug in all_slugs:
        if slug in RESERVED_SLUGS:
            continue
        if slug not in referenced:
            issues["orphan"].append(slug)

    # 4. isolated entity (entity with 0 inbound links)
    for p in (root / "entities").glob("*.md"):
        if p.stem not in referenced:
            issues["isolated"].append(p.stem)

    # 5. contradictions (Phase 4 stub: simple text-dup detection)
    seen_lines: dict[str, str] = {}  # normalized → first slug
    for path in root.rglob("*.md"):
        if path.stem in RESERVED_SLUGS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.split("\n"):
            line = line.strip()
            if len(line) < 20:
                continue
            norm = re.sub(r"\s+", " ", line.lower())
            if norm in seen_lines:
                issues["contradictions"].append({
                    "first": seen_lines[norm],
                    "duplicate": path.stem,
                    "line": line[:80],
                })
            else:
                seen_lines[norm] = path.stem

    # 6. stale claims (>90 days old, no recent update)
    cutoff = datetime.now() - timedelta(days=stale_days)
    for path in (root / "entities").glob("*.md"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = CREATED_RE.search(text)
        if m:
            try:
                ts = datetime.fromisoformat(m.group(1))
                if ts < cutoff:
                    issues["stale_claims"].append({"slug": path.stem, "created": m.group(1)})
            except ValueError:
                pass

    # 7. missing cross refs (Phase 4 stub: skip)

    # 8. mode_coverage (Phase 7+): methods tree methods with 0 entries,
    #    and entries with no classification tags.
    if methods_tree is not None:
        from .wiki_store import wiki_mode_coverage
        cov = wiki_mode_coverage(root, methods_tree)
        for m in cov.get("unused_methods", []):
            issues["mode_coverage"].append({
                "kind": "method_unused",
                "method": m,
            })
        for slug in cov.get("untagged_entries", []):
            issues["mode_coverage"].append({
                "kind": "entry_untagged",
                "slug": slug,
            })

    return issues


def lint_summary(issues: dict[str, list[Any]]) -> dict[str, int]:
    """Return count per category."""
    return {k: len(v) for k, v in issues.items()}


if __name__ == "__main__":
    import json
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("wiki")
    if not root.exists():
        print(f"Wiki not found at {root}; run init first")
        sys.exit(1)
    # If user wants method coverage, pass --with-methods
    methods_tree = None
    if len(sys.argv) > 2 and sys.argv[2] == "--with-methods":
        from .methods_tree import MethodsTree
        methods_tree = MethodsTree()
    issues = lint_wiki(root, methods_tree=methods_tree)
    print(json.dumps(lint_summary(issues), indent=2))
    if any(issues.values()):
        print("\nDetails:")
        print(json.dumps(issues, ensure_ascii=False, indent=2))
