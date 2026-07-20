<div align="center">

# mini-mp-agent

**Single-agent multi-role PWR Loop with Karpathy LLM Wiki**
*5 modes · 18-method work tree · 0 external dependencies · 333/333 tests PASS*

[![Tests](https://github.com/quick123-666/mini-mp-agent/actions/workflows/test.yml/badge.svg)](https://github.com/quick123-666/mini-mp-agent/actions/workflows/test.yml)
[![Release v1.3.0](https://img.shields.io/badge/release-v1.3.0-blue.svg)](https://github.com/quick123-666/mini-mp-agent/releases/tag/v1.3.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Dependencies: 0](https://img.shields.io/badge/dependencies-0-success.svg)](#-philosophy)
[![Tests 333/333](https://img.shields.io/badge/tests-333%2F333-brightgreen.svg)](#-tests)
[![Wiki recall](https://img.shields.io/badge/wiki_recall-3--phase-blueviolet.svg)](./RELEASE_NOTES_v1.3.0.md)

**Languages**: [English](./README.md) · [中文 (简体)](./README.zh-CN.md)

---

</div>

> **🆕 v1.3.0 — Wiki Recall + Two-Table Docs** (2026-07-20): 3-phase recall pipeline (`wiki_recall.py` keyword_grep → semantic_match → hybrid_rerank), full L1 method node replacing the 489-byte stub, public `docs/RELEASE_STATUS.md` + local `docs/DEV_PLAN.md` two-table pattern. See [RELEASE_NOTES_v1.3.0.md](./RELEASE_NOTES_v1.3.0.md).
>
> **v1.1.1 — Ship patch** (2026-07-18): `.gitignore llmwiki/ + *.lock`, `_sanitize_project_slug()` cross-platform safety, real OpenClaw cron (3h) hooked. 310 → 333 tests. See [RELEASE_NOTES_v1.1.1.md](./RELEASE_NOTES_v1.1.1.md).
>
> **v1.1.0 — LLM Wiki redesign** (2026-07-18): 1 session = 1 topic (67x fewer files). New `scripts/wiki_ingest.py` 4-way pipeline (cron-full / mem / session / lint) + atomic state + auto index regen. See [RELEASE_NOTES_v1.1.0.md](./RELEASE_NOTES_v1.1.0.md).

---

> *"LLM writes, Python handles bookkeeping."* — Andrej Karpathy

**mini-mp-agent** ships an *all-in-one* orchestration primitive: a single Python process hosting **4 internal roles** (Planner / Worker / Reviewer / Reflector) that switch via `SYSTEM_PROMPT` variants. It avoids multi-agent session complexity while keeping the **Plan → Work → Review → Reflect** state machine, a **5-mode dispatcher** (qa / task / discuss / auto / sprint), and an **independent 18-method work tree**.

[🚀 Quick Start](#-quick-start) · [📖 Docs](#-project-layout) · [🐛 Issues](https://github.com/quick123-666/mini-mp-agent/issues) · [💬 Discussions](https://github.com/quick123-666/mini-mp-agent/discussions)

---

## 📑 Table of Contents

- [🧐 About the Project](#-about-the-project)
  - [Built With](#built-with)
- [✨ Features](#-features)
- [🏗️ Architecture](#-architecture)
- [🌳 Work Method Tree](#-work-method-tree)
- [🚀 Quick Start](#-quick-start)
- [📦 Installation](#-installation)
- [🧪 Tests](#-tests)
- [🗂️ Project Layout](#-project-layout)
- [⚙️ Configuration](#-configuration)
- [🧭 Design Philosophy](#-design-philosophy)
- [🛣️ Roadmap](#-roadmap)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)
- [📬 Contact](#-contact)
- [🙏 Acknowledgments](#-acknowledgments)

---

## 🧐 About the Project

Most "multi-agent" systems spin up multiple sessions to coordinate work — paying for session setup, prompt-cache misses, and IPC. **mini-mp-agent** does the opposite: one process, four roles, one `SYSTEM_PROMPT` swap per turn.

It also carries an **independent 18-method work method tree** — a deterministic, versioned, lintable recipe library (`modes` → `recipes` → `sub-steps` → `primitives`) that the agent consults to choose between `atomic_write`, `wiki_recall`, `parallel_execute`, and friends. The tree is not LLM-generated; it is a first-class knowledge artifact.

### Built With

- **Python 3.11+** — stdlib only, zero external dependencies
- **asyncio** — `asyncio.Queue`, `asyncio.gather`, `run_in_executor`
- **File concurrency** — `msvcrt.locking` (Windows) / `fcntl.flock` (Unix) + `os.replace`
- **CI** — GitHub Actions on `ubuntu-latest` × Python 3.11
- **Wiki pattern** — Karpathy LLM Wiki (LLM writes, Python handles bookkeeping)

---

## ✨ Features

- 🎯 **5-mode dispatcher** — `qa` · `task` · `discuss` · `auto` · `sprint`, single-file routing (~180 LOC)
- 🔁 **4-role PWR state machine** — Planner → Worker → Reviewer → Reflector with score-based early-stop
- 🌳 **18-method work tree** — L0 modes (5) · L1 recipes (5) · L2 sub-steps (5) · L3 primitives (3), schema-validated
- 📚 **Karpathy LLM Wiki** — 3 categories (`concepts` / `facts` / `procedures`) + **8-step lint** (orphan / broken / isolated / stale / contradictions / missing / cross_refs / **mode_coverage**)
- 🏷️ **Wiki classification** — entries tagged with `modes`, `l1_recipes`, `roles`, `failure_categories`; queryable via 4 dedicated APIs + `wiki_mode_coverage()` audit
- 🔒 **atomic_write + per-file lock** — `.tmp.<hex>` + `os.replace` + retry 5 with backoff
- ⚡ **asyncio concurrency** — `task_queue.py` WorkerPool (max=100) + `parallel_execute` recipe
- 🧪 **Mock-friendly LLM client** — Anthropic-compatible real API + deterministic mock fallback (no API key needed for tests)
- 📦 **Zero external dependencies** — install nothing, run anywhere with Python 3.11+
- ✅ **333 / 333 tests PASS** — stdlib-only runner, no `pytest` required

---

## 🏗️ Architecture

```
                 ┌─────────────────────────┐
                 │  User query / task      │
                 └────────────┬────────────┘
                              ▼
                 ┌─────────────────────────┐
                 │  Mode router            │
                 │  (qa/task/discuss/      │
                 │   auto/sprint)          │
                 └────────────┬────────────┘
                              ▼
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
 ┌───────────┐          ┌───────────┐         ┌──────────────┐
 │ PWR Loop  │          │  Discuss  │         │ Wiki         │
 │ 4 roles   │          │ 5-persona │         │ recall +     │
 │ plan→work │          │ debate    │         │ persist      │
 │ →review   │          └───────────┘         └──────┬───────┘
 │ →reflect  │                                      │
 └─────┬─────┘                                      │
       │           ┌────────────────────────┐       │
       └──────────▶│ Work Method Tree       │◀──────┘
                   │ 18 nodes, L0–L3        │
                   └────────────┬───────────┘
                                ▼
                   ┌────────────────────────┐
                   │ LLM client             │
                   │ (Anthropic) + mock     │
                   └────────────────────────┘
```

**PWR Loop** = `Plan → Work → Review → Reflect` with optional early-stop on score threshold. Each role is a different `SYSTEM_PROMPT` registered in `scripts/roles.py`. The mode router picks which handler to invoke; the work method tree tells each handler which primitive / sub-step / recipe to call next.

---

## 🌳 Work Method Tree

The heart of mini-mp-agent is a **standalone, versioned recipe tree** that tells the system which tools are available, how they fit together, and who runs them. The tree is the source of truth — not an LLM artifact.

### Kitchen analogy

Imagine a **1-person restaurant** that gets an order "fish-flavored pork":

```
Waiter receives order →  Chef reads it
                          │
                          ▼
                     "This is a main dish"
                     (not dessert / drink)
                          │
                          ▼
                     Look up "fish-flavored pork" recipe
                     3 steps: slice meat · mix sauce · stir-fry
                          │
                          ▼
                     Stir-fry needs: wok + heat + spatula
                          │
                          ▼
                     Plate ✅
```

The 4 layers map directly onto the tree:

| Layer | Kitchen | Real meaning | Example |
|---|---|---|---|
| **L0** | Station type | Which entry point? | main dish / soup / dessert |
| **L1** | Recipe | A complete cooking flow | "fish-flavored pork" |
| **L2** | Recipe step | One step in a recipe | slice meat · mix sauce · stir-fry |
| **L3** | Physical tool | The actual utensil | wok · knife · fire |

**18 nodes across 4 levels.**

### 4 questions, 4 actions

The tree answers 4 questions every agent needs:

#### Q1: "Can you do this?"

```python
tree.search("parallel execution")
# → [parallel_execute (50%), execute_task (30%), plan_task (20%)]
```

Scoring: keyword match (+2) · name match (+1) · description match (0).

#### Q2: "What does this node do?"

```python
auto = tree.get("m_auto")
# Returns an 8-field card (no LLM involved):
#   node_id, name, level, purpose, inputs, outputs,
#   dependencies, failure_modes, agent_role
```

#### Q3: "What's inside?"

```python
tree.get_children("m_auto", depth=1)
# → [decompose_task, plan_task, execute_task, review_task, reflect_task]
```

L3 primitives return empty — tools have no children.

#### Q4: "How do I get from A to B?"

```python
tree.find_path("m_sprint", "atomic_write")
# → ['m_sprint', 'wiki_persist', 'atomic_write']
```

### Validation: catch typos before they ship

```python
report = tree.validate()
# → {
#     'valid': True,
#     'errors': [],
#     'stats': {'total_nodes': 18, 'total_edges': 25},
#     'by_level': {0: 5, 1: 5, 2: 5, 3: 3},
#     'by_role':  {'planner': 3, 'worker': 3, 'reviewer': 3,
#                  'reflector': 1, 'dispatcher': 5, 'shared': 3}
#   }
```

Catches: missing edge targets · illegal level jumps (e.g. L0 → L4) · cycles.

### Recipe format

Each L1/L2/L3 node is one YAML file under `methods/recipes/`. **Adding a new method = adding a YAML file, no Python change required.**

```yaml
# methods/recipes/wiki_persist.yaml
node_id: wiki_persist
name: Wiki Persist
level: 2
purpose: Write dialogue entry + entities + optional topic to wiki after PWR completes.
agent_role: worker
inputs: ["task (str)", "result (Any)", "wiki_root (Path)"]
outputs: ["dialogue_slug (str)", "entity_slugs (list[str])", "lint_summary (dict)"]
dependencies: ["extract_entities", "lint_wiki", "atomic_write"]
failure_modes: ["wiki_locked", "lint_fail"]
selector_keywords: ["persist", "save to wiki", "落盘", "存档"]
maturity: experimental
evidence: tests/test_phase6.py
```

> Full walkthrough, design rationale, and the kitchen analogy in plain language: see [`METHODS_TREE_INTRO.md`](./METHODS_TREE_INTRO.md).

---

## 🚀 Quick Start

```python
from scripts.handlers import handle_auto, handle_sprint
from scripts.methods_tree import MethodsTree

# 1. Consult the work method tree
tree = MethodsTree()
auto = tree.get("m_auto")
print(auto.purpose)
# → 'Run full PWR Loop with max_iter=3 and early-stop on score threshold.'

# 2. Find a path through the tree
path = tree.find_path("m_sprint", "atomic_write")
# → ['m_sprint', 'wiki_persist', 'atomic_write']

# 3. Run a task end-to-end
result = handle_sprint("design clean exit mode", wiki_root="./wiki")
```

Run the e2e demo:

```bash
python examples/e2e_demo.py
```

---

## 📦 Installation

mini-mp-agent has **zero external dependencies** — stdlib only.

```bash
git clone https://github.com/quick123-666/mini-mp-agent.git
cd mini-mp-agent
```

No `pip install` step required. Python 3.11+ recommended.

---

## 🧪 Tests

We ship a **custom stdlib-only test runner** — no `pytest` needed. Each `tests/test_*.py` is a self-contained script with its own PASS / FAIL accounting.

```bash
# Run each test file
python tests/test_pwr_loop.py
python tests/test_mode_router.py
python tests/test_methods_tree.py
python tests/test_phase3_phase4.py
python tests/test_phase5.py
python tests/test_phase6.py
python tests/test_phase8_wiki_classification.py
```

Expected output: `=== N/N PASS, 0 FAIL ===` for each.

| Test file | Tests | Covers |
|---|---:|---|
| `test_pwr_loop.py` | 51 | 4 roles · PWR state machine · score parsing |
| `test_mode_router.py` | 39 | 5-mode dispatch routing |
| `test_methods_tree.py` | 32 | 18-node tree · search / get / find_path / validate |
| `test_phase3_phase4.py` | 78 | atomic_write + task_queue |
| `test_phase5.py` | 50 | entity_extractor + 5-persona discuss |
| `test_phase6.py` | 35 | llm_client + wiki_integration |
| `test_phase8_wiki_classification.py` | 22 | front-matter + query APIs + mode_coverage |
| **Total** | **333** | **All passing ✅** |

### Optional: pytest cross-check

```bash
pip install pytest
python -m pytest tests/ -q --tb=line
```

> The CI workflow runs the stdlib runners first (authoritative), then pytest with `continue-on-error: true` as a sanity check.

---

## 🗂️ Project Layout

```
mini-mp-agent/
├── .github/
│   └── workflows/
│       └── test.yml            # CI: stdlib runner + pytest cross-check
├── methods/                    # 18-method work tree (Phase 7)
│   ├── recipes/                # 18 YAML recipe files
│   ├── _index.json
│   ├── _schema.yaml
│   ├── tree.yaml
│   └── _meta/graph.json
├── scripts/                    # 14 source modules (~2.5k LOC)
│   ├── mode_router.py
│   ├── pwr_loop.py
│   ├── roles.py
│   ├── handlers.py
│   ├── methods_tree.py
│   ├── wiki_store.py
│   ├── dialogue_parser.py
│   ├── entity_extractor.py
│   ├── lint_wiki.py
│   ├── atomic_write.py
│   ├── task_queue.py
│   ├── wiki_integration.py
│   └── llm_client.py
├── tests/                      # 8 files, 333 tests (stdlib runner)
├── examples/
│   └── e2e_demo.py             # End-to-end demo
├── README.md                   # ← you are here
├── METHODS_TREE_INTRO.md       # Plain-language tree walkthrough
├── FEATURES.md                 # Full feature list
├── BUILD.md                    # Development manual
├── CHANGELOG.md
├── LICENSE                     # MIT
├── VERSION.json
└── pyproject.toml
```

---

## ⚙️ Configuration

The LLM client reads API config from `~/.config/agent-platform/agent-config.json`:

```json
{
  "provider": "anthropic",
  "api_key": "sk-...",
  "model": "claude-sonnet-4-5",
  "base_url": "https://api.anthropic.com"
}
```

If the file is missing, `llm_client` **falls back to a deterministic mock** so all tests pass without any real API call. Set `LLM_DEBUG=1` for verbose logging.

---

## 🧭 Design Philosophy

> *"LLM writes, Python handles bookkeeping."* — Andrej Karpathy

- **0 external deps** (stdlib only) — installable in any Python 3.11+ environment
- **Graceful degradation** — mock LLM lets tests run without API keys
- **Per-file locking + atomic_write** — safe for multi-session concurrency
- **Parallel ops** via `run_in_executor` / `inspect.iscoroutine`
- **Independent work method tree** — not an LLM-generated artifact; versioned and lintable
- **GitHub-friendly paths** — sanitized at packaging time

---

## 🛣️ Roadmap

This project currently has **no formal roadmap**. The work method tree, PWR loop, and wiki classification are all shipped in v1.0.1 — the next direction will be driven by user feedback and GitHub Issues.

If you'd like to suggest a direction:

- 💡 [Open a feature request](https://github.com/quick123-666/mini-mp-agent/issues/new?labels=enhancement)
- 🐛 [Report a bug](https://github.com/quick123-666/mini-mp-agent/issues/new?labels=bug)
- 💬 [Start a discussion](https://github.com/quick123-666/mini-mp-agent/discussions/new)

For context on what shipped in v1.0.1, see [`RELEASE_NOTES_v1.0.1.md`](./RELEASE_NOTES_v1.0.1.md).

---

## 🤝 Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Contribution requirements

- All **333 existing tests must still pass** (run the stdlib runners above).
- New features should add at least one test in the matching `tests/test_*.py`.
- Wiki-related changes must keep all **8 lint steps clean** — `python -m scripts.lint_wiki` (or `scripts/lint_wiki.py` if invoked as a CLI).
- Use the **independent work method tree** rather than hard-coding recipes in Python — the tree is the source of truth.

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](./LICENSE) for the full text.

---

## 📬 Contact

- 🐛 **GitHub Issues** — [open one](https://github.com/quick123-666/mini-mp-agent/issues/new)
- 💬 **GitHub Discussions** — [start a thread](https://github.com/quick123-666/mini-mp-agent/discussions/new)
- 🏷️ **Releases** — [v1.1.1](https://github.com/quick123-666/mini-mp-agent/releases/tag/v1.1.1) · [v1.1.0](https://github.com/quick123-666/mini-mp-agent/releases/tag/v1.1.0) · [v1.0.1](https://github.com/quick123-666/mini-mp-agent/releases/tag/v1.0.1)

---

## 🙏 Acknowledgments

- [Andrej Karpathy](https://github.com/karpathy) — for the **LLM Wiki** philosophy that this project embodies
- [OpenHands](https://github.com/All-Hands-AI/OpenHands) / CocoLoop — inspiration for the multi-role orchestration pattern
- [meta-planner](https://github.com/) — the local knowledge-brain project this skill was extracted from (private lineage, public repo forthcoming)
- [Awesome README](https://github.com/jehna/awesome-readme) · [Best README Template](https://github.com/othneildrew/Best-README-Template) — README structure inspiration
- All early testers and contributors 💙

---

<div align="center">

**⭐ Star this repo if you find it useful!**

Made with ❤️ by the mini-mp-agent contributors.

</div>
