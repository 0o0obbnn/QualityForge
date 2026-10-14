import { expect, test } from "@playwright/test";

/**
 * 审核台 + 看板冒烟（对齐 27 页原型结构，mock 模式）。
 * 覆盖：应用壳导航、看板表格与筛选、新建工作项持久化、审核详情 4 Tab、决策弹窗流程、工作项详情。
 */

test.describe("应用壳与导航（mock 模式）", () => {
  test("侧栏 8 模块可见，任务看板带待审核徽标", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".sidebar .brand")).toHaveText("QualityForge");
    const navItems = page.locator(".sidebar .nav-item");
    await expect(navItems).toHaveCount(8);
    await expect(page.locator(".sidebar .nav-badge")).toHaveText("7");
    // 顶栏上下文与搜索
    await expect(page.getByText("示例项目 · 结算中心")).toBeVisible();
    await expect(page.getByPlaceholder("搜索工作项、用例、契约…")).toBeVisible();
  });

  test("工作看板：KPI 4 卡 + 表格 6 行 + AI 运行面板", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "工作看板" })).toBeVisible();
    const kpis = page.locator(".kpi");
    await expect(kpis).toHaveCount(4);
    const rows = page.locator("tbody tr");
    await expect(rows).toHaveCount(6);
    await expect(page.locator(".ai-run")).toHaveCount(3);
    await expect(page.getByText("Release 进度 · R-2026.08")).toBeVisible();
  });

  test("筛选 chip 过滤工作项", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "阻塞" }).click();
    const rows = page.locator("tbody tr");
    await expect(rows).toHaveCount(1);
    await expect(rows.first()).toContainText("SECRET_ACCESS_DENIED");
    // 切回全部
    await page.getByRole("button", { name: "全部", exact: true }).click();
    await expect(page.locator("tbody tr")).toHaveCount(6);
  });

  test("新建工作项：表单校验 + 创建后入列表顶部", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "新建工作项" }).click();
    // 空标题提交被拒
    await page.locator("#newItemForm").evaluate((form: HTMLFormElement) => form.requestSubmit());
    await expect(page.locator(".toast.err")).toBeVisible();
    // 填写标题后创建
    await page.fill('input[name="title"]', "补充退款场景用例");
    await page.locator("#newItemForm").evaluate((form: HTMLFormElement) => form.requestSubmit());
    await expect(page.locator(".toast.ok")).toBeVisible();
    const firstRow = page.locator("tbody tr").first();
    await expect(firstRow).toContainText("补充退款场景用例");
    await expect(firstRow).toContainText("WI-9001");
  });

  test("待审核页：队列 7 项 + 详情 kv + 4 Tab 切换", async ({ page }) => {
    await page.goto("/reviews");
    await expect(page.getByRole("heading", { name: "待我审核" })).toBeVisible();
    const queue = page.locator(".qitem");
    await expect(queue).toHaveCount(7);
    // 详情 kv
    await expect(page.getByText("RT-4832 · SINGLE_REVIEW")).toBeVisible();
    await expect(page.getByText("contentDigest: sha256:3f9a…c21e")).toBeVisible();
    // 4 Tab
    for (const tab of ["版本 Diff", "来源追溯", "检查结果", "证据"]) {
      await page.getByRole("tab", { name: tab }).click();
      await expect(page.getByRole("tab", { name: tab })).toHaveClass(/on/);
    }
    // Diff 内容
    await page.getByRole("tab", { name: "版本 Diff" }).click();
    await expect(page.locator(".diff-view").getByText("网关故障注入")).toBeVisible();
    // 来源追溯
    await page.getByRole("tab", { name: "来源追溯" }).click();
    await expect(page.getByText("CONFIRMED 来源", { exact: false })).toBeVisible();
  });

  test("决策流程：批准弹窗绑定 digest 文案 + 退回表单必填校验", async ({ page }) => {
    await page.goto("/reviews");
    // 第一项（策略）可批准
    await page.getByRole("button", { name: /批准 V2/ }).click();
    await expect(page.getByText("批准后将绑定当前版本摘要")).toBeVisible();
    await expect(page.locator(".modal.open").getByText("sha256:3f9a…c21e", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "取消", exact: true }).click();
    // 退回必填校验
    await page.getByRole("button", { name: "退回修改" }).click();
    await page.getByRole("button", { name: "提交退回" }).click();
    await expect(page.locator(".toast.err")).toBeVisible();
    // 填写完整后提交
    await page.selectOption(".modal.open select", { label: "范围需要调整" });
    await page.fill(".modal.open textarea", "补充网关故障场景覆盖");
    await page.getByRole("button", { name: "提交退回" }).click();
    await expect(page.locator(".toast.ok")).toBeVisible();
    // 队列项显示已退回（H8 自动聚焦后选中态已移到下一项，用非选中定位）
    await expect(page.locator(".qitem").first()).toContainText("已退回");
  });

  test("禁用原因：陈旧版本项批准按钮禁用且原因可见", async ({ page }) => {
    await page.goto("/reviews");
    await page.locator(".qitem").nth(1).click();
    const approve = page.getByRole("button", { name: /批准 V3/ });
    await expect(approve).toBeDisabled();
    await expect(page.getByTestId("approve-blocked-reasons")).toContainText("此版本已陈旧");
  });

  test("工作项详情：基本信息 + AI 运行清单 + 事件时间线 + 取消弹窗", async ({ page }) => {
    await page.goto("/work-items/WI-0246");
    await expect(page.getByText("WI-0246")).toBeVisible();
    await expect(page.getByText("生成测试计划草稿")).toBeVisible();
    await expect(page.getByText("事件时间线")).toBeVisible();
    await expect(page.getByText("Token 用量")).toBeVisible();
    // 取消任务危险弹窗
    await page.getByRole("button", { name: "取消任务" }).click();
    await expect(page.getByText("取消将停止未开始节点")).toBeVisible();
    await page.getByRole("button", { name: "确认取消" }).click();
    await expect(page.locator(".toast.err")).toBeVisible();
    await expect(page.locator(".page-head").getByText("已取消", { exact: true })).toBeVisible();
  });

  test("占位模块可路由（帮助中心入口验证 8 模块导航）", async ({ page }) => {
    await page.goto("/planning");
    await expect(page.getByRole("heading", { name: "测试规划与设计" })).toBeVisible();
    await expect(page.getByText("模块建设中")).toBeVisible();
    await page.goto("/quality");
    await expect(page.getByRole("heading", { name: "质量中心" })).toBeVisible();
  });
});
