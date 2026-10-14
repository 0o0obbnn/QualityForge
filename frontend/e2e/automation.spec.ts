import { expect, test } from "@playwright/test";

/**
 * 自动化工作台冒烟（mock 模式）：脚本列表/代码审核/配套资产三页（Sprint 2 T7）。
 */

test.describe("自动化工作台（mock 模式）", () => {
  test("自动化工作台页：脚本列表 + 三张规范卡片", async ({ page }) => {
    await page.goto("/automation/scripts");
    await expect(page.getByRole("heading", { name: "自动化工作台", exact: true })).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(3);
    await expect(page.getByText("settlement_api_flow.py")).toBeVisible();
    await expect(page.getByText("8 个 TestCaseVersion")).toBeVisible();
    await expect(page.getByText("待代码审核").first()).toBeVisible();
    // 三张卡片
    await expect(page.getByText("用例绑定").first()).toBeVisible();
    await expect(page.getByText("代码检查").first()).toBeVisible();
    await expect(page.getByText("Secret 隔离")).toBeVisible();
    await expect(page.getByText("检查 PASS 不替代代码批准")).toBeVisible();
  });

  test("代码审核页：Diff 增删行 + 检查结果 + 审核信息", async ({ page }) => {
    await page.goto("/automation/code-review");
    await expect(page.getByRole("heading", { name: "settlement_api_flow.py · V2" })).toBeVisible();
    await expect(page.getByText("代码 Diff")).toBeVisible();
    await expect(page.getByText("def test_refund_idempotency(api):")).toBeVisible();
    await expect(page.getByText("返回首次结果").first()).toBeVisible();
    await expect(page.getByText("契约绑定 · 22 个 operation 引用一致")).toBeVisible();
    await expect(page.getByText("阻断项不可人工放行")).toBeVisible();
    await expect(page.getByText("RT-4841").first()).toBeVisible();
    await expect(page.getByText("CODE_REVIEW").first()).toBeVisible();
  });

  test("配套资产页：四 Tab 切换（Locator/Mock/数据/视觉）", async ({ page }) => {
    await page.goto("/automation/assets");
    await expect(page.getByRole("heading", { name: "配套资产", exact: true })).toBeVisible();
    // Locator 默认
    await expect(page.getByText("checkout-submit-btn")).toBeVisible();
    await expect(page.getByText("DECAYING")).toBeVisible();
    await expect(page.getByText("#checkout-submit")).toBeVisible();
    // Mock Tab
    await page.getByRole("tab", { name: "Mock 配置" }).click();
    await expect(page.getByText("gw-timeout-mock")).toBeVisible();
    await expect(page.getByText("header[x-mock]=timeout")).toBeVisible();
    // 测试数据 Tab（空态）
    await page.getByRole("tab", { name: "测试数据" }).click();
    await expect(page.getByText("暂无测试数据资产")).toBeVisible();
    // 视觉基线 Tab（空态）
    await page.getByRole("tab", { name: "视觉基线" }).click();
    await expect(page.getByText("暂无视觉基线资产")).toBeVisible();
  });

  test("侧栏「自动化工作台」入口指向脚本页", async ({ page }) => {
    await page.goto("/");
    await page.locator(".sidebar .nav-item", { hasText: "自动化工作台" }).click();
    await expect(page).toHaveURL(/\/automation\/scripts/);
    await expect(page.getByRole("heading", { name: "自动化工作台", exact: true })).toBeVisible();
  });
});
