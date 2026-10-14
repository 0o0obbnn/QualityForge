/**
 * 审核台最低信息完整性判定（M1-F1）。
 *
 * 权威源：Page-Map §3「审核界面最低信息」——审核页必须同时展示 15 项。
 * 该函数用于：① 渲染前对数据做完整性检查；② 验收核对表自动化（缺失项直接生成）。
 * 纯函数层，便于 vitest 契约测试守护。
 */

export interface ReviewDetailData {
  artifactType?: string;
  artifactId?: string;
  artifactVersionId?: string;
  contentDigest?: string;
  sourceVersionId?: string;
  diffSummary?: string;
  authors?: { providerId?: string; humanActorName?: string };
  deterministicCheck?: { status?: string; detail?: string };
  independentVerification?: { status?: string; detail?: string };
  evidence?: Array<{ kind?: string; label?: string }>;
  risk?: { level?: string; note?: string };
  policyType?: string;
  dutySeparation?: { conflicted?: boolean; note?: string };
  historyDecisions?: Array<{ decision?: string; by?: string; at?: string }>;
  staleStatus?: { stale?: boolean; latestVersionId?: string };
}

interface InfoItem {
  label: string;
  present: (data: ReviewDetailData) => boolean;
}

/** Page-Map §3 的 15 项最低信息，按原文顺序。 */
const INFO_ITEMS: InfoItem[] = [
  { label: "产出物类型", present: (d) => Boolean(d.artifactType) },
  { label: "稳定ID", present: (d) => Boolean(d.artifactId) },
  { label: "版本ID", present: (d) => Boolean(d.artifactVersionId) },
  { label: "摘要", present: (d) => Boolean(d.contentDigest) },
  { label: "来源版本", present: (d) => Boolean(d.sourceVersionId) },
  { label: "变更Diff", present: (d) => Boolean(d.diffSummary) },
  {
    label: "AI/人工作者",
    present: (d) => Boolean(d.authors?.providerId && d.authors.humanActorName),
  },
  { label: "确定性检查", present: (d) => Boolean(d.deterministicCheck?.status) },
  { label: "独立验证", present: (d) => Boolean(d.independentVerification?.status) },
  { label: "Evidence", present: (d) => (d.evidence?.length ?? 0) > 0 },
  { label: "风险", present: (d) => Boolean(d.risk?.level) },
  { label: "ReviewPolicy", present: (d) => Boolean(d.policyType) },
  { label: "职责分离", present: (d) => typeof d.dutySeparation?.conflicted === "boolean" },
  { label: "历史决定", present: (d) => (d.historyDecisions?.length ?? 0) > 0 },
  { label: "陈旧状态", present: (d) => typeof d.staleStatus?.stale === "boolean" },
];

export function missingReviewInfoItems(data: ReviewDetailData): string[] {
  return INFO_ITEMS.filter((item) => !item.present(data)).map((item) => item.label);
}

export function reviewInfoItemCount(): number {
  return INFO_ITEMS.length;
}
