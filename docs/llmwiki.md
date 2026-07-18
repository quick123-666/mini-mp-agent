# LLM Wiki — 自动沉淀 session 知识

> **设计原则**：每次对话站在前次肩膀上。Session 内容 LCM 已能字面搜，
> LLM Wiki 的增量价值是**结构化沉淀**（决策/方法/教训/关联），让
> `lcm_grep` 搜不到的问句能命中。

## 形态

```
llmwiki/
├── topics/<session-id>.md    # 每 session 1 个主题页（auto-ingest）
├── index.md                    # 按时间倒序的全量列表
├── timeline.md                 # 1 行摘要 / 主题
├── by-project/<name>.md        # 按项目聚合
├── _state.json                 # 增量解析状态（atomic write）
└── _lint.log                   # 健康检查历史
```

**没有人手写的 wiki**——所有页面由 cron 3h 跑自动生成。

## 4 路 Ingest 触发

| 触发源 | 频率 | 抓什么 |
|--------|------|--------|
| `cron-full` | 每天 23:00（wrapper 内判断 hour==23） | 扫所有 session JSONL，mtime 增量 |
| `mem` | 每 3h | 扫 MEMORY.md 段落级 delta（`last_line` 状态） |
| `session` | 手动 | 单个 session-id 立即 ingest |
| `lint` | 每 3h | 孤岛/过时/矛盾检测（不写新页面） |

**入口统一**：`scripts/wiki_ingest.py --source <src>`  
**Cron wrapper**：`scripts/cron_llmwiki.sh`（每 3h 跑，hour==23 加跑 cron-full）

## 主题页结构（不极简）

```markdown
---
slug: <session-id>-<slug>
type: topic
created: 2026-07-18T14:30:00
session: 416641e6-ccf1-4ee0-ad84-a8c0be119539
duration_min: 18
messages: 6
tags: [crontab, schtasks, system-auth, ...]
decisions: [D-160, D-161]
methods: [M-SchtasksXML-001]
projects: [openclaw-manager, ai-os]
llm_summary: |
  200-500 字 LLM 摘要
---

## 关键工具调用时间线
## 决策 & 方法链接
## 关联项目 & 主题
## 实体标签（3-4 字中文 + 项目术语）
## 原文索引
```

## 查询路径

1. **想"上次为什么这么干"** → `lcm_grep "schtasks SYSTEM 身份"`，命中 topic 摘要句
2. **想"项目 X 改过几次"** → 打开 `llmwiki/by-project/X.md`
3. **想"最近所有主题"** → 打开 `llmwiki/timeline.md`

## Entity 处理（不写独立文件）

- `_match_chinese_phrases`：2-字 + 噪声降 0.3，3-4 字保 0.5
- entity 写进 topic front-matter `tags:` 字段，**不**生成 565 个散文件
- 旧版 `write_entity` 保留代码但不再被 `wiki_ingest.py` 调用

## 健康检查（cron 3h 跑）

`scripts/wiki_lint.py` 三项：

1. **orphans** — 没有任何入链的主题页（LCM 搜不到）
2. **stale** — >90 天无入链的主题页
3. **contradictions** — 同一 D-NNN/M-XXX 在多个主题里被不同描述引用

输出 `_lint.log`（JSON Lines，每行一次检查摘要）。

## 手动触发示例

```bash
# 全量（mock LLM，不耗 API）
PYTHONPATH=. python scripts/wiki_ingest.py --wiki-root ./llmwiki --source cron-full --mock --limit 5

# 单 session（真 LLM）
PYTHONPATH=. python scripts/wiki_ingest.py --wiki-root ./llmwiki --source session --session-id 416641e6-... 

# Lint
PYTHONPATH=. python scripts/wiki_lint.py --wiki-root ./llmwiki --stale-days 90

# 完整 cron cycle
bash scripts/cron_llmwiki.sh
```

## OpenClaw cron 配置

```python
cron.add(name="llmwiki-ingest-3h",
         schedule={"kind": "every", "everyMs": 3 * 60 * 60 * 1000},
         sessionTarget="isolated",
         payload={"kind": "agentTurn",
                  "message": "bash scripts/cron_llmwiki.sh"},
         failureAlert={"after": 2, "cooldownMs": 3600000, ...})
```

## 演进历史

- v1.0.1 (`7e23778`)：旧版 `wiki_from_session.py` 写 565 entity flood
- v1.1.0（本次）：砍 entity 散文件，改 1 session 1 topic，4 路 Ingest
