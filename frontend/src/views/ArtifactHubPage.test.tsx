import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { Profile } from "../types";
import { ArtifactHubPage } from "./ArtifactHubPage";

vi.mock("../services/dataService", () => ({
  fetchStrategies: vi.fn(async () => [
    { id: "TS-1", title: "结算中心主测试策略", version: "V2", scope: "结算", risks: 2, status: "待审核", statusClass: "st-review", action: "审核" },
  ]),
  fetchPlans: vi.fn(async () => [
    { id: "TP-1", title: "结算中心测试计划", version: "V1", lifecycle: "ACTIVE", lifecycleClass: "st-run", milestones: "4 个里程碑", status: "草稿生成中", statusClass: "st-review", depends: "TS-1" },
  ]),
  fetchCases: vi.fn(async () => [
    { id: "DC-1", title: "支付成功", sub: "正向", pri: "P1", status: "待审核", statusClass: "st-review", cover: "REQ-1", coverClass: "b-ok" },
  ]),
  fetchExecutionPlans: vi.fn(async () => [
    { id: "EP-1", title: "回归执行", version: "V1", environment: "staging", trigger: "手工", triggerClass: "b-acc", concurrency: "2", status: "执行中", statusClass: "st-run", frozen: "V1" },
  ]),
  fetchDefects: vi.fn(async () => [
    { id: "D-1", title: "重复回调异常", sub: "支付", severity: "严重", lifecycle: "NEW", lifecycleClass: "st-review", version: "V1", sync: "待批准", syncClass: "b-warn" },
  ]),
  fetchReport: vi.fn(async () => ({
    title: "TestReport R-2026.08",
    ref: "TR-1 草稿 V1",
    kpis: [],
    summary: [],
    gates: [],
  })),
}));

const PROFILE: Profile = {
  userId: "user-test",
  tenantId: "tenant-test",
  workspaceId: "workspace-test",
  email: "lead@example.test",
  actorType: "USER",
  capabilities: [],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/artifacts"]}>
      <Routes>
        <Route element={<Outlet context={{ profile: PROFILE }} />}>
          <Route path="/artifacts" element={<ArtifactHubPage />} />
          <Route path="/planning/strategies" element={<h1>策略详情入口</h1>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("ArtifactHubPage", () => {
  it("以 Release 为主线展示七类测试产出物", async () => {
    renderPage();

    expect(screen.getByRole("heading", { name: "测试产出物" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText("结算中心主测试策略")).toHaveLength(2));
    expect(screen.getAllByRole("button", { name: /查看.+:/ })).toHaveLength(7);
    expect(screen.getByText("1 个严重缺陷未关闭")).toBeInTheDocument();
    expect(screen.getByText("草稿待签署")).toBeInTheDocument();
  });

  it("可以从总览进入具体产出物", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /查看策略:/ }));
    expect(screen.getByRole("heading", { name: "策略详情入口" })).toBeInTheDocument();
  });
});
