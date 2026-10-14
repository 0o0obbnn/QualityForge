# 55-Agent 与 Skill 运行治理 SOP

> 状态：现行Gate 0治理基线 + V1目标治理补充（待运行时激活）
> 适用范围：需求资料 → Testing IR → 测试策略 → 测试计划 → 场景 → 用例 → 断言 → Coverage → 人工评审  
> 不适用范围：生产环境自治、自动发布、完整 Skill 市场、分布式 Multi-Agent 平台  
> 机器可读配置：Gate 0见[`agents.json`](../../prototypes/agent-governance/agents.json)与[`gate0-workflow.json`](../../prototypes/agent-governance/gate0-workflow.json)；独立评审平面见[`platform-review-agent.json`](../../prototypes/agent-governance/platform-review-agent.json)与[`platform-review-workflow.json`](../../prototypes/agent-governance/platform-review-workflow.json)

## 1. 目的与裁决

QualityForge 当前采用“**1 个监督者 + 3 个受限 Subagent + 14 个 Gate 0 Skill**”的最小治理模型。Skill 是可复用的原子能力或确定性门禁，Agent 是受权限约束的职责承担者，Workflow 是固定的调用拓扑；三者不得混为一谈，也不按一项 Skill 配一个 Agent。

在Gate 0生产治理之外，另设“**1个外部独立平台评审Agent**”。它不是第4个Subagent，不进入生产委派DAG，不参与被审平台的资产生成或整改，仅对冻结快照形成咨询性评审报告。两套角色的统计、权限和运行目录必须分开，不能把“4个Gate 0 Agent”改写为“5个协作Agent”。

本阶段按21号矩阵的L2受限代理模式运行：Subagent只允许读取权威资料、在单次运行目录形成草稿、调用allowlist内Skill、输出可审计裁决。任何AI均无权批准自己的结果、修改正式权威源、发布Skill、写外部系统或控制发布门禁；正式动作必须由UserIdentity经应用服务执行并产生AuthorizationDecision。

## 2. 真相源层级

发生冲突时按以下顺序裁决：

1. 术语、实体、API、DB 与 AI 自治仍分别以 `03`、`04`、`32`、`33`、`21` 号权威源为准。
2. 单个 Skill 的行为、输入输出和 Must Not 以对应 `prototypes/skills/<skill-id>/SKILL.md` 为准。
3. Gate 0 Agent职责、Skill allowlist和权限以`agents.json`为准；平台独立评审边界以`platform-review-agent.json`为准。
4. Gate 0拓扑以`gate0-workflow.json`为准；平台评审拓扑以`platform-review-workflow.json`为准，两者不得互相委派。
5. 本文件规定运行、审批、异常处理和变更 SOP。
6. 宿主工具（Codex、ZCode、WorkBuddy 等）的配置只是适配副本，不得反向覆盖上述项目真相源。

Skill 被宿主发现、安装或显示，不等于已完成调用验证；静态 checker PASS 也不等于平台运行、人工验收或正式资产发布成功。

## 3. 角色与职责分离

| Agent | 职责 | Skill allowlist | 禁止事项 |
|---|---|---|---|
| `qf-supervisor` | 分类、结构预检、派发、终止、汇总 | 无业务Skill；使用治理结构验证器 | 不生成业务资产、不审批、不发布 |
| `qf-requirement-ir` | 需求评审包和 IR 草稿 | 需求质量、规则、领域、状态、编译 5 个 Skill | 不改原始需求、不批准自己的 IR |
| `qf-test-design` | 策略、计划、场景、用例、候选断言草稿 | 策略校验、计划编排、场景、用例、断言5个Skill | 不执行测试、不修改已验证IR |
| `qf-independent-verifier` | 独立验证和人工路由 | IR、断言、Coverage、HITL 4 个 Skill | 不修复被审资产、不代替人工批准 |

只有 Supervisor 可以派发 Subagent，最大委派深度为 1；Subagent 不得继续创建下级 Agent。生成者和验证者必须使用不同角色配置，不能通过切换提示词假装完成独立复核。

### 3.1 独立平台评审平面

| Agent | 评审范围 | 可复用Skill | 禁止事项 |
|---|---|---|---|
| `qf-platform-reviewer` | 产品、需求、架构、契约、安全、AI治理、可测试性、体验、验收证据 | `quality-governance`、`contract-drift-detector`，仅限只读适用输入 | 不接受生产派工、不调度生产Agent、不改文档/代码/测试/证据、不整改或关闭Finding、不批准 |

该Agent只能由授权UserIdentity或经批准的只读计划发起。输入必须是带`sourcePaths`、`sourceDigests`、`exclusions`和时间戳的冻结快照；同一快照重评也创建新的`reviewRunId`。Finding必须区分`CONFIRMED/INFERRED/UNRESOLVED`，包含精确证据、影响、建议、验收标准和限制。它的PASS或`READY_WITH_LIMITATIONS`都不是平台验收，人类必须决定接受报告、要求整改或驳回报告。

### 3.2 V1协作与评估角色（目标）

V1在Gate 0角色之上引入三类产品责任：协调Agent负责对话、澄清、TaskCard/AgentPlan和委派；专业Agent只在TaskContract范围内生产/执行；评估Agent只读冻结产出并按Rubric出具评估。生产与评估必须使用独立Session、独立权限和不可变输入摘要。此模型的目标契约见39号，不改写当前Gate 0已验证事实。

运行前必须依次完成：资料完整性/冲突检查 → 澄清闭环 → TaskCard/AgentPlan人工确认 → 权限/数据安全/预算预检 → 锁定TaskContract。运行中暂停、继续、取消、重试和调整范围均须创建RunCommand并取得CommandReceipt，不得以前端本地状态冒充执行控制。

## 4. 最小权限基线

### 4.1 文件系统

- 可读：现行文档、Skill 原型、E2E 正反样例和本治理配置。
- 可写：`prototypes/agent-governance/runs/{runId}/` 对应的单次运行目录。
- 平台评审仅可写：`prototypes/agent-governance/platform-review-runs/{reviewRunId}/`；不得复用生产运行目录。
- 禁写：`docs/**`、`prototypes/skills/**`、`prototypes/e2e-validation*/**`。
- 从运行草稿提升为正式资产必须创建绑定`artifactType + artifactId + artifactVersionId + contentDigest`的ReviewTask，由满足ReviewPolicy、作用域能力和职责分离的人类审批，再由应用服务执行；Agent本身不直接写权威源。

### 4.2 网络、外部系统与 Secret

- 默认 `deny_all`，无网络白名单。
- 默认不注入任何 Secret，不持久化、不记录 Secret 值。
- Defect管理平台、CI/CD、代码仓库、被测系统和外部LLM均属于额外授权范围；本Gate 0原型不自动访问。
- 未来开放单次访问时必须同时声明目标 allowlist、用途、过期时间、Secret 键名和人工审批记录。
- 禁止 Agent 将输入、输出、日志或异常堆栈中的敏感数据带出工作空间。

### 4.3 运行预算

- 同参失败最多重试 1 次。
- 默认单次 Agent 超时 600 秒、最大 12 步。
- 工作流遇到 `REJECT`、`ERROR`、`TIMEOUT` 必须停止并保留证据。
- 相同 Skill 与相同输入不得循环调用；检测到循环时由 Supervisor 终止。

## 5. Skill 触发协议

Skill 只有在以下条件全部满足时才能触发：

1. 用户目标落入当前 Workflow 范围；
2. 前置节点已完成并产生规定产物；
3. 输入满足对应 `SKILL.md` 和 Schema；
4. 调用 Agent 的 `allowedSkills` 包含该 Skill；
5. 使用的 Skill 版本和评测入口可追踪；
6. 权限、网络、Secret、预算和人工检查点均满足；
7. 没有命中 `DO NOT`、强制人工检查点或降级条件。

Skill 的 `description` 只用于发现候选能力，不构成授权。模型不得根据自然语言相似度绕过 allowlist，也不得调用 PRD 示例中存在但尚未注册的 `git-reader`、`log-analyzer`、`execution-log-fetcher`。

对只负责验证的 Skill，上游 Agent 应先形成候选结构化产物，再调用 Skill 进行裁决；不得要求验证器代替生成器补齐或修复输入。

## 6. Gate 0 标准流程

```text
Supervisor: governance-structure-validator 结构预检
  ↓ PASS
Requirement & IR: requirement-quality-gate
  ↓ PASS
Requirement & IR: business-rule / domain-model / state-machine（可并行）
  ↓ 全部完成
Requirement & IR: requirement-compiler
  ↓
Independent Verification: ir-validator
  ↓ PASS
Test Design: strategy → test-plan → scenario → test-case → assertion-generator
  ↓
Independent Verification: assertion-verifier → coverage-analyzer → hitl-gatekeeper
  ↓
人工决定批准、驳回或修改
```

工作流中的 `PASS` 只允许进入下一节点；`REJECT` 停止；`BLOCK_HUMAN` 创建 ReviewTask 并暂停；`ERROR/TIMEOUT` 停止并保存现场。任何节点都不能把“HTTP 成功”“文件已生成”“模型自评通过”解释为下游 Gate PASS。

## 7. 运行 SOP

### 7.1 受理与建档

Supervisor 创建唯一 `runId`，保存原始目标、调用人、工作空间、输入资料清单、敏感级别、禁止动作和期望产物。缺少输入或目标超出 Gate 0 时停止并请求补充，不静默扩大范围。

### 7.2 权威源锁定

记录本次运行使用的术语、领域、AI 治理、API、DB、Skill 和 Workflow 版本或内容哈希。运行过程中权威源发生变化时，本次运行不得混用新旧版本，应终止或从受影响节点重放。

### 7.3 预检

执行以下检查：

- Agent 与 Skill 均存在且处于允许范围；
- Workflow 是 DAG，所有依赖存在；
- 输入 Schema、来源溯源和必要前置状态完整；
- 文件、网络、Secret、预算和用户 RBAC 满足；
- 强制人工检查点已声明。

### 7.4 执行与留痕

每个节点至少记录 `runId`、`nodeId`、Agent、Skill、Skill 版本、输入/输出哈希、开始/结束时间、裁决、Finding Code、降级原因和后续路由。不得记录隐藏思维链；只记录可审计的决策摘要、证据引用、Tool 调用及其输入输出，且必须脱敏。

### 7.5 独立验证

- `qf-independent-verifier` 读取生成产物的不可变快照。
- 只执行验证、覆盖率和路由，不修改快照。
- checker 未运行、异常退出或输入不完整时按未通过处理，不允许模型补写一个 PASS。
- 被驳回的产物返回原生成角色创建新版本，再重新验证；不得覆盖原失败证据。

### 7.6 人工审批与发布

AI输出的`PASS`不是人的批准。以下动作必须由具备相应作用域能力、满足ReviewPolicy和职责分离的人类确认：

- TestStrategy、TestPlan和TestCase正式版本批准；
- DesignTestCase → TestCase正式入库；
- 修改 Testing IR、业务规则、断言或权威契约；
- 发布或升级可执行 Skill；
- 写外部Defect系统、CI/CD、代码仓库、被测系统或生产邻近环境；
- 放行发布门禁；
- 任何关键路径、来源冲突或强制 `BLOCK_HUMAN`。

人工审批记录必须包含审批人、身份类型、作用域、能力、ReviewPolicy版本、时间、决议、备注、`artifactId`、`artifactVersionId`、`contentDigest`和最终发布版本。PlatformAdmin、TenantAdmin或WorkspaceAdmin身份本身不自动构成业务批准能力；Approver是ReviewTask职责而不是全局角色。

### 7.7 异常、取消与重放

- 用户可随时取消；Supervisor 停止未开始节点并保留已完成产物。
- 超时、循环、越权、Schema 错误和 checker 异常均 fail-closed。
- 重放必须创建新 `runId` 或新 attempt，引用原失败运行，不覆盖原记录。
- 越权尝试、Secret 暴露或异常外联按安全事件处理，立即中止并通知管理员。

### 7.8 运行后复盘

至少统计路由正确率、REJECT/BLOCK 分布、人工修改率、误放/误阻、Skill 错误率、超时、成本和越权尝试。没有真实 Golden Set 和人工标注前，不得用“执行成功率”替代业务正确率。

## 8. 宿主适配规则

Codex、ZCode、WorkBuddy 或其他宿主只负责把项目真相源转换成各自支持的 Agent/Skill 配置：

- 适配器必须保留 Agent ID、Skill allowlist、禁止动作和人工审批边界；
- 宿主不支持某项硬权限时，该 Agent 不得获得对应能力，不能只靠 Prompt 声明“请勿使用”；
- 复制或安装后必须执行发现检查和一次真实调用；
- 宿主侧配置漂移时，以项目配置重新生成，不手工双向维护。

## 9. Given/When/Then 验收标准

### AC-01 未授权 Skill 被阻断

- **Given** `qf-test-design` 的 allowlist 不含 `ir-validator`；
- **When** 它尝试调用 `ir-validator`；
- **Then** 运行在调用前以权限错误终止，Skill 不执行，并记录 Agent、Skill 和 `runId`。

### AC-02 生成者不能批准自己的产物

- **Given** `qf-requirement-ir` 生成了 IR 草稿；
- **When** 它尝试将草稿标记为人工批准或正式发布；
- **Then** 操作被拒绝，草稿保持未发布状态，必须交给独立验证和人工审批。

### AC-03 网络与 Secret 默认拒绝

- **Given** Gate 0 默认策略没有网络目标和 Secret 键；
- **When** 任一 Agent 请求外联或 Secret；
- **Then** 请求在执行前被拒绝，日志不得包含 Secret 值。

### AC-04 Workflow 可执行

- **Given** 当前 `agents.json`、`gate0-workflow.json` 和 30 个 Skill 目录；
- **When** 执行 `python3 prototypes/agent-governance/validate.py`；
- **Then** 返回码为0，并确认4个Agent、14个Gate 0 Skill、无环依赖、默认零网络、无Secret、正式批准humanOnly、审核绑定精确版本与摘要。

### AC-05 非 PASS 不得前进

- **Given** 任一节点返回 `REJECT`、`ERROR` 或 `TIMEOUT`；
- **When** Supervisor 计算下一步；
- **Then** 后续业务节点均不启动，当前证据被保留；`BLOCK_HUMAN` 只能进入人工评审暂停态。

### AC-06 平台评审隔离可验证

- **Given** 当前4个Gate 0 Agent和`qf-platform-reviewer`配置；
- **When** 执行治理验证器；
- **Then** 验证器确认评审Agent不在Gate 0注册表和委派图中、零网络/Secret/外部写入、只能写独立评审目录、不能整改或自行处置，最终报告必须进入人工处置节点。

## 10. 变更规则

- 新增或删除 Skill：先修改对应 `SKILL.md`，再调整 Agent allowlist、Workflow、eval 和本 SOP 引用。
- 新增 Agent：必须证明现有角色无法通过权限收窄承担职责，并补独立权限与路由评测。
- 放宽网络、Secret、正式资产写入或委派深度：视为安全关键变更，必须人工评审。
- 修改 AI 自治或阈值：只在 `21-AI介入点降级矩阵.md` 裁决，本文件引用，不另立数值。
- 每次治理配置变更后必须运行 `validate.py`；验证通过只证明结构一致，不证明真实业务正确。

## 11. 当前实施状态与边界

截至2026-08-12，Stage 4本地运行时已用SQLite持久化`gate0-planning-slice.json`对应的最短闭环。`deterministic-local` Provider不读取模型Secret；产物先进入`PENDING_REVIEW`，Agent JWT不能批准，全部ReviewTask由具备产物级能力的UserIdentity批准后才完成WorkItem。浏览器E2E已验证服务重启后四项审核状态仍存在且最终Session=`COMPLETED`。

30/30 Skill均有标准`evals/evals.json`，统一入口共发现103个eval case并运行14个确定性runner。该结果证明目录、Schema与已接入确定性runner可回归，不证明30个Skill都完成真实模型效果评测。

当前SQLite方案面向单机本地验证：租户/Workspace隔离由服务层强制并有负向测试，但没有PostgreSQL原生RLS；本地HS256签名密钥每次启动随机生成，重启需重新登录，不等于OIDC/生产认证。当前也没有消息队列、分布式Runner、真实模型适配、宿主专用插件或自动发布。下一阶段应先补正式产出物的“人工批改→新版本→复核”闭环，再决定何时以目标PostgreSQL与企业身份替换本地Profile。

2026-08-27回填的Conversation、Clarification、TaskContract、RunCommand和EvaluationRun仍属`CONTRACT_PENDING/IMPLEMENTATION_PENDING`；未经32/33/36激活与E2E验证，不得写入“已实施”口径。
