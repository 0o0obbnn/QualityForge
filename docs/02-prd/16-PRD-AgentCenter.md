# 16-PRD-AI Agent中心

## 1. 目标与边界

统一管理Skill、Agent、Prompt、Workflow、Session、Trace、Eval和AI运行策略，使AI可控、可审计、可降级、可持续改进。Skill是原子能力；Agent是职责/权限边界；Workflow是固定或版本化DAG，三者不得合并。

本模块不拥有业务产出物正文，也不代替任务看板、ReviewTask或业务模块发布服务。

## 2. 功能需求

| 能力 | 需求 | 人工控制 |
|---|---|---|
| Skill | 稳定根/版本、输入输出契约、实现引用、风险、依赖、权限和eval | 发布/升级可执行Skill需代码与安全Review |
| Agent | 目标、职责、allowedSkills、工具/文件/网络/Secret、委派深度和预算 | 能力扩大需治理审核 |
| Prompt | 不可变版本、模型/模板/摘要和适用范围 | 版本发布及高风险变更审核 |
| Workflow | DAG、节点Agent/Skill、输入输出、权限、重试、降级和human checkpoints | 发布前结构、权限和业务Eval |
| Session/Trace | 发起人、WorkItem、版本快照、授权决定、节点/tool调用、输入输出摘要、成本 | 敏感字段脱敏；不记录隐藏思维链 |
| Eval | Golden Set、数据集版本、目标版本、指标、结果、人工基线和适用性 | 决定准入、回滚并形成版本化校准记录。校准记录按 21 号 §4 落 t_calibration_record；无有效校准记录时分数只排序、不驱动自治（裁决 B2-3，2026-08-14；校准记录 V1 即承担自治判定底座，非 V2 增强，裁决 2026-08-15 B15） |
| 运行控制 | 暂停、取消、预算、循环检测、熔断和L0-L3降级（等级定义与默认级别以 21 号 AI介入点降级矩阵为唯一权威源，裁决 2026-08-14 批次二） | 人工可随时接管；正式审核不可跳过 |
| 独立平台评审 | 在生产Agent委派图之外按冻结快照评审产品、需求、架构、契约、安全、AI治理、可测试性、体验和验收证据 | 只输出咨询性Finding；人工处置，评审Agent不得建设、整改或关闭Finding |
| 协调Agent | 维护Conversation，识别资料缺口，发起Clarification，生成TaskCard/AgentPlan，委派专业Agent | 人工确认范围、计划、预算与高风险检查点 |
| 专业Agent | 在锁定TaskContract与权限交集中生成、检查或执行特定任务 | 越范围、越预算或高风险动作一律停止/澄清 |
| 评估Agent | 使用冻结输入和版本化Rubric独立评估产出物，输出分维度得分、阻断项和证据 | 不参与生成或修复被评产出物；评分不代替人工批准 |
| 对话与命令 | Conversation/Message、Clarification、TaskContract、RunCommand/Receipt | 命令由REST受权与幂等处理；WebSocket只推送状态和回执 |

## 3. 权限模型

Agent最终权限=发起人当前RBAC∩AgentVersion权限∩Workflow节点权限∩WorkItem/环境/集成策略−显式Deny−humanOnly。任一层缺失即拒绝。

默认：网络deny-all、Secret空、外部写入deny、正式资产写入/批准deny、Subagent委派深度受限。Agent不得以用户拥有的批准权代表用户作ReviewDecision。

## 4. Gate 0基线

当前原型为1个Supervisor+3个受限Subagent、14个Gate 0 Skill，覆盖需求→TestingIR→策略→计划→用例→Coverage→人工审核包。它是V0局部链，不代表V1完整Agent平台。

另设1个`qf-platform-reviewer`，独立于上述Gate 0生产链：它不在`agents.json`和Supervisor委派列表内，不接受生产Agent派工，也不能反向调度生产Agent。其机器可读权限与只读评审流程分别见`prototypes/agent-governance/platform-review-agent.json`与`prototypes/agent-governance/platform-review-workflow.json`（完整路径，裁决 2026-08-14 批次二）。独立评审的目的不是增加一个“更高权限Agent”，而是用更窄权限建立对平台本身的第二视角。

## 5. 主流程

```text
用户对话 → 资料完整性检查/澄清 → 确认TaskCard + AgentPlan
→ WorkItem + TaskContract + 用户授权 → 锁定Agent/Skill/Prompt/Workflow/来源版本
→ 结构/权限预检 → 节点执行与Trace → 确定性检查/独立验证（`INDEPENDENT_VERIFY` 介入点，裁决 2026-08-14 批次二，见 21 号 §5：确定性检查+独立 verifier 裁决构成三层证据第二层，仅产出裁决与证据）
→ 到human checkpoint创建ReviewTask并暂停
→ 人工决定后由业务应用服务发布，Agent继续或结束
```

## 6. 异常与降级

- 未授权Skill/tool/网络/Secret：调用前拒绝并中止/降级。
- 循环、超时、预算超限：停止未开始节点，保存现场，WorkItem阻塞。
- 模型/Prompt/Skill/Workflow版本变化：原校准记录失效，回退L1并重评。
- 校准记录过期、评测跌破门槛、误放/误阻超警戒线：按 21 号 §6.1 降级触发，回退并重建校准（裁决 2026-08-14 批次二，对齐 21 号）。
- Trace缺失或checker异常：不得给PASS，不得进入正式审核的“可批准”状态。

## 7. 验收标准

### AC-07 独立验证行为契约（第0周补丁 B2，2026-08-14）

- **独立性定义**：verifier 与 producer 权限隔离（不同 Agent 会话、只读被审资产、不可反向调度生产 Agent）；同一 LLM 供应商可被使用，但 verifier 输出必须独立裁决、不接受 producer 自述结论。
- **裁决组合规则**：确定性检查（结构/绑定/摘要）全部通过 → verifier 裁决；确定性检查失败直接 FAIL，不进入 verifier。
- **失败流向**：FAIL → 对应 WorkItem 转 REWORK 并附裁决证据；REVIEW_REQUIRED → 创建 ReviewTask 走人工审核；ERROR（verifier 超时/不可用）→ 不产出裁决、不阻断人工审核，记录 ERROR 并告警。
- **超时处理**：verifier 超时上限 60s；超时后按 ERROR 处理，审核流程可继续（独立验证为增强非阻塞）。
- **三层证据呈现**：审核界面必须可区分展示 ①确定性检查证据 ②verifier 裁决 ③人工审核决定，三层不可合并展示。
- **Given** verifier 裁决 FAIL；**When** 生成独立验证结果；**Then** WorkItem 转 REWORK 且裁决证据只追加。



### AC-01 Skill与Agent不混同

- **Given** `coverage-analyzer`是Skill；
- **When** Workflow调用它；
- **Then** 由授权Agent执行并分别记录AgentVersion与SkillVersion，不创建同名Agent冒充独立职责。

### AC-02 权限取交集

- **Given** 用户有外部写权限但AgentVersion禁止；
- **When** Agent尝试同步Defect；
- **Then** 操作被拒绝并记录DENY，不因用户权限放行。

### AC-03 机器PASS不等于人工批准

- **Given** 所有Gate 0 checker通过；
- **When** human_gate到达；
- **Then** 创建绑定策略/计划/用例版本摘要的ReviewTask并`BLOCK_HUMAN`。

### AC-04 Eval版本可复现

- **Given** Agent变更Prompt；
- **When** 查看准入结果；
- **Then** 旧Eval只关联旧PromptVersion，新版本必须重新运行指定DatasetVersion。

### AC-05 平台评审与生产Agent隔离

- **Given** Gate 0 Supervisor或任一生产Subagent请求调用`qf-platform-reviewer`；
- **When** 运行时计算委派关系；
- **Then** 请求在执行前被拒绝，平台评审只能由授权UserIdentity或经批准的只读计划基于冻结快照发起。

### AC-06 评审Agent不能整改或自行结案

- **Given** `qf-platform-reviewer`发现一个P1 Finding；
- **When** 它尝试修改文档、源码、测试、证据或把Finding标记为已关闭；
- **Then** 写入和处置均被拒绝；它只能给出证据、影响、建议和验收标准，由人决定是否建立独立整改WorkItem。

## 8. 版本范围

V1实现协调Agent+受限专业Agent+独立评估Agent的最小协作链，以及Conversation、Clarification、TaskContract、完整运行命令、Trace、基础Eval和版本化校准记录。V2增强团队治理、复杂工作流与广泛集成；V3支持经评测的扩展代理与企业能力供应链。
## 8. 指标承接(裁决 2026-08-14;指标口径见 20 号 §1.1 受控 metricKey 登记表,覆盖率口径见 22 号附录 C)

| 指标 | 本模块角色 | 基线 | 测量方法 | 验收 |
|---|---|---|---|---|
| Golden Set 准确率/召回率(M-32/33) | 生产 | 黄金集建立后批准(22 §6) | EvalRun 对版本化 EvalDataset 的结果,绑定 target/dataset/environment | AC:只认 EvalRun 结果,模型自评分无效 |
| 越权率(M-35) | 生产 | 试点后批准 | Agent 请求被 DENY 次数/请求总数,AuthorizationDecision | AC:成功越权率独立监控期望为 0 |
| 误阻率(M-36) | 生产 | Golden Set 建立后批准 | 判拒绝但应通过样本/判拒绝总数 | AC:无人工标注不得报告;与误放率配对 |
| AI 草稿采用率(M-38) | 生产 | 试点后批准 | 四项合计 100%:直接/修改后/退回/废弃,分母=AI 提交审核版本数 | AC:采用≠正确,与误放率互补解读 |
| AI 任务成功率(M-39) | 生产 | 试点后批准 | SUCCEEDED/已结束 AI run 总数 | AC:任务成功率≠业务正确率,不得替代 M-32 |
| AI 超时率/重试/错误率(M-40/41/42) | 生产 | 试点后批准 | errorCode/attemptNo/SkillInvocation 统计 | AC:按介入点+模型版本分层 |
