/**
 * 领域类型（看板/审核/工作项详情的 UI 层数据形态）。
 * 从 mock/mockData.ts 抽离至此——类型是契约的一部分，不随 mock 数据文件变动。
 * mock 模式与真实模式（services/dataService.ts 映射后）共用同一套类型。
 */

export interface QueueItem {
  id: string;
  workItemId: string;
  reviewTaskId: string;
  type: "策略" | "用例" | "计划" | "代码" | "报告" | "知识";
  typeClass: "strategy" | "case" | "plan" | "code" | "report" | "knowledge";
  title: string;
  version: string;
  due: string;
  dueClass: "err" | "warn" | "muted";
  detail: ReviewDetailData;
}

export interface ReviewDetailData {
  reviewTask: string;
  policy: string;
  artifactVersion: string;
  changeSummary: string;
  aiRun: string;
  sourceBaseline: string;
  digest: string;
  /** 完整摘要（真实模式下提交决定用） */
  digestFull?: string;
  tabs: {
    diff: Array<{ kind: "add" | "del" | "plain"; old: string; next: string }>;
    trace: Array<{ label: string; state: "confirmed" | "inferred" }>;
    checks: Array<{ state: "pass" | "review" | "pending"; label: string; verdict: string }>;
    evidence: Array<{ label: string; href: string }>;
  };
  approveDisabledReason?: string | null;
  policyBar: string;
  /** WP-05 切片二（批次六十七）：任务状态（真实模式来自 ReviewTask.status） */
  taskStatus?: string;
  /** WP-05 发布链：资产根 id（发布命令的路径参数，完整 UUID） */
  artifactId?: string;
  /** WP-05 发布链：契约 artifactType 枚举 */
  artifactTypeCode?: string;
  /** WP-05 切片二：最少不同审批人数（>1 时展示双人复核进度） */
  minApprovers?: number;
  /** WP-05 切片二：已记录的批准决定 */
  approvals?: Array<{ actorId: string; decidedAt: string; comments?: string | null }>;
}

export interface BoardRow {
  id: string;
  title: string;
  sub: string;
  type: string;
  typeClass: string;
  status: "review" | "run" | "blocked" | "done" | "backlog";
  statusLabel: string;
  actor: string;
  ai: boolean;
  priority: "P0" | "P1" | "P2";
  risk: "高" | "中" | "低";
  due: string;
  dueOver: boolean;
  filter: string;
  href: string;
}

export interface AiRun {
  name: string;
  agent: string;
  step: string;
  progress: number;
}

export interface WorkItemDetailData {
  id: string;
  type: string;
  typeClass: string;
  title: string;
  createdAt: string;
  actor: string;
  ai: boolean;
  status: string;
  statusLabel: string;
  basicInfo: Array<{ k: string; v: string }>;
  run: {
    step: string;
    elapsed: string;
    progress: number;
    checks: Array<{ state: "pass" | "review" | "pending"; label: string; verdict: string }>;
  };
  timeline: Array<{ at: string; text: string; current?: boolean }>;
  assets: Array<{ k: string; v: string; href?: string }>;
  metrics: Array<{ k: string; v: string }>;
}

/* ===== M3 执行域领域类型（契约 32/33/36 对齐，2026-08-18） ===== */

/** 契约 ExecutionTask（32 L1279：8 状态；33 t_execution_task 对齐） */
export interface ExecutionTask {
  id: string;
  executionPlanVersionId: string;
  runnerId?: string;
  status: "PENDING" | "QUEUED" | "RUNNING" | "PAUSED" | "COMPLETED" | "FAILED" | "CANCELLED" | "TIMED_OUT" | "BLOCKED";
  startedAt?: string;
  completedAt?: string;
}

/** 契约 ExecutionResult（32 L1280：5 值全大写） */
export interface ExecutionResult {
  id: string;
  executionTaskId: string;
  testCaseVersionId?: string;
  status: "PASSED" | "FAILED" | "SKIPPED" | "ERROR" | "INCONCLUSIVE";
  durationMs?: number;
  logRef?: string;
  createdAt?: string;
}

/** 契约 ExecutionArtifact（32 L1281：4 值 artifactType） */
export interface ExecutionArtifact {
  id: string;
  executionResultId: string;
  artifactType: "LOG" | "SCREENSHOT" | "VIDEO" | "TRACE";
  ref?: string;
  digest?: string;
  createdAt?: string;
}

/**
 * 视图聚合类型（dataService map 输出，供页面渲染）：
 * 审计结论——attemptNo/durationMs/result 契约无直出字段，须客户端聚合
 * （durationMs 由 startedAt/completedAt 计算；result 经 listExecutionResults join；attempt 经 retry_of_task_id 链）。
 */
export interface ExecutionTaskRow {
  id: string;
  taskNo: string;
  scriptVersion: string;
  attemptNo: number;
  status: ExecutionTask["status"];
  result: ExecutionResult["status"] | null;
  runnerId: string;
  durationMs: number | null;
}

/** 执行进度（docs/36 §4 ExecutionProgressUpdated：七计数，SKIPPED/ERROR/INCONCLUSIVE 分别计数） */
export interface ExecutionProgress {
  total: number;
  completed: number;
  passed: number;
  failed: number;
  skipped: number;
  error: number;
  inconclusive: number;
}
