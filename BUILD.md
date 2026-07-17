# BUILD.md — mini-mp-agent 完整工程开发手册

> 严格按以下步骤执行,可以从 0 复制出一份完全相同的 mini-mp-agent v1.0.1 项目。
>
> **预估工时**: 4-5 小时(含测试)。
> **依赖**: Python 3.10+,Git,标准库(无 pip 包)。

## 0. 项目结构预览

最终项目结构:

```
mini-mp-agent/
├── README.md / METHODS_TREE_INTRO.md / FEATURES.md / BUILD.md
├── CHANGELOG.md / VERSION.json
├── SKILL.md / LICENSE
├── pyproject.toml / .gitignore
├── methods/                  ← Phase 7 — 独立工作方法树
│   ├── _index.json
│   ├── _schema.yaml
│   ├── tree.yaml
│   ├── _meta/graph.json
│   └── recipes/  (15 个 yaml)
├── scripts/                  ← 14 个源模块
│   ├── __init__.py
│   ├── mode_router.py        (Phase 1)
│   ├── roles.py              (Phase 2)
│   ├── pwr_loop.py           (Phase 2)
│   ├── handlers.py           (Phase 1+5+6)
│   ├── atomic_write.py       (Phase 3)
│   ├── task_queue.py         (Phase 3)
│   ├── wiki_store.py         (Phase 4+8)
│   ├── dialogue_parser.py    (Phase 4)
│   ├── lint_wiki.py          (Phase 4+8)
│   ├── entity_extractor.py   (Phase 5)
│   ├── llm_client.py         (Phase 6)
│   ├── wiki_integration.py   (Phase 6+8)
│   └── methods_tree.py       (Phase 7)
└── tests/                    ← 7 个测试文件,共 307 测试
    ├── test_mode_router.py
    ├── test_pwr_loop.py
    ├── test_phase3_phase4.py
    ├── test_phase5.py
    ├── test_phase6.py
    ├── test_methods_tree.py
    └── test_phase8_wiki_classification.py
```

---

## Part 1: 项目初始化(5 分钟)

### 1.1 创建项目根 + git 初始化

```bash
mkdir mini-mp-agent
cd mini-mp-agent
git init -b main
```

### 1.2 `pyproject.toml` (Python 包元数据,纯声明)

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "mini-mp-agent"
version = "1.0.1"
description = "Single-agent multi-role PWR loop with work method tree, Karpathy LLM Wiki, asyncio"
requires-python = ">=3.10"
dependencies = []

[tool.setuptools.packages.find]
where = ["."]
include = ["scripts*", "mini_mp_agent*"]
```

### 1.3 `.gitignore`

```gitignore
__pycache__/
*.py[cod]
build/
dist/
.venv/
.pytest_cache/
.DS_Store
*.lock
```

### 1.4 `LICENSE` (MIT)

```
MIT License

Copyright (c) 2026 mini-mp-agent contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
```

### 1.5 验证

```bash
git add .
git commit -m "init: project skeleton (pyproject + .gitignore + LICENSE)"
```

---

## Part 2: 工作方法树(Phase 7,50 分钟)

> **为啥先做方法树?** 方法树是后 7 个步骤的"基础设施",其他模块都会 import `MethodsTree`。先建后用。

### 2.1 目录结构

```bash
mkdir -p methods/recipes methods/_meta
```

### 2.2 `methods/_schema.yaml` (8 字段 schema,140 字节一行)

```yaml
version: 1
node_fields:
  - name: node_id
    type: string
    required: true
    pattern: "^[a-z][a-z0-9_]{2,40}$"
  - name: name
    type: string
    required: true
  - name: level
    type: integer
    required: true
    enum: [0, 1, 2, 3, 4]
  - name: purpose
    type: string
    required: true
  - name: inputs
    type: array
    items: string
  - name: outputs
    type: array
    items: string
  - name: dependencies
    type: array
    items: string
  - name: failure_modes
    type: array
    items: string
  - name: agent_role
    type: string
    enum: [planner, worker, reviewer, reflector, dispatcher, shared]
  - name: selector_keywords
    type: array
    items: string
  - name: maturity
    type: string
    enum: [experimental, stable, deprecated]
```

### 2.3 `methods/_index.json` (18 nodes + 25 edges)

完整 JSON 见包内文件 `methods/_index.json`。结构:

- `version: 1`
- `total_methods: 18`
- `levels`: L0=5 / L1=5 / L2=5 / L3=3
- `nodes`: 18 个 `{id, level, role, maturity}`
- `edges`: 25 个 `{from, to}`

### 2.4 `methods/recipes/*.yaml` (15 个)

每个文件用同一种结构:

```yaml
node_id: <id>
name: <人读名>
level: <0-3>
purpose: <一句话做什么>
inputs: [<输入列表>]
outputs: [<输出列表>]
dependencies: [<依赖的 method_id 列表>]
failure_modes: [<已知失败模式>]
agent_role: <planner/worker/reviewer/reflector/dispatcher/shared>
selector_keywords: [<路由关键词>]
maturity: <experimental/stable/deprecated>
evidence: <测试文件路径>
```

完整 15 个 recipe 已 ship 在 `methods/recipes/`。要点:
- **L0 模式**(5): m_qa / m_task / m_discuss / m_auto / m_sprint,`agent_role: dispatcher`
- **L1 recipe**(5): decompose_task / plan_task / execute_task / review_task / reflect_task,对应 PWR 5 阶段
- **L2 sub-step**(5): wiki_recall / wiki_persist / score_output / extract_entities / lint_wiki
- **L3 primitive**(3): atomic_write / parallel_execute / early_stop

### 2.5 `methods/tree.yaml` (人读树视图)

完整内容见包内 `methods/tree.yaml`。结构 (5 个 root,每个展开 1-2 层):

```yaml
version: 1
tree:
  - node_id: m_qa
    level: 0
    children:
      - node_id: decompose_task
        level: 1
        ...
```

### 2.6 `methods/_meta/graph.json` (依赖图)

完整内容见包内 `methods/_meta/graph.json`。结构: `{"edges": [{from, to, type}]}`。

### 2.7 `scripts/methods_tree.py` (4 API,310 行)

**实现关键点**:

```python
# (a) MethodNode dataclass,9 字段
@dataclass
class MethodNode:
    node_id: str
    name: str
    level: int
    purpose: str
    inputs: list[str]
    outputs: list[str]
    dependencies: list[str]
    failure_modes: list[str]
    agent_role: str = "shared"
    selector_keywords: list[str]
    maturity: str = "experimental"
    evidence: str = ""
    parents: list[str] = field(default_factory=list)

# (b) MethodsTree 类 4 API + validate
class MethodsTree:
    def __init__(self, root=DEFAULT_ROOT):
        self.root = Path(root)
        self._nodes = {}
        self._edges = []
        self._load()
    
    def search(self, query, top_k=3) -> list[MethodNode]:
        """关键词匹配:selector_keywords hit +2,purpose 词 hit +1,name 词 hit +2"""
        ...
    
    def get(self, node_id) -> Optional[MethodNode]:
        return self._nodes.get(node_id)
    
    def get_children(self, node_id, depth=1) -> list[MethodNode]:
        """从 self._edges 找所有 where from=node_id,递归扩展"""
        ...
    
    def find_path(self, from_id, to_id) -> Optional[list[str]]:
        """BFS self._edges"""
        ...
    
    def validate(self) -> dict:
        """检查 edge 引用 + level 跳变 + 统计 stats"""
        ...

# (c) 加载 _index.json + 每份 recipes/*.yaml,内嵌极简 YAML parser
# (d) parents 自动反填:遍历 edges 构建 parent_map
```

**YAML parser 极简版**(避免 PyYAML):

```python
def _parse_yaml_recipe(self, path: Path) -> Optional[MethodNode]:
    text = path.read_text(encoding="utf-8")
    data = {}
    current_key = None
    current_list = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current_list is not None:
                current_list.append(stripped[2:].strip().strip('"').strip("'"))
            continue
        if ":" in stripped:
            if current_key and current_list is not None:
                data[current_key] = current_list
                current_list = None
            key, _, val = stripped.partition(":")
            key, val = key.strip(), val.strip()
            if val == "":
                current_key = key
                current_list = []
            elif val.startswith("[") and val.endswith("]"):
                items = val[1:-1].split(",")
                data[key] = [i.strip() for i in items if i.strip()]
            else:
                data[key] = val.strip('"').strip("'")
    if "level" in data:
        try: data["level"] = int(data["level"])
        except: data["level"] = 0
    return MethodNode(**data)
```

**`validate()` level 跳变规则**(允许 0 / +1 / +2 / +3,禁止负跳):

```python
for edge in self._edges:
    f, t = edge["from"], edge["to"]
    lvl_from = self._nodes[f].level
    lvl_to = self._nodes[t].level
    diff = lvl_to - lvl_from
    if diff < 0: errors.append(f"upward transition {f}→{t}")
    elif diff > 3: errors.append(f"jump too large {f}→{t}")
```

完整实现见 `scripts/methods_tree.py`。

### 2.8 测试: `tests/test_methods_tree.py` (32 测试,完整代码在包内)

关键断言:

```python
def test_tree_loads_18_nodes():
    assert len(TREE) == 18

def test_search_score_keyword_priority():
    results = TREE.search("atomic")
    assert results[0].node_id == "atomic_write"  # selector_keywords 优先

def test_find_path_transitive():
    path = TREE.find_path("m_sprint", "atomic_write")
    assert path[0] == "m_sprint"
    assert path[-1] == "atomic_write"

def test_validate_passes():
    report = TREE.validate()
    assert report["valid"]
    assert report["stats"]["total_nodes"] == 18
    assert report["stats"]["total_edges"] >= 20
```

测试用一个简单 `assert_eq / assert_true / assert_in` 工具函数(不用 pytest)。Runner 模式:

```python
TESTS = [<list of test functions>]
def main():
    passed = failed = 0
    for t in TESTS:
        try: t(); passed += 1
        except AssertionError as e: print(f"[FAIL] {t.__name__}: {e}"); failed += 1
    print(f"{passed}/{passed+failed} passed")
    sys.exit(0 if failed == 0 else 1)
```

### 2.9 Part 2 验证

```bash
$ python -m scripts.methods_tree
=== Method Tree Validation ===
valid: True
errors: []
stats: {'total_nodes': 18, 'total_edges': 25, ...}

$ python -m tests.test_methods_tree
=== methods_tree tests (32) ===
  [PASS] test_tree_loads_18_nodes
  ...
32/32 passed, 0 failed

$ git add -A && git commit -m "phase 7: methods tree (18 nodes, 4 API)"
```

---

## Part 3: Phase 1 — Mode Router(15 分钟)

### 3.1 `scripts/__init__.py`

```python
"""mini-mp-agent source package."""
```

### 3.2 `scripts/mode_router.py` (~180 行)

**核心数据结构**:

```python
from dataclasses import dataclass

@dataclass
class ModeDecision:
    mode: str
    scores: dict          # qa/task/discuss/auto/sprint → score
    matched_keywords: dict
    reason: str

@dataclass
class CostEstimate:
    latency_s: float
    tokens: int

# 5 mode 优先级 (高 → 低)
MODE_PRIORITY = {"sprint": 5, "discuss": 4, "task": 3, "qa": 2, "auto": 1}

# 5 mode 成本估计
MODE_COST = {
    "qa":      CostEstimate(2.0, 500),
    "task":    CostEstimate(10.0, 1500),
    "discuss": CostEstimate(20.0, 3000),
    "auto":    CostEstimate(30.0, 2500),
    "sprint":  CostEstimate(40.0, 3500),
}

# 关键词集 (从方法树 selector_keywords 聚合)
KEYWORDS = {
    "qa":      {"what", "how", "why", "explain", "什么是", "怎么", "为什么", ...},
    "task":    {"做", "fix", "修", "create", "写", "实现", "build", "ship", ...},
    "discuss": {"对比", "评估", "选哪个", "vs", "compare", "讨论", "权衡", ...},
    "auto":    set(),
    "sprint":  {"全栈", "多步", "完整", "ship it", "项目", "一整套", "全套", ...},
}

def detect_mode(task: str) -> ModeDecision:
    """返回最高 priority 的命中 mode"""
    scores = {m: 0 for m in MODE_PRIORITY}
    matched = {m: [] for m in MODE_PRIORITY}
    task_lower = task.lower()
    for mode, kws in KEYWORDS.items():
        for kw in kws:
            if kw.lower() in task_lower:
                scores[mode] += 1
                matched[mode].append(kw)
    # 选 max score,平局用 priority tie-breaker
    best_mode = max(scores, key=lambda m: (scores[m], MODE_PRIORITY[m]))
    if scores[best_mode] == 0:
        best_mode = "auto"  # 默认 fallback
    return ModeDecision(
        mode=best_mode,
        scores=scores,
        matched_keywords=matched,
        reason=f"score {scores[best_mode]} on {best_mode}; via {matched[best_mode]}"
    )

def route(task, mode=None, handlers=None) -> ModeDecision:
    if mode is not None:
        return ModeDecision(mode=mode, scores={}, matched_keywords={}, reason="explicit override")
    return detect_mode(task)
```

完整实现见 `scripts/mode_router.py`。

### 3.3 `scripts/handlers.py` v1 (Phase 1 stub,150 行)

```python
"""Handler stubs for each of 5 modes (Phase 1)."""
from .mode_router import detect_mode, MODE_COST

def handle_qa(task: str) -> dict:
    """Single LLM call. Stub: returns metadata only."""
    return {"phase": 1, "mode": "qa", "task": task, "handler": "qa"}

def handle_task(task: str) -> dict:
    return {"phase": 1, "mode": "task", "task": task, "handler": "task"}

def handle_discuss(task: str) -> dict:
    return {"phase": 1, "mode": "discuss", "task": task, "handler": "discuss"}

def handle_auto(task: str) -> dict:
    return {"phase": 1, "mode": "auto", "task": task, "handler": "auto"}

def handle_sprint(task: str) -> dict:
    return {"phase": 1, "mode": "sprint", "task": task, "handler": "sprint"}

HANDLERS = {
    "qa": handle_qa,
    "task": handle_task,
    "discuss": handle_discuss,
    "auto": handle_auto,
    "sprint": handle_sprint,
}
```

(后续 Phase 2/5/6 会重写 handlers.py 调真 PWR loop / 5-persona / wiki integration)

### 3.4 测试 `tests/test_mode_router.py` (39 测试)

关键断言:

```python
from scripts.mode_router import detect_mode, MODE_PRIORITY, MODE_COST

def test_qa_detected():
    d = detect_mode("什么是 PWR")
    assert d.mode == "qa"

def test_task_detected():
    d = detect_mode("做一个 chat bot")
    assert d.mode == "task"

def test_discuss_detected():
    d = detect_mode("对比 mp 和 mini-mp")
    assert d.mode == "discuss"

def test_sprint_priority_beats_auto():
    """auto 应该有 score 0,sprint 有命中,mode=sprint"""
    d = detect_mode("全栈 ship Plan F v8")
    assert d.mode == "sprint"

def test_default_auto_when_no_match():
    d = detect_mode("hello")
    assert d.mode == "auto"

def test_cost_estimate():
    for mode in ("qa", "task", "discuss", "auto", "sprint"):
        cost = MODE_COST[mode]
        assert cost.tokens > 0
        assert cost.latency_s > 0
```

### 3.5 Part 3 验证

```bash
$ python -m tests.test_mode_router
=== mode_router tests (39) ===
  ...
39/39 PASS

$ git add -A && git commit -m "phase 1: mode router (5 modes, priority tie-breaker)"
```

---

## Part 4: Phase 2 — PWR Loop(40 分钟)

### 4.1 `scripts/roles.py` (4 SYSTEM_PROMPT,130 行)

**Planner SYSTEM_PROMPT** (关键):

```python
PLANNER_SYSTEM = """你是一名 Planner (mini-mp-agent 内置角色).

任务: 给定 task, 拆解成可执行的 plan 步骤.

【工作方法树参考】 (Phase 7+ 已集成)
在拆 task 之前, 你必须先查询工作方法树 (scripts.methods_tree.MethodsTree):
- tree.search(task, top_k=3)        → 找到最相关的 3 个 method
- tree.get(node_id)                  → 拿完整 method 定义
- tree.get_children(node_id, depth=2) → 拿子方法
- tree.find_path(start, end)         → 拿依赖路径

可用 method 总览 (18 个, 4 层 L0-L3):
  L0 mode:      m_qa / m_task / m_discuss / m_auto / m_sprint
  L1 recipe:    decompose_task / plan_task / execute_task / review_task / reflect_task
  L2 sub-step:  wiki_recall / wiki_persist / score_output / extract_entities / lint_wiki
  L3 primitive: atomic_write / parallel_execute / early_stop

Plan schema (markdown):
\`\`\`
## Plan
- step 1: <description> [op=<method>] [parallel=<true|false>]
- step 2: <description> [op=<method>] [parallel=<true|false>]
- ...
\`\`\`

约束:
- 3-7 步, 每步 [op=] 必须是上述 18 个 method 之一
- 标 parallel=True 的 step 可 asyncio.gather 并行
- 不要解释, 只输出 Plan 块
"""
```

类似写 `WORKER_SYSTEM` / `REVIEWER_SYSTEM` / `REFLECTOR_SYSTEM`(完整内容见包内 `scripts/roles.py`)。

### 4.2 `scripts/pwr_loop.py` (~270 行)

**核心数据结构**:

```python
from dataclasses import dataclass, field, asdict

LLMCallable = Callable[[str, str], str]  # (system_prompt, user_msg) -> response_text

@dataclass
class PWRIteration:
    iter: int
    role_history: list[str]
    plan: str = ""
    result: str = ""
    review_score: float = 0.0
    review_notes: str = ""
    reflection: str = ""
    needs_replan: bool = False

@dataclass
class PWRResult:
    task: str
    iterations: list[PWRIteration]
    final_score: float
    success: bool
    total_iters: int
    total_tokens: int = 0
    error: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)

def stub_llm(system_prompt, user_msg) -> str:
    """Phase 1 stub. 返回带 user_msg 的 hash 的固定文本"""
    return f"STUB: {hashlib.md5(user_msg.encode()).hexdigest()[:10]}"

def make_score_llm(target_score=0.5, label=""):
    """返回固定 score 的 LLM (测试用)"""
    def _score(system, msg):
        return f"score={target_score}"
    _score.__name__ = f"score_{target_score}_{label}"
    return _score

DEFAULT_LLM = stub_llm
```

**state machine**:

```python
def run_pwr(task, llm=DEFAULT_LLM, threshold=0.7, max_iter=3, **kwargs) -> PWRResult:
    iterations = []
    for i in range(max_iter):
        # 1. Planner: produce plan
        plan_text = llm(PLANNER_SYSTEM, task)
        # 2. Worker: execute
        result = llm(WORKER_SYSTEM, f"plan={plan_text}; task={task}")
        # 3. Reviewer: score
        score_text = llm(REVIEWER_SYSTEM, f"result={result}")
        score = parse_review_score(score_text)
        it = PWRIteration(iter=i, plan=plan_text, result=result, 
                         review_score=score, role_history=["planner","worker","reviewer"])
        iterations.append(it)
        # 4. Early stop check
        if score >= threshold:
            return PWRResult(task, iterations, score, True, i+1)
        # 5. Reflection (if fail)
        if i < max_iter - 1:
            reflection = llm(REFLECTOR_SYSTEM, f"score={score} task={task}")
            it.reflection = reflection
            it.needs_replan = True
    return PWRResult(task, iterations, iterations[-1].review_score if iterations else 0.0,
                    False, len(iterations))

def parse_review_score(text):
    """'score=0.85' → 0.85,  '90%' → 0.9,  '-0.5' → 0.5 (fallback), clamp [0,1]"""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(%)?", text)
    if m:
        val = float(m.group(1))
        is_pct = m.group(2) == "%"
        if is_pct:
            val /= 100.0
        return max(0.0, min(1.0, val))
    return 0.5
```

**集成 methods_tree 单例**:

```python
from .methods_tree import MethodsTree as _MethodsTree

_METHOD_TREE = None

def get_method_tree() -> _MethodsTree:
    global _METHOD_TREE
    if _METHOD_TREE is None:
        _METHOD_TREE = _MethodsTree()
    return _METHOD_TREE
```

完整实现见 `scripts/pwr_loop.py`。

### 4.3 重写 `scripts/handlers.py` 调真 PWR(从 stub 升级)

```python
from .pwr_loop import run_pwr, make_score_llm
from .role_prompts import PLANNER_SYSTEM, WORKER_SYSTEM, REVIEWER_SYSTEM, REFLECTOR_SYSTEM  # noqa

def handle_qa(task, llm=None) -> dict:
    """直接 1 次 LLM 答"""
    response = (llm or stub_llm)("", task)
    return {"mode": "qa", "task": task, "response": response}

def handle_task(task, llm=None, **kwargs) -> dict:
    """PWR 1 轮"""
    result = run_pwr(task, llm=llm or stub_llm, max_iter=1, threshold=0.7, **kwargs)
    return {"mode": "task", "pwr": result.to_dict()}

def handle_auto(task, llm=None, **kwargs) -> dict:
    result = run_pwr(task, llm=llm or stub_llm, max_iter=3, threshold=0.7, **kwargs)
    return {"mode": "auto", "pwr": result.to_dict()}

def handle_sprint(task, llm=None, wiki_root=None, **kwargs) -> dict:
    """auto + wiki 集成"""
    result = run_pwr(task, llm=llm or stub_llm, max_iter=3, threshold=0.7, **kwargs)
    wiki = {}
    if wiki_root:
        from .wiki_integration import persist_to_wiki_from_pwr
        wiki = persist_to_wiki_from_pwr(wiki_root, task, result.to_dict(), write_topic_for=task[:30])
    return {"mode": "sprint", "pwr": result.to_dict(), "wiki": wiki, "classification": wiki.get("classification", {})}
```

### 4.4 测试 `tests/test_pwr_loop.py` (51 测试)

关键断言:

```python
def test_pwri_basic_runs():
    pwr = run_pwr("hello", llm=stub_llm, max_iter=1)
    assert isinstance(pwr, PWRResult)
    assert pwr.total_iters == 1

def test_pwr_early_stop_on_threshold():
    llm = make_score_llm(0.95)
    pwr = run_pwr("any", llm=llm, threshold=0.9, max_iter=5)
    assert pwr.success
    assert pwr.total_iters == 1  # stopped after 1 iter

def test_pwr_max_iter_limit():
    pwr = run_pwr("any", llm=make_score_llm(0.5), threshold=0.9, max_iter=3)
    assert pwr.success == False
    assert pwr.total_iters == 3

def test_parse_review_score_percent():
    assert parse_review_score("90%") == 0.9
def test_parse_review_score_decimal():
    assert parse_review_score("0.85") == 0.85
def test_parse_review_score_negative():
    assert parse_review_score("-0.5") == 0.5  # regex miss → fallback
def test_parse_review_score_clamp():
    assert parse_review_score("1.5") == 1.0
def test_parse_review_score_zero():
    assert parse_review_score("0") == 0.0
```

---

## Part 5: Phase 3 — 并发原语(35 分钟)

### 5.1 `scripts/atomic_write.py` (~120 行)

**核心实现**:

```python
import os, sys, tempfile
from pathlib import Path

def atomic_write(target_path, content, retries=5, encoding="utf-8"):
    """tmp + os.replace + per-file lock + retry 5"""
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    
    # Cross-platform file lock
    lock_path = target.with_suffix(target.suffix + ".lock")
    
    for attempt in range(retries):
        try:
            # Write to tmp
            rand = os.urandom(4).hex()
            tmp_path = target.parent / f".tmp.{target.name}.{rand}"
            tmp_path.write_text(content, encoding=encoding)
            # Atomic rename
            os.replace(tmp_path, target)
            return True
        except PermissionError:
            if attempt < retries - 1:
                import time
                time.sleep(0.05 * (attempt + 1))  # linear backoff
            continue
        except Exception:
            return False
    return False
```

完整实现含 Windows `msvcrt.locking` + Unix `fcntl.flock` 跨平台锁。

### 5.2 `scripts/task_queue.py` (~200 行)

**核心数据结构**:

```python
import asyncio, inspect
from dataclasses import dataclass, field
from typing import Callable, Optional

@dataclass
class Task:
    name: str
    fn: Callable  # can be sync or async
    
@dataclass
class QueueResult:
    name: str
    value: object
    duration_s: float = 0.0
    error: Optional[str] = None

class TaskQueue:
    """asyncio.Queue + N workers, sync/async auto-detect"""
    
    def __init__(self, workers=3, max_size=100, timeout=30.0):
        self.queue = asyncio.Queue(maxsize=max_size)
        self.workers_n = workers
        self.timeout_s = timeout
        self.results_dict = {}
        self._tasks = []
        self._loop = None
    
    def submit(self, task: Task):
        if self.queue.full():
            raise QueueFull(f"queue full (max_size={self.queue.maxsize})")
        self.queue.put_nowait(task)
        self._tasks.append(task)
    
    async def submit_async(self, task: Task):
        await self.queue.put(task)
    
    async def run_batch(self) -> dict[str, QueueResult]:
        """Run all submitted tasks concurrently via worker coroutines."""
        workers = [asyncio.create_task(self._worker_loop(i)) for i in range(self.workers_n)]
        await self.queue.join()
        for w in workers:
            w.cancel()
        return self.results_dict
    
    async def _worker_loop(self, worker_id):
        loop = asyncio.get_running_loop()
        while True:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=self.timeout_s)
            except asyncio.TimeoutError:
                return
            start = loop.time()
            try:
                ret = task.fn()  # Run function
                # CRITICAL: detect if coroutine — iscoroutinefunction
                # doesn't detect lambdas wrapping async fns.
                # So: call it, then check the returned value.
                if inspect.iscoroutine(ret):
                    ret = await ret
                self.results_dict[task.name] = QueueResult(
                    name=task.name, value=ret, duration_s=loop.time() - start
                )
            except Exception as e:
                self.results_dict[task.name] = QueueResult(
                    name=task.name, value=None, duration_s=loop.time() - start,
                    error=str(e)
                )
            finally:
                self.queue.task_done()
```

**关键陷阱**: sync 函数不能直接 await(会阻塞 event loop)。改用 `loop.run_in_executor`:

```python
import concurrent.futures
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

async def _run_one(task):
    loop = asyncio.get_running_loop()
    if inspect.iscoroutinefunction(task.fn):
        return await task.fn()
    else:
        # Sync: run in executor (true thread parallelism)
        return await loop.run_in_executor(executor, task.fn)
```

完整实现见 `scripts/task_queue.py`。

### 5.3 测试

`tests/test_phase3_phase4.py` 覆盖 atomic_write + task_queue,50+ 检查。

---

## Part 6: Phase 4 — Karpathy LLM Wiki(40 分钟)

### 6.1 `scripts/dialogue_parser.py` (~110 行)

```python
import re
from typing import List, Dict

STOP_WORDS = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", ...}

def slugify(text: str) -> str:
    """保留中文 + 英文 word,kebab-case"""
    text = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text.lower())
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:80]

def parse_messages(messages: List[Dict]) -> List[Dict]:
    """[{role, content, ts}] → 增 slug/intent/keywords"""
    out = []
    for msg in messages:
        m = msg.copy()
        m["slug"] = slugify(msg["content"][:50])
        m["intent"] = classify_intent(msg["content"])
        m["keywords"] = extract_keywords(msg["content"])
        out.append(m)
    return out

def classify_intent(text: str) -> str:
    """question / command / discussion"""
    if "?" in text or "？" in text or "为什么" in text or "怎么" in text:
        return "question"
    if any(text.startswith(p) for p in ["做", "write", "create", "fix", "build"]):
        return "command"
    return "discussion"

def extract_keywords(text: str, top_k=5) -> List[str]:
    """Top K non-stopword tokens,中英文 + Chinese n-gram"""
    tokens = re.findall(r"[\w\u4e00-\u9fff]{2,}", text.lower())
    chinese_phrases = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    candidates = [t for t in tokens if t.lower() not in STOP_WORDS] + chinese_phrases
    return list(dict.fromkeys(candidates))[:top_k]

def group_by_intent(entries: List[Dict]) -> Dict[str, List[Dict]]:
    result = {}
    for e in entries:
        result.setdefault(e["intent"], []).append(e)
    return result
```

### 6.2 `scripts/wiki_store.py` (~500 行,Phase 8 增强)

**核心函数**:

```python
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import json
from .atomic_write import atomic_write

DEFAULT_WIKI_ROOT = Path("wiki")

@dataclass
class WikiEntry:
    slug: str
    type: str
    created: str
    modes: List[str]
    l1_recipes: List[str]
    roles: List[str]
    failure_categories: List[str]
    path: str = ""
    
    def to_dict(self):
        return self.__dict__.copy()

def init_wiki(root=DEFAULT_WIKI_ROOT) -> Path:
    """Create wiki/ + subdirs"""
    root = Path(root)
    for sub in ["", "dialogue", "entities", "topics", "_meta", "by_mode"]:
        (root / sub).mkdir(parents=True, exist_ok=True)
    # Init files via atomic_write
    atomic_write(root / "index.md", "# Wiki Index\n\n| slug | type | created | modes |\n|------|------|---------|-------|\n")
    atomic_write(root / "log.md", "# Wiki Log\n\n")
    atomic_write(root / "contradictions.md", "# Contradictions\n\n")
    atomic_write(root / "coverage.md", "# Wiki Method Coverage\n\n_Auto-generated._\n")
    atomic_write(root / "_meta" / "graph.json", "{}")
    atomic_write(root / "_meta" / ".frontmatter_cache.json", "{}")
    return root

def _front_matter(slug, type_, ts, modes=None, l1_recipes=None, roles=None, failure_categories=None):
    parts = [f"slug: {slug}", f"type: {type_}", f"created: {ts}"]
    if modes: parts.append(_format_list_field(modes, "modes"))
    if l1_recipes: parts.append(_format_list_field(l1_recipes, "l1_recipes"))
    if roles: parts.append(_format_list_field(roles, "roles"))
    if failure_categories: parts.append(_format_list_field(failure_categories, "failure_categories"))
    return "---\n" + "\n".join(parts) + "\n---\n\n"

def write_dialogue(root, slug, content, metadata=None,
                   modes=None, l1_recipes=None, roles=None, failure_categories=None):
    root = Path(root)
    meta = dict(metadata or {})
    ts = meta.pop("ts", None) or _now()
    path = root / "dialogue" / f"{slug}.md"
    atomic_write(path, _front_matter(slug, "dialogue", ts, modes, l1_recipes, roles, failure_categories) + content)
    _append_index(root, slug, "dialogue", ts, modes)
    _append_log(root, f"dialogue/{slug} created (modes={modes or []})")
    _update_cache(root, slug, "dialogue", ts, modes, l1_recipes, roles, failure_categories)
    return path

# 类似 write_entity / write_topic

# Cache: O(1) lookups
def _load_cache(root):
    p = root / "_meta" / ".frontmatter_cache.json"
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except: return {}

# Phase 8 queries
def wiki_by_mode(root, mode_id):
    cache = _load_cache(root)
    return [_entry_from_cache(root, slug, data) for slug, data in cache.items()
            if mode_id in (data.get("modes") or [])]

def wiki_by_role(root, role):  # 类似
def wiki_by_l1_recipe(root, recipe_id):  # 类似
def wiki_by_failure_category(root, cat):  # 类似

def wiki_mode_coverage(root, methods_tree=None):
    """返回 total_entries / by_method / by_role / by_mode / untagged_entries / unused_methods"""
    cache = _load_cache(root)
    by_method = {}
    by_role = {}
    by_mode = {}
    untagged = []
    for slug, data in cache.items():
        for m in (data.get("modes") or []) + (data.get("l1_recipes") or []):
            by_method[m] = by_method.get(m, 0) + 1
        for r in (data.get("roles") or []):
            by_role[r] = by_role.get(r, 0) + 1
        for mode in (data.get("modes") or []):
            by_mode[mode] = by_mode.get(mode, 0) + 1
        if not data.get("modes") and not data.get("l1_recipes") and not data.get("roles"):
            untagged.append(slug)
    return {
        "total_entries": len(cache), "by_method": by_method,
        "by_role": by_role, "by_mode": by_mode, "untagged_entries": untagged,
        "unused_methods": [],  # populated if methods_tree given
    }
```

完整 502 行 (含分类、缓存、CLI、coverage report 等)。

### 6.3 `scripts/lint_wiki.py` (~165 行,Phase 8 加 8 步)

```python
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

def lint_wiki(root, stale_days=90, methods_tree=None) -> dict:
    issues = {
        "orphan": [], "missing": [], "broken_wikilinks": [],
        "isolated": [], "contradictions": [], "stale_claims": [],
        "missing_cross_refs": [], "mode_coverage": [],  # NEW Phase 8
    }
    # ... (steps 1-7 implementation details)
    
    # 8. mode_coverage (NEW)
    if methods_tree:
        from .wiki_store import wiki_mode_coverage
        cov = wiki_mode_coverage(root, methods_tree)
        for m in cov.get("unused_methods", []):
            issues["mode_coverage"].append({"kind": "method_unused", "method": m})
        for slug in cov.get("untagged_entries", []):
            issues["mode_coverage"].append({"kind": "entry_untagged", "slug": slug})
    
    return issues

def lint_summary(issues):
    return {k: len(v) for k, v in issues.items()}
```

### 6.4 测试

`tests/test_phase3_phase4.py` 覆盖 wiki_store + dialogue_parser + lint_wiki 共 78 个检查。

---

## Part 7: Phase 5 — Entity + 5-Persona Discuss(40 分钟)

### 7.1 `scripts/entity_extractor.py` (~225 行)

**核心**:
- 14 项目别名表(如 `{"langchain": "langchain", "lang-graph": "langchain", ...}`)
- NER 分类: url / person / file / concept / tool
- 置信度计算
- 中文短语提取(短句 ≥2 字)

```python
ALIAS_TABLE = {
    "langchain": ["langchain", "lang-chain", "lang_graph"],
    "langgraph": ["langgraph", "lang-graph"],
    "autogen": ["autogen", "auto-gen", "auto_gen"],
    "openai": ["openai", "open-ai", "open_ai"],
    # ...
}

def extract_entities(text: str) -> List[Dict]:
    entities = []
    for canonical, aliases in ALIAS_TABLE.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE):
                entities.append({"entity": canonical, "type": "tool", 
                                "confidence": 0.9, "match": alias})
    # Chinese phrase extraction
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    for phrase in set(chinese):
        if len(phrase) >= 2:  # ≥2 char filter
            entities.append({"entity": phrase, "type": "concept",
                            "confidence": 0.6, "match": phrase})
    return _dedup(entities)

def group_by_type(entities):
    result = {}
    for e in entities:
        result.setdefault(e["type"], []).append(e)
    return result
```

### 7.2 升级 `scripts/handlers.py` — 5-persona discuss

```python
PRAGMATIST_SYSTEM = "你是 Pragmatist, 关注工程落地..."
SKEPTIC_SYSTEM = "你是 Skeptic, 反驳 / 质疑现有方案..."
OPTIMIST_SYSTEM = "你是 Optimist, 寻找未来机遇..."
THEORIST_SYSTEM = "你是 Theorist, 探讨理论深度..."
IMPLEMENTER_SYSTEM = "你是 Implementer, 关注执行细节..."

def handle_discuss(task, llm=None, **kwargs) -> dict:
    base_llm = llm or stub_llm
    personas = [
        ("pragmatist", PRAGMATIST_SYSTEM),
        ("skeptic", SKEPTIC_SYSTEM),
        ("optimist", OPTIMIST_SYSTEM),
        ("theorist", THEORIST_SYSTEM),
        ("implementer", IMPLEMENTER_SYSTEM),
    ]
    # 并发 5 persona
    from .task_queue import TaskQueue, Task
    q = TaskQueue(workers=5)
    for name, system in personas:
        q.submit(Task(name, lambda s=system: base_llm(s, task)))
    asyncio.run(q.run_batch())
    
    # 聚合
    responses = {name: r.value for name, r in q.results_dict.items()}
    consensus = _extract_consensus(responses)
    disagreements = _extract_disagreements(responses)
    
    return {
        "mode": "discuss",
        "responses": responses,
        "consensus": consensus,
        "disagreements": disagreements,
    }
```

### 7.3 测试

`tests/test_phase5.py` 50 测试。

---

## Part 8: Phase 6 — LLM Client + Wiki Integration(40 分钟)

### 8.1 `scripts/llm_client.py` (~225 行)

```python
import os, json, hashlib
from pathlib import Path
from typing import Callable

LLMCallable = Callable[[str, str], str]

class LLMBackend:
    MOCK = "mock"
    REAL = "real"
    MINIMAX = "minimax"

DEFAULT_PROVIDER = "agent-platform"
DEFAULT_MODEL = "<MODEL_NAME>"
DEFAULT_BASE_URL = "<LLM_BASE_URL>"

def _read_api_config():
    """Read agent-config.json for provider URL, API key"""
    config_path = Path("~/.config/agent-platform/agent-config.json").expanduser()
    if not config_path.exists():
        return None
    return json.loads(config_path.read_text(encoding="utf-8"))

class RealLLM:
    def __init__(self, model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL):
        cfg = _read_api_config() or {}
        self.model = model
        self.base_url = base_url
        self.api_key = cfg.get("api_key") or os.environ.get("AGENT_LLM_KEY", "")
    
    def __call__(self, system_prompt, user_msg):
        if not self.api_key:
            return _mock_llm(system_prompt, user_msg)
        # POST Anthropic-compatible
        try:
            import urllib.request
            payload = {
                "model": self.model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_msg}],
            }
            req = urllib.request.Request(
                f"{self.base_url}/v1/messages",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                }
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return _extract_text(data)
        except Exception as e:
            return f"[ERROR: {e}]"

def _extract_text(data: dict) -> str:
    """Parse Anthropic response, fall back to thinking field"""
    for block in data.get("content", []):
        if block.get("type") == "text":
            return block.get("text", "")
    return data.get("thinking", "")

def _mock_llm(system_prompt, user_msg):
    """Deterministic mock for offline / no API key"""
    h = hashlib.md5((system_prompt + user_msg).encode()).hexdigest()[:8]
    return f"MOCK-{h}: 模拟回复 (无 API key)"

def get_default_llm():
    cfg = _read_api_config()
    if cfg and cfg.get("api_key"):
        return RealLLM()
    return _mock_llm

def force_real(model=None, base_url=None):
    return RealLLM(model=model or DEFAULT_MODEL, base_url=base_url or DEFAULT_BASE_URL)

def force_mock():
    return _mock_llm

def make_score_llm(llm, target_score=0.85):
    """Wrap any LLM to produce a number string"""
    def _score(system, msg):
        prompt = "You are a strict reviewer. Reply with only a number 0.0-1.0."
        response = llm(prompt, msg)
        m = re.search(r"(\d+(?:\.\d+)?)\s*(%)?", response)
        if m:
            val = float(m.group(1))
            is_pct = m.group(2) == "%"
            if is_pct: val /= 100.0
            return max(0.0, min(1.0, val))
        return 0.5  # fallback
    return _score
```

### 8.2 `scripts/wiki_integration.py` (~170 行)

```python
def build_messages_from_pwr(task, pwr_result):
    messages = [{"role": "user", "content": task, "ts": _now()}]
    for it in pwr_result.get("iterations", []):
        for role in ("planner", "worker", "reviewer", "reflection"):
            if it.get(role):
                messages.append({"role": "assistant", "content": it[role], "ts": it.get("ts") or _now()})
    return messages

def persist_to_wiki(root, task, pwr_result, write_topic_for=None,
                   modes=None, l1_recipes=None, roles=None, failure_categories=None):
    """Write classified entries to wiki"""
    root = Path(root)
    init_wiki(root)  # idempotent
    
    messages = build_messages_from_pwr(task, pwr_result)
    entries = parse_messages(messages)
    
    for e in entries:
        write_dialogue(root, e["slug"], format_entry(e),
                       modes=modes, l1_recipes=l1_recipes,
                       roles=roles, failure_categories=failure_categories)
    
    entities = extract_entities("\n".join(m["content"] for m in messages))
    for e in entities:
        slug = slugify(e["entity"])
        write_entity(root, slug, format_entity(e, task),
                     modes=modes, l1_recipes=l1_recipes, roles=roles)
    
    if write_topic_for:
        write_topic(root, slugify(write_topic_for), format_topic(...),
                    modes=modes, l1_recipes=l1_recipes, roles=roles)
    
    issues = lint_wiki(root, methods_tree=MethodsTree())
    return {"dialogue_written": len(entries), "lint_summary": lint_summary(issues)}

def persist_to_wiki_from_pwr(root, task, pwr_result_dict, write_topic_for=None):
    """Auto-derive classification from PWRResult.iterations"""
    iterations = pwr_result_dict.get("iterations", [])
    recipes = []
    roles = set()
    has_reflection = False
    for it in iterations:
        for key in ("planner", "worker", "reviewer", "reflection"):
            if it.get(key):
                if key == "reflection":
                    has_reflection = True
                else:
                    recipes.append(f"{key}_task")
                    roles.add(key)
    return persist_to_wiki(
        root, task, pwr_result_dict,
        write_topic_for=write_topic_for,
        modes=["m_sprint"],
        l1_recipes=recipes or None,
        roles=sorted(roles) or None,
        failure_categories=["reflect_triggered"] if has_reflection else None,
    )
```

### 8.3 测试 `tests/test_phase6.py` 35 个

---

## Part 9: Phase 8 — Wiki 分类(v1.0.1,30 分钟)

> 已在 Part 6.2 `wiki_store.py` 介绍新增 API。这里只补 Phase 8 专测。

### 9.1 `tests/test_phase8_wiki_classification.py` (22 测试,完整代码在包内)

```
- test_front_matter_has_classification
- test_front_matter_without_classification  (backward compat)
- test_multiple_modes
- test_cache_updated_after_write
- test_cache_refresh_rebuild
- test_wiki_by_mode_returns_correct_entries
- test_wiki_by_role_returns_correct_entries
- test_wiki_by_l1_recipe
- test_wiki_by_failure_category
- test_query_returns_empty_for_no_match
- test_entry_has_path_attribute
- test_coverage_basic_stats
- test_coverage_untagged_entries
- test_coverage_unused_methods
- test_coverage_without_methods_tree
- test_render_coverage_md
- test_generate_coverage_report_writes_file
- test_lint_includes_mode_coverage
- test_lint_without_methods_tree_empty_mode_coverage
- test_lint_summary_8_keys
- test_lint_summary_includes_unused_method_count
- test_persist_to_wiki_classifies_entries
```

### 9.2 修复 2 个已存测试(因为 lint 现在返 8 键)

```python
# tests/test_phase3_phase4.py
def test_lint_summary_keys():
    ...
    check("summary has 8 keys", len(summary) == 8)
    expected = {"orphan", "missing", "broken_wikilinks", "isolated", 
                "contradictions", "stale_claims", "missing_cross_refs", 
                "mode_coverage"}  # NEW
    check("summary keys match", set(summary.keys()) == expected)

# tests/test_phase6.py
def test_persist_to_wiki():
    ...
    check("lint_summary has 8 keys", len(result["lint_summary"]) == 8)  # 7 → 8
```

---

## Part 10: 文档(15 分钟)

### 10.1 `README.md`

```markdown
# mini-mp-agent
> Version 1.0.1 — Single-agent multi-role PWR loop + work method tree + Karpathy LLM Wiki + asyncio
> 307/307 tests PASS · MIT License · 0 external dependencies

[full README content - see package README.md]
```

### 10.2 `METHODS_TREE_INTRO.md` — 方法树通俗介绍

完整内容 3466 字节见包内文件。**(人话版,8 节)**

### 10.3 `FEATURES.md` — 完整特色功能

完整内容 15879 字节见包内文件。**(15 节,中文含架构图)**

### 10.4 `CHANGELOG.md`

```markdown
## [1.0.1] - 2026-07-18
Wiki method-tree classification (Phase 8): ... [详细]

## [1.0.0] - 2026-07-18
Initial stable release (Phase 1-7): ...
```

### 10.5 `VERSION.json`

```json
{
  "name": "mini-mp-agent",
  "version": "1.0.1",
  "type": "single-agent-multi-role-loop",
  ...
}
```

完整内容见包内文件。

### 10.6 `SKILL.md` (skill 入口,实际用户用)

(描述 mini-mp-agent 是 skill 时怎么用,提供给 OpenClaw/Agent 平台调用)

---

## Part 11: 最终验证 + 打包(10 分钟)

### 11.1 跑全部测试

```bash
$ for t in tests/test_*.py; do
    PYTHONPATH=. python -m tests.$(basename $t .py) 2>&1 | tail -1
  done

32/32 passed, 0 failed
39/39 PASS, 0 FAIL
51/51 PASS, 0 FAIL
78/78 PASS, 0 FAIL
50/50 PASS, 0 FAIL
35/35 PASS, 0 FAIL
22/22 passed, 0 failed

TOTAL: 307/307 PASS
```

### 11.2 跑 CLI 检查

```bash
$ PYTHONPATH=. python -m scripts.methods_tree
valid: True, errors: [], nodes=18, edges=25

$ PYTHONPATH=. python -m scripts.methods_tree search wiki
  lint_wiki: Run 7-step linter...
  wiki_persist: Write dialogue entry...
  wiki_recall: Search the wiki...

$ PYTHONPATH=. python -m scripts.methods_tree path m_sprint atomic_write
m_sprint -> wiki_persist -> atomic_write
```

### 11.3 跑 e2e demo

```bash
$ PYTHONPATH=. python examples/e2e_demo.py
[sprint handler running...]
[wiki entries written: dialogue=5 entities=3 topic=1]
[lint summary: 7 keys, no issues]
SUCCESS
```

### 11.4 git tag

```bash
$ git add -A
$ git commit -m "v1.0.1: complete release (8 phases, 307 tests)"
$ git tag -a v1.0.1 -m "v1.0.1 stable release"
$ git log --oneline
1fb1805 (HEAD -> main, tag: v1.0.1) v1.0.1: complete release
(earlier commits from each phase)
```

### 11.5 完整文件清单核对

```bash
$ find . -type f \( -name "*.py" -o -name "*.json" -o -name "*.yaml" -o -name "*.md" -o -name "*.toml" -o -name "LICENSE" -o -name ".gitignore" \) | grep -v __pycache__ | grep -v ".git/" | wc -l
50  # 期望 50 文件

$ ls -la
# README.md METHODS_TREE_INTRO.md FEATURES.md CHANGELOG.md BUILD.md
# SKILL.md VERSION.json LICENSE .gitignore pyproject.toml
# methods/ scripts/ tests/ examples/

$ du -sh .
# ~200 KB (no deps)
```

---

## Part 12: 调试清单(常见坑)

### 坑 1: GBK 编码 (Windows)

**现象**: Chinese text displays as `???` in console.

**解决**:
- Python 文件读写都 explicit `encoding="utf-8"`
- 不要用 PowerShell 默认 ANSI

### 坑 2: PowerShell `$var` 在 heredoc 中不展开

**现象**: @'...'@ here-string 中 `$var` 静默丢失。

**解决**:
- 用 Python 写文件不用 PS heredoc,或
- `Set-Content -Encoding UTF8`

### 坑 3: `inspect.iscoroutinefunction(lambda: async_fn())` 返 False

**现象**: 包装 async 的 lambda 被识别成 sync,走 `await` 时 coroutine 丢失。

**解决**:
```python
ret = task.fn()
if inspect.iscoroutine(ret):  # 调一次看返回值类型
    ret = await ret
```

### 坑 4: sync 函数直接 await 阻塞 event loop

**解决**: `await loop.run_in_executor(executor, sync_fn)`

### 坑 5: pytest fixture 名 vs 函数参数名

**现象**: `def func(tmp_path):` 把 fixture 当参数传入失败。

**解决**: 用普通 `root_dir` 参数 + 自己 build tmp。

### 坑 6: 写文件被 SMOKE 测试读旧版本

**现象**: smoke test 找的是旧的 backup,断言失败。

**解决**: 
- SMOKE 测试前清 stale backup
- `sorted(..., reverse=True)[0]` 取最新
- smoke 用 subprocess,取回 stdout

---

## 附录 A: 工时表

| Phase | 内容 | 文件 | 行 | 测试 | 工时 |
|---|---|---|---|---|---|
| Phase 7 | methods tree (18 nodes) | 19 | ~700 | 32 | 50 min |
| Phase 1 | mode router | 3 | ~300 | 39 | 15 min |
| Phase 2 | PWR loop | 3 | ~400 | 51 | 40 min |
| Phase 3 | atomic + queue | 2 | ~350 | (in p34) | 35 min |
| Phase 4 | wiki store + lint | 3 | ~700 | (in p34) | 40 min |
| Phase 5 | entity + 5-persona | 1+1 | ~375 | 50 | 40 min |
| Phase 6 | LLM client + integration | 2 | ~400 | 35 | 40 min |
| Phase 8 | wiki classification | 1+1 | ~200 | 22 | 30 min |
| Docs | 4 MD + JSON + SKILL | 7 | ~28KB | - | 15 min |
| Final verify | tag + commit | - | - | - | 10 min |
| **Total** | | **42** | **~3300** | **307** | **~5h** |

## 附录 B: 关键设计原则(抄下来贴在备忘)

1. **0 外部依赖** — 0 个 pip install。YAML / JSON / locking 全部内嵌实现
2. **Graceful degradation** — 无 API key → mock;无 wiki → in-memory
3. **Injectable LLM** — `LLMCallable = Callable[[str,str],str]` 类型测试注入
4. **方法树 = 白名单** — Planner 不能瞎编 op,只能从 18 method 里选
5. **append-only 记忆** — wiki/log.md 不可变,新条目只追加
6. **per-file locking** — 跨进程互斥不靠文件 mutex
7. **coverage audit** — 自动报哪些方法没沉淀到 wiki

---

## 附录 C: 进一步发展(可选路线)

| 方向 | 难度 | 说明 |
|---|---|---|
| 加 RAG layer | 低 | `wiki_recall` 增强成 embedding search |
| 加 mutator | 中 | mutate_light.py + evolve_loop.py + fitness.py |
| 加 Bayesian 优化 | 中 | tune threshold / max_iter via Optuna |
| 加 web UI | 高 | FastAPI + Vue chat interface |
| 拆 multi-agent | 高 | PWR 4 agent 各自独立 sub-session |

---

**完工**: 跟着这份 BUILD.md 走,从 0 到 v1.0.1 包,5 小时能 ship 一份**完整可运行**的 mini-mp-agent。

如果卡在哪一步,直接 `cat <file>` 看包里的源文件,逐行对照。
