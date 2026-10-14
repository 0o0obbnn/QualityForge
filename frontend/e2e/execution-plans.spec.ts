import { expect, test } from "@playwright/test";

/**
 * 执行计划页冒烟（mock 模式）：计划列表 + 版本冻结清单（Sprint 2 T8）。
 */

test.describe("执行计划页（mock 模式）", () => {
  test("计划列表：环境/触发/并发/状态列 + 冻结清单", async ({ page }) => {
    await page.goto("/execution");
    await expect(page.getByRole("heading", { name: "执行计划", exact: true })).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(2);
    await expect(page.getByText("R-2026.08 回归执行")).toBeVisible();
    await expect(page.getByText("EP-2026-0811-007").first()).toBeVisible();
    await expect(page.locator("tbody").getByText("手工", { exact: true })).toBeVisible();
    await expect(page.locator("tbody").getByText("执行中", { exact: true })).toBeVisible();
    // 冻结清单
    await expect(page.getByText("版本冻结清单 · EP-2026-0811-007 V1")).toBeVisible();
    await expect(page.getByText("settlement V7 · recon V4")).toBeVisible();
    await expect(page.getByText("冻结后用例/脚本发布新版本不影响本次执行")).toBeVisible();
  });

  test("计划行点击跳转执行监控", async ({ page }) => {
    await page.goto("/execution");
    await page.locator("tbody tr").first().click();
    await expect(page).toHaveURL(/\/execution-monitor/);
    await expect(page.getByRole("heading", { name: "执行监控" })).toBeVisible();
  });

  test("执行监控页「返回执行计划」互跳", async ({ page }) => {
    await page.goto("/execution-monitor");
    await page.getByRole("button", { name: "返回执行计划" }).click();
    await expect(page).toHaveURL(/\/execution$/);
    await expect(page.getByRole("heading", { name: "执行计划", exact: true })).toBeVisible();
  });
});
