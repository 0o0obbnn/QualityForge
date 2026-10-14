import { expect, test } from "@playwright/test";

/** 协作对话页（WP-03 前端接入，mock 模式）。 */

test.describe("协作对话页（mock）", () => {
  test("会话列表 + 消息流 + 发送追加", async ({ page }) => {
    await page.goto("/conversations");
    await expect(page.getByRole("heading", { name: "协作对话" })).toBeVisible();
    // mock 台账两条会话，最近活跃（退款策略协作）默认选中并展示消息
    await expect(page.getByText("R-2026.09 发布口径对齐")).toBeVisible();
    await expect(
      page.getByText("已归纳 3 条业务规则，需要先澄清风控阈值口径（见澄清卡）"),
    ).toBeVisible();

    // 发送消息：追加到消息流
    await page.getByLabel("消息内容").fill("补充一条口径确认");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByText("补充一条口径确认")).toBeVisible();

    // 敏感分级：CONFIDENTED/RESTRICTED 正文转引用 chip
    await page.getByLabel("数据分级").selectOption("CONFIDENTIAL");
    await page.getByLabel("消息内容").fill("机密正文不入明文");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByText(/敏感内容按引用存储/).first()).toBeVisible();
  });

  test("新建会话弹层：标题必填后创建并切换", async ({ page }) => {
    await page.goto("/conversations");
    await page.getByRole("button", { name: /新建会话/ }).click();
    const createButton = page.getByRole("button", {
      name: "创建",
      exact: true,
    });
    await expect(createButton).toBeDisabled();
    await page.getByLabel("会话主题").fill("冒烟新会话");
    await createButton.click();
    await expect(page.locator(".toast.ok")).toBeVisible();
    await expect(page.getByText("尚无消息，发送第一条协作消息")).toBeVisible();
  });
});
