import { Button, Field, Textarea } from "@fluentui/react-components";
import {
  CheckmarkCircleRegular,
  DismissCircleRegular,
} from "@fluentui/react-icons";

import {
  approveDisabledReasonLabel,
  type ApproveDisabledReason,
} from "./approveGate";

/**
 * 审核决定面板（M1-F1）：批准/退回修改/拒绝三个动作。
 * 批准禁用时必须渲染可见原因（开发计划 v1.1 §四 M1 前端轨 2；
 * 前端禁用不是授权边界，服务端仍会校验）。
 */

export interface DecisionPanelProps {
  disabledReasons: ApproveDisabledReason[];
  busy: boolean;
  comments: string;
  onCommentsChange: (value: string) => void;
  onDecide: (decision: "APPROVE" | "REQUEST_CHANGES" | "REJECT") => void;
}

export function DecisionPanel({
  disabledReasons,
  busy,
  comments,
  onCommentsChange,
  onDecide,
}: DecisionPanelProps) {
  const approveDisabled = disabledReasons.length > 0 || busy;
  return (
    <div className="decision-panel" data-testid="decision-panel">
      <Field label="审核意见" hint="退回或拒绝时请说明原因">
        <Textarea value={comments} onChange={(_, data) => onCommentsChange(data.value)} resize="vertical" />
      </Field>
      <div className="decision-actions">
        <Button
          appearance="primary"
          icon={<CheckmarkCircleRegular />}
          aria-label="批准产出物"
          disabled={approveDisabled}
          onClick={() => onDecide("APPROVE")}
        >
          批准
        </Button>
        <Button disabled={busy} onClick={() => onDecide("REQUEST_CHANGES")}>
          退回修改
        </Button>
        <Button
          appearance="secondary"
          icon={<DismissCircleRegular />}
          aria-label="拒绝产出物"
          disabled={busy}
          onClick={() => onDecide("REJECT")}
        >
          拒绝
        </Button>
      </div>
      {disabledReasons.length > 0 && !busy && (
        <ul className="approve-blocked-reasons" data-testid="approve-blocked-reasons" aria-live="polite">
          {disabledReasons.map((reason) => (
            <li key={reason}>{approveDisabledReasonLabel(reason)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
