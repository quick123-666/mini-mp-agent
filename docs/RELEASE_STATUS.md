# Release Status

Two-table docs (M-SyncDevPlan-001): public coarse table here
(committed); full fine-grained dev plan at `docs/DEV_PLAN.md`
(local-only, `.gitignore`'d).

| Version | Date       | Status  | Headline                                  |
|---------|------------|---------|-------------------------------------------|
| v1.3.1  | 2026-07-20 | shipped | CI fix: tree-level registration + parser     |
| v1.3.0  | 2026-07-20 | shipped | Wiki recall 3-phase + two-table docs      |
| v1.1.1  | 2026-07-18 | shipped | Ship patch: .gitignore + slug + cron      |
| v1.1.0  | 2026-07-18 | shipped | LLM Wiki redesign (1 session = 1 topic)   |
| v1.0.1  | 2026-07-17 | shipped | Phase 1-8: modes, PWR, atomic, wiki       |

## v1.3.1

- Tree-level fix: register `wiki_recall`/`sync_dev_plan` in `_index.json` + level parser hardening + test expectations.

## v1.3.0

- `scripts/wiki_recall.py` — 3-phase recall (keyword_grep →
  semantic_match → hybrid_rerank), embedding-free.
- `methods/recipes/wiki_recall.yaml` — full L1 method node.
- Two-table docs: this file (public) + `docs/DEV_PLAN.md` (local).

Next: v1.4.0 — embedding-based recall + CJK tokenizer.
