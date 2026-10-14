#!/usr/bin/env python3
"""
HITL Gatekeeper 裁决路由器。

确定性策略执行，刻意不引入 LLM：路由逻辑正是模型容易漂移的地方，
因此只在此处编码一次。

置信度是证据元数据，不是授权机制。任何正式产出物和任何强制检查点
无论分数高低都路由到 BLOCK_HUMAN。非正式机器步骤在无强制检查点时
可继续；后续的正式产出物门禁仍然不可跳过。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
import uuid

FORCED_CHECKPOINT_EVENTS = frozenset(
    {
        "critical_path",
        "contract_mutation",
        "breaking_drift",
        "healing_overrun",
    }
)
FORMAL_ASSET_TYPES = frozenset(
    {
        "test_strategy",
        "test_plan",
        "test_case",
        "automation_script",
        "result_analysis",
        "defect",
        "test_report",
        "knowledge_entry",
    }
)

REQUIRED_FIELDS = ("event_type", "asset_type", "source_trace", "proposed_action")
VALID_EVENT_TYPES = FORCED_CHECKPOINT_EVENTS | {"inference", "ambiguity_flag"}
VALID_ASSET_TYPES = (
    frozenset(
        {
            "requirement",
            "rule",
            "scenario",
            "case",
            "assertion",
            "locator",
            "fixture",
            "contract",
        }
    )
    | FORMAL_ASSET_TYPES
)

SLA_SECONDS = {
    "critical_path": 4 * 3600,
    "contract_mutation": 24 * 3600,
    "breaking_drift": 24 * 3600,
    "healing_overrun": 8 * 3600,
    "default": 48 * 3600,
}


def _trace_id(source_trace, proposed_action):
    h = hashlib.sha1(f"{source_trace}|{proposed_action}".encode("utf-8")).hexdigest()
    return f"TRC-{h[:12]}"


def decide(
    *,
    event_type,
    asset_type,
    source_trace,
    proposed_action,
    confidence=None,
    ir_element_id=None,
    artifact_id=None,
    artifact_version_id=None,
    content_digest=None,
    policy_type=None,
):
    if asset_type in FORMAL_ASSET_TYPES:
        return _block(
            reason="正式产出物必须由授权的人工 ReviewDecision 裁决；置信度不参与该决定。",
            policy_clause="policy.md#正式产出物",
            confidence=confidence,
            event_type=event_type,
            asset_type=asset_type,
            source_trace=source_trace,
            proposed_action=proposed_action,
            ir_element_id=ir_element_id,
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            content_digest=content_digest,
            policy_type=policy_type,
        )
    if event_type in FORCED_CHECKPOINT_EVENTS:
        return _block(
            reason=f"强制检查点：{event_type}。该事件类型不参考置信度。",
            policy_clause="policy.md#强制检查点",
            confidence=confidence,
            event_type=event_type,
            asset_type=asset_type,
            source_trace=source_trace,
            proposed_action=proposed_action,
            ir_element_id=ir_element_id,
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            content_digest=content_digest,
            policy_type=policy_type,
        )

    if event_type == "ambiguity_flag":
        return _block(
            reason="调用方 skill 已发出 NEED_HUMAN_REVIEW（歧义/冲突/来源缺失）。模型不得编造解决方案。",
            policy_clause="policy.md#强制检查点",
            confidence=confidence,
            event_type=event_type,
            asset_type=asset_type,
            source_trace=source_trace,
            proposed_action=proposed_action,
            ir_element_id=ir_element_id,
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            content_digest=content_digest,
            policy_type=policy_type,
        )

    if confidence is None:
        return _block(
            reason="inference 事件缺少置信度分数；缺失的分数不是高分。",
            policy_clause="policy.md#置信度不是授权",
            confidence=None,
            event_type=event_type,
            asset_type=asset_type,
            source_trace=source_trace,
            proposed_action=proposed_action,
            ir_element_id=ir_element_id,
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            content_digest=content_digest,
            policy_type=policy_type,
        )

    return _pass(
        confidence, event_type, asset_type, source_trace, proposed_action, ir_element_id
    )


def _base(event_type, asset_type, source_trace, proposed_action, ir_element_id):
    return {
        "trace_id": _trace_id(source_trace, proposed_action),
        "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "skill": "28",
        "event_type": event_type,
        "asset_type": asset_type,
        "source_trace": source_trace,
        "proposed_action": proposed_action,
        "ir_element_id": ir_element_id,
        "sla_seconds": SLA_SECONDS.get(event_type, SLA_SECONDS["default"]),
    }


def _pass(
    confidence, event_type, asset_type, source_trace, proposed_action, ir_element_id
):
    reason = "非正式机器步骤可继续；置信度仅作记录，不授权任何资产变更。"
    return {
        "decision": "PASS",
        "reason": reason,
        "policy_clause": "policy.md#置信度不是授权",
        "confidence": confidence,
        "review_task": None,
        "audit": _base(
            event_type, asset_type, source_trace, proposed_action, ir_element_id
        ),
    }


def _block(
    *,
    reason,
    policy_clause,
    confidence,
    event_type,
    asset_type,
    source_trace,
    proposed_action,
    ir_element_id,
    artifact_id,
    artifact_version_id,
    content_digest,
    policy_type,
):
    severity = "forced" if event_type in FORCED_CHECKPOINT_EVENTS else "required"
    return {
        "decision": "BLOCK_HUMAN",
        "reason": reason,
        "policy_clause": policy_clause,
        "confidence": confidence,
        "review_task": _review_task(
            severity=severity,
            event_type=event_type,
            asset_type=asset_type,
            source_trace=source_trace,
            proposed_action=proposed_action,
            confidence=confidence,
            ir_element_id=ir_element_id,
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            content_digest=content_digest,
            policy_type=policy_type,
        ),
        "audit": _base(
            event_type, asset_type, source_trace, proposed_action, ir_element_id
        ),
    }


def _review_task(
    *,
    severity,
    event_type,
    asset_type,
    source_trace,
    proposed_action,
    confidence,
    ir_element_id,
    artifact_id,
    artifact_version_id,
    content_digest,
    policy_type,
):
    return {
        "review_id": f"RVW-{uuid.uuid4().hex[:10]}",
        "severity": severity,
        "event_type": event_type,
        "asset_type": asset_type,
        "artifact_id": artifact_id,
        "artifact_version_id": artifact_version_id,
        "content_digest": content_digest,
        "policy_type": policy_type,
        "source_trace": source_trace,
        "proposed_action": proposed_action,
        "confidence": confidence,
        "ir_element_id": ir_element_id,
        "must_present": [
            "artifact_id",
            "artifact_version_id",
            "content_digest",
            "policy_type",
            "source_trace",
            "proposed_action",
        ],
    }


def _validate(args):
    missing = [f for f in REQUIRED_FIELDS if not getattr(args, f)]
    if missing:
        return f"缺少必填字段：{', '.join(missing)}"
    if args.event_type not in VALID_EVENT_TYPES:
        return f"无效的 --event-type '{args.event_type}'；合法值：{sorted(VALID_EVENT_TYPES)}"
    if args.asset_type not in VALID_ASSET_TYPES:
        return f"无效的 --asset-type '{args.asset_type}'；合法值：{sorted(VALID_ASSET_TYPES)}"
    if args.event_type == "contract_mutation" and not args.ir_element_id:
        return "contract_mutation 必须提供 --ir-element-id（声明被变更的对象）"
    if args.asset_type in FORMAL_ASSET_TYPES:
        missing_binding = [
            name
            for name in (
                "artifact_id",
                "artifact_version_id",
                "content_digest",
                "policy_type",
            )
            if not getattr(args, name)
        ]
        if missing_binding:
            return f"正式产出物缺少审核绑定字段：{', '.join(missing_binding)}"
    if args.confidence is not None and not (0.0 <= args.confidence <= 1.0):
        return f"--confidence 必须在 [0.0, 1.0] 区间内，当前为 {args.confidence}"
    return None


def main(argv=None):
    p = argparse.ArgumentParser(description="HITL 门禁裁决路由器")
    p.add_argument("--confidence", type=float, default=None)
    p.add_argument("--event-type", required=True)
    p.add_argument("--asset-type", required=True)
    p.add_argument("--source-trace", required=True)
    p.add_argument("--proposed-action", required=True)
    p.add_argument("--ir-element-id", default=None)
    p.add_argument("--artifact-id", default=None)
    p.add_argument("--artifact-version-id", default=None)
    p.add_argument("--content-digest", default=None)
    p.add_argument("--policy-type", default=None)
    args = p.parse_args(argv)
    err = _validate(args)
    if err:
        print(json.dumps({"error": err}, ensure_ascii=False), file=sys.stderr)
        return 3
    decision = decide(
        event_type=args.event_type,
        asset_type=args.asset_type,
        source_trace=args.source_trace,
        proposed_action=args.proposed_action,
        confidence=args.confidence,
        ir_element_id=args.ir_element_id,
        artifact_id=args.artifact_id,
        artifact_version_id=args.artifact_version_id,
        content_digest=args.content_digest,
        policy_type=args.policy_type,
    )
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 2 if decision["decision"] == "BLOCK_HUMAN" else 0


if __name__ == "__main__":
    sys.exit(main())
