import { test } from "@playwright/test";
test.skip(process.env.CI === "true", "本地截图");
test("采集 M4 质量中心截图", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/quality/analyses");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/14-结果分析.png", fullPage: true });
  await page.goto("/quality/defects");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/15-Defect.png", fullPage: true });
  await page.goto("/quality/reports");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/16-报告与门禁.png", fullPage: true });
});
