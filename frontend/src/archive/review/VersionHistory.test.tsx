import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VersionHistory, type ArtifactVersionRow } from "./VersionHistory";

/**
 * M1-F1 验收口径（开发计划 v1.1 §四 M1 前端轨 3）：
 * 版本历史视图：新旧版本切换 + Diff 摘要（完整 Diff 归 M2）。
 */
describe("VersionHistory 版本历史视图", () => {
  const versions: ArtifactVersionRow[] = [
    {
      versionId: "tp-1-v1",
      versionNo: 1,
      status: "REJECTED",
      createdAt: "2026-08-17T08:00:00Z",
      diffSummary: "初版：基于需求 req-1-v1 生成 8 条用例",
    },
    {
      versionId: "tp-1-v2",
      versionNo: 2,
      status: "CHANGES_REQUESTED",
      createdAt: "2026-08-17T09:00:00Z",
      diffSummary: "按退回意见补充边界值",
    },
    {
      versionId: "tp-1-v3",
      versionNo: 3,
      status: "OPEN",
      createdAt: "2026-08-17T10:00:00Z",
      diffSummary: "新增 2 条用例，删除 1 条",
    },
  ];

  it("渲染全部版本行且 Diff 摘要可见", () => {
    render(<VersionHistory versions={versions} currentVersionId="tp-1-v3" onSelect={() => {}} />);
    const history = screen.getByTestId("version-history");
    expect(history.querySelectorAll("li")).toHaveLength(3);
    expect(history).toHaveTextContent("v1");
    expect(history).toHaveTextContent("v3");
    expect(history).toHaveTextContent("初版：基于需求 req-1-v1 生成 8 条用例");
    expect(history).toHaveTextContent("新增 2 条用例，删除 1 条");
  });

  it("当前版本行带 aria-current 标识", () => {
    render(<VersionHistory versions={versions} currentVersionId="tp-1-v3" onSelect={() => {}} />);
    const currentRow = screen.getByRole("button", { name: /v3/ });
    expect(currentRow).toHaveAttribute("aria-current", "true");
    const otherRow = screen.getByRole("button", { name: /v1/ });
    expect(otherRow).not.toHaveAttribute("aria-current");
  });

  it("点击历史版本触发 onSelect 回调", () => {
    const onSelect = vi.fn();
    render(<VersionHistory versions={versions} currentVersionId="tp-1-v3" onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button", { name: /v1/ }));
    expect(onSelect).toHaveBeenCalledWith("tp-1-v1");
  });

  it("无 Diff 摘要时显示占位文案", () => {
    const noDiff: ArtifactVersionRow[] = [
      { versionId: "tp-1-v1", versionNo: 1, status: "OPEN", createdAt: "2026-08-17T08:00:00Z", diffSummary: "" },
    ];
    render(<VersionHistory versions={noDiff} currentVersionId="tp-1-v1" onSelect={() => {}} />);
    expect(screen.getByTestId("version-history")).toHaveTextContent("无 Diff 摘要");
  });
});
