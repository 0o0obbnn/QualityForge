export interface ApiEnvelope<T> {
  code: string
  message: string
  traceId: string
  data: T
}

export interface LocalAuthStatus {
  setupRequired: boolean
  authenticated: boolean
  profile: Profile | null
}

export interface Profile {
  userId: string
  tenantId: string
  workspaceId: string
  email: string
  actorType: "USER" | "SERVICE" | "AGENT"
  capabilities: string[]
  /** 当前真实 Release；为空时禁止需要 Release 的正式创建。 */
  releaseId?: string
  releaseName?: string
}

/** WP-01A 项目/Release 上下文（listWorkspaces / listReleases 投影行）。 */
export interface WorkspaceOption {
  id: string
  name: string
  /** WP-01 常用项目置顶（服务端置顶组优先排序；mock 模式本地维护）。 */
  pinned?: boolean
}

export interface ReleaseOption {
  id: string
  name: string
  status: string
}

export interface ReviewTask {
  id: string
  workItemId: string
  agentSessionId: string
  artifactType: "TEST_STRATEGY" | "TEST_PLAN" | "TEST_CASE"
  artifactId: string
  artifactVersionId: string
  contentDigest: string
  policyType: string
  status: string
  assignments: Array<Record<string, unknown>>
  createdAt: string
  /** 契约 32-API规范.yaml L879：过期时间，用于陈旧状态判定（M1-F1 #12） */
  expiresAt?: string
  /** 墙 M-120 裁决：单值禁用原因（M1 实际值 TASK_CLOSED / STALE_VERSION，null=可批准） */
  approveDisabledReason?: string | null
  /** WP-05 切片二：最少不同审批人数（SINGLE_REVIEW=1、FOUR_EYES=2） */
  minApprovers?: number
  /** WP-05 切片二：已记录的批准决定（FOUR_EYES 逐人追加） */
  approvals?: Array<ReviewApproval>
}

export interface ReviewApproval {
  actorId: string
  decidedAt: string
  comments?: string | null
}

export interface ReviewArtifact {
  artifactType: ReviewTask["artifactType"]
  artifactId: string
  artifactVersionId: string
  contentDigest: string
  content: Record<string, unknown>
}

export interface TraceEvent {
  sequence: number
  nodeId: string
  agentId: string
  skillId: string
  status: string
  occurredAt: string
  artifactType?: string
  artifactVersionId?: string
  contentDigest?: string
}

/** AgentSession 状态枚举，权威源 33 t_agent_session CHECK，见 03 术语表 §13.13。 */
export type AgentSessionStatus = "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED" | "CANCELLED" | "BLOCKED"

export interface AgentSession {
  id: string
  status: AgentSessionStatus
  /** Stage 4 过渡字段，随 WorkItemRun/Agent 模型迁移移除（同 32 AgentSession 标注）。 */
  reviewTaskIds?: string[]
  workItemRunId?: string
  agentId?: string
  workflowVersionId?: string
  promptVersionId?: string
  tokenUsage?: Record<string, unknown>
  cost?: Record<string, unknown>
  errorCode?: string
  startedAt?: string
  completedAt?: string
}

/* ---------- M5 降级状态（假设契约 GET /ai/provider/status，mock 先行） ---------- */
export type ProviderState = "NOMINAL" | "DEGRADED" | "UNKNOWN";

export interface ProviderStatus {
  status: ProviderState;
  providerId: string;
  fallbackProviderId?: string;
  reason?: string;
  since?: string;
}

/** WP-03 协作对话（批次六十前端接入）。 */
export interface ConversationRow {
  id: string
  title: string
  status: string
  releaseId?: string | null
  workItemId?: string | null
  lastActivityAt: string
}

export interface ConversationMessageRow {
  id: string
  conversationId: string
  actorType: "USER" | "AGENT" | "SYSTEM"
  actorId: string
  messageType: string
  contentRef: string
  contentDigest: string
  dataClass: "PUBLIC" | "INTERNAL" | "CONFIDENTIAL" | "RESTRICTED"
  createdAt: string
}

/** WP-03 任务卡与 AgentPlan（批次六十一前端接入）。 */
export interface TaskCardRow {
  id: string
  workItemId: string
  objective: string
  scope: string
  status: "SUBMITTED" | "ACTIVE" | "SUPERSEDED" | "DRAFT"
  contentDigest: string
  createdAt: string
}

export interface AgentPlanStepRow {
  stepKey: string
  agentRole: string
  description: string
}

export interface AgentPlanRow {
  id: string
  workItemId: string
  taskCardId: string
  planVersion: number
  steps: AgentPlanStepRow[]
  status: "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "SUPERSEDED" | "DRAFT"
  contentDigest: string
  createdAt: string
}

/** WP-04 运行命令回执（批次六十一前端接入）。 */
export interface RunCommandResult {
  id: string
  commandType: string
  status: string
  receipt: {
    accepted: boolean
    effectiveStatus: string
    safePointRef: string
    reasonCode: string
    completedAt: string
  }
}
