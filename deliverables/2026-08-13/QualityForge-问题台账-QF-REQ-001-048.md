# QualityForge 需求重构后评审 · 问题台账(QF-REQ-001 ~ 048)

> 评审编号:QF-RR-2026-0813 ｜ 日期:2026-08-13 ｜ 状态口径:OPEN=待整改 / FIXING=整改中 / CLOSED=已关闭(需复评确认)
> 编号说明:QF-REQ = 问题台账;QF-RSK = 风险登记(另册);QF-UNC = 待核实附册
> 来源编号:QUAL-A(六维评审·模块10-13)/ QUAL-B(六维评审·模块14-17)/ CONS(一致性扫描)/ NEW(重构新问题)/ GAP(覆盖度缺口)/ RISK(风险)
> 合并规则:7 组合并(14 条→7 条),见 QF-REQ-002/008/009/010/011/003/004 备注

## 一、阻断级(1 条)

### QF-REQ-001 · WorkItem 关键字段未落四源 【阻断】
- **状态**:OPEN ｜ **来源**:QUAL-A-01 ｜ **质量维度**:一致性/完整性
- **问题**:05 §5.5.3 规定 WorkItem 必填/关键字段 `objective/acceptanceCriteria/requiresReview/lockVersion/constraints/agentId`,但 04 §3.1、32 OpenAPI、33 `t_work_item` DDL 均未建模。`requiresReview` 是 05 §5.5.4 规则 1 与 GWT-5.5.12-1、10-PRD AC-01 的实现前提——缺字段则"正式产出不得绕过人工审核"核心门禁无法实现、验收无法进行;`lockVersion` 缺失使乐观锁约束无法满足。
- **影响**:WorkItem 建模/API/DDL;任务看板核心验收(05 §5.5.12-1/2/7、10-PRD AC-01)
- **证据**:05-功能模块重构方案.md §5.5.3(L467-497) vs 04-核心领域模型.md §3.1 vs 33-数据库Schema设计.md §5 `t_work_item`(L330-351) vs 32-API规范.yaml WorkItem/WorkItemCreate schema
- **整改建议**:04/32/33 同步补 6 字段(required 列表 + DDL 列 + 领域模型字段表),追加 CHANGELOG 条目;补后重跑 L1 一致性扫描与 Golden 链验证

## 二、严重级(6 条)

### QF-REQ-002 · WorkItemType 枚举三方冲突 【严重】
- **状态**:OPEN ｜ **来源**:QUAL-A-02 + CONS-01(合并 M1)
- **问题**:05 §5.5.2 定义 11 值(STRATEGY/PLAN/TEST_DESIGN/AUTOMATION_WEB/AUTOMATION_API/EXECUTION/RESULT_ANALYSIS/DEFECT/REPORT/KNOWLEDGE/GENERAL);04 §3.1(L116)、32(L748/L771)、33(L332)三方一致为 10 值(CASE/AUTOMATION/ANALYSIS 替代 TEST_DESIGN/AUTOMATION_WEB/AUTOMATION_API/RESULT_ANALYSIS)。按 04/32/33 实现则与产品裁决不符,按 05 实现则被 DB CHECK 拒绝。
- **影响**:WorkItem 创建/过滤/看板视图(§5.5.9);13-PRD Web/API 脚本类型归属展示
- **证据**:05 §5.5.2 vs 04 §3.1 L116 vs 32 L748/L771 vs 33 L332
- **整改建议**:二选一收敛。建议以 04/32/33 的 10 值为准回改 05 §5.5.2(其 TEST_DESIGN 与 21 号介入点同名易混淆);若坚持细分类型则同批升级四源+CHANGELOG,禁止只改一边

### QF-REQ-003 · CoverageReport 契约链断裂 【严重】
- **状态**:OPEN ｜ **来源**:QUAL-A-04 + QUAL-B-01(合并 M5)
- **问题**:12-PRD §2/§3 将 CoverageReport 列为设计链实体、AC-03 以"CoverageReport 声称 90%"为验收对象;05 §4.6/§5.12.7 将 CoverageReport 唯一写入归"质量分析与缺陷",§5.12.4 未收录;PRD15 全文零承接 CoverageReport,而 05 §5.13.3 将"基础覆盖/风险汇总"列为 V1 必交付。同名产出物两模块可写,违反 §5.12.1 唯一写入边界;"设计覆盖"与"执行覆盖报告"未拆分。
- **影响**:12 模块覆盖分析 AC-03;14 模块唯一写入;V1 覆盖度闭环验收
- **证据**:12-PRD §2/§3/AC-03 vs 05 §4.6(L306)/§5.12.7(L2159)/§5.13.3(L2315) vs 15-PRD 全文(grep 零命中)
- **整改建议**:裁决"设计覆盖(需求→用例映射)"与"执行覆盖报告"两个概念归属;PRD15 补 CoverageReport 需求行与 AC;同步 04/32/33 唯一 Owner 标注

### QF-REQ-004 · 执行→分析契约验证链断裂 【严重】
- **状态**:OPEN ｜ **来源**:QUAL-B-02 + QUAL-B-03(合并 M6)
- **问题**:05 §5.10.8 强制"测试执行产生 APIObservation 和 ContractCheckResult,未检查不能计为通过、INCONCLUSIVE 不能被报告为契约一致",§5.12.6 将二者唯一写入归测试执行;但 PRD14 全文无 ContractCheckResult 需求与 AC(证据仅泛称"请求/响应"),PRD15 报告行未含"执行基线摘要/已检查 Operation 数/偏差数/未检查数/不可判定数"披露项。V1 API 契约验证证据链在 PRD 层断裂。
- **影响**:V1 API 执行契约偏差检测、报告披露、验收
- **证据**:05 §5.10.8(L1741-1757)/§5.12.6(L2140-2151) vs 14-PRD §2/§3/§6 vs 15-PRD §3(L24)
- **整改建议**:PRD14 补 ContractCheckResult/APIObservation 需求+AC(含"未检查不计通过");PRD15 报告行补契约检查披露项;32 补 ContractCheckResult schema

### QF-REQ-005 · OpenAPI 成功响应过度通用化 【严重】
- **状态**:OPEN ｜ **来源**:NEW-01(数字经复核修正)
- **问题**:32-API 共 102 个 operation,其中 **58 处**成功响应引用 Generic(GenericListResponse 25 + GenericObjectResponse 33,占 58/102),无字段/必填/枚举/分页约束,客户端无法生成稳定契约。"71 paths 完整"的宣称在契约深度上延续原审计"广度完整、深度不足"判断,从实体层转移到响应层。
- **影响**:客户端生成、联调、测试资产生成质量
- **证据**:32-API规范.yaml(58 处 Generic 引用);37/54 的"58 处"为正确口径
- **整改建议**:核心链(策略/计划/用例/执行/分析)operation 响应契约逐条收敛;37/54 口径同步;收敛批次进 CHANGELOG

### QF-REQ-006 · AI 校准记录无结构化载体、无实例 【严重】
- **状态**:OPEN ｜ **来源**:GAP-02(维持高)
- **问题**:21 §4/AC-03 要求校准记录含 threshold/sampleSize/baseline/validFrom/expiresAt/fallbackLevel,并规定"无有效校准记录时分数只能排序、不得触发自治";但 33 `t_eval_dataset/t_eval_case/t_eval_run/t_eval_result` 仅 scope/metrics JSONB,无 threshold/有效期/回退等级列、无"介入点↔阈值↔回退等级"登记表;32 无校准注册 API;30 套 Skill eval 全部为确定性结构校验(103 cases),无真实模型校准实例。L2/L3 准入依据缺失,21 号 AC-03 常驻 fail-closed。
- **影响**:校准治理实现期退化为自由格式 JSONB;自治等级无法按契约启用
- **证据**:21 §4/AC-03 vs 33 t_eval_*(L1801-1846) vs 32 /ai/eval-runs vs prototypes/skills evals(30/30 确定性校验)
- **整改建议**:33 补校准记录表(threshold/validFrom/expiresAt/fallbackLevel 列)+ 登记表;32 补校准注册/查询 API;建立真实模型 Golden Set 校准计划(05§十一 步骤 5)

### QF-REQ-007 · 05 §十一 五个后续步骤未绑定版本里程碑与验收门 【严重】
- **状态**:OPEN ｜ **来源**:GAP-04
- **问题**:05 §十一 后续 5 步骤(批改→新版本→二次复核、看板分派/SLA/Diff、AutomationScript 闭环、四类产出物运行证据、真实模型黄金集)全部落在 V1 准出范围内,但无"步骤↔版本↔验收证据"对照表与时间锚点;收口复核开放项 1/2 直接威胁 V1 准出,延期风险不可见。
- **影响**:V1 范围管理与进度可追踪性;准出时"静态闭环 vs 运行时验收"争议
- **证据**:05 §十一 vs 22 §3 V1 范围 vs 收口复核 §4 开放项 1/2
- **整改建议**:建立 5 步骤 × V1/V2 里程碑 × 验收证据对照表;每步骤定义 DoD(完成定义)与责任 Owner

## 三、一般级(29 条)

| 编号 | 来源 | 问题摘要 | 影响 | 证据 | 整改建议 |
|---|---|---|---|---|---|
| QF-REQ-008 | QUAL-A-03+CONS-02(M2) | 通用产出物 reviewStatus:05 §5.6.2 用 REWORK/缺 STALE,孤立偏离 03/04/32/33 与 12-PRD 一致的 9 值(CHANGES_REQUESTED+STALE) | 产出物状态机实现口径 | 05 §5.6.2(L691) vs 04 §1.2 vs 33 L501 等 | 05 §5.6.2 回改 9 值枚举 |
| QF-REQ-009 | QUAL-A-05+CONS-04(M3) | WorkItem 状态机迁移集合不一致(05 §5.5.4 有 IN_PROGRESS→DONE 等,04 §11.1 无)+ 04/05 双重权威声明 | 非审核类工作项无法直接 DONE;实现两套迁移表 | 04 §11.1 vs 05 §5.5.4 | 以 05 迁移表补齐 04 状态图;消除双重权威声明 |
| QF-REQ-010 | QUAL-A-06+CONS-03(M4) | WorkItemRun 枚举冲突(05: RUNNING/SUCCESS/FAILED/TIMEOUT/CANCELLED vs 33: PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED)+ tokenUsage/cost 无列 | 看板 AI 运行状态与成本指标 | 05 §5.5.6 vs 33 L377 t_work_item_run | 统一枚举(建议以 33 为准,TIMEOUT 归 errorCode);补成本字段或声明来源 |
| QF-REQ-011 | QUAL-B-06+CONS-08(M7) | 15-PRD §4 命名漂移:ExternalSyncAttempt/approvalReviewTaskId vs 权威名 DefectSyncAttempt/approvalId | 32/33 落地时字段分歧 | 15-PRD §4 vs 03 §10 vs 04 §8.2 vs 05 §5.9.8 | 统一为 DefectSyncAttempt/approvalId |
| QF-REQ-012 | QUAL-A-07 | 32 将 agentSessionId 列为 ReviewTask 必填,05 §5.6.8/04 §3.3/33 均无此字段(人工直接修改提交审核无 AgentSession);COMMENT 动作是否落库未决 | ReviewTask API 契约;人工审核兼容性 | 32 ReviewTask schema vs 05 §5.6.7/§5.6.8 vs 33 t_review_task | 32 取消必填或改为可选;COMMENT 落库口径裁决 |
| QF-REQ-013 | QUAL-A-09 | 4 个 PRD 版本范围为段落式,未按 05 §5.13.7 逐项标注 MUST/SHOULD/LATER+Owner+验收证据;13-PRD 功能表含 V2 能力 | V1 范围裁剪与验收边界 | 10/11/12/13-PRD §版本范围 vs 05 §5.13.7 | 逐能力标注版本归属与验收证据 |
| QF-REQ-014 | QUAL-A-12 | 10-PRD §4 状态链暗示 REWORK 可直接→DONE,与 05 §5.5.4(REWORK→IN_PROGRESS)不符 | 看板状态流转实现误导 | 10-PRD §4 vs 05 §5.5.4 | 10-PRD 状态链改与 05 一致 |
| QF-REQ-015 | QUAL-B-04 | PRD14 §3 误用"APIContractBaseline"作为执行冻结对象;05 §5.10.7 明确执行须用 ExecutionContractBaseline(APIContractBaseline 仅 TEST_DESIGN/MOCK/CONTRACT_ANALYSIS) | 执行冻结按错误基线实现的风险 | 14-PRD §3 vs 05 §5.10.7 | PRD14 术语改为 ExecutionContractBaseline |
| QF-REQ-016 | QUAL-B-05 | PRD14 未覆盖 ExecutionContractBaseline 冻结内容清单(运行时映射/认证/脱敏快照/授权快照/baselineDigest)与"基线撤销/权限失效/凭证不可用→BLOCKED"触发 | 基线撤销后执行阻塞无需求依据 | 05 §5.10.7(L1737-1739) vs 14-PRD §5 | PRD14 §5 补基线撤销异常与 AC |
| QF-REQ-017 | QUAL-B-07 | 16-PRD §6 未承接 21 §6.1"校准记录过期/评测跌破门槛/误放误阻超警戒线"降级触发 | Agent 运行策略在评测跌破门槛时缺 PRD 级依据 | 16-PRD §6 vs 21 §6.1(L118-120) | PRD16 补降级触发闭环(关联 QF-REQ-006) |
| QF-REQ-018 | QUAL-B-09 | PRD17 未覆盖 §5.11.8 SupportAccessGrant/紧急访问(break-glass)契约,§5.12.9 明确归平台管理 | 高权限运维路径缺需求依据;审计/恢复路径风险 | 17-PRD 全文 vs 05 §5.11.8/§5.12.9 | PRD17 补紧急访问需求+AC+审计要求 |
| QF-REQ-019 | QUAL-B-10 | 21 §5 CONFIG_ASSIST(默认 L1)与 01 功能地图"配置预检/最小权限建议"未入 PRD17(功能表无 AI 作用列) | 平台管理 AI 辅助需求缺失 | 21 §5(L75) vs 01 §2(行31) vs 17-PRD §2 | PRD17 功能表补 AI/系统作用列与需求 |
| QF-REQ-020 | CONS-05 | 37 §2 操作数列三处偏差:任务看板 9≠10、AI Agent 中心 6≠8、平台管理 17≠22(实算:10/8/22) | 导航文档数字失真 | 37 §2 vs 32 tags 实算 | 37 §2 按 32 实算修正,37/54 同源 |
| QF-REQ-021 | CONS-06 | 01 §2 知识库行误用废弃别名"Requirement"(权威名 RequirementDocument) | 顶层产品文档使用废弃别名 | 01 §2(L25) vs 03 §6 | 改为 RequirementDocument |
| QF-REQ-022 | CONS-07 | ExecutionBatch 在 03/04/32/33 均不存在,但 18-PRD §1 与 14-PRD §2 使用"Batch/Task"表述 | 触发批次概念无契约载体 | 18-PRD §1 vs 14-PRD §2 vs 04 §7 | 删除 Batch 表述或显式建模,同步四源 |
| QF-REQ-023 | GAP-01(修正后) | "独立验证"环节缺专门载体:总纲 §8/旅程 A 要求"确定性检查/独立验证/人工审核"三层证据分别报告,但无逐产出物独立验证介入点/通过条件/降级触发(现有 PLATFORM_INDEPENDENT_REVIEW 与 Gate 0 verifier 仅部分覆盖);"AI 自评 AI"风险(53 号检查点 1)无对应缓解 | 三层证据第二层无法验收;总纲 §8 部分落空 | 02 §8 vs 21 §5 vs 05 §5.6.3 vs 53 §五 | 21 号补独立验证介入点定义(运行主体/输入输出/通过条件/降级);16-PRD 补承接 |
| QF-REQ-024 | GAP-03 | 五类覆盖率口径(实例/设计/可执行/严格有效/人工验收)无权威精确定义与计算规则 | 试点覆盖度不可比;收益主张失真 | 22 §3 vs 12-PRD AC-03 vs 15-PRD AC-03 | 补五类口径定义+计算规则+样例,试点前冻结 |
| QF-REQ-025 | GAP-06 | V1"外部同步可先手工"与 EXTERNAL_WRITE 验收衔接未定义(手工模式 approvalId↔payloadDigest/幂等键/回执是否落库) | 外部写入安全底线在 V1 退化 | 22 §3 vs 05 §5.9.7-5.9.8/5.9.11 | 定义手工模式批准记录与回执数据结构(关联 QF-RSK-010) |
| QF-REQ-026 | GAP-07 | 无全局指标口径/数据字典(人工修改率/误放率/遗漏率等分子分母采样窗口未集中定义,与 20-NFR metricKey 无映射) | 指标采集不一致,V1 基线不可比 | 02 §7 vs 05 §八 vs 20-NFR §7 | 建指标数据字典,映射 20-NFR metricKey |
| QF-REQ-027 | GAP-08 | V1 看板范围不含效率指标采集载体(05 §5.5.11 指标 vs 22 §3 V1 看板行 vs 05 §5.13.3 V1 退出条件需记录人工净处理时间等) | V1 退出条件基线条目无产品载体 | 05 §5.5.11/§5.13.3 vs 22 §3 vs 10-PRD §8 | V1 看板补指标采集能力或声明手工采集流程 |
| QF-REQ-028 | NEW-02 | 目标架构 104 表未按 V1 裁剪证明(全量实现放大迁移/RLS/运维成本) | 工程误判"按图全建" | 33(104 CREATE TABLE) vs 05 §5.12.11 | 产出 V1 表清单与目标表对照,裁剪决策记录 |
| QF-REQ-029 | NEW-03 | 05 §8 指标基线义务(每项指标在对应 PRD 补基线/测量方法/GWT)仅 3/10 PRD 落地(11/12/16) | 效果衡量承诺悬空于 05 方案层 | 05 §8.1/8.2 vs 10 个 PRD grep | 8 个业务 PRD 补指标承接段(关联 QF-REQ-026/027) |
| QF-REQ-030 | NEW-04 | C-1/L1-004 关闭证据时点错位:07-31/08-11 复扫以 TestDesignPlan 链为证据,CH-40 起 TestDesignPlan 退场,t_test_plan 已无 requirement_document_id | "C-1 已修复"结论在新模型下需重证 | 05 §5.7.2 vs 33 t_test_plan(L771-786) vs L1-复扫 L1-004 | 目标态下重做 RTM 正向链核验,更新关闭证据 |
| QF-REQ-031 | NEW-05 | 多态溯源无外键(t_work_item_artifact.artifact_id、t_source_trace_edge from/to、t_review_task 多态引用均无 FK) | DB 层无法保证溯源/审核引用完整性 | 33 L354-368/L510;CHANGELOG-08-04 | 应用层拦截+运行时负向测试补证;评估部分 FK 化 |
| QF-REQ-032 | NEW-06 | 运行时证据缺口:Stage4 仅 22/102 ops、3/8 产出物;AutomationScript/ResultAnalysis/Defect/TestReport/KnowledgeEntry 无纵向切片;版本 Diff 未实现 | V1 范围承诺与证据差距明显;文档闭环被误读为开发完成 | 收口复核开放项 1/2 vs 05 §5.13.3 | 按 QF-REQ-007 里程碑补齐 5 类产出物切片证据 |
| QF-REQ-033 | NEW-07 | Skill eval 是结构校验而非效果评测(30/30 evals.json+14 确定性 runner 全为静态检查) | "Skill 统一 eval PASS"易误读为 AI 效果达标 | 收口复核 §3 vs Stage4 §2 项3 | 区分"结构校验"与"效果评测"两种口径,宣传用语校正 |
| QF-REQ-034 | NEW-08 | SQLite 本地 Profile ≠ PostgreSQL(RLS/跨租户并发/生产恢复未验证) | "单机可运行"≠"多租户隔离安全" | Stage4 vs 收口复核开放项 3 | V1 前 PG 冒烟:104 表迁移+RLS+核心链路并发 |
| QF-REQ-035 | NEW-09 | PRD 文件名与模块内容错位(10-PRD-Workspace.md 内容=任务看板等,仅文件头声明) | 按文件名导航/机械扫描误判 | docs/02-prd/10~17 文件头 vs 05 §5.14 | 54 索引增加显式"文件名↔模块"映射表;工具扫描按标题而非文件名 |
| QF-REQ-036 | NEW-10 | 21 号 21 个介入点(实算)未与 32 operation/33 表三方对账;新增介入点契约落地未审计 | 治理矩阵超前于契约实现 | 21 §5(21 个 key) vs 32 vs 33 | 建三方对账表,进 L1 扫描基线 |

## 四、建议级(12 条)

| 编号 | 来源 | 问题摘要 | 证据 | 整改建议 |
|---|---|---|---|---|
| QF-REQ-037 | QUAL-A-08 | WorkItemArtifact 关联字段命名:05 §5.5.5 role vs 04/33 relation_type(33 多 SUPERSEDES) | 05 §5.5.5 vs 04 §3.2 vs 33 | API 层统一命名与取值 |
| QF-REQ-038 | QUAL-A-10 | BLOCK_HUMAN 术语未注明来源(55-SOP 定义为 Workflow 节点裁决);10-PRD "返回 409"混入 HTTP 细节 | 12-PRD §6 vs 55-SOP;10-PRD §6 | 术语标注来源;HTTP 细节移出需求 |
| QF-REQ-039 | QUAL-A-11 | V1 隔离试运行沙箱验收口径未定义(非 root/只读根/零外网如何证明) | 05 §5.8.8 vs 30/31 | 补 V1 沙箱验收量化口径与失败阈值 |
| QF-REQ-040 | QUAL-A-13 | 11-PRD AC-01"摘要匹配"依赖主观判断,未给判定口径;AC-02 冲突落点未指明 | 11-PRD §6 vs 05 §5.10.8 | 补抽样比例/比对方式;显式引用变更 WorkItem |
| QF-REQ-041 | QUAL-B-08 | 16-PRD 用 L0-L3/回退 L1 未定义等级含义、未引用 21 为权威源 | 16-PRD §2/§6 vs 21 §2 | 显式引用 21 号 SSOT |
| QF-REQ-042 | QUAL-B-11 | Pipeline 触发版本归属不明(14-PRD §2/§7 vs 05 §5.13.3/§5.13.4 无流水线字眼) | 14-PRD vs 05 §5.13 | 明确 CI 触发归属(建议 V2 归 15 号) |
| QF-REQ-043 | QUAL-B-12 | V1 重试上限未写明(§5 按策略新 attempt vs §5.13.3 一次受控重试) | 14-PRD §5 vs 05 §5.13.3 | V1 重试次数上限写入 PRD |
| QF-REQ-044 | QUAL-B-13 | 16-PRD §4 引用 platform-review-agent.json 未给路径/校验方式;AC-05/06 无自动化验证挂载点 | 16-PRD §4/§7 vs prototypes | 文件路径与校验契约化 |
| QF-REQ-045 | CONS-09 | ReviewDecision 概念未实体化(01/10/20/21/31/34/32 引用,04/33 无独立实体;03 与 04 迁移表目标表述不一) | 04 §3.3/§12 vs 33 vs 32 L853 | 显式说明"ReviewDecision=ReviewAssignment.decision+AuthorizationDecision 投影"或补实体 |
| QF-REQ-046 | CONS-10 | 03 §13.8/13.9 小节编号重复(两处 13.8、两处 13.9) | 03 §13(L277-297) | 重排为 13.8-13.11 |
| QF-REQ-047 | GAP-05 | 知识回流 V1/V2 措辞不一致(15-PRD §5"提交 KnowledgeEntry 候选" vs 22 V2"知识反馈";证据实际在 05 §5.13.3 L2309) | 15-PRD §5 vs 22 §3/§4 vs 05 §5.13.3 | 澄清 V1 知识候选链路交付边界 |
| QF-REQ-048 | NEW-11 | 修复证据链依赖内部自述(L1 复扫/收口复核均为内部产出;B-4/B-5/B-6 与 C-4 缺第三方交叉核验) | 现状复审 §1.2 vs L1 复扫 §二 | 关键关闭项引入独立复审或第三方抽查 |

## 五、风险登记册(QF-RSK-001 ~ 013)

| 编号 | 类别 | 风险描述 | 概率 | 严重度 | 缓解方向 | 关联 |
|---|---|---|---|---|---|---|
| QF-RSK-001 | 业务 | V1 试点未严格采集效率/质量数据,收益主张无法验证 | 中 | 高 | 采集清单转强制数据字典(QF-REQ-026/027) | 02§7/05§5.13.3 |
| QF-RSK-002 | 业务 | 单 Workspace+SINGLE_REVIEW 试点结论外推为团队协作价值 | 中 | 中 | 试点报告强制声明边界 | 05§5.11.7 |
| QF-RSK-003 | 业务 | 覆盖率分母口径漂移致质量指标可操纵 | 中 | 高 | 补五类覆盖率权威定义(QF-REQ-024) | 22§3 |
| QF-RSK-004 | 技术 | V1 八模块×八产出物 vs 当前 3/8 证据;延期或缩范围 | 高 | 高 | 05§十一步骤绑里程碑(QF-REQ-007) | 05§十一/22§3 |
| QF-RSK-005 | 技术 | 确定性 Provider≠真实模型;正确性/延迟/成本/出站未评测 | 高 | 高 | 黄金集先行;接入前评测;AC-03 兜底 | 收口复核开放项4 |
| QF-RSK-006 | 技术 | SQLite 原型≠PostgreSQL RLS/并发/恢复 | 中 | 中 | V1 试点前 PG 冒烟(QF-REQ-034) | 30/33 |
| QF-RSK-007 | 技术 | V2 外部集成若 V1 未保留 Link/SyncAttempt 结构,集成成本剧增 | 低-中 | 中 | V1 手工同步保留数据结构(QF-REQ-025) | 05§5.9 |
| QF-RSK-008 | 范围 | 8 模块 V1"最小入口"颗粒度未冻结,边界漂移 | 高 | 中 | 按 05§5.13.7 标注 MUST/SHOULD/LATER(QF-REQ-013) | 05§5.13.7 |
| QF-RSK-009 | 范围 | V2 项被提前拉入 V1"补全闭环体验" | 中 | 中 | 执行 05§5.13.7 变更规则;走 53 号审计 | 05§5.13.7 |
| QF-RSK-010 | 合规/安全 | 外部写入 approvalId↔payloadDigest 校验被简化 | 中 | 高 | V1 手工模式也走批准记录+幂等键+回执 | 05§5.9.8/15-PRD§4 |
| QF-RSK-011 | 合规/安全 | Secret 双信封在原型期无实现,V1 凭证体系延期 | 中 | 高 | Secret 服务随 V1 交付;禁止明文回退 | 17-PRD AC-03 |
| QF-RSK-012 | 合规/安全 | AutomationScript 任意代码执行(RCE)+Skill 供应链 | 中 | 高 | V1 Runner 容器化隔离+零默认外网+依赖锁扫描 | 05§5.8.8/55 |
| QF-RSK-013 | 合规/安全 | 真实 LLM 接入=测试数据出站;脱敏/区域策略未评测 | 高 | 高 | 接入前出站评测;无评测前保持确定性 Provider/L0 | 21§2 L0 |

## 六、待核实附册(QF-UNC,摘选)

| 编号 | 内容 | 影响项 |
|---|---|---|
| QF-UNC-001 | Stage4 运行时证据范围(21 源文件/10 测试/E2E 页面)未独立复验 | QF-REQ-032 |
| QF-UNC-002 | 104 表字段级与 04/32 逐字段对照未全量执行 | QF-REQ-028 |
| QF-UNC-003 | 21 介入点↔32 operation↔33 表三方对账未完成 | QF-REQ-036 |
| QF-UNC-004 | 02 总纲 6 角色与 05§5.11.3 六模板逐能力对账未逐行比对 | C-6 残留 |
| QF-UNC-005 | 36-WebSocket 契约、38-数据库迁移约定未纳入扫描 | 14 号实时通道 |
| QF-UNC-006 | OpenAPI 官方 validator 执行环境与命令未复核 | QF-REQ-005 |
| QF-UNC-007 | Stage4 负向安全测试(E2E 负向用例)清单未逐项核验 | QF-RSK-011/012 |
| QF-UNC-008 | C-4 从"10 非标准"到"30/30"之间无独立审计记录 | QF-REQ-033 |

---
*台账维护规则:整改完成后须按 53 号方案在 docs/05-audits/current/ 复验记录中关闭,关闭时引用证据位置;不改写历史审计结论。*
