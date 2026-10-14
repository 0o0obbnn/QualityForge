import { test } from "@playwright/test";
test.skip(process.env.CI === "true", "本地截图");
test("采集规划域三页截图", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/planning/strategies");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/20-测试策略.png", fullPage: true });
  await page.goto("/planning/plans");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/21-测试计划.png", fullPage: true });
  await page.goto("/planning/cases");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/22-场景用例.png", fullPage: true });
});
