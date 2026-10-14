import { test } from "@playwright/test";

/**
 * 原型对齐证据截图：看板、待审核、工作项详情（桌面 + 移动）。
 * 运行前提：dev server 已在外部启动（VITE_MOCK=1）。
 */
test.skip(process.env.CI === "true", "视觉证据仅本地采集");

test("采集原型对齐后关键界面截图", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });

  // 1. 工作看板（10-board.html 结构）
  await page.goto("/");
  await page.waitForSelector("tbody tr");
  await page.screenshot({ path: "visual-align/01-工作看板-桌面.png", fullPage: true });

  // 2. 待我审核（11-reviews.html 结构）
  await page.goto("/reviews");
  await page.waitForSelector(".qitem");
  await page.screenshot({ path: "visual-align/02-待我审核-桌面.png", fullPage: true });

  // 3. 审核详情 4 Tab 之一：版本 Diff
  await page.getByRole("tab", { name: "版本 Diff" }).click();
  await page.waitForSelector(".diff-view");
  await page.screenshot({ path: "visual-align/03-审核详情-DiffTab.png", fullPage: true });

  // 4. 工作项详情（12-workitem.html 结构）
  await page.goto("/work-items/WI-0246");
  await page.waitForSelector(".two-col");
  await page.screenshot({ path: "visual-align/04-工作项详情-桌面.png", fullPage: true });

  // 5. 移动端看板
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.waitForSelector(".nav-hamburger");
  await page.screenshot({ path: "visual-align/05-移动端-390px.png", fullPage: true });
});
