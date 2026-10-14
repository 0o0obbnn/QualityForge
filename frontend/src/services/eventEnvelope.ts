/**
 * 事件信封与轮询去重（对齐 docs/36 §3 通用事件信封 + §4 ExecutionTask Stream）。
 * 纯函数层，vitest 守护：eventId 去重、sequence 缺口检测、终态判定。
 */

export interface EventEnvelope {
  schemaVersion: string;
  eventId: string;
  type: string;
  sequence: number;
  /** docs/36 §3：服务端稳定补发游标；客户端不得解析内部格式，仅保存用于 lastOffset 重连 */
  offset?: string;
  tenantId?: string;
  workspaceId?: string;
  resourceType: string;
  resourceId: string;
  occurredAt: string;
  traceId?: string;
  data: Record<string, unknown>;
}

export type ExecutionTaskStatus =
  | "PENDING"
  | "QUEUED"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | "TIMED_OUT"
  | "BLOCKED";

/** docs/36 §4：终态——轮询渲染到此即停 */
export const TERMINAL_STATUSES: ReadonlySet<ExecutionTaskStatus> = new Set([
  "COMPLETED",
  "FAILED",
  "CANCELLED",
  "TIMED_OUT",
]);

export function isTerminal(status: string): boolean {
  return TERMINAL_STATUSES.has(status as ExecutionTaskStatus);
}

/**
 * 合并一批事件：按 eventId 去重，按 sequence 检测单资源缺口。
 * 返回 { merged, gaps }：gaps 为每个资源缺失的 sequence 区间描述。
 */
export function mergeEvents(
  existing: EventEnvelope[],
  incoming: EventEnvelope[],
): { merged: EventEnvelope[]; gaps: Array<{ resourceId: string; missing: number[] }> } {
  const byId = new Map<string, EventEnvelope>();
  for (const event of existing) byId.set(event.eventId, event);
  for (const event of incoming) {
    if (!byId.has(event.eventId)) byId.set(event.eventId, event);
  }
  const merged = [...byId.values()].sort(
    (a, b) => Date.parse(a.occurredAt) - Date.parse(b.occurredAt),
  );

  // 按资源检测 sequence 缺口
  const seqByResource = new Map<string, number[]>();
  for (const event of merged) {
    const list = seqByResource.get(event.resourceId) ?? [];
    list.push(event.sequence);
    seqByResource.set(event.resourceId, list);
  }
  const gaps: Array<{ resourceId: string; missing: number[] }> = [];
  for (const [resourceId, seqs] of seqByResource) {
    const sorted = [...seqs].sort((a, b) => a - b);
    const missing: number[] = [];
    for (let index = 1; index < sorted.length; index += 1) {
      for (let seq = sorted[index - 1] + 1; seq < sorted[index]; seq += 1) missing.push(seq);
    }
    if (missing.length > 0) gaps.push({ resourceId, missing });
  }
  return { merged, gaps };
}
