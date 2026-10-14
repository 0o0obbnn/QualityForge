import { expect, test } from "@playwright/test";

/**
 * M4 质量中心冒烟（mock 模式）：结果分析、Defect、报告与门禁三视图。
 */

test.describe("M4 质量中心（mock 模式）", () => {
  test("结果分析页：AI 标签 + 置信度 + 失败聚类侧栏", async ({ page }) => {
    await page.goto("/quality/analyses");
    await expect(page.getByRole("heading", { name: "结果分析" })).toBeVisible();
    await expect(page.getByText("重复回调 order_no 不一致")).toBeVisible();
    await expect(page.getByText("0.72")).toBeVisible();
    await expect(page.getByText("失败聚类 FC-08")).toBeVisible();
    await expect(page.getByText("聚类≠Defect")).toBeVisible();
  });

  test("Defect 页：列表 + 严重度筛选", async ({ page }) => {
    await page.goto("/quality/defects");
    await expect(page.getByRole("heading", { name: "Defect", exact: true })).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(3);
    // 筛选严重
    await page.getByRole("button", { name: "严重", exact: true }).click();
    await expect(page.locator("tbody tr")).toHaveCount(2);
    // 筛选已同步
    await page.getByRole("button", { name: "已同步", exact: true }).click();
    await expect(page.locator("tbody tr")).toHaveCount(1);
    await expect(page.getByText("已同步 JIRA")).toBeVisible();
  });

  test("报告与门禁页：KPI 3 卡 + 门禁建议", async ({ page }) => {
    await page.goto("/quality/reports");
    await expect(page.getByRole("heading", { name: "报告与门禁" })).toBeVisible();
    await expect(page.locator(".kpi")).toHaveCount(3);
    await expect(page.getByText("96.1%")).toBeVisible();
    await expect(page.getByText("建议有条件放行,网关故障注入待补测")).toBeVisible();
    await expect(page.getByText("门禁: 核心通过率 ≥ 95%")).toBeVisible();
    await expect(page.getByText("未达标")).toBeVisible();
  });

  test("侧栏「质量中心」入口指向结果分析页", async ({ page }) => {
    await page.goto("/");
    await page.locator(".sidebar .nav-item", { hasText: "质量中心" }).click();
    await expect(page).toHaveURL(/\/quality\/analyses/);
    await expect(page.getByRole("heading", { name: "结果分析" })).toBeVisible();
  });
});
