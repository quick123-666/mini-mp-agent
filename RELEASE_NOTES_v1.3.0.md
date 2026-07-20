# Release Notes — v1.3.0 (2026-07-20)

> **v1.3.0 — Wiki Recall + Two-Table Docs** (2026-07-20)

A "**recall-grade**" release. After v1.1.1's infrastructure patch, v1.3.0 lands
the missing piece of the Karpathy LLM wiki: a real **3-phase recall pipeline**
that can be used by `Worker` and `Reviewer` to pull prior project context
into a fresh session. Also adds the project's **two-table documentation
pattern** (`docs/DEV_PLAN.md` local + `docs/RELEASE_STATUS.md` public).

## Why v1.3.0 (and not v1.2.0)

`v1.2.0` was planned as `wiki_recall 3-phase` but never actually shipped —
the method node `methods/recipes/wiki_recall.yaml` existed (489-byte stub)
but the implementation `scripts/wiki_recall.py` did not. v1.3.0 closes that
gap and also adds a second long-deferred piece: the **two-table docs
pattern** from `M-SyncDevPlan-001` (local fine-grained + public coarse).

> The version jump (1.1.1 → 1.3.0) reflects that **wiki_recall is the
> primary feature surface** and skipping 1.2.0 keeps the public release
> numbering aligned with what users actually consume (not the Gantt chart).

## What's in v1.3.0

### Added — Wiki Recall 3-Phase Pipeline

- **`scripts/wiki_recall.py`** (10 KB) — embedding-free 3-phase recall:
  - **Phase 1 `keyword_grep`** — tokenize query, scan `llmwiki/index.md` +
    `timeline.md` + `by-project/*.md` + `topics/*.md`. Returns first-pass
    candidates scored by `matched_tokens / query_tokens`.
  - **Phase 2 `semantic_match`** — small in-file synonym table
    (`SYNONYMS` dict: laap↔aris, pwr↔plan/work/review/reflect,
    self-model↔self_model↔identity↔ego, …) re-ranks Phase 1 hits.
    Direct match weight 1.0, synonym-only 0.4.
  - **Phase 3 `hybrid_rerank`** — `final = phase1·1.0 + phase2·0.7 +
    project_affinity·0.5`. Sort by `(final desc, mtime desc)`, take
    top-k. Returns `TopicHit` dataclass with full provenance.
  - **CLI** — `python scripts/wiki_recall.py "query" --top-k 5 --json`
  - **Smoke-tested live** — query `laap aris self-model` returns
    `2026-07-15-laap-aris` as top hit with score 3.75, 7 matched terms.
- **`methods/recipes/wiki_recall.yaml`** (3.3 KB) — full L1 method node
  with `inputs / outputs / cli / failure_modes / success_criteria / lint`.
  Replaces the 489-byte stub from `D-BuildLLMWiki-001`.
  - `decision_id: D-WikiRecall-3Phase-001`
  - `introduced_in: v1.3.0`

### Added — Two-Table Documentation Pattern

- **`docs/RELEASE_STATUS.md`** — public coarse table (commit + push).
  6 columns: version, date, status, headline, commit count, test count.
- **`docs/DEV_PLAN.md`** — local fine-grained table (`.gitignore`'d).
  Same columns + sub-feature status + blocker + ETA. ~3× the rows
  of the public table.
- **`methods/recipes/sync_dev_plan.yaml`** — L1 method node implementing
  `M-SyncDevPlan-001` (6-step: write fine → write coarse → gitignore
  → commit coarse+other → push). Decision ID `D-SyncDevPlan-001`.

### Changed

- `VERSION.json` bumped to `1.3.0`; added `wiki_recall` + `two_table_pattern`
  component sections; added `phase_11` to the phase history.
- `README.md` badge: `v1.1.1` → `v1.3.0`, intro paragraph updated to
  mention wiki recall.

## Out of scope (deferred)

- **Real embedding-based recall** (Phase 4 of `wiki_recall.yaml`) —
  needs vector store + a model. Tracked for v1.4.0.
- **CJK tokenizer improvement** — current regex `[一-鿿]` is naive;
  no Jieba/character n-grams yet. Tracked for v1.4.0.
- **v1.2.0 standalone release notes** — never written, intentionally
  skipped. CHANGELOG just shows the jump.

## Verification

Smoke-test commands (must pass before tagging):

```bash
# Phase 1+2+3 recall on live wiki
python scripts/wiki_recall.py "laap aris self-model" --top-k 5
# expected: top hit = 2026-07-15-laap-aris

# JSON mode
python scripts/wiki_recall.py "pwr loop reflect" --json
# expected: ≥ 1 hit with final_score > 0.5

# Empty index graceful failure
python scripts/wiki_recall.py "" 2>&1
# expected: usage error, exit 2

# Method lint (no schema violations)
python scripts/lint_wiki.py --check-methods
# expected: no errors
```

## Upgrade notes

No breaking changes. All v1.1.x consumers continue to work. New consumers
can `from wiki_recall import recall` to use the 3-phase pipeline
directly.
