import { expect, test } from "@playwright/test";

/**
 * WP-01A 工作区切换（真实后端，无 mock）：
 * 登录 → 当前工作区建探针工作项 → 顶栏切换到第二项目 → Release 重置、旧数据不残留、新上下文可写。
 * 前置：后端 8000 已初始化（admin@test.com / Test1234567890），
 * 且已运行 backend/scripts/qf_seed_workspace.py 种子第二项目（否则本件 skip）。
 */

test.describe("WP-01A 工作区切换", () => {
  test("切换后重置 Release、旧工作区数据不残留、新上下文可写", async ({
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

    const workspaces = (
      await (await page.request.get("/api/v1/workspaces")).json()
    ).data as Array<{
      id: string;
      name: string;
    }>;
    const me = (await (await page.request.get("/api/v1/auth/me")).json())
      .data as {
      workspaceId: string;
    };
    const target = workspaces.find((ws) => ws.id !== me.workspaceId);
    test.skip(
      !target,
      "需要先种子第二个工作区（backend/scripts/qf_seed_workspace.py）",
    );

    // 当前工作区建探针工作项（稍后验证切换后不残留）
    const probeTitle = `切换残留探针 ${Date.now()}`;
    await page.goto("/board");
    await page.getByRole("button", { name: "新建工作项" }).click();
    await page.fill('input[name="title"]', probeTitle);
    await page.selectOption('select[name="type"]', { label: "用例" });
    await page
      .locator("#newItemForm")
      .evaluate((form: HTMLFormElement) => form.requestSubmit());
    await expect(page.locator(".toast.ok")).toBeVisible();
    await expect(
      page.locator("tbody").getByText(probeTitle).first(),
    ).toBeVisible();

    // 顶栏切换到第二项目
    const currentName =
      workspaces.find((ws) => ws.id === me.workspaceId)?.name ?? "当前项目";
    await page.getByRole("button", { name: currentName, exact: false }).click();
    await page
      .locator("#m-ws-switch")
      .locator("div.row", { hasText: target!.name })
      .first()
      .click();
    await expect(page.locator(".toast.ok")).toBeVisible();

    // Release 重置为第二项目的默认发布
    await expect(
      page.getByRole("button", { name: /Release 默认发布/ }),
    ).toBeVisible();

    // 看板：旧工作区数据不残留
    await page.goto("/board");
    await expect(page.getByRole("heading", { name: "工作看板" })).toBeVisible();
    await expect(page.getByText(probeTitle)).toHaveCount(0);

    // 新上下文可写：第二项目建工作项
    const secondTitle = `第二项目用例 ${Date.now()}`;
    await page.getByRole("button", { name: "新建工作项" }).click();
    await page.fill('input[name="title"]', secondTitle);
    await page.selectOption('select[name="type"]', { label: "用例" });
    await page
      .locator("#newItemForm")
      .evaluate((form: HTMLFormElement) => form.requestSubmit());
    await expect(page.locator(".toast.ok")).toBeVisible();
    await expect(
      page.locator("tbody").getByText(secondTitle).first(),
    ).toBeVisible();
  });
});
