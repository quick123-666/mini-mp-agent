"""Phase 11 — wiki_recall 3-phase recall for mini-mp-agent.

3-phase recall pipeline (Phase 1-3 of wiki_recall):

  Phase 1 — keyword_grep
      Tokenize the query, FTS5-style match against llmwiki/index.md +
      llmwiki/timeline.md + llmwiki/by-project/*.md. Returns initial
      candidate topic ids sorted by recency.

  Phase 2 — semantic_match
      Cheap synonym expansion (a small in-file synonym table) +
      prefix matching on each query token. Re-ranks Phase 1 hits by
      (hit_count, mtime).

  Phase 3 — hybrid_rerank
      Final rerank: combines Phase 1 + Phase 2 scores plus a tiny
      project-affinity bonus (matching by-project file). Returns
      top-k topic ids with the absolute path to the topic file.

This is intentionally lightweight (no embeddings, no network) so it
runs in a cron slot under a few hundred ms. Future phases (Phase 4+)
may add real embedding-based recall behind a feature flag.

CLI:
    python scripts/wiki_recall.py "query string" --top-k 5
    python scripts/wiki_recall.py "query string" --json
    python scripts/wiki_recall.py "query string" --root /path/to/llmwiki

Env:
    MINI_MP_LLMWIKI_ROOT   override wiki root (default: <repo>/llmwiki)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ------------------------------------------------------------------ paths

ROOT = Path(__file__).resolve().parent.parent  # repo root (scripts/..)
WIKI_ROOT = Path(os.environ.get(
    "MINI_MP_LLMWIKI_ROOT",
    str(ROOT / "llmwiki"),
))

# ------------------------------------------------------------------ models


@dataclass
class TopicHit:
    topic_id: str           # e.g. "2026-07-20-laap-aris-checkpoint"
    title: str
    path: str               # absolute path to .md
    mtime: float            # unix seconds
    phase1_score: float = 0.0
    phase2_score: float = 0.0
    final_score: float = 0.0
    project: Optional[str] = None
    matched_terms: List[str] = field(default_factory=list)


# ------------------------------------------------------------------ small synonym table

# Project / domain terms we know about. Add as the wiki grows.
SYNONYMS: Dict[str, List[str]] = {
    "laap": ["aris", "ari_self", "ari-brain", "aral", "agent-templates"],
    "aris": ["laap", "ari_self", "ari-brain"],
    "pwr": ["plan", "work", "review", "reflect", "loop"],
    "wiki": ["llmwiki", "knowledge-base", "kb", "rec"],
    "recall": ["grep", "search", "find", "lookup", "query"],
    "method": ["recipe", "m", "tree", "node"],
    "ship": ["release", "deploy", "publish"],
    "cron": ["schedule", "job", "timer", "heartbeat"],
    "encoding": ["gbk", "utf-8", "utf8", "bom", "mojibake"],
    "self-model": ["self_model", "selfmodel", "identity", "ego"],
}


# ------------------------------------------------------------------ helpers

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-一-鿿]+")


def _tokenize(s: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(s) if t]


def _expand_tokens(tokens: List[str]) -> List[str]:
    """Phase 2 input: original tokens + their synonyms, deduped."""
    out: List[str] = []
    seen = set()
    for tok in tokens:
        for t in [tok] + SYNONYMS.get(tok, []):
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


# ------------------------------------------------------------------ Phase 1


def phase1_keyword_grep(
    query_tokens: List[str], wiki_root: Path
) -> Dict[str, TopicHit]:
    """Scan index.md, timeline.md, and by-project/*.md for first-pass hits.

    Returns: dict keyed by topic_id → TopicHit (only phase1_score populated).
    """
    hits: Dict[str, TopicHit] = {}

    candidate_files: List[Path] = []
    for name in ("index.md", "timeline.md"):
        p = wiki_root / name
        if p.exists():
            candidate_files.append(p)
    by_proj = wiki_root / "by-project"
    if by_proj.is_dir():
        candidate_files.extend(sorted(by_proj.glob("*.md")))

    # Also include topic files under topics/ and by-project/
    for sub in ("topics", "by-project"):
        d = wiki_root / sub
        if d.is_dir():
            candidate_files.extend(sorted(d.glob("*.md")))

    for path in candidate_files:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        text = _read_text(path).lower()
        if not text:
            continue

        # Find topic ids mentioned in this file.
        topic_ids = set(re.findall(
            r"\b\d{4}-\d{2}-\d{2}-[a-z0-9_\-]+", text, flags=re.IGNORECASE
        ))
        # If this file *is* a topic, its own id is its stem.
        if path.stem not in topic_ids and re.match(
            r"\d{4}-\d{2}-\d{2}-", path.stem
        ):
            topic_ids.add(path.stem)

        for topic_id in topic_ids:
            matched = [t for t in query_tokens if t in text]
            if not matched:
                continue
            score = float(len(matched)) / max(1, len(query_tokens))
            existing = hits.get(topic_id)
            if existing is None or score > existing.phase1_score:
                # Try to derive a title from the topic file (first non-empty,
                # non-heading line, or fallback to stem).
                topic_path = _find_topic_file(wiki_root, topic_id)
                title = topic_id
                if topic_path is not None:
                    for line in _read_text(topic_path).splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            title = line[:120]
                            break
                hits[topic_id] = TopicHit(
                    topic_id=topic_id,
                    title=title,
                    path=str(topic_path) if topic_path else str(path),
                    mtime=mtime,
                    phase1_score=score,
                    matched_terms=matched,
                )
    return hits


def _find_topic_file(wiki_root: Path, topic_id: str) -> Optional[Path]:
    for sub in ("topics", "by-project"):
        p = wiki_root / sub / f"{topic_id}.md"
        if p.exists():
            return p
    return None


# ------------------------------------------------------------------ Phase 2


def phase2_semantic_match(
    query_tokens: List[str], hits: Dict[str, TopicHit]
) -> Dict[str, TopicHit]:
    """Re-score Phase 1 hits using expanded token set (synonyms)."""
    expanded = _expand_tokens(query_tokens)
    for hit in hits.values():
        path = Path(hit.path)
        text = _read_text(path).lower()
        if not text:
            hit.phase2_score = 0.0
            continue
        matched_expanded = [t for t in expanded if t in text]
        # Synonym matches are worth less than direct matches.
        direct = set(matched_expanded) & set(query_tokens)
        synonym_only = [t for t in matched_expanded if t not in direct]
        hit.phase2_score = (
            float(len(direct)) * 1.0 + float(len(synonym_only)) * 0.4
        )
        hit.matched_terms = sorted(set(hit.matched_terms + matched_expanded))
    return hits


# ------------------------------------------------------------------ Phase 3


def phase3_hybrid_rerank(
    query_tokens: List[str], hits: Dict[str, TopicHit], top_k: int
) -> List[TopicHit]:
    """Combine phase1 + phase2 scores with a project-affinity bonus."""
    # Project affinity: a topic living in by-project/<project>.md gets +0.5
    # if any of its path tokens is a known project mentioned in query.
    by_proj = WIKI_ROOT / "by-project"
    project_mentions = set(query_tokens)

    for hit in hits.values():
        project_bonus = 0.0
        for proj_path in by_proj.glob("*.md") if by_proj.is_dir() else []:
            proj_name = proj_path.stem.lower()
            if proj_name in project_mentions and proj_name in hit.path.lower():
                project_bonus = 0.5
                hit.project = proj_name
                break

        hit.final_score = (
            hit.phase1_score * 1.0
            + hit.phase2_score * 0.7
            + project_bonus
        )

    ranked = sorted(
        hits.values(), key=lambda h: (h.final_score, h.mtime), reverse=True
    )
    return ranked[:top_k]


# ------------------------------------------------------------------ entrypoint


def recall(
    query: str, top_k: int = 5, wiki_root: Optional[Path] = None
) -> List[TopicHit]:
    root = Path(wiki_root) if wiki_root else WIKI_ROOT
    tokens = _tokenize(query)
    if not tokens:
        return []

    p1 = phase1_keyword_grep(tokens, root)
    if not p1:
        return []
    p2 = phase2_semantic_match(tokens, p1)
    return phase3_hybrid_rerank(tokens, p2, top_k)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="wiki_recall 3-phase recall")
    ap.add_argument("query", help="natural-language query")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--root", type=Path, default=None, help="wiki root override")
    ap.add_argument("--json", action="store_true", help="emit JSON output")
    args = ap.parse_args(argv)

    hits = recall(args.query, top_k=args.top_k, wiki_root=args.root)

    if args.json:
        print(json.dumps(
            [asdict(h) for h in hits], ensure_ascii=False, indent=2
        ))
        return 0

    if not hits:
        print(f"[wiki_recall] no hits for: {args.query!r}", file=sys.stderr)
        return 1

    for i, h in enumerate(hits, 1):
        print(f"{i}. {h.topic_id}  score={h.final_score:.2f}")
        print(f"   title : {h.title}")
        if h.project:
            print(f"   proj  : {h.project}")
        print(f"   path  : {h.path}")
        print(f"   match : {', '.join(h.matched_terms)}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
