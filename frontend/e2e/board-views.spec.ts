import { expect, test } from "@playwright/test";

/**
 * M2 七类看板视图冒烟（mock 模式）：视图切换、AI 工作中、退回重做、待执行、阻塞风险、管理视图。
 */

test.describe("看板七类视图（mock 模式）", () => {
  test("视图切换 tabs 渲染七入口 + 我的待审核跳转", async ({ page }) => {
    await page.goto("/");
    const tabs = page.getByRole("tab");
    await expect(tabs).toHaveCount(7);
    await expect(page.getByRole("tab", { name: "全部工作项" })).toHaveClass(/on/);
    // 默认视图：KPI + 表格
    await expect(page.locator(".kpi")).toHaveCount(4);
    await expect(page.locator("tbody tr")).toHaveCount(6);
    // 切到 AI 工作中
    await page.getByRole("tab", { name: "AI 工作中" }).click();
    await expect(page.getByText("3 个运行")).toBeVisible();
  });

  test("视图 2 AI 工作中：任务/Agent/步骤/预算/操作列", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "AI 工作中" }).click();
    await expect(page.locator("tbody tr")).toHaveCount(3);
    await expect(page.getByText("TestStrategy 草稿生成")).toBeVisible();
    await expect(page.getByText("attempt 1").first()).toBeVisible();
    await expect(page.getByText("预算 300s")).toBeVisible();
  });

  test("视图 3 退回重做：审核意见/差异/当前修改人", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "退回重做" }).click();
    await expect(page.getByText("2 项返工中")).toBeVisible();
    await expect(page.getByText("第 1 轮")).toBeVisible();
    await expect(page.getByText("退出标准未覆盖网关故障场景,补充后重新提交")).toBeVisible();
    await expect(page.getByText("策略 Agent")).toBeVisible();
  });

  test("视图 4 待执行：环境/Release/脚本版本/ExecutionTask", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "待执行" }).click();
    await expect(page.getByText("3 个执行计划")).toBeVisible();
    await expect(page.getByText("EP-2026-0811-007")).toBeVisible();
    await expect(page.getByText("settlement_api_flow V2")).toBeVisible();
    await expect(page.getByText("ET-0812-004")).toBeVisible();
  });

  test("视图 5 阻塞风险：按原因分组 + 责任方/持续时间/恢复条件", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "阻塞风险" }).click();
    await expect(page.getByText("3 项阻塞 · 2 类原因")).toBeVisible();
    await expect(page.getByText("SECRET_ACCESS_DENIED")).toBeVisible();
    await expect(page.getByText("Runner 离线")).toBeVisible();
    await expect(page.getByText("补 Vault 授权后由 Runner 重试")).toBeVisible();
  });

  test("视图 7 管理视图：8 张指标卡 + 分布面板 + 口径提示", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "管理视图" }).click();
    await expect(page.locator(".kpi")).toHaveCount(8);
    await expect(page.getByText("Lead Time 中位")).toBeVisible();
    await expect(page.getByText("AI 采用率")).toBeVisible();
    await expect(page.getByText("指标基于 WorkItemEvent 事件流计算")).toBeVisible();
  });

  test("分派弹窗：打开→确认→执行者更新", async ({ page }) => {
    await page.goto("/");
    await page.locator("tbody tr").first().getByRole("button", { name: "分派" }).click();
    await expect(page.getByText("分派工作项")).toBeVisible();
    await page.getByRole("button", { name: "确认分派" }).click();
    await expect(page.locator(".toast.ok")).toBeVisible();
    await expect(page.locator("tbody tr").first()).toContainText("王测试");
  });

  test("H8 连续导航：退回后自动聚焦下一项", async ({ page }) => {
    await page.goto("/reviews");
    await expect(page.locator(".qitem").first()).toHaveClass(/selected/);
    await page.getByRole("button", { name: "退回修改" }).click();
    await page.selectOption(".modal.open select", { label: "范围需要调整" });
    await page.fill(".modal.open textarea", "补充网关故障场景覆盖");
    await page.getByRole("button", { name: "提交退回" }).click();
    await expect(page.locator(".toast.ok")).toBeVisible();
    // 自动聚焦下一项（第二项选中）
    await expect(page.locator(".qitem").nth(1)).toHaveClass(/selected/);
  });

  test("帮助与术语页可路由", async ({ page }) => {
    await page.goto("/help");
    await expect(page.getByRole("heading", { name: "帮助与术语" })).toBeVisible();
    await expect(page.getByText("8 个核心条目")).toBeVisible();
    await expect(page.getByRole("cell", { name: "contentDigest", exact: true })).toBeVisible();
  });
});
