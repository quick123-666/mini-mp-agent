# Changelog

## [1.0.1] - 2026-07-18

Wiki method-tree classification: tag every entry with the L0 modes / L1 recipes / roles / failure categories that produced it.

### Added

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
