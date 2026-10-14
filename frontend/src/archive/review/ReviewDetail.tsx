import { Badge } from "@fluentui/react-components";

import type { ReviewDetailData } from "./reviewInfo";

/**
 * 审核详情信息区（M1-F1）：按 Page-Map §3 渲染 15 项最低信息。
 * 纯展示组件，输入为 ReviewDetailData，缺项渲染为「—」占位，
 * 数据完整性判定由 reviewInfo.missingReviewInfoItems 负责（验收核对表用它自动化）。
 */

const STATUS_LABELS: Record<string, string> = {
  PASSED: "通过",
  FAILED: "未通过",
  PENDING: "待执行",
};

function CheckStatus({ status }: { status?: string }) {
  if (!status) return <span>—</span>;
  return (
    <Badge
      appearance="tint"
      color={status === "PASSED" ? "success" : status === "FAILED" ? "danger" : "informative"}
    >
      {STATUS_LABELS[status] ?? status}
    </Badge>
  );
}

export function ReviewDetail({ data }: { data: ReviewDetailData }) {
  return (
    <dl className="artifact-meta artifact-meta-full" data-testid="review-detail">
      <div>
        <dt>产出物类型</dt>
        <dd>{data.artifactType ?? "—"}</dd>
      </div>
      <div>
        <dt>稳定ID</dt>
        <dd>{data.artifactId ?? "—"}</dd>
      </div>
      <div>
        <dt>版本ID</dt>
        <dd>{data.artifactVersionId ?? "—"}</dd>
      </div>
      <div>
        <dt>摘要</dt>
        <dd className="mono">{data.contentDigest || "—"}</dd>
      </div>
      <div>
        <dt>来源版本</dt>
        <dd className="mono">{data.sourceVersionId ?? "—"}</dd>
      </div>
      <div>
        <dt>变更Diff</dt>
        <dd>{data.diffSummary ?? "—"}</dd>
      </div>
      <div>
        <dt>AI/人工作者</dt>
        <dd>
          {data.authors?.providerId ?? "—"}
          {data.authors?.humanActorName ? ` · ${data.authors.humanActorName}` : ""}
        </dd>
      </div>
      <div>
        <dt>确定性检查</dt>
        <dd>
          <CheckStatus status={data.deterministicCheck?.status} />
          {data.deterministicCheck?.detail ? ` ${data.deterministicCheck.detail}` : ""}
        </dd>
      </div>
      <div>
        <dt>独立验证</dt>
        <dd>
          <CheckStatus status={data.independentVerification?.status} />
          {data.independentVerification?.detail ? ` ${data.independentVerification.detail}` : ""}
        </dd>
      </div>
      <div>
        <dt>Evidence</dt>
        <dd>
          {(data.evidence?.length ?? 0) > 0
            ? data.evidence!.map((item) => `${item.kind ?? "—"}：${item.label ?? ""}`).join("；")
            : "—"}
        </dd>
      </div>
      <div>
        <dt>风险</dt>
        <dd>
          {data.risk?.level ? (
            <Badge appearance="tint" color={data.risk.level === "HIGH" ? "danger" : "informative"}>
              {data.risk.level}
            </Badge>
          ) : (
            "—"
          )}
          {data.risk?.note ? ` ${data.risk.note}` : ""}
        </dd>
      </div>
      <div>
        <dt>ReviewPolicy</dt>
        <dd className="mono">{data.policyType ?? "—"}</dd>
      </div>
      <div>
        <dt>职责分离</dt>
        <dd>
          {typeof data.dutySeparation?.conflicted === "boolean" ? (
            <Badge
              appearance="tint"
              color={data.dutySeparation.conflicted ? "danger" : "success"}
            >
              {data.dutySeparation.conflicted ? "冲突" : "无冲突"}
            </Badge>
          ) : (
            "—"
          )}
          {data.dutySeparation?.note ? ` ${data.dutySeparation.note}` : ""}
        </dd>
      </div>
      <div>
        <dt>历史决定</dt>
        <dd>
          {(data.historyDecisions?.length ?? 0) > 0
            ? data.historyDecisions!
                .map((item) => `${item.decision ?? "—"}（${item.by ?? "?"} ${item.at ?? ""}）`)
                .join("；")
            : "—"}
        </dd>
      </div>
      <div>
        <dt>陈旧状态</dt>
        <dd>
          {typeof data.staleStatus?.stale === "boolean" ? (
            <Badge appearance="tint" color={data.staleStatus.stale ? "warning" : "success"}>
              {data.staleStatus.stale
                ? `陈旧（最新 ${data.staleStatus.latestVersionId ?? "?"}）`
                : "当前"}
            </Badge>
          ) : (
            "—"
          )}
        </dd>
      </div>
    </dl>
  );
}
