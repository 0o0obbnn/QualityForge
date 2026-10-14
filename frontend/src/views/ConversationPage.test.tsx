import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { ConversationRow, Profile } from "../types";
import { ConversationPage } from "./ConversationPage";

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

const conversations: ConversationRow[] = [
  {
    id: "c-1",
    title: "退款策略协作",
    status: "ACTIVE",
    releaseId: "r-1",
    workItemId: null,
    lastActivityAt: "2026-08-30T09:30:00+00:00",
  },
];

const mocks = vi.hoisted(() => ({
  created: {
    id: "c-2",
    title: "新会话",
    status: "ACTIVE",
    releaseId: "r-1",
    workItemId: null,
    lastActivityAt: "2026-08-31T08:00:00+00:00",
  },
  appended: {
    id: "m-9",
    conversationId: "c-1",
    actorType: "USER" as const,
    actorId: "u-1",
    messageType: "TEXT",
    contentRef: "第一条协作消息",
    contentDigest: "0".repeat(64),
    dataClass: "INTERNAL" as const,
    createdAt: "2026-08-31T08:01:00+00:00",
  },
}));

vi.mock("../services/dataService", () => ({
  fetchConversations: vi.fn(async () => [...conversations, mocks.created]),
  createConversation: vi.fn(async () => mocks.created),
  fetchConversationMessages: vi.fn(async (conversationId: string) =>
    conversationId === "c-1"
      ? [
          {
            id: "m-1",
            conversationId,
            actorType: "AGENT",
            actorId: "agent-1",
            messageType: "TEXT",
            contentRef: "已归纳 3 条业务规则",
            contentDigest: "0".repeat(64),
            dataClass: "INTERNAL",
            createdAt: "2026-08-30T09:05:00+00:00",
          },
        ]
      : [],
  ),
  appendConversationMessage: vi.fn(async () => mocks.appended),
}));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/conversations"]}>
      <Routes>
        <Route element={<Outlet context={{ profile }} />}>
          <Route path="/conversations" element={<ConversationPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("ConversationPage（WP-03 前端接入）", () => {
  it("渲染会话列表与选中会话的消息流", async () => {
    renderPage();
    expect((await screen.findAllByText("退款策略协作")).length).toBeGreaterThan(
      0,
    );
    expect(await screen.findByText("已归纳 3 条业务规则")).toBeVisible();
    expect(screen.getByText("新会话")).toBeVisible();
  });

  it("发送消息追加到当前会话消息流", async () => {
    renderPage();
    await screen.findByText("已归纳 3 条业务规则");
    const input = screen.getByLabelText("消息内容");
    await userEvent.type(input, "第一条协作消息");
    await userEvent.click(screen.getByRole("button", { name: "发送" }));
    await waitFor(() => {
      expect(screen.getByText("第一条协作消息")).toBeVisible();
    });
  });

  it("新建会话：标题必填，提交后关闭弹层并选中新会话", async () => {
    renderPage();
    await screen.findAllByText("退款策略协作");
    await userEvent.click(screen.getByRole("button", { name: /新建会话/ }));
    const createButton = screen.getByRole("button", { name: "创建" });
    expect(createButton).toBeDisabled();
    await userEvent.type(screen.getByLabelText("会话主题"), "新会话");
    expect(createButton).toBeEnabled();
    await userEvent.click(createButton);
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "新建协作会话" })).toBeNull();
    });
  });
});
