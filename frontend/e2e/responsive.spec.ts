import { expect, test } from "@playwright/test";

/**
 * 响应式走查（deep_delivery 验收标准「主流终端构建通过」）：
 * 桌面 1440 与移动 390 宽度走关键页面，检查关键元素可见性与水平溢出。
 */

const KEY_ROUTES = ["/board", "/reviews", "/planning/strategies", "/execution-monitor", "/platform", "/agent"];

function expectNoHorizontalOverflow(page: import("@playwright/test").Page) {
  return expect
    .poll(async () =>
      page.evaluate(() => {
        const doc = document.documentElement;
        return doc.scrollWidth - doc.clientWidth;
      }),
    )
    .toBeLessThanOrEqual(1);
}

test.describe("桌面 1440×900 关键页面", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  for (const route of KEY_ROUTES) {
    test(`桌面宽度 ${route} 无水平溢出且关键元素可见`, async ({ page }) => {
      await page.goto(route);
      await expect(page.locator("main, .app").first()).toBeVisible();
      await expect(page.locator(".topbar")).toBeVisible();
      await expect(page.locator(".provider-chip")).toBeVisible();
      await expectNoHorizontalOverflow(page);
    });
  }
});

test.describe("移动 390×844 关键页面", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  for (const route of KEY_ROUTES) {
    test(`移动宽度 ${route} 无水平溢出且顶栏可用`, async ({ page }) => {
      await page.goto(route);
      await expect(page.locator(".topbar")).toBeVisible();
      // 移动端侧栏隐藏、汉堡按钮可用
      await expect(page.locator(".nav-hamburger")).toBeVisible();
      await expectNoHorizontalOverflow(page);
    });
  }

  test("移动宽度 汉堡按钮可打开导航抽屉并可关闭", async ({ page }) => {
    await page.goto("/board");
    await page.locator(".nav-hamburger").click();
    await expect(page.locator(".nav-drawer.open")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.locator(".nav-drawer.open")).toHaveCount(0);
  });

  test("移动宽度 看板表格内容可横向滚动容器而非页面溢出", async ({ page }) => {
    await page.goto("/board");
    await expectNoHorizontalOverflow(page);
  });
});
