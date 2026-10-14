import { test } from "@playwright/test";
test.skip(process.env.CI === "true", "本地截图");
test("采集知识库三页截图", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/knowledge/sources");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/17-来源与需求.png", fullPage: true });
  await page.goto("/knowledge/contracts");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/18-API契约.png", fullPage: true });
  await page.goto("/knowledge/entries");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/19-知识库.png", fullPage: true });
});
