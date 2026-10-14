import { test } from "@playwright/test";
test.skip(process.env.CI === "true", "本地截图");
test("采集 Agent 中心三页截图", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/agent");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/27-能力注册.png", fullPage: true });
  await page.goto("/agent/operations");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/28-运行与评测.png", fullPage: true });
  await page.goto("/agent/trace/a9f2c1");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/29-Agent-Trace.png", fullPage: true });
});
