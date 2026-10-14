# QualityForge 术语表（Glossary）

> 本文档是QualityForge模块名、页面名、领域实体名、状态名和AI治理概念的术语权威源。产品展示名、领域名、API名和DB名可以采用不同命名风格，但必须遵守本文映射。旧名只用于迁移、历史审计和Source Trace，不得继续作为现行可写契约。

## 1. 命名约定

| 层级 | 规范 |
|---|---|
| 产品展示 | 面向测试人员，优先使用清晰中文业务语言 |
| 领域实体 | 使用稳定PascalCase英文名 |
| API资源 | 使用复数kebab-case；JSON字段使用camelCase |
| DB物理名 | 表/列使用snake_case，表统一`t_`前缀 |
| 状态/枚举 | API统一UPPER_SNAKE_CASE；UI负责中文本地化 |
| 历史名称 | 在“旧名/别名”列标记；废弃名不得创建新实体、字段或路径 |

产品版本V0/V1/V2/V3与API URL中的`/api/v1`、`/api/v2`属于不同版本轴，不得混用。

---

## 2. 一级模块命名

| 英文规范名 | 中文展示名 | 领域/API边界 | 旧名/别名 | 定义 |
|---|---|---|---|---|
| **Work Board** | 任务看板 | Work Management；`/work-items`、`/review-tasks` | Workbench中的任务卡片 | 统一展示人工任务、Agent运行、阻塞、依赖、审核待办、返工和进度；拥有工作项，不拥有业务产出物正文。 |
| **Knowledge Base** | 知识库 | Knowledge；`/knowledge` | Knowledge Center、知识中心 | 管理原始来源、需求、API契约、已审核知识、Source Trace、检索和知识候选发布，是AI的可信输入源。 |
| **Test Planning & Design** | 测试策划与设计 | Test Planning & Design；`/test-strategies`、`/test-plans`、`/test-cases` | Test Design、测试设计 | 把Release目标、需求和风险转化为策略、计划、规则、场景、用例、断言和覆盖结论。 |
| **Test Automation Development** | 自动化测试开发 | Automation；`/automation` | Test Asset中的脚本/数据/Locator/Mock | 把批准的测试设计转化为可审查、可调试、可执行的Web/API自动化代码及其配套资产。 |
| **Test Execution** | 测试执行 | Execution；`/execution-plans`、`/execution-tasks`、`/execution-results` | Execution、Test Execution | 冻结精确资产、环境和契约版本，调度Runner并保存不可变执行结果与制品。 |
| **Quality Analysis & Defects** | 质量分析与缺陷 | Quality；`/quality` | Quality Intelligence、测试分析、CI/CD Center | 将原始执行证据转化为结果分析、失败聚类、Defect、报告、门禁和交付集成结论。 |
| **AI Agent Center** | AI Agent中心 | AI Governance；`/ai/agents`、`/ai/skills`、`/ai/workflows`、`/ai/evals` | Agent Center、Skill Center、Test Capability Center | 管理Agent、Skill、Workflow、Prompt、Trace、Eval、权限和运行治理；不拥有业务产出物最终批准权。 |
| **Platform Administration** | 平台管理 | Platform；`/platform` | Platform Settings、系统设置 | 管理租户、用户、Workspace、Release、Environment、RBAC、Secret、模型、Runner、集成和审计。 |

以下旧一级模块正式退场：

- **Test Asset**：不再作为一级模块；用例/套件归测试策划与设计，代码/数据/Locator/Mock归自动化测试开发，APIContract归知识库。
- **Skill Center**：产品入口并入AI Agent中心；Skill与Agent领域实体和生命周期仍分离。
- **CI/CD Center**：产品入口并入质量分析与缺陷，作为流水线和质量门禁集成能力。
- **Workspace**：不再作为独立业务功能模块；产品界面显示“项目”，技术实体仍为Workspace，基础管理归平台管理。

---

## 3. 主要页面命名

| 英文规范名 | 中文展示名 | 所属模块 | 旧名/别名 | 定义 |
|---|---|---|---|---|
| **Work Board** | 任务看板 | 任务看板 | Workbench任务区 | 展示我的任务、Agent处理中、待审核、返工、阻塞和计划/Release进度。 |
| **Review Inbox** | 审核收件箱 | 任务看板 | 用例评审板、知识审核台 | 按风险、SLA和产出物类型聚合ReviewTask，提供精确版本、Diff、证据和决议入口。 |
| **Source Library** | 来源资料库 | 知识库 | 需求列表、文档中心 | 管理RequirementDocument、OpenAPI、仓库和其他SourceSnapshot。 |
| **API Contract Library** | API契约库 | 知识库 | 契约管理、API资产 | 展示APIContract版本、Operation、Diff、审核和基线。 |
| **Planning & Design Workbench** | 策划与设计工作台 | 测试策划与设计 | Test Design Workbench | 生成和审核策略、计划、规则、场景、用例、断言与覆盖缺口。 |
| **Automation Workbench** | 自动化开发工作台 | 自动化测试开发 | 资产中心、脚本编辑器 | 管理Web/API代码、Diff、检查、Code Review、试运行、数据、Locator和Mock。 |
| **Execution Console** | 执行控制台 | 测试执行 | 执行面板 | 创建ExecutionPlan，查看任务、实时进度、日志、证据和Runner使用情况。 |
| **Quality Dashboard** | 质量分析看板 | 质量分析与缺陷 | Quality Intelligence Dashboard | 展示覆盖、失败、风险、Defect、报告、趋势和门禁。 |
| **Defect Review** | 缺陷审核台 | 质量分析与缺陷 | 智能缺陷推荐、一键提单 | 审核内部DefectVersion、证据、重复候选和外部同步。 |
| **Agent Governance Console** | Agent治理台 | AI Agent中心 | Agent Registry & Orchestrator | 管理Agent/Skill/Workflow/Prompt、权限、Trace和Eval。 |
| **Platform Console** | 平台管理台 | 平台管理 | System Integration Settings | 管理成员、RBAC、Environment、Secret、模型、Runner、Integration和Audit。 |

首页可继续使用**Workbench/工作台**作为跨模块摘要入口，但它不拥有WorkItem、业务产出物或平台配置。

---

## 4. 项目、身份与平台实体

| 领域规范名 | 中文 | 唯一业务Owner | 旧名/别名 | 定义 |
|---|---|---|---|---|
| **Tenant** | 租户 | 平台管理 | Organization（非同义，仅外部映射） | 多租户隔离和租户级策略边界。 |
| **User** | 用户 | 平台管理 | Account | 人类身份及认证关联；不以单一`role`字段表达最终权限。 |
| **Workspace** | 项目/工作空间 | 平台管理 | Project（仅UI别名）、Project Container | 测试数据、权限和执行上下文的顶级业务边界。UI统一显示“项目”，技术契约只使用Workspace/workspaceId，不新增Project实体。 |
| **Release** | 发布版本 | 平台管理 | 发版节点、业务版本 | Workspace内一次业务发布的追溯锚点；不等于任何资产的修订version。 |
| **Environment** | 测试环境 | 平台管理 | Env | 被测部署环境的身份、能力和健康状态；Secret只保存引用。 |
| **WorkspaceSecret** | 项目密钥 | 平台管理 | Secret | 加密保存的凭证引用、作用域、轮换和吊销记录；普通接口不返回明文。 |
| **RunnerNode** | 执行节点 | 平台管理 | Runner、执行机 | 注册、提供执行能力并回传健康状态的物理或虚拟节点；执行模块只调度使用。 |
| **LlmConfig** | 模型配置 | 平台管理 | LLM Gateway Config | 模型供应商、模型路由、配额和Secret引用配置。 |
| **IntegrationConfig** | 集成配置 | 平台管理 | Integration | Git、Jira、PingCode、SSO、消息等厂商中立的认证与作用域配置。 |
| **AuditLog** | 审计日志 | 平台管理 | Audit Event | 只追加的高价值操作、安全、授权和外部写入审计记录。 |

---

## 5. 任务、审核与授权实体

| 领域规范名 | 中文 | 唯一业务Owner | 旧名/别名 | 定义 |
|---|---|---|---|---|
| **WorkItem** | 工作项 | 任务看板 | Task、Job（仅运行实例别名） | 人、Agent或系统为产生/审核/执行测试产出物而处理的统一业务工作单元。注：WorkItemType 含 `TEST_DESIGN`，与 21 号介入点 `TEST_DESIGN` 同名不同义，按上下文区分（裁决 2026-08-14）。 |
| **WorkItemArtifact** | 工作项产出物关联 | 任务看板 | - | WorkItem与精确业务产出物版本/摘要的关系。 |
| **WorkItemRun** | 工作项处理尝试 | 任务看板 | Attempt | 一次人工、Agent或系统处理尝试，不等于业务产出物。 |
| **WorkItemEvent** | 工作项事件 | 任务看板 | Task History | 只追加记录状态、责任、阻塞、恢复和取消变化。 |
| **WorkItemDependency** | 工作项依赖 | 任务看板 | Dependency | WorkItem之间的有向依赖关系，禁止形成循环。 |
| **ReviewTask** | 审核任务 | 任务看板 | HITL Task、评审任务、审批单 | 绑定精确artifactId/version/contentDigest、审核策略、Reviewer/Approver职责和决议的人工任务。 |
| **ReviewAssignment** | 审核分配 | 任务看板 | - | ReviewTask与指定审核人、职责、能力、SLA的关系。 |
| **ReviewPolicy** | 审核策略 | 平台管理 | HITL Policy | 按产出物类型和风险定义审核阶段、人数、能力、职责分离和阻断检查。 |
| **RoleDefinition** | 角色定义 | 平台管理 | Role | 可版本化的能力集合模板。 |
| **RoleBinding** | 角色绑定 | 平台管理 | User Role | 把角色模板按PLATFORM/TENANT/WORKSPACE/RESOURCE作用域和有效期授予主体。 |
| **Permission** | 权限能力 | 平台管理 | Capability | 稳定`resource.action`能力键及其风险/条件约束。 |
| **AuthorizationDecision** | 授权决定 | 平台管理 | AuthZ Decision | 服务端对高价值动作作出的ALLOW/DENY及策略/角色/条件快照。 |
| **Reviewer** | 审核人职责 | 审核流程 | 审查员 | ReviewTask中的临时职责，不是全局万能用户角色。 |
| **Approver** | 批准人职责 | 审核流程 | 审批人角色（废弃） | 对正式生效承担责任的ReviewTask职责；只能由具备相应能力的人类承担。 |

内置RBAC角色模板为PlatformAdmin、TenantAdmin、WorkspaceAdmin、TestLead、TestEngineer和ViewerAuditor。管理员身份不自动获得测试业务批准能力。

---

## 6. 知识与API契约实体

| 领域规范名 | 中文 | 唯一业务Owner | 旧名/别名 | 定义 |
|---|---|---|---|---|
| **RequirementDocument** | 需求文档 | 知识库 | Requirement | 导入的PRD、用户故事等需求来源的稳定身份；内容变化形成不可变版本/快照。 |
| **SourceSnapshot** | 来源快照 | 知识库 | Raw Source | 某次文件、URL、仓库、手工或流量来源的不可变内容、位置、revision和digest。 |
| **SourceTrace** | 来源溯源 | 知识库 | Provenance | 从原始来源、规则、用例、代码、执行到分析/Defect/报告的只追加可追溯关系。 |
| **APIContract** | API契约 | 知识库 | Swagger Spec、接口资产 | Workspace内一个逻辑API服务/契约集合的稳定身份，不再等于单个path+method行。 |
| **APIContractVersion** | API契约版本 | 知识库 | Normalized Spec | 从SourceSnapshot解析、规范化、审核和发布的不可变完整契约版本。 |
| **APIOperationVersion** | API操作版本 | 知识库 | Endpoint Contract | APIContractVersion中的不可变method/path/parameter/request/response/security子项。 |
| **APIContractBaseline** | API契约基线 | 知识库 | API Schema Baseline | 某Release及设计/Mock/分析用途批准采用的精确契约版本集合。 |
| **KnowledgeEntry** | 知识条目 | 知识库 | Knowledge Item、Test Pattern | 具有来源、适用范围、验证证据、失效条件、版本和人工发布记录的正式知识。 |
| **KnowledgeCandidate** | 知识候选 | 知识库 | Pattern Draft | 从分析、Defect、复盘等产生的待审核建议；不得直接进入RAG正式检索。 |
| **KnowledgeVector** | 知识向量 | 知识库 | Vector Chunk | 从已发布KnowledgeEntryVersion派生、可重建的检索索引，不是业务事实。 |
| **AIContextSnapshot** | AI上下文快照 | 知识库 | AIContext、WorkspaceAIContext（废弃实体） | 针对WorkItem从批准来源、规则、环境引用和策略生成的不可变推理输入快照。Prompt归Agent中心，模型路由归平台管理。 |

---

## 7. 测试策划与设计实体

| 领域规范名 | 中文 | 唯一业务Owner | 旧名/别名 | 定义 |
|---|---|---|---|---|
| **TestStrategy** | 测试策略 | 测试策划与设计 | TestDesignPlan、测试方案（均废弃） | 对Release定义目标、范围、风险、方法、测试类型、准入/退出、环境/数据/自动化/缺陷策略的正式产出物。 |
| **TestPlan** | 测试计划 | 测试策划与设计 | 发版里程碑（废弃语义） | 基于批准TestStrategy拆解责任、时间、任务、资源、依赖和验收标准的正式活动计划。 |
| **TestingIR** | 测试中间表示 | 测试策划与设计 | Testing IR | 从精确需求/API来源编译出的结构化需求、规则、实体、状态机、接口和约束中间表示。 |
| **BusinessRule** | 业务规则 | 测试策划与设计 | - | 从TestingIR提取并经复核的条件、动作、来源和适用范围。 |
| **TestScenario** | 测试场景 | 测试策划与设计 | TestScene（废弃） | TestPlan下需要覆盖的业务路径或质量场景。 |
| **DesignTestCase** | 用例草稿 | 测试策划与设计 | 设计测试用例、候选用例 | AI/人工生成的待审核用例版本；批准后形成或修订正式TestCase。 |
| **TestCase** | 测试用例 | 测试策划与设计 | 用例资产 | 跨计划复用的正式测试意图，包含前置、步骤、数据、预期、断言、来源和版本。 |
| **Assertion** | 断言 | 测试策划与设计 | - | 绑定精确用例版本的可验证target/expression/expected及来源。 |
| **TestSuite** | 测试套件 | 测试策划与设计 | 用例集 | 经过版本化的静态/规则用例集合；执行计划只引用精确套件版本。 |

`TestDesignPlan`不再是现行实体；历史ID通过legacyRef/Source Trace映射到TestStrategy。

---

## 8. 自动化测试开发实体

| 领域规范名 | 中文 | 唯一业务Owner | 旧名/别名 | 定义 |
|---|---|---|---|---|
| **AutomationScript** | 自动化脚本 | 自动化测试开发 | 自动化代码身份 | Web/API等自动化实现的稳定身份。 |
| **AutomationScriptVersion** | 自动化代码版本 | 自动化测试开发 | Script Version | 不可变代码、语言、框架、来源、commit/blob/digest、配置、审核和发布版本，是正式产出物。 |
| **AutomationScriptVersionCaseBinding** | 代码用例绑定 | 自动化测试开发 | script.testCaseId（废弃） | 自动化代码版本与一个或多个精确TestCaseVersion的覆盖关系。 |
| **AutomationCheckRun** | 自动化检查运行 | 自动化测试开发 | Code Check | 语法、静态、安全、依赖和隔离试运行的只追加结果。 |
| **TestData** | 测试数据 | 自动化测试开发 | Data Set | 参数化输入、生成结果或受控数据引用，包含脱敏、版本和清理信息。 |
| **TestDataProfile** | 测试数据配置 | 自动化测试开发 | Data Profile | 测试数据Schema、生成、约束、脱敏和清理策略。 |
| **Locator** | 定位符 | 自动化测试开发 | Selector | UI元素定位的版本化定义；执行产生自愈候选，人工审核后才更新正式版本。 |
| **MockConfig** | Mock配置 | 自动化测试开发 | Mock Rule | 绑定精确APIContractVersion的Mock行为、匹配和响应配置。 |
| **VisualBaseline** | 视觉基线 | 自动化测试开发 | BaselineItem.UI_SCREENSHOT | 经审核的视觉预期版本。 |
| **PerformanceBaseline** | 性能基线 | 自动化测试开发 | BaselineItem.PERFORMANCE_METRIC | 经审核的性能预期版本；按版本计划后续启用。 |

通用`BaselineItem`实体退场；API Schema基线统一使用APIContractBaseline。

---

## 9. 测试执行实体

| 领域规范名 | 中文 | 唯一业务Owner | 旧名/别名 | 定义 |
|---|---|---|---|---|
| **ExecutionPlan** | 执行计划 | 测试执行 | Run Plan | 绑定TestPlan、精确用例/代码版本、环境、触发、并发和Runner策略的机器运行配置。 |
| **ExecutionContractBaseline** | 执行契约基线 | 测试执行 | Runtime Contract Snapshot | ExecutionPlan发布时冻结的APIContract版本、环境映射、认证引用和digest。 |
| **ExecutionTask** | 执行任务 | 测试执行 | Run Task | ExecutionPlan触发后产生的物理作业实例。 |
| **ExecutionResult** | 执行结果 | 测试执行 | Test Result | 单个用例在ExecutionTask中的不可变执行事实；通过、失败、跳过、错误和未判定必须区分。 |
| **ExecutionArtifact** | 执行制品 | 测试执行 | Log/Screenshot/Video/Trace | 日志、截图、视频、Trace、请求/响应等受控制品的引用、digest、权限和保留策略。 |
| **APIObservation** | API观察 | 测试执行 | Traffic Observation | 执行中实际请求/响应的脱敏事实，不得反向改写正式APIContract。 |
| **ContractCheckResult** | 契约检查结果 | 测试执行 | Contract Diff Result | APIObservation与ExecutionContractBaseline比较得到的MATCH/DEVIATION/NOT_CHECKED/INCONCLUSIVE结果。 |

---

## 10. 质量分析与缺陷实体

| 领域规范名 | 中文 | 唯一业务Owner | 旧名/别名 | 定义 |
|---|---|---|---|---|
| **ResultAnalysis** | 结果分析 | 质量分析与缺陷 | Analysis Result | 引用不可变执行证据并区分事实、推断、置信度、替代解释和影响的正式产出物。 |
| **FailureCluster** | 失败聚类 | 质量分析与缺陷 | Error Cluster、Defect Group | 在指定算法/规则版本下对相似失败的候选分组；不等于Defect。 |
| **FailureAnalysis** | 失败分析 | 质量分析与缺陷 | RCA Result | 对单个或一组失败的分类、根因候选和建议；人工审核不能用`manualVerified`布尔值替代。 |
| **CoverageReport** | 覆盖率报告 | 质量分析与缺陷 | Coverage Analysis | 按明确分母、精确版本和有效证据计算的规则/场景/状态/断言/API覆盖结果；未检查不计通过。 |
| **Defect** | 缺陷 | 质量分析与缺陷 | Bug（UI别名） | 平台内部问题的稳定身份和生命周期；不等于FailureCluster或外部Issue。 |
| **DefectVersion** | 缺陷版本 | 质量分析与缺陷 | Bug Draft | 包含标题、步骤、预期、实际、严重度、优先级、环境、证据、来源和digest的正式产出物版本。 |
| **DefectEvidence** | 缺陷证据 | 质量分析与缺陷 | - | DefectVersion与执行、分析、需求、规则、日志、截图等精确证据的关系。 |
| **ExternalDefectLink** | 外部缺陷映射 | 质量分析与缺陷 | jiraIssueKey（废弃字段） | 内部Defect与Jira/PingCode等外部Issue的厂商中立映射。 |
| **DefectSyncAttempt** | 缺陷同步尝试 | 质量分析与缺陷 | Defect Export | 绑定批准DefectVersion、最终Payload摘要、人工EXTERNAL_WRITE批准、幂等键和回执的外部操作记录。 |
| **TestReport** | 测试报告 | 质量分析与缺陷 | - | 绑定不可变范围/结果/覆盖/缺陷/风险快照并经REPORT_SIGNOFF的正式质量产出物。 |
| **QualityGate** | 质量门禁 | 质量分析与缺陷 | Gate | 基于确定性规则和已批准输入给出放行、警告、阻断或需人工决定的门禁。 |
| **PipelineConfig** | 流水线配置 | 质量分析与缺陷 | CI/CD Config | 外部流水线触发、测试选择和QualityGate绑定配置；凭证归IntegrationConfig。 |
| **PipelineRun** | 流水线运行 | 质量分析与缺陷 | CI Run | 一次流水线触发、测试、门禁输入、决定和外部回执的只追加记录。 |

---

## 11. AI Agent中心实体与概念

| 规范名 | 中文 | 旧名/别名 | 定义 |
|---|---|---|---|
| **Skill** | 技能 | Capability、Test Capability | 可复用的原子能力或确定性门禁，具有输入/输出Schema、版本、权限需求和Eval。 |
| **Agent** | 智能体 | AI Agent | 受职责、Skill allowlist、文件/网络/Secret/外部写入和委派边界约束的机器身份。 |
| **AgentWorkflow** | Agent工作流 | Workflow | 固定或版本化的Agent/Skill调用DAG及人工检查点。 |
| **AgentPromptVersion** | Agent Prompt版本 | Prompt Versioning | 不可变System Prompt、参数、兼容范围、评测和发布版本。 |
| **AgentSession** | Agent会话 | Agent Run | 一次Agent处理会话的状态、输入/输出摘要、成本、耗时和WorkItem关联。 |
| **AgentTraceNode** | Agent追踪节点 | Chain of Thought（禁止作为同义词） | 记录决策摘要、证据、路由、工具、脱敏输入/输出和错误；不保存或展示隐藏思维链。 |
| **SkillInvocation** | Skill调用 | Tool Invocation | 一次Skill调用的版本、输入摘要、权限决定、结果和错误。 |
| **EvalDataset/EvalCase** | 评测集/评测用例 | - | 经批准的正反样例、期望和版本。 |
| **EvalRun/EvalResult** | 评测运行/结果 | - | Agent、Skill、Prompt在精确版本上的只追加评测证据。 |
| **AI Producer** | AI生产者 | Generator Agent | 生成或修改草稿的Agent责任；永远不能批准正式产出物。 |
| **Independent Verifier** | 独立验证者 | Checker Agent | 与生成角色分离，输出机器裁决和人工路由；不能修复被审资产或代替人工批准。 |
| **Platform Review Agent** | 平台独立评审Agent | Platform Reviewer | 位于生产Agent委派图之外，基于冻结快照对测试平台的产品、需求、架构、契约、安全、AI治理、可测试性、体验和验收证据进行只读评审；只输出咨询性Finding和整改建议，不能参与被审建设、修复Finding或代替人工处置。 |
| **Source Trace** | 来源溯源 | Provenance | 见§6；AI输出必须区分`CONFIRMED/INFERRED/UNRESOLVED`并引用精确来源。 |
| **RAG** | 检索增强生成 | Retrieval-Augmented Generation | 从已发布且权限允许的知识版本检索上下文；向量命中不是事实确认。 |
| **Self Healing** | 自愈候选 | Auto Healing | AI根据执行观察提出Locator/脚本修订候选；正式资产更新仍需审核。 |
| **Conversation** | 协作对话 | Chat Session | 围绕一个Workspace/Release的持续人机协作上下文；不等同于一次Agent运行。 |
| **ConversationMessage** | 对话消息 | Message | 用户、AI或系统在Conversation中的只追加消息，包含来源、可见性和追溯关系。 |
| **ClarificationRequest/Response** | 澄清请求/答复 | Question/Answer | AI因资料缺失、冲突或高风险假设而发起的可审计问题，及人工对其的结构化裁决。 |
| **TaskCard** | 任务卡 | AI Task | 对话意图转换成的结构化任务，固定目标、范围、输入、交付物、验收、预算和风险等约束。 |
| **AgentPlan** | Agent执行计划 | Execution Proposal | 由协调Agent生成、人工确认后生效的分步方案，包含专业Agent、工具、检查点、预算和失败策略。 |
| **TaskContract** | 任务契约 | Run Contract | TaskCard与已确认AgentPlan组成的可执行版本，一次Run必须锁定其精确版本和摘要。 |
| **RunCommand/CommandReceipt** | 运行命令/回执 | Control Command | 暂停、继续、取消、重试或调整范围的受权幂等请求，以服务端回执而非客户端显示为真相。 |
| **EvaluationRun** | 独立评估运行 | Assessment Run | 评估Agent对冻结产出版本运行Rubric并产生分维度结果、阻断项和证据的只追加事实。 |
| **EvaluationRubric** | 评估量规 | Scoring Rubric | 定义评估维度、权重、阻断规则、适用范围和版本的受控规则集。 |
| **CalibrationSample** | 校准样本 | Human Baseline | 用于验证评分与人工基准一致性的已批准样本；无有效校准时分数不能驱动自治。 |
| **ProjectContextProjection** | 项目上下文投影 | Project Cockpit View | 首屏展示的项目/发布、资料完整性、风险和最新活动只读投影。 |
| **WorkOrchestrationProjection** | 工作编排投影 | Work Control View | 汇总TaskCard、AgentPlan、Run、澄清、审核和阻塞的只读投影。 |
| **ReleaseReadinessProjection** | 交付就绪度投影 | Readiness View | 基于已批准事实、执行证据和评估结果生成的只读交付状态投影。 |

Skill是原子能力，Agent是责任/权限/工作流边界；不得按“一项Skill配置一个Agent”机械映射。

Conversation保存长期协作语境，AgentSession保存一次机器运行事实，WorkItem保存业务工作流；三者不得混用。

---

## 12. 正式产出物与审核术语

八类正式测试产出物为：

1. TestStrategy；
2. TestPlan；
3. TestCase；
4. Web/API AutomationScriptVersion；
5. ResultAnalysis；
6. DefectVersion；
7. TestReport；
8. KnowledgeEntry。

| 规范名 | 中文 | 定义 |
|---|---|---|
| **SINGLE_REVIEW** | 单人审核 | LOW/MEDIUM风险时，一名具备专属批准能力的人类可修改AI草稿后批准；记录`independentReview=false`。 |
| **FOUR_EYES** | 四眼审核 | 至少两个不同自然人承担Reviewer和Approver，最终Approver不能是最后修改人。 |
| **CODE_REVIEW** | 代码审核 | 确定性检查、精确代码版本/digest和人工Review组成的自动化代码门禁。 |
| **EXTERNAL_WRITE** | 外部写入批准 | 对provider、integration、operation、精确版本和最终payloadDigest的即时人工批准。 |
| **REPORT_SIGNOFF** | 报告签署 | 对不可变数据快照和正式质量结论的人工签署。 |
| **KNOWLEDGE_PUBLISH** | 知识发布 | 对来源、适用范围、失效条件、敏感信息和复用性的人工批准。 |
| **contentDigest** | 内容摘要 | 对所有受审核正文、结构化字段和证据清单规范化后计算的摘要。摘要变化使旧批准失效。 |
| **STALE** | 待复核/已失效 | 上游来源、证据、权限或内容变化导致原批准不能继续作为当前有效结论。 |

所有正式产出物至少需要一名人类批准；TenantAdmin开关、AI置信度、Agent PASS或确定性检查PASS均不能替代。

---

## 13. 核心状态与枚举

### 13.1 通用产出物审核状态

`DRAFT / GENERATING / PENDING_REVIEW / CHANGES_REQUESTED / APPROVED / PUBLISHED / REJECTED / STALE / ARCHIVED`

### 13.2 WorkItem状态

`BACKLOG / READY / IN_PROGRESS / PENDING_REVIEW / REWORK / APPROVED / BLOCKED / DONE / CANCELLED`

### 13.3 ReviewTask状态

`OPEN / IN_PROGRESS / APPROVED / CHANGES_REQUESTED / REJECTED / EXPIRED / CANCELLED`

### 13.4 ExecutionTask状态

`PENDING / QUEUED / RUNNING / COMPLETED / FAILED / CANCELLED / TIMED_OUT / BLOCKED`

### 13.5 ExecutionResult状态

`PASSED / FAILED / SKIPPED / ERROR / INCONCLUSIVE`

未检查、SKIPPED、ERROR、BLOCKED或INCONCLUSIVE不得折算为PASSED。

### 13.6 Release状态

`PLANNING / TESTING / RELEASED / ARCHIVED`

### 13.7 TestPlan生命周期

`NOT_STARTED / ACTIVE / COMPLETED / CANCELLED / ARCHIVED`

审核状态与生命周期状态必须分字段保存。

### 13.8 Defect生命周期

`NEW / OPEN / IN_PROGRESS / RESOLVED / VERIFIED / CLOSED / REJECTED / DUPLICATE / ARCHIVED`

### 13.9 RequirementDocumentVersion解析状态

`DRAFT / PARSING / COMPLETED / FAILED`

该状态只表达需求版本的解析进度，不代替`reviewStatus`。

RESOLVED表示声称已修复，VERIFIED必须具备回归证据和人工确认。

### 13.10 API契约检查状态

`MATCH / DEVIATION / NOT_CHECKED / INCONCLUSIVE`

### 13.11 风险等级

`LOW / MEDIUM / HIGH / CRITICAL`

### 13.12 失败分类

`PRODUCT_BUG / SCRIPT_ISSUE / ENVIRONMENT_ISSUE / DATA_ISSUE / FLAKY_TEST / UNKNOWN`

### 13.13 AgentSession状态

`PENDING / RUNNING / SUCCEEDED / FAILED / CANCELLED / BLOCKED`

权威源为 33 号 t_agent_session CHECK 约束（同 05 §5.8 WorkItemRun.status 口径）：SUCCEEDED 表示成功完成，BLOCKED 表示等待人工介入或外部依赖。历史值 COMPLETED（系误借 13.4 ExecutionTask 语义）与 PAUSED_FOR_HUMAN（无库表承载）均已废弃，不得再出现在契约与前端代码中。

---

## 14. 废弃术语迁移表

| 废弃术语 | 标准替代 | 保留场景 |
|---|---|---|
| Project/projectId | Workspace/workspaceId | UI“项目”展示、外部系统映射或历史文本 |
| TestDesignPlan/测试方案 | TestStrategy/测试策略 | legacyRef、历史审计和CHANGELOG |
| TestPlan=发版里程碑 | Release + TestPlan | 历史文档说明 |
| Test Asset一级模块 | 按实体Owner拆分 | 历史导航/审计 |
| Quality Intelligence一级模块 | Quality Analysis & Defects | 历史导航/审计 |
| Skill Center一级模块 | AI Agent Center中的Skill管理 | 历史导航/审计 |
| CI/CD Center一级模块 | Quality中的Pipeline/QualityGate | 历史导航/审计 |
| AIContext可写实体 | AIContextSnapshot + Knowledge/Prompt/LlmConfig | legacyRef |
| BaselineItem | APIContractBaseline/VisualBaseline/PerformanceBaseline | 历史数据映射 |
| Runner（领域实体名） | RunnerNode | UI简称Runner |
| jiraIssueKey on FailureCluster | ExternalDefectLink | 历史数据迁移 |
| manualVerified | ReviewTask/ReviewAssignment | 历史数据迁移 |
| L1自动发布正式资产 | 人工审核策略 | 只可作为应被阻断的负例 |
