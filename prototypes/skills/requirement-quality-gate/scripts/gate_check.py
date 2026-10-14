#!/usr/bin/env python3
"""需求质量评审报告的确定性契约 gate。"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys


REQUIRED_DIMENSIONS = frozenset(
    {
        "ambiguity",
        "consistency",
        "testability",
        "completeness",
        "nfr_measurability",
        "role_permission",
    }
)
VALID_STATUSES = frozenset({"CLEAR", "FINDING", "NOT_APPLICABLE"})
VALID_SEVERITIES = frozenset({"REVIEW", "REJECT"})
ALLOWED_FINDING_CODES = frozenset(
    {
        "AMBIGUOUS_LANGUAGE",
        "CROSS_SOURCE_CONFLICT",
        "INCOMPLETE_REQUIREMENT",
        "MISSING_EXCEPTION_BEHAVIOR",
        "MISSING_REQUIRED_ACTOR",
        "ROLE_PERMISSION_CONFLICT",
        "UNMEASURABLE_NFR",
        "UNTESTABLE_ACCEPTANCE_CRITERIA",
    }
)
HARD_REJECT_CODES = frozenset(
    {
        "CROSS_SOURCE_CONFLICT",
        "MISSING_REQUIRED_ACTOR",
        "ROLE_PERMISSION_CONFLICT",
        "UNMEASURABLE_NFR",
        "UNTESTABLE_ACCEPTANCE_CRITERIA",
    }
)


def _gate_finding(code, target, message):
    return {
        "code": code,
        "severity": "REJECT",
        "target": target,
        "evidence": message,
    }


def _source_root(source_ref):
    return str(source_ref).split("§")[0].split(":")[0].strip()


def check_review(packet):
    gate_findings = []
    if not isinstance(packet, dict):
        packet = {}
        gate_findings.append(
            _gate_finding(
                "INVALID_REVIEW_PACKET", "root", "评审根节点必须是对象"
            )
        )

    if not packet.get("review_id"):
        gate_findings.append(
            _gate_finding("MISSING_REVIEW_ID", "review_id", "review_id 为必填项")
        )

    source_ids = packet.get("source_ids", []) or []
    if not isinstance(source_ids, list):
        source_ids = []
        source_set = set()
    else:
        source_set = {
            item for item in source_ids if isinstance(item, str) and item.strip()
        }
    if not source_ids or len(source_set) != len(source_ids):
        gate_findings.append(
            _gate_finding(
                "INVALID_SOURCE_SET",
                "source_ids",
                "source_ids 必须是非空且唯一的字符串",
            )
        )

    assessments = packet.get("assessments", []) or []
    assessment_by_dimension = {}
    for index, assessment in enumerate(assessments):
        target = f"assessments[{index}]"
        if not isinstance(assessment, dict):
            gate_findings.append(
                _gate_finding(
                    "INVALID_ASSESSMENT", target, "assessment 必须是对象"
                )
            )
            continue
        dimension = assessment.get("dimension")
        if dimension not in REQUIRED_DIMENSIONS:
            gate_findings.append(
                _gate_finding(
                    "UNKNOWN_QUALITY_DIMENSION",
                    target,
                    f"不支持 dimension {dimension!r}",
                )
            )
            continue
        if dimension in assessment_by_dimension:
            gate_findings.append(
                _gate_finding(
                    "DUPLICATE_QUALITY_DIMENSION",
                    dimension,
                    "同一 dimension 被评估多次",
                )
            )
        assessment_by_dimension[dimension] = assessment
        if assessment.get("status") not in VALID_STATUSES:
            gate_findings.append(
                _gate_finding(
                    "INVALID_ASSESSMENT_STATUS",
                    dimension,
                    "status 必须是 CLEAR、FINDING 或 NOT_APPLICABLE",
                )
            )
        if not str(assessment.get("rationale", "")).strip():
            gate_findings.append(
                _gate_finding(
                    "MISSING_ASSESSMENT_RATIONALE",
                    dimension,
                    "assessment 必须提供 rationale",
                )
            )
        finding_ids = assessment.get("finding_ids", [])
        if not isinstance(finding_ids, list):
            gate_findings.append(
                _gate_finding(
                    "INVALID_FINDING_REFS", dimension, "finding_ids 必须是数组"
                )
            )
        elif any(not isinstance(item, str) or not item for item in finding_ids):
            gate_findings.append(
                _gate_finding(
                    "INVALID_FINDING_REFS",
                    dimension,
                    "finding_ids 必须是非空字符串",
                )
            )
        elif assessment.get("status") == "FINDING" and not finding_ids:
            gate_findings.append(
                _gate_finding(
                    "FINDING_STATUS_WITHOUT_FINDING",
                    dimension,
                    "FINDING 状态的 assessment 必须引用至少一个 finding",
                )
            )
        elif assessment.get("status") in {"CLEAR", "NOT_APPLICABLE"} and finding_ids:
            gate_findings.append(
                _gate_finding(
                    "NONFINDING_STATUS_WITH_FINDING",
                    dimension,
                    "只有 FINDING 状态的 assessment 才能引用 finding",
                )
            )

    for dimension in sorted(REQUIRED_DIMENSIONS - set(assessment_by_dimension)):
        gate_findings.append(
            _gate_finding(
                "MISSING_QUALITY_DIMENSION",
                dimension,
                "强制质量维度未被评估",
            )
        )

    quality_findings = packet.get("findings", []) or []
    quality_by_id = {}
    validated_quality = []
    for index, quality in enumerate(quality_findings):
        target = f"findings[{index}]"
        if not isinstance(quality, dict):
            gate_findings.append(
                _gate_finding(
                    "INVALID_QUALITY_FINDING", target, "finding 必须是对象"
                )
            )
            continue
        finding_id = quality.get("finding_id")
        valid_finding_id = isinstance(finding_id, str) and bool(finding_id)
        safe_target = finding_id if valid_finding_id else target
        if not valid_finding_id:
            gate_findings.append(
                _gate_finding("MISSING_FINDING_ID", target, "finding_id 为必填项")
            )
        elif finding_id in quality_by_id:
            gate_findings.append(
                _gate_finding(
                    "DUPLICATE_FINDING_ID", finding_id, "finding_id 必须唯一"
                )
            )
        else:
            quality_by_id[finding_id] = quality
        code = quality.get("code")
        severity = quality.get("severity")
        if not isinstance(code, str) or code not in ALLOWED_FINDING_CODES:
            gate_findings.append(
                _gate_finding(
                    "UNKNOWN_FINDING_CODE",
                    safe_target,
                    f"不支持 code {code!r}",
                )
            )
        if not isinstance(severity, str) or severity not in VALID_SEVERITIES:
            gate_findings.append(
                _gate_finding(
                    "INVALID_FINDING_SEVERITY",
                    safe_target,
                    f"不支持 severity {severity!r}",
                )
            )
        if isinstance(code, str) and code in HARD_REJECT_CODES and severity != "REJECT":
            gate_findings.append(
                _gate_finding(
                    "INVALID_SEVERITY_FOR_CODE",
                    safe_target,
                    f"{code} 必须为 REJECT",
                )
            )
        refs = quality.get("source_refs", [])
        if not isinstance(refs, list) or not refs:
            gate_findings.append(
                _gate_finding(
                    "MISSING_FINDING_EVIDENCE_REF",
                    finding_id or target,
                    "source_refs 不能为空",
                )
            )
        else:
            for ref in refs:
                if _source_root(ref) not in source_set:
                    gate_findings.append(
                        _gate_finding(
                            "UNDECLARED_FINDING_SOURCE",
                            finding_id or target,
                            f"source 引用 {ref!r} 未在 source_ids 中声明",
                        )
                    )
        if not str(quality.get("evidence", "")).strip():
            gate_findings.append(
                _gate_finding(
                    "MISSING_FINDING_EVIDENCE",
                    finding_id or target,
                    "必须提供逐字或忠实的证据",
                )
            )
        if not str(quality.get("question", "")).strip():
            gate_findings.append(
                _gate_finding(
                    "MISSING_RESOLUTION_QUESTION",
                    finding_id or target,
                    "必须提供具体的澄清问题",
                )
            )
        validated_quality.append(quality)

    referenced_ids = set()
    for assessment in assessment_by_dimension.values():
        ids = assessment.get("finding_ids", [])
        if isinstance(ids, list):
            for finding_id in ids:
                if not isinstance(finding_id, str) or not finding_id:
                    continue
                referenced_ids.add(finding_id)
                if finding_id not in quality_by_id:
                    gate_findings.append(
                        _gate_finding(
                            "UNKNOWN_FINDING_REF",
                            assessment["dimension"],
                            f"finding {finding_id!r} 不存在",
                        )
                    )
    for finding_id in sorted(set(quality_by_id) - referenced_ids):
        gate_findings.append(
            _gate_finding(
                "UNBOUND_QUALITY_FINDING",
                finding_id,
                "finding 未绑定到任何 assessment 维度",
            )
        )

    has_gate_reject = bool(gate_findings)
    has_quality_reject = any(
        item.get("severity") == "REJECT" for item in validated_quality
    )
    has_quality_review = any(
        item.get("severity") == "REVIEW" for item in validated_quality
    )
    verdict = (
        "REJECT"
        if has_gate_reject or has_quality_reject
        else ("PASS_WITH_REVIEW" if has_quality_review else "PASS")
    )
    combined_findings = gate_findings + validated_quality
    return {
        "skill": "requirement-quality-gate",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "review_id": packet.get("review_id"),
        "verdict": verdict,
        "reject_findings": sum(
            1 for item in combined_findings if item.get("severity") == "REJECT"
        ),
        "review_findings": sum(
            1 for item in validated_quality if item.get("severity") == "REVIEW"
        ),
        "findings": combined_findings,
        "routing": {
            "PASS": "需求评审可进入融合",
            "PASS_WITH_REVIEW": "挂起等待澄清评审",
            "REJECT": "阻断需求融合",
        }[verdict],
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    try:
        with open(args.review, encoding="utf-8") as handle:
            packet = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": f"读取输入失败：{exc}"}), file=sys.stderr)
        return 3
    result = check_review(packet)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    try:
        if args.out:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(output)
        else:
            print(output)
    except OSError as exc:
        print(json.dumps({"error": f"写入输出失败：{exc}"}), file=sys.stderr)
        return 3
    return {"PASS": 0, "PASS_WITH_REVIEW": 1, "REJECT": 2}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
