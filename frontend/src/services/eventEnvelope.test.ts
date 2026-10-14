import { describe, expect, it } from "vitest";

import {
  isTerminal,
  mergeEvents,
  TERMINAL_STATUSES,
  type EventEnvelope,
} from "./eventEnvelope";

/**
 * docs/36 §3 事件信封 + §4 ExecutionTask Stream 契约测试：
 * eventId 去重、sequence 缺口检测、终态判定。
 */

function envelope(partial: Partial<EventEnvelope>): EventEnvelope {
  return {
    schemaVersion: "1.0",
    eventId: "ev-0",
    type: "ExecutionTaskStatusChanged",
    sequence: 1,
    resourceType: "EXECUTION_TASK",
    resourceId: "EX-T-1",
    occurredAt: "2026-08-18T10:00:00Z",
    data: {},
    ...partial,
  };
}

describe("eventEnvelope 终态判定", () => {
  it("COMPLETED/FAILED/CANCELLED/TIMED_OUT 为终态", () => {
    for (const status of TERMINAL_STATUSES) {
      expect(isTerminal(status)).toBe(true);
    }
  });

  it("RUNNING/PENDING/QUEUED/BLOCKED 非终态", () => {
    expect(isTerminal("RUNNING")).toBe(false);
    expect(isTerminal("PENDING")).toBe(false);
    expect(isTerminal("QUEUED")).toBe(false);
    expect(isTerminal("BLOCKED")).toBe(false);
  });
});

describe("eventEnvelope 合并去重与缺口检测", () => {
  it("按 eventId 去重：重复事件只保留一次", () => {
    const a = envelope({ eventId: "ev-1", sequence: 1 });
    const aDup = envelope({ eventId: "ev-1", sequence: 1 });
    const { merged } = mergeEvents([a], [aDup]);
    expect(merged).toHaveLength(1);
  });

  it("sequence 连续：无缺口", () => {
    const existing = [
      envelope({ eventId: "ev-1", sequence: 1, resourceId: "EX-1" }),
      envelope({ eventId: "ev-2", sequence: 2, resourceId: "EX-1" }),
    ];
    const incoming = [envelope({ eventId: "ev-3", sequence: 3, resourceId: "EX-1" })];
    const { merged, gaps } = mergeEvents(existing, incoming);
    expect(merged).toHaveLength(3);
    expect(gaps).toHaveLength(0);
  });

  it("sequence 缺口：检测并报告缺失序号", () => {
    const existing = [envelope({ eventId: "ev-1", sequence: 1, resourceId: "EX-1" })];
    const incoming = [envelope({ eventId: "ev-3", sequence: 3, resourceId: "EX-1" })];
    const { merged, gaps } = mergeEvents(existing, incoming);
    expect(merged).toHaveLength(2);
    expect(gaps).toEqual([{ resourceId: "EX-1", missing: [2] }]);
  });

  it("多资源各自独立检测缺口", () => {
    const events = [
      envelope({ eventId: "a1", sequence: 1, resourceId: "EX-A" }),
      envelope({ eventId: "a3", sequence: 3, resourceId: "EX-A" }),
      envelope({ eventId: "b1", sequence: 1, resourceId: "EX-B" }),
      envelope({ eventId: "b2", sequence: 2, resourceId: "EX-B" }),
    ];
    const { gaps } = mergeEvents([], events);
    expect(gaps).toContainEqual({ resourceId: "EX-A", missing: [2] });
    expect(gaps).toHaveLength(1);
  });
});
