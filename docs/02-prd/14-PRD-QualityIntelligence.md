# 14-PRD-测试执行

> 现行模块：测试执行。文件名为兼容历史链接保留。质量分析职责迁至15号。

## 1. 目标与边界

以可复现、可授权、可观察的方式运行人工/自动化测试并保存不可变事实。测试执行拥有ExecutionPlan、Task、Result、Log和Evidence，不拥有对失败的业务解释、Defect或报告结论。

## 2. 功能需求

| 能力 | 需求 | AI/系统作用 | 人工控制 |
|---|---|---|---|
| 执行计划 | 稳定根+不可变版本，绑定TestPlanVersion、Release、Environment、范围、并发、Runner策略 | 校验并冻结全部资产版本 | 审核高风险环境/范围和首跑 |
| 触发 | V1：手工、计划；V2：Webhook、Pipeline（裁决 B2-9）；统一幂等 | 创建Batch/Task并授权 | 取消、重跑和高风险触发需权限 |
| 调度 | 按能力/资源池/配额选Runner，租约、心跳和重试 | 自动调度、故障检测 | 处理资源不足或特殊环境 |
| 执行任务 | 状态、attempt、超时、重试（V1 默认一次受控重试，裁决 2026-08-14 批次二）、环境/授权快照 | 执行固定版本，不临时换资产 | 可暂停/取消；不能编辑运行中版本 |
注：暂停 = status=BLOCKED + blocked_reason=USER_PAUSED（裁决 2026-08-14 B4：字段落 33 t_execution_task，语义与依赖阻塞等区分由 blocked_reason 承载，状态机不新增 PAUSED） |
| 契约检查 | 按ExecutionContractBaseline记录APIObservation与ContractCheckResult（MATCH/DEVIATION/NOT_CHECKED/INCONCLUSIVE）；未检查不能计为通过（裁决 B2-2，2026-08-14） | 自动检查与偏差标注 | 偏差证据只追加；INCONCLUSIVE 不得报告为契约一致 |
| 结果 | 每个attempt产生独立ExecutionResult | 记录事实和机器判定 | 人工注释不能改原始事实 |
| 证据 | 请求/响应、日志、截图、视频、Trace、性能数据、摘要和保留策略 | 自动采集、脱敏和索引 | 敏感证据访问受限 |
| 实时流 | ExecutionTask进度、日志和制品事件 | 断线续传、顺序/offset | WebSocket不承载批准/修改命令 |
| 手工测试 | 记录步骤结果、实际结果和证据（已裁决纳入 V1，O2 裁决 2026-08-17） | 辅助整理 | 测试人员对手工结果负责 |

## 3. 状态与事实规则

- ExecutionTask状态：`PENDING/QUEUED/RUNNING/COMPLETED/FAILED/CANCELLED/TIMED_OUT/BLOCKED`。其中`COMPLETED`表示任务调度与采集完成；用例业务结论只看ExecutionResult的`PASSED/FAILED/SKIPPED/ERROR/INCONCLUSIVE`。
- `FAILED`表示被测行为未满足断言；`ERROR`表示环境、脚本、Runner或平台未完成有效验证；二者不可合并。
- 重跑创建新Batch/Task attempt，不覆盖旧结果。
- ExecutionPlanVersion必须固定TestCaseVersion、AutomationScriptVersion、ExecutionContractBaseline（由 APIContractBaseline 复制精确版本+运行时映射/认证/脱敏快照，裁决 2026-08-14 批次二）、Environment和数据/Mock/Locator等引用及摘要。
- ResultAnalysis只能引用ExecutionResult，不能反写其状态或正文。

## 4. 主流程

```text
已批准TestPlan/Case/Script → 创建ExecutionPlanVersion → 预检授权/环境/能力/版本
→ 触发Batch → 调度Task/Runner → 采集Result/Log/Evidence
→ 完成状态与实时事件 → 质量分析与缺陷模块读取不可变事实进行分析
```

## 5. 异常与恢复

- Runner失联：租约到期后按策略创建新attempt；原attempt标记ERROR并保留证据。
- 版本摘要不匹配：启动前返回`STALE_ARTIFACT_VERSION`，禁止执行。
- 执行基线撤销/权限失效/必需凭证不可用：ExecutionTask转`BLOCKED`，不自动切换到最新版（裁决 2026-08-14 批次二，对齐 05 §5.10.7）。
- 环境/Secret无权：返回明确原因，不把未执行记为失败用例。
- 网络中断：实时订阅可用offset补拉；服务端结果不依赖客户端在线。
- 取消：停止未开始任务，运行中任务尽力终止并记录实际状态。

## 6. 验收标准

### AC-01 版本冻结

- **Given** ExecutionPlanVersion已创建；
- **When** TestCase或Script发布新版本；
- **Then** 本次执行仍使用已冻结旧版本，新版本需新ExecutionPlanVersion。

### AC-02 FAIL与ERROR分离

- **Given** 一个断言失败、另一个Runner启动失败；
- **When** 汇总结果；
- **Then** 前者为FAILED、后者为ERROR，报告不能把ERROR计入有效业务失败/通过分母而不披露。

### AC-03 重跑不覆盖

- **Given** Task attempt1失败；
- **When** 自动重试成功；
- **Then** attempt1和attempt2均可查，最终汇总说明采用规则。

### AC-04 实时票据授权

- **Given** 用户无目标Task访问权；
- **When** 申请WebSocket票据；
- **Then** 签发被拒绝且不泄漏任务存在性。

### AC-05 契约偏差事实留存（裁决 B2-2，2026-08-14）

- **Given** 执行完成且部分Operation未检查；
- **When** 生成执行结果；
- **Then** ContractCheckResult 含 MATCH/DEVIATION/NOT_CHECKED/INCONCLUSIVE 四态且未检查不计为通过，INCONCLUSIVE 不被报告为契约一致。

## 7. 版本范围

V1支持单资源池Web/API执行、冻结、结果与证据；V2增强多Runner、恢复和流水线；V3增强弹性、性能/安全等执行能力与企业隔离。
## 8. 指标承接(裁决 2026-08-14;指标口径见 20 号 §1.1 受控 metricKey 登记表,覆盖率口径见 22 号附录 C)

| 指标 | 本模块角色 | 基线 | 测量方法 | 验收 |
|---|---|---|---|---|
| 失败结果到 Bug 草稿时间(M-06) | 生产 | 试点后批准(22 §6) | ExecutionResult FAILED→首个 Defect 草稿创建,FailureAnalysis 关联 | AC:草稿≠提交≠外部同步,分层计时 |
| 平均重试次数(M-41) | 生产 | 试点后批准 | attemptNo>1 之和/任务数,WorkItemRun.attemptNo、ExecutionTask.retryOfTaskId | AC:重试不覆盖历史证据 |
| 结果可复现率(M-22 备选) | 生产 | 载体建立后批准 | 同基线重跑判定一致比例,ExecutionTask 重跑 | AC:环境快照不同不可比 |
