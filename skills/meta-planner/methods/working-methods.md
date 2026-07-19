# 工作方法论 v1.0.0 — Clean Baseline (Reconstructed 2026-07-19)

**Reconstructed from**: MEMORY.md + 7 个 UTF8_OK 源文件（memory/2026-07-16.md / 5 meta-planner skills / 1 harness-builder）
**Status**: 索引重建完成 (231 unique D/M-NNN ID), 详细内容分散在 `memory/`、`skills/`、`scripts/`
**Source original**: `skills/meta-planner/methods/working-methods.md` v0.1.3 (19211 bytes, MIXED 双错码, 不可救)
**Encoding**: UTF-8 (无 BOM, write 工具原生)
**No structural claims**: 不写"7 节点 / 3 节点"等结构性断言，避免脑补

---

## 0. 元规则 (l0, 跨项目)

### 编码与读

- **D-DetectEncoding-001** [imp=0.95] [cat=l0|method|tool] — 读前必跑 `scripts/detect_corrupted_encoding.ps1`
- **D-VerifyBeforeUse-001** [imp=0.95] [cat=l0|method|process] — LLM 读前必 verify 3 步
- **D-ReadAllTextBOM-001** — PowerShell `ReadAllText` 默认 UTF-8 无 BOM 但 PS 5.1+Encoding=GBK 字节兼容读
- **D-BackupBeforeDestructiveTransform-001** [imp=0.9] [cat=l0|method|process] — 批量不可逆转换前必做可回滚备份
- **M-PowerShellGBK-001** — PowerShell 中文输出 GBK 坑
- **M-PS51Encoding-002** — PS 5.1 编码行为差异
- **M-WinGBK-001** — Windows 默认 GBK 输出
- **M-GBKCmd-001** — GBK 字节级处理
- **M-GBKCmdStr-001** — GBK 字符串边界
- **M-PSDollarUnderscoreCmdline-001** [imp=0.8] [cat=l0|tool|method] — PS 5.1 `-Command` 模式 `$_` 被吃，必须写脚本
- **M-AddContentGBK-001** [imp=0.7] [cat=l0] — `Add-Content` 默认 cp936，需 `-Encoding utf8` 显式
- **M-BatEncoding-001** — .bat 脚本中文编码

### 流程与门禁

- **D-ShipCompletionDefinition-001** [imp=0.9] [cat=l0|decision|process] — ship 完成硬门槛 (代码/文档/M-D/MEMORY/BUILD.md)
- **D-MethodClassification-001** [imp=0.9] [cat=l0|decision|process] — 工作方法 cat= 必填 (l0/l1/l2/other)
- **D-CatbaseNoRun-001** — catbase 不直接 run
- **D-DispatchVerify-001** — dispatch 后必 verify 返回
- **M-DispatchVerify-001** — dispatch verify 实现
- **M-VerifyExec-001** — exec 后必 verify 退出码
- **M-VerifyWrapper-001** — wrapper 层 verify

### 安全 / 备份

- **D-GBKStdoutFix-001** — stdout GBK 修复策略
- **M-LAAPNoGitBackup-001** [imp=0.9] [cat=l1] — LAAP 非 git，destructive 前 Copy-Item 备份
- **M-ResetBackup-003** — 备份重置流程

### 元设计

- **D-TeamH-001** — Team H 团队设计决策
- **D-StylexHook-001** — StyleX hook 决策
- **M-HookResearch-001** — hook 研究方法

---

## 1. Agent 架构 (l1, 跨项目复用)

### 路由与派发

- **D-MCPTemplateBridge-001** — MCP template 桥接决策
- **M-DispatchNested-001** — 嵌套 dispatch
- **M-DispatchTeamG-001** — Team G dispatch
- **M-DispatchV06-001** — dispatch v0.6
- **M-SwarmDispatch-001** — Swarm 派活
- **M-SwarmExecute-001** — Swarm 执行
- **M-SwarmRegistry-001** — Swarm 注册
- **M-SwarmMethodTree-001** — Swarm 方法树
- **M-RouteToTeamV06-001** — Team v0.6 路由
- **M-TeamA-001 ~ M-TeamA-004** — Team A 4 个方法
- **M-TeamARouter-001** — Team A 路由
- **M-TeamHDispatch-001** — Team H dispatch
- **M-TeamHScope-001** — Team H scope
- **M-TeamHSandbox-001** — Team H sandbox
- **M-TeamMethodsIndex-002** — Team methods 索引
- **M-TeamRegistryV01-001** — Team registry v0.1
- **M-TeamRegistryV02-001** — Team registry v0.2
- **M-TeamRouting-001 ~ M-TeamRouting-005** — 团队路由 5 个版本
- **M-TeamEmbeddingV01-001** — 团队 embedding v0.1
- **M-HybridRoutingV03-001** — 混合路由 v0.3
- **M-TierFastPath-001** — Tier 快速路径
- **M-TierRouterAsync-001** — Tier 路由异步
- **M-TierRouterFallback-001** — Tier 路由 fallback
- **M-PCAutoRoute-001** — PC 自动路由
- **M-PCDispatch-001** — PC 派发
- **M-PCNaturalLang-001** — PC 自然语言派发
- **M-PrefixSwitch-001** — 前缀切换
- **M-StageKindSchemaV06-001~003** — Stage kind schema v0.6 (3 个)
- **M-PersistTreeV06-001~005** — Persist tree v0.6 (5 个)
- **M-KeywordDecomposeV04-001** — 关键词分解 v0.4
- **M-KeywordDecompV05-001~003** — 关键词分解 v0.5 (3 个)
- **M-KeywordInferV03-001** — 关键词推断 v0.3
- **M-LLMDecomposeV05-001** — LLM 分解 v0.5
- **M-LLMRouteV01-001** — LLM 路由 v0.1
- **M-LLMStub-001** — LLM stub
- **M-WorkerInfer-001** — Worker 推断
- **M-WorkerPoolComplete-001** — Worker pool 完成
- **M-WorkerPoolV02-001** — Worker pool v0.2

### 方法论管理

- **M-MethodSediment-001** — 方法论沉淀
- **M-MethodsIndexIncomplete-001** — 索引不完整时处理
- **M-AutoPromotedIndexRow-001** — 索引行自动晋升
- **M-DistillTrigger-001** — 蒸馏触发
- **M-PromoteGating-001** — 晋升门禁
- **M-Step3-001** — Step 3 处理
- **M-HandleInMain-001** — main 句柄
- **M-HandleTierNested-002** — tier 嵌套处理
- **M-JunctionPath-001** — 节点路径
- **M-TopologicalSort-001** — 拓扑排序
- **M-DecisionTrail-001** — 决策轨迹
- **M-LessonSync-001** — 教训同步
- **M-CognitiveNone-001** — 认知无
- **M-CoEvolve-001** — 协同演化
- **M-SONA-001** — SONA 框架

### MCP / Bridge

- **M-AIOSBridge-001~003** — AIOS 桥接 3 个
- **M-AIOSBridgeStub-001~002** — AIOS 桥接 stub 2 个
- **M-MCPSchemaDriven-001** — MCP schema 驱动
- **M-McpSessionReset-001** — MCP session 重置
- **M-MCPStdIO-001** — MCP stdio
- **M-FastMCPNoPort-001** — FastMCP 无端口
- **M-WebRTCBroadcast-001** — WebRTC 广播
- **M-BuiltinWebSocket-001** — 内置 WebSocket
- **M-PythonBackendWS-001** — Python backend WS

### Embedding / Search

- **M-Embed-001~005** — Embedding 5 个
- **M-CosineSearch-001** — Cosine 搜索
- **M-VectorRecallFAISS-001** — FAISS 向量召回
- **M-TokenizerNoJieba-001** — 分词不用 jieba
- **M-FormatFix-001** — 格式修复
- **M-WebMirror-002** — Web 镜像 (反例)
- **M-WebSearch-001** — Web 搜索
- **M-WebFetch-002** — Web fetch

---

## 2. 编程与脚本 (l1)

### Python / 工具链

- **D-PythonProjectAnalyzerDesign-001** — Python 项目分析器设计 (树状 vs 线性)
- **D-RuffBatchFixBeatsPylint-001** — ruff --fix 1.7s 修 3362 issues 比 pylint 强 10x
- **M-PythonProjectAnalyzer-001** — 8 节点方法树
- **M-PydepsPathArg-001** — pydeps 只接单包名
- **M-PylintStdoutCapture-001** — pylint Popen+文件流避免 pipe 死锁
- **M-PyFileAssociation-001** — Python 文件关联
- **M-PyInStdout-001** — Python stdout
- **M-PyReplaceAnchor-001** — Python 替换锚点
- **M-AstGrepOpenAIImport-001** — ast-grep 找 OpenAI import
- **M-LLMBoundaryAstGrep-001** — ast-grep 找 LLM 边界
- **M-PythonPackageMarker-001** — Python 包 marker

### Frontend / UI

- **M-ReactHMR-001** — React HMR
- **M-ReactMemo-001** — React.memo
- **M-UI-001** — UI 设计
- **M-ChatHtmlApprovalBinding-001** — chat html 审批绑定
- **M-ChatHtmlEdit-001** — chat html 编辑
- **M-ChatHtmlToolCallConfusion-001** — chat html toolcall 混淆
- **M-AiohttpStaticReload-001** — aiohttp 静态重载
- **M-FastAPIState-001** — FastAPI state
- **M-HMRTest-001** — HMR 测试
- **M-HttpAsyncE2E-001** — HTTP 异步 E2E

### PowerShell / Windows

- **M-PowerShellEchoSplit-001** — PS echo 分割
- **M-PowerShellSlow-001** — PS 慢
- **M-AIOSPowerShellEscape-001** — PS 转义
- **M-PSTaskRun-001** — PS task 运行
- **M-WinTaskKill-001** — taskkill 替代 Stop-Process
- **M-SchtasksXML-001** — schtasks XML
- **M-ProcessDetach-001** — process 分离
- **M-JsonSerialize-001** — JSON 序列化
- **M-InspectSignature-001** — 签名检查
- **M-SysNoPath-001** — 系统无 PATH
- **M-PathInsert0-001** — PATH 插入 0 位
- **M-LogBeforeDefined-001** — log 早于定义
- **M-RetryWithLog-001** — 重试+日志
- **M-NestedFunctionRevert-001** — 嵌套函数回退
- **M-PendingStub-001** — pending stub
- **M-WebCryptoReuse-001** — WebCrypto 复用
- **M-OptOutCrypto-001** — 关闭加密
- **M-UnifiedImport-001** — 统一 import
- **M-ReorderImports-001** — 重排 import
- **M-MethodsIndexIncomplete-001** — 索引不完整
- **M-SmokeStale-001** — 烟雾测试陈旧

### 测试

- **M-E2ETest-001** — E2E 测试
- **M-LiveVerify-001** — 在线 verify
- **M-QAArchive-001** — QA 归档
- **M-QABM25-001~003** — BM25 QA 3 个
- **M-QAFTS5-001~003** — FTS5 QA 3 个
- **M-QAFirstBeforeAction-002** — QA 先于行动
- **M-AtomicFunctionCard-001** — 原子功能卡
- **M-SafeRespond-001** — 安全响应
- **M-Archive-001** — 归档
- **M-Abort-001** — 中止

### 调度

- **M-CronAlert-001** — cron 告警
- **M-CronDaily-001** — cron 日报
- **M-DockerHealthcheck-001** — Docker 健康检查

### 数据库 / 跨 DB

- **M-CrossDB-001** — 跨 DB
- **M-PropChain-001** — 链式属性
- **M-ScopeMap-001** — scope 映射
- **M-SlugifySlug-001** — slugify

---

## 3. 沙箱与子 agent (l1)

- **M-AIOSAtomicWrite-001~002** — AIOS 原子写 2 个
- **M-AIOSDispatchTest-001** — AIOS dispatch test
- **M-AIOSRouteDef-001~003** — AIOS 路由定义 3 个
- **M-AIOSReportFormat-001~003** — AIOS 报告格式 3 个
- **M-AIOSSmokeFix-001** — AIOS 烟雾修复
- **M-SandboxApprovalAsError-001** — 沙箱批准当错误
- **M-SandboxLogOrder-002** — 沙箱日志顺序
- **M-RuntimeMutableWhitelist-001** — 运行时可变白名单
- **M-MethodsIndexIncomplete-001** — 索引不完整处理
- **M-FixTeamBGBK-001** — Team B GBK 修复
- **M-FixTeamBStylexHook-001** — Team B StyleX hook 修复
- **M-ProjectFusion-001** — 项目融合

---

## 4. LAAP 项目 (l2, 单项目)

- **D-LAAPZeroLLM-001** — 早期错误判定 (LAAP = Zero-LLM, 已被 D-LAAPNotZeroLLM-001 推翻)
- **D-LAAPNotZeroLLM-001** [imp=0.9] [cat=l2] — LAAP = AGI Framework v2.3.0 Unified Mind
- **D-LAAPAGIFramework-001** [imp=0.9] [cat=l2] — LAAP 8 大认知模块
- **D-LAAPArchitectureFinding-001** [imp=0.9] [cat=l2] — LAAP 架构发现
- **D-LAAPBrainNotRunning-001** — LAAP Brain 未运行
- **D-LAAPDeploy-001** — LAAP 部署决策
- **D-LAAPLorentBond-001** [imp=0.7] [cat=l2] — LAAP 长期记忆人格特征保留
- **D-ChatProxyKeyHermesDotEnv-001** — chat_proxy key 在 hermes .env
- **M-LAAPDeployVerify-001** — LAAP 部署验证
- **M-LaapModulePath-001** — LAAP 模块路径
- **M-ChatProxyNoLorryHardcode-001** — chat_proxy 不硬编码 "Lorry"
- **M-ReadEngineeringDocFirst-001** [imp=0.7] [cat=l2] — 读工程文档先于源码

---

## 5. AIOS 大项目 (l2)

- **D-AIOSBigProject-001~003, 005, 006, 007** — AIOS 6 个早期决策 (004 缺失)
- **M-AIOSBridge-001~003, Stub-001~002** — 见 §1 MCP
- **M-AIOSAtomicWrite-001~002** — 见 §3
- **M-AIOSDispatchTest-001 / AIOSTscShellTrue-001** — AIOS 测试相关
- **M-AIOSPowerShellEscape-001** — 见 §2 PowerShell
- **M-AIOSRouteDef-001~003** — 见 §3
- **M-AIOSReportFormat-001~003** — 见 §3
- **M-AIOSSmokeFix-001** — 见 §3

---

## 6. 量化交易 (l2, 跨项目, JSTrader)

- **M-JSTrader-001** — JSTrader 主方法
- **M-TestnetDefault-001** — 测试网默认
- **M-GapAnalysis-001** — 缺口分析
- **M-HarvestAutoSlug-001** — 自动 slug 收割
- **M-TechStackAdapt-001** — 技术栈适配

---

## 7. 倒填与反例 (other)

- **M-WebMirror-002** — Web 镜像反例
- **M-ExtractFailuresV07-001~003** — 抽取失败 v0.7 (3 个)
- **M-WebMirror-002** — 镜像反模式

---

## 元索引

| 段 | 类别 | 数量 |
|---|---|---|
| §0 | l0 元规则 | ~25 |
| §1 | l1 Agent 架构 | ~80 |
| §2 | l1 编程脚本 | ~40 |
| §3 | l1 沙箱子 agent | ~12 |
| §4 | l2 LAAP | ~12 |
| §5 | l2 AIOS | ~17 |
| §6 | l2 量化交易 | ~5 |
| §7 | other 反例 | ~4 |
| **合计** | | **~195** (重复 36 跨段) |

**总 ID 数**: 231 unique (从 MEMORY.md 提取)
**未列入 ID**: 0（231 全部按主题分类）
**缺失原始内容**: 每条 ID 的"内容描述"和"教训原文"在 MEMORY.md + memory/*.md + skills/*/SKILL.md 中可查，本文件仅做索引

---

## 已知未 ship (2026-07-19 17:30)

- 整体转新编码 (95% MIXED 不可逆，5% GBK-cleaned 子集待工具)
- 脱敏更新 GitHub (mini-mp-agent / laap 仓库)
- 清理 95% 损坏文件 (.bak/ → archive/，释放索引)
- P2 验证 cron 自动触发 (laap_healthcheck 已取消, ship_check 14:08)

**重建原则**: 不脑补, 不写"7 节点"等结构, 已知 ID 全部列入, 描述留白指向原文件。
