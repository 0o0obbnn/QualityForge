# QualityForge 需求重构后评审 · 需求条目盘点清单(408 条)

> 评审编号:QF-RR-2026-0813 ｜ 日期:2026-08-13 ｜ 盘点口径:需求来源 = 各 PRD「功能需求」表行 + 05 方案 §5.5-5.15 契约规则与 GWT 验收基线 + 总纲 §5 核心业务规则 + 功能地图 §2 模块职责承诺
> 条目编号:INV-模块-序号(01=任务看板,02=知识库,03=测试策划与设计,04=自动化测试开发,05=测试执行,06=质量分析与缺陷,07=AI Agent中心,08=平台管理,00=跨模块全局契约);需求类型:功能/规则/验收/非功能;状态:已定义/部分定义/仅原则性声明
> 证据位置缩写:05=docs/01-product/05-功能模块重构方案.md;PRD10~17=docs/02-prd/对应文件;地图=01-产品功能地图v2.0.md;总纲=02-PRD总纲.md

---

## 2. 需求条目总清单

> 条目编号：`INV-模块-序号`（01=任务看板，02=知识库，03=测试策划与设计，04=自动化测试开发，05=测试执行，06=质量分析与缺陷，07=AI Agent 中心，08=平台管理，00=跨模块全局契约）
> 需求类型：功能 / 规则 / 验收 / 非功能
> 状态：已定义（有具体字段/条件/验收点） / 部分定义（方向明确但细节延后） / 仅原则性声明（高层承诺）
> 证据位置：文件路径用缩写——`05`=docs/01-product/05-功能模块重构方案.md；`PRD10`~`PRD17`=docs/02-prd/对应文件；`地图`=01-产品功能地图v2.0.md；`总纲`=02-PRD总纲.md

### 2.1 模块一：任务看板（PRD10 + 05 §5.5/§5.6/§5.12.2）

| 条目编号 | 需求名称 | 所属模块 | 需求来源 | 需求类型 | 状态 |
|---|---|---|---|---|---|
| INV-01-01 | 工作项管理：创建/查询/筛选/分派/优先级/父子关系/Release与TestPlan关联 | 任务看板 | PRD10 §3（L18-28） | 功能 | 已定义 |
| INV-01-02 | 工作项 AI 拆解建议与人工确认（关键范围/负责人/优先级） | 任务看板 | PRD10 §3（L18-28） | 功能 | 已定义 |
| INV-01-03 | 状态流转：按状态机流转并记录原因；BLOCKED/取消/关键范围变更需理由或权限 | 任务看板 | PRD10 §3（L18-28） | 功能 | 已定义 |
| INV-01-04 | AI 运行可视化：Agent/Skill/版本/步骤/耗时/成本/Trace/降级，可暂停可取消 | 任务看板 | PRD10 §3（L18-28） | 功能 | 已定义 |
| INV-01-05 | 审核队列：按产出物/风险/Release/到期时间/职责筛选，预检摘要与证据 | 任务看板 | PRD10 §3（L18-28） | 功能 | 已定义 |
| INV-01-06 | 退回重做：保留原版本与决定，创建新版本/attempt，审核人复核新摘要 | 任务看板 | PRD10 §3（L18-28） | 功能 | 已定义 |
| INV-01-07 | 阻塞管理：原因码/详情/恢复条件/依赖人系统/SLA，AI 归纳+人工裁决 | 任务看板 | PRD10 §3（L18-28） | 功能 | 已定义 |
| INV-01-08 | 看板统计：WIP/周期/审核时长/阻塞/人工接管/AI失败，指标仅用于改进不作绩效自动裁决 | 任务看板 | PRD10 §3（L18-28） | 非功能 | 已定义 |
| INV-01-09 | WorkItem 统一状态机：BACKLOG→READY→IN_PROGRESS→PENDING_REVIEW→REWORK/APPROVED→DONE，支持 BLOCKED/CANCELLED | 任务看板 | PRD10 §4（L30-37） | 规则 | 已定义 |
| INV-01-10 | WorkItemRun 记录 actorType/Agent与Workflow版本/授权快照/IO摘要/Trace/verdict | 任务看板 | PRD10 §4（L30-37） | 规则 | 已定义 |
| INV-01-11 | ReviewTask 绑定 artifactType/artifactId/artifactVersionId/contentDigest/policyType | 任务看板 | PRD10 §4（L30-37） | 规则 | 已定义 |
| INV-01-12 | ReviewDecision 仅 APPROVE/REQUEST_CHANGES/REJECT 且只追加，仅 UserIdentity 可作出 | 任务看板 | PRD10 §4（L30-37） | 规则 | 已定义 |
| INV-01-13 | 看板"已批准"≠外部同步或发布完成，后续动作各自重新授权 | 任务看板 | PRD10 §4（L30-37） | 规则 | 已定义 |
| INV-01-14 | 输入版本变化：产出标 STALE、暂停审核、重新生成受影响内容 | 任务看板 | PRD10 §6（L46-52） | 规则 | 已定义 |
| INV-01-15 | Agent 越权/循环/超时/预算超限：停止后续节点、保留 Trace、WorkItem 转 BLOCKED | 任务看板 | PRD10 §6（L46-52） | 规则 | 已定义 |
| INV-01-16 | 审核人无能力/作用域或违反职责分离：拒绝决定并重新分派 | 任务看板 | PRD10 §6（L46-52） | 规则 | 已定义 |
| INV-01-17 | 依赖资源取消/归档：返回 409 与阻塞引用，不级联删除证据 | 任务看板 | PRD10 §6（L46-52） | 规则 | 已定义 |
| INV-01-18 | AC-01 AI 产出进入人工审核（PENDING_REVIEW + 绑定精确版本/摘要的 ReviewTask，不直接批准） | 任务看板 | PRD10 §7 AC-01（L55-60） | 验收 | 已定义 |
| INV-01-19 | AC-02 退回不覆盖历史（V2 重新检查/审核，V1/决定/Trace 可查） | 任务看板 | PRD10 §7 AC-02（L61-66） | 验收 | 已定义 |
| INV-01-20 | AC-03 越权失败关闭（外部写入未授权则调用不发生、阻塞、记录 DENY） | 任务看板 | PRD10 §7 AC-03（L67-72） | 验收 | 已定义 |
| INV-01-21 | AC-04 聚合不篡改 Owner 状态（看板只读投影，不存第二份可写报告状态） | 任务看板 | PRD10 §7 AC-04（L73-78） | 验收 | 已定义 |
| INV-01-22 | WorkItem 定位与边界：统一编排单元，不取代业务实体、不保存产出物正文、不取代 AgentSession/ExecutionTask/ReviewTask | 任务看板 | 05 §5.5.1（L424-448） | 规则 | 已定义 |
| INV-01-23 | WorkItem 类型体系：STRATEGY/PLAN/TEST_DESIGN/AUTOMATION_WEB/AUTOMATION_API/EXECUTION/RESULT_ANALYSIS/DEFECT/REPORT/KNOWLEDGE/GENERAL | 任务看板 | 05 §5.5.2（L449-466） | 规则 | 已定义 |
| INV-01-24 | WorkItem 最小字段集（id/tenantId/workspaceId/releaseId/parentWorkItemId/type/title/objective/acceptanceCriteria/constraints/priority/riskLevel/status/currentActorType/humanAssigneeId/agentId/requiresReview/reviewPolicyId/dueAt/blockedReason/createdBy/lockVersion 等 25 字段） | 任务看板 | 05 §5.5.3（L467-497） | 规则 | 已定义 |
| INV-01-25 | objective 与 acceptanceCriteria 必须由测试人员创建或确认，AI 不得扩大顶层目标与授权范围 | 任务看板 | 05 §5.5.3（L467-497） | 规则 | 已定义 |
| INV-01-26 | 统一任务状态机 + currentActorType 派生展示标签（AI 处理中/人工处理中/系统执行中/待审核） | 任务看板 | 05 §5.5.4（L498-529） | 规则 | 已定义 |
| INV-01-27 | 状态机核心规则 6 条：requiresReview 不得直入 DONE；PENDING_REVIEW 前必须有版本化 OUTPUT；APPROVED 前必须有已解决 ReviewTask+签名；版本一致性校验；BLOCKED 结构化原因；DONE 后不得原地修改 | 任务看板 | 05 §5.5.4（L498-529） | 规则 | 已定义 |
| INV-01-28 | WorkItemArtifact 关联对象：role（INPUT/OUTPUT/REVIEW_TARGET/EVIDENCE）、精确版本、受控 artifactType 注册表、同租户校验、删除不级联 | 任务看板 | 05 §5.5.5（L530-551） | 规则 | 已定义 |
| INV-01-29 | WorkItemRun 尝试记录与 WorkItemEvent 只追加事件（周期/等待/SLA 指标必须从事件计算） | 任务看板 | 05 §5.5.6（L552-572） | 规则 | 已定义 |
| INV-01-30 | ReviewTask 关系规则：按 reviewPolicy 创建、指向精确 REVIEW_TARGET、REQUEST_CHANGES/REJECT 转 REWORK、全部通过才 APPROVED、审核人权限校验、AI 不能作为正式批准人、超时不自动批准/拒绝 | 任务看板 | 05 §5.5.7（L573-582） | 规则 | 已定义 |
| INV-01-31 | 父子任务与依赖：WorkItemDependency 显式记录、环检测拒绝、取消父任务不级联取消已开始子任务 | 任务看板 | 05 §5.5.8（L583-590） | 规则 | 已定义 |
| INV-01-32 | 任务看板视图：我的待审核/AI工作中/退回重做/待执行执行中/阻塞与风险/全部工作项/管理视图 7 类视图 | 任务看板 | 05 §5.5.9（L591-602） | 功能 | 已定义 |
| INV-01-33 | 看板权限能力点 8 项（workitem:create/assign/run/interrupt/edit/review/approve/cancel/admin），最终动作取用户∩Agent∩Workflow 交集 fail-closed | 任务看板 | 05 §5.5.10（L603-620） | 规则 | 已定义 |
| INV-01-34 | 看板指标体系（Lead/Cycle Time、AI/人工/审核/阻塞时间、通过率/返工、AI 成功率/成本、WIP/吞吐/SLA、产出物生成到批准时间、采用率等），指标基于事件计算 | 任务看板 | 05 §5.5.11（L621-635） | 非功能 | 已定义 |
| INV-01-35 | GWT-5.5.12-1 正式产出审核门禁（requiresReview=true 只能进 PENDING_REVIEW） | 任务看板 | 05 §5.5.12（L636-661） | 验收 | 已定义 |
| INV-01-36 | GWT-5.5.12-2 审核版本一致性（并发更新则原审核不得批准新版本） | 任务看板 | 05 §5.5.12（L636-661） | 验收 | 已定义 |
| INV-01-37 | GWT-5.5.12-3 完整追溯（报告可反查输入/策略/用例/代码/结果/分析/审核/Trace） | 任务看板 | 05 §5.5.12（L636-661） | 验收 | 已定义 |
| INV-01-38 | GWT-5.5.12-4 AI 越权阻断（无正式资产写入权限时发布/外部提交被拒并转 BLOCKED） | 任务看板 | 05 §5.5.12（L636-661） | 验收 | 已定义 |
| INV-01-39 | GWT-5.5.12-5 失败与重试分离（重试额度内新建 attempt 保持 IN_PROGRESS，超界转 BLOCKED） | 任务看板 | 05 §5.5.12（L636-661） | 验收 | 已定义 |
| INV-01-40 | GWT-5.5.12-6 阻塞可恢复（输入补齐且权限通过可从 BLOCKED 恢复 READY，保留阻塞时长/原因） | 任务看板 | 05 §5.5.12（L636-661） | 验收 | 已定义 |
| INV-01-41 | GWT-5.5.12-7 终态不可篡改（DONE 后拒绝原地修改，引导创建修订 WorkItem） | 任务看板 | 05 §5.5.12（L636-661） | 验收 | 已定义 |
| INV-01-42 | GWT-5.5.12-8 任务依赖无环（保存依赖时拒绝循环并指出路径） | 任务看板 | 05 §5.5.12（L636-661） | 验收 | 已定义 |
| INV-01-43 | 八类正式产出物范围界定（策略/计划/用例/自动化代码/结果分析/缺陷/报告/知识条目；支撑资产版本化但不强制逐对象一级审核） | 任务看板* | 05 §5.6.1（L664-678） | 规则 | 已定义 |
| INV-01-44 | 通用产出物审核接口（artifactId/type/workspaceId/releaseId/version/contentDigest/reviewStatus/sourceTrace/generatedByAgentId/editedBy/approvedBy/reviewTaskIds/supersedesVersion/changeSummary） | 任务看板* | 05 §5.6.2（L679-701） | 规则 | 已定义 |
| INV-01-45 | 审核参与者责任矩阵（AI Producer/Human Editor/Reviewer/Approver/Artifact Owner/System 各自责任与禁止事项） | 任务看板* | 05 §5.6.3（L702-714） | 规则 | 已定义 |
| INV-01-46 | 审核策略类型：SINGLE_REVIEW/FOUR_EYES/CODE_REVIEW/EXTERNAL_WRITE/REPORT_SIGNOFF/KNOWLEDGE_PUBLISH，只能调严不可放宽 | 任务看板* | 05 §5.6.4（L715-727） | 规则 | 已定义 |
| INV-01-47 | 正式产出物审核矩阵（8 类产出物 × AI 职责/人工审核重点/批准责任/正式生效条件） | 任务看板* | 05 §5.6.5（L728-740） | 规则 | 已定义 |
| INV-01-48 | 各产出物最低内容门禁（不满足不得进入 PENDING_REVIEW；门禁失败不得用人工审核工单掩盖） | 任务看板* | 05 §5.6.6（L741-755） | 规则 | 已定义 |
| INV-01-49 | 审核操作与版本规则（APPROVE/REQUEST_CHANGES/REJECT/COMMENT；7 条版本规则：修改必新版本、摘要不可变、审核失效、不可覆盖、精确引用、影响分析、废弃≠删除） | 任务看板* | 05 §5.6.7（L756-774） | 规则 | 已定义 |
| INV-01-50 | ReviewTask 最小审核记录字段（workItemId/artifactType/version/contentDigest/policyType/reviewRole/assigneeId/decision/comments/diffRef/checkResults/decidedAt/signature 等 14 字段） | 任务看板* | 05 §5.6.8（L775-795） | 规则 | 已定义 |
| INV-01-51 | 直接人工修改与 AI 重做规则（直接修改不自动获批、AI 必须读结构化意见输出变更摘要、真实 Diff、HIGH/CRITICAL 主 Editor 不得唯一 Approver、返工超限转 BLOCKED） | 任务看板* | 05 §5.6.9（L796-804） | 规则 | 已定义 |
| INV-01-52 | GWT-5.6.10-1 正式用例迁移（批准 v2 固化并发布，v1/未批准 v3 不得被执行计划选中） | 任务看板* | 05 §5.6.10（L805-836） | 验收 | 已定义 |
| INV-01-53 | GWT-5.6.10-2 代码发布门禁（静态检查失败拒绝批准，备注不得绕过） | 任务看板* | 05 §5.6.10（L805-836） | 验收 | 已定义 |
| INV-01-54 | GWT-5.6.10-3 外部 Bug 写入（无 EXTERNAL_WRITE 批准时外部调用被拒并记越权审计） | 任务看板* | 05 §5.6.10（L805-836） | 验收 | 已定义 |
| INV-01-55 | GWT-5.6.10-4 报告数据一致性（快照变化后拒绝沿用旧摘要签字） | 任务看板* | 05 §5.6.10（L805-836） | 验收 | 已定义 |
| INV-01-56 | GWT-5.6.10-5 知识发布（缺适用范围/来源保持草稿并阻止创建可批准发布任务） | 任务看板* | 05 §5.6.10（L805-836） | 验收 | 已定义 |
| INV-01-57 | GWT-5.6.10-6 高风险职责分离（HIGH 风险主 Editor 不能作为唯一 Approver） | 任务看板* | 05 §5.6.10（L805-836） | 验收 | 已定义 |
| INV-01-58 | GWT-5.6.10-7 人工修改使审核失效（v1 未完成审核不适用于 v2） | 任务看板* | 05 §5.6.10（L805-836） | 验收 | 已定义 |
| INV-01-59 | GWT-5.6.10-8 AI 重做差异可见（逐项采纳状态 + v1→v2 真实 Diff + 未采纳原因） | 任务看板* | 05 §5.6.10（L805-836） | 验收 | 已定义 |
| INV-01-60 | GWT-5.6.10-9 批准后不可覆盖（PUBLISHED 报告修改须建 v2 修订工作项） | 任务看板* | 05 §5.6.10（L805-836） | 验收 | 已定义 |
| INV-01-61 | GWT-5.6.10-10 下游只使用批准版本（v3 PENDING_REVIEW 只能进隔离试验且不得产生正式质量结论） | 任务看板* | 05 §5.6.10（L805-836） | 验收 | 已定义 |
| INV-01-62 | 任务看板实体唯一业务所有者（WorkItem/WorkItemArtifact/WorkItemRun/WorkItemEvent/WorkItemDependency/ReviewTask/ReviewAssignment） | 任务看板 | 05 §5.12.2（L2077-2088） | 规则 | 已定义 |
| INV-01-63 | GWT-5.12.12-1 任务与正文分离（任务状态变化只更新看板对象，不改策略正文/审核摘要） | 任务看板 | 05 §5.12.12（L2235-2268） | 验收 | 已定义 |
| INV-01-64 | 模块职责承诺：WorkItem/ReviewTask/ReviewDecision 为看板核心产出，AI 拆分派发+人工审核裁决 | 任务看板 | 地图 §2 模块表（L19-32） | 规则 | 仅原则性声明 |

> *标注：§5.6 正式产出物与审核契约横跨全部 8 个业务模块，本清单按「ReviewTask 归任务看板」（05 §5.12.1 规则 4）整体计入任务看板，但其中策略/计划/用例/代码/分析/缺陷/报告/知识的具体审核内容分别由各 Owner 模块 PRD 承接。

### 2.2 模块二：知识库（PRD11 + 05 §5.10/§5.12.3）

| 条目编号 | 需求名称 | 所属模块 | 需求来源 | 需求类型 | 状态 |
|---|---|---|---|---|---|
| INV-02-01 | 来源导入：文件/URL/集成/手工/流量，固化原文/定位/摘要/授权/时间，AI 解析分类+敏感性提示，人工确认范围/冲突 | 知识库 | PRD11 §2（L11-22） | 功能 | 已定义 |
| INV-02-02 | 需求版本：RequirementDocument 稳定根+不可变版本，保留 SourceTrace，AI 抽取章节/规则/变更摘要，人工裁决歧义 | 知识库 | PRD11 §2（L11-22） | 功能 | 已定义 |
| INV-02-03 | API 契约：APIContract 稳定根/Version/Operation-Schema 版本/DECLARED-OBSERVED 分层，AI 规范化+漂移分析，人工批准基线/冲突 | 知识库 | PRD11 §2（L11-22） | 功能 | 已定义 |
| INV-02-04 | 契约基线：为 Release 和用途固定契约版本/摘要集合，AI 推荐受影响契约，人工确认关键接口范围 | 知识库 | PRD11 §2（L11-22） | 功能 | 已定义 |
| INV-02-05 | 知识条目：草稿/审核/发布/失效/归档全生命周期，记录适用/失效条件和来源 | 知识库 | PRD11 §2（L11-22） | 功能 | 已定义 |
| INV-02-06 | 检索：关键词/向量/图谱混合检索，返回来源/版本/相关性解释，用户可排除错误来源 | 知识库 | PRD11 §2（L11-22） | 功能 | 已定义 |
| INV-02-07 | 候选治理：重复/冲突/陈旧/敏感/低证据候选聚类与合并建议，人工决定合并/发布/拒绝 | 知识库 | PRD11 §2（L11-22） | 功能 | 已定义 |
| INV-02-08 | SourceSnapshot 不可变，重新抓取产生新快照 | 知识库 | PRD11 §3（L23-31） | 规则 | 已定义 |
| INV-02-09 | APIContract 由知识库唯一拥有，Mock/设计/执行只引用 APIContractVersion/Baseline | 知识库 | PRD11 §3（L23-31） | 规则 | 已定义 |
| INV-02-10 | DECLARED/OBSERVED/MANUAL/MERGED 必须标记来源，不静默覆盖 | 知识库 | PRD11 §3（L23-31） | 规则 | 已定义 |
| INV-02-11 | KnowledgeEntry 为八类正式产出物之一，至少一名人类批准后才可 PUBLISHED | 知识库 | PRD11 §3（L23-31） | 规则 | 已定义 |
| INV-02-12 | 检索结果必须带 sourceTrace/version/digest/适用范围，Agent 不得把高相似度当事实 | 知识库 | PRD11 §3（L23-31） | 规则 | 已定义 |
| INV-02-13 | 来源撤权/敏感性变化：停止新增使用并标记受影响产出物待重评，不删除历史证据 | 知识库 | PRD11 §3（L23-31） | 规则 | 已定义 |
| INV-02-14 | 文档破损/加密/格式不支持：保留导入失败记录转人工补录/转换，不编造解析内容 | 知识库 | PRD11 §5（L41-47） | 规则 | 已定义 |
| INV-02-15 | DECLARED 与 OBSERVED 冲突：同时保留、创建冲突 WorkItem，禁止自动合并为权威 | 知识库 | PRD11 §5（L41-47） | 规则 | 已定义 |
| INV-02-16 | 依赖内容摘要变化：使用方版本标 STALE 并重新评估 | 知识库 | PRD11 §5（L41-47） | 规则 | 已定义 |
| INV-02-17 | 无有效 Eval 校准记录：检索分数仅排序，不自动发布知识或选择契约真相 | 知识库 | PRD11 §5（L41-47） | 规则 | 已定义 |
| INV-02-18 | AC-01 来源可追溯（规则可定位 SourceSnapshot/文档版本/原文位置，摘要匹配） | 知识库 | PRD11 §6 AC-01（L50-55） | 验收 | 已定义 |
| INV-02-19 | AC-02 契约冲突不静默覆盖（两类证据并存+冲突，不改已批准版本） | 知识库 | PRD11 §6 AC-02（L56-61） | 验收 | 已定义 |
| INV-02-20 | AC-03 知识发布需要人（PENDING_REVIEW + ReviewTask 绑定版本/摘要，Agent 不能发布） | 知识库 | PRD11 §6 AC-03（L62-67） | 验收 | 已定义 |
| INV-02-21 | AC-04 精确基线可复现（原执行仍解析旧版本摘要，新版本不自动替换历史基线） | 知识库 | PRD11 §6 AC-04（L68-73） | 验收 | 已定义 |
| INV-02-22 | APIContract 唯一写入所有者裁决：知识库唯一，其余 7 模块只读消费/发起请求（含各自可否直接修改的 8 行职责表） | 知识库 | 05 §5.10.1（L1571-1587） | 规则 | 已定义 |
| INV-02-23 | 三层对象分层：SourceSnapshot/APIContractVersion/APIContractBaseline + APIObservation/ContractCheckResult，各层变化方式与断言依据 | 知识库 | 05 §5.10.2（L1588-1610） | 规则 | 已定义 |
| INV-02-24 | APIContract 稳定身份（id/workspaceId/name/serviceKey/protocol/description/owningTeamRef/currentVersionId/publishedVersionId/status；baseUrl 不属于稳定身份） | 知识库 | 05 §5.10.3（L1611-1630） | 规则 | 已定义 |
| INV-02-25 | SourceSnapshot 最小字段与约束（sourceType/sourceIntegrationId/sourceLocator/fetchedRevision/rawContentRef/rawDigest/mediaType/fetchStatus/fetchedByActor/fetchedAt；防内网探测、必须全 SHA、失败保留快照、人工录入也成快照） | 知识库 | 05 §5.10.4（L1631-1656） | 规则 | 已定义 |
| INV-02-26 | APIContractVersion 与 APIOperation 最小字段与约束（sourceKind、parserVersion、normalizationRulesVersion、validationStatus、breakingChangeLevel、changeSummary；operationVersionId 绑定；不得静默追加未声明响应；手工修正必须新版本） | 知识库 | 05 §5.10.5（L1657-1692） | 规则 | 已定义 |
| INV-02-27 | 契约校验/Diff/人工审核规则（8 条：确定性校验清单、AI 不能批准、精确 versionId+digest、BREAKING 用 FOUR_EYES、偏差理由记录、发布不自动替换基线、Reviewer 与修改人分离） | 知识库 | 05 §5.10.6（L1693-1716） | 规则 | 已定义 |
| INV-02-28 | APIContractBaseline（purpose=TEST_DESIGN/MOCK/CONTRACT_ANALYSIS、版本不可覆盖成员）与 ExecutionContractBaseline（执行冻结快照、只追加、失效转 BLOCKED 不自动切最新） | 知识库* | 05 §5.10.7（L1717-1740） | 规则 | 已定义 |
| INV-02-29 | 运行观察与契约偏差：APIObservation/ContractCheckResult 最小内容，未检查≠通过、INCONCLUSIVE 不得报告为一致、观察不能直接写版本、TestReport 必须披露基线/已检查/偏差/未检查/不可判定数 | 知识库* | 05 §5.10.8（L1741-1757） | 规则 | 已定义 |
| INV-02-30 | 写入命令面：ImportAPIContractSource 等 9 个命令的唯一执行者与结果；删除只允许归档，被引用资产禁止物理删除 | 知识库 | 05 §5.10.9（L1758-1775） | 规则 | 已定义 |
| INV-02-31 | GWT-5.10.11-1 唯一写入所有者（向导上传只创建一套 SourceSnapshot/APIContract） | 知识库 | 05 §5.10.11（L1792-1831） | 验收 | 已定义 |
| INV-02-32 | GWT-5.10.11-2 原始来源不可覆盖（两快照并存可追溯各自契约版本） | 知识库 | 05 §5.10.11（L1792-1831） | 验收 | 已定义 |
| INV-02-33 | GWT-5.10.11-3 相同内容不伪造版本（NO_CONTENT_CHANGE 不生成虚假新版本） | 知识库 | 05 §5.10.11（L1792-1831） | 验收 | 已定义 |
| INV-02-34 | GWT-5.10.11-4 流量不能改写声明契约（只生成 Observation 与变更建议） | 知识库 | 05 §5.10.11（L1792-1831） | 验收 | 已定义 |
| INV-02-35 | GWT-5.10.11-5 审核绑定精确摘要（digest 变化必须新版本重新审核） | 知识库 | 05 §5.10.11（L1792-1831） | 验收 | 已定义 |
| INV-02-36 | GWT-5.10.11-6 破坏性变更双人审核（BREAKING 要求 FOUR_EYES） | 知识库 | 05 §5.10.11（L1792-1831） | 验收 | 已定义 |
| INV-02-37 | GWT-5.10.11-7 执行不跟随最新版漂移（冻结 v3 继续用 v3 + 影响 WorkItem） | 知识库 | 05 §5.10.11（L1792-1831） | 验收 | 已定义 |
| INV-02-38 | GWT-5.10.11-8 同路径跨服务共存（serviceKey+version 区分） | 知识库 | 05 §5.10.11（L1792-1831） | 验收 | 已定义 |
| INV-02-39 | GWT-5.10.11-9 外部引用可复现（$ref 锁定 revision+digest，仅 branch 不能批准） | 知识库 | 05 §5.10.11（L1792-1831） | 验收 | 已定义 |
| INV-02-40 | GWT-5.10.11-10 未检查不等于通过（报告分别显示已检查/未检查数） | 知识库 | 05 §5.10.11（L1792-1831） | 验收 | 已定义 |
| INV-02-41 | GWT-5.10.11-11 真实旧消费者不产生双写（限期适配器内部仍调知识库命令） | 知识库 | 05 §5.10.11（L1792-1831） | 验收 | 已定义 |
| INV-02-42 | GWT-5.10.11-12 引用资产不可物理删除（只允许废弃/归档） | 知识库 | 05 §5.10.11（L1792-1831） | 验收 | 已定义 |
| INV-02-43 | 知识库实体唯一业务所有者（RequirementDocument/SourceSnapshot/APIContract/APIContractVersion/APIOperationVersion/APIContractBaseline/KnowledgeEntry/KnowledgeVector/KnowledgeGraphNode-Edge/KnowledgeCandidate/SourceTrace；AIContext 退场拆为 AIContextSnapshot） | 知识库 | 05 §5.12.3（L2089-2107） | 规则 | 已定义 |
| INV-02-44 | GWT-5.12.12-2 知识候选不能跨域发布（Agent 直接创建 Published KnowledgeEntry 被拒） | 知识库 | 05 §5.12.12（L2235-2268） | 验收 | 已定义 |
| INV-02-45 | GWT-5.12.12-5 API 契约无双写（自动化开发发现 Schema 错误只生成变更 WorkItem） | 知识库 | 05 §5.12.12（L2235-2268） | 验收 | 已定义 |
| INV-02-46 | 总纲规则 8：APIContract 由知识库模块唯一拥有，设计/Mock/执行均引用精确版本基线 | 知识库 | 总纲 §5 规则 8（L31-38） | 规则 | 已定义 |
| INV-02-47 | 模块职责承诺：解析来源/规范化契约/识别冲突/提炼知识草稿（AI）+ 裁决来源冲突/审核知识契约（人工），产出 SourceSnapshot/Requirement/APIContract/KnowledgeEntry | 知识库 | 地图 §2 模块表（L19-32） | 规则 | 仅原则性声明 |

> *标注：§5.10.7/5.10.8 中 ExecutionContractBaseline、APIObservation、ContractCheckResult 的持久化归测试执行（见 05 §5.12.6），但契约语义与报告披露规则属知识库契约，本清单计入知识库，执行侧以 INV-05 引用。

### 2.3 模块三：测试策划与设计（PRD12 + 05 §5.7/§5.12.4）

| 条目编号 | 需求名称 | 所属模块 | 需求来源 | 需求类型 | 状态 |
|---|---|---|---|---|---|
| INV-03-01 | TestStrategy 正式产出物必需内容（目标/范围/风险/测试类型/方法/准入退出/环境数据自动化缺陷策略） | 测试策划与设计 | PRD12 §2（L9-18） | 规则 | 已定义 |
| INV-03-02 | TestPlan 正式产出物必需内容（策略版本/Release/目标/类型/范围/里程碑/资源/依赖/时间/验收准则） | 测试策划与设计 | PRD12 §2（L9-18） | 规则 | 已定义 |
| INV-03-03 | TestCase 正式产出物必需内容（前置/步骤/数据引用/预期/断言/优先级/类型/SourceTrace） | 测试策划与设计 | PRD12 §2（L9-18） | 规则 | 已定义 |
| INV-03-04 | TestingIR/BusinessRule/Assertion/CoverageReport/TestScenario/DesignTestCase 为设计链实体/中间产物，与三类正式产出物不同生命周期 | 测试策划与设计 | PRD12 §2（L9-18） | 规则 | 已定义 |
| INV-03-05 | 范围输入：读取 RequirementVersion/APIContractBaseline/Release/已审核知识，人工确认关键路径/排除项/冲突来源 | 测试策划与设计 | PRD12 §3（L19-30） | 功能 | 已定义 |
| INV-03-06 | TestingIR 编译：规则/领域/状态机/断言/SourceTrace，人工裁决关键规则冲突，IR 验证≠业务批准 | 测试策划与设计 | PRD12 §3（L19-30） | 功能 | 已定义 |
| INV-03-07 | 策略草稿：风险驱动策略生成+结构检查，人工审核范围/风险/门槛引用 | 测试策划与设计 | PRD12 §3（L19-30） | 功能 | 已定义 |
| INV-03-08 | 计划草稿：阶段 DAG/里程碑/资源/验收准则生成，人工审核资源/时间/依赖/责任 | 测试策划与设计 | PRD12 §3（L19-30） | 功能 | 已定义 |
| INV-03-09 | 场景/用例生成：正向/反向/边界/权限/状态/兼容/异常，人工批改业务步骤/数据/预期 | 测试策划与设计 | PRD12 §3（L19-30） | 功能 | 已定义 |
| INV-03-10 | 覆盖分析：Requirement/API/Rule/Scenario/TestCase 映射与缺口，人工决定接受缺口或补充草稿 | 测试策划与设计 | PRD12 §3（L19-30） | 功能 | 已定义 |
| INV-03-11 | 版本/Diff：变更摘要与受影响链生成，人工审核精确版本不沿用陈旧批准 | 测试策划与设计 | PRD12 §3（L19-30） | 功能 | 已定义 |
| INV-03-12 | 策略/计划/执行计划三概念不得合并（TestStrategy 替代 TestDesignPlan；TestPlan 表达项目执行安排；ExecutionPlan 表达机器执行配置） | 测试策划与设计 | PRD12 §4（L31-38） | 规则 | 已定义 |
| INV-03-13 | DesignTestCase 是 AI 设计草稿，只有通过检查+人工审核后才能迁移为 TestCaseVersion | 测试策划与设计 | PRD12 §4（L31-38） | 规则 | 已定义 |
| INV-03-14 | Coverage 必须声明分子/分母/排除项/映射证据，不得用生成数量代替覆盖 | 测试策划与设计 | PRD12 §4（L31-38） | 规则 | 已定义 |
| INV-03-15 | 正式版本状态机 DRAFT/GENERATING/PENDING_REVIEW/CHANGES_REQUESTED/APPROVED/PUBLISHED/REJECTED/STALE/ARCHIVED | 测试策划与设计 | PRD12 §4（L31-38） | 规则 | 已定义 |
| INV-03-16 | 任一来源/契约版本变化应影响分析并标记相关草稿/已批准版本待重评，而非静默改写 | 测试策划与设计 | PRD12 §4（L31-38） | 规则 | 已定义 |
| INV-03-17 | 来源质量差/规则冲突：停止关键路径生成，创建 BLOCK_HUMAN | 测试策划与设计 | PRD12 §6（L49-55） | 规则 | 已定义 |
| INV-03-18 | AI 不可用：允许人工创建版本并继续使用相同检查/审核流程 | 测试策划与设计 | PRD12 §6（L49-55） | 规则 | 已定义 |
| INV-03-19 | 覆盖映射不足：标记 INCONCLUSIVE 或缺口，不自动补齐后静默发布 | 测试策划与设计 | PRD12 §6（L49-55） | 规则 | 已定义 |
| INV-03-20 | 策略未批准：计划可生成草稿但不能批准/启动执行 | 测试策划与设计 | PRD12 §6（L49-55） | 规则 | 已定义 |
| INV-03-21 | AC-01 策略、计划、执行计划分离（建 TestPlanVersion 不改策略、不建 Runner 配置） | 测试策划与设计 | PRD12 §7 AC-01（L58-63） | 验收 | 已定义 |
| INV-03-22 | AC-02 AI 用例不能直接入库（机器检查全 PASS 仍需 ReviewTask + 人工批准） | 测试策划与设计 | PRD12 §7 AC-02（L64-69） | 验收 | 已定义 |
| INV-03-23 | AC-03 覆盖分母透明（90% 可查分子/分母/排除项/未覆盖项/每条 SourceTrace） | 测试策划与设计 | PRD12 §7 AC-03（L70-75） | 验收 | 已定义 |
| INV-03-24 | AC-04 陈旧版本重评（基线切换 breaking change 后旧批准不自动覆盖 V2） | 测试策划与设计 | PRD12 §7 AC-04（L76-81） | 验收 | 已定义 |
| INV-03-25 | 四概念裁决：Release（业务版本，非正式审核产出物）/TestStrategy/TestPlan/ExecutionPlan 各自回答的问题与审核属性 | 测试策划与设计 | 05 §5.7.1（L839-863） | 规则 | 已定义 |
| INV-03-26 | TestDesignPlan 退场裁决（策略内容迁 TestStrategy、测试方案中文名废弃、TestScenario 改归 testPlanId、TestPlan 不再承担发布里程碑、legacyRef 保留追溯） | 测试策划与设计 | 05 §5.7.2（L864-878） | 规则 | 已定义 |
| INV-03-27 | TestStrategy 最小字段（19 字段）与约束：同一时刻单 PUBLISHED 基线、多来源关联、默认 SINGLE_REVIEW/高风险 FOUR_EYES、AI 不能发布策略基线 | 测试策划与设计 | 05 §5.7.4（L892-920） | 规则 | 已定义 |
| INV-03-28 | TestPlan 最小字段（18 字段）与约束：必须绑定已批准策略版本才能发布、草稿不得 ACTIVE、范围不得超出策略 inScope、WorkItem 是计划执行单元 | 测试策划与设计 | 05 §5.7.5（L921-951） | 规则 | 已定义 |
| INV-03-29 | TestScenario 归属 TestPlan；DesignTestCase 归属 TestScenario 并在批准后形成可跨计划复用的正式 TestCase；计划完成不删除已批准用例 | 测试策划与设计 | 05 §5.7.6（L952-959） | 规则 | 已定义 |
| INV-03-30 | ExecutionPlan 与 TestPlan 语义区分（6 项对比）+ ExecutionPlan 目标新增字段（testPlanId/releaseId/精确版本选择/environmentId/scopeConfigs/触发/并发/Runner策略/configurationDigest） | 测试策划与设计 | 05 §5.7.7（L960-986） | 规则 | 已定义 |
| INV-03-31 | 创建正式 ExecutionTask 的 5 项前置条件（计划批准且 NOT_STARTED/ACTIVE、资产版本批准、Environment 同 Workspace、Secret/Runner/外访权限通过、配置摘要与授权一致） | 测试策划与设计* | 05 §5.7.7（L960-986） | 规则 | 已定义 |
| INV-03-32 | 变更影响规则 6 条（策略新版→影响分析不自动切换；计划关键变化→新版本重审；计划新版不自动改场景用例；ExecutionPlan 配置变→旧授权失效；Release 归档禁新建执行；Testing→Released 必须引用已签字报告或例外） | 测试策划与设计* | 05 §5.7.8（L987-995） | 规则 | 已定义 |
| INV-03-33 | 文档阶段迁移规则（TestDesignPlan 各字段→TestStrategy/多来源映射、TestScenario.testPlanId、ExecutionPlan 精确绑定，迁移后重新验证可信链） | 测试策划与设计 | 05 §5.7.9（L996-1013） | 规则 | 已定义 |
| INV-03-34 | GWT-5.7.10-1 概念唯一性（不再出现独立测试方案实体或把 TestPlan 称为发布版本） | 测试策划与设计 | 05 §5.7.10（L1014-1045） | 验收 | 已定义 |
| INV-03-35 | GWT-5.7.10-2 策略先于计划生效（v2 PENDING_REVIEW 时拒绝发布绑定计划但允许草稿） | 测试策划与设计 | 05 §5.7.10（L1014-1045） | 验收 | 已定义 |
| INV-03-36 | GWT-5.7.10-3 一个版本多计划（多计划绑定同一批准策略，独立负责人/周期/验收） | 测试策划与设计 | 05 §5.7.10（L1014-1045） | 验收 | 已定义 |
| INV-03-37 | GWT-5.7.10-4 计划范围不得越界（OutOfScope 任务阻止发布或走策略例外审核） | 测试策划与设计 | 05 §5.7.10（L1014-1045） | 验收 | 已定义 |
| INV-03-38 | GWT-5.7.10-5 策略变更不静默传播（三个影响分析项，仍引用 v1 直至人工确认迁移） | 测试策划与设计 | 05 §5.7.10（L1014-1045） | 验收 | 已定义 |
| INV-03-39 | GWT-5.7.10-6 场景归属明确（可定位 TestPlan/策略版本/Release/来源需求，不依赖废弃 TestDesignPlan） | 测试策划与设计 | 05 §5.7.10（L1014-1045） | 验收 | 已定义 |
| INV-03-40 | GWT-5.7.10-7 计划与执行计划分离（ExecutionPlan 只选可执行资产，不复制人工任务） | 测试策划与设计 | 05 §5.7.10（L1014-1045） | 验收 | 已定义 |
| INV-03-41 | GWT-5.7.10-8 批准版本执行（引用 PENDING_REVIEW 脚本的正式执行被拒） | 测试策划与设计* | 05 §5.7.10（L1014-1045） | 验收 | 已定义 |
| INV-03-42 | GWT-5.7.10-9 发布状态有证据（无签字报告/例外时 Testing→Released 被拒） | 测试策划与设计* | 05 §5.7.10（L1014-1045） | 验收 | 已定义 |
| INV-03-43 | GWT-5.7.10-10 历史链不丢失（legacyRef/Source Trace 反查 TestStrategy 及下游） | 测试策划与设计 | 05 §5.7.10（L1014-1045） | 验收 | 已定义 |
| INV-03-44 | 测试策划与设计实体唯一业务所有者（TestStrategy/TestPlan/TestingIR/BusinessRule/TestScenario/DesignTestCase/TestCase/Assertion/TestSuite/TestSuiteCaseMapping） | 测试策划与设计 | 05 §5.12.4（L2108-2122） | 规则 | 已定义 |
| INV-03-45 | 模块职责承诺：AI 编译 TestingIR/生成草稿/覆盖分析；人工审核策略/计划/用例；产出 TestStrategy/TestPlan/TestCase | 测试策划与设计 | 地图 §2 模块表（L19-32） | 规则 | 仅原则性声明 |

> *标注：INV-03-31/32 及 GWT-5.7.10-8/9 的落点涉及测试执行（ExecutionPlan/ExecutionTask）与平台管理（Release 状态），其执行侧行为在 INV-05/INV-08 中亦有对应条目，此处按 §5.7 契约归属计入策划设计。

### 2.4 模块四：自动化测试开发（PRD13 + 05 §5.8/§5.12.5）

| 条目编号 | 需求名称 | 所属模块 | 需求来源 | 需求类型 | 状态 |
|---|---|---|---|---|---|
| INV-04-01 | 脚本稳定根/版本：按能力命名，版本记录语言/框架/运行时/依赖锁/来源模式/摘要，代码 Review 后批准 | 自动化测试开发 | PRD13 §2（L9-21） | 功能 | 已定义 |
| INV-04-02 | 用例绑定：一脚本版本覆盖多 TestCaseVersion，一用例可有多种自动化实现，审核绑定真实性 | 自动化测试开发 | PRD13 §2（L9-21） | 功能 | 已定义 |
| INV-04-03 | Web 自动化：页面对象/组件、Locator、等待、截图/视频配置，AI 生成与诊断候选，人工审核关键路径/稳定性/敏感操作 | 自动化测试开发 | PRD13 §2（L9-21） | 功能 | 已定义 |
| INV-04-04 | API 自动化：基于 APIContractVersion 生成请求/断言/鉴权引用/数据 | 自动化测试开发 | PRD13 §2（L9-21） | 功能 | 已定义 |
| INV-04-05 | 代码检查：格式/类型/静态安全/依赖/契约绑定/受控试跑，检查 PASS 不替代代码批准 | 自动化测试开发 | PRD13 §2（L9-21） | 功能 | 已定义 |
| INV-04-06 | Locator：稳定根/版本、主/备选择器、证据和 supersedes，自愈候选需审核后才成正式版本 | 自动化测试开发 | PRD13 §2（L9-21） | 功能 | 已定义 |
| INV-04-07 | Mock/数据/视觉：Mock 绑定契约版本；数据含生成/脱敏/清理；视觉含视口/遮罩/摘要，人工审核业务约束/隐私风险 | 自动化测试开发 | PRD13 §2（L9-21） | 功能 | 已定义 |
| INV-04-08 | Git 模式：固定 repo、完整 commit SHA、path、blob SHA 和 digest，PR/补丁候选，仓库写入另行人工批准 | 自动化测试开发 | PRD13 §2（L9-21） | 功能 | 已定义 |
| INV-04-09 | AutomationScript 是八类正式产出物之一，AI 不能把检查 PASS 直接变成 APPROVED/PUBLISHED | 自动化测试开发 | PRD13 §3（L22-29） | 规则 | 已定义 |
| INV-04-10 | 执行只接收已批准脚本版本和完整依赖/运行时指纹；运行时临时修复产生候选新版本，不覆盖已冻结版本 | 自动化测试开发 | PRD13 §3（L22-29） | 规则 | 已定义 |
| INV-04-11 | 代码正文与 Secret 分离（secretRef 引用，日志/Trace 无明文） | 自动化测试开发 | PRD13 §3（L22-29） | 规则 | 已定义 |
| INV-04-12 | API 代码绑定 APIContractVersion，契约变化触发影响分析而非静默重生成覆盖 | 自动化测试开发 | PRD13 §3（L22-29） | 规则 | 已定义 |
| INV-04-13 | Locator 自愈默认只在单次运行尝试，正式资产变更走 Diff 和 ReviewTask | 自动化测试开发 | PRD13 §3（L22-29） | 规则 | 已定义 |
| INV-04-14 | 框架/Runner 能力不匹配：返回 RUNNER_CAPABILITY_MISSING 并阻塞，不降级为错误框架 | 自动化测试开发 | PRD13 §5（L40-46） | 规则 | 已定义 |
| INV-04-15 | 依赖无锁/来源不可信/安全扫描失败：禁止批准或执行 | 自动化测试开发 | PRD13 §5（L40-46） | 规则 | 已定义 |
| INV-04-16 | Secret 未授权：生成可审查模板但不试跑，记录 SECRET_ACCESS_DENIED | 自动化测试开发 | PRD13 §5（L40-46） | 规则 | 已定义 |
| INV-04-17 | Locator 多候选冲突或连续失败：停止自愈并人工定位 | 自动化测试开发 | PRD13 §5（L40-46） | 规则 | 已定义 |
| INV-04-18 | AC-01 多对多绑定（1 脚本覆盖 10 用例无需复制 10 份脚本） | 自动化测试开发 | PRD13 §6 AC-01（L49-54） | 验收 | 已定义 |
| INV-04-19 | AC-02 依赖可复现（缺 frameworkVersion/runtimeVersion/dependencyDigest 阻断发布与执行） | 自动化测试开发 | PRD13 §6 AC-02（L55-60） | 验收 | 已定义 |
| INV-04-20 | AC-03 自愈不污染正式资产（原 LocatorVersion 不变，新候选带证据进 ReviewTask） | 自动化测试开发 | PRD13 §6 AC-03（L61-66） | 验收 | 已定义 |
| INV-04-21 | AC-04 API 副作用受控（删除类 API 在目标环境/清理策略未授权时拒绝试跑/执行） | 自动化测试开发 | PRD13 §6 AC-04（L67-72） | 验收 | 已定义 |
| INV-04-22 | 自动化类型与 V1 支持状态（WEB/API 必须支持；MOBILE/PERFORMANCE 预留不承诺 V1；SECURITY 预留默认禁用） | 自动化测试开发 | 05 §5.8.2（L1070-1081） | 规则 | 部分定义 |
| INV-04-23 | AutomationScript 稳定身份最小字段（9 字段，移除 codeContent/version/testCaseId UNIQUE，primaryVersionId 只能指向 PUBLISHED） | 自动化测试开发 | 05 §5.8.3（L1082-1099） | 规则 | 已定义 |
| INV-04-24 | AutomationScriptVersion 最小字段（18 字段）与 MANAGED/GIT 唯一权威源规则（branch/PR 只能导航不能作执行证据、脱敏快照须与权威摘要一致） | 自动化测试开发 | 05 §5.8.4（L1100-1130） | 规则 | 已定义 |
| INV-04-25 | 用例绑定对象字段（scriptVersionId/testCaseId+version/role=PRIMARY-COVERED-SETUP-TEARDOWN/coverageNotes）与规则（新用例版本→影响分析、执行前绑定校验） | 自动化测试开发 | 05 §5.8.5（L1131-1149） | 规则 | 已定义 |
| INV-04-26 | Web/API 类型专属配置（WEB：browser/viewport/baseUrlRef/Locator版本/storage-auth 引用/截图视频 Trace 策略/运行时版本/清理恢复；API：protocol/baseUrlRef/APIContract 版本/authProfile/断言/幂等重放/速率限制；Typed Schema 版本化） | 自动化测试开发 | 05 §5.8.6（L1150-1173） | 规则 | 已定义 |
| INV-04-27 | AI 生成/人工修改与 Diff（生成必须交付 8 类信息：精确版本/文件清单/依赖变化/断言映射/运行清理说明/已知限制/真实 Unified Diff/自检结果；重做逐项标记采纳状态） | 自动化测试开发 | 05 §5.8.7（L1174-1188） | 规则 | 已定义 |
| INV-04-28 | AutomationCheckRun 最低检查基线 10 项（格式语法/静态检查/Secret 扫描/依赖许可证/安全扫描/用例断言映射/隔离试运行/Locator 健康/APIContract 一致性/清理幂等）+ 隔离 Runner 默认配置 + 豁免流程 | 自动化测试开发 | 05 §5.8.8（L1189-1209） | 规则 | 已定义 |
| INV-04-29 | Git 与外部写入（凭证归平台集成、AI 内部草稿区生成、push/PR 属 EXTERNAL_WRITE、批准必须针对 commit/blob/digest、提交后回读校验、内容变化不静默更新） | 自动化测试开发 | 05 §5.8.9（L1210-1217） | 规则 | 已定义 |
| INV-04-30 | Code Review 与发布（ReviewTask 展示 8 类信息；LOW/MEDIUM 至少一名 Reviewer、HIGH/CRITICAL 与外部写入/Secret 变化 FOUR_EYES、摘要一致性、PUBLISHED 可设 primary、废弃不删除历史） | 自动化测试开发 | 05 §5.8.10（L1218-1237） | 规则 | 已定义 |
| INV-04-31 | 正式执行绑定（引用 scriptVersionId 非 script.id/primaryVersionId；启动保存全量快照；默认只执行 PUBLISHED；PENDING_REVIEW 仅隔离试验+EXPERIMENTAL 标记；能力不足调度前失败转 BLOCKED；结果协议统一） | 自动化测试开发* | 05 §5.8.11（L1238-1246） | 规则 | 已定义 |
| INV-04-32 | GWT-5.8.13-1 一用例多实现（同用例允许多 AutomationScript 分别绑定） | 自动化测试开发 | 05 §5.8.13（L1261-1294） | 验收 | 已定义 |
| INV-04-33 | GWT-5.8.13-2 一脚本多用例（绑定记录精确用例版本与覆盖说明） | 自动化测试开发 | 05 §5.8.13（L1261-1294） | 验收 | 已定义 |
| INV-04-34 | GWT-5.8.13-3 Git 精确定位（缺 full SHA/path/blob SHA/digest 时拒绝，仅 branch 拒绝） | 自动化测试开发 | 05 §5.8.13（L1261-1294） | 验收 | 已定义 |
| INV-04-35 | GWT-5.8.13-4 强制检查不可绕过（Secret 扫描高风险拒绝批准，评论不能覆盖阻断） | 自动化测试开发 | 05 §5.8.13（L1261-1294） | 验收 | 已定义 |
| INV-04-36 | GWT-5.8.13-5 AI 外部写入受控（无 EXTERNAL_WRITE 批准时 push/PR 被拒并审计） | 自动化测试开发 | 05 §5.8.13（L1261-1294） | 验收 | 已定义 |
| INV-04-37 | GWT-5.8.13-6 审核摘要一致（批准 digest A 后内容变 B 则批准失效） | 自动化测试开发 | 05 §5.8.13（L1261-1294） | 验收 | 已定义 |
| INV-04-38 | GWT-5.8.13-7 试验与正式结果隔离（EXPERIMENTAL 结果不进正式报告/门禁） | 自动化测试开发 | 05 §5.8.13（L1261-1294） | 验收 | 已定义 |
| INV-04-39 | GWT-5.8.13-8 执行版本不可漂移（primaryVersionId 更新不影响既有 ExecutionPlan） | 自动化测试开发 | 05 §5.8.13（L1261-1294） | 验收 | 已定义 |
| INV-04-40 | GWT-5.8.13-9 用例变化影响分析（新用例版本→影响 WorkItem，不自动宣称仍覆盖） | 自动化测试开发 | 05 §5.8.13（L1261-1294） | 验收 | 已定义 |
| INV-04-41 | GWT-5.8.13-10 运行能力前置校验（缺浏览器版本时执行前 BLOCKED，不隐式改用其他版本） | 自动化测试开发 | 05 §5.8.13（L1261-1294） | 验收 | 已定义 |
| INV-04-42 | 自动化开发实体唯一业务所有者（AutomationScript/AutomationScriptVersion/CaseBinding/AutomationCheckRun/TestData/TestDataProfile/Locator/MockConfig/VisualBaseline/PerformanceBaseline；BaselineItem 退场、API_SCHEMA 基线不新增同义实体） | 自动化测试开发 | 05 §5.12.5（L2123-2139） | 规则 | 已定义 |
| INV-04-43 | GWT-5.12.12-6 候选自愈不覆盖 Locator（审核前正式 Locator 不变） | 自动化测试开发 | 05 §5.12.12（L2235-2268） | 验收 | 已定义 |
| INV-04-44 | 模块职责承诺：AI 生成代码/检查/调试建议/Locator-Mock-数据候选；人工代码审核/关键修复/批准版本；产出 AutomationScript 及配套资产 | 自动化测试开发 | 地图 §2 模块表（L19-32） | 规则 | 仅原则性声明 |

> *标注：INV-04-31 执行侧约束与测试执行模块交互，其运行时行为（冻结、调度）在 INV-05 对应条目承接。

### 2.5 模块五：测试执行（PRD14 + 05 §5.12.6）

| 条目编号 | 需求名称 | 所属模块 | 需求来源 | 需求类型 | 状态 |
|---|---|---|---|---|---|
| INV-05-01 | 执行计划：稳定根+不可变版本，绑定 TestPlanVersion/Release/Environment/范围/并发/Runner 策略，校验并冻结全部资产版本，人工审核高风险环境/范围/首跑 | 测试执行 | PRD14 §2（L9-21） | 功能 | 已定义 |
| INV-05-02 | 触发：手工/计划/Webhook/Pipeline，统一幂等，创建 Batch/Task 并授权，取消/重跑/高风险触发需权限 | 测试执行 | PRD14 §2（L9-21） | 功能 | 已定义 |
| INV-05-03 | 调度：按能力/资源池/配额选 Runner，租约/心跳/重试，自动故障检测，人工处理资源不足/特殊环境 | 测试执行 | PRD14 §2（L9-21） | 功能 | 已定义 |
| INV-05-04 | 执行任务：状态/attempt/超时/重试/环境与授权快照，执行固定版本不临时换资产，可暂停/取消，运行中版本不可编辑 | 测试执行 | PRD14 §2（L9-21） | 功能 | 已定义 |
| INV-05-05 | 结果：每个 attempt 产生独立 ExecutionResult，记录事实和机器判定，人工注释不能改原始事实 | 测试执行 | PRD14 §2（L9-21） | 功能 | 已定义 |
| INV-05-06 | 证据：请求/响应、日志、截图、视频、Trace、性能数据、摘要和保留策略，自动采集/脱敏/索引，敏感证据访问受限 | 测试执行 | PRD14 §2（L9-21） | 功能 | 已定义 |
| INV-05-07 | 实时流：ExecutionTask 进度/日志/制品事件，断线续传、顺序/offset，WebSocket 不承载批准/修改命令 | 测试执行 | PRD14 §2（L9-21） | 功能 | 已定义 |
| INV-05-08 | 手工测试：记录步骤结果、实际结果和证据，AI 辅助整理，测试人员对手工结果负责 | 测试执行 | PRD14 §2（L9-21） | 功能 | 已定义 |
| INV-05-09 | ExecutionTask 状态机（PENDING/QUEUED/RUNNING/COMPLETED/FAILED/CANCELLED/TIMED_OUT/BLOCKED）与业务结论（PASSED/FAILED/SKIPPED/ERROR/INCONCLUSIVE）分离 | 测试执行 | PRD14 §3（L22-29） | 规则 | 已定义 |
| INV-05-10 | FAILED（被测行为未满足断言）与 ERROR（环境/脚本/Runner/平台未完成有效验证）不可合并 | 测试执行 | PRD14 §3（L22-29） | 规则 | 已定义 |
| INV-05-11 | 重跑创建新 Batch/Task attempt，不覆盖旧结果 | 测试执行 | PRD14 §3（L22-29） | 规则 | 已定义 |
| INV-05-12 | ExecutionPlanVersion 必须固定 TestCaseVersion/AutomationScriptVersion/APIContractBaseline/Environment/数据-Mock-Locator 引用及摘要 | 测试执行 | PRD14 §3（L22-29） | 规则 | 已定义 |
| INV-05-13 | ResultAnalysis 只能引用 ExecutionResult，不能反写其状态或正文 | 测试执行 | PRD14 §3（L22-29） | 规则 | 已定义 |
| INV-05-14 | Runner 失联：租约到期后按策略创建新 attempt，原 attempt 标记 ERROR 并保留证据 | 测试执行 | PRD14 §5（L38-45） | 规则 | 已定义 |
| INV-05-15 | 版本摘要不匹配：启动前返回 STALE_ARTIFACT_VERSION，禁止执行 | 测试执行 | PRD14 §5（L38-45） | 规则 | 已定义 |
| INV-05-16 | 环境/Secret 无权：返回明确原因，不把未执行记为失败用例 | 测试执行 | PRD14 §5（L38-45） | 规则 | 已定义 |
| INV-05-17 | 网络中断：实时订阅可用 offset 补拉，服务端结果不依赖客户端在线 | 测试执行 | PRD14 §5（L38-45） | 规则 | 已定义 |
| INV-05-18 | 取消：停止未开始任务，运行中任务尽力终止并记录实际状态 | 测试执行 | PRD14 §5（L38-45） | 规则 | 已定义 |
| INV-05-19 | AC-01 版本冻结（新版本需新 ExecutionPlanVersion，本次执行仍用旧冻结版本） | 测试执行 | PRD14 §6 AC-01（L48-53） | 验收 | 已定义 |
| INV-05-20 | AC-02 FAIL 与 ERROR 分离（报告不得把 ERROR 计入有效业务失败/通过分母而不披露） | 测试执行 | PRD14 §6 AC-02（L54-59） | 验收 | 已定义 |
| INV-05-21 | AC-03 重跑不覆盖（attempt1/attempt2 均可查，汇总说明采用规则） | 测试执行 | PRD14 §6 AC-03（L60-65） | 验收 | 已定义 |
| INV-05-22 | AC-04 实时票据授权（无访问权申请 WebSocket 票据被拒且不泄漏任务存在性） | 测试执行 | PRD14 §6 AC-04（L66-71） | 验收 | 已定义 |
| INV-05-23 | 测试执行实体唯一业务所有者（ExecutionPlan/ExecutionPlanVersion/ExecutionContractBaseline/ExecutionTask/ExecutionResult/ExecutionArtifact/APIObservation/ContractCheckResult） | 测试执行 | 05 §5.12.6（L2140-2151） | 规则 | 已定义 |
| INV-05-24 | GWT-5.12.12-3 执行结果不可反写（分析批准后 ExecutionResult 原始状态/日志/摘要不变） | 测试执行 | 05 §5.12.12（L2235-2268） | 验收 | 已定义 |
| INV-05-25 | 模块职责承诺：AI 冻结资产版本/调度 Runner/重试/采集日志证据；人工批准高风险首跑/处理环境例外；产出 ExecutionPlan/ExecutionTask/ExecutionResult/Evidence | 测试执行 | 地图 §2 模块表（L19-32） | 规则 | 仅原则性声明 |

### 2.6 模块六：质量分析与缺陷（PRD15 + 05 §5.9/§5.12.7）

| 条目编号 | 需求名称 | 所属模块 | 需求来源 | 需求类型 | 状态 |
|---|---|---|---|---|---|
| INV-06-01 | ResultAnalysis 正式产出物（结果引用/聚类/RCA/置信限制/替代解释/影响/建议） | 质量分析与缺陷 | PRD15 §2（L9-16） | 规则 | 已定义 |
| INV-06-02 | Defect 正式产出物（标题/复现/期望实际/严重度/类型/环境/影响 Release/Evidence） | 质量分析与缺陷 | PRD15 §2（L9-16） | 规则 | 已定义 |
| INV-06-03 | TestReport 正式产出物（范围/执行/指标快照/结论/风险/限制/签署） | 质量分析与缺陷 | PRD15 §2（L9-16） | 规则 | 已定义 |
| INV-06-04 | 结果分析：聚类失败/关联日志 Trace/RCA/替代解释，人工审核证据充分性，不接受越界推断 | 质量分析与缺陷 | PRD15 §3（L17-28） | 功能 | 已定义 |
| INV-06-05 | FailureCluster：按特征聚合 ExecutionResult，支持拆分/合并建议，Cluster 不是 Defect，人工决定是否建 Defect | 质量分析与缺陷 | PRD15 §3（L17-28） | 功能 | 已定义 |
| INV-06-06 | Defect：生成草稿/去重/复现步骤/严重度建议，人工批准版本/流转/关闭/重复关系 | 质量分析与缺陷 | PRD15 §3（L17-28） | 功能 | 已定义 |
| INV-06-07 | 外部同步：生成固定 payload/附件/操作建议，每次 CREATE/UPDATE/COMMENT/TRANSITION 等写入单独批准 | 质量分析与缺陷 | PRD15 §3（L17-28） | 功能 | 已定义 |
| INV-06-08 | 报告：汇总冻结范围/执行事实/已批准分析 Defect/指标，人工签署发布并披露 ERROR/阻塞/排除项 | 质量分析与缺陷 | PRD15 §3（L17-28） | 功能 | 已定义 |
| INV-06-09 | 质量门禁：执行版本化确定性规则，AI 提供风险/回归建议，门禁规则变更/放行/阻断豁免由人决定 | 质量分析与缺陷 | PRD15 §3（L17-28） | 功能 | 已定义 |
| INV-06-10 | 流水线：关联触发/运行/回调/回执，外部写入与触发范围受授权 | 质量分析与缺陷 | PRD15 §3（L17-28） | 功能 | 已定义 |
| INV-06-11 | ResultAnalysis 与 ExecutionResult 分离，分析可被推翻但结果事实不被改写 | 质量分析与缺陷 | PRD15 §4（L29-37） | 规则 | 已定义 |
| INV-06-12 | FailureCluster 只聚合失败，不存外部缺陷键，不代表缺陷成立 | 质量分析与缺陷 | PRD15 §4（L29-37） | 规则 | 已定义 |
| INV-06-13 | Defect 稳定根和不可变版本分离于生命周期状态，关闭/验证需要证据 | 质量分析与缺陷 | PRD15 §4（L29-37） | 规则 | 已定义 |
| INV-06-14 | 每个 ExternalSyncAttempt 绑定 DefectVersion/Integration/操作/payloadDigest/approvalReviewTaskId/幂等键 | 质量分析与缺陷 | PRD15 §4（L29-37） | 规则 | 已定义 |
| INV-06-15 | TestReport 固定 scopeSnapshot/executionSnapshot，签署后内容不可变，更正产生新版本 | 质量分析与缺陷 | PRD15 §4（L29-37） | 规则 | 已定义 |
| INV-06-16 | AI 建议不能自动放行/阻断发布；确定性门禁规则必须版本化和可解释 | 质量分析与缺陷 | PRD15 §4（L29-37） | 规则 | 已定义 |
| INV-06-17 | Evidence 不足/关联 ID 缺失：分析标记 INCONCLUSIVE 并请求补证，不制造确定根因 | 质量分析与缺陷 | PRD15 §6（L47-53） | 规则 | 已定义 |
| INV-06-18 | 外部系统冲突/超时：记录 attempt 和回执，重试使用同一幂等键，不假报成功 | 质量分析与缺陷 | PRD15 §6（L47-53） | 规则 | 已定义 |
| INV-06-19 | 报告数据快照变化：旧审核作废，创建新版本 | 质量分析与缺陷 | PRD15 §6（L47-53） | 规则 | 已定义 |
| INV-06-20 | 质量门禁依赖不可用：返回不可判定，不能默认放行 | 质量分析与缺陷 | PRD15 §6（L47-53） | 规则 | 已定义 |
| INV-06-21 | AC-01 聚类不等于 Defect（只产生 Cluster/分析草稿，不自动建已批准 Defect 或外部 Issue） | 质量分析与缺陷 | PRD15 §7 AC-01（L56-61） | 验收 | 已定义 |
| INV-06-22 | AC-02 外部写入逐次批准（旧批准不能复用于新 SyncAttempt） | 质量分析与缺陷 | PRD15 §7 AC-02（L62-67） | 验收 | 已定义 |
| INV-06-23 | AC-03 报告分母透明（完整分类/分母定义/排除理由，不把无效执行算 PASS） | 质量分析与缺陷 | PRD15 §7 AC-03（L68-73） | 验收 | 已定义 |
| INV-06-24 | AC-04 AI 分析可被纠正（新分析版本保留替代解释，原版本可审计，ExecutionResult 不变） | 质量分析与缺陷 | PRD15 §7 AC-04（L74-79） | 验收 | 已定义 |
| INV-06-25 | 六层职责分离（ExecutionResult/FailureAnalysis/FailureCluster/Defect/ExternalDefectLink/DefectSyncAttempt 各自回答的问题与可批准性） | 质量分析与缺陷 | 05 §5.9.1（L1297-1331） | 规则 | 已定义 |
| INV-06-26 | 聚类/分析/缺陷基数关系（5 条：分析指向结果、聚类含多分析、聚类可不建 Defect 可拆分、Defect 多引用、重算不改已批准证据快照、非缺陷结论保留） | 质量分析与缺陷 | 05 §5.9.2（L1332-1340） | 规则 | 已定义 |
| INV-06-27 | Defect 稳定身份与生命周期（defectKey/生命周期状态机 9 态、reviewStatus 与 lifecycleStatus 独立、状态事件只追加、REJECTED/DUPLICATE 保留理由、VERIFIED 需回归证据） | 质量分析与缺陷 | 05 §5.9.3（L1341-1370） | 规则 | 已定义 |
| INV-06-28 | DefectVersion 最小字段（17 组字段；正文不保存明文凭证/脱敏/无限期下载地址，制品进受控存储） | 质量分析与缺陷 | 05 §5.9.4（L1371-1395） | 规则 | 已定义 |
| INV-06-29 | DefectEvidence 证据关系（evidenceType 12 类/evidenceId+version/digest/relationType 6 类）与最低证据门槛（PRODUCT/SECURITY/PERFORMANCE 需期望+实际依据；证据缺失可 DRAFT 不可批准；摘要变化转 STALE；AI 推断标记 INFERRED） | 质量分析与缺陷 | 05 §5.9.5（L1396-1417） | 规则 | 已定义 |
| INV-06-30 | Defect 生成/审核/发布规则 10 条（状态流 DRAFT→PENDING_REVIEW→APPROVED/STALE；确定性校验清单；Reviewer 审精确版本；FOUR_EYES 适用范围；Agent 不能批准；批准后变化必新版本；内部批准≠外部写入；REJECTED/DUPLICATE 保留证据；只有批准版本可进报告/门禁/同步） | 质量分析与缺陷 | 05 §5.9.6（L1418-1442） | 规则 | 已定义 |
| INV-06-31 | ExternalDefectLink 厂商中立映射（integrationId+externalIssueId 全局唯一、外部 Key 变化不影响内部身份、重复确认需人工、外部删除不级联、回写不直接覆盖、CONFLICT 进 WorkItem） | 质量分析与缺陷 | 05 §5.9.7（L1443-1468） | 规则 | 已定义 |
| INV-06-32 | DefectSyncAttempt 外部写入/幂等/重试/冲突（attempt 字段 13 项；调用前人工 EXTERNAL_WRITE 批准、批准对象六要素、幂等键派生、超时先确认再重试、失败不改内部事实、远端变化进 CONFLICT、附件逐个上传、批量=逐条编排） | 质量分析与缺陷 | 05 §5.9.8（L1469-1496） | 规则 | 已定义 |
| INV-06-33 | 重复识别与回归验证（确定性规则+语义相似度候选人工确认、DUPLICATE 必填 duplicateOfDefectId 且保留证据、主缺陷关闭不自动关重复；RESOLVED≠VERIFIED、VERIFIED 需 REGRESSION_VERIFICATION 证据、回归失败转回 OPEN、Agent 只能建议验证通过） | 质量分析与缺陷 | 05 §5.9.9（L1497-1514） | 规则 | 已定义 |
| INV-06-34 | GWT-5.9.11-1 聚类不等于缺陷（拆分后只为产品问题建 Defect，脚本问题保留非缺陷结论） | 质量分析与缺陷 | 05 §5.9.11（L1529-1568） | 验收 | 已定义 |
| INV-06-35 | GWT-5.9.11-2 一缺陷多证据（多 ExecutionResult/FailureAnalysis，每条带摘要与关系类型） | 质量分析与缺陷 | 05 §5.9.11（L1529-1568） | 验收 | 已定义 |
| INV-06-36 | GWT-5.9.11-3 证据不足不能批准（只有 AI 根因猜测时拒绝并指出缺失证据） | 质量分析与缺陷 | 05 §5.9.11（L1529-1568） | 验收 | 已定义 |
| INV-06-37 | GWT-5.9.11-4 审核绑定精确版本（v2 批准不适用于 v3/digest B） | 质量分析与缺陷 | 05 §5.9.11（L1529-1568） | 验收 | 已定义 |
| INV-06-38 | GWT-5.9.11-5 AI 不能直接外部提交（无 EXTERNAL_WRITE 批准时调用被拒+越权审计） | 质量分析与缺陷 | 05 §5.9.11（L1529-1568） | 验收 | 已定义 |
| INV-06-39 | GWT-5.9.11-6 外部写入幂等（超时重试先发现既有 Issue 建映射，不重复创建） | 质量分析与缺陷 | 05 §5.9.11（L1529-1568） | 验收 | 已定义 |
| INV-06-40 | GWT-5.9.11-7 远端冲突不覆盖（同步进 CONFLICT 并创建处理 WorkItem） | 质量分析与缺陷 | 05 §5.9.11（L1529-1568） | 验收 | 已定义 |
| INV-06-41 | GWT-5.9.11-8 部分附件失败可见（逐附件独立状态，整体不得显示完全成功） | 质量分析与缺陷 | 05 §5.9.11（L1529-1568） | 验收 | 已定义 |
| INV-06-42 | GWT-5.9.11-9 重复关系需人工确认（未确认只能展示候选） | 质量分析与缺陷 | 05 §5.9.11（L1529-1568） | 验收 | 已定义 |
| INV-06-43 | GWT-5.9.11-10 修复不等于验证（无回归结果拒绝 VERIFIED） | 质量分析与缺陷 | 05 §5.9.11（L1529-1568） | 验收 | 已定义 |
| INV-06-44 | GWT-5.9.11-11 外部失败不损坏内部事实（已批准版本不变，同步 FAILED+可重试 WorkItem） | 质量分析与缺陷 | 05 §5.9.11（L1529-1568） | 验收 | 已定义 |
| INV-06-45 | GWT-5.9.11-12 厂商映射与业务对象解耦（一 Defect 多 ExternalDefectLink，身份生命周期唯一） | 质量分析与缺陷 | 05 §5.9.11（L1529-1568） | 验收 | 已定义 |
| INV-06-46 | 质量模块实体唯一业务所有者（ResultAnalysis/FailureCluster/FailureAnalysis/CoverageReport/Defect/DefectVersion/DefectEvidence/DefectStatusEvent/ExternalDefectLink/DefectSyncAttempt/TestReport/QualityGate/PipelineConfig/PipelineRun） | 质量分析与缺陷 | 05 §5.12.7（L2152-2170） | 规则 | 已定义 |
| INV-06-47 | 总纲规则 7：Defect 与 FailureCluster 分离；外部写入逐次审批、幂等并保留回执/冲突 | 质量分析与缺陷 | 总纲 §5 规则 7（L31-38） | 规则 | 已定义 |
| INV-06-48 | 模块职责承诺：AI 聚类/RCA/Defect-报告草稿/门禁建议；人工审核分析-Defect-报告/外部写入和发布判断；产出 ResultAnalysis/Defect/TestReport/QualityGate | 质量分析与缺陷 | 地图 §2 模块表（L19-32） | 规则 | 仅原则性声明 |

### 2.7 模块七：AI Agent 中心（PRD16 + 05 §5.12.8）

| 条目编号 | 需求名称 | 所属模块 | 需求来源 | 需求类型 | 状态 |
|---|---|---|---|---|---|
| INV-07-01 | Skill：稳定根/版本、输入输出契约、实现引用、风险、依赖、权限和 eval，发布/升级需代码与安全 Review | AI Agent 中心 | PRD16 §2（L9-21） | 功能 | 已定义 |
| INV-07-02 | Agent：目标/职责/allowedSkills/工具文件网络 Secret/委派深度/预算，能力扩大需治理审核 | AI Agent 中心 | PRD16 §2（L9-21） | 功能 | 已定义 |
| INV-07-03 | Prompt：不可变版本、模型/模板/摘要和适用范围，版本发布及高风险变更需审核 | AI Agent 中心 | PRD16 §2（L9-21） | 功能 | 已定义 |
| INV-07-04 | Workflow：DAG、节点 Agent/Skill、输入输出、权限、重试、降级和 human checkpoints，发布前结构/权限/业务 Eval | AI Agent 中心 | PRD16 §2（L9-21） | 功能 | 已定义 |
| INV-07-05 | Session/Trace：发起人/WorkItem/版本快照/授权决定/节点 tool 调用/IO 摘要/成本，敏感字段脱敏，不记录隐藏思维链 | AI Agent 中心 | PRD16 §2（L9-21） | 功能 | 已定义 |
| INV-07-06 | Eval：Golden Set、数据集版本、目标版本、指标、结果、人工基线和适用性，决定准入/回滚并形成版本化校准记录 | AI Agent 中心 | PRD16 §2（L9-21） | 功能 | 已定义 |
| INV-07-07 | 运行控制：暂停/取消/预算/循环检测/熔断/L0-L3 降级，人工可随时接管，正式审核不可跳过 | AI Agent 中心 | PRD16 §2（L9-21） | 功能 | 已定义 |
| INV-07-08 | 独立平台评审：在生产委派图之外按冻结快照评审 9 个领域，只输出咨询性 Finding，评审 Agent 不得建设/整改/关闭 | AI Agent 中心 | PRD16 §2（L9-21） | 功能 | 已定义 |
| INV-07-09 | 权限模型：最终权限=发起人 RBAC∩AgentVersion∩Workflow 节点∩WorkItem/环境/集成策略−ExplicitDeny−humanOnly，任一层缺失即拒绝 | AI Agent 中心 | PRD16 §3（L22-27） | 规则 | 已定义 |
| INV-07-10 | 默认 deny-all：网络、Secret 空、外部写入、正式资产写入/批准、Subagent 委派深度受限 | AI Agent 中心 | PRD16 §3（L22-27） | 规则 | 已定义 |
| INV-07-11 | Agent 不得以用户拥有的批准权代表用户作 ReviewDecision | AI Agent 中心 | PRD16 §3（L22-27） | 规则 | 已定义 |
| INV-07-12 | Gate 0 基线：1 Supervisor+3 受限 Subagent、14 个 Gate 0 Skill，覆盖需求→TestingIR→策略→计划→用例→Coverage→人工审核包，为 V0 局部链不代表 V1 | AI Agent 中心 | PRD16 §4（L28-33） | 规则 | 部分定义 |
| INV-07-13 | qf-platform-reviewer 独立隔离：不在 agents.json/Supervisor 委派列表、不接受生产 Agent 派工、不能反向调度生产 Agent，只读评审流程按冻结快照 | AI Agent 中心 | PRD16 §4（L28-33） | 规则 | 已定义 |
| INV-07-14 | 未授权 Skill/tool/网络/Secret：调用前拒绝并中止/降级 | AI Agent 中心 | PRD16 §6（L43-49） | 规则 | 已定义 |
| INV-07-15 | 循环/超时/预算超限：停止未开始节点，保存现场，WorkItem 阻塞 | AI Agent 中心 | PRD16 §6（L43-49） | 规则 | 已定义 |
| INV-07-16 | 模型/Prompt/Skill/Workflow 版本变化：原校准记录失效，回退 L1 并重评 | AI Agent 中心 | PRD16 §6（L43-49） | 规则 | 已定义 |
| INV-07-17 | Trace 缺失或 checker 异常：不得给 PASS，不得进入正式审核的可批准状态 | AI Agent 中心 | PRD16 §6（L43-49） | 规则 | 已定义 |
| INV-07-18 | AC-01 Skill 与 Agent 不混同（分别记录 AgentVersion 与 SkillVersion） | AI Agent 中心 | PRD16 §7 AC-01（L52-57） | 验收 | 已定义 |
| INV-07-19 | AC-02 权限取交集（用户有权限但 AgentVersion 禁止则拒绝并记录 DENY） | AI Agent 中心 | PRD16 §7 AC-02（L58-63） | 验收 | 已定义 |
| INV-07-20 | AC-03 机器 PASS 不等于人工批准（human_gate 到达创建 ReviewTask 并 BLOCK_HUMAN） | AI Agent 中心 | PRD16 §7 AC-03（L64-69） | 验收 | 已定义 |
| INV-07-21 | AC-04 Eval 版本可复现（旧 Eval 只关联旧 PromptVersion，新版本必须重新运行指定 DatasetVersion） | AI Agent 中心 | PRD16 §7 AC-04（L70-75） | 验收 | 已定义 |
| INV-07-22 | AC-05 平台评审与生产 Agent 隔离（运行时拒绝生产 Agent 调用 qf-platform-reviewer） | AI Agent 中心 | PRD16 §7 AC-05（L76-81） | 验收 | 已定义 |
| INV-07-23 | AC-06 评审 Agent 不能整改或自行结案（写入和处置被拒，只能给证据/影响/建议/验收标准） | AI Agent 中心 | PRD16 §7 AC-06（L82-87） | 验收 | 已定义 |
| INV-07-24 | AI Agent 中心实体唯一业务所有者（Skill/WorkspaceSkillEnablement/Agent/WorkspaceAgentEnablement/AgentWorkflow/AgentPromptVersion/AgentSession/AgentTraceNode/SkillInvocation/EvalDataset/EvalRun） | AI Agent 中心 | 05 §5.12.8（L2171-2186） | 规则 | 已定义 |
| INV-07-25 | GWT-5.12.12-9 Agent 运行与业务草稿分离（Session 状态归 Agent 中心，草稿归业务模块只经 WorkItem 关联） | AI Agent 中心 | 05 §5.12.12（L2235-2268） | 验收 | 已定义 |
| INV-07-26 | 总纲规则 5：AI 自治默认 L2 受限代理；没有经批准且仍有效的 Eval 校准记录时，分数不能驱动高价值自治 | AI Agent 中心 | 总纲 §5 规则 5（L31-38） | 规则 | 已定义 |
| INV-07-27 | 模块职责承诺：AI 执行受限 Workflow/留 Trace/运行 Eval；人工发布能力权限/审核评测/处理越权和降级；产出 Skill/Agent/Workflow/Trace/Eval | AI Agent 中心 | 地图 §2 模块表（L19-32） | 规则 | 仅原则性声明 |

### 2.8 模块八：平台管理（PRD17 + 05 §5.11/§5.7.3/§5.12.9）

| 条目编号 | 需求名称 | 所属模块 | 需求来源 | 需求类型 | 状态 |
|---|---|---|---|---|---|
| INV-08-01 | Tenant/Workspace：生命周期、成员和隔离，UI 把 Workspace 展示为项目，不新增 Project 实体，归档保留历史引用 | 平台管理 | PRD17 §2（L9-23） | 功能 | 已定义 |
| INV-08-02 | Release：范围、计划时间、状态和关联版本，关闭/归档前校验未完成工作和报告 | 平台管理 | PRD17 §2（L9-23） | 功能 | 已定义 |
| INV-08-03 | Environment：类型、endpoint 映射、能力、数据策略和 secretRef，不保存连接串明文 | 平台管理 | PRD17 §2（L9-23） | 功能 | 已定义 |
| INV-08-04 | Secret：密文、keyVersion、作用域、过期、轮换和使用审计，元数据与使用权限分离，API 不返回明文 | 平台管理 | PRD17 §2（L9-23） | 功能 | 已定义 |
| INV-08-05 | Runner/资源池：能力、运行时、健康、配额和 Workspace 范围，注册/隔离/撤销受平台权限控制 | 平台管理 | PRD17 §2（L9-23） | 功能 | 已定义 |
| INV-08-06 | Integration：Defect/Git/CI/通知等端点/凭据引用/作用域，出站 allowlist、逐次高价值授权和回执 | 平台管理 | PRD17 §2（L9-23） | 功能 | 已定义 |
| INV-08-07 | RBAC：Permission/RoleDefinition/RoleBinding/ExplicitDeny/委派，四级作用域，管理员不能自我无限授权 | 平台管理 | PRD17 §2（L9-23） | 功能 | 已定义 |
| INV-08-08 | ReviewPolicy：产出物/风险对应阶段、人数、能力、职责分离和 blockingChecks，平台最低要求只能调严不能取消至少一名人类 | 平台管理 | PRD17 §2（L9-23） | 功能 | 已定义 |
| INV-08-09 | LLM 配置：Provider/模型/路由、数据区域、预算和允许用途，不在此设置业务自治阈值，版本变化触发重评 | 平台管理 | PRD17 §2（L9-23） | 功能 | 已定义 |
| INV-08-10 | 审计：AuthorizationDecision、AuditLog、保留/导出，只追加、脱敏、访问受限 | 平台管理 | PRD17 §2（L9-23） | 功能 | 已定义 |
| INV-08-11 | 对象关系：Tenant 含多 Workspace，Workspace 含多 Release；Environment/Integration/RoleBinding 按作用域生效 | 平台管理 | PRD17 §3（L24-31） | 规则 | 已定义 |
| INV-08-12 | PlatformAdmin 管理基础设施不默认读取租户业务内容；TenantAdmin 不默认批准 Workspace 产出物；WorkspaceAdmin 不默认签署报告或豁免门禁 | 平台管理 | PRD17 §3（L24-31） | 规则 | 已定义 |
| INV-08-13 | 租户/Workspace 上下文缺失：服务层和 RLS 同时拒绝 | 平台管理 | PRD17 §5（L41-48） | 规则 | 已定义 |
| INV-08-14 | Secret 过期/无权：执行阻塞，不回退到明文或默认凭据 | 平台管理 | PRD17 §5（L41-48） | 规则 | 已定义 |
| INV-08-15 | Runner 能力不足：明确阻塞并建议资源，不把任务发送到不兼容节点 | 平台管理 | PRD17 §5（L41-48） | 规则 | 已定义 |
| INV-08-16 | 集成不可用：保留 attempt/回执并人工处理，不假报外部成功 | 平台管理 | PRD17 §5（L41-48） | 规则 | 已定义 |
| INV-08-17 | ReviewPolicy/RoleBinding 变更：后续高价值动作重新计算，已签署历史保留策略快照 | 平台管理 | PRD17 §5（L41-48） | 规则 | 已定义 |
| INV-08-18 | AC-01 项目等于 Workspace（保存只创建 Workspace 返回 workspaceId） | 平台管理 | PRD17 §6 AC-01（L51-56） | 验收 | 已定义 |
| INV-08-19 | AC-02 管理员不自动批准（无业务审核能力时批准 TestReport 返回 403+AuthorizationDecision） | 平台管理 | PRD17 §6 AC-02（L57-62） | 验收 | 已定义 |
| INV-08-20 | AC-03 Secret 不泄漏（响应/日志/Trace 无明文，只看到引用和元数据） | 平台管理 | PRD17 §6 AC-03（L63-68） | 验收 | 已定义 |
| INV-08-21 | AC-04 跨租户失败关闭（服务层和 RLS 拒绝且不泄漏资源存在性） | 平台管理 | PRD17 §6 AC-04（L69-74） | 验收 | 已定义 |
| INV-08-22 | Release 最小职责（业务版本标识/计划实际发布时间/范围摘要/Planning-Testing-Released-Archived 生命周期/聚合结果/追溯锚点；不保存策略正文/排期/用例范围/执行参数） | 平台管理 | 05 §5.7.3（L879-891） | 规则 | 已定义 |
| INV-08-23 | 角色模板/审核职责/机器身份四概念分离（产品 Persona、RBAC 角色模板、审核职责、机器身份不得混用；授权判定公式 9 项交集 fail-closed） | 平台管理 | 05 §5.11.1（L1834-1864） | 规则 | 已定义 |
| INV-08-24 | 作用域模型：PLATFORM/TENANT/WORKSPACE/RESOURCE 四级及 6 条继承规则（平台不穿透、管理不自动业务批准、跨 Workspace 逐项授权、Release 非独立权限边界） | 平台管理 | 05 §5.11.2（L1865-1884） | 规则 | 已定义 |
| INV-08-25 | 内置角色模板 6 个（PlatformAdmin/TenantAdmin/WorkspaceAdmin/TestLead/TestEngineer/ViewerAuditor）及各模板"明确不默认拥有"清单，角色来源可解释 | 平台管理 | 05 §5.11.3（L1885-1899） | 规则 | 已定义 |
| INV-08-26 | 权限领域对象 9 类（RoleDefinition/Permission/RolePermission/RoleBinding/ExplicitDeny/ReviewPolicy/ReviewAssignment/AuthorizationDecision/DelegationGrant）最小字段与版本化规则 | 平台管理 | 05 §5.11.4（L1900-1915） | 规则 | 已定义 |
| INV-08-27 | 稳定能力键体系（10 族能力键：work_item/artifact/strategy/test_plan/test_case/automation/execution/analysis-defect-report/knowledge-contract/agent-skill/管理；普通 approve 不含外部写入/签署/门禁豁免） | 平台管理 | 05 §5.11.5（L1916-1934） | 规则 | 已定义 |
| INV-08-28 | 八类正式产出物最低批准映射（8 行 × LOW/MEDIUM 与 HIGH/CRITICAL 最低批准 + 额外约束；APIContract 走专属能力；ExecutionPlan 需 execution_plan.approve） | 平台管理 | 05 §5.11.6（L1935-1949） | 规则 | 已定义 |
| INV-08-29 | SINGLE_REVIEW 与 FOUR_EYES 规则（至少一名人类、同人跨角色不算四眼、AI/Verifier Agent 不算人眼、单人强制四眼转 BLOCKED、只能调严） | 平台管理 | 05 §5.11.7（L1950-1962） | 规则 | 已定义 |
| INV-08-30 | 管理员/业务批准/紧急访问边界（管理员身份不自动业务批准；TenantAdmin 自授高风险能力需复核；SupportAccessGrant 限时只读；break-glass 不得伪造批准；Secret 管理不返回明文；门禁豁免独立限时带理由） | 平台管理 | 05 §5.11.8（L1963-1972） | 规则 | 已定义 |
| INV-08-31 | Agent 与服务账号边界（独立机器身份、不得获得人类责任能力、批准人与执行服务分别审计、Agent 不能自批、Runner 限时凭证、机器身份 RoleBinding 限定） | 平台管理 | 05 §5.11.9（L1973-1982） | 规则 | 已定义 |
| INV-08-32 | 授权决策/并发/撤销（AuthorizationDecision 最少 10 项内容；9 个重算时点；撤销立即阻止新动作、Token 限时失效、批量逐项授权） | 平台管理 | 05 §5.11.10（L1983-1998） | 规则 | 已定义 |
| INV-08-33 | GWT-5.11.12-1 管理员不等于业务批准人（TenantAdmin 批准 TestReport 被拒并说明缺 report.signoff） | 平台管理 | 05 §5.11.12（L2015-2054） | 验收 | 已定义 |
| INV-08-34 | GWT-5.11.12-2 Workspace 隔离（同 Tenant 跨 Workspace 审核被服务端拒绝） | 平台管理 | 05 §5.11.12（L2015-2054） | 验收 | 已定义 |
| INV-08-35 | GWT-5.11.12-3 单人低风险试点（SINGLE_REVIEW 允许并记录 independentReview=false） | 平台管理 | 05 §5.11.12（L2015-2054） | 验收 | 已定义 |
| INV-08-36 | GWT-5.11.12-4 高风险四眼阻断（仅一名成员时 BLOCKED，管理员开关不能绕过） | 平台管理 | 05 §5.11.12（L2015-2054） | 验收 | 已定义 |
| INV-08-37 | GWT-5.11.12-5 多角色同一人不算四眼（自然人身份相同则拒绝） | 平台管理 | 05 §5.11.12（L2015-2054） | 验收 | 已定义 |
| INV-08-38 | GWT-5.11.12-6 AI PASS 不能批准（无人类批准记录保持 PENDING_REVIEW） | 平台管理 | 05 §5.11.12（L2015-2054） | 验收 | 已定义 |
| INV-08-39 | GWT-5.11.12-7 权限点击时重算（角色撤销后批准被服务端拒绝） | 平台管理 | 05 §5.11.12（L2015-2054） | 验收 | 已定义 |
| INV-08-40 | GWT-5.11.12-8 外部写入独立授权（defect.approve 不含 defect.external_write） | 平台管理 | 05 §5.11.12（L2015-2054） | 验收 | 已定义 |
| INV-08-41 | GWT-5.11.12-9 平台管理员默认看不到租户内容（无 SupportAccessGrant 拒绝并审计） | 平台管理 | 05 §5.11.12（L2015-2054） | 验收 | 已定义 |
| INV-08-42 | GWT-5.11.12-10 机器身份不冒充批准人（批准人与执行服务分别记录） | 平台管理 | 05 §5.11.12（L2015-2054） | 验收 | 已定义 |
| INV-08-43 | GWT-5.11.12-11 批量逐项授权（10 项中 8 允许 2 拒绝，不整批伪报成功） | 平台管理 | 05 §5.11.12（L2015-2054） | 验收 | 已定义 |
| INV-08-44 | GWT-5.11.12-12 紧急访问不能篡改业务结论（break-glass 无业务签署能力） | 平台管理 | 05 §5.11.12（L2015-2054） | 验收 | 已定义 |
| INV-08-45 | 平台管理实体唯一业务所有者（Tenant/User/Workspace/Release/Environment/WorkspaceSecret/RunnerNode/LlmConfig/AuditLog/IntegrationConfig/RoleDefinition/Permission/RolePermission/RoleBinding/ExplicitDeny/ReviewPolicy/AuthorizationDecision/DelegationGrant/SupportAccessGrant） | 平台管理 | 05 §5.12.9（L2187-2207） | 规则 | 已定义 |
| INV-08-46 | GWT-5.12.12-4 Runner 所有权明确（执行不能直接修改 RunnerNode 能力声明） | 平台管理 | 05 §5.12.12（L2235-2268） | 验收 | 已定义 |
| INV-08-47 | GWT-5.12.12-7 发布上下文不复制计划（Release 日期变化不静默覆盖 TestPlan 日期） | 平台管理 | 05 §5.12.12（L2235-2268） | 验收 | 已定义 |
| INV-08-48 | GWT-5.12.12-8 集成配置与业务回执分离（凭证轮换不影响 ExternalDefectLink/历史 SyncAttempt） | 平台管理 | 05 §5.12.12（L2235-2268） | 验收 | 已定义 |
| INV-08-49 | 总纲规则 1：UI"项目"就是 Workspace；Release 是 Workspace 内版本/迭代交付批次 | 平台管理 | 总纲 §5 规则 1（L31-38） | 规则 | 已定义 |
| INV-08-50 | 总纲规则 6：管理员身份不自动获得业务批准；最终授权取多层权限交集并 fail-closed | 平台管理 | 总纲 §5 规则 6（L31-38） | 规则 | 已定义 |
| INV-08-51 | 模块职责承诺：配置预检/最小权限建议/异常提示（AI）；安全配置/成员权限/Secret 和基础设施管理（人工）；产出 Workspace/Release/RBAC/Environment/Integration/AuditLog | 平台管理 | 地图 §2 模块表（L19-32） | 规则 | 仅原则性声明 |

### 2.9 跨模块全局契约（05 §5.12.1/§5.13/§5.14/§5.15 + 总纲部分）

| 条目编号 | 需求名称 | 所属模块 | 需求来源 | 需求类型 | 状态 |
|---|---|---|---|---|---|
| INV-00-01 | 总纲规则 2：WorkItem 统一承载待办/AI 运行/人工工作/阻塞/审核路由，但不取代业务产出物 | 跨模块 | 总纲 §5 规则 2（L31-38） | 规则 | 已定义 |
| INV-00-02 | 总纲规则 3：正式产出物以稳定根+不可变版本保存，发布/批准绑定精确摘要 | 跨模块 | 总纲 §5 规则 3（L31-38） | 规则 | 已定义 |
| INV-00-03 | 总纲规则 4：ExecutionResult/Evidence/ReviewDecision/AuthorizationDecision/AuditLog/Agent Trace 只追加 | 跨模块 | 总纲 §5 规则 4（L31-38） | 规则 | 已定义 |
| INV-00-04 | 实体唯一业务所有者判定规则 7 条（单 Owner、精确版本引用、建议归 WorkItem/Candidate、审核归看板/授权归平台、执行证据归执行、AI 证据归 Agent 中心、泛化实体拆分退场） | 跨模块 | 05 §5.12.1（L2057-2076） | 规则 | 已定义 |
| INV-00-05 | 现行实体冲突与退场清单（10 项裁决：TestPlan 里程碑移交 Release、TestDesignPlan 退场、AIContext 拆分、APIContract 重构、BaselineItem 退场、Runner 归平台、ReviewTask 归看板、KnowledgeCandidate 归知识库、管理员权限收窄） | 跨模块 | 05 §5.12.10（L2208-2221） | 规则 | 已定义 |
| INV-00-06 | 完整性约束 5 条（新实体先定 Owner、跨域编辑用命令编排、双可编辑入口至少一个改只读、后续聚合遵循唯一写入、独立复审扫全部写命令） | 跨模块 | 05 §5.12.11（L2222-2234） | 规则 | 已定义 |
| INV-00-07 | GWT-5.12.12-10 退场实体无新写入（TestDesignPlan/AIContext/BaselineItem 新契约无写入，限期适配器只能转目标 Owner 命令） | 跨模块 | 05 §5.12.12（L2235-2268） | 验收 | 已定义 |
| INV-00-08 | V0 范围（冻结 8 模块/术语/领域/状态机/API-DB-RBAC 契约；Gate 0 链验证；不包含可登录 Web/真实 Runner/Jira 写入/多租户）与 V0 退出条件 | 跨模块 | 05 §5.13.2（L2284-2303） | 规则 | 已定义 |
| INV-00-09 | V1 范围：8 模块最小能力表（每模块 V1 必须交付/明确不做清单）+ 八类正式产出物全覆盖 + 人工批准底线 + V1 退出条件（含无基线数字禁止承诺） | 跨模块 | 05 §5.13.3（L2304-2342） | 规则 | 已定义 |
| INV-00-10 | V2 增量范围（8 模块各一行增量清单） | 跨模块 | 05 §5.13.4（L2343-2359） | 规则 | 部分定义 |
| INV-00-11 | V3 增量范围（8 模块各一行增量清单） | 跨模块 | 05 §5.13.5（L2360-2374） | 规则 | 部分定义 |
| INV-00-12 | 跨版本不变项 8 条（租户边界与 Secret 不明文、AI 不能自批、精确版本+digest+Trace、执行证据不可覆盖、外部写入默认拒绝、最小权限+Trace、未检查不伪报通过、审计只追加） | 跨模块 | 05 §5.13.6（L2375-2387） | 规则 | 已定义 |
| INV-00-13 | 版本范围变更规则 6 条（前移带齐依赖、延期不破闭环、规划中不可操作、版本项标 MUST/SHOULD/LATER、NFR 需基线、退出只用单次完整证据） | 跨模块 | 05 §5.13.7（L2388-2396） | 规则 | 已定义 |
| INV-00-14 | GWT-5.13.8-1 V0 不冒充产品 | 跨模块 | 05 §5.13.8（L2397-2424） | 验收 | 已定义 |
| INV-00-15 | GWT-5.13.8-2 V1 闭环不缺模块（缺审核队列/报告签署则 V1 不成立） | 跨模块 | 05 §5.13.8（L2397-2424） | 验收 | 已定义 |
| INV-00-16 | GWT-5.13.8-3 目标态不等于当前范围（规划项不可操作/不计入完成） | 跨模块 | 05 §5.13.8（L2397-2424） | 验收 | 已定义 |
| INV-00-17 | GWT-5.13.8-4 正式产出始终人工批准（更高自动化下 Defect/报告仍须人批准签署） | 跨模块 | 05 §5.13.8（L2397-2424） | 验收 | 已定义 |
| INV-00-18 | GWT-5.13.8-5 前移功能带齐依赖（Jira 前移须带 Integration/EXTERNAL_WRITE/幂等/冲突/审计验收） | 跨模块 | 05 §5.13.8（L2397-2424） | 验收 | 已定义 |
| INV-00-19 | GWT-5.13.8-6 延期不破闭环（Git 延期用 MANAGED+人工导出替代，不删代码审核） | 跨模块 | 05 §5.13.8（L2397-2424） | 验收 | 已定义 |
| INV-00-20 | GWT-5.13.8-7 无基线数字不能承诺（1000 并发等标为待基线候选） | 跨模块 | 05 §5.13.8（L2397-2424） | 验收 | 已定义 |
| INV-00-21 | GWT-5.13.8-8 单次证据验证退出（不能拼接历史样例宣称通过） | 跨模块 | 05 §5.13.8（L2397-2424） | 验收 | 已定义 |
| INV-00-22 | 三套名称职责（产品展示名/领域名/API 资源名/DB 名/JSON 字段五层规则） | 跨模块 | 05 §5.14.1（L2427-2440） | 规则 | 已定义 |
| INV-00-23 | 一级模块名称映射（8 模块展示名/领域边界名/API 前缀/旧入口处理） | 跨模块 | 05 §5.14.2（L2441-2455） | 规则 | 已定义 |
| INV-00-24 | 核心名词裁决（16 组：项目=Workspace、发布版本=Release、测试策略/计划/执行计划、用例草稿/正式用例、自动化代码、缺陷、执行节点、审核任务、技能等） | 跨模块 | 05 §5.14.3（L2456-2474） | 规则 | 已定义 |
| INV-00-25 | 兼容原则（Gate D 直接改 OpenAPI 无运行时代理；发现真实消费者再升级适配；/api/v1 保留为首个交付代际；产品版本与 API 版本分离；发布后兼容规则 6 条） | 跨模块 | 05 §5.14.4（L2475-2494） | 规则 | 已定义 |
| INV-00-26 | 旧路径到目标路径映射（31 组旧路径族迁移类型与目标路径） | 跨模块 | 05 §5.14.5（L2495-2528） | 规则 | 已定义 |
| INV-00-27 | Schema 与字段迁移策略（12 组旧 Schema/字段目标处理与兼容规则；新旧字段值冲突 400 拒绝） | 跨模块 | 05 §5.14.6（L2529-2545） | 规则 | 已定义 |
| INV-00-28 | 状态和错误兼容（UPPER_SNAKE_CASE 状态、未知枚举不默认 PASS、code+message+details+traceId、403 视为预期安全变化、异步返回 WorkItem/attempt、删除默认归档 409） | 跨模块 | 05 §5.14.7（L2546-2555） | 规则 | 已定义 |
| INV-00-29 | GWT-5.14.8-1 展示名不制造新实体（创建项目只返回 workspaceId） | 跨模块 | 05 §5.14.8（L2556-2589） | 验收 | 已定义 |
| INV-00-30 | GWT-5.14.8-2 设计稿阶段不背负假兼容（保留迁移映射+CHANGELOG） | 跨模块 | 05 §5.14.8（L2556-2589） | 验收 | 已定义 |
| INV-00-31 | GWT-5.14.8-3 真实消费者触发兼容升级（发现客户端必须先提供适配再删旧路径） | 跨模块 | 05 §5.14.8（L2556-2589） | 验收 | 已定义 |
| INV-00-32 | GWT-5.14.8-4 API 版本与产品版本分离（V2 无破坏性变化仍可 /api/v1） | 跨模块 | 05 §5.14.8（L2556-2589） | 验收 | 已定义 |
| INV-00-33 | GWT-5.14.8-5 旧资产入口不双写（编辑用例只进 /test-cases Owner） | 跨模块 | 05 §5.14.8（L2556-2589） | 验收 | 已定义 |
| INV-00-34 | GWT-5.14.8-6 旧缺陷导出被拆分（先批准 DefectVersion 再逐条 SyncAttempt） | 跨模块 | 05 §5.14.8（L2556-2589） | 验收 | 已定义 |
| INV-00-35 | GWT-5.14.8-7 字段冲突拒绝（旧 projectId 与新 workspaceId 冲突 400） | 跨模块 | 05 §5.14.8（L2556-2589） | 验收 | 已定义 |
| INV-00-36 | GWT-5.14.8-8 未知状态不伪报通过（显示未知并提示升级） | 跨模块 | 05 §5.14.8（L2556-2589） | 验收 | 已定义 |
| INV-00-37 | GWT-5.14.8-9 废弃资源保留证据（legacyRef 反查历史 ID） | 跨模块 | 05 §5.14.8（L2556-2589） | 验收 | 已定义 |
| INV-00-38 | GWT-5.14.8-10 导航合并不合并实体（/ai/skills 与 /ai/agents 各自状态机） | 跨模块 | 05 §5.14.8（L2556-2589） | 验收 | 已定义 |
| INV-00-39 | 全局引用扫描范围与快照（扫描范围/排除项；Gate C 快照：27 文档 300 处旧模块名、14 文档 72 处退场实体、4 文档 9 处旧 Defect 耦合、10 文档 28 处旧角色、18 文档 343 处旧 API 路径） | 跨模块 | 05 §5.15.1（L2592-2619） | 规则 | 已定义 |
| INV-00-40 | Gate D 执行批次与依赖（D1 术语→D2 技术契约→D3 安全治理→D4 产品版本→D5 架构体验→D6 CHANGELOG+复审；8 条执行约束） | 跨模块 | 05 §5.15.5（L2675-2708） | 规则 | 已定义 |
| INV-00-41 | 允许保留的旧引用（5 类 allowlist）与 Gate D 完成定义 8 条件 | 跨模块 | 05 §5.15.6/5.15.7（L2709-2724） | 规则 | 已定义 |
| INV-00-42 | GWT-5.15.8-1 扫描范围可复现 | 跨模块 | 05 §5.15.8（L2725-2752） | 验收 | 已定义 |
| INV-00-43 | GWT-5.15.8-2 历史审计不被改写 | 跨模块 | 05 §5.15.8（L2725-2752） | 验收 | 已定义 |
| INV-00-44 | GWT-5.15.8-3 直接命中不等于唯一影响（零文本命中也要语义复核） | 跨模块 | 05 §5.15.8（L2725-2752） | 验收 | 已定义 |
| INV-00-45 | GWT-5.15.8-4 API 与 DB 同批（新增 Schema 无对应 DB 表则 D2 不完成） | 跨模块 | 05 §5.15.8（L2725-2752） | 验收 | 已定义 |
| INV-00-46 | GWT-5.15.8-5 旧自治规则转负例（confidence>0.80 自动入库改为应生成 ReviewTask 的负例） | 跨模块 | 05 §5.15.8（L2725-2752） | 验收 | 已定义 |
| INV-00-47 | GWT-5.15.8-6 PRD 迁移不丢需求（Locator 迁自动化开发、APIContract 迁知识库，原功能可寻） | 跨模块 | 05 §5.15.8（L2725-2752） | 验收 | 已定义 |
| INV-00-48 | GWT-5.15.8-7 允许引用不误报（CHANGELOG 旧路径分类为允许历史引用） | 跨模块 | 05 §5.15.8（L2725-2752） | 验收 | 已定义 |
| INV-00-49 | GWT-5.15.8-8 复审独立（方案自称已同步不覆盖独立审计事实） | 跨模块 | 05 §5.15.8（L2725-2752） | 验收 | 已定义 |
| INV-00-50 | 效果衡量指标体系（效率 7 项+质量 8 项，每项须有基线/测量方法/GWT，禁止无基线百分比目标） | 跨模块 | 05 §八（L2802-2830）；总纲 §7（L40-48） | 非功能 | 部分定义 |
| INV-00-51 | 总纲全局验收原则（GWT 含正常/异常/权限/陈旧/降级；文档静态一致≠业务验收；三层证据分别报告；版本交付列清范围/非目标/基线/限制/恢复） | 跨模块 | 总纲 §8（L50-54） | 规则 | 已定义 |
| INV-00-52 | 总纲目标与非目标（5 目标/5 非目标：V0 无 SaaS、V1 无人测试承诺、不复制 Project、不跳过审核/写入批准/签署、无基线不承诺收益并发延迟准确率） | 跨模块 | 总纲 §3（L13-23） | 规则 | 已定义 |
| INV-00-53 | 成功度量方法（5 维度指标 + 防误导约束；先人工基线再比较） | 跨模块 | 总纲 §7（L40-48） | 非功能 | 部分定义 |
| INV-00-54 | 全局对象边界（项目/发布版本/环境/工作台首页/Agent-Skill 不计入一级模块） | 跨模块 | 05 §2.2（L48-56） | 规则 | 已定义 |
| INV-00-55 | 人机职责边界（§3.4：10 类必须人工审核项 vs 7 类可自动但留痕项） | 跨模块 | 05 §3.4（L134-161） | 规则 | 已定义 |
| INV-00-56 | 正式产出物统一生命周期与概念阶段映射（BACKLOG/IN_PROGRESS/PENDING_REVIEW/REWORK/APPROVED/PUBLISHED/ARCHIVED，各实体状态机必须可映射） | 跨模块 | 05 §3.3（L105-133） | 规则 | 已定义 |
| INV-00-57 | V0 版本演进承诺（V0 设计和 Gate 0 原型/V1 单 Workspace 试点闭环/V2 团队协同/V3 企业规模） | 跨模块 | 地图 §6（L47-55） | 规则 | 仅原则性声明 |

---

## 3. 按 8 模块分组统计

| 模块 | 需求条目数 | GWT 验收标准数 | 仅原则性声明条数 | 部分定义条数 |
|---|---|---|---|---|
| 01 任务看板 | 64 | 23（PRD10 AC×4 + 05 §5.5.12×8 + §5.6.10×10 + §5.12.12-1） | 1（地图 §2 承诺） | 0 |
| 02 知识库 | 47 | 18（PRD11 AC×4 + 05 §5.10.11×12 + §5.12.12-2/-5） | 1（地图 §2 承诺） | 0 |
| 03 测试策划与设计 | 45 | 14（PRD12 AC×4 + 05 §5.7.10×10） | 1（地图 §2 承诺） | 0 |
| 04 自动化测试开发 | 44 | 15（PRD13 AC×4 + 05 §5.8.13×10 + §5.12.12-6） | 1（地图 §2 承诺） | 1（§5.8.2 预留类型） |
| 05 测试执行 | 25 | 5（PRD14 AC×4 + §5.12.12-3） | 1（地图 §2 承诺） | 0 |
| 06 质量分析与缺陷 | 48 | 16（PRD15 AC×4 + 05 §5.9.11×12） | 1（地图 §2 承诺） | 0 |
| 07 AI Agent 中心 | 27 | 7（PRD16 AC×6 + §5.12.12-9） | 1（地图 §2 承诺） | 1（Gate 0 基线） |
| 08 平台管理 | 51 | 19（PRD17 AC×4 + 05 §5.11.12×12 + §5.12.12-4/-7/-8） | 1（地图 §2 承诺） | 0 |
| 00 跨模块全局契约 | 57 | 27（05 §5.12.12-10 + §5.13.8×8 + §5.14.8×10 + §5.15.8×8） | 1（地图 §6 承诺） | 4（V2/V3 增量、效果衡量指标、成功度量方法） |
| **合计** | **408** | **144** | **9** | **6** |

> 统计口径说明：
> 1. GWT 验收标准数 = 05 方案 §5.5–5.15 各节 GWT 基线条目（110 条）+ 各 PRD AC 条目（34 条：10/11/12/13/14/15/17 各 4、16 号 6）= 144 条；其中 05 §5.12.12 的 10 条按涉及模块分配（9 条入 01/02/04/05/07/08，1 条归跨模块）。
> 2. 05 方案 §5.12.12 共 10 条 GWT，其中 9 条按涉及模块分配到 01/02/04/05/07/08，1 条（退场实体无新写入）归跨模块。
> 3. §5.6 正式产出物审核契约（含 §5.6.10 的 10 条 GWT）整体计入任务看板（ReviewTask 归看板），但其内容约束全部 8 个业务模块——若按"产出物 Owner"重新归属，GWT 计数将向各业务模块分散，此为口径选择而非遗漏。
> 4. 部分 05 GWT 条目与 PRD AC 语义重叠（如 05 §5.6.10-3 外部 Bug 写入 ≈ PRD10 AC-03、05 §5.8.13-5 ≈ PRD13 AC-04 的越权面），本清单按来源分别计数，未合并去重，符合"不合并重复计数"要求；如需去重口径可另出映射表。
> 5. 需求条目总数 408 = 8 模块 351 + 跨模块 57。若只统计"8 模块 × 各功能能力行"的最小编制（PRD 功能需求表行 62 条 + 05 契约子节规则约 97 条 + GWT 144 条 + 承诺 9 条），最小口径约为 312 条；本清单采用"每条规则/每条 GWT/每个 AC 均独立计数"的完整口径。

---

## 4. 未核实项清单

> 以下项目在本轮盘点中无法仅凭上述 11 份文档核实，需主代理/后续子代理用其他权威源（03 术语表、04 核心领域模型、32-API 规范、33-数据库 Schema、34-认证授权设计、21-AI 介入点降级矩阵、55-Agent 治理 SOP、22-版本规划）交叉验证：

| 编号 | 未核实项 | 原因 | 建议核实源 |
|---|---|---|---|
| U-01 | WorkItem 25 个最小字段是否已落入 33-数据库 Schema 与 32-API 规范（含 lockVersion、currentActorType） | 05 §5.5.3 是产品契约，未在本次盘点范围内核对技术契约 | 33、32、04 |
| U-02 | 八类正式产出物的通用审核接口（14 字段）是否在 03/04 中按实体落地（reviewStatus 状态枚举一致性） | 05 §5.6.2 明确"不要求立即建立通用 Artifact 表" | 03、04、33 |
| U-03 | §5.11 稳定能力键（10 族）是否与 34-认证授权设计中的能力目录完全一致（含独立外部写入/签署/门禁豁免能力键） | 05 §5.11.5 自述"Gate D 已同步"，需独立验证 | 34、32 |
| U-04 | 内置角色模板 6 个与总纲 §2 用户身份 7 类（TestEngineer/TestLead/WorkspaceAdmin/TenantAdmin/PlatformAdmin/ViewerAuditor/Service-Agent）的映射关系是否完整闭环 | 总纲含 Service/Agent 身份，05 §5.11.3 未单列机器身份模板 | 总纲 §2、34、55 |
| U-05 | Gate 0 基线（1 Supervisor+3 Subagent、14 Skill）与实际 `prototypes/agent-governance/agents.json` 配置的一致性 | PRD16 §4 引用原型资产，不在本次文档范围内 | prototypes/agent-governance/agents.json |
| U-06 | qf-platform-reviewer 的 `platform-review-agent.json` 与 `platform-review-workflow.json` 是否存在且与 PRD16 §4 描述一致 | PRD16 提及文件，本次未读取 | prototypes/ 目录 |
| U-07 | Release 生命周期（Planning/Testing/Released/Archived）是否已在 33-数据库与 32-API 落地，且与 §5.7.8 规则 6（Testing→Released 需签字报告）一致 | 05 §5.7.3 为职责定义 | 33、32 |
| U-08 | V1"Web/API 各至少 4 类结果样例"等退出条件是否有对应的运行时 E2E 验证资产（05 §5.15.3 提到 e2e-validation 原型已部分改造） | 05 §5.13.3 为验收要求，未核实实现状态 | prototypes/e2e-validation/、05-audits |
| U-09 | 总纲 §7 成功度量"先建立人工基线"是否已在 22-版本规划中给出基线方法（本清单见 05 §八 指标仍为"部分定义"） | 05 §八 自述"必须在对应 PRD 中补充基线" | 22、20-非功能需求 |
| U-10 | PRD 10–17 的"版本范围"节（V1/V2/V3 各模块能力承诺）与 05 §5.13 版本表是否逐项对齐（如 PRD10 §8 与 05 §5.13.3 任务看板行） | 双源并存，未做逐格比对 | 22、05 §5.13、各 PRD §8/§7 |
| U-11 | PRD16 §2"独立平台评审 9 个领域"与 05/治理文档中的评审范围定义是否一致（05 未重复列出 9 领域明细） | PRD16 是唯一列出 9 领域处 | 55、05 §10.6 Gate E |
| U-12 | 文档破损/加密/格式不支持、Runner 失联、网络中断等异常路径是否在 32-API 中有对应错误码（如 STALE_ARTIFACT_VERSION、RUNNER_CAPABILITY_MISSING、SECRET_ACCESS_DENIED） | 各 PRD 定义错误码，未核对 API 契约 | 32 |
| U-13 | 05 §5.10.4"在线 URL 导入防内网探测/重定向绕过"等安全约束是否已落入非功能需求 20 号与安全设计 | 05 为产品契约 | 20、31 |
| U-14 | 地图 §3 测试生命周期主闭环与 05 §5.1 主流程是否在导航/线框（06-wireframes）中一致呈现（任务看板为流程入口） | 本次未读线框 | docs/06-wireframes/* |
| U-15 | "30 个 Skill 原型"（05 §5.15.3）与 PRD16 Gate 0"14 个 Skill"的计数关系（30 为存量全量、14 为 Gate 0 范围？） | 05 与 PRD16 数字并存，未核实 | prototypes/skills/ 目录清单 |

---

## 5. 盘点方法与口径说明（附）

- **只读原则**：本盘点未修改任何被评审文档；输出仅写入 `.cluster/qf-req-review-20260813/subagent_01_inventory.md`。
- **条目来源覆盖**：① 8 份 PRD（10–17）的「功能需求」表行（62 行，全部覆盖）；② 05 方案 §5.5–5.15 的规则条款（每子节按规则簇计 1 条）与 GWT 基线（每小条计 1 条，共 110 条）；③ 各 PRD 验收标准 AC（34 条）；④ 总纲 §5 核心业务规则 8 条（按 Owner 映射到模块）；⑤ 功能地图 §2 模块职责承诺 8 行 + §6 版本演进承诺 1 条（作为"仅原则性声明"计入）。
- **正式产出物契约 vs 模块功能需求**：05 §5.6（正式产出物与审核契约）明确标注为跨模块审核契约（条目以 * 标注并计入任务看板）；§5.7/§5.8/§5.9/§5.10 分别为策划设计/自动化/质量/知识库的实体契约，已归入对应模块。§5.6 与各 PRD「正式产出物」节（PRD12/15 的 §2）存在承接关系：PRD 定义产出物内容，05 定义审核与版本规则，两者互补不重复。
- **计数完整性**：8 模块 × 各功能能力行全覆盖（PRD10 7 行、PRD11 7 行、PRD12 7 行、PRD13 8 行、PRD14 8 行、PRD15 7 行、PRD16 8 行、PRD17 10 行 = 62 行，全部有对应条目）；未发现任何模块缺失。
