import { test } from "@playwright/test";
test.skip(process.env.CI === "true", "本地截图");
test("采集自动化三页截图", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/automation/scripts");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/23-自动化工作台.png", fullPage: true });
  await page.goto("/automation/code-review");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/24-代码审核.png", fullPage: true });
  await page.goto("/automation/assets");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/25-配套资产.png", fullPage: true });
});
