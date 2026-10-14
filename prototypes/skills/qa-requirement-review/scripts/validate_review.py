#!/usr/bin/env python3
"""Validate the lifecycle contract of a requirement quality review."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

DIMENSIONS = {
    "ambiguity",
    "consistency",
    "testability",
    "completeness",
    "nfr_measurability",
    "role_permission",
}
ASSESSMENT_STATUS = {"CLEAR", "FINDING", "NOT_APPLICABLE", "NOT_REVIEWED"}
LIFECYCLE_STATUS = {"DRAFT", "REVIEW_REQUIRED", "BLOCKED", "ACCEPTED"}
AUDIT_VERDICTS = {"NOT_RUN", "PASS", "PASS_WITH_REVIEW", "REJECT"}
UNIT_STATUS = {"processed", "review_required", "skipped", "unavailable"}
EVIDENCE_TYPES = {"QUOTE", "ABSENCE", "CONFLICT"}
READINESS = {"ready", "review_required", "blocked"}
CATEGORIES = {"normal", "negative", "boundary", "permission", "state", "data", "integration", "nfr", "exploratory"}
TEST_DIMENSIONS = {"functional", "field_validation", "sorting", "state_transition", "permission", "integration", "nfr"}
def _fold_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value)


MINIMUM_SEVERITY = {
    "CROSS_SOURCE_CONFLICT": "REJECT",
    "INTRA_DOCUMENT_CONFLICT": "REJECT",
    "ROLE_PERMISSION_CONFLICT": "REJECT",
    "UNTESTABLE_ACCEPTANCE_CRITERIA": "REJECT",
    "MISSING_REQUIRED_ACTOR": "REVIEW",
    "UNMEASURABLE_NFR": "REJECT",
    "AMBIGUOUS_LANGUAGE": "REVIEW",
    "INCOMPLETE_REQUIREMENT": "REVIEW",
    "MISSING_EXCEPTION_BEHAVIOR": "REVIEW",
    "MISSING_REFERENCED_ARTIFACT": "REJECT",
    "MISSING_EXISTING_BASELINE": "REJECT",
    "PENDING_REQUIRED_ARTIFACT": "REJECT",
    "UNRESOLVED_INTERNAL_REFERENCE": "REVIEW",
}
REQUIRED_TOP_LEVEL = {
    "meta", "review_id", "source_ids", "sources", "source_units", "source_unit_dispositions", "requirements",
    "assessments", "requirement_assessments", "findings", "test_points", "coverage", "audit",
}


def duplicates(items: list[Any], key: str) -> set[str]:
    values = [item.get(key) for item in items if isinstance(item, dict) and isinstance(item.get(key), str)]
    return {value for value in values if values.count(value) > 1}


def validate(review: dict[str, Any], source_text: str | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    missing = sorted(REQUIRED_TOP_LEVEL - review.keys())
    if missing:
        return [f"missing top-level keys: {', '.join(missing)}"], warnings

    meta = review.get("meta")
    audit = review.get("audit")
    coverage = review.get("coverage")
    if not isinstance(meta, dict) or not isinstance(audit, dict) or not isinstance(coverage, dict):
        return ["meta, coverage, and audit must be objects"], warnings
    if meta.get("artifact_kind") != "requirement_quality_review":
        errors.append("meta.artifact_kind must be requirement_quality_review")
    if meta.get("review_mode") not in {"full", "quick"}:
        errors.append("meta.review_mode must be full or quick")
    if meta.get("lifecycle_status") not in LIFECYCLE_STATUS:
        errors.append("meta.lifecycle_status is invalid")
    if audit.get("verdict") not in AUDIT_VERDICTS:
        errors.append("audit.verdict is invalid")
    if not isinstance(audit.get("downstream_eligible"), bool):
        errors.append("audit.downstream_eligible must be boolean")
    if not isinstance(review.get("review_id"), str) or not review["review_id"].strip():
        errors.append("review_id must be a non-empty string")

    array_names = ["source_ids", "sources", "source_units", "source_unit_dispositions", "requirements", "assessments", "requirement_assessments", "findings", "test_points"]
    for name in array_names:
        if not isinstance(review.get(name), list):
            errors.append(f"{name} must be an array")
    if errors:
        return errors, warnings

    sources = review["sources"]
    source_ids = {item.get("source_id") for item in sources if isinstance(item, dict)}
    declared_source_ids = review["source_ids"]
    if any(not isinstance(value, str) or not value for value in declared_source_ids):
        errors.append("source_ids must contain non-empty strings")
    if set(declared_source_ids) != source_ids:
        errors.append("source_ids must exactly match sources[].source_id")
    if duplicates(sources, "source_id"):
        errors.append("duplicate source ids")
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"source[{index}] must be an object")
            continue
        if not source.get("file") or not source.get("type") or not source.get("version"):
            errors.append(f"source[{index}] lacks file, type, or version")
        digest = source.get("sha256")
        if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
            errors.append(f"source[{index}] has invalid sha256")

    units = review["source_units"]
    if duplicates(units, "unit_id"):
        errors.append("duplicate source unit ids")
    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            errors.append(f"source_unit[{index}] must be an object")
            continue
        if unit.get("source_id") not in source_ids:
            errors.append(f"source_unit[{index}] references unknown source")
        if unit.get("status") not in UNIT_STATUS or not isinstance(unit.get("relevant"), bool):
            errors.append(f"source_unit[{index}] has invalid status or relevant flag")
        if not unit.get("kind") or not unit.get("locator"):
            errors.append(f"source_unit[{index}] lacks kind or locator")
        if unit.get("status") != "processed" and not unit.get("reason"):
            errors.append(f"source_unit[{index}] must explain non-processed status")

    requirements = review["requirements"]
    requirement_ids = {item.get("requirement_id") for item in requirements if isinstance(item, dict)}
    if duplicates(requirements, "requirement_id"):
        errors.append("duplicate requirement ids")
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            errors.append(f"requirement[{index}] must be an object")
            continue
        if not requirement.get("requirement_id") or not requirement.get("title") or not requirement.get("summary"):
            errors.append(f"requirement[{index}] lacks id, title, or summary")
        refs = requirement.get("source_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"requirement {requirement.get('requirement_id', index)} has no source_refs")
        else:
            for ref in refs:
                if not isinstance(ref, dict) or ref.get("source_id") not in source_ids or not ref.get("locator") or not ref.get("quote"):
                    errors.append(f"requirement {requirement.get('requirement_id', index)} has invalid source_ref")
                elif source_text is not None and declared_source_ids and ref.get("source_id") == declared_source_ids[0] and _fold_ws(str(ref["quote"])) not in _fold_ws(source_text):
                    errors.append(f"requirement {requirement.get('requirement_id', index)} quote not found in primary source")

    findings = review["findings"]
    finding_ids = {item.get("finding_id") for item in findings if isinstance(item, dict)}
    findings_by_id = {
        item.get("finding_id"): item for item in findings
        if isinstance(item, dict) and item.get("finding_id")
    }
    if duplicates(findings, "finding_id"):
        errors.append("duplicate finding ids")
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(f"finding[{index}] must be an object")
            continue
        finding_id = finding.get("finding_id", f"[{index}]")
        code = finding.get("code")
        if code not in MINIMUM_SEVERITY:
            errors.append(f"finding {finding_id} has unknown code")
        if finding.get("severity") not in {"REJECT", "REVIEW"}:
            errors.append(f"finding {finding_id} has invalid severity")
        elif code in MINIMUM_SEVERITY and MINIMUM_SEVERITY[code] == "REJECT" and finding.get("severity") != "REJECT":
            errors.append(f"finding {finding_id} downgrades a mandatory REJECT code")
        if finding.get("certainty") not in {"confirmed", "risk", "clarification"}:
            errors.append(f"finding {finding_id} has invalid certainty")
        lifecycle_status = finding.get("lifecycle_status", "OPEN")
        if lifecycle_status not in {"OPEN", "RESOLVED", "WITHDRAWN", "ACCEPTED_RISK"}:
            errors.append(f"finding {finding_id} has invalid lifecycle_status")
        if lifecycle_status == "RESOLVED" and (not finding.get("resolution") or not finding.get("resolution_source_refs")):
            errors.append(f"resolved finding {finding_id} lacks resolution evidence")
        resolution_refs = finding.get("resolution_source_refs", [])
        if resolution_refs and (
            not isinstance(resolution_refs, list)
            or any(not any(str(ref).startswith(f"{source_id}:") or str(ref).startswith(f"{source_id}#") for source_id in source_ids) for ref in resolution_refs)
        ):
            errors.append(f"finding {finding_id} has invalid resolution_source_refs")
        evidence_type = finding.get("evidence_type")
        if evidence_type not in EVIDENCE_TYPES:
            errors.append(f"finding {finding_id} has invalid evidence_type")
        refs = finding.get("source_refs")
        if not isinstance(refs, list) or not refs or not finding.get("evidence"):
            errors.append(f"finding {finding_id} lacks source_refs or evidence")
        elif any(not isinstance(ref, str) or ref.split(":", 1)[0] not in source_ids for ref in refs):
            errors.append(f"finding {finding_id} references an unknown source")
        elif evidence_type == "QUOTE" and source_text is not None and _fold_ws(str(finding.get("evidence"))) not in _fold_ws(source_text):
            errors.append(f"finding {finding_id} quote evidence not found in primary source")
        if evidence_type == "ABSENCE" and (not finding.get("inspected_scope") or not finding.get("expected_element")):
            errors.append(f"finding {finding_id} absence evidence lacks inspected_scope or expected_element")
        if evidence_type == "CONFLICT" and (not isinstance(refs, list) or len(set(refs)) < 2):
            errors.append(f"finding {finding_id} conflict evidence needs two distinct source_refs")
        related = finding.get("requirement_ids")
        if not isinstance(related, list) or not related or set(related) - requirement_ids:
            errors.append(f"finding {finding_id} has invalid requirement_ids")
        affected = finding.get("affected_test_dimensions")
        if affected is not None and (
            not isinstance(affected, list) or not affected or set(affected) - TEST_DIMENSIONS
        ):
            errors.append(f"finding {finding_id} has invalid affected_test_dimensions")
    open_finding_ids = {
        item.get("finding_id") for item in findings if isinstance(item, dict)
        and item.get("lifecycle_status", "OPEN") not in {"RESOLVED", "WITHDRAWN"}
    }

    dispositions = review["source_unit_dispositions"]
    relevant_unit_ids = {unit.get("unit_id") for unit in units if isinstance(unit, dict) and unit.get("relevant")}
    if duplicates(dispositions, "unit_id"):
        errors.append("duplicate source unit dispositions")
    if {item.get("unit_id") for item in dispositions if isinstance(item, dict)} != relevant_unit_ids:
        errors.append("source_unit_dispositions must cover every relevant source unit exactly once")
    for index, item in enumerate(dispositions):
        if not isinstance(item, dict):
            errors.append(f"source_unit_disposition[{index}] must be an object")
            continue
        if item.get("disposition") not in {"requirement", "finding", "no_output", "unavailable", "review_required"}:
            errors.append(f"source_unit_disposition[{index}] has invalid disposition")
        if not item.get("reason") or not isinstance(item.get("requirement_ids"), list) or not isinstance(item.get("finding_ids"), list):
            errors.append(f"source_unit_disposition[{index}] lacks reason or references")
        elif set(item["requirement_ids"]) - requirement_ids or set(item["finding_ids"]) - finding_ids:
            errors.append(f"source_unit_disposition[{index}] has unknown references")
        elif item.get("disposition") == "requirement" and not item["requirement_ids"]:
            errors.append(f"source_unit_disposition[{index}] requirement disposition has no requirement")
        elif item.get("disposition") == "finding" and not item["finding_ids"]:
            errors.append(f"source_unit_disposition[{index}] finding disposition has no finding")

    assessments = review["assessments"]
    if len(assessments) != len(DIMENSIONS) or {item.get("dimension") for item in assessments if isinstance(item, dict)} != DIMENSIONS:
        errors.append("assessments must cover each canonical dimension exactly once")
    for index, assessment in enumerate(assessments):
        if not isinstance(assessment, dict):
            errors.append(f"assessment[{index}] must be an object")
            continue
        status = assessment.get("status")
        refs = assessment.get("finding_ids")
        if status not in ASSESSMENT_STATUS or not assessment.get("rationale") or not isinstance(refs, list):
            errors.append(f"assessment[{index}] has invalid status, rationale, or finding_ids")
        elif set(refs) - finding_ids:
            errors.append(f"assessment[{index}] references unknown finding")
        elif status == "FINDING" and not refs:
            errors.append(f"assessment[{index}] FINDING status has no finding_ids")
        elif status == "FINDING" and not set(refs).intersection(open_finding_ids):
            errors.append(f"assessment[{index}] FINDING status has no open finding")
        elif status != "FINDING" and refs:
            errors.append(f"assessment[{index}] non-FINDING status must not reference findings")

    per_req = review["requirement_assessments"]
    if duplicates(per_req, "assessment_id"):
        errors.append("duplicate requirement assessment ids")
    by_requirement: dict[str, set[str]] = {value: set() for value in requirement_ids}
    for index, assessment in enumerate(per_req):
        if not isinstance(assessment, dict):
            errors.append(f"requirement_assessment[{index}] must be an object")
            continue
        requirement_id = assessment.get("requirement_id")
        dimension = assessment.get("dimension")
        if requirement_id not in requirement_ids or dimension not in DIMENSIONS:
            errors.append(f"requirement_assessment[{index}] has invalid requirement or dimension")
            continue
        if dimension in by_requirement[requirement_id]:
            errors.append(f"requirement {requirement_id} repeats dimension {dimension}")
        by_requirement[requirement_id].add(dimension)
        if assessment.get("status") not in ASSESSMENT_STATUS or not assessment.get("rationale"):
            errors.append(f"requirement_assessment[{index}] has invalid status or rationale")
        refs = assessment.get("finding_ids")
        if not isinstance(refs, list) or set(refs) - finding_ids:
            errors.append(f"requirement_assessment[{index}] has invalid finding_ids")
        elif assessment.get("status") == "FINDING" and not set(refs).intersection(open_finding_ids):
            errors.append(f"requirement_assessment[{index}] FINDING status has no open finding")
        elif any(
            requirement_id not in findings_by_id[finding_id].get("requirement_ids", [])
            for finding_id in refs
        ):
            errors.append(f"requirement_assessment[{index}] references a finding outside its requirement scope")
    for requirement_id, dimensions in by_requirement.items():
        if dimensions != DIMENSIONS:
            errors.append(f"requirement {requirement_id} does not cover all six dimensions")

    test_points = review["test_points"]
    if duplicates(test_points, "test_point_id"):
        errors.append("duplicate test point ids")
    for index, point in enumerate(test_points):
        if not isinstance(point, dict):
            errors.append(f"test_point[{index}] must be an object")
            continue
        if point.get("requirement_id") not in requirement_ids:
            errors.append(f"test_point[{index}] references unknown requirement")
        if point.get("category") not in CATEGORIES or point.get("readiness") not in READINESS:
            errors.append(f"test_point[{index}] has invalid category or readiness")
        if not point.get("objective") or not point.get("action") or not point.get("expected_result"):
            errors.append(f"test_point[{index}] lacks objective, action, or expected_result")
        if not isinstance(point.get("preconditions"), list):
            errors.append(f"test_point[{index}] preconditions must be an array")
        source_refs = point.get("source_refs")
        if not isinstance(source_refs, list) or not source_refs:
            errors.append(f"test_point[{index}] has no source_refs")
        blockers = point.get("blocking_finding_ids")
        if not isinstance(blockers, list) or set(blockers) - finding_ids:
            errors.append(f"test_point[{index}] has invalid blocking_finding_ids")
        if point.get("readiness") == "blocked" and not blockers:
            errors.append(f"test_point[{index}] is blocked without a blocking finding")
        if point.get("readiness") == "ready" and (
            not point.get("preconditions") or blockers
        ):
            errors.append(f"test_point[{index}] ready state requires explicit preconditions and no blockers")

    source_coverage = coverage.get("source_coverage")
    if not isinstance(source_coverage, dict):
        errors.append("coverage.source_coverage must be an object")
        source_coverage = {}
    relevant_units = [unit for unit in units if isinstance(unit, dict) and unit.get("relevant")]
    actual_counts = {
        "relevant_units": len(relevant_units),
        "processed_units": sum(unit.get("status") == "processed" for unit in relevant_units),
        "review_required_units": sum(unit.get("status") == "review_required" for unit in relevant_units),
        "skipped_units": sum(unit.get("status") == "skipped" for unit in relevant_units),
        "unavailable_units": sum(unit.get("status") == "unavailable" for unit in relevant_units),
    }
    for key, value in actual_counts.items():
        if source_coverage.get(key) != value:
            errors.append(f"coverage.source_coverage.{key} must equal {value}")
    if source_coverage.get("claim") not in {"full", "quick"}:
        errors.append("coverage.source_coverage.claim must be full or quick")
    if not isinstance(source_coverage.get("uncovered_ranges"), list):
        errors.append("coverage.source_coverage.uncovered_ranges must be an array")
    if coverage.get("requirement_count") != len(requirements):
        errors.append("coverage.requirement_count does not match requirements")
    if coverage.get("requirement_assessment_count") != len(per_req):
        errors.append("coverage.requirement_assessment_count does not match requirement_assessments")
    if coverage.get("expected_requirement_assessment_count") != len(requirements) * len(DIMENSIONS):
        errors.append("coverage.expected_requirement_assessment_count is incorrect")
    if coverage.get("source_unit_disposition_count") != len(dispositions):
        errors.append("coverage.source_unit_disposition_count does not match dispositions")
    disposition_by_unit = {
        item.get("unit_id"): item for item in dispositions if isinstance(item, dict)
    }
    unresolved_unit_ids = {
        unit.get("unit_id") for unit in relevant_units
        if unit.get("status") in {"review_required", "unavailable", "skipped"}
    }
    unresolved_unit_ids.update(relevant_unit_ids - disposition_by_unit.keys())
    unresolved_unit_ids.update(
        unit_id for unit_id, item in disposition_by_unit.items()
        if item.get("disposition") in {"unavailable", "review_required"}
    )
    if coverage.get("unresolved_source_unit_count") != len(unresolved_unit_ids):
        errors.append("coverage.unresolved_source_unit_count does not match source status and dispositions")

    unreviewed = any(item.get("status") == "NOT_REVIEWED" for item in assessments + per_req if isinstance(item, dict))
    unresolved_findings = any(
        item.get("lifecycle_status", "OPEN") not in {"RESOLVED", "WITHDRAWN"}
        for item in findings if isinstance(item, dict)
    )
    uncovered = source_coverage.get("uncovered_ranges") or []
    assessment_evidence_complete = all(
        item.get("status") in {"FINDING", "NOT_REVIEWED"}
        or (isinstance(item.get("source_refs"), list) and bool(item["source_refs"]))
        for item in per_req if isinstance(item, dict)
    )
    full_acceptance = (
        meta.get("review_mode") == "full"
        and source_coverage.get("claim") == "full"
        and not actual_counts["skipped_units"]
        and not actual_counts["unavailable_units"]
        and not actual_counts["review_required_units"]
        and not uncovered
        and not unresolved_unit_ids
        and not unreviewed
        and not unresolved_findings
        and assessment_evidence_complete
        and audit.get("verdict") == "PASS"
        and meta.get("lifecycle_status") == "ACCEPTED"
    )
    if audit.get("downstream_eligible") is True and not full_acceptance:
        errors.append("audit.downstream_eligible cannot be true before full acceptance")
    if audit.get("downstream_eligible") is True and not assessment_evidence_complete:
        errors.append("accepted review assessments require source_refs")
    if full_acceptance and audit.get("downstream_eligible") is not True:
        errors.append("accepted review must set audit.downstream_eligible=true")
    if meta.get("review_mode") == "quick" and audit.get("downstream_eligible"):
        errors.append("quick review cannot be downstream eligible")
    if audit.get("verdict") == "PASS" and (unreviewed or unresolved_findings):
        errors.append("PASS review cannot contain unreviewed assessments or unresolved findings")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a requirement quality review")
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--require-accepted", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.review.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("review root must be an object")
        source_text = args.source.read_text(encoding="utf-8") if args.source else None
        errors, warnings = validate(data, source_text)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"structural_verdict":"FAIL","artifact_verdict":"REJECT","errors":[str(exc)],"warnings":[]}, ensure_ascii=False, indent=2))
        return 3
    accepted = not errors and data["audit"].get("downstream_eligible") is True
    result = {
        "structural_verdict": "PASS" if not errors else "FAIL",
        "artifact_verdict": data["audit"].get("verdict"),
        "downstream_eligible": accepted,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        return 2
    if args.require_accepted and not accepted:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
