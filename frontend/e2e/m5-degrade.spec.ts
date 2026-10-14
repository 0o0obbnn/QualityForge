import { expect, test } from "@playwright/test";

/**
 * M5 降级状态呈现冒烟（mock 模式）：顶栏 Provider chip 三态中的 mock 形态。
 * mock 模式 fetchProviderStatus 返回 NOMINAL；三态渲染由 vitest ProviderStatusChip.test 覆盖。
 */

test.describe("M5 Provider 降级状态（mock 模式）", () => {
  test("看板页顶栏显示 AI Provider 正常 chip", async ({ page }) => {
    await page.goto("/board");
    const chip = page.locator(".provider-chip");
    await expect(chip).toBeVisible();
    await expect(chip).toHaveClass(/st-done/);
    await expect(chip).toContainText("AI Provider 正常");
    await expect(chip).not.toContainText("降级");
  });

  test("平台管理页同样显示 Provider chip（全局顶栏）", async ({ page }) => {
    await page.goto("/platform");
    await expect(page.locator(".provider-chip")).toBeVisible();
    await expect(page.locator(".provider-chip")).toContainText("AI Provider 正常");
    // 平台级上下文不受影响
    await expect(page.getByText("平台级")).toBeVisible();
  });

  test("chip 位于项目上下文之后、搜索框之前（顶栏顺序）", async ({ page }) => {
    await page.goto("/board");
    const topbar = page.locator(".topbar");
    const ctx = topbar.locator(".ctx");
    const chip = topbar.locator(".provider-chip");
    const search = topbar.locator(".search");
    const ctxBox = await ctx.boundingBox();
    const chipBox = await chip.boundingBox();
    const searchBox = await search.boundingBox();
    expect(ctxBox).toBeTruthy();
    expect(chipBox).toBeTruthy();
    expect(searchBox).toBeTruthy();
    expect((ctxBox?.x ?? 0) + (ctxBox?.width ?? 0)).toBeLessThanOrEqual(chipBox?.x ?? 0);
    expect((chipBox?.x ?? 0) + (chipBox?.width ?? 0)).toBeLessThanOrEqual(searchBox?.x ?? 0);
  });
});
