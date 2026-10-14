import { test } from "@playwright/test";
test.skip(process.env.CI === "true", "本地截图");
test("采集执行计划页截图", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/execution");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/26-执行计划.png", fullPage: true });
});
