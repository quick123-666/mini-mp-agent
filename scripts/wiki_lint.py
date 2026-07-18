"""LLM Wiki health check (cron-friendly).

Replaces examples/_lint_wiki_summary.py.

Three checks (vs the existing scripts/lint_wiki.py 8-step pass which validates
wiki structure, this one focuses on *content* health):

1. orphans       — topic pages that are never linked to from any other page
                    or index (would be lost in plain LCM grep)
2. stale         — topic pages with created older than --stale-days and no
                    incoming links
3. contradictions — for any (D-NNN / M-XXX) decision code appearing in more
                    than one topic with different first-line text, log both
                    versions for human review

Output: JSON report on stdout, plus an entry appended to <wiki_root>/_lint.log.

Designed to be cheap (one read per topic, no LLM) and safe to call hourly.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def _read_topics(wiki_root: Path) -> List[Dict[str, Any]]:
    """Return [{path, rel, slug, created, body, links_out, codes}]"""
    topics_dir = wiki_root / "topics"
    if not topics_dir.exists():
        return []
    out = []
    for md in sorted(topics_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        # parse front-matter
        meta: Dict[str, Any] = {"path": md, "rel": md.relative_to(wiki_root).as_posix()}
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end > 0:
                block = text[3:end]
                for line in block.splitlines():
                    line = line.strip()
                    if not line or ":" not in line:
                        continue
                    k, _, v = line.partition(":")
                    v = v.strip()
                    if v.startswith("[") and v.endswith("]"):
                        meta[k.strip()] = [
                            x.strip().strip('"').strip("'")
                            for x in v[1:-1].split(",")
                            if x.strip()
                        ]
                    else:
                        meta[k.strip()] = v.strip('"').strip("'")
                meta["body"] = text[end + 4 :].strip()
            else:
                meta["body"] = text
        else:
            meta["body"] = text
        # extract outgoing [[wikilinks]] and decision/method codes
        meta["links_out"] = set(re.findall(r"\[\[([^\]]+)\]\]", meta["body"]))
        meta["codes"] = set(re.findall(r"\bD-\d{3,}\b|\bM-[A-Za-z]+-\d{3,}\b", meta["body"]))
        out.append(meta)
    return out


def _collect_inbound_links(wiki_root: Path) -> Dict[str, Set[str]]:
    """For each topic slug, which other pages link to it?
    Also include index/timeline/by-project as 'meta' inlinks."""
    inbound: Dict[str, Set[str]] = {}
    extras = []
    for sub in ("index.md", "timeline.md"):
        p = wiki_root / sub
        if p.exists():
            extras.append(p)
    bp = wiki_root / "by-project"
    if bp.exists():
        extras.extend(bp.glob("*.md"))
    for p in extras:
        text = p.read_text(encoding="utf-8", errors="replace")
        # collect wikilink targets AND md-relatives
        for m in re.finditer(r"\[\[([^\]]+)\]\]", text):
            inbound.setdefault(m.group(1), set()).add(p.name)
        for m in re.finditer(r"\(([^)]+\.md)\)", text):
            tgt = m.group(1).split("/")[-1].removesuffix(".md")
            inbound.setdefault(tgt, set()).add(p.name)
    return inbound


def lint_llmwiki(
    wiki_root: Path,
    stale_days: int = 90,
) -> Dict[str, Any]:
    """Run all three checks; return report dict."""
    topics = _read_topics(wiki_root)
    inbound = _collect_inbound_links(wiki_root)

    orphans: List[str] = []
    stale: List[Dict[str, Any]] = []
    code_index: Dict[str, List[Tuple[str, str]]] = {}  # code -> [(slug, first_line)]
    now = datetime.now(timezone.utc)

    for t in topics:
        slug = t.get("slug") or t["path"].stem
        in_meta = inbound.get(slug, set())
        in_other_topics: Set[str] = set()
        for other in topics:
            if other["path"] == t["path"]:
                continue
            if slug in other.get("links_out", set()):
                in_other_topics.add(other.get("slug", other["path"].stem))
        in_total = in_meta | in_other_topics
        if not in_total:
            orphans.append(slug)
        # stale check
        created_str = t.get("created", "")
        try:
            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            age_days = (now - created_dt).days
        except Exception:
            age_days = 0
        if age_days > stale_days and not in_total:
            stale.append({"slug": slug, "age_days": age_days, "created": created_str})
        # decision code index
        first_line = (t.get("body") or "").splitlines()[0][:120] if t.get("body") else ""
        for code in t.get("codes", set()):
            code_index.setdefault(code, []).append((slug, first_line))

    contradictions: List[Dict[str, Any]] = []
    for code, refs in code_index.items():
        if len(refs) < 2:
            continue
        # contradiction heuristic: same code, different first-line text
        first_lines = {line for _, line in refs}
        if len(first_lines) > 1:
            contradictions.append({
                "code": code,
                "occurrences": [{"slug": s, "first_line": l} for s, l in refs],
            })

    report = {
        "checked_at": _now_iso(),
        "wiki_root": str(wiki_root),
        "topics_total": len(topics),
        "orphans": orphans,
        "stale": stale,
        "contradictions": contradictions,
        "summary": {
            "orphan_count": len(orphans),
            "stale_count": len(stale),
            "contradiction_count": len(contradictions),
        },
    }
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="LLM Wiki health check (orphans/stale/contradictions)")
    p.add_argument("--wiki-root", type=Path, default=ROOT / "llmwiki")
    p.add_argument("--stale-days", type=int, default=90)
    p.add_argument("--json", action="store_true", help="JSON only on stdout")
    args = p.parse_args()

    report = lint_llmwiki(args.wiki_root, stale_days=args.stale_days)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        s = report["summary"]
        print(f"=== LLM WIKI LINT ({args.wiki_root}) ===")
        print(f"  topics   : {report['topics_total']}")
        print(f"  orphans  : {s['orphan_count']}")
        print(f"  stale    : {s['stale_count']}")
        print(f"  contradict: {s['contradiction_count']}")
        if report["orphans"]:
            print("\n  Orphan topics (not linked from anywhere):")
            for o in report["orphans"][:20]:
                print(f"    - {o}")
        if report["stale"]:
            print("\n  Stale topics (older than {args.stale_days} days, no inbound):")
            for o in report["stale"][:20]:
                print(f"    - {o['slug']} ({o['age_days']}d)")
        if report["contradictions"]:
            print("\n  Possible contradictions:")
            for c in report["contradictions"][:10]:
                print(f"    - {c['code']}: {len(c['occurrences'])} different versions")
                for occ in c["occurrences"][:3]:
                    print(f"        * {occ['slug']}: {occ['first_line'][:80]}")

    # append to lint log
    log_path = args.wiki_root / "_lint.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": report["checked_at"], **report["summary"]}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
