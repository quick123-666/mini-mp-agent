# mini-mp-agent MD 索引 + 读优先级

> **生成时间**: 2026-07-20 13:36 (Asia/Shanghai)
> **总业务 MD 数**: 49 (排除 _cron_wiki/ _seed_wiki/ examples/ 等历史/演示目录)
> **生成方法**: M-MDIndex-001 (D-MDIndex-001, 2026-07-20 13:36 ship)
> **维护原则**: 任何文件新增/删除, 同步更新本索引 + MEMORY.md L0 段必读规则

## 读优先级 (L0 ~ L4)

| 优先级 | 触发 | 文件 | 强制力 |
|---:|---|---|---|
| **#1 L0** | 任何任务 | `MEMORY.md` (本项目) | **30 秒内必读** (RULE 入口) |
| **#2 L0** | 任何任务 | `MD_INDEX.md` (本文件) | **30 秒内必读** (RULE-MDIndex-013) |
| #3 L0 | L0 触发时联动 | `MEMORY.md` ## L3 段 → `issues-tracking.md` (workspace 根) | 读最近 7 天 ISSUE |
| #4 L1 | 项目首读 | `README.md` / `README.zh-CN.md` / `SKILL.md` | 项目入口 |
| #5 L1 | 查方法论 | `METHODS_TREE_INTRO.md` / `FEATURES.md` | 18 方法树 + 5 模式 |
| #6 L2 | 发布/构建 | `BUILD.md` / `CHANGELOG.md` / `RELEASE_NOTES_v*.md` / `RELEASE_CHECKLIST.md` | ship 时查 |
| #7 L2 | 文档 | `docs/DEV_PLAN.md` (本地) / `docs/RELEASE_STATUS.md` (公开) / `docs/cron-jobs.md` / `docs/llmwiki.md` | 按需 |
| #8 L3 | LAAP 问题 | `wiki/by-project/laap.md` + `wiki/topics/2026-07-20-laap-aris-checkpoint.md` + `wiki/topics/2026-07-15-laap-aris.md` + LAAP 类 12 文件 | **mtime 倒序** |
| #9 L4 | Karpathy wiki 状态 | `wiki/index.md` / `wiki/timeline.md` / `wiki/log.md` / `wiki/coverage.md` / `llmwiki/*` | wiki lint 时查 |

## 全清单 (按类别分组, 按 mtime 倒序)

### A. 产品主入口 (9 个, git 跟踪)

| 文件 | 大小 | mtime | 功能/作用 |
|---|---:|---|---|
| `README.zh-CN.md` | 17.5KB | 07-18 15:23 | 中文项目入口 |
| `README.md` | 18.0KB | 07-18 15:21 | 英文项目入口, OpenClaw 注入 Project Context 时不带, 但用户手动查看必读 |
| `RELEASE_NOTES_v1.1.0.md` | 6.5KB | 07-18 15:21 | v1.1.0 release notes (含 wiki_recall) |
| `RELEASE_CHECKLIST.md` | 1.5KB | 07-18 11:12 | 发布前 checklist |
| `RELEASE_NOTES_v1.0.1.md` | 4.7KB | 07-18 11:10 | v1.0.1 release notes |
| `BUILD.md` | 49.6KB | 07-18 03:07 | 50KB, 完整构建文档 (历史), ship 时查 |
| `CHANGELOG.md` | 2.8KB | 07-18 03:07 | 版本变更日志 |
| `FEATURES.md` | 20.2KB | 07-18 03:03 | 20KB, 功能列表 (18 方法 + 5 模式 + Karpathy wiki) |
| `SKILL.md` | 3.6KB | 07-18 02:59 | Skill 触发词 + 路由说明, OpenClaw 注入, **首读**之一 |

### B. 方法论 (1 个)

| 文件 | 大小 | mtime | 功能/作用 |
|---|---:|---|---|
| `METHODS_TREE_INTRO.md` | 6.1KB | 07-18 02:59 | 18 方法树介绍, L1 查方法论必读 |

### C. LAAP 必读 (5 个, mtime 倒序 — 任何 LAAP 问题先 recall 这 N 个)

> **历史规则**: 旧"LAAP 必读 3 文件" → 已升级为"LAAP 必读 5 个" (RULE-MDIndex-013 联动, 2026-07-20 13:36 ship)
> **召回顺序**: 按 mtime 倒序, 最新优先

| 文件 | 大小 | mtime | 功能/作用 |
|---|---:|---|---|
| `wiki/topics/2026-07-20-answer-organization-mechanism.md` | 9.2KB | 07-20 11:47 | 9.4KB, 13:36 答案组织机制, 7 段意识流分析 |
| `wiki/by-project/laap.md` | 8.3KB | 07-20 11:39 | 8.5KB, LAAP 项目实体页, **结构化字段: 身份/路径/端口/状态/已知问题/启动命令** |
| `wiki/topics/2026-07-20-laap-aris-checkpoint.md` | 12.2KB | 07-20 11:39 | 12.4KB, 13:36 最新 checkpoint, 4 端口/P0/P1 全快照 |
| `wiki/by-project/(uncategorized).md` | 9.0KB | 07-18 23:02 | (LAAP 相关话题) |
| `wiki/topics/2026-07-15-laap-aris.md` | 121.0KB | 07-18 23:02 | 123.9KB, 历史 LAAP 大档案 (108KB+), 5+ D-NNN ship |



> ⚠️ **2026-07-20 13:43 净化**: LAAP 详细 (端口/代码位置/启动命令/P0) 已提取到 LAAP 项目自己的 wiki (`E:\新建文件夹\laap\wiki\2026-07-20-mini-mp-agent-context-extraction.md`). 本项目 wiki 留历史档案 + 净化声明, 不再更新 LAAP 详细. **新方法**: M-CrossProjectPurify-001

### D. 文档 (4 个)

| 文件 | 大小 | mtime | 功能/作用 |
|---|---:|---|---|
| `docs/RELEASE_STATUS.md` | 1.8KB | 07-20 12:54 | 公开粗表, commit+push, 比例 ≈ DEV_PLAN 30% |
| `docs/DEV_PLAN.md` | 6.1KB | 07-20 12:53 | 本地专用细表 (在 .gitignore), 全字段, ship 时填 |
| `docs/cron-jobs.md` | 4.2KB | 07-20 02:31 | OpenClaw cron 任务清单, M-SyncCronDoc-001 输出 |
| `docs/llmwiki.md` | 3.6KB | 07-18 15:02 | llmwiki 系统说明 |

### E. Karpathy wiki 状态 (30 个)

| 文件 | 大小 | mtime | 功能/作用 |
|---|---:|---|---|
| `wiki/coverage.md` | 569B | 07-20 11:41 | 569B, 覆盖率 |
| `wiki/log.md` | 329B | 07-20 11:41 | wiki 操作日志 |
| `llmwiki/index.md` | 290B | 07-20 11:00 | llmwiki 当前状态 |
| `llmwiki/timeline.md` | 271B | 07-20 11:00 | llmwiki 时间线 |
| `llmwiki/by-project/(uncategorized).md` | 250B | 07-20 11:00 | (待登记) |
| `wiki/contradictions.md` | 18B | 07-18 23:02 | 18B, 矛盾点 (空) |
| `wiki/index.md` | 3.3KB | 07-18 23:02 | wiki 索引入口, M-LintWiki-001 输出 |
| `wiki/timeline.md` | 9.1KB | 07-18 23:02 | 9.3KB, 时间线, lint 时查 |
| `wiki/topics/1-cd-to-cusersadministratorqclawworkspace.md` | 2.5KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-06-29-pi-browser-harness.md` | 10.8KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-06-agent-templates-2026-07-02.md` | 17.6KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-08-mcp-toolbox-mcp-toolbox-for-databases.md` | 7.7KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-08-ruflo.md` | 59.9KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-11-phase-1-memory-layer-ship.md` | 46.5KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-13-m3-p3-extent-allocator-ship-recovery-from-8d87016.md` | 25.4KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-14-ai-os-symboliclink-d-126.md` | 36.2KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-14-stylex-skill-ship-15-4-harvest-promote-d-128.md` | 5.0KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-14-team-e-agent-ship-d-115.md` | 45.1KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-14-team-g-ship-d-122-method-tree---execute-registry-docstring.md` | 5.7KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-14-team-h-q-a-team-ship-llm-d-123-m-qwenthink-001-m-wingbk-001.md` | 6.2KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-14-team-h-qa_log-ship-d-124-m-qafts5-001-002-003.md` | 5.0KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-14-team-h-qa_log-v1.5-d-125-4-phase-ship.md` | 5.5KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-15-d-127-ship-8-team.md` | 12.9KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-15-section.md` | 49.6KB | 07-18 23:02 | (待登记) |
| `wiki/topics/2026-07-17-d-152-tier-1-2-fast-path-ship-imp-0.85-cat-ship-decision.md` | 24.3KB | 07-18 23:02 | (待登记) |
| `wiki/topics/use-the-ascii-short-path-m-subst-already-mapped-to-the-repo-.md` | 2.2KB | 07-18 23:02 | (待登记) |
| `llmwiki/log.md` | 151B | 07-18 15:15 | (待登记) |
| `llmwiki/topics/current-time-saturday-july-18th-2026---1502-asiashanghai.md` | 7.8KB | 07-18 15:15 | (待登记) |
| `llmwiki/contradictions.md` | 18B | 07-18 15:14 | (待登记) |
| `llmwiki/coverage.md` | 125B | 07-18 15:14 | (待登记) |

## 统计

- **总业务文件**: 49 个
- **A 产品主入口**: 9 个
- **B 方法论**: 1 个
- **C LAAP 必读**: 5 个 (旧 3 → 新 5)
- **D 文档**: 4 个
- **E wiki 状态**: 30 个

## 元规则

1. **本索引** (`MD_INDEX.md`) 已被 RULE-MDIndex-013 提升为 **L0 必读** (与 MEMORY.md 同优先级)
2. **MEMORY.md 优先级最高**: 任何任务, 30 秒内必读 (L0 硬禁止)
3. **新 md 文件**: 添加后必须立即更新本索引, 注明功能/作用
4. **删除 md**: 走 M-SafeRemove-001 备份 (RULE-SafeRemove-012)
5. **LAAP 必读升级**: 旧 3 文件 → 新 5 文件 (mtime 倒序, 含 by-project + 话题快照)
6. **未登记的 md**: 标 `(待登记)`, 待补全功能描述
7. **下次 lint 时间**: M-LintWiki-001 weekly (周日)

## 维护命令 (Python 重新生成)

```python
import os, datetime
ROOT = r"E:\新建文件夹\新建文件夹gent-templates-2026-07-02\mini-mp-agent"
md_files = []
for root, dirs, files in os.walk(ROOT):
    rel_root = os.path.relpath(root, ROOT).replace(os.sep, "/")
    if any(d in rel_root for d in ["_archive", "_cron_wiki", "_seed_wiki", "examples", ".git"]):
        continue
    for f in files:
        if f.endswith(".md"):
            full = os.path.join(root, f)
            md_files.append((os.path.relpath(full, ROOT), os.path.getsize(full),
                datetime.datetime.fromtimestamp(os.path.getmtime(full)).strftime("%m-%d %H:%M")))
# 然后按 classify() 分组 (A/B/C/D/E), 写本文件
```

---

🤖 Generated with M-MDIndex-001 (D-MDIndex-001, 2026-07-20 13:36)
