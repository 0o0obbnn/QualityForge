import { expect, test } from "@playwright/test";

/**
 * 联调主流程（真实后端，无 mock）：
 * 登录 → 产出物总览首屏 → 看板列表回显后端数据 → 新建工作项落库 → 列表刷新可见 → 待审核空态（尚无审核任务）。
 * 前置：后端 8000 端口运行且已初始化（admin@test.com / Test1234567890）。
 */

test.describe("前后端联调主流程", () => {
  test("登录 → 看板真实数据 → 新建工作项落库 → 刷新可见", async ({ page }) => {
    const uniqueTitle = `联调 UI 创建用例 ${Date.now()}`;
    await page.goto("/");
    // 已初始化后端 → 登录页
    await expect(page.getByText("登录审核工作台")).toBeVisible();
    await page.fill('input[type="email"]', "admin@test.com");
    await page.fill('input[type="password"]', "Test1234567890");
    await page.getByRole("button", { name: "登录" }).click();
    // 登录后默认进入产出物总览首屏（/artifacts）
    await expect(page.getByRole("heading", { name: "测试产出物" })).toBeVisible();
    // 显式进入工作看板
    await page.goto("/board");
    await expect(page.getByRole("heading", { name: "工作看板" })).toBeVisible();

    // 新建工作项 → 落库
    await page.getByRole("button", { name: "新建工作项" }).click();
    await page.fill('input[name="title"]', uniqueTitle);
    await page.selectOption('select[name="type"]', { label: "用例" });
    await page.locator("#newItemForm").evaluate((form: HTMLFormElement) => form.requestSubmit());
    await expect(page.locator(".toast.ok")).toBeVisible();
    // 列表中应出现新创建的项（多次重跑同名累积，用 first() 消歧）
    await expect(page.locator("tbody").getByText(uniqueTitle).first()).toBeVisible();
    await page.reload();
    await expect(page.locator("tbody").getByText(uniqueTitle).first()).toBeVisible();
  });

  test("待审核页真实模式空态（后端尚无审核任务时不虚构数据）", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("登录审核工作台")).toBeVisible();
    await page.fill('input[type="email"]', "admin@test.com");
    await page.fill('input[type="password"]', "Test1234567890");
    await page.getByRole("button", { name: "登录" }).click();
    // 等待登录完成（进入产出物总览首屏）
    await expect(page.getByRole("heading", { name: "测试产出物" })).toBeVisible();
    await page.goto("/reviews");
    await expect(page.getByText("暂无待审核任务")).toBeVisible();
  });

  test("错误路径：未登录访问看板被守卫拦截", async ({ page }) => {
    // 清 cookie 模拟未登录
    await page.context().clearCookies();
    await page.goto("/board");
    await expect(page.getByText("登录审核工作台")).toBeVisible();
  });
});
