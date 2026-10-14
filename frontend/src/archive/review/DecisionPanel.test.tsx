import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DecisionPanel } from "./DecisionPanel";

/**
 * M1-F1 验收口径（开发计划 v1.1 §四 M1 前端轨 2）：
 * 批准禁用态必须渲染可见原因，四类：权限不足/陈旧版本/前置审核未完成/摘要不一致
 * （+ 职责分离冲突为 Page-Map §3 补充第五类）。
 */
describe("DecisionPanel 批准禁用原因渲染", () => {
  it("无禁用原因时批准按钮可点击，无原因列表", () => {
    render(
      <DecisionPanel
        disabledReasons={[]}
        busy={false}
        comments=""
        onCommentsChange={() => {}}
        onDecide={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: "批准产出物" })).toBeEnabled();
    expect(screen.queryByTestId("approve-blocked-reasons")).not.toBeInTheDocument();
  });

  it("权限不足时批准按钮禁用并渲染可见原因", () => {
    render(
      <DecisionPanel
        disabledReasons={["PERMISSION"]}
        busy={false}
        comments=""
        onCommentsChange={() => {}}
        onDecide={() => {}}
      />,
    );
    const button = screen.getByRole("button", { name: "批准产出物" });
    expect(button).toBeDisabled();
    const reasons = screen.getByTestId("approve-blocked-reasons");
    expect(reasons).toHaveTextContent("当前角色无权批准此产出物");
  });

  it("陈旧版本 + 摘要不一致时两条原因均可见", () => {
    render(
      <DecisionPanel
        disabledReasons={["STALE_VERSION", "DIGEST_MISMATCH"]}
        busy={false}
        comments=""
        onCommentsChange={() => {}}
        onDecide={() => {}}
      />,
    );
    const reasons = screen.getByTestId("approve-blocked-reasons");
    expect(reasons.children).toHaveLength(2);
    expect(reasons).toHaveTextContent("此版本已陈旧");
    expect(reasons).toHaveTextContent("批准摘要与当前内容摘要不一致");
  });

  it("职责分离冲突原因可见", () => {
    render(
      <DecisionPanel
        disabledReasons={["DUTY_SEPARATION"]}
        busy={false}
        comments=""
        onCommentsChange={() => {}}
        onDecide={() => {}}
      />,
    );
    expect(screen.getByTestId("approve-blocked-reasons")).toHaveTextContent("职责分离冲突");
  });

  it("busy 时所有按钮禁用，但原因列表不显示（避免与加载态混淆）", () => {
    render(
      <DecisionPanel
        disabledReasons={["BLOCKING_CHECK"]}
        busy={true}
        comments=""
        onCommentsChange={() => {}}
        onDecide={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: "批准产出物" })).toBeDisabled();
    expect(screen.queryByTestId("approve-blocked-reasons")).not.toBeInTheDocument();
  });

  it("点击退回修改触发 onDecide 回调", () => {
    const onDecide = vi.fn();
    render(
      <DecisionPanel
        disabledReasons={[]}
        busy={false}
        comments=""
        onCommentsChange={() => {}}
        onDecide={onDecide}
      />,
    );
    fireEvent.click(screen.getByText("退回修改"));
    expect(onDecide).toHaveBeenCalledWith("REQUEST_CHANGES");
  });
});
