import { describe, expect, it } from "vitest";

import {
  approveDisabledReasons,
  approveDisabledReasonLabel,
  type ApproveGateInput,
} from "./approveGate";

/**
 * M1-F1 验收口径（开发计划 v1.1 §四 M1 前端轨 2）：
 * 批准按钮禁用时必须渲染可见原因，四类：权限不足 / 陈旧版本 / 前置审核未完成 / 摘要不一致。
 * 契约补充口径（Page-Map §3）：职责分离冲突同属禁用原因。
 */
describe("approveGate 批准禁用原因判定", () => {
  const base: ApproveGateInput = {
    canDecide: true,
    staleVersion: false,
    blockingChecks: [],
    digestMatches: true,
    dutySeparationConflict: false,
    taskClosed: false,
  };

  it("无任何问题时返回空数组（批准可用）", () => {
    expect(approveDisabledReasons(base)).toEqual([]);
  });

  it("权限不足 → PERMISSION，且为唯一原因时不重复", () => {
    const reasons = approveDisabledReasons({ ...base, canDecide: false });
    expect(reasons).toEqual(["PERMISSION"]);
  });

  it("五类原因齐全时全部判定（含职责分离）", () => {
    const reasons = approveDisabledReasons({
      canDecide: false,
      staleVersion: true,
      blockingChecks: ["deterministic-check"],
      digestMatches: false,
      dutySeparationConflict: true,
      taskClosed: false,
    });
    expect(reasons).toContain("PERMISSION");
    expect(reasons).toContain("STALE_VERSION");
    expect(reasons).toContain("BLOCKING_CHECK");
    expect(reasons).toContain("DIGEST_MISMATCH");
    expect(reasons).toContain("DUTY_SEPARATION");
    expect(reasons).toHaveLength(5);
  });

  it("摘要不一致且版本陈旧 → 两条原因均可见", () => {
    const reasons = approveDisabledReasons({ ...base, staleVersion: true, digestMatches: false });
    expect(reasons).toEqual(["STALE_VERSION", "DIGEST_MISMATCH"]);
  });

  it("任务已结 → TASK_CLOSED（墙 M-121 契约实际值）", () => {
    const reasons = approveDisabledReasons({ ...base, taskClosed: true });
    expect(reasons).toEqual(["TASK_CLOSED"]);
  });

  it("所有原因均有中文文案，无回落枚举原值", () => {
    for (const reason of [
      "PERMISSION",
      "STALE_VERSION",
      "BLOCKING_CHECK",
      "DIGEST_MISMATCH",
      "DUTY_SEPARATION",
      "TASK_CLOSED",
    ] as const) {
      expect(approveDisabledReasonLabel(reason)).not.toBe(reason);
    }
    expect(approveDisabledReasonLabel("PERMISSION")).toBe("当前角色无权批准此产出物");
    expect(approveDisabledReasonLabel("TASK_CLOSED")).toBe("任务已结，无法再批准");
  });
});
