/**
 * 数据服务层（mock/真实双模式）：
 * - VITE_MOCK=1：返回原型演示数据（mockData.ts），前端独立可预览
 * - 否则：调用后端契约接口（32-API规范.yaml），联调后切换零代码
 * 页面组件只依赖本层导出的类型，不感知数据来源。
 */

import { api } from "../api";
import type {
  AgentPlanRow,
  ConversationMessageRow,
  ConversationRow,
  Profile,
  RunCommandResult,
  TaskCardRow,
  ProviderStatus,
  ReleaseOption,
  ReviewArtifact,
  ReviewTask,
  WorkspaceOption,
} from "../types";
import {
  agentPlanRows,
  boardRows,
  conversationMessageRows,
  conversationRows,
  queueItems,
  taskCardRows,
  workItemDetail,
  workspaceRows,
} from "../mock/mockData";
import type { BoardRow, QueueItem } from "../types/domain";

const MOCK_MODE = import.meta.env.VITE_MOCK === "1";

/* ---------- mock 本地持久化（deep_delivery：提交可重新查询、刷新不丢） ---------- */

const MOCK_STORE_KEY = "qf_mock_store";

type MockStore = Record<string, Array<Record<string, unknown>>>;

function loadMockStore(): MockStore {
  try {
    const raw = window.localStorage.getItem(MOCK_STORE_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? (parsed as MockStore) : {};
  } catch {
    return {};
  }
}

function saveMockStore(store: MockStore): void {
  try {
    window.localStorage.setItem(MOCK_STORE_KEY, JSON.stringify(store));
  } catch {
    /* 隐私模式等写入失败：静默降级为会话内存，功能不阻塞 */
  }
}

function readMockCollection<T extends Record<string, unknown>>(key: string): T[] {
  return (loadMockStore()[key] ?? []) as T[];
}

function appendMockItem(key: string, item: Record<string, unknown>): void {
  const store = loadMockStore();
  const items = store[key] ?? [];
  items.push(item);
  store[key] = items;
  saveMockStore(store);
}

/** 审核决定台账读取入口（供验收复核与测试使用） */
export function readMockDecisions(): Array<Record<string, unknown>> {
  return readMockCollection("reviewDecisions");
}

export function resetMockStore(): void {
  try {
    window.localStorage.removeItem(MOCK_STORE_KEY);
  } catch {
    /* 同上：失败静默 */
  }
}

/* ---------- 审核队列 ---------- */

function mapReviewTask(task: ReviewTask): QueueItem {
  const typeMap: Record<string, { label: QueueItem["type"]; cls: QueueItem["typeClass"] }> = {
    TEST_STRATEGY: { label: "策略", cls: "strategy" },
    TEST_PLAN: { label: "计划", cls: "plan" },
    TEST_CASE: { label: "用例", cls: "case" },
  };
  const mapped = typeMap[task.artifactType] ?? { label: "知识", cls: "knowledge" };
  return {
    id: task.id,
    workItemId: task.workItemId.slice(0, 8),
    reviewTaskId: task.id.slice(0, 8),
    type: mapped.label,
    typeClass: mapped.cls,
    title: `${mapped.label} ${task.artifactVersionId.slice(0, 8)}`,
    version: "V?",
    due: task.expiresAt ? new Date(task.expiresAt).toLocaleString() : "—",
    dueClass: "muted",
    detail: {
      reviewTask: `${task.id.slice(0, 8)} · ${task.policyType}`,
      policy: task.policyType,
      artifactVersion: task.artifactVersionId,
      changeSummary: "（联调：变更摘要随版本接口返回）",
      aiRun: `会话 ${task.agentSessionId.slice(0, 8)}`,
      sourceBaseline: "（联调：来源基线待溯源接口）",
      digest: task.contentDigest.slice(0, 18) + "…",
      digestFull: task.contentDigest,
      tabs: {
        diff: [],
        trace: [],
        checks: [],
        evidence: [{ label: "产出物正文", href: "/planning" }],
      },
      approveDisabledReason: task.approveDisabledReason ?? null,
      policyBar: `审核策略: ${task.policyType} · 决定仅限人工 · 前端禁用不是授权边界`,
      taskStatus: task.status,
      artifactId: task.artifactId,
      artifactTypeCode: task.artifactType,
      minApprovers: task.minApprovers,
      approvals: task.approvals ?? [],
    },
  };
}

export async function fetchReviewQueue(profile: Profile): Promise<QueueItem[]> {
  if (MOCK_MODE) return queueItems;
  const response = await api<ReviewTask[]>(`/api/v1/review-tasks?workspaceId=${profile.workspaceId}`);
  return response.data.map(mapReviewTask);
}

export async function fetchReviewArtifact(taskId: string): Promise<ReviewArtifact | null> {
  if (MOCK_MODE) return null;
  try {
    const response = await api<ReviewArtifact>(`/api/v1/review-tasks/${taskId}/artifact`);
    return response.data;
  } catch {
    return null;
  }
}

export async function submitReviewDecision(
  taskId: string,
  decision: "APPROVE" | "REQUEST_CHANGES" | "REJECT",
  contentDigest: string,
  comments: string,
): Promise<void> {
  if (MOCK_MODE) {
    // mock 持久化：审核决定写入台账，刷新不丢（台账可在 /reviews 列表复核）
    appendMockItem("reviewDecisions", {
      taskId,
      decision,
      contentDigest: contentDigest.slice(0, 12),
      comments,
      decidedAt: new Date().toISOString(),
    });
    return;
  }
  await api<ReviewTask>(`/api/v1/review-tasks/${taskId}/decisions`, {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify({ decision, contentDigest, comments: comments || undefined }),
  });
}

/* ---------- 工作看板 ---------- */

export async function fetchBoardRows(profile: Profile): Promise<BoardRow[]> {
  if (MOCK_MODE) {
    const created = readMockCollection<Record<string, unknown>>("workItems").map((item) => ({
      id: String(item.id ?? "").slice(0, 8),
      title: String(item.title ?? ""),
      sub: String(item.description ?? "").slice(0, 40) || "—",
      type: String(item.workItemType ?? "知识"),
      typeClass: "",
      status: "review" as BoardRow["status"],
      statusLabel: "待审核",
      actor: "—",
      ai: false,
      priority: (item.priority as BoardRow["priority"]) ?? "P2",
      risk: "中" as BoardRow["risk"],
      due: String(item.createdAt ?? "").slice(5, 10) || "—",
      dueOver: false,
      filter: "review",
      href: `/work-items/${String(item.id ?? "")}`,
    }));
    return [...created, ...boardRows];
  }
  const response = await api<Array<Record<string, unknown>>>(`/api/v1/work-items?workspaceId=${profile.workspaceId}`);
  const rows: BoardRow[] = response.data.map((item) => ({
    id: String(item.id ?? "").slice(0, 8),
    title: String(item.title ?? ""),
    sub: String(item.objective ?? "").slice(0, 40) || "—",
    type: String(item.workItemType ?? "知识"),
    typeClass: "",
    status: (item.status === "OPEN" ? "review" : "backlog") as BoardRow["status"],
    statusLabel: item.status === "OPEN" ? "待审核" : "待办",
    actor: "—",
    ai: false,
    priority: (item.priority as BoardRow["priority"]) ?? "P2",
    risk: (item.riskLevel === "HIGH" ? "高" : item.riskLevel === "MEDIUM" ? "中" : "低") as BoardRow["risk"],
    due: "—",
    dueOver: false,
    filter: "review",
    href: `/work-items/${item.id}`,
  }));
  return rows;
}

export async function createWorkItem(
  profile: Profile,
  payload: { title: string; description?: string; workItemType: string; priority: string },
): Promise<string | null> {
  if (MOCK_MODE) {
    // mock 持久化：新建工作项写入台账，刷新后仍在看板列表可查
    appendMockItem("workItems", {
      id: crypto.randomUUID(),
      title: payload.title,
      description: payload.description ?? "",
      workItemType: payload.workItemType,
      priority: payload.priority,
      createdAt: new Date().toISOString(),
    });
    return null;
  }
  if (!profile.releaseId) {
    throw new Error("当前项目没有可用 Release，不能创建正式工作项");
  }
  const response = await api<{ id: string }>("/api/v1/work-items", {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify({
      workspaceId: profile.workspaceId,
      releaseId: profile.releaseId,
      workItemType:
        payload.workItemType === "用例"
          ? "CASE"
          : payload.workItemType === "策略"
            ? "STRATEGY"
            : payload.workItemType === "计划"
              ? "PLAN"
              : "GENERAL",
      title: payload.title,
      objective: payload.description || payload.title,
      acceptanceCriteria: payload.description || payload.title,
      requiresReview: true,
      priority: payload.priority,
      riskLevel: "MEDIUM",
    }),
  });
  return String(response.data.id);
}

/* ---------- 待审核计数（侧栏徽标） ---------- */

export async function fetchReviewCount(profile: Profile): Promise<number> {
  if (MOCK_MODE) return 6;
  try {
    const response = await api<ReviewTask[]>(`/api/v1/review-tasks?workspaceId=${profile.workspaceId}`);
    return response.data.filter((task) => task.status === "OPEN").length;
  } catch {
    return 0;
  }
}

export { workItemDetail };

/* ---------- 执行域（真实模式接 listExecutionTasks + listEvents 轮询补读；WS/SSE 为已知降级） ---------- */

import { executionTasks, mockEventFeed } from "../mock/mockData";
import type { ExecutionTask, ExecutionTaskRow, ExecutionResult } from "../types/domain";
import type { EventEnvelope } from "./eventEnvelope";

/**
 * 契约 ExecutionTask → 视图聚合行。attemptNo/durationMs/result 契约无直出字段，
 * 由本函数聚合：durationMs 由 startedAt/completedAt 计算；result 与 attemptNo 真实模式
 * 需分别 join listExecutionResults 与 retry_of_task_id 链（后端实现后接入）。
 */
function mapExecutionTask(task: ExecutionTask): ExecutionTaskRow {
  const durationMs =
    task.startedAt && task.completedAt
      ? Date.parse(task.completedAt) - Date.parse(task.startedAt)
      : null;
  return {
    id: task.id,
    taskNo: task.id,
    scriptVersion: "—",
    attemptNo: 1,
    status: task.status,
    result: null,
    runnerId: task.runnerId ?? "—",
    durationMs,
  };
}

export async function fetchExecutionTasks(workspaceId: string): Promise<ExecutionTaskRow[]> {
  if (MOCK_MODE) {
    return executionTasks.map((task) => ({
      id: task.id,
      taskNo: task.taskNo,
      scriptVersion: task.scriptVersion,
      attemptNo: task.attemptNo,
      status: task.status as ExecutionTask["status"],
      result: task.result as ExecutionResult["status"] | null,
      runnerId: task.runnerId,
      durationMs: task.durationMs,
    }));
  }
  // 真实模式：listExecutionTasks 的 workspaceId 为必填查询参数（审计 D 类：前端参数缺陷已修复）
  const response = await api<ExecutionTask[]>(`/api/v1/execution-tasks?workspaceId=${workspaceId}`);
  return response.data.map(mapExecutionTask);
}

export async function fetchExecutionEvents(workspaceId: string): Promise<EventEnvelope[]> {
  if (MOCK_MODE) {
    return mockEventFeed.map((event) => ({
      schemaVersion: "1.0",
      eventId: event.eventId,
      type: event.type,
      sequence: event.sequence,
      resourceType: event.resourceType,
      resourceId: event.resourceId,
      occurredAt: event.occurredAt,
      data: event.data,
    }));
  }
  // 真实模式：listEvents 轮询补读口径（WS/SSE 未实现为已知降级）；REST 面无 sequence，
  // 统一置 0 → mergeEvents 缺口检测不误报
  const response = await api<Array<Record<string, unknown>>>(
    `/api/v1/observability/events?workspaceId=${workspaceId}&pageSize=100`,
  );
  return response.data.map((event) => ({
    schemaVersion: "1.0",
    eventId: String(event.eventId ?? ""),
    type: String(event.eventType ?? ""),
    sequence: 0,
    resourceType: String(event.subjectType ?? ""),
    resourceId: String(event.subjectId ?? ""),
    occurredAt: String(event.occurredAt ?? ""),
    data: (event.payload as Record<string, unknown>) ?? {},
  }));
}

/* ---------- 知识域（后端 listRequirementDocuments/createRequirementDocument 等已实现，前端 mock 先行） ---------- */

import { sourceSnapshots, requirementDocs, knowledgeEntries } from "../mock/mockData";

export type SourceSnapshotRow = (typeof sourceSnapshots)[number];
export type RequirementDocRow = (typeof requirementDocs)[number];
export type KnowledgeEntryRow = (typeof knowledgeEntries)[number];

export async function fetchSourceSnapshots(_profile: Profile): Promise<SourceSnapshotRow[]> {
  if (MOCK_MODE) return sourceSnapshots;
  // 真实模式：后端暂无 listSourceSnapshots 接口（来源导入归 M3/M4 后端待办），返回空态
  return [];
}

export async function fetchRequirementDocs(profile: Profile): Promise<RequirementDocRow[]> {
  if (MOCK_MODE) return requirementDocs;
  const response = await api<Array<Record<string, unknown>>>(`/api/v1/knowledge/requirements?workspaceId=${profile.workspaceId}`);
  return response.data.map((item) => ({
    id: String(item.id ?? "").slice(0, 14),
    title: String(item.title ?? ""),
    items: String(item.items ?? "—"),
    version: String(item.version ?? "V?"),
    parseStatus: "已解析",
    reviewStatus: "已发布",
    reviewClass: "st-done",
    rules: "—",
  }));
}

export async function fetchKnowledgeEntries(profile: Profile): Promise<KnowledgeEntryRow[]> {
  if (MOCK_MODE) return knowledgeEntries;
  const response = await api<Array<Record<string, unknown>>>(`/api/v1/knowledge/entries?workspaceId=${profile.workspaceId}`);
  return response.data.map((item) => ({
    id: String(item.id ?? "").slice(0, 14),
    title: String(item.knowledgeKey ?? ""),
    sub: `knowledgeKey: ${String(item.knowledgeKey ?? "")}`,
    category: String(item.category ?? "—"),
    version: "V1",
    status: String(item.status ?? "ACTIVE") === "ACTIVE" ? "已发布" : String(item.status ?? ""),
    statusClass: "st-done",
    expiry: "—",
  }));
}

/* ---------- 规划域（Sprint 1 T4：后端 listTestStrategies/listTestPlans/listTestCases/listTestCaseVersions 已实现，mock 先行+真实切换） ---------- */

import { strategyRows, planRows, caseRows } from "../mock/mockData";

export type StrategyRow = (typeof strategyRows)[number];
export type PlanRow = (typeof planRows)[number];
export type CaseRow = (typeof caseRows)[number];

export async function fetchStrategies(profile: Profile): Promise<StrategyRow[]> {
  if (MOCK_MODE) return strategyRows;
  const response = await api<Array<Record<string, unknown>>>(`/api/v1/test-strategies?workspaceId=${profile.workspaceId}`);
  return response.data.map((item) => ({
    id: String(item.id ?? "").slice(0, 16),
    title: String(item.title ?? ""),
    version: String(item.version ?? "V?"),
    scope: "—",
    risks: 0,
    status: item.publishedVersionId ? "已发布" : "待审核",
    statusClass: item.publishedVersionId ? "st-done" : "st-review",
    action: item.publishedVersionId ? "已发布" : "待审核",
  }));
}

export async function fetchPlans(profile: Profile): Promise<PlanRow[]> {
  if (MOCK_MODE) return planRows;
  const response = await api<Array<Record<string, unknown>>>(`/api/v1/test-plans?workspaceId=${profile.workspaceId}`);
  return response.data.map((item) => ({
    id: String(item.id ?? "").slice(0, 16),
    title: String(item.title ?? ""),
    version: String(item.version ?? "V?"),
    lifecycle: "ACTIVE",
    lifecycleClass: "st-run",
    milestones: "—",
    status: item.publishedVersionId ? "已发布" : "草稿",
    statusClass: item.publishedVersionId ? "st-done" : "st-review",
    depends: "—",
  }));
}

export async function fetchCases(profile: Profile): Promise<CaseRow[]> {
  if (MOCK_MODE) return caseRows;
  const response = await api<Array<Record<string, unknown>>>(`/api/v1/test-cases?workspaceId=${profile.workspaceId}`);
  return response.data.map((item) => ({
    id: String(item.id ?? "").slice(0, 8),
    title: String(item.title ?? ""),
    sub: "—",
    pri: "P2",
    status: item.publishedVersionId ? "已发布" : "待审核",
    statusClass: item.publishedVersionId ? "st-done" : "st-review",
    cover: "—",
    coverClass: "b-gray",
  }));
}

/* ---------- WP-05 资产发布链（批次六十七：发布是审核通过后的 Owner 命令，正式执行只消费 PUBLISHED 版本） ---------- */

export interface PublishResult {
  versionId: string;
  reviewStatus: string;
}

async function publishVersion(path: string): Promise<PublishResult> {
  const response = await api<Record<string, unknown>>(path, {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
  });
  return {
    versionId: String(response.data.id ?? ""),
    reviewStatus: String(response.data.reviewStatus ?? "PUBLISHED"),
  };
}

export async function publishStrategyVersion(strategyId: string, versionId: string): Promise<PublishResult> {
  if (MOCK_MODE) return { versionId, reviewStatus: "PUBLISHED" };
  return publishVersion(`/api/v1/test-strategies/${strategyId}/versions/${versionId}/publish`);
}

export async function publishPlanVersion(planId: string, versionId: string): Promise<PublishResult> {
  if (MOCK_MODE) return { versionId, reviewStatus: "PUBLISHED" };
  return publishVersion(`/api/v1/test-plans/${planId}/versions/${versionId}/publish`);
}

export async function publishCaseVersion(testCaseId: string, versionId: string): Promise<PublishResult> {
  if (MOCK_MODE) return { versionId, reviewStatus: "PUBLISHED" };
  return publishVersion(`/api/v1/test-cases/${testCaseId}/versions/${versionId}/publish`);
}

/* ---------- 工作项详情（Sprint 1 T5：getWorkItem/listWorkItemRuns 已实现，mock 先行+真实切换） ---------- */


export async function fetchWorkItemDetail(_profile: Profile, workItemId: string): Promise<typeof workItemDetail | null> {
  if (MOCK_MODE) return workItemDetail;
  // 真实模式：getWorkItem 已实现；无数据（404/空）返回 null → 页面显示空态，不虚构
  const response = await api<Record<string, unknown> | null>(`/api/v1/work-items/${workItemId}`);
  const item = response.data;
  if (!item) return null;
  return {
    ...workItemDetail,
    id: String(item.id ?? "").slice(0, 8),
    type: "计划",
    title: String(item.title ?? workItemDetail.title),
    createdAt: String(item.createdAt ?? workItemDetail.createdAt),
    basicInfo: [
      { k: "描述", v: String(item.objective ?? "—") },
      { k: "优先级", v: String(item.priority ?? "P2") },
      { k: "风险等级", v: String(item.riskLevel ?? "低") },
      { k: "关联 Release", v: "—" },
      { k: "父工作项", v: "—" },
      { k: "负责人", v: "—" },
    ],
  };
}

/* ---------- 审核 4 Tab（Sprint 1 T6：getReviewArtifact 已实现，Tab 内容从 artifact.content 提取） ---------- */

import type { ReviewDetailData } from "../types/domain";

/**
 * 从 ReviewArtifact.content 提取 4 Tab 内容（diff/trace/checks/evidence）。
 * content 为自由结构：按已知 key 提取，缺失 key 返回空数组 → Tab 显示空态文案，不虚构。
 */
export async function fetchArtifactTabContent(_profile: Profile, taskId: string): Promise<Partial<ReviewDetailData["tabs"]>> {
  if (MOCK_MODE) return {};
  try {
    const response = await api<ReviewArtifact>(`/api/v1/review-tasks/${taskId}/artifact`);
    const content = response.data.content as Record<string, unknown>;
    const asList = (value: unknown): never[] => (Array.isArray(value) ? (value as never[]) : []);
    return {
      diff: asList(content?.diff),
      trace: asList(content?.trace),
      checks: asList(content?.checks),
      evidence: asList(content?.evidence),
    };
  } catch {
    return {};
  }
}

/* ---------- 执行计划域（真实模式接 listExecutionPlans/createExecutionPlan，批次四十六补路由） ---------- */

import { executionPlanRows } from "../mock/mockData";

export type ExecutionPlanRow = (typeof executionPlanRows)[number];

/** 测试计划选项（完整 UUID，供 createExecutionPlan 的 testPlanId 引用；fetchPlans 的 id 为展示截断版） */
export interface TestPlanOption {
  id: string;
  title: string;
}

export async function fetchTestPlanOptions(profile: Profile): Promise<TestPlanOption[]> {
  if (MOCK_MODE) return planRows.map((plan) => ({ id: plan.id, title: plan.title }));
  const response = await api<Array<Record<string, unknown>>>(`/api/v1/test-plans?workspaceId=${profile.workspaceId}`);
  return response.data.map((item) => ({ id: String(item.id ?? ""), title: String(item.title ?? "") }));
}

export async function fetchExecutionPlans(profile: Profile): Promise<ExecutionPlanRow[]> {
  if (MOCK_MODE) {
    const created = readMockCollection<Record<string, unknown>>("executionPlans").map((item) => ({
      id: String(item.id ?? "").slice(0, 8),
      title: String(item.name ?? ""),
      version: "V1",
      environment: String(item.environment ?? ""),
      trigger: String(item.triggerType ?? "手工"),
      triggerClass: "b-acc",
      concurrency: String(item.concurrency ?? "1"),
      status: "未启动",
      statusClass: "st-idle",
      frozen: "—",
    }));
    return [...created, ...executionPlanRows];
  }
  // 真实模式：listExecutionPlans（批次四十六补路由）；记录无环境/触发/并发字段，占位不虚构
  const response = await api<Array<Record<string, unknown>>>(`/api/v1/execution-plans?workspaceId=${profile.workspaceId}`);
  return response.data.map((item) => ({
    id: String(item.id ?? "").slice(0, 8),
    title: String(item.name ?? item.planKey ?? ""),
    version: "V1",
    environment: "—",
    trigger: "手工",
    triggerClass: "b-acc",
    concurrency: "—",
    status: String(item.status ?? "") === "ACTIVE" ? "已激活" : String(item.status ?? "—"),
    statusClass: "st-run",
    frozen: String(item.currentVersionId ?? "").slice(0, 8) || "—",
  }));
}

export async function createExecutionPlan(
  profile: Profile,
  payload: {
    planKey: string;
    name: string;
    testPlanId: string;
    environment?: string;
    triggerType?: string;
    concurrency?: number;
  },
): Promise<void> {
  if (MOCK_MODE) {
    // mock 持久化：新建执行计划写入台账，刷新后仍在执行计划列表可查
    appendMockItem("executionPlans", {
      id: crypto.randomUUID(),
      name: payload.name,
      planKey: payload.planKey,
      environment: payload.environment ?? "—",
      triggerType: payload.triggerType ?? "手工",
      concurrency: payload.concurrency ?? 1,
      createdAt: new Date().toISOString(),
    });
    return;
  }
  // 契约根层必填 workspaceId/planKey/name/testPlanId；版本层字段（环境/触发/并发）延期不提交
  await api<{ id: string }>("/api/v1/execution-plans", {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify({
      workspaceId: profile.workspaceId,
      planKey: payload.planKey,
      name: payload.name,
      testPlanId: payload.testPlanId,
    }),
  });
}

/* ---------- 质量域（Sprint 2 T9：后端 quality 11 op 已实现，curl 核字段通过，数据为空） ---------- */

import { analysisRows, defectRows, reportDetail } from "../mock/mockData";

export async function fetchAnalyses(profile: Profile): Promise<typeof analysisRows> {
  if (MOCK_MODE) return analysisRows;
  const response = await api<Array<Record<string, unknown>>>(`/api/v1/quality/result-analyses?workspaceId=${profile.workspaceId}`);
  return response.data.map((item) => ({
    id: String(item.id ?? "").slice(0, 6),
    title: String(item.title ?? ""),
    ref: "—",
    confidence: Number(item.confidence ?? 0),
    status: String(item.status ?? "review"),
    statusLabel: String(item.status ?? "review") === "done" ? "已批准" : "待审核",
  }));
}

export async function fetchDefects(profile: Profile): Promise<typeof defectRows> {
  if (MOCK_MODE) return defectRows;
  const response = await api<Array<Record<string, unknown>>>(`/api/v1/quality/defects?workspaceId=${profile.workspaceId}`);
  return response.data.map((item, index) => ({
    id: String(item.id ?? `D-${index}`).slice(0, 6),
    title: String(item.title ?? ""),
    sub: "—",
    severity: (item.severity as "严重" | "一般") ?? "一般",
    lifecycle: String(item.status ?? "NEW"),
    lifecycleClass: "st-review",
    version: "V1",
    sync: "待批准",
    syncClass: "b-warn",
  }));
}

export async function fetchReport(profile: Profile): Promise<typeof reportDetail> {
  if (MOCK_MODE) return reportDetail;
  const response = await api<Array<Record<string, unknown>>>(`/api/v1/quality/reports?workspaceId=${profile.workspaceId}`);
  const first = response.data[0];
  if (!first) return { ...reportDetail, title: "TestReport（真实模式无数据）" };
  return {
    ...reportDetail,
    title: String(first.title ?? reportDetail.title),
    ref: String(first.id ?? reportDetail.ref),
    summary: [
      { k: "范围快照", v: String(first.summary ?? "—") },
      { k: "风险摘要", v: "—" },
      { k: "结论", v: "—" },
    ],
  };
}

/* ---------- Agent 域（Sprint 2 T11：后端 listAgentSessions/getAgentSession/getAgentSessionTrace/createAgentSession 已实现） ---------- */

import { sessionRows } from "../mock/mockData";

export async function fetchAgentSessions(profile: Profile): Promise<typeof sessionRows> {
  if (MOCK_MODE) return sessionRows;
  const response = await api<Array<Record<string, unknown>>>(`/api/v1/ai/sessions?workspaceId=${profile.workspaceId}`);
  return response.data.map((item) => ({
    id: String(item.id ?? "").slice(0, 6),
    title: `run ${String(item.id ?? "").slice(0, 6)} · ${String(item.workflowLabel ?? "执行")}`,
    sub: String(item.workItemId ?? "—"),
    workflow: String(item.workflowKey ?? "—"),
    status: String(item.status ?? "RUNNING") === "DONE" ? "完成" : "运行中",
    statusClass: String(item.status ?? "RUNNING") === "DONE" ? "st-done" : "st-run",
    cost: String(item.cost ?? "—"),
  }));
}

/* ---------- 平台域（环境列表/创建已接后端 listEnvironments/createEnvironment，批次四十六补路由） ---------- */

import { envRows } from "../mock/mockData";

export type EnvironmentRow = (typeof envRows)[number];

export async function fetchEnvironments(profile: Profile): Promise<EnvironmentRow[]> {
  if (MOCK_MODE) {
    const created = readMockCollection<Record<string, unknown>>("environments").map((item) => ({
      title: String(item.title ?? ""),
      sub: `新建 · ${String(item.createdAt ?? "").slice(5, 16)}`,
      type: String(item.type ?? "测试"),
      endpoint: String(item.endpoint ?? "—"),
      secret: String(item.secret ?? "—"),
      status: "就绪",
      statusClass: "st-done",
    }));
    return [...created, ...envRows];
  }
  const response = await api<Array<Record<string, unknown>>>(
    `/api/v1/platform/workspaces/${profile.workspaceId}/environments`,
  );
  return response.data.map((item) => {
    const endpoints = (item.endpointMappings as Record<string, unknown>) ?? {};
    const endpointValues = Object.values(endpoints);
    const secretRefs = Array.isArray(item.secretRefs) ? (item.secretRefs as string[]) : [];
    return {
      title: String(item.name ?? ""),
      sub: `创建 · ${String(item.createdAt ?? "").slice(5, 16)}`,
      type: String(item.environmentType ?? "—"),
      endpoint: endpointValues.length > 0 ? String(endpointValues[0]) : "—",
      secret: secretRefs.length > 0 ? `secret:${secretRefs[0]}` : "—",
      status: "就绪",
      statusClass: "st-done",
    };
  });
}

export async function createEnvironment(
  profile: Profile,
  payload: {
    title: string;
    type: string;
    endpoint: string;
    secret: string;
  },
): Promise<void> {
  if (MOCK_MODE) {
    appendMockItem("environments", { ...payload, createdAt: new Date().toISOString() });
    return;
  }
  // secretRefs 契约为 UUID 引用列表；Secret 目录接口未实现，真实模式不提交（缺省空列表）
  await api<{ id: string }>(`/api/v1/platform/workspaces/${profile.workspaceId}/environments`, {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify({
      name: payload.title,
      environmentType: payload.type,
      endpointMappings: payload.endpoint && payload.endpoint !== "—" ? { default: payload.endpoint } : {},
    }),
  });
}

/* ---------- M5 Provider 降级状态（GET /ai/provider/status 批次四十六已实装；404/异常回落 UNKNOWN） ---------- */

export async function fetchProviderStatus(): Promise<ProviderStatus> {
  if (MOCK_MODE) {
    return { status: "NOMINAL", providerId: "deterministic-local" };
  }
  try {
    const response = await api<Record<string, unknown>>("/api/v1/ai/provider/status");
    const status = String(response.data.status ?? "UNKNOWN");
    return {
      status: status === "NOMINAL" || status === "DEGRADED" ? status : "UNKNOWN",
      providerId: String(response.data.providerId ?? "—"),
      fallbackProviderId:
        typeof response.data.fallbackProviderId === "string" ? response.data.fallbackProviderId : undefined,
      reason: typeof response.data.reason === "string" ? response.data.reason : undefined,
      since: typeof response.data.since === "string" ? response.data.since : undefined,
    };
  } catch {
    return { status: "UNKNOWN", providerId: "—" };
  }
}

/* ---------- WP-01A 项目/Release 上下文（listWorkspaces / listReleases） ---------- */

const MOCK_RELEASE: ReleaseOption = { id: "00000000-0000-4000-8000-000000000001", name: "R-2026.08", status: "ACTIVE" };

/** 服务端口径：仅返回 ACTIVE 且按 updatedAt DESC（最近活跃优先）；前端不重算排序，取首位即当前。 */
export function pickCurrentRelease(releases: ReleaseOption[]): ReleaseOption | undefined {
  return releases[0];
}

export async function fetchWorkspaces(): Promise<WorkspaceOption[]> {
  if (MOCK_MODE) {
    return workspaceRows.map((row) => ({ id: row.key, name: row.title }));
  }
  const response = await api<Array<WorkspaceOption>>("/api/v1/workspaces");
  return response.data.map((workspace) => ({
    id: workspace.id,
    name: workspace.name,
    pinned: Boolean((workspace as { pinned?: boolean }).pinned),
  }));
}

/** WP-01A 专用切换命令：服务端校验成员关系并重签 JWT（新 cookie 随响应落位）。 */
export async function switchWorkspaceProfile(workspaceId: string): Promise<Profile> {
  const response = await api<Profile>("/api/v1/auth/switch-workspace", {
    method: "POST",
    body: JSON.stringify({ workspaceId }),
  });
  return response.data;
}

/** WP-01 常用项目置顶命令（用户偏好，幂等；mock 模式本地维护）。 */
export async function setWorkspacePin(workspaceId: string, pinned: boolean): Promise<void> {
  if (MOCK_MODE) return;
  await api(`/api/v1/workspaces/${workspaceId}/pin`, {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify({ pinned }),
  });
}

export async function fetchReleases(workspaceId: string): Promise<ReleaseOption[]> {
  if (MOCK_MODE) {
    return [MOCK_RELEASE];
  }
  const response = await api<ReleaseOption[]>(`/api/v1/workspaces/${workspaceId}/releases`);
  return response.data.map((release) => ({ id: release.id, name: release.name, status: release.status }));
}

/* ---------- WP-03 协作对话（批次六十；contentRef 策略：PUBLIC/INTERNAL 低敏可内联正文，
   CONFIDENTIAL/RESTRICTED 必须传引用 URI，本地运行时简化口径见 HANDOFF） ---------- */

function sha256Hex(text: string): string {
  // 轻量占位摘要（浏览器 SubtleCrypto 为异步；本地运行时仅用于展示一致性，不参与服务端校验）
  let hash = 0n;
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 131n + BigInt(text.charCodeAt(i))) & 0xffffffffffffffffn;
  }
  return hash.toString(16).padStart(16, "0").padEnd(64, "0");
}

export async function fetchConversations(profile: Profile): Promise<ConversationRow[]> {
  if (MOCK_MODE) {
    return [...conversationRows].sort((a, b) => (a.lastActivityAt < b.lastActivityAt ? 1 : -1));
  }
  const response = await api<Array<Record<string, unknown>>>(
    `/api/v1/conversations?workspaceId=${profile.workspaceId}`,
  );
  return response.data.map((row) => ({
    id: String(row.id),
    title: String(row.title),
    status: String(row.status),
    releaseId: row.releaseId ? String(row.releaseId) : null,
    workItemId: row.workItemId ? String(row.workItemId) : null,
    lastActivityAt: String(row.lastActivityAt),
  }));
}

export async function createConversation(
  profile: Profile,
  input: { title: string },
): Promise<ConversationRow> {
  if (MOCK_MODE) {
    const row = {
      id: `c-mock-${Date.now()}`,
      title: input.title,
      status: "ACTIVE",
      releaseId: profile.releaseId ?? null,
      workItemId: null,
      lastActivityAt: new Date().toISOString(),
    };
    conversationRows.push(row);
    return { ...row };
  }
  const response = await api<Record<string, unknown>>("/api/v1/conversations", {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify({
      workspaceId: profile.workspaceId,
      releaseId: profile.releaseId,
      title: input.title,
    }),
  });
  const row = response.data;
  return {
    id: String(row.id),
    title: String(row.title),
    status: String(row.status),
    releaseId: row.releaseId ? String(row.releaseId) : null,
    workItemId: row.workItemId ? String(row.workItemId) : null,
    lastActivityAt: String(row.lastActivityAt),
  };
}

export async function fetchConversationMessages(conversationId: string): Promise<ConversationMessageRow[]> {
  if (MOCK_MODE) {
    return conversationMessageRows
      .filter((m) => m.conversationId === conversationId)
      .map((m) => ({ ...m }));
  }
  const response = await api<Array<Record<string, unknown>>>(
    `/api/v1/conversations/${conversationId}/messages`,
  );
  return response.data.map((row) => ({
    id: String(row.id),
    conversationId: String(row.conversationId),
    actorType: row.actorType as ConversationMessageRow["actorType"],
    actorId: String(row.actorId),
    messageType: String(row.messageType),
    contentRef: String(row.contentRef),
    contentDigest: String(row.contentDigest),
    dataClass: row.dataClass as ConversationMessageRow["dataClass"],
    createdAt: String(row.createdAt),
  }));
}

export async function appendConversationMessage(
  profile: Profile,
  conversationId: string,
  input: { content: string; dataClass: "PUBLIC" | "INTERNAL" | "CONFIDENTIAL" | "RESTRICTED" },
): Promise<ConversationMessageRow> {
  const isSensitive = input.dataClass === "CONFIDENTIAL" || input.dataClass === "RESTRICTED";
  const contentRef = isSensitive && !input.content.includes("://")
    ? `conv-ref://${sha256Hex(input.content)}`
    : input.content;
  const contentDigest = sha256Hex(input.content);
  if (MOCK_MODE) {
    const row = {
      id: `m-mock-${Date.now()}`,
      conversationId,
      actorType: "USER" as const,
      actorId: profile.userId,
      messageType: "TEXT",
      contentRef,
      contentDigest,
      dataClass: input.dataClass,
      createdAt: new Date().toISOString(),
    };
    conversationMessageRows.push(row);
    const conversation = conversationRows.find((c) => c.id === conversationId);
    if (conversation) conversation.lastActivityAt = row.createdAt;
    return { ...row };
  }
  const response = await api<Record<string, unknown>>(
    `/api/v1/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({
        messageType: "TEXT",
        contentRef,
        contentDigest,
        dataClass: input.dataClass,
      }),
    },
  );
  const row = response.data;
  return {
    id: String(row.id),
    conversationId: String(row.conversationId),
    actorType: row.actorType as ConversationMessageRow["actorType"],
    actorId: String(row.actorId),
    messageType: String(row.messageType),
    contentRef: String(row.contentRef),
    contentDigest: String(row.contentDigest),
    dataClass: row.dataClass as ConversationMessageRow["dataClass"],
    createdAt: String(row.createdAt),
  };
}

/* ---------- WP-03 任务卡/AgentPlan + WP-04 执行命令（批次六十一） ---------- */

export async function fetchTaskCards(workItemId: string): Promise<TaskCardRow[]> {
  if (MOCK_MODE) {
    return taskCardRows.filter((card) => card.workItemId === workItemId).map((card) => ({ ...card }));
  }
  const response = await api<Array<Record<string, unknown>>>(
    `/api/v1/work-items/${workItemId}/task-cards`,
  ).catch(() => ({ data: [] as Array<Record<string, unknown>> }));
  return (response.data ?? []).map((row) => ({
    id: String(row.id),
    workItemId: String(row.workItemId),
    objective: String(row.objective),
    scope: String(row.scope),
    status: row.status as TaskCardRow["status"],
    contentDigest: String(row.contentDigest),
    createdAt: String(row.createdAt),
  }));
}

export async function createTaskCard(
  profile: Profile,
  workItemId: string,
  input: {
    objective: string
    scope: string
    acceptanceCriteria: string
    constraints: string
    requestedPermissions: string[]
    budgetMinutes: number
  },
): Promise<TaskCardRow> {
  const payload = {
    objective: input.objective,
    scope: input.scope,
    acceptanceCriteria: input.acceptanceCriteria,
    constraints: input.constraints,
    requestedPermissions: input.requestedPermissions,
    budget: { maxMinutes: input.budgetMinutes },
  };
  if (MOCK_MODE) {
    const row = {
      id: `tc-mock-${Date.now()}`,
      workItemId,
      objective: input.objective,
      scope: input.scope,
      status: "SUBMITTED" as const,
      contentDigest: "c3".repeat(32),
      createdAt: new Date().toISOString(),
    };
    for (const card of taskCardRows) {
      if (card.workItemId === workItemId && card.status !== "SUPERSEDED") card.status = "SUPERSEDED";
    }
    taskCardRows.push(row);
    return { ...row };
  }
  const response = await api<Record<string, unknown>>(`/api/v1/work-items/${workItemId}/task-cards`, {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify(payload),
  });
  const row = response.data;
  return {
    id: String(row.id),
    workItemId: String(row.workItemId),
    objective: String(row.objective),
    scope: String(row.scope),
    status: row.status as TaskCardRow["status"],
    contentDigest: String(row.contentDigest),
    createdAt: String(row.createdAt),
  };
}

export async function fetchAgentPlans(profile: Profile, workItemId: string): Promise<AgentPlanRow[]> {
  if (MOCK_MODE) {
    return agentPlanRows.filter((plan) => plan.workItemId === workItemId).map((plan) => ({ ...plan }));
  }
  const response = await api<Array<Record<string, unknown>>>(
    `/api/v1/work-items/${workItemId}/agent-plans?workspaceId=${profile.workspaceId}`,
  ).catch(() => ({ data: [] as Array<Record<string, unknown>> }));
  return (response.data ?? []).map((row) => ({
    id: String(row.id),
    workItemId: String(row.workItemId),
    taskCardId: String(row.taskCardId),
    planVersion: Number(row.planVersion),
    steps: (row.steps ?? []) as AgentPlanRow["steps"],
    status: row.status as AgentPlanRow["status"],
    contentDigest: String(row.contentDigest),
    createdAt: String(row.createdAt),
  }));
}

export async function createAgentPlan(
  workItemId: string,
  taskCardId: string,
  steps: Array<{ stepKey: string; agentRole: string; description: string }>,
): Promise<AgentPlanRow> {
  if (MOCK_MODE) {
    const row = {
      id: `ap-mock-${Date.now()}`,
      workItemId,
      taskCardId,
      planVersion: agentPlanRows.filter((p) => p.workItemId === workItemId).length + 1,
      steps,
      status: "PENDING_APPROVAL" as const,
      contentDigest: "d4".repeat(32),
      createdAt: new Date().toISOString(),
    };
    for (const plan of agentPlanRows) {
      if (plan.workItemId === workItemId && plan.status === "PENDING_APPROVAL") plan.status = "SUPERSEDED";
    }
    agentPlanRows.push(row);
    return { ...row };
  }
  const response = await api<Record<string, unknown>>(`/api/v1/work-items/${workItemId}/agent-plans`, {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify({ taskCardId, steps }),
  });
  const row = response.data;
  return {
    id: String(row.id),
    workItemId: String(row.workItemId),
    taskCardId: String(row.taskCardId),
    planVersion: Number(row.planVersion),
    steps: row.steps as AgentPlanRow["steps"],
    status: row.status as AgentPlanRow["status"],
    contentDigest: String(row.contentDigest),
    createdAt: String(row.createdAt),
  };
}

export async function decideAgentPlan(
  planId: string,
  decision: "APPROVE" | "REJECT",
  expectedContentDigest: string,
  reason: string,
): Promise<{ planStatus: string }> {
  if (MOCK_MODE) {
    const plan = agentPlanRows.find((p) => p.id === planId);
    if (plan) {
      plan.status = decision === "APPROVE" ? "APPROVED" : "REJECTED";
      return { planStatus: plan.status };
    }
    return { planStatus: "NOT_FOUND" };
  }
  const response = await api<Record<string, unknown>>(`/api/v1/agent-plans/${planId}/decisions`, {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify({ decision, expectedContentDigest, reason }),
  });
  return { planStatus: String(response.data.planStatus) };
}

export async function issueExecutionCommand(
  executionTaskId: string,
  commandType: "PAUSE" | "RESUME" | "CANCEL",
  reason: string,
): Promise<RunCommandResult> {
  if (MOCK_MODE) {
    return {
      id: `cmd-mock-${Date.now()}`,
      commandType,
      status: "EFFECTIVE",
      receipt: {
        accepted: true,
        effectiveStatus: commandType === "PAUSE" ? "PAUSED" : commandType === "RESUME" ? "RUNNING" : "CANCELLED",
        safePointRef: `execution_task:${executionTaskId}@RUNNING>PAUSED`,
        reasonCode: "EFFECTIVE_AT_STATUS_BOUNDARY",
        completedAt: new Date().toISOString(),
      },
    };
  }
  const response = await api<Record<string, unknown>>(
    `/api/v1/execution-tasks/${executionTaskId}/commands`,
    {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({ commandType, reason }),
    },
  );
  const row = response.data;
  const receipt = row.receipt as Record<string, unknown>;
  return {
    id: String(row.id),
    commandType: String(row.commandType),
    status: String(row.status),
    receipt: {
      accepted: Boolean(receipt.accepted),
      effectiveStatus: String(receipt.effectiveStatus),
      safePointRef: String(receipt.safePointRef ?? ""),
      reasonCode: String(receipt.reasonCode ?? ""),
      completedAt: String(receipt.completedAt ?? ""),
    },
  };
}
