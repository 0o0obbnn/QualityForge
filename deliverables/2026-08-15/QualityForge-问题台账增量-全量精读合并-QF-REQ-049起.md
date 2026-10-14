# QualityForge 问题台账增量 · 全量精读合并清单(QF-REQ-049 起)

> 日期:2026-08-15 ｜ 来源:全量精读合并(用户提供,主 agent 抽查验证 P0-1/2/6 三条全部属实)
> 与既有台账衔接:QF-REQ-001~048(8-13 评审)+ 本增量 QF-REQ-049~103(55 条)
> 分类:A=主 agent 可直接修复(基线已存在,纯一致性修复)｜ B=出草案+用户一次裁决 ｜ C=必须用户拍板(产品/商业决策)

## 一、P0(阻塞开发/建库/审核闭环,9 条)

| 编号 | 问题 | 证据 | 影响 | 分类 |
|---|---|---|---|---|
| QF-REQ-049 | ExecutionResult.status 三向不一致(32 驼峰四值缺 INCONCLUSIVE vs 33/36 五值全大写;32 注释自称已对齐) | 32 L1272 vs 33 L1279、36 L75 | 执行事实核心真相源,进度统计与 36 验收基线 6 无法实现 | A |
| QF-REQ-050 | AutomationScriptVersionCreate 冲突扩大(dependencyLockRef/sourceTrace/runtimeSpec/checkSummary 在 32/33/04 缺;GIT 字段 fullCommitSha vs gitCommitSha 分叉) | 32 L1112、05 L1114-1119、04 L281 | 依赖锁/可复现性安全底线在 API 层不设防 | A |
| QF-REQ-051 | AgentSession 三方三种模型(32 workItemId/workflowKey vs 04/33 workItemRunId/agentId/promptVersionId;status 枚举 32 PAUSED_FOR_HUMAN vs 33 BLOCKED/SUCCEEDED) | 32 L1143 vs 33 L1771、04 L395 | Agent 中心核心关联实体无法落地,Gate 0 会话审计链断裂 | A |
| QF-REQ-052 | TestReport 缺版本层契约(仅单体 schema,TestReportVersion schema+端点缺失;REPORT_SIGNOFF 绑定 artifactVersionId) | 32 L1278 vs 04 L377、34 §5 | 报告签署(humanOnly)无 API 落点 | A |
| QF-REQ-053 | PipelineRun.status 混入门禁裁决语义(32 五值含门禁 vs 33 运行状态+独立 gateDecision 列) | 32 L1281 vs 33 L1654-1656 | 无法区分"运行失败"与"门禁拦截" | A |
| QF-REQ-054 | 目标 DDL 不可执行(CHECK 枚举未加引号、REAL 非 PG 类型、t_work_item 前向引用 t_agent、JSONB 列建 UNIQUE) | 33 L1902/L1882/L338/L724 | 38 §7"空库升级到 head 无错误"必然失败 | A |
| QF-REQ-055 | 错误码三源不一致(32 实测 21 值 vs 37 只列 16 值,缺 429 行与 4 个本地认证码) | 32 L793 vs 37 L130-138 | 前端错误处理与认证链无对齐文档 | A |
| QF-REQ-056 | 存量/本地脚本导入路径无正式定义(05 全文无、32 无批量端点) | 05 grep、32 /automation/* | 试点客户既有资产无法迁入 | C |
| QF-REQ-057 | GIT 延期替代路径"人工导出"仅一句 AC、全文无定义 | 05 L2415、13-PRD | GWT-5.13.8-6 不可验收 | C |

## 二、P1(阻塞验收/治理闭环,20 条)

### 契约层(11 条)

| 编号 | 问题 | 证据 | 分类 |
|---|---|---|---|
| QF-REQ-058 | 表数口径三处分叉(30 说 104、33 L3 残留 106、38 说 107;实测 CREATE TABLE=107) | 30/33 L3/38 | A |
| QF-REQ-059 | 37 基线失真:声称 80 paths 实算 72;§2 地图漏 4 个新路径;54 §7 滞后(80 vs 实测 105 schemas) | 37/54 | A |
| QF-REQ-060 | RunnerHeartbeat 状态词表与 RunnerNode 不一致;taskId 必填致 IDLE 无法上报 | 32 heartbeat vs RunnerNode | A |
| QF-REQ-061 | 多个响应 schema 缺 33 NOT NULL 列(TestStrategyVersion 7 项等 5 实体) | 32 vs 33 | A |
| QF-REQ-062 | 产品必填但 API 未强制(TestCaseVersion.sourceTrace、KnowledgeEntryVersion.sensitivity、DefectTransition 回归证据单 UUID) | 05 vs 32 | A |
| QF-REQ-063 | ReviewTask API 缺 policyVersionId;ReviewArtifact.artifactType 仅 3 类(六类策略中 4 类无契约) | 32 ReviewTask | B |
| QF-REQ-064 | ExecutionPlanVersion 字段名漂移(contentDigest/frozenBaselineRef 33 无列);ExecutionTask 缺 authorizationDecisionId 等 4 字段 | 32 vs 33 | A |
| QF-REQ-065 | ResultAnalysisVersion/TestSuite 缺版本端点,"稳定根+不可变版本"断链 | 32 vs 04/33 | A |
| QF-REQ-066 | CalibrationRecord/VerifyVerdict 缺租户上下文(t_verify_verdict 无 tenant_id,RLS 套不上) | 33 vs 34 AC-04 | A |
| QF-REQ-067 | permissionKey 能力键目录完全缺失(34 只有中文描述,种子 0013 无法生成) | 34 §4.2 | B |
| QF-REQ-068 | 32 顶层 security 为 [BearerAuth, CookieAuth](OpenAPI 语义=AND)与 37"或"矛盾;Cookie 写操作 CSRF 契约缺失 | 32 顶层 vs 37 | B |

### 产品层(3 条)

| 编号 | 问题 | 证据 | 分类 |
|---|---|---|---|
| QF-REQ-069 | 状态机系统性缺口(ReviewTask/Assignment 无迁移表;Skill ERROR 死状态;Release TESTING 无中断出边;约 18 实体 status 无枚举) | 04/05 | B |
| QF-REQ-070 | 术语表失控(约 20 实体未登记 03,违反 04 §13.1;ReviewDecision 三处定位不一) | 04 vs 03 | A(登记)/B(ReviewDecision 定位) |
| QF-REQ-071 | 04 §6.1 与 05 §5.8.4 已互矛盾(并入 QF-REQ-050) | — | A |

### PRD 层(3 条)

| 编号 | 问题 | 证据 | 分类 |
|---|---|---|---|
| QF-REQ-072 | "指标数据字典"6 处悬空引用(11/13/14/15/16/17-PRD 指向不存在于受控体系的文件) | PRD grep | B |
| QF-REQ-073 | 通知渠道 Owner 悬空(19 号裁决归 17,但 17-PRD 无此行) | 19 vs 17-PRD | A |
| QF-REQ-074 | 仅 13-PRD 有行级 MUST/SHOULD/LATER 标注;11-PRD"来源导入"功能表与 V1 范围冲突 | PRD | B |

### 治理层(3 条)

| 编号 | 问题 | 证据 | 分类 |
|---|---|---|---|
| QF-REQ-075 | GDPR/数据主体权利零条款;20 §4.6"历史引用阻止删除"与删除权冲突;24-合规文档未落地 | 20 §4.6 | C |
| QF-REQ-076 | LLM 数据出站审批流缺失(V1 接真实模型前同样无依据) | 20 §5 | C |
| QF-REQ-077 | 保留期限无任何数字条款(审计/证据/Trace 无上下限) | 05 V3 行 | C |

## 三、P2(26 条,摘要)

- **结构类(4)**:PRD 文件名↔模块错位 6 处且 02 无映射提示;15/16-PRD 重复 ## 8. 章节号;16-PRD AC 编号乱序。
- **指标口径类(4)**:人工修改率双口径(12 vs 15 M-16)、重试次数公式含糊、M-20 键名前缀违规、"警戒线"无定义。
- **契约散点类(10)**:DefectVersionCreate.evidence minItems:1 与"先建草稿后补证"矛盾;36 缺 DefectSyncResult 事件;ws-ticket 返回 GenericObject;400 vs 422 分裂;actorType 词表三套;WorkItemRun 缺 BLOCKED;结果级重跑与 UNIQUE 冲突;Idempotency-Key 强加于票据签发;37 操作数滞后;E8 空分母剩余范围待确认。
- **建模类(5)**:APPROVED vs PUBLISHED 语义未定;Skill 未采用稳定根+版本;Defect.releaseId 必填困住探索性缺陷;PipelineConfig 引用执行计划根而非版本;全局关系图缺半数实体。
- **治理类(3)**:V2 准出口径两处互不引用(22 vs 05 §5.13.4);53"80 条 API"滞后且无合规检查点;55 与 16-PRD 超时上限无交叉引用;16-PRD 校准记录写为 V2 增强与 V1 自治底座矛盾。

**P2 分类**:结构类 4 条 = A;指标口径 4 条 = B;契约散点 10 条 = A(6)/B(4);建模类 5 条 = B(4)/C(1);治理类 3 条 = B(2)/C(1)。

## 四、统计与处理顺序

| 分类 | 数量 | 处理 |
|---|---|---|
| A:主 agent 直接修 | 约 30 | 按批执行(每批 CHANGELOG 入册+验证) |
| B:草案+一次裁决 | 约 15 | 出《待裁决清单+推荐方案》,用户逐条"同意/改X" |
| C:必须拍板 | 约 8 | 出《待拍板清单》,用户决策 |

建议顺序:P0 契约裁决轮(B 类先裁决)→ DDL 可执行性修复(A,独立一批跑空库演练)→ 合规治理(C 拍板)→ P1 补齐 → P2 清理。

## 五、M1-B0 复核追加（2026-08-17，续编 QF-REQ-078 起）

> 来源：M1-B0 QF-REQ-001 四源二次复核（deliverables/2026-08-17/QF-REQ-001-四源二次复核记录.md §四），实测发现，不当场扩围。

| 编号 | 问题 | 证据 | 级别 | 处置 |
|---|---|---|---|---|
| QF-REQ-078 | 运行时会话状态枚举与契约不一致：planning_workflow 用 RUNNING→PAUSED_FOR_HUMAN→COMPLETED，契约 AgentSession.status 为 PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED/BLOCKED，且黑名单明禁 PAUSED_FOR_HUMAN/COMPLETED；现有契约测试只校 yaml↔33 号，未覆盖运行时取值 | planning_workflow.py L399/L403/L683-700 vs 32 号 AgentSession schema vs test_contract_enums.py FORBIDDEN_VALUES | 严重 | **已关闭（M1-B1，批次三十）**：运行时收敛到契约枚举（BLOCKED/SUCCEEDED/FAILED）＋存量加载归一（_LEGACY_SESSION_STATUS_MAP）＋test_rework_closed_loop.py 枚举守卫断言 |
| QF-REQ-079 | M1 实施计划 v1.1 现状表将 createTestStrategy/createTestPlan/createTestCase/createTestCaseVersion 列为已实现，实测 22 项实现清单仅含对应四个 list | test_openapi_contract.py EXPECTED_IMPLEMENTED_OPERATION_IDS | 轻微 | 已随批更正 M1 实施计划两行口径（改判未实现，M1 范围再评估） |
| QF-REQ-080 | M1-B1 切片 DTO 与契约约束口径差异：TestStrategyVersionCreate/TestPlanVersionCreate 切片实现增加字段长度/日期格式/UUID 类型约束，而 32 号契约对应 schema 仅有字段清单无约束；实现更严不破坏客户端兼容，但契约文本未同步 | backend/src/qf/schemas/planning.py vs 32 号 L1039/L1073 | 轻微 | 登记开放项，归 M2 契约批次对齐（为契约补约束或出裁决豁免） |
| QF-REQ-081 | 需求全量评审报告 §5.6 gate 宣称「6 项开放决策（O1–O6）」，但全文仅 O1–O5 有定义与 T 映射，O6 零定义零引用，属编号多报 | 需求全量评审报告-2026-08-15 §5.6 vs §5.5 T1–T8 表 | 轻微 | **已处置（M1-B2 关闭包）**：判定实际开放决策 5 项，关闭包 §1.6 证据关闭；后续引用以关闭包口径为准 |
