import { describe, expect, it } from "vitest";

import { statusBadgeAppearance, statusBadgeColor, statusLabel } from "./statusBadge";

/**
 * 契约状态展示断言（wall VERDICT req-contract-reconciliation 批次结束条件）：
 * 运行/审核状态必须按契约枚举正确映射，FAILED 必须渲染为 danger，
 * 且已废弃的幽灵值（BLOCK_HUMAN/PAUSED_FOR_HUMAN/COMPLETED）不得获得语义化映射。
 */
describe("statusBadge 契约状态映射", () => {
  it("FAILED 渲染为 danger（失败不得显示为中性色）", () => {
    expect(statusBadgeColor("FAILED")).toBe("danger");
    expect(statusLabel("FAILED")).toBe("失败");
  });

  it("REJECTED 渲染为 danger、APPROVED 渲染为 success 实心", () => {
    expect(statusBadgeColor("REJECTED")).toBe("danger");
    expect(statusBadgeColor("APPROVED")).toBe("success");
    expect(statusBadgeAppearance("APPROVED")).toBe("filled");
  });

  it("AgentSession 权威枚举（03 §13.13）均有中文文案，无回落原值", () => {
    for (const status of ["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "BLOCKED"]) {
      expect(statusLabel(status)).not.toBe(status);
    }
    expect(statusLabel("SUCCEEDED")).toBe("已完成");
    expect(statusLabel("BLOCKED")).toBe("已阻塞");
  });

  it("废弃幽灵值无语义映射（原样回落，防止误用复活）", () => {
    expect(statusLabel("BLOCK_HUMAN")).toBe("BLOCK_HUMAN");
    expect(statusLabel("PAUSED_FOR_HUMAN")).toBe("PAUSED_FOR_HUMAN");
    expect(statusBadgeColor("BLOCK_HUMAN")).toBe("informative");
  });

  it("EXPIRED/CANCELLED 有中文映射且 EXPIRED 为 danger（陈旧状态依赖，M1-F1 补齐）", () => {
    expect(statusLabel("EXPIRED")).toBe("已过期");
    expect(statusLabel("CANCELLED")).toBe("已取消");
    expect(statusBadgeColor("EXPIRED")).toBe("danger");
    expect(statusBadgeColor("CANCELLED")).toBe("informative");
  });
});
