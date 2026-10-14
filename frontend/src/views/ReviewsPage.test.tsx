import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { ToastProvider } from "../app/Toast";
import { describe, expect, it, vi } from "vitest";
import type { Profile } from "../types";
import { ReviewsPage } from "./ReviewsPage";
import type { QueueItem } from "../types/domain";

const profile: Profile = {
  userId: "u-1",
  tenantId: "t-1",
  workspaceId: "ws-1",
  email: "lead@qualityforge.local",
  actorType: "USER",
  capabilities: [],
  releaseId: "r-1",
  releaseName: "R-2026.08",
};

function queueItem(overrides: Partial<QueueItem> & { detail?: Partial<QueueItem["detail"]> }): QueueItem {
  const { detail, ...rest } = overrides;
  return {
    id: "q-x",
    workItemId: "WI-0001",
    reviewTaskId: "RT-0001",
    type: "策略",
    typeClass: "strategy",
    title: "TestStrategy V1",
    version: "V1",
    due: "—",
    dueClass: "muted",
    ...rest,
    detail: {
      reviewTask: "RT-0001 · SINGLE_REVIEW",
      policy: "SINGLE_REVIEW",
      artifactVersion: "8c3f2a61-4b7d-4e29-9c55-1f6e0a2b7d10",
      changeSummary: "—",
      aiRun: "—",
      sourceBaseline: "—",
      digest: "sha256:7c41…9b02",
      tabs: { diff: [], trace: [], checks: [], evidence: [] },
      approveDisabledReason: null,
      policyBar: "审核策略: SINGLE_REVIEW",
      ...detail,
    },
  } as QueueItem;
}

const approvedItem = queueItem({
  id: "q-approved",
  reviewTaskId: "RT-4901",
  title: "已批准策略 V1",
  detail: {
    taskStatus: "APPROVED",
    artifactTypeCode: "TEST_STRATEGY",
    artifactId: "5d2e8f47-9a1b-4c63-b8e4-7f0d3a9c2e55",
    minApprovers: 1,
    approvals: [{ actorId: "u-1", decidedAt: "2026-09-05T09:30:00+00:00" }],
  },
} as Partial<QueueItem>);

const fourEyesItem = queueItem({
  id: "q-four-eyes",
  reviewTaskId: "RT-4902",
  title: "双人复核策略 V2",
  detail: {
    policy: "FOUR_EYES",
    reviewTask: "RT-4902 · FOUR_EYES",
    minApprovers: 2,
    approvals: [{ actorId: "u-1", decidedAt: "2026-09-05T10:00:00+00:00" }],
  },
} as Partial<QueueItem>);

const mocks = vi.hoisted(() => ({
  publishStrategyVersion: vi.fn(),
}));

vi.mock("../services/dataService", () => ({
  fetchReviewQueue: vi.fn(async () => [approvedItem, fourEyesItem]),
  fetchArtifactTabContent: vi.fn(async () => null),
  submitReviewDecision: vi.fn(async () => ({})),
  publishStrategyVersion: mocks.publishStrategyVersion,
  publishPlanVersion: vi.fn(async () => ({
    versionId: "v",
    reviewStatus: "PUBLISHED",
  })),
  publishCaseVersion: vi.fn(async () => ({
    versionId: "v",
    reviewStatus: "PUBLISHED",
  })),
}));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/reviews"]}>
      <ToastProvider>
        <Routes>
          <Route element={<Outlet context={{ profile }} />}>
            <Route path="/reviews" element={<ReviewsPage />} />
          </Route>
        </Routes>
      </ToastProvider>
    </MemoryRouter>,
  );
}

describe("ReviewsPage（WP-05 发布链与双人复核）", () => {
  it("FOUR_EYES 任务展示双人复核进度", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("已批准策略 V1");
    await user.click(screen.getByText("双人复核策略 V2"));
    const progress = await screen.findByTestId("four-eyes-progress");
    expect(progress).toHaveTextContent("1/2 名审批人已批准 · 双人复核");
  });

  it("已批准任务走发布确认弹层并展示 PUBLISHED 结果", async () => {
    const user = userEvent.setup();
    mocks.publishStrategyVersion.mockResolvedValueOnce({
      versionId: "8c3f2a61-4b7d-4e29-9c55-1f6e0a2b7d10",
      reviewStatus: "PUBLISHED",
    });
    renderPage();
    await screen.findByText("已批准策略 V1");
    await user.click(screen.getByRole("button", { name: "发布版本" }));
    expect(screen.getByRole("heading", { name: "确认发布" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "确认发布" }));
    expect(mocks.publishStrategyVersion).toHaveBeenCalledWith(
      "5d2e8f47-9a1b-4c63-b8e4-7f0d3a9c2e55",
      "8c3f2a61-4b7d-4e29-9c55-1f6e0a2b7d10",
    );
    expect(await screen.findByText(/reviewStatus PUBLISHED/)).toBeVisible();
    expect(screen.getByRole("button", { name: "已发布" })).toBeDisabled();
  });

  it("发布失败透出后端错误信息", async () => {
    const user = userEvent.setup();
    mocks.publishStrategyVersion.mockRejectedValueOnce(
      new Error("仅 APPROVED 版本可发布"),
    );
    renderPage();
    await screen.findByText("已批准策略 V1");
    await user.click(screen.getByRole("button", { name: "发布版本" }));
    await user.click(screen.getByRole("button", { name: "确认发布" }));
    expect(
      await screen.findByText(/发布失败：仅 APPROVED 版本可发布/),
    ).toBeVisible();
  });
});
