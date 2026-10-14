# QualityForge WebSocket实时契约

> 本文是[32-API规范.yaml](32-API规范.yaml)的实时补充。REST负责创建资源、状态转换、批准、取消和外部写入；WebSocket只推送实时状态、日志和Trace，不提供绕过REST授权/幂等门禁的高价值写操作。

## 1. 通道

| 通道 | 握手URL | 主要事件 | Owner |
|---|---|---|---|
| ExecutionTask Stream | `/api/v1/execution-tasks/{executionTaskId}/stream` | 任务状态、结果、日志摘要、制品可用、契约偏差 | 测试执行 |
| WorkItem Stream | `/api/v1/work-items/{workItemId}/stream` | 工作项状态、Agent尝试、阻塞、产出物、审核创建 | 任务看板 |
| Agent Trace Stream | `/api/v1/ai/sessions/{agentSessionId}/trace-stream` | 会话状态、TraceNode、SkillInvocation、权限拒绝 | AI Agent中心 |
| Workspace Event Stream | `/api/v1/workspaces/{workspaceId}/events` | 当前用户有权看到的任务/审核/执行/质量摘要事件 | 任务看板聚合投影 |
| Conversation Stream（待激活） | `/api/v1/conversations/{conversationId}/stream` | 消息追加、澄清、TaskContract、RunCommand回执摘要 | 项目与协作 |

旧`/executions/tasks/*`、`/agents/sessions/*`、`/workspaces/*/scan-stream`和独立`ai-observe`通道不再是现行契约。来源导入/AI扫描进度统一表现为WorkItem事件；AI观察作为ExecutionTask/Agent Trace中的建议事件，不与执行事实并列为第二真相源。

## 2. 鉴权与授权

1. 客户端以Bearer JWT调用`POST /api/v1/auth/ws-tickets`，请求资源类型和资源ID。
2. 服务端在签发时完成Tenant、Workspace、RBAC和资源授权，返回一次性、短时、绑定资源的ticket。
3. 客户端使用`wss://.../stream?ticket=...&lastOffset=...`握手；ticket使用后立即失效。
4. 网关必须剥离客户端伪造的身份Header，并使用票据中的可信身份。
5. 连接存续期间角色撤销、Workspace归档或资源权限变化时，服务端终止订阅；不能只在握手时授权。
6. PlatformAdmin默认无租户业务内容权限；没有SupportAccessGrant时不能订阅租户流。
7. 每个下行事件在发布前按Tenant/Workspace/Resource权限过滤；禁止先广播再由前端隐藏。

票据响应不进入URL日志或Audit明文；服务端只保存票据摘要、资源、签发人、过期时间和使用结果。

## 3. 通用事件信封

```json
{
  "schemaVersion": "1.0",
  "eventId": "5e87195a-e0c5-4caa-9dd8-e99485c60493",
  "type": "WorkItemStatusChanged",
  "sequence": 128,
  "offset": "1720785600123-0",
  "tenantId": "d213d4df-f54a-48f5-b359-ea16c948d51e",
  "workspaceId": "9aa59f51-aa50-4aa7-97da-27eb6c61cf63",
  "resourceType": "WORK_ITEM",
  "resourceId": "92456992-af60-4f15-b20c-bc8c0292d61c",
  "occurredAt": "2026-08-11T12:00:03.412Z",
  "traceId": "tr_01J5...",
  "data": {}
}
```

| 字段 | 规则 |
|---|---|
| `schemaVersion` | 事件Schema版本；新增可选字段不升主版本 |
| `eventId` | UUID；客户端最终去重键 |
| `type` | 受控事件类型，不允许业务自由字符串 |
| `sequence` | 单资源单调递增序号 |
| `offset` | 服务端稳定补发游标；客户端不能解析其内部格式 |
| `tenantId/workspaceId` | 权限上下文；平台级事件workspaceId可空 |
| `resourceType/resourceId` | 事件主资源 |
| `occurredAt` | UTC ISO8601 |
| `traceId` | 与REST、Audit、Agent/Runner日志关联 |
| `data` | 类型专属载荷；不得包含Secret或隐藏思维链 |

送达语义为至少一次；客户端按eventId去重，并按sequence检测缺口。WebSocket事件不是数据库事实的替代，断线或缺口时使用REST读取当前资源及归档事件。

## 4. ExecutionTask Stream

| type | data最小字段 | 事实等级 |
|---|---|---|
| `ExecutionTaskStatusChanged` | `fromStatus/toStatus/reasonCode` | CONFIRMED |
| `ExecutionProgressUpdated` | `total/completed/passed/failed/skipped/error/inconclusive` | CONFIRMED |
| `ExecutionLogAvailable` | `executionResultId/artifactId/level/preview` | CONFIRMED；完整日志走受控制品读取 |
| `ExecutionResultRecorded` | `executionResultId/testCaseVersionId/scriptVersionId/status/durationMs/isExperimental` | CONFIRMED |
| `ExecutionArtifactAvailable` | `executionResultId/artifactId/artifactType/mediaType` | CONFIRMED；不推永久URL |
| `ContractDeviationDetected` | `executionResultId/checkResultId/operationVersionId/status/severity` | CONFIRMED比较结果 |
| `AutomationChangeSuggested` | `candidateType/locatorId/scriptVersionId/confidence/evidenceRefs` | INFERRED；不得自动改正式资产 |
| `ExecutionTaskTerminated` | `finalStatus/reasonCode` | CONFIRMED |

`ExecutionProgressUpdated`必须把SKIPPED、ERROR、INCONCLUSIVE分别计数，不能只推passRate掩盖分母。`ExecutionResultRecorded.status`只允许`PASSED/FAILED/SKIPPED/ERROR/INCONCLUSIVE`。

取消、重试和状态改变必须调用32中的REST命令并携带Idempotency-Key；WebSocket不接受`Abort/Pause/Approve`等业务命令。

## 5. WorkItem Stream

| type | data最小字段 |
|---|---|
| `WorkItemStatusChanged` | `fromStatus/toStatus/currentActorType/currentActorId/reason` |
| `WorkItemRunStarted` | `workItemRunId/attemptNo/actorType/agentSessionId` |
| `WorkItemRunCompleted` | `workItemRunId/status/outputDigest/errorCode` |
| `WorkItemBlocked` | `reasonCode/details/dependencyIds` |
| `ArtifactVersionProduced` | `artifactType/artifactId/artifactVersionId/contentDigest/relationType` |
| `ReviewTaskCreated` | `reviewTaskId/policyType/riskLevel/expiresAt` |
| `ReviewTaskCompleted` | `reviewTaskId/status/decisionCount` |

来源导入、TestingIR编译、用例/代码/报告生成等异步工作统一通过WorkItemRun事件展示；事件不能把Agent输出PASS表达为正式资产APPROVED。

## 6. Agent Trace Stream

| type | data最小字段 |
|---|---|
| `AgentSessionStatusChanged` | `status/errorCode` |
| `AgentTraceNodeRecorded` | `traceNodeId/parentNodeId/nodeType/decisionSummary/evidenceRefs/status/durationMs` |
| `SkillInvocationStarted` | `invocationId/skillId/skillVersion/authorizationDecisionId` |
| `SkillInvocationCompleted` | `invocationId/status/outputDigest/errorCode` |
| `AgentPermissionDenied` | `authorizationDecisionId/action/reasonCode` |
| `HumanCheckpointReached` | `workItemId/reviewTaskId/artifactVersionId/contentDigest` |

Trace只包含可审计决策摘要、证据、路由和脱敏工具信息；不得保存或推送隐藏Chain of Thought、Secret、原始Token或未授权正文。

### 6.1 Conversation Stream目标事件（待激活）

| type | data最小字段 |
|---|---|
| `ConversationMessageAppended` | `messageId/actorType/messageType/createdAt` |
| `ClarificationRequested` | `clarificationRequestId/reasonCode/riskLevel/status` |
| `ClarificationResolved` | `clarificationRequestId/responseId/resolvedBy/status` |
| `TaskContractActivated` | `taskContractId/taskCardId/agentPlanVersionId/contentDigest` |
| `RunCommandReceiptRecorded` | `commandId/commandType/decision/effectiveAt/reasonCode` |
| `EvaluationRunCompleted` | `evaluationRunId/targetVersionId/rubricVersionId/status/blockingCount` |

上述事件在对应REST、授权、DB与重连测试同步前不纳入现行运行契约。客户端不得通过Conversation Stream发送暂停、取消、批准或调整范围命令。

## 7. Workspace Event Stream

该通道是面向任务看板的投影，不产生新业务事实。允许事件：

- `BoardItemChanged`：用户有权访问的WorkItem摘要变化；
- `ReviewInboxChanged`：分配给当前用户或其授权职责的审核摘要；
- `ReleaseProgressChanged`：Release/TestPlan聚合进度；
- `QualityRiskChanged`：已批准或明确标为草稿的风险摘要；
- `RunnerAvailabilityChanged`：Workspace可用Runner能力摘要，不包含其他租户节点信息。

事件必须带`sourceResourceType/sourceResourceId/sourceSequence`，客户端需要详情时读取Owner REST资源。聚合投影不得提供跨Owner写入入口。

## 8. 重连、保留与背压

- 客户端保存最后确认offset；重连使用新的ticket和`lastOffset`。
- 服务端从可配置的事件流保留窗口补发；超出窗口返回`ResyncRequired`，客户端使用REST重新同步。
- 背压时可合并低价值进度/日志预览事件，但不能丢状态终态、ExecutionResult、ReviewTask、授权拒绝和外部写入结果。
- 合并/丢弃时发送`BackpressureNotice`，包含事件类型和数量；不得声称流完整。
- 具体保留时间、连接数、延迟和缓冲阈值必须有负载模型与测量基线；旧设计中的固定200ms/500连接/1MB等数字在完成基线前不作为已批准SLA。

## 9. 关闭码

| code | 含义 | 客户端处理 |
|---:|---|---|
| 1000 | 正常终止或资源终态 | 不自动重连；读取REST终态 |
| 1001 | 服务重启/网络切换 | 退避后携lastOffset重连 |
| 4401 | ticket无效、过期或已使用 | 重新申请ticket |
| 4403 | Tenant/Workspace/资源权限拒绝 | 停止重连并展示授权错误 |
| 4404 | 资源不存在或不可见 | 停止重连 |
| 4409 | offset冲突、资源终态或订阅状态冲突 | REST重新同步 |
| 4429 | 当前租户/用户连接配额不足 | 退避并降低订阅数量 |
| 4500 | 服务端不可恢复错误 | 使用traceId报告并回退REST |

## 10. 验收基线

1. Given用户只有Workspace A权限，When订阅Workspace B，Then握手以4403拒绝且无任何B数据帧。
2. Given角色在连接后被撤销，When下一次授权重检发生，Then连接终止且不继续推送。
3. Given同一event至少一次送达两次，When客户端处理，Then按eventId只应用一次。
4. Givensequence出现缺口且offset已过期，When重连，Then收到ResyncRequired并通过REST恢复，不能假定数据完整。
5. GivenAgent建议Locator修改，When未有人工审核，Then只出现AutomationChangeSuggested，不出现正式Locator变更事件。
6. Given执行包含SKIPPED/ERROR/INCONCLUSIVE，When推送进度，Then三者分别计数且不计入PASSED。
7. Given日志含Token，When形成Trace/Log预览，Then敏感值已脱敏，完整制品仍受权限控制。
8. Given客户端通过WebSocket发送Approve/Abort命令，When服务端收到，Then拒绝并要求调用受控REST端点。
