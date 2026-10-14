#!/usr/bin/env python3
"""Merge evidenced finding resolutions and recompute review lifecycle conservatively."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DECISIONS = {
    "RESOLVE": "RESOLVED",
    "WITHDRAW": "WITHDRAWN",
    "ACCEPT_RISK": "ACCEPTED_RISK",
    "KEEP_OPEN": "OPEN",
    "CONFIRM": "OPEN",
}
ASSESSMENT_STATUSES = {"CLEAR", "FINDING", "NOT_APPLICABLE", "NOT_REVIEWED"}
SOURCE_DISPOSITIONS = {"requirement", "finding", "no_output", "unavailable", "review_required"}
TEST_DIMENSIONS = {"functional", "field_validation", "sorting", "state_transition", "permission", "integration", "nfr"}


def open_finding(finding: dict[str, Any]) -> bool:
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
    findings = {item.get("finding_id"): item for item in review.get("findings", [])}
    per_req = review.get("requirement_assessments", [])
    for assessment in per_req:
        assessment["finding_ids"] = [finding_id for finding_id in assessment.get("finding_ids", []) if open_finding(findings.get(finding_id, {}))]
        if assessment.get("status") == "FINDING" and not assessment["finding_ids"]:
            assessment["status"] = "NOT_REVIEWED"
            assessment["rationale"] = "关联问题已关闭，仍需 AI 或人工依据解决证据重新评审该维度"

    for overall in review.get("assessments", []):
        dimension = overall.get("dimension")
        scoped = [item for item in per_req if item.get("dimension") == dimension]
        finding_ids = sorted({finding_id for item in scoped for finding_id in item.get("finding_ids", [])})
        if finding_ids:
            status = "FINDING"
        elif any(item.get("status") == "NOT_REVIEWED" for item in scoped):
            status = "NOT_REVIEWED"
        elif scoped and all(item.get("status") == "NOT_APPLICABLE" for item in scoped):
            status = "NOT_APPLICABLE"
        else:
            status = "CLEAR"
        overall.update({"status": status, "finding_ids": finding_ids, "rationale": "由逐需求评审状态重新汇总"})

    coverage = review.setdefault("coverage", {})
    source_coverage = coverage.setdefault("source_coverage", {})
    relevant_units = {
        item.get("unit_id"): item for item in review.get("source_units", [])
        if isinstance(item, dict) and item.get("relevant") is True and item.get("unit_id")
    }
    dispositions = {
        item.get("unit_id"): item for item in review.get("source_unit_dispositions", [])
        if isinstance(item, dict) and item.get("unit_id") in relevant_units
    }
    unresolved_unit_ids = {
        unit_id for unit_id, unit in relevant_units.items()
        if unit.get("status") in {"review_required", "unavailable", "skipped"}
    }
    unresolved_unit_ids.update(relevant_units.keys() - dispositions.keys())
    unresolved_unit_ids.update(
        unit_id for unit_id, item in dispositions.items()
        if item.get("disposition") in {"review_required", "unavailable"}
    )
    review_required_units = sum(unit.get("status") == "review_required" for unit in relevant_units.values())
    unavailable_units = sum(unit.get("status") == "unavailable" for unit in relevant_units.values())
    skipped_units = sum(unit.get("status") == "skipped" for unit in relevant_units.values())
    processed_units = sum(unit.get("status") == "processed" for unit in relevant_units.values())
    source_coverage.update({
        "relevant_units": len(relevant_units),
        "processed_units": processed_units,
        "review_required_units": review_required_units,
        "skipped_units": skipped_units,
        "unavailable_units": unavailable_units,
    })
    coverage["requirement_count"] = len(review.get("requirements", []))
    coverage["requirement_assessment_count"] = len(per_req)
    coverage["expected_requirement_assessment_count"] = len(review.get("requirements", [])) * 6
    coverage["source_unit_disposition_count"] = len(dispositions)
    coverage["unresolved_source_unit_count"] = len(unresolved_unit_ids)
    complete_sources = (
        review.get("meta", {}).get("review_mode") == "full"
        and source_coverage.get("claim") == "full"
        and not source_coverage.get("skipped_units")
        and not source_coverage.get("unavailable_units")
        and not source_coverage.get("review_required_units")
        and not source_coverage.get("uncovered_ranges")
        and not coverage.get("unresolved_source_unit_count")
    )
    unreviewed = any(item.get("status") == "NOT_REVIEWED" for item in review.get("assessments", []) + per_req)
    open_findings = [item for item in findings.values() if open_finding(item)]
    open_reject = any(item.get("severity") == "REJECT" for item in open_findings)
    assessment_evidence_complete = all(
        item.get("status") in {"FINDING", "NOT_REVIEWED"}
        or (isinstance(item.get("source_refs"), list) and bool(item["source_refs"]))
        for item in per_req if isinstance(item, dict)
    )
    invalid_ready_points = sum(
        not ready_point_is_complete(item)
        for item in review.get("test_points", []) if isinstance(item, dict)
    )
    accepted = (
        complete_sources
        and not unreviewed
        and not open_findings
        and assessment_evidence_complete
        and not invalid_ready_points
    )
    audit = review.setdefault("audit", {})
    audit["verdict"] = "PASS" if accepted else ("REJECT" if open_reject else "PASS_WITH_REVIEW")
    audit["downstream_eligible"] = accepted
    open_reject_count = sum(item.get("severity") == "REJECT" for item in open_findings)
    not_reviewed_count = sum(item.get("status") == "NOT_REVIEWED" for item in per_req)
    audit["errors"] = [f"存在 {open_reject_count} 个阻断 finding"] if open_reject_count else []
    audit["warnings"] = []
    if not_reviewed_count:
        audit["warnings"].append(f"仍有 {not_reviewed_count} 个逐需求维度未完成语义评审")
    if coverage["unresolved_source_unit_count"]:
        audit["warnings"].append(f"仍有 {coverage['unresolved_source_unit_count']} 个来源单元未完成处置或不可用")
    if not assessment_evidence_complete:
        audit["warnings"].append("仍有已评审维度缺少来源引用")
    if invalid_ready_points:
        audit["warnings"].append(f"仍有 {invalid_ready_points} 个 ready 测试点缺少前置条件、来源或完整 Oracle")
    review.setdefault("meta", {})["lifecycle_status"] = "ACCEPTED" if accepted else ("BLOCKED" if open_reject else "REVIEW_REQUIRED")
    review["meta"]["resolved_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply evidenced resolutions to a requirement review")
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--resolutions", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    review = json.loads(args.review.read_text(encoding="utf-8"))
    package = json.loads(args.resolutions.read_text(encoding="utf-8"))
    findings = {item.get("finding_id"): item for item in review.get("findings", [])}
    requirement_ids = {item.get("requirement_id") for item in review.get("requirements", [])}
    function_ids = {
        value for item in review.get("requirements", []) for value in item.get("function_refs", [])
    }
    atomic_ids = {
        value for item in review.get("requirements", []) for value in item.get("atomic_refs", [])
    }
    source_unit_ids = {item.get("unit_id") for item in review.get("source_units", []) if isinstance(item, dict)}
    disposition_index = {
        item.get("unit_id"): item for item in review.get("source_unit_dispositions", []) if isinstance(item, dict)
    }
    for update in package.get("source_unit_reviews", []):
        unit_id, disposition = update.get("unit_id"), update.get("disposition")
        if unit_id not in source_unit_ids or disposition not in SOURCE_DISPOSITIONS:
            raise SystemExit(f"invalid source unit review: {unit_id}")
        if not update.get("reason"):
            raise SystemExit(f"source unit review requires reason: {unit_id}")
        if set(update.get("requirement_ids", [])) - requirement_ids:
            raise SystemExit(f"source unit review references unknown requirement: {unit_id}")
        if set(update.get("finding_ids", [])) - findings.keys():
            raise SystemExit(f"source unit review references unknown finding: {unit_id}")
        normalized = {
            "unit_id": unit_id,
            "disposition": disposition,
            "requirement_ids": update.get("requirement_ids", []),
            "finding_ids": update.get("finding_ids", []),
            "reason": update["reason"],
        }
        if unit_id in disposition_index:
            disposition_index[unit_id].update(normalized)
        else:
            review.setdefault("source_unit_dispositions", []).append(normalized)
            disposition_index[unit_id] = normalized
        source_unit = next(item for item in review.get("source_units", []) if item.get("unit_id") == unit_id)
        source_unit["status"] = {
            "requirement": "processed", "finding": "processed", "no_output": "processed",
            "unavailable": "unavailable", "review_required": "review_required",
        }[disposition]
    for finding in package.get("new_findings", []):
        finding_id = finding.get("finding_id")
        evidence_type = finding.get("evidence_type")
        source_refs = finding.get("source_refs", [])
        if not finding_id or finding_id in findings:
            raise SystemExit(f"new finding has missing or duplicate id: {finding_id}")
        if finding.get("severity") not in {"REJECT", "REVIEW"} or evidence_type not in {"QUOTE", "ABSENCE", "CONFLICT"}:
            raise SystemExit(f"new finding has invalid severity or evidence type: {finding_id}")
        if not finding.get("code") or not finding.get("evidence") or not source_refs:
            raise SystemExit(f"new finding is incomplete: {finding_id}")
        if not isinstance(finding.get("affected_test_dimensions"), list) or not finding["affected_test_dimensions"] or set(finding["affected_test_dimensions"]) - TEST_DIMENSIONS:
            raise SystemExit(f"new finding has invalid affected_test_dimensions: {finding_id}")
        if not finding.get("requirement_ids") or set(finding["requirement_ids"]) - requirement_ids:
            raise SystemExit(f"new finding references unknown requirements: {finding_id}")
        if evidence_type == "CONFLICT" and len(set(source_refs)) < 2:
            raise SystemExit(f"conflict finding requires two source refs: {finding_id}")
        if evidence_type == "ABSENCE" and (not finding.get("inspected_scope") or not finding.get("expected_element")):
            raise SystemExit(f"absence finding lacks scope or expected element: {finding_id}")
        finding = {**finding, "lifecycle_status": finding.get("lifecycle_status", "OPEN")}
        review.setdefault("findings", []).append(finding)
        findings[finding_id] = finding
    assessment_index = {(item.get("requirement_id"), item.get("dimension")): item for item in review.get("requirement_assessments", [])}
    for resolution in package.get("resolutions", []):
        finding_id, decision = resolution.get("finding_id"), resolution.get("decision")
        if finding_id not in findings:
            raise SystemExit(f"resolution references unknown finding: {finding_id}")
        if decision not in DECISIONS:
            raise SystemExit(f"invalid decision for {finding_id}: {decision}")
        if decision in {"RESOLVE", "WITHDRAW", "CONFIRM"} and (not resolution.get("resolution") or not resolution.get("source_refs")):
            raise SystemExit(f"{decision} requires resolution and source_refs: {finding_id}")
        finding = findings[finding_id]
        finding["lifecycle_status"] = DECISIONS[decision]
        if decision == "CONFIRM":
            added_requirements = resolution.get("add_requirement_ids", [])
            added_functions = resolution.get("add_function_ids", [])
            added_atomics = resolution.get("add_atomic_ids", [])
            if set(added_requirements) - requirement_ids:
                raise SystemExit(f"CONFIRM adds unknown requirements: {finding_id}")
            if set(added_functions) - function_ids:
                raise SystemExit(f"CONFIRM adds unknown functions: {finding_id}")
            if set(added_atomics) - atomic_ids:
                raise SystemExit(f"CONFIRM adds unknown atomic functions: {finding_id}")
            finding["requirement_ids"] = sorted(set(finding.get("requirement_ids", [])) | set(added_requirements))
            finding["function_ids"] = sorted(set(finding.get("function_ids", [])) | set(added_functions))
            finding["atomic_ids"] = sorted(set(finding.get("atomic_ids", [])) | set(added_atomics))
            was_candidate = finding.get("certainty") != "confirmed"
            finding["certainty"] = "confirmed"
            if was_candidate:
                finding["origin"] = "semantic_review"
            finding["semantic_review"] = {
                "decision": "CONFIRM",
                "rationale": resolution["resolution"],
                "source_refs": resolution["source_refs"],
            }
        if decision != "CONFIRM" and resolution.get("resolution"):
            finding["resolution"] = resolution["resolution"]
        if decision != "CONFIRM" and resolution.get("source_refs"):
            finding["resolution_source_refs"] = resolution["source_refs"]
        for update in resolution.get("assessment_updates", []):
            key = (update.get("requirement_id"), update.get("dimension"))
            if key not in assessment_index:
                raise SystemExit(f"assessment update references unknown requirement/dimension: {key}")
            if update.get("status") not in ASSESSMENT_STATUSES or not update.get("rationale"):
                raise SystemExit(f"invalid assessment update: {key}")
            if update["status"] in {"CLEAR", "NOT_APPLICABLE"} and not (
                update.get("source_refs") or resolution.get("source_refs")
            ):
                raise SystemExit(f"assessment update requires source_refs: {key}")
            assessment_index[key].update({"status": update["status"], "rationale": update["rationale"]})
            assessment_index[key]["source_refs"] = update.get("source_refs") or resolution.get("source_refs", [])
            if update["status"] != "FINDING":
                assessment_index[key]["finding_ids"] = [value for value in assessment_index[key].get("finding_ids", []) if value != finding_id]
    for update in package.get("assessment_reviews", []):
        key = (update.get("requirement_id"), update.get("dimension"))
        if key not in assessment_index:
            raise SystemExit(f"assessment review references unknown requirement/dimension: {key}")
        if update.get("status") not in ASSESSMENT_STATUSES - {"NOT_REVIEWED"} or not update.get("rationale"):
            raise SystemExit(f"incomplete assessment review: {key}")
        finding_ids = update.get("finding_ids", [])
        if update["status"] == "FINDING" and (not finding_ids or set(finding_ids) - findings.keys()):
            raise SystemExit(f"FINDING assessment review requires valid finding_ids: {key}")
        if update["status"] == "FINDING" and any(
            update["requirement_id"] not in findings[finding_id].get("requirement_ids", [])
            for finding_id in finding_ids
        ):
            raise SystemExit(f"FINDING assessment review has cross-requirement finding_ids: {key}")
        if update["status"] in {"CLEAR", "NOT_APPLICABLE"} and not update.get("source_refs"):
            raise SystemExit(f"assessment review requires source_refs: {key}")
        assessment_index[key].update({"status": update["status"], "rationale": update["rationale"]})
        if update.get("source_refs"):
            assessment_index[key]["source_refs"] = update["source_refs"]
        assessment_index[key]["finding_ids"] = finding_ids if update["status"] == "FINDING" else []
    recompute(review)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
