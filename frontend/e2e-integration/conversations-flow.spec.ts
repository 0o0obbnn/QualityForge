import { expect, test } from "@playwright/test";

/**
 * WP-03 协作对话真实后端链（批次六十）：
 * 登录 → 新建会话 → 发送消息（INTERNAL 内联 + CONFIDENTIAL 转引用）→ 刷新后消息持久。
 * 前置：后端 8000 已初始化（admin@test.com / Test1234567890）。
 */

test.describe("WP-03 协作对话（真实后端）", () => {
  test("新建会话 → 发消息 → 引用分级 → 刷新持久", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("登录审核工作台")).toBeVisible();
    await page.fill('input[type="email"]', "admin@test.com");
    await page.fill('input[type="password"]', "Test1234567890");
    await page.getByRole("button", { name: "登录" }).click();
    await expect(
      page.getByRole("heading", { name: "测试产出物" }),
    ).toBeVisible();

    await page.goto("/conversations");
    await expect(page.getByRole("heading", { name: "协作对话" })).toBeVisible();

    const title = `联调会话 ${Date.now()}`;
    await page.getByRole("button", { name: /新建会话/ }).click();
    await page.getByLabel("会话主题").fill(title);
    await page.getByRole("button", { name: "创建", exact: true }).click();
    await expect(page.locator(".toast.ok")).toBeVisible();
    await expect(page.getByText("尚无消息，发送第一条协作消息")).toBeVisible();

    // INTERNAL 低敏正文内联发送
    await page.getByLabel("消息内容").fill("以 v3 风控口径为准");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByText("以 v3 风控口径为准")).toBeVisible();

    // CONFIDENTIAL 正文转引用 chip（服务端与前端同口径）
    await page.getByLabel("数据分级").selectOption("CONFIDENTIAL");
    await page.getByLabel("消息内容").fill("涉密判据正文");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByText(/敏感内容按引用存储/).first()).toBeVisible();

    // 刷新后消息持久（真实库回读）
    await page.reload();
    await expect(page.getByText("以 v3 风控口径为准")).toBeVisible();
    await expect(page.getByText(/敏感内容按引用存储/).first()).toBeVisible();
  });
});
