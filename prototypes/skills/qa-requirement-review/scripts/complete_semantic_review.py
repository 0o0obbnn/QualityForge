#!/usr/bin/env python3
"""Conservatively finalize an AI-authored requirement review.

This compatibility entrypoint deliberately performs no semantic review. It
preserves unresolved assessments and AI-authored test points, binds open
findings, and recomputes lifecycle and coverage from deterministic facts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DIMENSIONS = (
    "ambiguity",
    "consistency",
    "testability",
    "completeness",
    "nfr_measurability",
    "role_permission",
)


def is_open(finding: dict[str, Any]) -> bool:
    return finding.get("lifecycle_status", "OPEN") not in {"RESOLVED", "WITHDRAWN"}


def ready_point_is_complete(point: dict[str, Any]) -> bool:
    return (
        point.get("readiness") != "ready"
        or (
            bool(point.get("objective"))
            and isinstance(point.get("preconditions"), list)
            and bool(point["preconditions"])
            and bool(point.get("action"))
            and bool(point.get("expected_result"))
            and isinstance(point.get("source_refs"), list)
            and bool(point["source_refs"])
            and not point.get("blocking_finding_ids")
        )
    )


def recompute(review: dict[str, Any]) -> None:
    findings = {
        item.get("finding_id"): item
        for item in review.get("findings", [])
        if isinstance(item, dict) and item.get("finding_id")
    }
    open_findings = {key: value for key, value in findings.items() if is_open(value)}
    per_requirement = review.get("requirement_assessments", [])

    for assessment in per_requirement:
        bound_ids = [
            finding_id
            for finding_id in assessment.get("finding_ids", [])
            if finding_id in open_findings
        ]
        if bound_ids:
            assessment["status"] = "FINDING"
            assessment["finding_ids"] = bound_ids
        elif assessment.get("status") == "FINDING":
            assessment.update(
                status="NOT_REVIEWED",
                rationale="关联问题已关闭，仍需 AI 或人工依据解决证据重新评审该维度",
                finding_ids=[],
            )

    for overall in review.get("assessments", []):
        scoped = [
            item
            for item in per_requirement
            if item.get("dimension") == overall.get("dimension")
        ]
        finding_ids = sorted(
            {
                finding_id
                for item in scoped
                for finding_id in item.get("finding_ids", [])
                if finding_id in open_findings
            }
        )
        if finding_ids:
            status = "FINDING"
        elif any(item.get("status") == "NOT_REVIEWED" for item in scoped):
            status = "NOT_REVIEWED"
        elif scoped and all(item.get("status") == "NOT_APPLICABLE" for item in scoped):
            status = "NOT_APPLICABLE"
        else:
            status = "CLEAR"
        overall.update(
            status=status,
            finding_ids=finding_ids,
            rationale="由 AI 或人工逐需求评审状态确定性汇总",
        )

    relevant_units = {
        item.get("unit_id"): item
        for item in review.get("source_units", [])
        if isinstance(item, dict) and item.get("relevant") is True and item.get("unit_id")
    }
    dispositions = {
        item.get("unit_id"): item
        for item in review.get("source_unit_dispositions", [])
        if isinstance(item, dict) and item.get("unit_id") in relevant_units
    }
    unresolved_unit_ids = {
        unit_id
        for unit_id, unit in relevant_units.items()
        if unit.get("status") in {"review_required", "unavailable", "skipped"}
    }
    unresolved_unit_ids.update(relevant_units.keys() - dispositions.keys())
    unresolved_unit_ids.update(
        unit_id
        for unit_id, disposition in dispositions.items()
        if disposition.get("disposition") in {"review_required", "unavailable"}
    )

    coverage = review.setdefault("coverage", {})
    source_coverage = coverage.setdefault("source_coverage", {})
    source_coverage.update(
        relevant_units=len(relevant_units),
        processed_units=sum(
            unit.get("status") == "processed" for unit in relevant_units.values()
        ),
        review_required_units=sum(
            unit.get("status") == "review_required" for unit in relevant_units.values()
        ),
        skipped_units=sum(
            unit.get("status") == "skipped" for unit in relevant_units.values()
        ),
        unavailable_units=sum(
            unit.get("status") == "unavailable" for unit in relevant_units.values()
        ),
    )
    coverage.update(
        requirement_count=len(review.get("requirements", [])),
        requirement_assessment_count=len(per_requirement),
        expected_requirement_assessment_count=len(review.get("requirements", []))
        * len(DIMENSIONS),
        source_unit_disposition_count=len(dispositions),
        unresolved_source_unit_count=len(unresolved_unit_ids),
    )

    unresolved_assessments = sum(
        item.get("status") == "NOT_REVIEWED" for item in per_requirement
    )
    open_values = list(open_findings.values())
    reject_count = sum(item.get("severity") == "REJECT" for item in open_values)
    review_count = sum(item.get("severity") == "REVIEW" for item in open_values)
    invalid_ready_points = sum(
        not ready_point_is_complete(item)
        for item in review.get("test_points", [])
        if isinstance(item, dict)
    )
    complete_sources = (
        review.get("meta", {}).get("review_mode") == "full"
        and source_coverage.get("claim") == "full"
        and not unresolved_unit_ids
        and not source_coverage.get("uncovered_ranges")
    )
    accepted = (
        complete_sources
        and not unresolved_assessments
        and not open_values
        and not invalid_ready_points
    )
    review.setdefault("meta", {})["lifecycle_status"] = (
        "ACCEPTED" if accepted else ("BLOCKED" if reject_count else "REVIEW_REQUIRED")
    )
    review["audit"] = {
        "verdict": "PASS" if accepted else ("REJECT" if reject_count else "PASS_WITH_REVIEW"),
        "downstream_eligible": accepted,
        "errors": [f"存在 {reject_count} 个阻断 finding"] if reject_count else [],
        "warnings": [
            message
            for condition, message in (
                (bool(unresolved_assessments), f"仍有 {unresolved_assessments} 个逐需求维度等待 AI 或人工语义评审"),
                (bool(unresolved_unit_ids), f"仍有 {len(unresolved_unit_ids)} 个来源单元未完成或不可用"),
                (bool(review_count), f"仍有 {review_count} 个 REVIEW finding"),
                (bool(invalid_ready_points), f"仍有 {invalid_ready_points} 个 ready 测试点不满足确定性完整性约束"),
            )
            if condition
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize an AI-authored review without making semantic decisions"
    )
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    review = json.loads(args.review.read_text(encoding="utf-8"))
    json.loads(args.mapping.read_text(encoding="utf-8"))
    args.source.read_text(encoding="utf-8")
    recompute(review)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
