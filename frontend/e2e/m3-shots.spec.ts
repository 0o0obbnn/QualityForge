import { test } from "@playwright/test";
test.skip(process.env.CI === "true", "本地截图");
test("采集 M3 执行与证据页截图", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/execution-monitor");
  await page.waitForTimeout(2500);
  await page.screenshot({ path: "visual-align/12-执行监控.png", fullPage: true });
  await page.goto("/evidence/EX-T-3185");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/13-证据审核.png", fullPage: true });
});
