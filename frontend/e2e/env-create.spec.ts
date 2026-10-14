import { expect, test } from "@playwright/test";

/**
 * 新建环境持久化 e2e（核验 P0-2 修复验收）：
 * 提交后列表立即可见 + toast 成功 + 刷新后记录不丢 + 校验失败可见错误。
 */

test.describe("新建环境提交闭环（P0-2 修复验收）", () => {
  test("新建环境 → 列表可见 → 刷新不丢", async ({ page }) => {
    await page.goto("/platform/environments");
    await page.evaluate(() => window.localStorage.removeItem("qf_mock_store"));
    await page.reload();

    const envName = `e2e-env-${Date.now().toString().slice(-6)}`;
    await page.getByRole("button", { name: "新建环境", exact: true }).click();
    await page.locator('.modal-box input[placeholder="例如: pre-prod"], .modal-box input.input').first().fill(envName);
    await page.getByRole("button", { name: "创建", exact: true }).click();
    await expect(page.locator(".toast, [class*=toast]").first()).toBeVisible();

    // 列表立即可见
    await expect(page.getByText(envName).first()).toBeVisible();

    // 刷新后记录不丢
    await page.reload();
    await expect(page.getByText(envName).first()).toBeVisible();

    // localStorage 台账可查
    const store = await page.evaluate(() => JSON.parse(window.localStorage.getItem("qf_mock_store") ?? "{}"));
    expect(store.environments?.some((item: { title?: string }) => item.title === envName)).toBe(true);
  });

  test("空名称提交显示校验错误，不创建记录", async ({ page }) => {
    await page.goto("/platform/environments");
    await page.evaluate(() => window.localStorage.removeItem("qf_mock_store"));
    await page.reload();

    await page.getByRole("button", { name: "新建环境", exact: true }).click();
    await page.getByRole("button", { name: "创建", exact: true }).click();
    await expect(page.locator(".field.has-err .err").first()).toBeVisible();

    const store = await page.evaluate(() => window.localStorage.getItem("qf_mock_store"));
    expect(store).toBeNull();
  });
});
