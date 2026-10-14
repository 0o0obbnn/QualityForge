import type { ProviderStatus } from "../types";

/**
 * AI Provider 状态 chip（M5 真实模型准入 · 降级状态呈现）。
 * 三态：
 * - NOMINAL：绿色（.st-done），Provider 正常
 * - DEGRADED：金色 warning（.st-review + .b-warn）——deterministic-local 是计划内 failover 与评估锚点，降级≠故障，不用红
 * - UNKNOWN：灰色（.st-idle），接口未就绪/异常回落
 */
export function ProviderStatusChip({ status }: { status: ProviderStatus }) {
  if (status.status === "DEGRADED") {
    return (
      <span
        className="provider-chip b-warn st-review"
        title={
          status.reason
            ? `已降级：${status.reason}（${status.since ?? "时间未知"} 起）`
            : `已降级：${status.fallbackProviderId ?? "本地确定性生成"}（${status.since ?? "时间未知"} 起）`
        }
      >
        <span className="d" />
        已降级：本地确定性生成
      </span>
    );
  }
  if (status.status === "UNKNOWN") {
    return (
      <span className="provider-chip st-idle" title="Provider 状态接口未就绪或不可达">
        <span className="d" />
        AI Provider 状态未知
      </span>
    );
  }
  return (
    <span className="provider-chip st-done" title={`当前 Provider：${status.providerId}`}>
      <span className="d" />
      AI Provider 正常
    </span>
  );
}
