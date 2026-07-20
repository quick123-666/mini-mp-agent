# Release Status (public, coarse)

> **Pattern**: 2-table docs (M-SyncDevPlan-001). Coarse table only.
> Full fine-grained table lives in `docs/DEV_PLAN.md` (local-only,
> `.gitignore`'d). See `methods/recipes/sync_dev_plan.yaml` for the
> sync protocol.

| Version | Date       | Status   | Headline                                       | Commits | Tests |
|---------|------------|----------|------------------------------------------------|--------:|------:|
| v1.3.0  | 2026-07-20 | shipped  | Wiki recall 3-phase + two-table docs            |      6+ | 333/333 (smoke) |
| v1.1.1  | 2026-07-18 | shipped  | Ship patch: .gitignore + slug + real cron      |      6+ | 333/333 |
| v1.1.0  | 2026-07-18 | shipped  | LLM Wiki redesign (1 session = 1 topic)        |      4+ | 310/310 |
| v1.0.1  | 2026-07-17 | shipped  | Phase 1-8: modes, PWR, atomic, wiki, methods   |     20+ | 285/285 |

## Highlights — v1.3.0

- **`scripts/wiki_recall.py`** — 3-phase recall: `keyword_grep` →
  `semantic_match` → `hybrid_rerank`. Embedding-free, cron-safe.
- **`methods/recipes/wiki_recall.yaml`** — full L1 method node
  (3.3 KB, replaces 489-byte stub).
- **Two-table docs** — public `docs/RELEASE_STATUS.md` + local
  `docs/DEV_PLAN.md` + `methods/recipes/sync_dev_plan.yaml`.

## Decision IDs in v1.3.0

- `D-WikiRecall-3Phase-001` — wiki recall 3-phase pipeline
- `D-SyncDevPlan-001` — two-table docs sync protocol

## Test posture

- Stable test count: **333/333 passing** (last full run at v1.1.1).
- v1.3.0 adds `scripts/wiki_recall.py` as smoke-tested (not
  pytest-covered yet — out of scope for this release; tracked for
  v1.4.0 alongside embedding-based recall Phase 4).

## Next (planned, not yet shipped)

- v1.4.0 — embedding-based recall (Phase 4 of `wiki_recall.yaml`) +
  CJK tokenizer improvement + `tests/test_wiki_recall.py` coverage.
- v1.5.0 — multi-wiki federation (per-agent / per-project roots).
