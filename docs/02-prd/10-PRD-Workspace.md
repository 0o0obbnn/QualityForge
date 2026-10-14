# 10-PRD-任务看板

> 现行模块：任务看板。文件名为兼容历史链接保留，不再表示Workspace是一级业务模块。Workspace由17号平台管理负责。

## 1. 目标与边界

任务看板是结构化工作入口；首屏则是“项目驾驶舱 + AI对话”入口。两者共同解决目标表达、任务分散、AI运行不可见、审核遗漏和阻塞难追踪的问题，但不拥有策略、用例、脚本、结果、Defect或报告正文。

## 2. 用户与核心场景

| 用户 | 要完成的事 |
|---|---|
| TestEngineer | 查看分配任务、AI进度、退回修改和阻塞，进入对应产出物处理 |
| TestLead | 调整范围/优先级/依赖，监控Release进展和审核积压 |
| Reviewer/Approver职责 | 在统一待审核队列查看Diff、证据、检查结果并决定 |
| Agent/Service | 在授权Workflow内领取步骤、写运行状态和提交审核包 |

## 3. 功能需求

| 能力 | 需求 | AI作用 | 人工控制 |
|---|---|---|---|
| 工作项 | 创建、查询、筛选、分派、优先级、父子关系、Release/TestPlan关联 | 根据目标建议拆分和依赖 | 确认关键范围、负责人和优先级 |
| 状态流转 | 按状态机流转并记录原因 | 自动推进低风险运行态 | `BLOCKED`、取消、关键范围变更需有理由/权限 |
| AI运行 | 显示Agent、Skill、版本、步骤、耗时、成本、Trace和降级 | 执行并持续上报 | 可暂停/取消；越权和异常由人处理 |
| 审核队列 | 按产出物、风险、Release、到期时间和职责筛选 | 预检摘要、证据、Diff和阻断检查 | ReviewDecision仅UserIdentity可作出 |
| 退回重做 | 保留原版本和决定，创建新版本/attempt | 按意见改稿并重新验证 | 审核人复核新摘要，不沿用旧批准 |
| 阻塞管理 | 原因码、详情、恢复条件、依赖人/系统和SLA | 归纳阻塞与建议下一步 | 决定接受风险、补资料或调整计划 |
| 看板统计 | WIP、周期、审核时长、阻塞、人工接管和AI失败 | 汇总趋势和异常 | 指标用于改进，不作为个人绩效自动裁决 |
| 首屏项目驾驶舱 | 默认显示最近更新项目，可切换项目/Release，展示资料完整度、当前阶段、风险、活动和待办 | 生成摘要并指向证据 | 项目切换后所有对话和命令必须使用新的workspaceId |
| 协作对话 | 创建/继续Conversation，把意图转为Clarification、TaskCard和AgentPlan | 提问、拆解、生成方案 | 人工确认TaskContract后才能执行 |
| 运行命令 | 暂停、继续、取消、重试、调整范围，展示CommandReceipt | 解释影响和恢复点 | 服务端重算授权，命令幂等且可审计 |

## 4. 核心契约

- WorkItem状态：`BACKLOG → READY → IN_PROGRESS → PENDING_REVIEW → REWORK(→ IN_PROGRESS)/APPROVED → DONE`，并支持`BLOCKED/CANCELLED`；完整迁移以 05 §5.5.4 为准（裁决 2026-08-14 批次二）。
- WorkItemRun记录actorType、Agent/Workflow版本、授权快照、输入输出摘要、Trace与verdict。
- ReviewTask绑定`artifactType、artifactId、artifactVersionId、contentDigest、policyType`。
- ReviewDecision为`APPROVE/REQUEST_CHANGES/REJECT`且只追加。
- 看板中“已批准”不等于外部同步或发布已完成；后续动作各自重新授权。

## 5. 主流程

```text
目标/Release → 创建WorkItem → AI或人工处理 → 形成不可变产出版本
→ 确定性检查/独立验证 → 创建ReviewTask → 人工决定
→ 批准后由Owner模块发布，或退回创建新版本 → WorkItem完成/继续
```

## 6. 异常与降级

- 输入版本变化：标记产出`STALE`，暂停审核并重新生成受影响内容。
- Agent越权、循环、超时或预算超限：停止后续节点，保留Trace，WorkItem转`BLOCKED`。
- 审核人无能力/作用域或违反职责分离：拒绝决定并重新分派。
- 依赖资源取消/归档：返回冲突并显示阻塞引用，不级联删除证据（HTTP 409 为实现细节，以语义为准，裁决 2026-08-14 批次二）。

## 7. 验收标准

### AC-01 AI产出进入人工审核

- **Given** AI完成TestPlanVersion草稿；
- **When** Workflow提交结果；
- **Then** WorkItem进入`PENDING_REVIEW`并创建绑定精确版本与摘要的ReviewTask，不直接批准。

### AC-02 退回不覆盖历史

- **Given** 审核人退回TestCaseVersion V1；
- **When** Agent按意见修改；
- **Then** 创建V2并重新检查/审核，V1、决定和Trace保持可查。

### AC-03 越权失败关闭

- **Given** Agent请求未在allowlist的外部写入；
- **When** 节点执行前授权；
- **Then** 调用不发生，WorkItem阻塞并记录DENY原因。

### AC-04 聚合不篡改Owner状态

- **Given** TestReport由质量分析与缺陷模块归档；
- **When** 看板刷新；
- **Then** 只读取投影并展示，不在看板存第二份可写报告状态。

## 8. 版本范围

V1交付基础看板、运行状态、审核队列、退回和阻塞处理，并采集效率指标（Lead/Cycle Time、审核时长、阻塞时长、AI 成功率与成本、产出物生成到批准时间等，见 05 §5.5.11；指标口径与数据字典按批 3/2026-08-14 定义，采集自 WorkItemEvent/WorkItemRun 事件，不手工录入）——这是 V1 退出条件“记录人工净处理时间/AI 草稿采用率/退回原因”的产品载体（裁决 2026-08-14）；V2增强SLA、团队负载和跨集成通知；V3增强在政策内的跨工作项L3编排，不取消人工硬门。

V1还必须交付首屏对话、最近项目驾驶舱、项目/Release切换、TaskCard/AgentPlan确认、澄清队列和真实运行命令；这些能力在39号契约激活前均为待实现。
