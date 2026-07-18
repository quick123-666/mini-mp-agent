# Release notes — v1.1.0

**mini-mp-agent** · LLM Wiki redesign · 2026-07-18

## TL;DR

LLM Wiki pipeline **redesigned around 1 session = 1 topic**. The old `wiki_from_session.py` flooded the wiki with 67 files per session (1 topic + 3 dialogue pages + 63 entity pages). v1.1.0 collapses this to a single rich topic page with entity metadata in the front-matter. New 4-way ingest pipeline (`cron-full` / `mem` / `session` / `auto`) with atomic state, automatic index regeneration, and weekly lint.

> **310 / 310 tests PASS** (51+39+32+78+50+38+22) · License: MIT · stdlib only

## What's in v1.1.0

### Wiki redesign: 1 session = 1 topic

**Before** (`7e23778`) — 1 session produced **67 files**:
- 1 topic page
- 3 dialogue pages (one per user/assistant turn group)
- 63 entity pages (one per extracted entity)

**After** (`6a220f9`) — 1 session produces **1 file**:
- 1 topic page with rich front-matter: `modes`, `roles`, `l1_recipes`, `failure_categories`, `entity_tags`, `created`
- Entity names go into `entity_tags: [...]` front-matter field, **no per-entity files**
- Dialogue exchanges stay in the topic body as quoted blocks (no per-message pages)

**File-count reduction: 67x per session** (565 entity spam across 9 sessions → 9 topic pages).

### `scripts/wiki_ingest.py` — 4-way ingest

New 19K-byte entry point supporting 4 invocation modes:

| Source | Frequency | Behavior |
|--------|-----------|----------|
| `cron-full` | daily 23:00 (wrapper-internal) | Scans all session JSONL files, mtime-based delta, full pipeline |
| `mem` | every 3h | Scans `MEMORY.md` line-level delta from `_state.json.last_line` |
| `session` | manual | Single `session-id` ingest on demand |
| `lint` | every 3h | Orphan/stale/contradiction check, no new pages |

All writes go through **atomic state write** (`.tmp.<hex>` + `os.replace`) so cron crashes mid-write never leave half-baked files.

### `scripts/wiki_lint.py` — 3 health checks

- `orphans` — pages with no incoming front-matter links
- `stale` — pages >90 days old with no recent references
- `contradictions` — multiple D-NNN / M-XXX versions in different files

### `scripts/cron_llmwiki.sh` — 3h wrapper

Hourly cron runs the 3h path (`mem` delta + `lint`). At hour 23 it additionally runs `cron-full` for full catch-up.

### `persist_to_wiki` semantics change

```python
# Old (v1.0.1): wrote 67 files
result = persist_to_wiki(root, "task", pwr)
# → result["dialogue_written"] = 3, result["entities_written"] = 63

# New (v1.1.0): writes 1 file
result = persist_to_wiki(root, "task", pwr, write_topic_for="my-topic")
# → result["topic_written"] = True, result["dialogue_written"] = 0, result["entities_written"] = 0
# → entity names live in topic front-matter entity_tags
```

### Backwards compatibility

- `init_wiki()` still creates empty `dialogue/` and `entities/` subdirectories so `write_dialogue()` / `write_entity()` APIs from `wiki_store` keep working for any external caller.
- Old `examples/wiki_from_session.py` and `examples/_lint_wiki_summary.py` are now thin wrappers (3-line imports) that forward to the new `scripts/wiki_ingest.py` and `scripts/wiki_lint.py`.
- All Phase 6 / Phase 8 tests updated to match the new design (4 test cases touched).

### Auto-rebuilt indexes

Every ingest pass auto-regenerates:
- `index.md` — all topics in reverse chronological order
- `by-project/*.md` — topics grouped by project tag
- `timeline.md` — 1-line per topic for cheap scanning

## What this replaces

| Old | New |
|-----|-----|
| `examples/wiki_from_session.py` (565 files / 9 sessions) | `scripts/wiki_ingest.py` (9 topic files / 9 sessions) |
| ad-hoc `wiki_integration_step` calling `write_dialogue` + `write_entity` | `persist_to_wiki` writes 1 topic page only |
| `examples/_lint_wiki_summary.py` | `scripts/wiki_lint.py` (orphans/stale/contradictions) |
| Single cron at 11:30 daily | 3h wrapper + hour 23 cron-full catch-up |

## New files

| File | Bytes | Role |
|------|-------|------|
| `scripts/wiki_ingest.py` | ~19K | 4-way ingest entry + index regen |
| `scripts/wiki_lint.py` | ~8K | Weekly health check |
| `scripts/cron_llmwiki.sh` | ~1.8K | 3h wrapper, hour 23 full catch-up |
| `docs/llmwiki.md` | ~2.8K | Pipeline design doc |

## Files changed

- `scripts/wiki_integration.py` — `persist_to_wiki` now writes 1 topic only
- `examples/wiki_from_session.py` — thin wrapper (3 lines)
- `examples/_lint_wiki_summary.py` — thin wrapper
- `tests/test_phase6.py` — 3 cases updated to assert new design
- `tests/test_phase8_wiki_classification.py` — 1 case updated to pass `write_topic_for`

## Test coverage

```
test_pwr_loop                       51/51 PASS
test_mode_router                    39/39 PASS
test_methods_tree                   32/32 PASS
test_phase3_phase4                  78/78 PASS
test_phase5                         50/50 PASS
test_phase6                         38/38 PASS  (was 35/35, +3 case updates)
test_phase8_wiki_classification     22/22 PASS  (was 21/22, fixed 1 case)
                          Total    310/310 PASS
```

## Commits (12 ahead of v1.0.1)

```
6a220f9 feat(wiki): v1.1.0 - 1 session 1 topic, 4-way ingest, weekly lint
7e23778 feat(wiki): skip OpenClaw heartbeat sessions
4285e90 fix(wiki): auto-write topic from first user content, not the meta-prompt
b509fad fix(llm): make _real_llm actually callable from defaults
a4d9b37 fix: wiki_integration_step now auto-derives modes/l1_recipes/roles from PWR result
16cd01a feat: add wiki_from_session.py to generate LLM Wiki from OpenClaw session history
a6a39d8 feat: add e2e_demo MOCK support + wiki seed/lint demo
0355ac6 docs: rewrite Work Method Tree section using kitchen analogy + 4-questions structure
b268f23 docs: remove ASCII roadmap diagram per user feedback
1fcf59a docs: add Work Method Tree section to README
bfc80d9 docs: add zh-CN README with language toggle
351445d feat: rewrite README with full project documentation
```

## Known issues / next steps

- `entity_tags` front-matter still contains ~70 short Chinese noun phrases (e.g. "不自动注", "不要自动"). `_match_chinese_phrases` 2-3 char extraction needs further `ZH_NOISE_SUBSTRINGS` filtering.
- GitHub Release needs to be created manually (no `gh` CLI in this environment).
- OpenClaw cron for `cron_llmwiki.sh` 3h schedule not yet installed.

## Upgrade notes

- Existing wiki state from v1.0.1 stays readable (topic pages are compatible).
- Old dialogue/entity pages are **not** auto-cleaned. Run `scripts/wiki_lint.py` to find orphans.
- To re-ingest legacy sessions: `python scripts/wiki_ingest.py --wiki-root llmwiki --source cron-full --no-skip`
