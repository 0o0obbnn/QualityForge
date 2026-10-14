import { expect, test } from "@playwright/test";

/**
 * Agent 中心三页冒烟（mock 模式）：能力注册（70）/ 运行与评测（71）/ Agent Trace（72）。
 */

test.describe("AI Agent 中心（mock 模式）", () => {
  test("能力注册：四 Tab 切换 + Skill 列表", async ({ page }) => {
    await page.goto("/agent");
    await expect(page.getByRole("heading", { name: "能力注册" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Skill (14)" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByText("requirement-compiler")).toBeVisible();
    await expect(page.getByText("只读来源")).toBeVisible();
    await expect(page.getByText("ACTIVE").first()).toBeVisible();
    // 切 Agent Tab
    await page.getByRole("tab", { name: "Agent (4)" }).click();
    await expect(page.getByText("qf-supervisor")).toBeVisible();
    await expect(page.getByText("3 subagent")).toBeVisible();
    // 切 Prompt Tab
    await page.getByRole("tab", { name: "Prompt 版本" }).click();
    await expect(page.getByText("requirement-ir-v3")).toBeVisible();
    await expect(page.getByText("草稿")).toBeVisible();
    // 切 Workflow Tab
    await page.getByRole("tab", { name: "Workflow" }).click();
    await expect(page.getByText("gate0-requirement-to-coverage")).toBeVisible();
  });

  test("能力注册：Skill 行弹窗 + 新建 Agent 校验", async ({ page }) => {
    await page.goto("/agent");
    await page.locator("tbody tr").first().click();
    await expect(page.getByRole("heading", { name: "requirement-compiler · V3" })).toBeVisible();
    await expect(page.getByText("ir-input.v3")).toBeVisible();
    await page.getByLabel("关闭").click();
    // 新建 Agent：空标识校验
    await page.getByRole("button", { name: "+ 新建 Agent" }).click();
    await page.getByRole("button", { name: "创建(待激活)" }).click();
    await expect(page.getByText("请输入标识")).toBeVisible();
    // 填写后创建成功 toast
    await page.getByPlaceholder("例如: qf-regression").fill("qf-regression");
    await page.getByRole("button", { name: "创建(待激活)" }).click();
    await expect(page.getByText("Agent 已创建,待治理审核激活(演示)")).toBeVisible();
  });

  test("运行与评测：KPI + Session 行跳 Trace", async ({ page }) => {
    await page.goto("/agent/operations");
    await expect(page.getByRole("heading", { name: "运行与评测" })).toBeVisible();
    await expect(page.getByText("今日 Session")).toBeVisible();
    await expect(page.getByText("27").first()).toBeVisible();
    await expect(page.getByText("92.4%").first()).toBeVisible();
    await expect(page.getByText("run a9f2c1 · 策略生成")).toBeVisible();
    await page.getByText("run a9f2c1 · 策略生成").click();
    await expect(page).toHaveURL(/\/agent\/trace\/a9f2c1/);
  });

  test("Agent Trace：节点步骤 + 元数据 + 授权快照", async ({ page }) => {
    await page.goto("/agent/trace/a9f2c1");
    await expect(page.getByText("Agent Trace · run a9f2c1")).toBeVisible();
    await expect(page.getByText("锁定策略版本 TS V2")).toBeVisible();
    await expect(page.getByText("生成资源与依赖清单")).toBeVisible();
    await expect(page.getByText("运行元数据")).toBeVisible();
    await expect(page.getByText("ses_a9f2c1")).toBeVisible();
    await expect(page.getByRole("heading", { name: "授权快照" })).toBeVisible();
    await expect(page.getByText("allowlist 5")).toBeVisible();
    await expect(page.getByText("deny")).toBeVisible();
    // 返回运行列表
    await page.getByRole("button", { name: "← 返回运行列表" }).click();
    await expect(page).toHaveURL(/\/agent\/operations/);
  });

  test("Trace 页「查看回放」入口：Workflow Tab 可达", async ({ page }) => {
    await page.goto("/agent");
    await page.getByRole("tab", { name: "Workflow" }).click();
    await page.getByRole("button", { name: "查看回放" }).click();
    await expect(page).toHaveURL(/\/agent\/trace\/a9f2c1/);
  });
});
