import { expect, test } from "@playwright/test";

/**
 * WP-05 资产发布链（批次六十七，mock 模式）：
 * 已批准（APPROVED）任务在审核台就地发布——发布入口可见性、确认弹窗、PUBLISHED toast、按钮翻转已发布。
 */

test.describe("WP-05 发布链（mock 模式）", () => {
  test("已批准任务显示发布入口，确认后 toast PUBLISHED 并翻转为已发布", async ({ page }) => {
    await page.goto("/reviews");
    const queue = page.locator(".qitem");
    await expect(queue).toHaveCount(7);
    await queue.filter({ hasText: "RT-4901" }).click();
    const publishButton = page.getByRole("button", { name: "发布版本" });
    await expect(publishButton).toBeVisible();
    await publishButton.click();
    await expect(page.getByRole("heading", { name: "确认发布" })).toBeVisible();
    await page.getByRole("button", { name: "确认发布" }).click();
    await expect(page.locator(".toast.ok")).toContainText("PUBLISHED");
    await expect(page.getByRole("button", { name: "已发布" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "发布版本" })).toHaveCount(0);
  });

  test("未批准任务不提供发布入口", async ({ page }) => {
    await page.goto("/reviews");
    // 默认选中 q1（无 taskStatus，待审核演示数据）
    await expect(page.getByRole("button", { name: "发布版本" })).toHaveCount(0);
  });
});
