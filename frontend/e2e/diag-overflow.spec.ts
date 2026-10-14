import { test } from "@playwright/test";

test.describe("诊断：移动宽度溢出元素", () => {
  test.use({ viewport: { width: 390, height: 844 } });
  for (const route of ["/board", "/reviews", "/planning/strategies", "/execution-monitor", "/platform", "/agent"]) {
    test(`诊断 ${route} 溢出元素`, async ({ page }) => {
      await page.goto(route);
      await page.waitForTimeout(500);
      const info = await page.evaluate(() => {
        const doc = document.documentElement;
        const out: string[] = [];
        for (const el of document.querySelectorAll("*")) {
          const r = el.getBoundingClientRect();
          if (r.right > doc.clientWidth + 1 && r.width > 50) {
            out.push(`${el.tagName}.${String(el.className).slice(0, 45)} w=${Math.round(r.width)} right=${Math.round(r.right)}`);
          }
        }
        return { scrollW: doc.scrollWidth, clientW: doc.clientWidth, out: out.slice(0, 6) };
      });
      console.log(`DIAG ${route}:`, JSON.stringify(info));
    });
  }
});
