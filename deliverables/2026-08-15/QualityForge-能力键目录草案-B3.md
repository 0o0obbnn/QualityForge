# QualityForge permissionKey 能力键目录 · 种子清单草案

> 用途：B3 裁决落地物（按 34 §4.2 关键权限整理种子清单）。本草案可直接作为 `docs/04-architecture/34-认证授权设计.md` 附录或独立受控文档 `docs/04-architecture/34a-能力键目录.md` 的素材；正式落库前须经 B4 评审（见 §4 未核实项）。
> 输入依据：34-认证授权设计 §4.2/§5/§6；05-功能模块重构方案 §5.5.10、§5.6.4、§5.11.3、§5.11.5、§5.11.6、§5.11.7、§5.11.9；PRD 10~17 各模块功能表"人工/安全控制"列。
> 状态：DRAFT v0.1 · 2026-08-15 · 共 61 个键（humanOnly=true 40 个，false 21 个）

---

## 1. 执行摘要

- 依据 34 §4.2 关键权限表（8 行）逐条落键，并按其"resourceType + action + humanOnly"结构扩展为种子目录；同时对齐 05 §5.11.5 稳定能力键的九大能力族示例与 §5.5.10 的 WorkItem 能力点（原 `workitem:xxx` 冒号写法与本目录点号写法冲突，见 §4.3-1）。
- 覆盖 8 个一级功能模块（任务看板 / 知识库 / 测试策划与设计 / 自动化测试开发 / 测试执行 / 质量分析与缺陷 / AI Agent 中心 / 平台管理），另设一组"通用正式产出物"能力族（跨模块生命周期动作，不归属单一模块）。
- 角色模板按 34 §4.1 / 05 §5.11.3 六模板标注适用性；"Reviewer/Approver"是 ReviewTask 临时审核职责，不是角色模板，故不在模板列出现（审核职责通过 ReviewPolicy.requiredCapabilities 绑定到本目录中 humanOnly=true 的批准类键）。
- humanOnly=true 的判定与强制语义：仅活跃 UserIdentity 可执行（34 §5 批准算法第 1 步）；Agent/Service 权限交集自动减去（34 §6）；写入 ReviewPolicy.requiredCapabilities 后可被 FOUR_EYES / SINGLE_REVIEW 等策略引用（05 §5.6.4、§5.11.7）。
- 任务要求的五类 humanOnly 必保项均已覆盖：REVIEW 通过/拒绝（`artifact.review`）、报告签署（`report.signoff`）、外部写入批准（`defect.external_write` / `integration.external_write` / `automation.push` / `automation.create_pr`）、Skill 发布（`skill.publish`）、Secret 读取（`secret.read_plaintext` + 人工授权落地 `secret.grant_use`，两者关系见 §4.3-2）。
- 34 §4.2 中"读取 Secret 明文"原始语义为 **humanOnly=否、原则上禁止**（仅受控执行服务短时解密）；本目录保留该语义并在 §4.3-2 记录与 B3 表述的差异，需 B4 裁决。

## 2. 命名规范说明

### 2.1 命名规则

1. 统一格式：`resource_type.action`，小写 snake_case，例如 `defect.external_write`、`quality_gate.override`。
2. `resource_type` 取领域实体稳定名（优先采用 33 号数据库 / 05 §5.12 实体名），`action` 取受控动作词表：`read / create_draft / edit / submit_review / review / approve / publish / archive / manage / run / start / stop / cancel / interrupt / retry / import / expire / resolve / verify / signoff / override / install / grant / register / external_write / bulk_approve / experimental_run / force_transition`。
3. 作用域（PLATFORM/TENANT/WORKSPACE/RESOURCE）、风险等级、条件（conditionSchema）与有效期**不进入键名**，由 Permission.scopeTypes / riskLimit / conditions 单独表达（34 §4.2）；同一键可绑定到多个作用域模板。
4. 批量操作必须独立成键（`test_case.bulk_approve`），不得用普通 approve 隐含批量权（05 §5.11.5、§5.11.12-11 逐项授权）。
5. 外部写入统一动词 `external_write`，具体载体（Git push/PR）可再细化（`automation.push`、`automation.create_pr`）；"批准后由应用服务执行"的发布类动作（`*.publish`）本身 humanOnly=false，但其前置批准为 humanOnly=true（05 §5.11.9：人工批准后由应用服务执行发布）。
6. `artifact.approve` 是通用批准键，**不是万能批准权**：实际批准必须同时匹配 artifactType、风险等级、Workspace、ReviewPolicy 与专属能力键（05 §5.11.5）；外部写入、报告签署、门禁豁免、权限授予、Secret 管理均使用独立键，不被任何 approve 键隐含。

### 2.2 模块前缀表

| 模块 | 前缀（resource_type） | 说明 |
|---|---|---|
| （跨模块通用） | `artifact` | 八类正式产出物通用生命周期（05 §5.6） |
| 任务看板 | `workitem` | 05 §5.5.10 能力点的规范化（原冒号写法废弃，见 §4.3-1） |
| 知识库 | `source` / `api_contract` / `knowledge` | 11-PRD：来源导入、契约版本/基线、知识条目 |
| 测试策划与设计 | `strategy` / `test_plan` / `test_case` / `testing_ir` / `coverage_design` | 12-PRD；coverage_design 仅指设计层覆盖分析中间产物（裁决 B2-1），执行覆盖率归质量模块 |
| 自动化测试开发 | `automation` / `locator` | 13-PRD；mock/test_data/visual_baseline 暂不独立建键（§4.1-3） |
| 测试执行 | `execution` / `execution_plan` | 14-PRD；ExecutionPlan 非八类产出物但正式执行前须批准（05 §5.11.6 注） |
| 质量分析与缺陷 | `analysis` / `defect` / `report` / `quality_gate` / `coverage_report` | 15-PRD |
| AI Agent 中心 | `skill` / `agent` / `workflow` / `eval` | 16-PRD；prompt 键暂缓（§4.1-5） |
| 平台管理 | `workspace` / `integration` / `secret` / `rbac` / `review_policy` / `audit` / `support_access` / `delegation` | 17-PRD / 34；tenant/release/environment/llm/runner_node 暂缓（§4.1-6） |

### 2.3 humanOnly 判定规则

- true：动作必须由人类执行或由人类作出前置批准；Agent、Runner、Scheduler、ServiceIdentity 一律不具备（34 §6 "− humanOnly 能力"；05 §5.11.9）。
- false：系统/Agent 可在授权交集内自动执行；若该动作属于"批准后发布/写入"链路，仍以对应 humanOnly=true 的批准键为前置（如 `artifact.publish` ← `artifact.approve`）。
- 34 §4.2 例外项：`secret.read_plaintext` 为"原则上禁止"型，humanOnly=false 且默认 DENY，仅受控执行服务按 secretRef 短时解密（34 §8）。

## 3. 能力键清单（种子，61 键）

> 角色模板缩写：PA=PlatformAdmin，TA=TenantAdmin，WA=WorkspaceAdmin，TL=TestLead，TE=TestEngineer，VA=ViewerAuditor。
> "对应能力点"列：`05§5.5.10`=原 workitem:xx 能力点；`05§5.11.5`=稳定能力键能力族；`34§4.2`=关键权限表行；`PRDxx`=该模块 PRD 人工/安全控制列。

### 3.1 通用正式产出物（artifact，7 键）

| 能力键 | 模块 | 中文描述 | 适用角色模板 | humanOnly | 对应能力点 |
|---|---|---|---|---|---|
| `artifact.read` | 通用 | 查看产出物及精确版本、Diff、审核记录与来源证据（含检索/审计只读） | 全部六模板；VA 默认可读已授权范围 | false | 05§5.11.5 artifact.read |
| `artifact.create_draft` | 通用 | 创建产出物草稿（AI 生成或人工录入；修订=创建新版本，与 edit 同语义） | TE、TL；Agent 受限（allowlist） | false | 34§4.2 创建/编辑草稿 |
| `artifact.edit` | 通用 | 修改非终态草稿并形成新版本（PENDING_REVIEW 后内容变化须重新审核，05§5.6.7-3） | TE、TL；Agent 受限 | false | 34§4.2 创建/编辑草稿；05§5.6.7 |
| `artifact.submit_review` | 通用 | 提交审核：创建绑定 artifactId/versionId/contentDigest 的 ReviewTask（Agent 可代提交，不能自批） | TE、TL；Agent 受限 | false | 05§5.5.10 workitem:review（提交审核包语义）；05§5.11.5 artifact.submit_review |
| `artifact.review` | 通用 | 作出审核决定：APPROVE / REQUEST_CHANGES / REJECT / COMMENT；仅 UserIdentity 可作出（ReviewDecision 不授予机器身份） | 获授权 Reviewer/Approver 职责（TL、TE 按策略） | **true** | 05§5.5.10 workitem:review（审核意见）；34§5 批准算法第 1 步；PRD10 审核队列 |
| `artifact.approve` | 通用 | 正式产出物最终批准；必须匹配 artifactType/风险/ReviewPolicy/职责分离（四眼时 Reviewer 与 Approver 分离，05§5.11.7） | 按产出物映射专属批准键（见 3.3~3.7） | **true** | 34§4.2 批准正式产出物；05§5.11.5 artifact.approve；05§5.11.6 |
| `artifact.publish` | 通用 | 发布正式版本/设为 primary（人工批准后由应用服务执行；不自动替换历史基线/冻结引用） | 应用服务执行，不直接授予人工 | false | 05§5.11.5 artifact.publish；05§5.11.9 |

### 3.2 任务看板（workitem，6 键）

| 能力键 | 模块 | 中文描述 | 适用角色模板 | humanOnly | 对应能力点 |
|---|---|---|---|---|---|
| `workitem.create` | 任务看板 | 创建工作项（目标/验收标准/类型/优先级；含编辑非终态工作项字段） | TE、TL、WA | false | 05§5.5.10 workitem:create / workitem:edit |
| `workitem.assign` | 任务看板 | 分派人员或 Agent（跨 Workspace 分派须逐 Workspace 授权） | TL、WA | false | 05§5.5.10 workitem:assign |
| `workitem.run` | 任务看板 | 启动、重试或继续处理工作项（人/Agent 均按交集授权） | TE、TL；Agent 受限 | false | 05§5.5.10 workitem:run |
| `workitem.interrupt` | 任务看板 | 中断 AI/系统运行（暂停、取消运行中 Agent 步骤；越权与异常由人处理） | TE、TL | false | 05§5.5.10 workitem:interrupt；PRD10 AI运行 |
| `workitem.cancel` | 任务看板 | 取消工作项（需理由；终态不可原地篡改） | TE、TL、WA | false | 05§5.5.10 workitem:cancel；PRD10 状态流转 |
| `workitem.force_transition` | 任务看板 | 强制流转/异常状态处理（原 workitem:admin 收窄：强制解锁、异常处置；"修改策略"部分归 rbac/review_policy 键） | TL、WA | **true** | 05§5.5.10 workitem:admin；PRD10 阻塞管理 |

### 3.3 知识库（6 键）

| 能力键 | 模块 | 中文描述 | 适用角色模板 | humanOnly | 对应能力点 |
|---|---|---|---|---|---|
| `source.import` | 知识库 | 导入来源（文件/URL/集成/手工/流量），固化 SourceSnapshot、摘要与授权 | TE、TL；Agent 受限 | false | PRD11 来源导入 |
| `source.conflict_resolve` | 知识库 | 裁决来源/规则冲突与敏感性歧义（DECLARED/OBSERVED 冲突不静默合并；撤权标记待重评） | TL、知识责任人（自定义） | **true** | PRD11 来源导入/需求版本；05§5.10.6-5 |
| `api_contract.approve` | 知识库 | 批准 APIContractVersion（精确 versionId+normalizedDigest+diffDigest；BREAKING/安全要求变化需 FOUR_EYES） | TL、契约审核人（自定义） | **true** | 05§5.11.5 api_contract.approve；05§5.10.6-3 |
| `api_contract.baseline_approve` | 知识库 | 批准 APIContractBaseline（设计/Mock/分析用途的契约集合，版本化不可原地覆盖） | TL、测试策划责任人 | **true** | 05§5.11.5 api_contract.baseline_approve；05§5.10.7 |
| `knowledge.publish` | 知识库 | 发布知识条目（KNOWLEDGE_PUBLISH 策略：来源/适用范围/有效期/专家审核；八类产出物之一） | 知识审批人（自定义）、TL | **true** | 05§5.6.4 KNOWLEDGE_PUBLISH；05§5.11.6；34§4.2 发布类；PRD11 知识条目 |
| `knowledge.expire` | 知识库 | 知识失效/纠错判断（过期复审、撤权触发 STALE 重评，不删除历史证据） | 知识责任人（自定义）、TL | **true** | PRD11 知识条目/关键规则；PRD11 §8 指标 M-31 |

### 3.4 测试策划与设计（6 键）

| 能力键 | 模块 | 中文描述 | 适用角色模板 | humanOnly | 对应能力点 |
|---|---|---|---|---|---|
| `strategy.approve` | 测试策划与设计 | 批准 TestStrategy（LOW/MEDIUM 单人；HIGH/CRITICAL FOUR_EYES 且至少一名 TL 能力） | TL（或等效自定义角色） | **true** | 05§5.11.5 strategy.approve；05§5.11.6；PRD12 策略草稿 |
| `test_plan.approve` | 测试策划与设计 | 批准 TestPlan（必须关联已批准策略与 Release；HIGH FOUR_EYES） | TL（或等效计划审批人） | **true** | 05§5.11.5 test_plan.approve；05§5.11.6；PRD12 计划草稿 |
| `test_case.approve` | 测试策划与设计 | 批准 TestCase/DesignTestCase 迁移发布（SINGLE_REVIEW 允许同一人改后批，须标 independentReview=false） | TE、TL | **true** | 05§5.11.5 test_case.approve；05§5.11.6/7；PRD12 场景/用例 |
| `test_case.bulk_approve` | 测试策划与设计 | 批量批准用例（逐项授权，任一 Deny 即该项拒绝，不得整批伪报成功） | TL、TE（按策略） | **true** | 05§5.11.5 test_case.bulk_approve；05§5.11.12-11 |
| `testing_ir.resolve_conflict` | 测试策划与设计 | 裁决 TestingIR 关键规则冲突（IR 验证不等于业务批准） | TL、规则责任人 | **true** | PRD12 TestingIR；PRD12 降级-规则冲突 |
| `coverage_design.accept_gap` | 测试策划与设计 | 决定接受设计层覆盖缺口或生成补充草稿（分母/分子透明；不自动补齐静默发布） | TL、TE | **true** | PRD12 覆盖分析/AC-03 |

### 3.5 自动化测试开发（6 键）

| 能力键 | 模块 | 中文描述 | 适用角色模板 | humanOnly | 对应能力点 |
|---|---|---|---|---|---|
| `automation.experimental_run` | 自动化测试开发 | 隔离试验运行 PENDING_REVIEW 脚本（结果标记 EXPERIMENTAL，不进正式报告/门禁；沙箱量化口径 B2-8） | TE、TL | false | 05§5.8.11；05§5.11.5 execution.experimental_run；PRD13 试运行 |
| `automation.approve` | 自动化测试开发 | 批准 AutomationScriptVersion（CODE_REVIEW：确定性检查通过+人工代码审核+精确提交/摘要；HIGH/CRITICAL FOUR_EYES） | 自动化 Reviewer（自定义）、TL | **true** | 05§5.6.4 CODE_REVIEW；05§5.11.5 automation.approve；05§5.8.10；PRD13 脚本版本 |
| `automation.publish` | 自动化测试开发 | 发布脚本版本并设为 primary（人工批准后应用服务执行；废弃不删历史） | 应用服务执行 | false | 05§5.11.5 automation.publish；05§5.8.10-4 |
| `automation.push` | 自动化测试开发 | Git push 外部写入（EXTERNAL_WRITE：每次写入前人工批准，绑定 payloadDigest；缺批准则拒绝并审计） | TL、代码责任人 | **true** | 05§5.8.9/5.8.13-5；05§5.11.5 automation.push |
| `automation.create_pr` | 自动化测试开发 | 创建外部 PR（EXTERNAL_WRITE 族；批准对象含 repo/分支/变更摘要，变化即失效） | TL、代码责任人 | **true** | 05§5.8.9/5.8.13-5；05§5.11.5 automation.create_pr |
| `locator.publish` | 自动化测试开发 | 写入正式 LocatorVersion（自愈候选带证据进 ReviewTask；正式资产变更走 Diff+人工审核） | TE、TL | **true** | 05§5.11.5（支撑资产）；PRD13 Locator/AC-03 |

### 3.6 测试执行（5 键）

| 能力键 | 模块 | 中文描述 | 适用角色模板 | humanOnly | 对应能力点 |
|---|---|---|---|---|---|
| `execution_plan.approve` | 测试执行 | 批准 ExecutionPlanVersion（非八类产出物，但正式执行前必须批准；冻结精确资产/环境/契约版本） | TL、TE（按策略） | **true** | 05§5.11.5 execution_plan.approve；05§5.11.6 注；PRD14 执行计划 |
| `execution.start` | 测试执行 | 触发测试执行（环境、Runner、Secret 及计划版本均授权；手工/计划触发，V2 支持 Webhook/Pipeline） | TE、TL | false | 34§4.2 触发测试执行；05§5.11.5 execution.start；PRD14 触发 |
| `execution.stop` | 测试执行 | 取消/暂停执行任务（USER_PAUSED 语义；尽力终止并记录实际状态） | TE、TL | false | 05§5.11.5 execution.stop；PRD14 执行任务/异常 |
| `execution.retry` | 测试执行 | 重跑（V1 默认一次受控重试；新 attempt 不覆盖旧结果） | TE、TL；系统自动（受控） | false | 05§5.11.5 execution.retry；PRD14 AC-03 |
| `execution.evidence_sensitive_read` | 测试执行 | 读取敏感执行证据（脱敏后索引；敏感证据访问受限，数据分级标准待定，见 §4.3-6） | TL、TE（条件化）、VA（授权范围） | false | PRD14 证据 |

### 3.7 质量分析与缺陷（7 键）

| 能力键 | 模块 | 中文描述 | 适用角色模板 | humanOnly | 对应能力点 |
|---|---|---|---|---|---|
| `analysis.approve` | 质量分析与缺陷 | 批准 ResultAnalysis（事实与推断分离检查；高严重度结论需 TL 能力） | TE、TL | **true** | 05§5.11.5 analysis.approve；05§5.11.6；PRD15 结果分析 |
| `defect.approve` | 质量分析与缺陷 | 批准 DefectVersion（精确版本+摘要；严重/安全缺陷 FOUR_EYES；内部批准≠外部已写入） | TE、TL | **true** | 05§5.11.5 defect.approve；05§5.9.6；PRD15 Defect |
| `defect.verify` | 质量分析与缺陷 | 验证/关闭缺陷（需证据；重复关系人工确认；CLOSED→OPEN 留状态事件） | TE、TL | **true** | 05§5.11.5 defect.verify；05§5.9.3/5.9.9；PRD15 Defect |
| `defect.external_write` | 质量分析与缺陷 | 批准外部缺陷写入（EXTERNAL_WRITE：provider+integrationId+operation+defectVersionId+payloadDigest 逐次即时批准，任一变化即失效） | TL、TE（获授权） | **true** | 34§4.2 批准外部 Defect 写入；05§5.11.5 defect.external_write；05§5.9.8；PRD15 AC-02 |
| `report.signoff` | 质量分析与缺陷 | 签署 TestReport（REPORT_SIGNOFF：数据快照未陈旧+范围/执行快照固定；签署后内容不可变，更正出新版本） | TL（或等效签署人） | **true** | 34§4.2 签署 TestReport；05§5.6.4 REPORT_SIGNOFF；05§5.11.5 report.signoff；PRD15 报告 |
| `quality_gate.override` | 质量分析与缺陷 | 质量门禁放行/豁免（独立能力、理由、时限、指定 Release/环境、补偿措施并进报告；不可被 AI 建议触发） | TL（+WA 配置面分离） | **true** | 34§4.2 质量门禁放行/豁免；05§5.11.5 quality_gate.override；05§5.11.8；PRD15 质量门禁 |
| `coverage_report.approve` | 质量分析与缺陷 | 批准 CoverageReport 分母口径与报告结论（执行覆盖率正式产出物，裁决 B2-1；未检查/不可判定不得计为通过） | TL、TE | **true** | PRD15 覆盖率/AC-03；PRD14 AC-05；裁决 B2-1/B2-2 |

### 3.8 AI Agent 中心（8 键）

| 能力键 | 模块 | 中文描述 | 适用角色模板 | humanOnly | 对应能力点 |
|---|---|---|---|---|---|
| `skill.publish` | AI Agent 中心 | 发布/升级可执行 Skill（代码与安全 Review+Eval+治理复核通过；稳定根/版本/输入输出契约） | 治理责任人（自定义）、TA/WA | **true** | 34§4.2 发布 Skill/Agent/Workflow；05§5.11.5 skill 族；PRD16 Skill |
| `skill.install` | AI Agent 中心 | Workspace 启用/停用 Skill（WorkspaceSkillEnablement；授权仍受平台 RBAC） | WA、TL | false | 05§5.11.5 skill.install/activate；PRD16 Skill；05§5.12.8 |
| `skill.grant_network` | AI Agent 中心 | 为 Skill 授予网络访问（HIGH/CRITICAL 与权限变化采用 FOUR_EYES；默认 deny-all） | TA/WA、治理责任人 | **true** | 05§5.11.5 skill.grant_network；05§5.8.10-2；PRD16 权限模型 |
| `skill.grant_secret` | AI Agent 中心 | 为 Skill 授权 Secret 引用（明文不进入 Agent 上下文；FOUR_EYES；可撤销） | TA/WA、治理责任人 | **true** | 05§5.11.5 skill.grant_secret；05§5.8.10-2；PRD16 权限模型 |
| `agent.publish` | AI Agent 中心 | 发布 Agent/能力扩大（目标、职责、allowedSkills、委派深度与预算经治理审核） | 治理责任人、TA | **true** | 34§4.2 发布 Skill/Agent/Workflow；05§5.11.5 agent.publish；PRD16 Agent |
| `agent.grant_permission` | AI Agent 中心 | 高风险 Agent 权限扩大（原 TestLead 可改 Agent 权限的收窄：需管理员+四眼策略；不得自授超委派上限） | TA/WA（复核链） | **true** | 05§5.11.5 agent.grant_permission；05§5.11.11；05§5.11.8 |
| `workflow.publish` | AI Agent 中心 | 发布 AgentWorkflow（DAG 结构、节点权限与业务 Eval 发布前审核；human checkpoints 不可移除） | 治理责任人、TL | **true** | 34§4.2 发布 Skill/Agent/Workflow；05§5.11.5（Agent/Workflow 族）；PRD16 Workflow |
| `eval.approve` | AI Agent 中心 | 决定 Eval 准入/回滚并形成版本化校准记录（无有效校准记录时分数只排序、不驱动自治，裁决 B2-3） | 治理责任人、TL | **true** | PRD16 Eval/AC-04；裁决 B2-3 |

### 3.9 平台管理（10 键）

| 能力键 | 模块 | 中文描述 | 适用角色模板 | humanOnly | 对应能力点 |
|---|---|---|---|---|---|
| `workspace.manage` | 平台管理 | Workspace 生命周期、成员与归档（V1 试点含 Environment/Release 身份管理；归档校验未完成工作与报告） | WA（PA/TA 平台侧） | false | 05§5.11.5 workspace.manage_members；PRD17 Tenant/Workspace/Release |
| `integration.manage` | 平台管理 | 集成配置管理（端点/凭据引用/出站 allowlist/作用域；不保存连接串明文） | TA、WA | false | 05§5.11.5 integration.manage；PRD17 Integration；34§8 |
| `integration.external_write` | 平台管理 | 通用外部写入批准（EXTERNAL_WRITE 通用能力；目标域名/操作类型/Workspace/Release 受限；幂等键+审核+负载摘要；defect.external_write、automation.push 为其具体实例） | TL、获授权责任人 | **true** | 34§4.2/§8 外部集成；05§5.6.4 EXTERNAL_WRITE；05§5.11.5 defect.external_write 族 |
| `secret.manage` | 平台管理 | Secret 创建/轮换/吊销/授权引用（只允许引用使用，UI/API 不返回明文；每次高价值操作记 AuthorizationDecision） | TA、WA | **true** | 05§5.11.5 secret.manage；05§5.11.8；34§8；PRD17 Secret |
| `secret.grant_use` | 平台管理 | 授权执行服务/集成按 secretRef 使用 Secret（B3"Secret 读取"人类控制意图的落地键；授权可撤销、过期） | TA、WA | **true** | 34§8 Secret 与集成安全；PRD17 Secret |
| `secret.read_plaintext` | 平台管理 | 读取 Secret 明文（humanOnly=否，**原则上禁止**：仅受控执行服务短时解密，用户与 Agent 不直接读取；与 B3 表述差异见 §4.3-2） | 无（受控执行服务，机器专属） | false（默认 DENY） | 34§4.2 读取 Secret 明文；34§8；PRD17 AC-03 |
| `rbac.manage` | 平台管理 | 管理 RoleDefinition/RoleBinding/ExplicitDeny/Delegation 上限（版本化+审计；不得给自己授予超出委派上限的能力） | PA、TA（TA 自授高风险能力需另一名 TA 复核） | **true** | 34§4.2 管理 RoleBinding/ReviewPolicy；05§5.11.5 tenant.manage_roles；05§5.11.8；PRD17 RBAC |
| `review_policy.manage` | 平台管理 | 管理 ReviewPolicy（阶段/人数/能力/职责分离/blockingChecks；平台最低要求只能调严；放宽需产品级变更） | PA、TA（受平台底线约束） | **true** | 34§4.2 管理 RoleBinding/ReviewPolicy；05§5.11.4/5.11.7；PRD17 ReviewPolicy |
| `audit.read` | 平台管理 | 只读访问审计日志与 AuthorizationDecision（只追加、脱敏、访问受限） | VA、TA/PA（各自范围） | false | 05§5.11.5 audit.read；34§9；PRD17 审计 |
| `support_access.grant` | 平台管理 | 支持访问授权（SupportAccessGrant：指定 Tenant/Workspace、工单、理由、能力、最长有效期、审批人；默认只读；break-glass 不得伪造业务批准；Agent 无权发起） | PA（审批人）、TA（配合） | **true** | 05§5.11.8 紧急访问；05§5.12.9 SupportAccessGrant；PRD17 支持访问 |
| `delegation.grant` | 平台管理 | 人类临时委派（DelegationGrant：委托人、受托人、能力、作用域、有效期、原因、默认不可再委托；不适用于 AI 批准） | TA、WA（按委派上限） | **true** | 05§5.11.4 DelegationGrant；05§5.12.9；PRD17 支持访问 |

## 4. 未覆盖项与未核实项

### 4.1 未覆盖（延后/建议不建键）

| 项 | 建议 | 理由 |
|---|---|---|
| `artifact.archive`（含 workitem 归档） | 建议 V1 补齐或并入各实体废弃规则 | 05§5.11.5 能力族含 archive；05§5.6.7-7 废弃≠删除，需引用检查与归档语义；34 §9 归档动作要审计 |
| `automation.check_run` | 建议不建权限键 | 确定性检查由系统自动执行（13-PRD），检查 PASS 不替代人工批准；不属于权限点 |
| `mock.publish` / `test_data.publish` / `visual_baseline.publish` | V1 不独立建键，随所属正式产出物或专项 WorkItem 审核 | 05§5.6.1：支撑资产"默认随所属正式产出物或专项 WorkItem 接受审核，不强制为每个细粒度对象单独创建一级审核流程"；如 V2 出现独立高风险配置再拆分 |
| `secret.read_metadata` | 建议不单独建键 | 元数据查看随 artifact.read / 环境-引用视图承载（17-PRD AC-03：只能看到引用和元数据）；如需独立管控由 B4 定 |
| `prompt.publish` / `agent.configure` / `agent.run` / `skill.activate` | 延后到 V2 细化 | 16-PRD：Prompt"版本发布及高风险变更审核"目前可由 workflow.publish 治理链承载；普通配置（agent.configure）与运行（agent.run）随 workitem.run+节点权限表达，V1 不单独建键 |
| `tenant.manage` / `release.manage` / `environment.manage` / `llm.manage` / `runner_node.register` | V1 暂缓，由 workspace.manage 与平台内部运维承载 | 05§5.13.3：V1 为单租户试点，多租户生命周期（V3）、LLM 路由与 Runner 注册属平台内部运维面；多租户落地时按 05§5.11.5 tenant/integration/secret 族拆分 |
| `failure_cluster.resolve` | 建议 V2 建键或并入 defect.approve 决策 | 15-PRD：Cluster 不是 Defect，人工决定是否建 Defect——该决策由 defect.approve 承载；聚类拆并属维护操作，V1 不强制独立键 |
| `knowledge.candidate_resolve` | 建议并入 knowledge.publish（发布/拒绝即治理决策） | 11-PRD 候选治理：人工决定合并/发布/拒绝；拒绝语义可由 publish 键+审计表达，独立键留待 V2 |
| `quality_gate.manage`（规则变更，非豁免） | 建议与 `quality_gate.override` 分列并由 B4 确认 | 15-PRD：门禁规则变更、放行/阻断豁免均"由人决定"；本草案只落 override，规则变更管理建议 V1 补 `quality_gate.manage`（true） |
| `pipeline.trigger` / `pipeline.manage` | V2 建键 | 15-PRD：交付集成（流水线）为 V2 能力；外部写入与触发范围受授权，落地时按 EXTERNAL_WRITE 族处理 |
| `automation.publish` 类"批准后系统执行"键 | 保持 false 语义即可 | 与 05§5.11.9"人工批准后由应用服务执行发布，审计同时记录批准人和执行服务身份"一致 |

### 4.2 未核实项（需 B4/产品裁决）

1. **冒号 vs 点号命名冲突**：05 §5.5.10 使用 `workitem:create`（冒号），§5.11.5 使用 `defect.external_write`、`work_item.create`（点号）。本目录统一采用点号（以 §5.11.5 为新权威）；需裁决废弃 §5.5.10 冒号写法并同步 32/33/34 附录。
2. **Secret 读取的 humanOnly 冲突**：B3 要求 humanOnly 至少覆盖"Secret 读取"；但 34 §4.2 明确"读取 Secret 明文 humanOnly=否、原则上禁止，仅受控执行服务短时解密"。本目录落地为 `secret.read_plaintext`（机器专属、默认 DENY）+ `secret.grant_use`（人工授权引用，true）；若 B3 原意是"Secret 的读取授权必须人工批准"，则 `secret.grant_use` 已覆盖；若原意是"人类可读明文"，则与 34 安全原则冲突，建议维持 34 口径。
3. **review 类键粒度**：本目录以 `artifact.review`（决策，true）作为 REVIEW 通过/拒绝的统一键；05§5.11.5 中 `api_contract.review`、`test_case.review` 等是否需独立成键（作为 ReviewPolicy.requiredCapabilities 精确引用）未定，建议 B4 裁决"通用 review + 专属 approve"或"逐资源 review/approve 全列"两种口径。
4. **`workitem.force_transition` 语义边界**：05§5.5.10 `workitem:admin` 含"修改策略、强制解锁、处理异常状态"，范围过宽；本目录收窄为强制流转/异常处置，"修改策略"归 `rbac.manage`/`review_policy.manage`，需确认。
5. **`workitem.assign` 是否允许 Agent 代执行**：05§5.5.10 未禁止 Agent 分派；本目录按 false 处理并建议加条件（仅限 Workflow 节点权限内、由 TL 发起），需确认。
6. **敏感证据分级标准缺失**：`execution.evidence_sensitive_read` 依赖数据分级/脱敏规则，PRD/34 均未定义分级标准；V1 建议先以"脱敏+权限引用"实现，分级标准延后。
7. **`skill.install` 的 scopeTypes**：WorkspaceSkillEnablement 的授权边界（WORKSPACE vs TENANT）未明确；需随 16-PRD V2 细化。
8. **CoverageReport 的 humanOnly 强制**：CoverageReport 不属于八类正式产出物，但 15-PRD 要求人工批准分母口径与结论；是否写入 ReviewPolicy 强制"至少一名人类批准"需确认（本目录暂按 true）。
9. **`delegation.grant` / `support_access.grant` 审批链**：34 未定义"谁批准授权者"的复核链（05§5.11.8 仅对 TA 自授提出复核要求）；建议补充四眼或上级审批链规则。
10. **`quality_gate.manage` 缺失确认**：见 §4.1，需 B4 定是否与 override 分列。
11. **05 §5.5.12-8 引用口径**：任务输入将"权限能力点"表述为 §5.5.12-8；经核对，05 中权限能力点为 §5.5.10（workitem:xx 能力点表），§5.5.12 为 Given/When/Then 验收基线、§5.8 为自动化代码契约。本目录以 §5.5.10 + §5.11.5 为映射源，特此说明。

### 4.3 后续动作建议

- 由 B4 评审本清单（重点：§4.2-1/2/3 三处命名与语义冲突）；
- 评审通过后落为 `docs/04-architecture/34a-能力键目录.md`（受控文档）或在 34 号新增附录，并同步 32-API 规范、33-数据库（permission 表 seed）与 38-种子数据约定；
- 与 05 §5.5.10 冒号写法建立迁移映射（旧 `workitem:xx` → 新 `workitem.xx`），Gate E/F 静态复审时校验无旧写法残留。
