#!/usr/bin/env python3
"""Validate a requirement source-dependency review artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REFERENCE_TYPES = {"internal_reference", "external_artifact", "existing_baseline", "pending_artifact"}
STATUSES = {"available", "review_required", "missing"}
CODES = {"MISSING_REFERENCED_ARTIFACT", "MISSING_EXISTING_BASELINE", "PENDING_REQUIRED_ARTIFACT", "UNRESOLVED_INTERNAL_REFERENCE"}


def validate(data: dict[str, Any], source: Path | None) -> list[str]:
    errors: list[str] = []
    if data.get("meta", {}).get("artifact_kind") != "requirement_source_dependency_review":
        errors.append("meta.artifact_kind must be requirement_source_dependency_review")
    dependencies = data.get("dependencies")
    findings = data.get("findings")
    if not isinstance(dependencies, list) or not isinstance(findings, list):
        return [*errors, "dependencies and findings must be arrays"]
    dependency_ids: list[str] = []
    for index, item in enumerate(dependencies):
        if not isinstance(item, dict):
            errors.append(f"dependency[{index}] must be an object")
            continue
        dependency_ids.append(item.get("dependency_id"))
        if item.get("reference_type") not in REFERENCE_TYPES or item.get("status") not in STATUSES:
            errors.append(f"dependency[{index}] has invalid type or status")
        if not all(item.get(key) for key in ("dependency_id", "reference_key", "target_name", "quote", "locator")):
            errors.append(f"dependency[{index}] lacks required trace fields")
        if item.get("reference_type") == "internal_reference" and item.get("status") == "available" and not item.get("target_locator"):
            errors.append(f"dependency[{index}] available internal reference lacks target_locator")
    if len(dependency_ids) != len(set(dependency_ids)):
        errors.append("duplicate dependency ids")
    known_dependencies = set(dependency_ids)
    finding_ids: list[str] = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(f"finding[{index}] must be an object")
            continue
        finding_ids.append(finding.get("finding_id"))
        if finding.get("code") not in CODES or finding.get("severity") not in {"REJECT", "REVIEW"}:
            errors.append(f"finding[{index}] has invalid code or severity")
        refs = finding.get("dependency_ids")
        if not isinstance(refs, list) or not refs or set(refs) - known_dependencies:
            errors.append(f"finding[{index}] has invalid dependency_ids")
        if finding.get("evidence_type") != "ABSENCE" or not finding.get("inspected_scope") or not finding.get("expected_element"):
            errors.append(f"finding[{index}] lacks absence evidence")
    if len(finding_ids) != len(set(finding_ids)):
        errors.append("duplicate finding ids")
    expected_summary = {
        "occurrence_count": len(dependencies),
        "distinct_target_count": len({item.get("reference_key") for item in dependencies if isinstance(item, dict)}),
        "by_type": {kind: sum(item.get("reference_type") == kind for item in dependencies if isinstance(item, dict)) for kind in sorted(REFERENCE_TYPES)},
        "by_status": {status: sum(item.get("status") == status for item in dependencies if isinstance(item, dict)) for status in ("available", "review_required", "missing")},
        "finding_count": len(findings),
    }
    if data.get("summary") != expected_summary:
        errors.append("summary must be derived from dependencies and findings")
    if source is not None:
        if not source.is_file():
            errors.append("primary source does not exist")
        elif data.get("source", {}).get("sha256") != hashlib.sha256(source.read_bytes()).hexdigest():
            errors.append("source review hash does not match primary source")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a requirement source dependency review")
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    data = json.loads(args.review.read_text(encoding="utf-8"))
    errors = validate(data, args.source)
    print(json.dumps({"verdict": "PASS" if not errors else "FAIL", "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
