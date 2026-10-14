import { Badge } from "@fluentui/react-components";

import { statusBadgeAppearance, statusBadgeColor, statusLabel } from "../statusBadge";

/**
 * 版本历史视图（M1-F1）：同一产出物新旧版本切换查看，Diff 摘要可见。
 * 完整 Diff 归 M2（开发计划 v1.1 §四 M1 前端轨 3）。
 */

export interface ArtifactVersionRow {
  versionId: string;
  versionNo: number;
  status: string;
  createdAt: string;
  diffSummary: string;
}

export interface VersionHistoryProps {
  versions: ArtifactVersionRow[];
  currentVersionId?: string;
  onSelect: (versionId: string) => void;
}

function formatTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

export function VersionHistory({ versions, currentVersionId, onSelect }: VersionHistoryProps) {
  return (
    <ol className="version-history" data-testid="version-history" aria-label="版本历史">
      {versions.map((version) => {
        const isCurrent = version.versionId === currentVersionId;
        return (
          <li key={version.versionId} className={isCurrent ? "version-row current" : "version-row"}>
            <button type="button" onClick={() => onSelect(version.versionId)} aria-current={isCurrent ? "true" : undefined}>
              <span className="version-no">v{version.versionNo}</span>
              <Badge appearance={statusBadgeAppearance(version.status)} color={statusBadgeColor(version.status)} size="small">
                {statusLabel(version.status)}
              </Badge>
              <span className="version-time">{formatTime(version.createdAt)}</span>
              <span className="version-diff">{version.diffSummary || "无 Diff 摘要"}</span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
