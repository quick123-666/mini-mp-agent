<div align="center">

# mini-mp-agent

**单智能体多角色 PWR 循环 + Karpathy LLM Wiki**
*5 种模式 · 18-方法工作树 · 0 外部依赖 · 307/307 测试通过*

[![Tests](https://github.com/quick123-666/mini-mp-agent/actions/workflows/test.yml/badge.svg)](https://github.com/quick123-666/mini-mp-agent/actions/workflows/test.yml)
[![Release v1.0.1](https://img.shields.io/badge/release-v1.0.1-blue.svg)](https://github.com/quick123-666/mini-mp-agent/releases/tag/v1.0.1)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Dependencies: 0](https://img.shields.io/badge/dependencies-0-success.svg)](#-设计理念)
[![Tests 307/307](https://img.shields.io/badge/tests-307%2F307-brightgreen.svg)](#-测试)

[English README](./README.md) · [🚀 快速上手](#-快速上手) · [📖 项目结构](#-项目结构) · [🐛 反馈问题](https://github.com/quick123-666/mini-mp-agent/issues)

---

</div>

> *"LLM 负责思考，Python 负责记账。"* — Andrej Karpathy

**mini-mp-agent** 是一个"一体化"编排原语：一个 Python 进程承载 **4 个内部角色**（Planner / Worker / Reviewer / Reflector），通过切换 `SYSTEM_PROMPT` 来实现角色流转。它绕开了多 agent session 的复杂度，同时保留了 **Plan → Work → Review → Reflect** 状态机、**5 种模式调度器**（qa / task / discuss / auto / sprint）和**独立的 18-方法工作树**。

---

## 📑 目录

- [🧐 关于本项目](#-关于本项目)
  - [技术栈](#技术栈)
- [✨ 功能特性](#-功能特性)
- [🏗️ 架构](#-架构)
- [🌳 工作方法树](#-工作方法树)
- [🚀 快速上手](#-快速上手)
- [📦 安装](#-安装)
- [🧪 测试](#-测试)
- [🗂️ 项目结构](#-项目结构)
- [⚙️ 配置](#-配置)
- [🧭 设计理念](#-设计理念)
- [🛣️ 路线图](#-路线图)
- [🤝 贡献](#-贡献)
- [📄 许可证](#-许可证)
- [📬 联系](#-联系)
- [🙏 致谢](#-致谢)

---

## 🧐 关于本项目

大多数"多 agent"系统要起多个 session 来协调工作——为此要付出 session 启动、prompt cache miss、IPC 等代价。**mini-mp-agent** 走的是相反的路：**一个进程、四个角色、每轮换一次 `SYSTEM_PROMPT`**。

它还内嵌了**独立的 18-方法工作树**——一个确定性的、版本化的、可 lint 的 recipe 库（`modes` → `recipes` → `sub-steps` → `primitives`），agent 通过查树来选择 `atomic_write`、`wiki_recall`、`parallel_execute` 等原语。这棵树不是 LLM 生成的，而是一等知识资产。

### 技术栈

- **Python 3.11+** — 仅用标准库，零外部依赖
- **asyncio** — `asyncio.Queue`、`asyncio.gather`、`run_in_executor`
- **文件并发** — `msvcrt.locking`（Windows）/ `fcntl.flock`（Unix）+ `os.replace`
- **CI** — GitHub Actions，`ubuntu-latest` × Python 3.11
- **Wiki 模式** — Karpathy LLM Wiki（LLM 思考，Python 记账）

---

## ✨ 功能特性

- 🎯 **5 种模式调度器** — `qa` · `task` · `discuss` · `auto` · `sprint`，单文件路由（约 180 行）
- 🔁 **4 角色 PWR 状态机** — Planner → Worker → Reviewer → Reflector，支持基于评分的早停
- 🌳 **18-方法工作树** — L0 模式（5 个）· L1 配方（5 个）· L2 子步骤（5 个）· L3 原语（3 个），schema 校验
- 📚 **Karpathy LLM Wiki** — 3 个分类（`concepts` / `facts` / `procedures`）+ **8 步 lint**（orphan / broken / isolated / stale / contradictions / missing / cross_refs / **mode_coverage**）
- 🏷️ **Wiki 分类** — 条目标记 `modes`、`l1_recipes`、`roles`、`failure_categories`；通过 4 个查询 API + `wiki_mode_coverage()` 审计接口
- 🔒 **atomic_write + 文件锁** — `.tmp.<hex>` + `os.replace` + 重试 5 次 + 退避
- ⚡ **asyncio 并发** — `task_queue.py` WorkerPool（最大 100）+ `parallel_execute` 配方
- 🧪 **友好的 mock LLM 客户端** — 兼容 Anthropic 的真实 API + 确定性的 mock 兜底（测试无需 API key）
- 📦 **零外部依赖** — 装包免配置，Python 3.11+ 即可运行
- ✅ **307 / 307 测试通过** — 纯标准库 runner，无需 `pytest`

---

## 🏗️ 架构

```
                 ┌─────────────────────────┐
                 │  用户查询 / 任务        │
                 └────────────┬────────────┘
                              ▼
                 ┌─────────────────────────┐
                 │  模式路由               │
                 │  (qa/task/discuss/      │
                 │   auto/sprint)          │
                 └────────────┬────────────┘
                              ▼
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
 ┌───────────┐          ┌───────────┐         ┌──────────────┐
 │ PWR 循环  │          │  Discuss  │         │ Wiki         │
 │ 4 角色    │          │ 5 人格    │         │ recall +     │
 │ plan→work │          │ 辩论      │         │ persist      │
 │ →review   │          └───────────┘         └──────┬───────┘
 │ →reflect  │                                      │
 └─────┬─────┘                                      │
       │           ┌────────────────────────┐       │
       └──────────▶│ 工作方法树             │◀──────┘
                   │ 18 节点，L0–L3         │
                   └────────────┬───────────┘
                                ▼
                   ┌────────────────────────┐
                   │ LLM 客户端             │
                   │ (Anthropic) + mock     │
                   └────────────────────────┘
```

**PWR 循环** = `Plan → Work → Review → Reflect`，可在评分达到阈值时早停。每个角色对应 `scripts/roles.py` 里注册的一个 `SYSTEM_PROMPT`。模式路由决定调用哪个 handler，工作方法树告诉 handler 接下来调用哪个原语 / 子步骤 / 配方。

---

## 🌳 工作方法树

mini-mp-agent 的核心是一棵**独立、版本化的工作树**——它告诉系统有哪些工具可用、它们怎么组合、由谁执行。树才是真相之源，不是 LLM 的临时产物。

### 厨房比喻

想象一家**只有一个员工的餐厅**，接到一份"鱼香肉丝"订单：

```
服务员接单 →  厨师看单
                │
                ▼
           "这是主菜档口"
           (不是甜品 / 饮品)
                │
                ▼
           查"鱼香肉丝"菜谱
           3 步: 切肉丝 · 调汁 · 大火爆炒
                │
                ▼
           大火爆炒要用: 锅 + 火 + 铲子
                │
                ▼
           出菜 ✅
```

四层直接对应工作树：

| 层 | 厨房 | 实际含义 | 例子 |
|---|---|---|---|
| **L0** | 档口类型 | 走哪个入口？ | 主菜 / 汤 / 甜品 |
| **L1** | 菜谱 | 一道完整菜的做法 | "鱼香肉丝做法" |
| **L2** | 菜谱的步骤 | 菜谱里的某一步 | 切肉丝 · 调汁 · 大火爆炒 |
| **L3** | 物理工具 | 真正动手的家伙 | 锅 · 刀 · 火 |

**18 个节点分布在 4 层**。

### 4 个核心问题，4 个查询动作

工作树回答 agent 必然会问的 4 个问题：

#### 问题 1:「这活你能干吗?」

```python
tree.search("并行执行")
# → [parallel_execute (50%), execute_task (30%), plan_task (20%)]
```

打分规则：关键词直接命中 +2 · 名字命中 +1 · 描述命中 0。

#### 问题 2:「这节点具体干啥?」

```python
auto = tree.get("m_auto")
# 返回 8 字段卡片（不调 LLM）：
#   node_id, name, level, purpose, inputs, outputs,
#   dependencies, failure_modes, agent_role
```

#### 问题 3:「它里面有啥?」

```python
tree.get_children("m_auto", depth=1)
# → [decompose_task, plan_task, execute_task, review_task, reflect_task]
```

L3 原语返回空——工具没有下一层。

#### 问题 4:「从 A 怎么走到 B?」

```python
tree.find_path("m_sprint", "atomic_write")
# → ['m_sprint', 'wiki_persist', 'atomic_write']
```

### 健康检查：拼写错？立刻抓出来

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

校验 3 件事：边引用的节点是否存在 · 级别跨度是否合理（如 L0 → L4 跳跃）· 是否出现环（死循环）。

### 配方格式

每个 L1/L2/L3 节点对应 `methods/recipes/` 下一个 YAML 文件。**新增方法 = 加一个 YAML 文件，无需改 Python**。

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

> 完整讲解、设计理念、人话版厨房比喻，详见 [`METHODS_TREE_INTRO.md`](./METHODS_TREE_INTRO.md)。

---

## 🚀 快速上手

```python
from scripts.handlers import handle_auto, handle_sprint
from scripts.methods_tree import MethodsTree

# 1. 查询工作方法树
tree = MethodsTree()
auto = tree.get("m_auto")
print(auto.purpose)
# → 'Run full PWR Loop with max_iter=3 and early-stop on score threshold.'

# 2. 在树中找路径
path = tree.find_path("m_sprint", "atomic_write")
# → ['m_sprint', 'wiki_persist', 'atomic_write']

# 3. 端到端跑任务
result = handle_sprint("设计一个干净的退出模式", wiki_root="./wiki")
```

跑 e2e 演示：

```bash
python examples/e2e_demo.py
```

---

## 📦 安装

mini-mp-agent **零外部依赖**——只用 Python 标准库。

```bash
git clone https://github.com/quick123-666/mini-mp-agent.git
cd mini-mp-agent
```

无需 `pip install`。建议 Python 3.11+。

---

## 🧪 测试

我们提供了**自定义的纯标准库测试 runner**——无需 `pytest`。每个 `tests/test_*.py` 都是自包含脚本，自带 PASS / FAIL 统计。

```bash
# 逐个跑测试文件
python tests/test_pwr_loop.py
python tests/test_mode_router.py
python tests/test_methods_tree.py
python tests/test_phase3_phase4.py
python tests/test_phase5.py
python tests/test_phase6.py
python tests/test_phase8_wiki_classification.py
```

预期输出：每个文件末尾打印 `=== N/N PASS, 0 FAIL ===`。

| 测试文件 | 测试数 | 覆盖范围 |
|---|---:|---|
| `test_pwr_loop.py` | 51 | 4 角色 · PWR 状态机 · 评分解析 |
| `test_mode_router.py` | 39 | 5 模式调度路由 |
| `test_methods_tree.py` | 32 | 18 节点树 · search / get / find_path / validate |
| `test_phase3_phase4.py` | 78 | atomic_write + task_queue |
| `test_phase5.py` | 50 | entity_extractor + 5 人格 discuss |
| `test_phase6.py` | 35 | llm_client + wiki_integration |
| `test_phase8_wiki_classification.py` | 22 | front-matter + 查询 API + mode_coverage |
| **合计** | **307** | **全部通过 ✅** |

### 可选：pytest 交叉验证

```bash
pip install pytest
python -m pytest tests/ -q --tb=line
```

> CI 工作流先跑标准库 runner（权威），再用 `continue-on-error: true` 跑 pytest 作为兜底。

---

## 🗂️ 项目结构

```
mini-mp-agent/
├── .github/
│   └── workflows/
│       └── test.yml            # CI：标准库 runner + pytest 交叉验证
├── methods/                    # 18-方法工作树（第 7 阶段）
│   ├── recipes/                # 18 个 YAML 配方文件
│   ├── _index.json
│   ├── _schema.yaml
│   ├── tree.yaml
│   └── _meta/graph.json
├── scripts/                    # 14 个源模块（约 2500 行）
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
├── tests/                      # 7 个文件，307 个测试（标准库 runner）
├── examples/
│   └── e2e_demo.py             # 端到端演示
├── README.md                   # 英文 README
├── README.zh-CN.md             # ← 你在这里
├── METHODS_TREE_INTRO.md       # 工作方法树的大白话讲解
├── FEATURES.md                 # 完整功能列表
├── BUILD.md                    # 开发手册
├── CHANGELOG.md
├── LICENSE                     # MIT
├── VERSION.json
└── pyproject.toml
```

---

## ⚙️ 配置

LLM 客户端从 `~/.config/agent-platform/agent-config.json` 读取配置：

```json
{
  "provider": "anthropic",
  "api_key": "sk-...",
  "model": "claude-sonnet-4-5",
  "base_url": "https://api.anthropic.com"
}
```

文件不存在时，`llm_client` **自动回退到确定性 mock**，所有测试无需真实 API 即可通过。设置 `LLM_DEBUG=1` 打开详细日志。

---

## 🧭 设计理念

> *"LLM 负责思考，Python 负责记账。"* — Andrej Karpathy

- **0 外部依赖**（仅标准库）—— 任何 Python 3.11+ 环境都能跑
- **优雅降级** —— mock LLM 让测试无需 API key
- **文件锁 + atomic_write** —— 多 session 并发安全
- **并行操作** 通过 `run_in_executor` / `inspect.iscoroutine`
- **独立的工作方法树** —— 不是 LLM 生成的产物；版本化、可 lint
- **GitHub 友好的路径** —— 打包时自动清洗

---

## 🛣️ 路线图

本项目目前**暂无正式路线图**。v1.0.1 已经把工作方法树、PWR 循环、wiki 分类全部 ship，下一步的方向由用户反馈和 GitHub Issues 驱动。

如果你想提建议：

- 💡 [提功能请求](https://github.com/quick123-666/mini-mp-agent/issues/new?labels=enhancement)
- 🐛 [报告 bug](https://github.com/quick123-666/mini-mp-agent/issues/new?labels=bug)
- 💬 [发起讨论](https://github.com/quick123-666/mini-mp-agent/discussions/new)

关于 v1.0.1 已交付的内容，详见 [`RELEASE_NOTES_v1.0.1.md`](./RELEASE_NOTES_v1.0.1.md)。

---

## 🤝 贡献

贡献正是让开源社区变得如此精彩的原因——无论是学习、启发还是创造。任何贡献都**深表感谢**。

如果你有能让项目更好的建议，请 fork 本仓库并发起 Pull Request，也可以直接开一个带 "enhancement" 标签的 issue。

1. Fork 本仓库
2. 创建特性分支（`git checkout -b feature/AmazingFeature`）
3. 提交修改（`git commit -m 'Add some AmazingFeature'`）
4. 推送到分支（`git push origin feature/AmazingFeature`）
5. 发起 Pull Request

### 贡献要求

- 全部 **307 个现有测试必须继续通过**（用上面的标准库 runner 跑）。
- 新功能要在对应的 `tests/test_*.py` 里至少加一个测试。
- Wiki 相关改动要保持全部 **8 步 lint 干净**——`python -m scripts.lint_wiki`（或 `scripts/lint_wiki.py` 作 CLI）。
- 优先使用**独立的工作方法树**，不要在 Python 里硬编码配方——树才是真相之源。

---

## 📄 许可证

本项目基于 MIT 许可证发布。完整文本见 [`LICENSE`](./LICENSE)。

---

## 📬 联系

- 🐛 **GitHub Issues** — [新建 issue](https://github.com/quick123-666/mini-mp-agent/issues/new)
- 💬 **GitHub Discussions** — [发起讨论](https://github.com/quick123-666/mini-mp-agent/discussions/new)
- 🏷️ **Releases** — [v1.0.1](https://github.com/quick123-666/mini-mp-agent/releases/tag/v1.0.1)

---

## 🙏 致谢

- [Andrej Karpathy](https://github.com/karpathy) — 提出 **LLM Wiki** 哲学，本项目正是这一思想的体现
- [OpenHands](https://github.com/All-Hands-AI/OpenHands) / CocoLoop — 多角色编排模式的灵感来源
- meta-planner — 这个 skill 从中抽取出来的本地知识脑项目（私有渊源，后续公开仓库）
- [Awesome README](https://github.com/jehna/awesome-readme) · [Best README Template](https://github.com/othneildrew/Best-README-Template) — README 结构借鉴
- 所有早期测试者和贡献者 💙

---

<div align="center">

**如果觉得有用，欢迎 ⭐ Star！**

由 mini-mp-agent 贡献者用 ❤️ 制作。

</div>
