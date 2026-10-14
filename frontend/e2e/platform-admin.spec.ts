import { expect, test } from "@playwright/test";

/**
 * 平台管理三页冒烟（mock 模式）：项目与 Release（80）/ 环境与资源（81）/ 集成与权限（82）。
 */

test.describe("平台管理（mock 模式）", () => {
  test("项目与 Release：项目列表 + Release 卡片 + 成员", async ({ page }) => {
    await page.goto("/platform");
    await expect(page.getByRole("heading", { name: "项目与 Release" })).toBeVisible();
    await expect(page.getByText("2 个项目(含本地创建)")).toBeVisible();
    await expect(page.getByText("结算中心")).toBeVisible();
    await expect(page.getByText("对账服务")).toBeVisible();
    await expect(page.getByText("Workspace · owner: 李测试")).toBeVisible();
    await expect(page.getByText("Release · R-2026.08")).toBeVisible();
    await expect(page.getByText("32 需求 · 236 用例")).toBeVisible();
    await expect(page.getByText("成员 (5)")).toBeVisible();
    await expect(page.getByText("赵运维")).toBeVisible();
    await expect(page.getByText("WorkspaceAdmin")).toBeVisible();
    // 平台级上下文
    await expect(page.getByText("平台级")).toBeVisible();
    // 行点击切换 toast
    await page.getByText("结算中心").click();
    await expect(page.getByText("切换到该项目(演示)")).toBeVisible();
  });

  test("环境与资源：环境表 + Runner/Secret/配额 + 新建环境校验", async ({ page }) => {
    await page.goto("/platform/environments");
    await expect(page.getByRole("heading", { name: "环境与资源" })).toBeVisible();
    await expect(page.getByText("staging", { exact: true })).toBeVisible();
    await expect(page.getByText("https://staging.settle.internal")).toBeVisible();
    await expect(page.getByText("secret:pre-db · V3")).toBeVisible();
    await expect(page.getByText("Secret 过期")).toBeVisible();
    await expect(page.getByText("runner-01")).toBeVisible();
    await expect(page.getByText("ONLINE_BUSY")).toBeVisible();
    await expect(page.getByText("HEARTBEAT_LOST")).toBeVisible();
    await expect(page.getByText("只显示引用")).toBeVisible();
    await expect(page.getByText("已过期")).toBeVisible();
    await expect(page.getByText("并发 Runner")).toBeVisible();
    await expect(page.getByText("2 / 8")).toBeVisible();
    await expect(page.getByText("¥342 / ¥2000")).toBeVisible();
    // 环境行点击详情
    await page.getByText("dev", { exact: true }).click();
    await expect(page.getByRole("heading", { name: "环境详情" })).toBeVisible();
    await expect(page.getByText("Web/API · 故障注入")).toBeVisible();
    await page.getByLabel("关闭").click();
    // 新建环境：空名称校验
    await page.getByRole("button", { name: "新建环境", exact: true }).click();
    await page.getByRole("button", { name: "创建", exact: true }).click();
    await expect(page.getByText("请输入名称")).toBeVisible();
    await page.getByPlaceholder("例如: pre-prod").fill("pre-prod");
    await page.getByRole("button", { name: "创建", exact: true }).click();
    // 持久化行为：提交后列表可见（含预置 staging/dev 之外的“就绪”行）
    await expect(page.getByText("环境已创建")).toBeVisible();
    await expect(page.locator("tbody").getByText("pre-prod", { exact: true })).toBeVisible();
  });

  test("环境与资源：轮换 Secret 危险操作确认", async ({ page }) => {
    await page.goto("/platform/environments");
    await page.getByRole("button", { name: "轮换 Secret" }).click();
    await expect(page.getByRole("heading", { name: "轮换 Secret" })).toBeVisible();
    await expect(page.getByText("危险操作确认")).toBeVisible();
    await page.getByRole("button", { name: "确认轮换" }).click();
    await expect(page.getByText("Secret 轮换已发起(演示)")).toBeVisible();
  });

  test("集成与权限：三 Tab 切换 + 审计日志 + 新建角色校验", async ({ page }) => {
    await page.goto("/platform/governance");
    await expect(page.getByRole("heading", { name: "集成与权限" })).toBeVisible();
    // 集成 Tab（默认）
    await expect(page.getByText("JIRA · 结算中心")).toBeVisible();
    await expect(page.getByText("*.atlassian.net")).not.toBeVisible();
    await expect(page.getByText("凭据失效")).toBeVisible();
    await page.getByText("JIRA · 结算中心").click();
    await expect(page.getByRole("heading", { name: "集成详情" })).toBeVisible();
    await expect(page.getByText("*.atlassian.net (allowlist)")).toBeVisible();
    await page.getByLabel("关闭").click();
    // RBAC Tab
    await page.getByRole("button", { name: "RBAC" }).click();
    await expect(page.getByText("内置角色不可被租户原地修改")).toBeVisible();
    await expect(page.getByText("TestLead")).toBeVisible();
    await page.getByText("TestEngineer").click();
    await expect(page.getByRole("heading", { name: "角色详情" })).toBeVisible();
    await expect(page.getByText("最终动作 = 用户 RBAC")).toBeVisible();
    await page.getByLabel("关闭").click();
    // 审核策略 Tab
    await page.getByRole("button", { name: "审核策略" }).click();
    await expect(page.getByText("SINGLE_REVIEW")).toBeVisible();
    await expect(page.getByText("FOUR_EYES")).toBeVisible();
    await expect(page.getByText("Reviewer ≠ Approver")).toBeVisible();
    await expect(page.getByText("平台最低要求只能调严")).toBeVisible();
    await page.getByText("CODE_REVIEW").click();
    await expect(page.getByRole("heading", { name: "审核策略" })).toBeVisible();
    await expect(page.getByText("digest 匹配 · 权限有效")).toBeVisible();
    await page.getByLabel("关闭").click();
    // 审计日志弹窗
    await page.getByRole("button", { name: "审计日志" }).click();
    await expect(page.getByRole("heading", { name: "审计日志" })).toBeVisible();
    await expect(page.getByText("review.approve")).toBeVisible();
    await expect(page.getByText("DENY (未授权)")).toBeVisible();
    await expect(page.getByText("coverage-analyzer v2")).toBeVisible();
    await page.getByRole("button", { name: "关闭" }).last().click();
    // 新建角色：空名称校验
    await page.getByRole("button", { name: "新建角色", exact: true }).click();
    await page.getByRole("button", { name: "创建", exact: true }).click();
    await expect(page.getByText("请输入名称")).toBeVisible();
    await page.getByPlaceholder("例如: 风险审核员").fill("风险审核员");
    await page.getByRole("button", { name: "创建", exact: true }).click();
    await expect(page.getByText("角色已创建,等待人工授权(演示)")).toBeVisible();
  });

  test("三页顶栏互跳", async ({ page }) => {
    await page.goto("/platform");
    await page.getByRole("button", { name: "环境与资源" }).click();
    await expect(page).toHaveURL(/\/platform\/environments/);
    await page.getByRole("button", { name: "集成与权限" }).click();
    await expect(page).toHaveURL(/\/platform\/governance/);
    await page.getByRole("button", { name: "项目" }).click();
    await expect(page).toHaveURL(/\/platform$/);
    // 侧栏 active 保持
    await expect(page.getByLabel("主导航").locator(".nav-item.active")).toContainText("平台管理");
  });
});
