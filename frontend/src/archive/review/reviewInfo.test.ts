import { describe, expect, it } from "vitest";

import { missingReviewInfoItems, type ReviewDetailData } from "./reviewInfo";

/**
 * M1-F1 验收口径（开发计划 v1.1 §四 M1 前端轨 1）：审核台呈现 Page-Map §3 最低信息。
 * Page-Map §3 原文：「审核页必须同时展示：产出物类型/稳定ID/版本ID/摘要、来源版本、
 * 变更Diff、AI/人工作者、确定性检查、独立验证、Evidence、风险、ReviewPolicy、
 * 职责分离、历史决定和陈旧状态。」共 15 项。
 */
describe("reviewInfo 审核台最低信息完整性", () => {
  const complete: ReviewDetailData = {
    artifactType: "TEST_PLAN",
    artifactId: "tp-1",
    artifactVersionId: "tp-1-v3",
    contentDigest: "sha256:abcd",
    sourceVersionId: "req-1-v2",
    diffSummary: "新增 2 条用例，删除 1 条",
    authors: { providerId: "deterministic-local", humanActorName: "王小明" },
    deterministicCheck: { status: "PASSED", detail: "结构判分 100" },
    independentVerification: { status: "PASSED", detail: "独立验证通过" },
    evidence: [{ kind: "TRACE", label: "生成轨迹 12 步" }],
    risk: { level: "HIGH", note: "涉及退款金额计算" },
    policyType: "TEST_PLAN_REVIEW",
    dutySeparation: { conflicted: false, note: "作者与审核者不同主体" },
    historyDecisions: [{ decision: "REQUEST_CHANGES", by: "李四", at: "2026-08-17T10:00:00Z" }],
    staleStatus: { stale: false, latestVersionId: "tp-1-v3" },
  };

  it("数据齐全时缺失列表为空", () => {
    expect(missingReviewInfoItems(complete)).toEqual([]);
  });

  it("全空数据时缺失全部 15 项", () => {
    expect(missingReviewInfoItems({})).toHaveLength(15);
  });

  it("缺来源版本与变更 Diff 时精确报出这两项", () => {
    const { sourceVersionId: _s, diffSummary: _d, ...rest } = complete;
    expect(missingReviewInfoItems(rest)).toEqual(["来源版本", "变更Diff"]);
  });

  it("缺 Evidence 与陈旧状态时精确报出这两项", () => {
    const { evidence: _e, staleStatus: _t, ...rest } = complete;
    expect(missingReviewInfoItems(rest)).toEqual(["Evidence", "陈旧状态"]);
  });

  it("摘要缺失判定为空字符串同样报缺", () => {
    const withEmptyDigest: ReviewDetailData = { ...complete, contentDigest: "" };
    expect(missingReviewInfoItems(withEmptyDigest)).toContain("摘要");
  });
});
