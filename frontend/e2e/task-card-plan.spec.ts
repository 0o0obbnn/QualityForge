import { expect, test } from "@playwright/test";

/** WP-03 任务卡/AgentPlan 裁决链 + WP-04 执行命令（批次六十一，mock 模式）。 */

test.describe("任务卡与计划裁决（mock）", () => {
  test("工作项详情：任务卡列表 + 计划批准链", async ({ page }) => {
    await page.goto("/work-items/WI-0246");
    await expect(
      page.getByRole("heading", { name: "任务卡（正式任务输入）" }),
    ).toBeVisible();
    await expect(page.getByText("生成结算中心回归资产")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "AgentPlan（人工裁决链）" }),
    ).toBeVisible();
    await expect(page.getByText("PENDING_APPROVAL").first()).toBeVisible();

    // 批准：理由必填 → 提交 → 状态翻转 APPROVED
    await page.getByRole("button", { name: "批准", exact: true }).click();
    const confirm = page.getByRole("button", { name: "确认批准" });
    await expect(confirm).toBeDisabled();
    await page.getByLabel("裁决理由（必填）").fill("方案与任务卡一致");
    await expect(confirm).toBeEnabled();
    await confirm.click();
    await expect(page.locator(".toast.ok")).toBeVisible();
    await expect(page.getByText("APPROVED").first()).toBeVisible();
  });

  test("固化任务卡：必填校验 + 新卡取代旧卡", async ({ page }) => {
    await page.goto("/work-items/WI-0246");
    await page.getByRole("button", { name: /固化任务卡/ }).click();
    const submit = page.getByRole("button", { name: "提交固化" });
    await expect(submit).toBeDisabled();
    await page.getByLabel("目标", { exact: true }).fill("冒烟新任务卡");
    await page.getByLabel("范围", { exact: true }).fill("冒烟范围");
    await page.getByLabel("验收判据").fill("冒烟判据");
    await expect(submit).toBeEnabled();
    await submit.click();
    await expect(page.locator(".toast.ok")).toBeVisible();
    await expect(page.getByText("冒烟新任务卡")).toBeVisible();
    await expect(page.getByText("SUPERSEDED").first()).toBeVisible();
  });

  test("执行监控：运行中任务可暂停/取消（回执 toast）", async ({ page }) => {
    await page.goto("/execution-monitor");
    const pauseButton = page
      .getByRole("button", { name: "暂停", exact: true })
      .first();
    await expect(pauseButton).toBeVisible();
    await pauseButton.click();
    await expect(page.locator(".toast.ok").first()).toBeVisible();
  });
});
