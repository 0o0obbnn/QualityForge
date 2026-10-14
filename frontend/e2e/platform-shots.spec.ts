import { test } from "@playwright/test";
test.skip(process.env.CI === "true", "本地截图");
test("采集平台管理三页截图", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/platform");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/30-项目与Release.png", fullPage: true });
  await page.goto("/platform/environments");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/31-环境与资源.png", fullPage: true });
  await page.goto("/platform/governance");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/32-集成与权限.png", fullPage: true });
});
