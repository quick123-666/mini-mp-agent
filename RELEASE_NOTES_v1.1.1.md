# Release Notes — v1.1.1 (2026-07-18)

**Type:** patch (post-release ship patch for v1.1.0)
**Tests:** 310 → **333 PASS** (23 new unit tests)
**Commits:** `e22308f`, `ae00553` (HEAD)
**Previous:** [v1.1.0](./RELEASE_NOTES_v1.1.0.md)

---

## TL;DR

v1.1.1 closes 3 ship-completion gaps from v1.1.0 per the `D-ShipCompletionDefinition-001` rule:

1. `.gitignore` was missing `llmwiki/` and `*.lock` → 17 runtime artifacts (7 `.lock` files + 10 wiki data files) got committed and pushed to remote main. Now properly gitignored and untracked.
2. `by-project/(uncategorized).md` displayed oddly in `git ls-files` and would have failed on Windows-reserved-character filesystems. New `_sanitize_project_slug()` normalizes all Windows-illegal chars.
3. The "OpenClaw cron (ID 3dfde4ad)" noted in MEMORY was never actually installed — `~/.openclaw/cron/jobs.json.migrated.3` was empty. Real cron now registered as `4bfd77ef-5728-4c0e-bc57-0f3f6f2712bd` (every 3h).

---

## What's Changed

### Fixed

#### `.gitignore` gaps from v1.1.0 ship (`e22308f`)

- Added `llmwiki/` and `*.lock` patterns
- `git rm -r --cached llmwiki/` removed 17 runtime artifacts (7 `.lock` files + 10 wiki data files)
- Verified: `git ls-files | grep '\.lock'` returns 0 files
- Verified: `git ls-files llmwiki/` returns 0 files

#### Cross-platform project slug bug (`ae00553`)

Before:
```python
# wiki_ingest._rebuild_by_project()
projects = m.get("projects") or ["(uncategorized)"]
# ... (uncategorized) appears in filename, git ls-files shows (uncategorized).md
```

After:
```python
# wiki_ingest._sanitize_project_slug()
import re
s = p.lower().strip()
s = re.sub(r'[<>:"/\\|?*()\[\]\s]+', "-", s)
s = re.sub(r"-+", "-", s).strip("-")
return s or "uncategorized"
```

Coverage:
- `<>:"/\|?*()[]` → `-` (Windows-reserved chars)
- Whitespace → `-`
- Multiple dashes collapse
- Empty/special-only → `uncategorized`
- Realistic names preserved (`mini-mp-agent` → `mini-mp-agent`)

#### Phantom cron from v1.1.0 ship (no commit — config-only)

- MEMORY noted: "挂 OpenClaw cron (ID 3dfde4ad) 每 3 小时" — never actually installed
- Reality check: `~/.openclaw/cron/jobs.json.migrated.3` was `{ "jobs": [] }`
- Real cron now registered:
  - **Job ID:** `4bfd77ef-5728-4c0e-bc57-0f3f6f2712bd`
  - **Schedule:** every 3h (10,800,000 ms)
  - **Session target:** `isolated` (ephemeral agentTurn)
  - **Payload:** `bash E:/mini-mp-agent/scripts/cron_llmwiki.sh`
  - **Delivery:** `announce` (webchat)
  - **Failure alert:** after 2 consecutive failures, cooldown 1h

### Added

#### `tests/test_by_project_slug.py` (23 tests)

```
[PASS] lowercase: got='foo' want='foo'
[PASS] trim spaces: got='bar' want='bar'
[PASS] slash → dash: got='team-a' want='team-a'
[PASS] backslash → dash (Windows safety): got='team-a' want='team-a'
[PASS] both slashes: got='a-b-c' want='a-b-c'
[PASS] angle brackets: got='foo-bar-baz' want='foo-bar-baz'
[PASS] colon: got='foo-bar' want='foo-bar'
[PASS] double quote: got='foo-bar' want='foo-bar'
[PASS] pipe: got='foo-bar' want='foo-bar'
[PASS] question mark: got='foo-bar' want='foo-bar'
[PASS] asterisk: got='foo-bar' want='foo-bar'
[PASS] parens round: got='uncategorized' want='uncategorized'
[PASS] square brackets: got='foo-bar-baz' want='foo-bar-baz'
[PASS] spaces collapse: got='foo-bar-baz' want='foo-bar-baz'
[PASS] tabs and newlines: got='foo-bar-baz' want='foo-bar-baz'
[PASS] collapse dashes: got='foo-bar' want='foo-bar'
[PASS] leading/trailing dash stripped: got='foo' want='foo'
[PASS] empty string → uncategorized: got='uncategorized' want='uncategorized'
[PASS] only special chars → uncategorized: got='uncategorized' want='uncategorized'
[PASS] only dashes → uncategorized: got='uncategorized' want='uncategorized'
[PASS] kebab-case preserved: got='mini-mp-agent' want='mini-mp-agent'
[PASS] CamelCase lowercased: got='minimpagent' want='minimpagent'
[PASS] mixed case + path: got='team-awesome' want='team-awesome'

=== 23/23 passed, 0 failed ===
```

Total project tests: **333/333 PASS** across 8 test files.

#### OpenClaw cron job `4bfd77ef`

Verified by manual force-run:
- `lastRunStatus: "ok"`
- `lastDurationMs: 70399` (1 min 10 s)
- `consecutiveErrors: 0`
- `nextRunAtMs: 1784385640023` (3 h after first run)

Wrapper script `cron_llmwiki.sh`:
- `hour==23`: cron-full (all sessions, mtime delta)
- other hours: incremental + lint
- Exit 0 = OK; 1 = ingest/lint failed (retry); 2 = setup error (alert)

### Lessons (cross-ref `~/.qclaw/workspace/memory/2026-07-18.md` § 19:34)

| ID | imp | Title |
|---|---|---|
| `M-GitignoreAtomicWrite-001` | 0.7 | atomic_write tools must `.gitignore` their `.lock` files |
| `M-SlugSanitize-001` | 0.6 | Cross-platform filesystem-safe slug generation is required, not just path separator handling |
| `D-CronRegisterVerify-001` | 0.8 | "I wrote it in MEMORY" ≠ "I installed it". Cron registration needs verification (check `jobs.json` non-empty) |
| `D-ShipCompletionDefinition-001` | 0.9 | ship 完成的硬门槛 = (1) 代码 push (2) 文档/产物落地 (3) ≥1 个 M-/D- 提炼进 memory/<date>.md (4) MEMORY.md 独立文件索引同步更新 |

---

## Migration

### From v1.1.0

No code-level breaking changes. The 3 fixes are all **silent correctness improvements**:

- `.gitignore` change: existing local `llmwiki/` dir is unaffected (still regenerable by cron). Pull this version and run `git rm -r --cached llmwiki/` if you have stale index entries.
- `_sanitize_project_slug` change: pre-existing `by-project/(uncategorized).md` files can be safely deleted; the next ingest will rewrite them as `by-project/uncategorized.md`.
- Cron change: no user action. Real cron will start triggering in 3h.

### Cron behavior

```
[now]       — first manual force-run (verified ok, 70s)
[now+3h]    — first scheduled run
[now+6h]    — second scheduled run
[now+9h]    — third scheduled run
[...23:00]  — first cron-full run (all sessions)
```

Each run writes to:
- `E:\mini-mp-agent\llmwiki\` (regenerable runtime output, gitignored)
- `E:\mini-mp-agent\llmwiki\_state.json` (atomic write)
- `E:\mini-mp-agent\llmwiki\index.md`, `timeline.md`, `by-project/*.md` (rebuilt indexes)

---

## Verification

| Check | Result |
|---|---|
| `git log --oneline -5` | `ae00553`, `e22308f`, ... |
| `git ls-files \| grep '\.lock'` | 0 files ✅ |
| `git ls-files llmwiki/` | 0 files ✅ |
| `python3 tests/test_*.py` (8 files) | 333/333 PASS ✅ |
| OpenClaw cron `4bfd77ef` `lastRunStatus` | `ok` ✅ |
| `cron_llmwiki.sh` manual force-run | 70s, no errors ✅ |
| `MEMORY.md` § 独立教训文件索引 line 104 | ✅ pointer added |

---

## Next: v1.2.0 candidates (not committed)

- `HEARTBEAT P0`: rebuild `_keyword_index.json` (3 weeks overdue)
- Real cron first natural run report (3h after install)
- Consider adding `scripts/ship_pre_flight.py` to enforce 4-item ship checklist automatically

---

## Credits

- v1.1.0 ship gaps found by user prompt ("为何没有自动提炼工作方法")
- `D-ShipCompletionDefinition-001` rule authored after ship
- M-/D- lessons written to `~/.qclaw/workspace/memory/2026-07-18.md` § 19:34