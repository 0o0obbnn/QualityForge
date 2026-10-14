import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReviewDetail } from "./ReviewDetail";
import type { ReviewDetailData } from "./reviewInfo";

/**
 * M1-F1 验收口径（开发计划 v1.1 §四 M1 前端轨 1）：
 * 审核台呈现 Page-Map §3 的 15 项最低信息（逐项核对表自动化基础）。
 */
describe("ReviewDetail 审核详情 15 项信息渲染", () => {
  const full: ReviewDetailData = {
    artifactType: "TEST_PLAN",
    artifactId: "tp-1",
    artifactVersionId: "tp-1-v3",
    contentDigest: "sha256:abcd",
    sourceVersionId: "req-1-v2",
    diffSummary: "新增 2 条用例",
    authors: { providerId: "deterministic-local", humanActorName: "王小明" },
    deterministicCheck: { status: "PASSED", detail: "结构判分 100" },
    independentVerification: { status: "PASSED", detail: "独立验证通过" },
    evidence: [{ kind: "TRACE", label: "生成轨迹 12 步" }],
    risk: { level: "HIGH", note: "退款金额" },
    policyType: "TEST_PLAN_REVIEW",
    dutySeparation: { conflicted: false, note: "不同主体" },
    historyDecisions: [{ decision: "REQUEST_CHANGES", by: "李四", at: "2026-08-17T11:00:00Z" }],
    staleStatus: { stale: false, latestVersionId: "tp-1-v3" },
  };

  it("数据齐全时渲染全部 15 项，无「—」占位", () => {
    render(<ReviewDetail data={full} />);
    const detail = screen.getByTestId("review-detail");
    // 15 项 dt 标题
    expect(detail.querySelectorAll("dt")).toHaveLength(15);
    // 关键值可见
    expect(detail).toHaveTextContent("TEST_PLAN");
    expect(detail).toHaveTextContent("tp-1");
    expect(detail).toHaveTextContent("tp-1-v3");
    expect(detail).toHaveTextContent("sha256:abcd");
    expect(detail).toHaveTextContent("req-1-v2");
    expect(detail).toHaveTextContent("新增 2 条用例");
    expect(detail).toHaveTextContent("deterministic-local");
    expect(detail).toHaveTextContent("王小明");
    expect(detail).toHaveTextContent("结构判分 100");
    expect(detail).toHaveTextContent("独立验证通过");
    expect(detail).toHaveTextContent("生成轨迹 12 步");
    expect(detail).toHaveTextContent("退款金额");
    expect(detail).toHaveTextContent("TEST_PLAN_REVIEW");
    expect(detail).toHaveTextContent("不同主体");
    expect(detail).toHaveTextContent("REQUEST_CHANGES");
    expect(detail).toHaveTextContent("李四");
    expect(detail).toHaveTextContent("当前");
    // 无「—」占位（所有 dd 不等于 —）
    const placeholders = Array.from(detail.querySelectorAll("dd")).filter(
      (dd) => dd.textContent === "—",
    );
    expect(placeholders).toHaveLength(0);
  });

  it("缺来源版本与 Diff 时对应位置渲染「—」", () => {
    const { sourceVersionId: _s, diffSummary: _d, ...rest } = full;
    render(<ReviewDetail data={rest} />);
    const detail = screen.getByTestId("review-detail");
    const dds = Array.from(detail.querySelectorAll("dd"));
    // 来源版本第 5 个 dt/dd
    expect(dds[4].textContent).toBe("—");
    expect(dds[5].textContent).toBe("—");
    // 其余仍有值
    expect(dds[0].textContent).toBe("TEST_PLAN");
  });
});
