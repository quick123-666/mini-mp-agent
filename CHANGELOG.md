# Changelog

## [1.1.1] - 2026-07-18

Post-release ship patch for v1.1.0. Closes 3 ship-completion gaps per `D-ShipCompletionDefinition-001`.

### Fixed

- **`.gitignore` gaps from v1.1.0 ship** — added `llmwiki/` and `*.lock` patterns; removed 17 runtime artifacts that were accidentally committed (7 `.lock` files + 10 wiki data files). Commit `e22308f`.
- **Cross-platform project slug bug** — `wiki_ingest._rebuild_by_project()` wrote `by-project/(uncategorized).md` which displayed oddly in git listings and would fail on Windows-reserved-character filesystems. Added `_sanitize_project_slug()` that normalizes `<>:"/\|?*()[]` and whitespace to dashes, with `uncategorized` fallback. Commit `ae00553`.
- **Phantom cron from v1.1.0 ship** — MEMORY noted an "OpenClaw cron (ID 3dfde4ad)" that was never actually installed (`~/.openclaw/cron/jobs.json.migrated.3` was empty). Now registered real cron job `4bfd77ef-5728-4c0e-bc57-0f3f6f2712bd` (every 3h, isolated agentTurn, runs `scripts/cron_llmwiki.sh`). Manual force-run succeeded (70s, lastRunStatus: ok).

### Added

- `tests/test_by_project_slug.py` — 23 unit tests covering edge cases (lowercase, trim, path separators, Windows-illegal chars, parens, square brackets, whitespace, empty fallback, realistic project names). 310 → **333 tests, all PASS**.
- `RELEASE_NOTES_v1.1.1.md` — patch release notes (this section expanded).
- OpenClaw cron job `4bfd77ef` (3h interval, hour==23 cron-full + lint, otherwise incremental + lint).

### Lessons (cross-ref `memory/2026-07-18.md` § 19:34)

- `M-GitignoreAtomicWrite-001` [imp=0.7] — atomic_write tools must `.gitignore` their `.lock` files.
- `M-SlugSanitize-001` [imp=0.6] — cross-platform filesystem-safe slug generation is required, not just path separator handling.
- `D-CronRegisterVerify-001` [imp=0.8] — "I wrote it in MEMORY" ≠ "I installed it". Cron registration needs verification (check `jobs.json` non-empty).

## [1.1.0] - 2026-07-18

LLM Wiki redesign: 1 session = 1 topic (67× fewer files). Switches the wiki from a 67-files-per-session scatter pattern to a single topic page per session, with entity/dialogue info compressed into front-matter tags.

### Added

- `scripts/wiki_ingest.py` — 4-way ingest pipeline (`cron-full`, `mem`, `session`, `auto`) with atomic state + auto index rebuild.
- `scripts/wiki_lint.py` — 8th lint step (mode coverage) + staleness + contradictions checks.
- `scripts/cron_llmwiki.sh` — wrapper script: `hour==23` triggers `cron-full`; other hours do incremental + lint.
- `examples/wiki_from_session.py` — backward-compat thin wrapper (3-line shim).
- `examples/_lint_wiki_summary.py` — backward-compat thin wrapper.
- `docs/llmwiki.md` — full design doc.
- `persist_to_wiki_from_pwr` derives `topic_title_hint` from session's first user message (not LLM meta-prompt).
- `_is_heartbeat_session()` filter — 12-keyword pattern (openclaw heartbeat / cron-poll / no action needed etc.) so OpenClaw heartbeat sessions don't pollute the wiki.
- `_real_llm` Anthropic-compatible endpoint auto-prefixes `/anthropic` (MiniMax M3 uses non-standard base URL).

### Changed

- `persist_to_wiki` now writes **only topic files** (1 per session). Entity tags compress into topic front-matter (`entity_tags:` field). 565 files → **1 file per session** for an 89-message session.
- `_state.json` atomic write via `.tmp.<hex>` + `os.replace`.
- Wiki index/timeline/by-project rebuilt on every ingest.

### Fixed

- `_real_llm(prompt)` signature now accepts `max_tokens` keyword (matches `LLMCallable` protocol).
- Real LLM endpoint correctly resolves to `https://api.minimax.chat/anthropic` (Anthropic-compatible), not `/v1/messages`.
- Session JSONL envelope parsing handles `{type: "message", message: {role, content: [{type, text} | {type: toolCall, ...}]}}` (OpenClaw stores content as list).
- Heartbeat session pollution: filtered to true sessions only (3 of 10 vs 0 of 10).

### Migration

- Old `wiki_from_session.py` 67-files-per-session pattern deprecated. Existing wiki data files left in place for now; new ingest goes to `llmwiki/` (regenerable).
- `_keyword_index.json` (HEARTBEAT P0) still pending — 3 weeks overdue, deferred to v1.2.0.

## [1.0.1] - 2026-07-18

Wiki method-tree classification: tag every entry with the L0 modes / L1 recipes / roles / failure categories that produced it.

### Added

- `BUILD.md` — complete engineering development manual. Follow the 12 parts to rebuild the project from scratch (~5h, 307 tests pass).
- `wiki_store.write_dialogue/write_entity/write_topic` accept classification kwargs (`modes`, `l1_recipes`, `roles`, `failure_categories`).
- `.frontmatter_cache.json` — O(1) classification lookups, auto-maintained.
- 4 new query APIs:
  - `wiki_by_mode(mode_id)` — entries tagged with an L0 mode (e.g. `m_sprint`).
  - `wiki_by_role(role)` — entries involving a role (planner/worker/reviewer/reflector).
  - `wiki_by_l1_recipe(recipe_id)` — entries produced by a recipe (e.g. `plan_task`).
  - `wiki_by_failure_category(category)` — reflection entries.
- `wiki_mode_coverage()` — coverage report: per-method entry count, untagged entries, unused methods (gaps in wiki).
- `generate_coverage_report()` — writes `wiki/coverage.md`.
- `lint_wiki(mode_coverage)` — 8th lint step (with `methods_tree` param).
- `persist_to_wiki_from_pwr()` — auto-derives classification from `PWRResult.iterations`.
- `METHODS_TREE_INTRO.md` — plain-language walkthrough of the work method tree (no jargon).
- `test_phase8_wiki_classification.py` — 22 dedicated tests (307/307 total).

### Changed

- `lint_wiki` returns 8 keys (was 7); `mode_coverage` always present (empty when no methods_tree).
- Wiki entries now write 4-column index (`modes` column added).

### Backward compatible

- Existing wiki code without classification still works (front-matter simply omits new fields).
- `lint_wiki(root)` (no methods_tree) still returns 8 keys with empty mode_coverage.

## [1.0.0] - 2026-07-18

Initial stable release.

### Phase 7 (new since v7.0.0-skeleton)
- Independent work method tree (18 methods, 4 levels L0-L3)
- `scripts/methods_tree.py` with 4 API: search / get / get_children / find_path
- `methods/` folder with `_index.json`, `_schema.yaml`, `tree.yaml`, `recipes/`, `_meta/graph.json`
- 32 dedicated tests for method tree

### Phase 6
- Real LLM client (Anthropic-compatible) with mock fallback
- Sprint-mode wiki integration (recall-before-plan + persist-after)

### Phase 5
- 5-persona parallel discuss mode (analyst/critic/advocate/skeptic/synthesizer)
- Entity extractor (15 alias table + Chinese noun phrases)

### Phase 4
- Karpathy LLM Wiki (dialogue/entities/topics + 7-step lint)

### Phase 3
- Atomic write + per-file locking
- asyncio.TaskQueue with parallel sync/async detect

### Phase 2
- PWR loop state machine
- 4 role SYSTEM_PROMPTs

### Phase 1
- 5-mode router with priority tie-breaker

### Quality
- 285 tests PASS
- 14 source modules, ~110 KB
- 0 external deps
