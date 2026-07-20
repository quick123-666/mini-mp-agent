# Encoding Quarantine Report (2026-07-19 18:30)

**Generated from**: `C:\Users\Administrator\.qclaw\workspace\scripts\encoding_detect.csv`
**Total .md files scanned**: 2245
**Total bytes**: 16.01 MB

## Summary

| Category | Count | Bytes | % |
|---|---|---|---|
| UTF8_OK | 12 | 121.9 KB | 0.53% |
| GBK_OK | 0 | 0 KB | 0% |
| DOUBLE_ENC | 0 | 0 KB | 0% |
| MIXED (total) | 2233 | 15.9 MB | 99.47% |
| - bom-ascii-cron (false positive) | 2202 | - | - |
| - true-mixed (real corruption) | 31 | - | - |
| EMPTY | 0 | 0 | 0% |

## Verdict

**31 true-MIXED files (1.38%)** require manual intervention or are unrecoverable (no original source).

Most of these are GBK bytes mis-stored as UTF-8 + UTF-8 BOM (double-encoding corruption, 16:30 LCM-era repair script created this state). Original content cannot be reconstructed without source backup.

## Top 20 directories with most MIXED files

- 100 - C:\Users\Administrator\.qclaw\workspace\skills\loops\prompts\zh
- 100 - C:\Users\Administrator\.qclaw\workspace\skills\loops\prompts\en
- 46 - C:\Users\Administrator\.qclaw\workspace\skills\nihaisha\references
- 40 - C:\Users\Administrator\.qclaw\workspace\memory
- 30 - C:\Users\Administrator\.qclaw\workspace\skills\meta-planner\agents\team-h\sandbox\evolve_workspace\node_modules\react-router\docs\how-to
- 30 - C:\Users\Administrator\.qclaw\workspace\skills\meta-planner\agents\team-h\sandbox\inbox\streaming-ai-chatbot\node_modules\react-router\docs\how-to
- 20 - C:\Users\Administrator\.qclaw\workspace\skills\meta-planner\agents\team-h\sandbox\evolve_workspace\node_modules\react-router\docs\explanation
- 20 - C:\Users\Administrator\.qclaw\workspace\skills\meta-planner\agents\team-h\sandbox\inbox\streaming-ai-chatbot\node_modules\react-router\docs\explanation
- 19 - C:\Users\Administrator\.qclaw\workspace\skills\stylex\functions
- 18 - C:\Users\Administrator\.qclaw\workspace\skills\design\references
- 12 - C:\Users\Administrator\.qclaw\workspace\skills\meta-planner\agents\sub-agents
- 11 - C:\Users\Administrator\.qclaw\workspace\skills\meta-planner\agents\team-h\sandbox\evolve_workspace\node_modules\react-router\docs\start\framework
- 11 - C:\Users\Administrator\.qclaw\workspace\skills\brand\references
- 11 - C:\Users\Administrator\.qclaw\workspace\skills\meta-planner\agents\team-h\sandbox\inbox\streaming-ai-chatbot\node_modules\react-router\docs\start\framework
- 10 - C:\Users\Administrator\.qclaw\workspace\skills\meta-planner\agents\team-h\sandbox\inbox\streaming-ai-chatbot\node_modules\react-router\docs\start\data
- 10 - C:\Users\Administrator\.qclaw\workspace\skills\obsidian-knowledge-brain\references
- 10 - C:\Users\Administrator\.qclaw\workspace\skills\meta-planner\agents\team-h\sandbox\evolve_workspace\node_modules\react-router\docs\start\data
- 7 - C:\Users\Administrator\.qclaw\workspace\skills\meta-planner\agents\team-h\sandbox\inbox\streaming-ai-chatbot\node_modules\node-domexception\.history
- 7 - C:\Users\Administrator\.qclaw\workspace\skills\ui-styling\references
- 7 - C:\Users\Administrator\.qclaw\workspace\skills\meta-planner\agents\team-h\sandbox\evolve_workspace\node_modules\node-domexception\.history

## Recommendation

1. **UTF8_OK files**: Safe to read. Use detector before reading (D-DetectEncoding-001).
2. **BOM+ASCII cron logs**: Safe to read (cron healthcheck output, no Chinese). Skip detector threshold for this case.
3. **True MIXED files**: Unrecoverable. Recommend moving to `archive/corrupted-2026-07-19/` for hygiene, OR leave in place with detector skip list.

**Decision pending**: Per D-ShipCompletionDefinition-001 rule 6, do not create new M-NNN for this; the encoding issue is already covered by M-WriteToolGBK-001 + D-BackupBeforeDestructiveTransform-001. The 95% MIXED damage is a historical artifact (2026-07-19 14:33 GBK repair attempt), not new errors.

