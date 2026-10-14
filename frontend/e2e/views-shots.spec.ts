import { test } from "@playwright/test";
test.skip(process.env.CI === "true", "本地截图");
test("采集新增视图截图", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  for (const [tab, name] of [["AI 工作中","06-AI工作中"],["退回重做","07-退回重做"],["待执行","08-待执行"],["阻塞风险","09-阻塞风险"],["管理视图","10-管理视图"]] as const) {
    await page.getByRole("tab", { name: tab }).click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: `visual-align/${name}-视图.png`, fullPage: true });
  }
  await page.goto("/help");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "visual-align/11-帮助与术语.png", fullPage: true });
});
