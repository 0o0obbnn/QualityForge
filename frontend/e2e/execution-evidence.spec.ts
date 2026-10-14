import { expect, test } from "@playwright/test";

/**
 * M3 执行与证据页冒烟（mock 模式）：
 * 执行监控页（轮询事件流、终态即停、任务列表）、证据审核页（断言明细/digest/attempt 历史）。
 */

test.describe("M3 执行监控与证据（mock 模式）", () => {
  test("执行监控页：KPI 4 卡 + 任务列表 4 行 + 状态/结果徽章", async ({ page }) => {
    await page.goto("/execution-monitor");
    await expect(page.getByRole("heading", { name: "执行监控" })).toBeVisible();
    await expect(page.locator(".kpi")).toHaveCount(4);
    const rows = page.locator("tbody tr");
    await expect(rows).toHaveCount(4);
    await expect(page.getByText("TC-0221 支付成功回调")).toBeVisible();
    await expect(page.getByText("COMPLETED")).toBeVisible();
    await expect(page.locator("tbody").getByText("PASSED", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("settlement_api_flow V2").first()).toBeVisible();
  });

  test("执行监控页：事件流轮询渲染（mock 2s 追加）", async ({ page }) => {
    await page.goto("/execution-monitor");
    const stream = page.getByTestId("event-stream");
    await expect(stream).toContainText("EX-T-3181 COMPLETED");
    // mock 每 2s 追加一批，等待结果事件
    await expect(stream).toContainText("result=PASSED", { timeout: 6000 });
    // 终态后显示结束标记
    await expect(page.getByText("事件流已结束（终态）")).toBeVisible({ timeout: 6000 });
  });

  test("执行监控页：点击任务行跳转证据页", async ({ page }) => {
    await page.goto("/execution-monitor");
    await page.locator("tbody tr").first().click();
    await expect(page).toHaveURL(/\/evidence\//);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("TC-0225 重复回调幂等");
  });

  test("证据页：断言明细 3/4 通过 + digest 展示 + attempt 历史", async ({ page }) => {
    await page.goto("/evidence/EX-T-3185");
    await expect(page.getByText("3/4 通过 · 1 失败")).toBeVisible();
    await expect(page.getByText("重复回调返回首次结果")).toBeVisible();
    await expect(page.getByText("sha256:44b2…f01d")).toBeVisible();
    await expect(page.getByText("#2", { exact: true })).toBeVisible();
    await expect(page.getByText("FAILED · 断言 #4")).toBeVisible();
    await expect(page.getByText("ExecutionResult 只追加").first()).toBeVisible();
  });

  test("侧栏「测试执行」入口指向执行监控页", async ({ page }) => {
    await page.goto("/");
    await page.locator(".sidebar .nav-item", { hasText: "测试执行" }).click();
    await expect(page).toHaveURL(/\/execution-monitor/);
    await expect(page.getByRole("heading", { name: "执行监控" })).toBeVisible();
  });
});
