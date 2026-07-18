# Release notes — v1.0.1

**mini-mp-agent** · single-agent multi-role PWR Loop · 2026-07-18

## TL;DR

Single-agent orchestration skill hosting **4 internal roles** in one Python process — avoids multi-agent session complexity by switching roles via `SYSTEM_PROMPT` variants. Ships **5 dispatch modes** (qa / task / discuss / auto / sprint) and an independent **18-method work method tree** (L0–L3). Zero external dependencies.

> **307 / 307 tests PASS** · License: MIT · stdlib only

## What's in v1.0.1

### Wiki method-tree classification (Phase 8)

Wiki entries are now tagged with the L0 mode(s) and L1 recipe(s) that produced them. Three new query APIs:

- `wiki_by_mode(mode_id) → list[WikiEntry]`
- `wiki_by_role(role) → list[WikiEntry]`
- `wiki_by_l1_recipe(l1_id) → list[WikiEntry]`
- `wiki_by_failure_category(category) → list[WikiEntry]`
- `wiki_mode_coverage() → dict` — auto-audit which methods have 0 wiki entries

Plus an **8th wiki lint step** `mode_coverage` (orphan / broken / isolated / stale / contradictions / missing / cross_refs / mode_coverage).

### Work method tree (18 methods, 4 levels)

| Level | Count | Examples |
|---|---|---|
| L0 — mode | 5 | `m_qa`, `m_task`, `m_discuss`, `m_auto`, `m_sprint` |
| L1 — recipe | 5 | `decompose_task`, `plan_task`, `execute_task`, `review_task`, `reflect_task` |
| L2 — sub-step | 5 | `wiki_recall`, `wiki_persist`, `score_output`, `extract_entities`, `lint_wiki` |
| L3 — primitive | 3 | `atomic_write`, `parallel_execute`, `early_stop` |

Each node carries 8 schema fields: `node_id`, `name`, `level`, `agent_role`, `inputs`, `outputs`, `dependencies`, `failure_modes`. Roles: `dispatcher / planner / worker / reviewer / reflector / shared`.

### Concurrency

- `task_queue.py` — `asyncio.Queue` + `WorkerPool` (max_size=100), sync/async auto-detect.
- `atomic_write.py` — `.tmp.<hex>` + `os.replace` + per-file `FileLock` (msvcrt.locking / fcntl.flock) + retry 5 with backoff.
- `parallel_execute` — RECIPES `parallel:` field + `asyncio.gather` / `run_in_executor`.

### LLM client

`scripts/llm_client.py` — real Anthropic-compatible API + deterministic mock fallback. Reads `~/.config/agent-platform/agent-config.json`, falls back to mock on missing config.

## Module map

| Module | Lines | Purpose |
|---|---|---|
| `scripts/mode_router.py` | ~180 | 5-mode dispatch |
| `scripts/pwr_loop.py` | ~270 | PWR state machine + early-stop |
| `scripts/roles.py` | ~130 | 4 role SYSTEM_PROMPTs |
| `scripts/handlers.py` | ~150 | mode handlers + 5-persona discuss |
| `scripts/methods_tree.py` | ~310 | tree API: search/get/find_path/validate |
| `scripts/wiki_store.py` | ~190 | Karpathy LLM Wiki (3 dirs + classification) |
| `scripts/dialogue_parser.py` | ~110 | parse text → dialogue segments |
| `scripts/entity_extractor.py` | ~225 | NER + 14-project alias table |
| `scripts/lint_wiki.py` | ~165 | 8-step lint |
| `scripts/atomic_write.py` | ~120 | atomic write + file lock |
| `scripts/task_queue.py` | ~200 | asyncio queue + WorkerPool |
| `scripts/wiki_integration.py` | ~170 | sprint recall-before-plan + persist-after |
| `scripts/llm_client.py` | ~225 | real LLM + mock fallback |

## Install & test

```bash
git clone https://github.com/quick123-666/mini-mp-agent.git
cd mini-mp-agent

# Run tests (stdlib only — no install required)
python tests/test_pwr_loop.py
python tests/test_mode_router.py
python tests/test_methods_tree.py
python tests/test_phase3_phase4.py
python tests/test_phase5.py
python tests/test_phase6.py
python tests/test_phase8_wiki_classification.py

# Or with pytest (optional)
pip install pytest
python -m pytest tests/
```

Expected: **307 / 307 PASS**.

## Quick start

```python
from scripts.handlers import handle_auto, handle_sprint
from scripts.methods_tree import MethodsTree

tree = MethodsTree()
auto = tree.get("m_auto")
print(auto.purpose)
# 'Run full PWR Loop with max_iter=3 and early-stop on score threshold.'

path = tree.find_path("m_sprint", "atomic_write")
# ['m_sprint', 'wiki_persist', 'atomic_write']

result = handle_sprint("design clean exit mode", wiki_root="./wiki")
```

## Design philosophy

> *"LLM writes, Python handles bookkeeping."* — Andrej Karpathy

- 0 external deps (stdlib only)
- Graceful degradation (mock LLM)
- Per-file locking + atomic_write
- Parallel ops via `run_in_executor` / `inspect.iscoroutine`
- Independent work method tree (no external dependency)
- GitHub-friendly paths

## License

MIT.

## Links

- README: see [`README.md`](./README.md)
- Walkthrough (no jargon): [`METHODS_TREE_INTRO.md`](./METHODS_TREE_INTRO.md)
- Full feature list: [`FEATURES.md`](./FEATURES.md)
- Development manual: [`BUILD.md`](./BUILD.md)
- Change history: [`CHANGELOG.md`](./CHANGELOG.md)
