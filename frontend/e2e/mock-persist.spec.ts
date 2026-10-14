import { expect, test } from "@playwright/test";

/**
 * mock 持久化 e2e 验收（deep_delivery 标准「数据记录可追踪」）：
 * 页面上真实提交 → 断言出现在列表 → 刷新页面 → 记录仍在 → 清空台账恢复基线。
 * 执行计划创建入口在前端尚未实现表单弹窗（跳转执行监控页），
 * 其持久化依赖 createExecutionPlan 调用（vitest 已覆盖），此处仅做看板工作项页面级实测。
 */

test.describe("mock 持久化关键路径（页面级实测）", () => {
  test("看板新建工作项 → 列表可见 → 刷新不丢 → 台账可清空", async ({ page }) => {
    await page.goto("/board");
    // 清空历史台账，保证基线一致
    await page.evaluate(() => window.localStorage.removeItem("qf_mock_store"));

    // 新建工作项（视图 6 全部工作项的新建弹窗）
    await page.getByText("全部工作项").click();
    const newBtn = page.locator('button:has-text("新建")').first();
    await newBtn.click();
    const title = `验收样例-${Date.now().toString().slice(-6)}`;
    await page.locator('input[name="title"]').fill(title);
    await page.getByRole("button", { name: "创建", exact: true }).click();
    await expect(page.locator(".toast, [class*=toast]").first()).toBeVisible();

    // 列表可见
    await expect(page.getByText(title).first()).toBeVisible();

    // 刷新后记录仍在
    await page.reload();
    await page.getByText("全部工作项").click();
    await expect(page.getByText(title).first()).toBeVisible();

    // localStorage 台账可查
    const store = await page.evaluate(() => JSON.parse(window.localStorage.getItem("qf_mock_store") ?? "{}"));
    expect(store.workItems?.some((item: { title?: string }) => item.title === title)).toBe(true);
  });

  test("看板新建第二个工作项 → 与第一个独立记录 → 刷新后两条都在", async ({ page }) => {
    await page.goto("/board");
    await page.evaluate(() => window.localStorage.removeItem("qf_mock_store"));
    await page.reload();
    await page.getByText("全部工作项").click();

    const ts = Date.now();
    const titles = [`A-${ts.toString().slice(-6)}`, `B-${ts.toString().slice(-5)}`];
    for (const t of titles) {
      await page.locator('button:has-text("新建")').first().click();
      await page.locator('input[name="title"]').fill(t);
      await page.getByRole("button", { name: "创建", exact: true }).click();
      await expect(page.locator(".toast, [class*=toast]").first()).toBeVisible();
    }

    await page.reload();
    await page.getByText("全部工作项").click();
    for (const t of titles) {
      await expect(page.getByText(t).first()).toBeVisible();
    }

    const store = await page.evaluate(() => JSON.parse(window.localStorage.getItem("qf_mock_store") ?? "{}"));
    expect(store.workItems?.length).toBe(2);
  });
});
