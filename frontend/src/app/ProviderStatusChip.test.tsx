import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProviderStatusChip } from "./ProviderStatusChip";

describe("ProviderStatusChip（M5 降级状态三态）", () => {
  it("NOMINAL：绿色正常态", () => {
    render(<ProviderStatusChip status={{ status: "NOMINAL", providerId: "zai/glm-4.6" }} />);
    const chip = screen.getByText("AI Provider 正常");
    expect(chip).toBeTruthy();
    expect(chip.closest(".provider-chip")?.className).toContain("st-done");
    expect(chip.closest(".provider-chip")?.getAttribute("title")).toBe("当前 Provider：zai/glm-4.6");
  });

  it("DEGRADED：金色降级态（b-warn + st-review），不用红", () => {
    render(
      <ProviderStatusChip
        status={{
          status: "DEGRADED",
          providerId: "zai/glm-4.6",
          fallbackProviderId: "deterministic-local",
          reason: "provider 超时",
          since: "2026-08-18T10:00:00Z",
        }}
      />,
    );
    const chip = screen.getByText("已降级：本地确定性生成");
    const cls = chip.closest(".provider-chip")?.className ?? "";
    expect(cls).toContain("st-review");
    expect(cls).toContain("b-warn");
    expect(cls).not.toContain("st-blocked");
    expect(chip.closest(".provider-chip")?.getAttribute("title")).toContain("provider 超时");
  });

  it("UNKNOWN：灰色未知态（接口未就绪回落）", () => {
    render(<ProviderStatusChip status={{ status: "UNKNOWN", providerId: "—" }} />);
    const chip = screen.getByText("AI Provider 状态未知");
    expect(chip.closest(".provider-chip")?.className).toContain("st-idle");
  });
});
