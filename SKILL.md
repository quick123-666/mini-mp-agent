# mini-mp-agent

> **v7.0.0-skeleton** — Mini-Meta-Planner: 4 角色 PWR Loop + mp bridge + Karpathy wiki + 高并发
> 
> 注册时间: 2026-07-17 | 作者: user + AgentPlatform | 状态: 骨架 (后续 ship 完整代码)

## 一句话

mini-mp = **4 内置角色 (Planner / Worker / Reviewer / Reflector) + 5 mode 派发 (qa/task/discuss/auto/sprint) + PWR Loop 状态机 + mp bridge (复用 mp 7 method, 只读) + Karpathy LLM Wiki 模式对话管理 + 3 worker 并发 (TaskQueue + FileLock per-file + atomic_write retry)**, mp 13/13 核心功能全部过来。

## 触发词

- "用 mini-mp 帮我..." / "mini-mp: <任务>" / "/mini-mp <任务>"
- "PWR 一下..." / "Plan-Work-Review..."
- "4 角色思考..." / "反射一下..."

## 5 mode (mode_router 派发)

| mode | 行为 | 耗时 | token |
|------|------|------|-------|
| qa | 1 次 LLM 直答 | < 2s | ~500 |
| task | PWR max_iter=1 | ~10s | ~1500 |
| discuss | 5 persona | ~20s | ~3000 |
| auto | 完整 PWR + Reflect | ~30s | ~2500 (默认) |
| sprint | auto + 跨 session 召回 | ~40s | ~3500 |

## 4 角色 (PWR Loop)

```
Planner → Worker → Reviewer → (if fail) Reflector → replan (max 3 iter)
```

- **Planner**: 拆 task + 调 mp_methods_bridge (sense → match → build 3 步)
- **Worker**: 执行 plan, 标记 parallel=True 的 op 用 asyncio.gather 并行
- **Reviewer**: 4 类 check (syntax/length/relevance) + score 0-1
- **Reflector**: 算 fingerprint + 14 类分类 + 同 fp ≥ 3 → 自动提议 recipe 写 yaml

## 高并发 (v7)

- **L0 TaskQueue**: max_size=100, 3 workers (asyncio.Queue + WorkerPool)
- **L2 Worker op**: RECIPES 标 parallel=True, asyncio.gather 并行
- **L1 atomic_write**: msvcrt.locking per-file FileLock + .tmp + os.replace + retry 5

## Wiki (Karpathy LLM 模式)

3 类对话管理:
- `dialogue/` — 每条对话 entry
- `entities/` — 主题/概念/项目实体页
- `topics/` — 跨多条对话的综述

7 步 lint: orphan / missing / broken_wikilinks / isolated / contradictions / stale_claims / missing_cross_refs

## 文件结构 (设计)

```
mini-mp-agent/
├── loop/                 跨角色编排 (pwr_loop, mode_router, task_queue)
├── tools/                共享工具 (atomic_write + FileLock, fingerprint)
├── agents/               4 角色实现 (Planner/Worker/Reviewer/Reflector)
├── wiki/                 Karpathy 模式对话管理
├── scripts/tools/        wiki_store / dialogue_parser / entity_extractor / lint_wiki
├── memory/               持久化 (log.jsonl / failure_index.jsonl / proposed_recipe.yaml)
└── tests/                32+5 测试 (含高并发)
```

## 当前状态 (ship 时序)

- [x] v7 完整设计文档 (`~/Desktop/mini-mp-v7-dev-doc/`)
- [x] AgentPlatform agent 注册 (mini-mp 单 agent)
- [ ] 完整代码 ship (后续 phase 1-5 + v7 并发)

## 跟 mp 的关系

| mp | mini-mp |
|----|---------|
| 6 team + 8 sub-agent | 1 agent + 4 内置角色 |
| 跨 session 状态 | 同 session 循环为主 |
| 91 D-NNN 决策 | 13 D-NNN 关键决策 |
| 13 recipe 全 versioned | 16 内置能力 (4×4) |
| 7 method 索引 | bridge 复用 7 method (只读) |
| 单一工作流 | 5 mode 派发 |

## 命令

```bash
# 测试 mini-mp agent 是否注册成功
# 在 AgentPlatform 中说: "用 mini-mp 解释 mp 是什么"
# 或 sessions_send sessionKey="agent:mini-mp:main" "..."
```

## 参考

- 设计文档: `<USER_HOME>\Desktop\mini-mp-v7-dev-doc\README.md` + `02-tools-wiki-memory.md`
- 源 mp: `~/.config/agent-platform/workspace/skills/meta-planner/` (v1.1.2, 91 D-NNN)
