import { test } from "@playwright/test";

test.describe("诊断2：page-head 子元素", () => {
  test.use({ viewport: { width: 390, height: 844 } });
  for (const route of ["/reviews", "/planning/strategies", "/execution-monitor", "/agent"]) {
    test(`诊断 ${route}`, async ({ page }) => {
      await page.goto(route);
      await page.waitForTimeout(500);
      const info = await page.evaluate(() => {
        const head = document.querySelector(".page-head");
        if (!head) return "no-page-head";
        const kids = Array.from(head.children).map((el) => {
          const r = el.getBoundingClientRect();
          return `${el.tagName}.${String(el.className).slice(0, 30)} w=${Math.round(r.width)} r=${Math.round(r.right)} flexShrink=${getComputedStyle(el).flexShrink} minW=${getComputedStyle(el).minWidth}`;
        });
        const hs = getComputedStyle(head);
        return { wrap: hs.flexWrap, display: hs.display, kids };
      });
      console.log(`DIAG2 ${route}:`, JSON.stringify(info));
    });
  }
});
