import { expect, test } from "@playwright/test";

/**
 * 知识库模块冒烟（mock 模式）：来源与需求、API 契约、知识库三页。
 */

test.describe("知识库模块（mock 模式）", () => {
  test("来源与需求页：三 Tab 切换", async ({ page }) => {
    await page.goto("/knowledge/sources");
    await expect(page.getByRole("heading", { name: "来源与需求" })).toBeVisible();
    // 来源快照 tab 默认
    await expect(page.getByText("结算中心需求规格 v2.1.docx")).toBeVisible();
    await expect(page.getByText("SS-2026-08-11-003")).toBeVisible();
    // 切需求文档
    await page.getByRole("tab", { name: "需求文档" }).click();
    await expect(page.getByText("32 项需求")).toBeVisible();
    await expect(page.getByText("REQ-2026-08-11")).toBeVisible();
    // 切冲突
    await page.getByRole("tab", { name: /冲突/ }).click();
    await expect(page.getByText("DECLARED vs OBSERVED 冲突")).toBeVisible();
    await expect(page.getByText("需人工裁决")).toBeVisible();
  });

  test("API 契约页：契约列表 + Operation 列表 + 基线侧栏", async ({ page }) => {
    await page.goto("/knowledge/contracts");
    await expect(page.getByRole("heading", { name: "API 契约" })).toBeVisible();
    await expect(page.locator("tbody").getByText("settlement-api", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("reconciliation-api").first()).toBeVisible();
    await expect(page.getByRole("cell", { name: "/settlements/{id}", exact: true })).toBeVisible();
    await expect(page.getByText("Release 契约基线")).toBeVisible();
    await expect(page.getByText("1 处 breaking")).toBeVisible();
  });

  test("知识库页：检索过滤 + 条目列表", async ({ page }) => {
    await page.goto("/knowledge/entries");
    await expect(page.getByRole("heading", { name: "知识库" })).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(4);
    // 检索过滤
    await page.fill('input[aria-label="知识库检索"]', "幂等");
    await expect(page.locator("tbody tr")).toHaveCount(2);
    await expect(page.getByText("支付幂等模式")).toBeVisible();
    await expect(page.getByText("退款幂等键规范")).toBeVisible();
    // 检索无结果
    await page.fill('input[aria-label="知识库检索"]', "不存在的词xyz");
    await expect(page.getByText("没有匹配的条目")).toBeVisible();
  });

  test("侧栏「知识与契约」入口指向来源页", async ({ page }) => {
    await page.goto("/");
    await page.locator(".sidebar .nav-item", { hasText: "知识与契约" }).click();
    await expect(page).toHaveURL(/\/knowledge\/sources/);
    await expect(page.getByRole("heading", { name: "来源与需求" })).toBeVisible();
  });
});
