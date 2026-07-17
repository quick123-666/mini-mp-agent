# mini-mp-agent

> **v1.0.1** — Single-agent multi-role PWR Loop + independent work method tree + Karpathy LLM Wiki + asyncio concurrency.
> 285+/285+ tests PASS · License: MIT · 0 external dependencies.

## What is mini-mp-agent?

A single-agent orchestration skill hosting 4 internal roles in one Python process. Avoids multi-agent session complexity by switching roles via SYSTEM_PROMPT variants. Ships 5 dispatch modes (qa / task / discuss / auto / sprint) and an independent **18-method work method tree** (L0-L3).

## Quick start

```python
from scripts.handlers import handle_auto, handle_sprint
from scripts.methods_tree import MethodsTree

# 1. Consult the work method tree
tree = MethodsTree()
auto = tree.get("m_auto")
print(auto.purpose)
# 'Run full PWR Loop with max_iter=3 and early-stop on score threshold.'

# 2. Find a path through the tree
path = tree.find_path("m_sprint", "atomic_write")
# ['m_sprint', 'wiki_persist', 'atomic_write']

# 3. Run a task end-to-end
result = handle_sprint("design clean exit mode", wiki_root="./wiki")
```

## What's in v1.0.1

This release introduces **method-tree classified wiki** — wiki entries are now tagged with the L0 mode(s) and L1 recipe(s) that produced them. Three new wiki APIs:

- `wiki_by_mode(mode_id) → list[WikiEntry]`
- `wiki_by_role(role) → list[WikiEntry]`
- `wiki_by_failure_category(category) → list[WikiEntry]`
- `wiki_mode_coverage() → dict` — auto-audit which methods have/don't have wiki entries.

Plus an 8th wiki lint step (`mode_coverage`).

For a plain-language walkthrough of the work method tree (no jargon), see [`METHODS_TREE_INTRO.md`](./METHODS_TREE_INTRO.md).

## Quick reference

| Module | Lines | Purpose |
|---|---|---|
| `scripts/mode_router.py` | ~180 | 5-mode dispatch (qa / task / discuss / auto / sprint) |
| `scripts/pwr_loop.py` | ~270 | Plan → Work → Review → Reflect state machine |
| `scripts/roles.py` | ~130 | 4 role SYSTEM_PROMPTs |
| `scripts/handlers.py` | ~150 | 5 mode handlers, 5-persona discuss, sprint wiki integration |
| `scripts/methods_tree.py` | ~310 | 18-method tree API: search / get / get_children / find_path / validate |
| `scripts/wiki_store.py` | ~190 | Karpathy LLM Wiki (3 dirs + index.md + log.md + contradictions.md + classification) |
| `scripts/dialogue_parser.py` | ~110 | Parse text → dialogue segments |
| `scripts/entity_extractor.py` | ~225 | NER with 14-project alias table |
| `scripts/lint_wiki.py` | ~165 | 8-step wiki linter (orphan / broken / isolated / stale / contradictions / missing / cross_refs / **mode_coverage**) |
| `scripts/atomic_write.py` | ~120 | tmp + os.replace + per-file lock + retry 5 |
| `scripts/task_queue.py` | ~200 | asyncio.Queue + WorkerPool, sync/async auto-detect |
| `scripts/wiki_integration.py` | ~170 | Sprint handler: recall-before-plan + persist-after |
| `scripts/llm_client.py` | ~225 | Real LLM (Anthropic-compatible) + mock fallback + score parser |

## Work method tree (18 methods, 4 levels)

L0 mode (5): m_qa / m_task / m_discuss / m_auto / m_sprint
L1 recipe (5): decompose_task / plan_task / execute_task / review_task / reflect_task
L2 sub-step (5): wiki_recall / wiki_persist / score_output / extract_entities / lint_wiki
L3 primitive (3): atomic_write / parallel_execute / early_stop

## Test

```bash
cd mini-mp-agent
python -m pytest tests/  # or python -m tests.test_*
```
Expected: **285+/285+ PASS**

## File layout

```
mini-mp-agent/
  methods/             # work method tree (Phase 7)
  scripts/             # 14 source modules
  tests/               # 6+ files, 285+ tests
  SKILL.md / VERSION.json / README.md / METHODS_TREE_INTRO.md
  CHANGELOG.md / LICENSE / pyproject.toml / .gitignore
  examples/e2e_demo.py
```

## Configuration

`llm_client.get_default_llm()` reads API config from `~/.config/agent-platform/agent-config.json`. Falls back to deterministic mock.

## Design philosophy

> "LLM writes, Python handles bookkeeping." - Andrej Karpathy

- 0 external deps (stdlib only)
- Graceful degradation (mock LLM)
- Per-file locking + atomic_write
- Parallel ops via run_in_executor / inspect.iscoroutine
- Independent work method tree (no external dependency)
- GitHub-friendly: paths sanitized at packaging time

## License

MIT.
