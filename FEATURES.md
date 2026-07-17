# mini-mp-agent 完整特色功能介绍 (v1.0.1)

> 一个 Python 编写的单 agent 编排工具,内置 4 个角色 + 完整 PWR 状态机 + 工作方法树 + Karpathy 对话 wiki + 并发原语,完全用标准库实现。

## 目录

1. [这是什么](#这是什么)
2. [5 分钟上手](#5-分钟上手)
3. [5 mode 路由](#1-5-mode-路由自动派发)
4. [PWR 状态机](#2-pwr-状态机plan--work--review--reflect)
5. [工作方法树](#3-工作方法树18-个方法独立知识体系)
6. [Karpathy LLM Wiki + 分类](#4-karpathy-llm-wiki--方法树分类v101-新增)
7. [5 视角并发讨论](#5-5-视角并发讨论discuss-模式)
8. [并发原语](#6-并发原语taskqueue--atomic_write)
9. [真实 LLM 接入 + mock 降级](#7-真实-llm-接入--mock-降级)
10. [实体识别 + 别名](#8-实体识别--别名)
11. [完整代码示例](#9-完整代码示例)
12. [架构图](#10-架构图)
13. [测试覆盖](#11-测试覆盖)

---

## 这是什么?

**mini-mp-agent** 是一个单 agent 4 角色编排 skill,在 1 个 Python 进程里跑 Plan → Work → Review → (Reflect) 状态机。免去多 agent session 复杂度,通过 SYSTEM_PROMPT 切换 4 种角色身份。

设计目标:
- **0 外部依赖** (纯 Python stdlib,可直接 pip install 无依赖)
- **可降级** (无 API key → deterministic mock,253+ 测试离线仍 PASS)
- **可观察** (每个 mode/recipe 都被 wiki 标签化分类,自动覆盖率审计)
- **可推理** (有 18 个 method 的工作方法树供 Planner 查,不能瞎编)

跟同类对比:
- 跟 LangGraph 对比:不用 DAG,直接 PWR 循环
- 跟 AutoGen 对比:无 multi-session,单进程内角色切换
- 跟 MetaGPT 对比:无 role 池,固定 4 角色

---

## 5 分钟上手

### 安装

```bash
git clone git@github.com:your-org/mini-mp-agent.git
cd mini-mp-agent
pip install -e .   # 无依赖,实际等于无操作
```

### 第一次跑

```python
from scripts.handlers import handle_sprint
from scripts.methods_tree import MethodsTree

# 1. 查看方法树 (18 个 method)
tree = MethodsTree()
print(f"共 {len(tree)} 个方法")

# 2. 找一个方法的依赖路径
path = tree.find_path("m_sprint", "atomic_write")
print(f"sprint 模式到原子写文件走 {len(path)} 步: {path}")

# 3. 完整跑一个任务 (sprint mode = PWR + wiki)
result = handle_sprint(
    "design clean exit mode for active cron jobs",
    wiki_root="./wiki",
)
print(f"success={result.get('success')}, tokens={result.get('total_tokens')}")
```

### 命令行

```bash
# 验证方法树
python -m scripts.methods_tree          # 18 nodes + 25 edges
python -m scripts.methods_tree list     # 列出全部
python -m scripts.methods_tree search wiki      # 关键词命中
python -m scripts.methods_tree path m_sprint atomic_write

# Wiki 维护
python -m scripts.wiki_store init ./demo-wiki
python -m scripts.wiki_store coverage ./demo-wiki
python -m scripts.wiki_store by-mode m_sprint ./demo-wiki
python -m scripts.lint_wiki ./demo-wiki --with-methods
```

---

## 1. 5 mode 路由(自动派发)

| mode | 干什么 | 何时用 | 默认 token |
|------|------|------|------|
| **qa** | 1 次 LLM 问 1 个问题 | 解释/定义/查询类 | ~500 |
| **task** | PWR 1 轮迭代 | 一次性的"做完"任务 | ~1500 |
| **discuss** | 5 persona 并行 + 综合 | 设计/对比/选型 | ~3000 |
| **auto** | 完整 PWR + Reflect(最多 3 轮) | 通用任务(默认) | ~2500 |
| **sprint** | auto + wiki recall + persist | 跨 session 大活儿 | ~3500 |

**路由规则**(关键词 + 优先级 tie-breaker):
- 关键词命中 → priority dict 排序 (sprint > discuss > task > qa)
- 平局时用 priority tie-breaker(默认 `auto`)
- 可手动 `route(task, mode="qa")` 强制覆盖

```python
from scripts.mode_router import detect_mode, route

# 自动检测
mode = detect_mode("对比 mp 和 mini-mp").mode  # → "discuss"
mode = detect_mode("做一个 chat bot").mode     # → "task"  
mode = detect_mode("什么是 PWR").mode          # → "qa"

# 手动覆盖
mode = detect_mode("设计一个...").mode         # → "auto" 或 "discuss"
mode = route("做一个 chat bot", mode="qa").mode  # → "qa"(强制)
```

**集成示例**:
- Agent 内部用 `detect_mode(user_input)` 自动选 mode
- 用户用 `/mode <name>` 命令强制切换
- 用户用 `mode="<name>"` 参数覆盖

---

## 2. PWR 状态机(Plan → Work → Review → Reflect)

```
              ┌──────────────┐
              │  Planner     │  ← 拆 task + 列计划
              └──────┬───────┘
                     │
              ┌──────▼───────┐
              │  Worker      │  ← 执行 plan
              └──────┬───────┘
                     │
              ┌──────▼───────┐
              │  Reviewer    │  ← 4 类 check → score 0-1
              └──────┬───────┘
                     │ score >= threshold?
       ┌─────────────┴────────────┐
       │ yes                      │ no
   ┌───▼────┐               ┌──────▼─────┐
   │ return │               │ Reflector   │ ← 算 fingerprint + 14 类分类
   └────────┘               └──────┬──────┘
                                   │ needs_replan
                            ┌──────▼──────┐
                            │  Planner    │ (next iter)
                            └──────────────┘
                max_iter (default 3)
```

**核心特性**:
- 每角色一份 SYSTEM_PROMPT,通过 LLM message role + system 注入切换
- 任意可注入的 LLM 函数 (`LLMCallable = Callable[[str, str], str]`) — 支持 mock / 真 LLM / 自定义
- `make_score_llm(target_score=N)` — 返回固定分数的 LLM (测试用)
- `make_score_llm` 智能解析: `"90%"` → 0.9 / `"0.85"` → 0.85 / `"-0.5"` → 0.5 (fallback) / clamp [0,1]
- early-stop: score ≥ threshold 立刻退出
- max_iter: 超 3 轮强制结束

```python
from scripts.pwr_loop import run_pwr, make_score_llm
from scripts.llm_client import get_default_llm

# 用真实 LLM
llm = get_default_llm()
result = run_pwr(task="refactor this code", llm=llm, threshold=0.7, max_iter=3)
print(f"success={result.success}, iters={result.total_iters}, score={result.final_score}")

# 用 mock (固定分数 0.9,跑 1 轮立刻停)
stub = make_score_llm(target_score=0.95)
result = run_pwr(task="any", llm=stub, threshold=0.9, max_iter=3)
print(f"score={result.final_score}, iters={result.total_iters}")  # 0.95 / 1
```

---

## 3. 工作方法树(18 个方法,独立知识体系)

**18 个方法** 分布在 4 层 (L0-L3):

```
L0 mode(5):     m_qa / m_task / m_discuss / m_auto / m_sprint
L1 recipe(5):   decompose_task / plan_task / execute_task / review_task / reflect_task
L2 sub-step(5): wiki_recall / wiki_persist / score_output / extract_entities / lint_wiki
L3 primitive(3):atomic_write / parallel_execute / early_stop
```

4 个查询 API + 1 个验证:

```python
from scripts.methods_tree import MethodsTree
tree = MethodsTree()

# 关键词搜 (top 3 相关)
results = tree.search("并行执行任务", top_k=3)
for m in results:
    print(f"{m.node_id}: {m.purpose}")

# 精确查 1 个
node = tree.get("execute_task")
print(f"purpose: {node.purpose}")
print(f"depends_on: {node.dependencies}")
print(f"failure_modes: {node.failure_modes}")
print(f"role: {node.agent_role}")

# 树展开 (从某节点往下 N 层)
children = tree.get_children("m_auto", depth=2)
for c in children:
    print(f"L{c.level} {c.node_id}")

# BFS 找依赖路径
path = tree.find_path("m_sprint", "atomic_write")
# → ['m_sprint', 'wiki_persist', 'atomic_write']

# 启动时一致性体检
report = tree.validate()
print(f"valid={report['valid']}, errors={report['errors']}")
print(f"stats={report['stats']}")
```

**设计哲学**:
- 完整 8 字段 schema,8 字段 + 1 自动反填 parents
- 启动时 `_load()` 一次性加载 18 个 method 到内存
- `validate()` 检查 edges / level transitions / level-counts
- CLI 入口 `python -m scripts.methods_tree <list|search|get|children|path>`

---

## 4. Karpathy LLM Wiki + 方法树分类(v1.0.1 新增)

**基础 wiki 结构**(Phase 4):

```
wiki/
├── index.md              # 总目录(表格)
├── log.md                # append-only 历史
├── contradictions.md     # 矛盾记录
├── coverage.md          # NEW 覆盖率报告
├── _meta/
│   ├── graph.json          # entity 关系图
│   └── .frontmatter_cache.json  # NEW front-matter 缓存(O(1))
├── dialogue/<slug>.md    # 对话 entries
├── entities/<slug>.md    # 人名 / 概念 / 工具
├── topics/<slug>.md      # 跨条目综述
└── by_mode/<mode_id>/    # NEW 按 mode 生成的子目录(自动)
```

**8-step linter**:
```
1. orphan             entry 没人引用
2. missing            alias of broken_wikilinks  
3. broken_wikilinks   [[X]] X 不存在
4. isolated           entity 没人引用
5. contradictions     文本重复检测
6. stale_claims       > 90 天没更新
7. missing_cross_refs cross-reference 缺失
8. mode_coverage      NEW Phase 8:哪些 method 缺 wiki 沉淀 / 哪些 entry 没分类
```

**v1.0.1 新增 4 个查询 API**:

```python
from scripts.wiki_store import (
    init_wiki, write_dialogue,
    wiki_by_mode, wiki_by_role, wiki_by_l1_recipe, wiki_by_failure_category,
    wiki_mode_coverage, generate_coverage_report,
)

root = init_wiki("./wiki")

# 写 entry 时顺便分类
write_dialogue(
    root, "sprint-decomp",
    "Decomp step content",
    modes=["m_sprint"],
    l1_recipes=["decompose_task"],
    roles=["planner"],
)

# 查询
sprint_entries = wiki_by_mode(root, "m_sprint")
planner_entries = wiki_by_role(root, "planner")
decomp_entries = wiki_by_l1_recipe(root, "decompose_task")

# 覆盖率审计
cov = wiki_mode_coverage(root, MethodsTree())
print(f"未沉淀方法: {cov['unused_methods']}")
print(f"未分类 entry: {cov['untagged_entries']}")

# 落盘
generate_coverage_report(root, MethodsTree())  # → wiki/coverage.md
```

**Auto-derive from PWR** (Phase 8):
```python
from scripts.wiki_integration import persist_to_wiki_from_pwr

pwr_result = {
    "status": "success",
    "iterations": [
        {"planner": "...", "worker": "...", "reviewer": "...", "reflection": "..."},
    ],
}
result = persist_to_wiki_from_pwr(
    root, "ship Plan F v8.1", pwr_result,
    write_topic_for="plan-f-ship",
)
# 自动从 iterations 提取:
#   modes = ['m_sprint']
#   l1_recipes = ['plan_task', 'execute_task', 'review_task']
#   roles = ['planner', 'worker', 'reviewer', 'reflector']
#   failure_categories = ['reflect_triggered']
```

---

## 5. 5 视角并发讨论(discuss 模式)

```python
from scripts.handlers import handle_discuss
result = handle_discuss("对比 mp 和 mini-mp 谁更适合小团队")
# 5 persona 并行:
#   - Pragmatist (工程落地视角)
#   - Skeptic (反驳 / 质疑)
#   - Optimist (机遇视角)
#   - Theorist (理论深度)
#   - Implementer (执行细节)
# 末尾合成最终结论
```

**核心特性**:
- 5 个 SYSTEM_PROMPT 并发 (TaskQueue.run_batch(workers=5))
- 各自 focus 不同维度,避免重复
- Modulator 聚合 consensus / disagreements / avg_score
- 返回 `consensus` / `disagreements` / `avg_score` 字段

---

## 6. 并发原语(TaskQueue + Atomic Write)

### TaskQueue (asyncio)

```python
from scripts.task_queue import TaskQueue, Task

# 提交混合 sync/async 任务,自动并行
q = TaskQueue(workers=3, max_size=100)

async def my_task(x):
    return x * 2

q.submit(Task("a", lambda: 1 + 1))                    # sync
await q.submit_async(Task("b", my_task, 5))            # async
await q.run_batch()                                    # 并行

results = q.results()  # {name: QueueResult}
```

**关键能力**:
- `inspect.iscoroutine(ret)` 自动检测 sync vs async
- sync 函数 → `run_in_executor` 真并行
- async 函数 → `asyncio.gather` 并发
- `max_size=100` 背压(超出抛 QueueFull)
- lambda 包 async 函数 `iscoroutinefunction` 不识别 → **先调一次看返回值类型**(踩过的坑)

### Atomic Write

```python
from scripts.atomic_write import atomic_write

# tmp + os.replace + per-file lock + retry 5
atomic_write(Path("output.txt"), "content here")
```

**保证**:
- 不会写到一半中断(写到 .tmp 完成才 rename)
- 跨进程互斥(Windows msvcrt.locking + Unix fcntl.flock)
- 失败自动重试 5 次 + 线性 backoff
- **幂等**(重复调用结果一致)

---

## 7. 真实 LLM 接入 + mock 降级

```python
from scripts.llm_client import (
    get_default_llm, force_mock, force_real,
    make_score_llm, has_real_llm,
)

# 自动:有 API key → 真实 LLM,无 → mock
llm = get_default_llm()

# 强制模式
stub = force_mock()
real = force_real(model="<ANTHROPIC_COMPATIBLE_MODEL>")

# 智能 score
score_fn = make_score_llm(llm)  # 接受 LLM,返回 0-1 分数函数
score = score_fn("user prompt", system="...")  # 处理 "90%" / "-0.5" / clamp [0,1]
```

**降级链**:
```
1. 读 agent-config.json 找 API key → 找到 → 真实 LLM
2. 未找到 → 读环境变量 → 找到 → 真实 LLM
3. 都没有 → 确定性 mock (基于输入 hash 生成固定输出)
```

---

## 8. 实体识别 + 别名

```python
from scripts.entity_extractor import extract_entities, group_by_type

text = "user 用 Python 写了 mini-mp-agent 的方法树"
entities = extract_entities(text)
# → [
#     {"entity": "Python", "type": "tool", "confidence": 0.95},
#     {"entity": "mini-mp-agent", "type": "concept", "confidence": 0.92},
#     ...
# ]

by_type = group_by_type(entities)
# → {"tool": [...], "concept": [...], ...}
```

**特性**:
- 14 个项目别名表(LangChain / CrewAI / AutoGen / Aris / mini-mp / SAG / ...)
- 中英文双语 stopword 过滤
- 中文短语启发式(`[\u4e00-\u9fff]{2,}`)
- 输出带置信度 + 类型(category: url/person/file/concept/tool)

---

## 9. 完整代码示例

### Sprint mode 一条龙(sprint + wiki + classify)

```python
from scripts.handlers import handle_sprint
from scripts.methods_tree import MethodsTree

result = handle_sprint(
    task="design clean exit-mode for active cron jobs when user says stop",
    wiki_root="./wiki",
    llm=None,  # 自动选 default LLM
)

print(result["pwr"])        # PWR 完整结果
print(result["wiki"])       # wiki 落盘统计
print(result["classification"])  # 分类标签
```

### 自定义 method → 注册到树 → Planner 自动用它

```python
# 1. 加 1 个 recipe (yaml)
import pathlib
(yaml_text := """
node_id: my_custom_step
name: My Custom Step
level: 2
purpose: 做某件特殊的事
inputs: [text]
outputs: [result]
agent_role: worker
failure_modes: [fail_a, fail_b]
maturity: experimental
selector_keywords: [my special]
""")
pathlib.Path("methods/recipes/my_custom_step.yaml").write_text(yaml_text)

# 2. 关联到 edge (在 _index.json edges 加 from/to)
# 3. 重启,PWR Loop 自动看到
```

---

## 10. 架构图

```
┌─────────────────────────────────────────────────────────────┐
│  User / Agent                                              │
│  input → mode_router.detect_mode()                         │
└────────────┬────────────────────────────────────────────────┘
             │
   ┌─────────▼──────────┐
   │   5 mode 分流       │
   │  qa/task/         │
   │  discuss/auto/    │
   │  sprint           │
   └─────────┬──────────┘
             │
   ┌─────────▼──────────┐
   │   PWR Loop         │  ← methods_tree 查 18 个 method
   │  Plan → Work →     │
   │  Review → Reflect  │
   │  (max_iter=3)      │
   └─────────┬──────────┘
             │
   ┌─────────┼─────────────────────────┐
   │         │                         │
   ▼         ▼                         ▼
┌────────┐ ┌────────┐             ┌──────────────┐
│ Wiki  │ │ LLM    │             │   并发原语   │
│ +分类  │ │ client │             │ task_queue   │
│ (v1.0.1│ │ + mock │             │ atomic_write │
│  新增) │ │ 降级   │             │ FileLock     │
└────────┘ └────────┘             └──────────────┘
```

**数据流(sprint mode 详细)**:

```
input
  → mode_router.route()=sprint
  → handle_sprint()
      → wiki_recall(task, wiki_root, top_k=3)  ← from methods_tree
      → run_pwr(task)
          → Planner 拆 3-7 步(op refs methods_tree)
          → Worker 执行 plan
          → Reviewer 打分 + 早退判断
          → (Reflector 如果 score < threshold)
      → persist_to_wiki_from_pwr()  ← auto-classify
          → write_dialogue(roles, recipes, modes)
          → write_entity(types, modes)
          → write_topic(sprint_summary, modes)
      → lint_wiki(methods_tree=tree)
      → generate_coverage_report()
      → return summary
```

---

## 11. 测试覆盖

| Test file | Pass | 内容 |
|---|---|---|
| test_mode_router | 39/39 | 5 mode dispatch + priority + cost estimation |
| test_pwr_loop | 51/51 | PWR state machine + role prompts + score parsing |
| test_phase3_phase4 | 78/78 | TaskQueue + atomic_write + Wiki 7-step lint + dialogue parser |
| test_phase5 | 50/50 | 5-persona discuss + entity extractor + alias table |
| test_phase6 | 35/35 | LLM client + score regex + wiki integration |
| test_methods_tree | 32/32 | 18-method tree + 4 API + validate + parents |
| test_phase8_wiki_classification | 22/22 | v1.0.1: front-matter + 4 query APIs + coverage + lint 8th |
| **Total** | **307/307** | |

**最大特性**: 全部 0 外部依赖 + 0 网络调用 + 0 API key 也能跑。

---

## 12. 设计哲学(给想深入的人)

1. **0 外部依赖**: 纯 Python stdlib,内嵌极简 YAML parser / JSON cache / 序列化
2. **Graceful degradation**: 无 API key 不报错,跑 mock;无 wiki 不报错,跑 in-memory
3. **跨 mode 解耦**: handlers 各自独立,但走同一份 wiki + methods_tree
4. **可观察性**: 每条 wiki entry 自带模式标签,可查覆盖率,可 lint
5. **可推理**: 工作方法树 18 个 method 是**白名单**,Planner 不能瞎编 op
6. **失败驱动**: Reflector 自动算 fingerprint + 14 类分类,下次遇到同 fp 提议新 recipe
7. **可测试**: LLMCallable 是注入式,测试可换 stub_llm / make_score_llm(N)

---

## 13. 适合场景

| 场景 | 适合用 mini-mp-agent? |
|---|---|
| 单进程 LLM orchestration | ✅ 完美 |
| 多 agent 协作(需要 sub-session) | ❌ 不适合(用 OpenHands / LangGraph) |
| 需要持久化 wiki 沉淀 | ✅ Karpathy 模式 + 分类 |
| 需要查覆盖率 / 知道哪些方法没用过 | ✅ v1.0.1 新增 |
| 离线跑 / 无 LLM API | ✅ mock 降级 |
| 生产级 robustness | ❌ 适合 prototype / internal tool,不是 production |
| 教学 / 研究 | ✅ 工作方法树非常适合学习 PWR pattern |

---

## 14. 引用格式

如果用在论文 / 报告里:

```bibtex
@software{mini_mp_agent_2026,
  author = {mini-mp-agent contributors},
  title = {mini-mp-agent: single-agent multi-role PWR loop with work method tree},
  version = {1.0.1},
  year = {2026},
  url = {<REPO_URL>}
}
```

---

## 15. License

MIT License - 详见 [LICENSE](./LICENSE)。
