# OpenClaw Cron Jobs (mini-mp-agent)

> **最后更新**: 2026-07-20 15:08:32 (Asia/Shanghai, 15:07 加状态)
> **方法节点**: `methods/recipes/sync_cron_doc.yaml` (M-SyncCronDoc-001, 2026-07-20 14:58 立)
> **触发**: 用户 "现在统一同步 mini-mp-agent/docs/cron-jobs.md"
> **流程**: cron list → 渲染本文件 → 更新顶部时间戳 → 校验 job 总数 = total (5)
> **关联**: workspace-mini-mp/cron_jobs_snapshot_2026-07-20.md (双项目同步快照)

## 概览表 (5 个任务, all Asia/Shanghai)

| # | 任务名 | cron expr | 周期 | job id |
|---:|---|---|---|---|
| 1 | `llmwiki-cron-full-nightly` | `0 23 * * *` | daily | `5e6ac85e-d426-4708-b6b3-9b428578e7d1` |
| 2 | `llmwiki-ingest-daily` | `0 11 * * *` | daily | `5b25178b-56b2-4e7c-8065-54d2725263fa` |
| 3 | `llmwiki-deep-lint` | `5 11 * * *` | daily | `0fdd2d0f-9940-4d7f-96d7-9165a7c2d043` |
| 4 | `llmwiki-backup-weekly` | `10 11 * * 0` | weekly Sunday | `4cae35bc-5f94-4b06-8a57-3aa1856d429a` |
| 5 | `llmwiki-compact-monthly` | `15 11 1 * *` | monthly 1st | `1b32c839-1a0a-4649-a10c-4ccc36dfd8ed` |

> **总任务数**: 5 (`total` from `cron list`)  
> **时区**: Asia/Shanghai (所有任务)  
> **agentId**: mini-mp  
> **sessionTarget**: isolated (无主 session 干扰)  
> **delivery.mode**: none (本地 webchat 静默)

---

## 1. `llmwiki-cron-full-nightly` — 23:00 daily

- **schedule**: `cron` `0 23 * * *` (Asia/Shanghai)
- **作用**: 全量 session JSONL 扫描, 补回 11:00 改 daily 后丢失的 cron-full 触发
- **payload**:
  ```
  cd "E:/新建文件夹/新建文件夹/agent-templates-2026-07-02/mini-mp-agent" && export PYTHONPATH=. && python scripts/wiki_ingest.py --wiki-root ./llmwiki --source cron-full 2>&1 | tail -50; echo "EXIT=$?"
  ```
- **failure alert**: `after=2, cooldown=1h, mode=announce`
- **state**: 🆕 未运行 (新)
- **next run**: 2026-07-20 23:00:00 Asia/Shanghai

## 2. `llmwiki-ingest-daily` — 11:00 daily

- **schedule**: `cron` `0 11 * * *` (Asia/Shanghai)
- **作用**: LLMwiki daily ingest + lint (由 `cron_llmwiki.sh` 包装)
- **payload**:
  ```
  bash E:/新建文件夹/新建文件夹/agent-templates-2026-07-02/mini-mp-agent/scripts/cron_llmwiki.sh 2>&1 | tail -50; echo "EXIT=$?"
  ```
- **failure alert**: `after=2, cooldown=1h, mode=announce`
- **state**: ✅ ok
- **last run**: 2026-07-20 11:00:00 Asia/Shanghai (79860 ms, ~80s)
- **next run**: 2026-07-21 11:00:00 Asia/Shanghai

## 3. `llmwiki-deep-lint` — 11:05 daily

- **schedule**: `cron` `5 11 * * *` (Asia/Shanghai)
- **作用**: 每日深度健康检查 (orphans / stale 30d / contradictions)
- **payload**:
  ```
  cd "E:/新建文件夹/新建文件夹/agent-templates-2026-07-02/mini-mp-agent" && export PYTHONPATH=. && python scripts/wiki_lint.py --wiki-root ./llmwiki --stale-days 30 --json 2>&1 | tail -80; echo "EXIT=$?"
  ```
- **failure alert**: `after=3, cooldown=24h, mode=announce` (更保守)
- **state**: ✅ ok
- **last run**: 2026-07-20 11:05:00 Asia/Shanghai (58449 ms, ~58s)
- **next run**: 2026-07-21 11:05:00 Asia/Shanghai

## 4. `llmwiki-backup-weekly` — 11:10 Sunday

- **schedule**: `cron` `10 11 * * 0` (Asia/Shanghai, weekly Sunday)
- **作用**: 每周日备份 `llmwiki/` 目录到 `backups/llmwiki_<date>.tar.gz`
- **payload**:
  ```
  cd "E:/新建文件夹/新建文件夹/agent-templates-2026-07-02/mini-mp-agent" && mkdir -p backups && tar czf "backups/llmwiki_$(date +%F).tar.gz" llmwiki/ 2>&1 | tail -20 && ls -lh backups/ | tail -10; echo "EXIT=$?"
  ```
- **failure alert**: `after=2, cooldown=7d, mode=announce`
- **state**: 🆕 未运行 (今天周一, 下次周日 2026-07-26)
- **next run**: 2026-07-26 11:10:00 Asia/Shanghai

## 5. `llmwiki-compact-monthly` — 11:15 monthly 1st

- **schedule**: `cron` `15 11 1 * *` (Asia/Shanghai, monthly 1st)
- **作用**: 每月 1 号输出 90 天 stale 报告到 `backups/stale_<YYYY-MM>.json` (**不删除**, 仅记录)
- **payload**:
  ```
  cd "E:/新建文件夹/新建文件夹/agent-templates-2026-07-02/mini-mp-agent" && mkdir -p backups && export PYTHONPATH=. && python scripts/wiki_lint.py --wiki-root ./llmwiki --stale-days 90 --json > "backups/stale_$(date +%Y-%m).json" 2>&1 && cat "backups/stale_$(date +%Y-%m).json" | python -c "import sys,json; d=json.load(sys.stdin); print(f\"stale_count={d.get('stale_count',0)} orphan_count={d.get('orphan_count',0)} contradiction_count={d.get('contradiction_count',0)}\")"; echo "EXIT=$?"
  ```
- **failure alert**: `after=2, cooldown=30d, mode=announce`
- **state**: 🆕 未运行 (今天 7/20, 下次 8/1)
- **next run**: 2026-08-01 11:15:00 Asia/Shanghai

---

## 典型一天时间线

```
11:00  #2 llmwiki-ingest-daily        (mem+lint, ~80s)  ✅
11:05  #3 llmwiki-deep-lint           (orphans/stale, ~58s) ✅
11:10  #4 llmwiki-backup-weekly       (跳过, 今天非周日)
11:15  #5 llmwiki-compact-monthly     (跳过, 今天非月初)
23:00  #1 llmwiki-cron-full-nightly   (全量 JSONL, ~30-120s)
```

---

## 同步工作流 (M-SyncCronDoc-001)

```python
# 1. 拿最新状态
result = call_cron_tool("list")
total = result["total"]

# 2. 渲染本文件 (5 段: 概览 / 详细 / 时间线 / 工作流 / 变更日志)
render_to_file(result["jobs"], "docs/cron-jobs.md")

# 3. 更新顶部 "最后更新" 时间戳
update_timestamp()

# 4. 校验 job 总数
assert count_rows_in_overview_table() == total

# 5. commit + push mini-mp-agent (走 RULE-Encoding-014)
```

---



---

## 当前状态 (2026-07-20 15:07): 工作中 vs 没工作

| 状态 | 数量 | 任务 |
|---|:---:|---|
| ✅ **工作中** | **2** | `llmwiki-ingest-daily` (last 11:00 ok), `llmwiki-deep-lint` (last 11:05 ok) |
| 🆕 **没工作中** (未到时间) | **3** | `llmwiki-cron-full-nightly` (23:00 今晚), `llmwiki-backup-weekly` (7/26 周日), `llmwiki-compact-monthly` (8/1 月初) |
| ❌ **没工作中** (出错) | **0** | (无失败) |

**合计**: 5 个任务 = 2 ✅ + 3 🆕 + 0 ❌

**持续检查**: `cron list` 拿最新 state.lastRunStatus + consecutiveErrors

---

## 变更日志

| 时间 | 变更 |
|---|---|
| 2026-07-20 02:27 | 5 任务建立, 时间对齐到 11:00-11:15 daily/weekly/monthly + 23:00 cron-full nightly |
| 2026-07-20 02:31 | docs/cron-jobs.md (mini-mp-agent) 首次建立 + M-SyncCronDoc-001 立 (当时实际未入库, 历史档案错记) |
| 2026-07-20 12:25 | 修复 02:30 那段 GBK 乱码 (RULE-Encoding-001 前置案例) |
| 2026-07-20 12:30 | M-SyncCronDoc-001 升级命名 + 加编码自检 |
| **2026-07-20 14:58** | **本次 re-ship**. 用户 "现在统一同步". 实际文件首次入库 (MEMORY 写过但文件没建). |
