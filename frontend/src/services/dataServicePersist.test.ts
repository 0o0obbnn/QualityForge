import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * mock 本地持久化验证（deep_delivery 验收标准「数据记录可追踪」）。
 * MOCK_MODE 在模块加载时求值，这里用 vi.stubEnv + vi.resetModules 动态加载 mock 分支。
 */

async function loadMockService() {
  vi.stubEnv("VITE_MOCK", "1");
  vi.resetModules();
  return import("./dataService");
}

const profile = { workspaceId: "ws-test" } as never;

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("mock 持久化台账", () => {
  it("createWorkItem 提交后在看板列表可查，且重新加载模块（模拟刷新）后记录不丢", async () => {
    const ds = await loadMockService();
    await ds.createWorkItem(profile, {
      title: "验收样例：退款场景用例",
      description: "持久化验收描述",
      workItemType: "用例",
      priority: "P1",
    });
    const rows = await ds.fetchBoardRows(profile);
    expect(rows.some((r) => r.title === "验收样例：退款场景用例")).toBe(true);

    // 模拟刷新：重新加载模块（新模块实例读同一 localStorage）
    vi.resetModules();
    const ds2 = await import("./dataService");
    const rows2 = await ds2.fetchBoardRows(profile);
    expect(rows2.some((r) => r.title === "验收样例：退款场景用例")).toBe(true);
  });

  it("createExecutionPlan 提交后在执行计划列表可查，且刷新后不丢", async () => {
    const ds = await loadMockService();
    await ds.createExecutionPlan(profile, {
      planKey: "EP-0819-42",
      name: "结算回归批次",
      testPlanId: "tp-test",
      environment: "staging",
      triggerType: "手工",
      concurrency: 4,
    });
    const plans = await ds.fetchExecutionPlans(profile);
    expect(plans.some((p) => p.environment === "staging" && p.status === "未启动")).toBe(true);

    vi.resetModules();
    const ds2 = await import("./dataService");
    const plans2 = await ds2.fetchExecutionPlans(profile);
    expect(plans2.some((p) => p.environment === "staging" && p.status === "未启动")).toBe(true);
  });

  it("submitReviewDecision 写入决定台账，可读取且刷新后不丢", async () => {
    const ds = await loadMockService();
    await ds.submitReviewDecision("rt-test", "APPROVE", "digest-abc123", "同意");
    expect(ds.readMockDecisions().length).toBe(1);
    expect(ds.readMockDecisions()[0]).toMatchObject({ taskId: "rt-test", decision: "APPROVE" });

    vi.resetModules();
    const ds2 = await import("./dataService");
    expect(ds2.readMockDecisions().length).toBe(1);
    expect(ds2.readMockDecisions()[0]).toMatchObject({ decision: "APPROVE" });
  });

  it("resetMockStore 清空台账后列表回到基线数据", async () => {
    const ds = await loadMockService();
    await ds.createWorkItem(profile, { title: "临时项", workItemType: "计划", priority: "P2" });
    const before = await ds.fetchBoardRows(profile);
    expect(before.some((r) => r.title === "临时项")).toBe(true);

    ds.resetMockStore();
    const after = await ds.fetchBoardRows(profile);
    expect(after.some((r) => r.title === "临时项")).toBe(false);
  });
});
