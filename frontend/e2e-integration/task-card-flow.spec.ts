import { expect, test } from "@playwright/test";

/**
 * WP-03 任务卡 → AgentPlan → 人工裁决 真实后端全链（批次六十一）。
 * 前置：后端 8000 已初始化（admin@test.com / Test1234567890）。
 */

test.describe("WP-03 任务卡与计划裁决（真实后端）", () => {
  test("建工作项 → 固化任务卡 → 生成计划 → 批准（ACTIVE 联动）", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.getByText("登录审核工作台")).toBeVisible();
    await page.fill('input[type="email"]', "admin@test.com");
    await page.fill('input[type="password"]', "Test1234567890");
    await page.getByRole("button", { name: "登录" }).click();
    await expect(
      page.getByRole("heading", { name: "测试产出物" }),
    ).toBeVisible();

    // 看板建工作项并进入详情
    await page.goto("/board");
    await page.getByRole("button", { name: "新建工作项" }).click();
    const title = `裁决链联调 ${Date.now()}`;
    await page.fill('input[name="title"]', title);
    await page.selectOption('select[name="type"]', { label: "策略" });
    await page
      .locator("#newItemForm")
      .evaluate((form: HTMLFormElement) => form.requestSubmit());
    await expect(page.locator(".toast.ok")).toBeVisible();
    await page.locator("tbody").getByText(title).first().click();
    await expect(
      page.getByRole("heading", { name: "任务卡（正式任务输入）" }),
    ).toBeVisible();

    // 固化任务卡
    await page.getByRole("button", { name: /固化任务卡/ }).click();
    await page.getByLabel("目标", { exact: true }).fill("联调裁决链任务卡");
    await page.getByLabel("范围", { exact: true }).fill("真实后端全链");
    await page.getByLabel("验收判据").fill("计划批准且任务卡转 ACTIVE");
    await page.getByRole("button", { name: "提交固化" }).click();
    await expect(page.getByText("联调裁决链任务卡")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("SUBMITTED").first()).toBeVisible();

    // 生成计划
    await page.getByRole("button", { name: /生成计划/ }).click();
    await page.getByPlaceholder("步骤键").fill("summarize");
    await page.getByPlaceholder("角色").fill("coordinator");
    await page.getByPlaceholder("描述").fill("需求归纳");
    await page.getByRole("button", { name: "生成并提交裁决" }).click();
    await expect(page.getByText("PENDING_APPROVAL").first()).toBeVisible({ timeout: 10_000 });

    // 批准（摘要对账由前端携带 plan.contentDigest）
    await page.getByRole("button", { name: "批准", exact: true }).click();
    await page.getByLabel("裁决理由（必填）").fill("与任务卡一致");
    await page.getByRole("button", { name: "确认批准" }).click();
    await expect(page.getByText("APPROVED").first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("ACTIVE").first()).toBeVisible();

    // 刷新后持久（真实库回读）
    await page.reload();
    await expect(page.getByText("APPROVED").first()).toBeVisible();
    await expect(page.getByText("联调裁决链任务卡")).toBeVisible();
  });
});
