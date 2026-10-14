#!/usr/bin/env python3
"""Refresh the deterministic graph and emit bounded semantic invalidation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}{result.stderr}")
    return result


def entity_ids(graph: dict[str, Any]) -> set[str]:
    specs = (
        ("modules", "module_id"), ("functions", "function_id"),
        ("atomic_functions", "atomic_id"), ("business_fields", "field_id"),
        ("business_objects", "object_id"), ("field_usages", "field_usage_id"),
        ("business_rules", "rule_id"), ("states", "state_id"),
        ("test_cases", "case_id"),
    )
    return {item[key] for array, key in specs for item in graph.get(array, []) if isinstance(item, dict) and item.get(key)}


def source_unit_changes(before: dict[str, Any], after: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    old_units = before.get("source_units", [])
    new_units = after.get("source_units", [])
    if not old_units or not new_units or any(
        not item.get("semantic_key") or not item.get("content_sha256")
        for item in [*old_units, *new_units]
    ):
        return "FULL_REVIEW_REQUIRED_LEGACY_LEDGER", []
    old = {item["semantic_key"]: item for item in old_units}
    new = {item["semantic_key"]: item for item in new_units}
    changes: list[dict[str, Any]] = []
    for key in sorted(old.keys() | new.keys()):
        if key not in old:
            change_type = "ADDED"
        elif key not in new:
            change_type = "DELETED"
        elif old[key]["content_sha256"] != new[key]["content_sha256"]:
            change_type = "MODIFIED"
        else:
            continue
        changes.append({
            "change_type": change_type, "semantic_key": key,
            "before_unit_id": old.get(key, {}).get("unit_id"), "after_unit_id": new.get(key, {}).get("unit_id"),
            "before_locator": old.get(key, {}).get("locator"), "after_locator": new.get(key, {}).get("locator"),
        })
    return "BOUNDED", changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild deterministic facts and invalidate only impacted semantic work")
    parser.add_argument("--before-graph", required=True, type=Path, help="Previous schema 1.4 typed graph")
    parser.add_argument("--source", required=True, type=Path, help="Current Markdown requirement")
    parser.add_argument("--source-review", type=Path, help="Updated qa-requirement-review source dependency review")
    parser.add_argument("--review", type=Path, help="Updated six-dimension requirement review; emits a READY-only test-design input")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--max-depth", type=int, default=3)
    args = parser.parse_args()
    for path in (args.before_graph, args.source, *([args.source_review] if args.source_review else []), *([args.review] if args.review else [])):
        if not path.is_file():
            raise SystemExit(f"missing input: {path}")
    before = json.loads(args.before_graph.read_text(encoding="utf-8"))
    if str(before.get("meta", {}).get("schema_version")) != "1.4":
        raise SystemExit("--before-graph must be a schema 1.4 typed graph")
    if any(item.get("origin") == "visual_evidence" for item in before.get("atomic_functions", [])):
        raise SystemExit("previous graph contains visual_evidence facts; revalidate visual evidence before incremental refresh")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pipeline_out = args.out_dir / "deterministic-refresh"
    pipeline = [sys.executable, str(SCRIPTS / "run_pipeline.py"), "--source", str(args.source), "--out-dir", str(pipeline_out)]
    if args.source_review:
        pipeline.extend(["--source-review", str(args.source_review)])
    if args.review:
        pipeline.extend(["--review", str(args.review)])
    else:
        pipeline.extend(["--through-stage", "enrich"])
    run(pipeline)
    generated = pipeline_out / f"{args.source.stem}_typed_graph.json"
    refreshed = json.loads(generated.read_text(encoding="utf-8"))

    # Test cases are downstream indexes, not extracted requirements. Preserve
    # them and only retain verifies edges whose targets still exist.
    test_cases = before.get("test_cases", []) if isinstance(before.get("test_cases", []), list) else []
    refreshed["test_cases"] = test_cases
    current_ids = entity_ids(refreshed)
    verifies = [
        relation for relation in before.get("relations", [])
        if relation.get("type") == "verifies"
        and relation.get("source_id") in {item.get("case_id") for item in test_cases}
        and relation.get("target_id") in current_ids
    ]
    existing_edges = {(item.get("source_id"), item.get("target_id"), item.get("type")) for item in refreshed.get("relations", [])}
    refreshed.setdefault("relations", []).extend(
        relation for relation in verifies
        if (relation.get("source_id"), relation.get("target_id"), relation.get("type")) not in existing_edges
    )
    refreshed.setdefault("coverage", {}).setdefault("graph_nodes", {})["test_cases"] = len(test_cases)
    refreshed["coverage"]["graph_edges"] = len(refreshed.get("relations", []))
    refreshed.setdefault("meta", {})["refresh"] = {
        "mode": "deterministic_full_scan_incremental_semantic_invalidation",
        "before_graph_sha256": sha256(args.before_graph),
        "source_sha256": sha256(args.source),
        "refreshed_at": now(),
    }
    refreshed_path = args.out_dir / f"{args.source.stem}_refreshed_typed_graph.json"
    refreshed_path.write_text(json.dumps(refreshed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    impact_path = args.out_dir / f"{args.source.stem}_change_impact.json"
    run([sys.executable, str(SCRIPTS / "compare_mapping_versions.py"), "--before", str(args.before_graph),
         "--after", str(refreshed_path), "--max-depth", str(args.max_depth), "--out", str(impact_path)])
    impact = json.loads(impact_path.read_text(encoding="utf-8"))
    unit_change_mode, unit_changes = source_unit_changes(before, refreshed)
    changed: set[str] = set()
    for change in impact.get("changes", []):
        if change.get("entity_id"):
            changed.add(change["entity_id"])
        relation = change.get("relation", {})
        changed.update(value for value in (relation.get("source_id"), relation.get("target_id")) if value)
    affected = changed | {item.get("entity_id") for item in impact.get("impact", {}).get("nodes", []) if item.get("entity_id")}
    old_atomic_ids = {item.get("atomic_id") for item in before.get("atomic_functions", [])}
    new_atomic_ids = {item.get("atomic_id") for item in refreshed.get("atomic_functions", [])}
    old_rule_ids = {item.get("rule_id") for item in before.get("business_rules", [])}
    new_rule_ids = {item.get("rule_id") for item in refreshed.get("business_rules", [])}
    case_ids = {item.get("case_id") for item in test_cases}
    deleted = sorted(item.get("entity_id") for item in impact.get("changes", []) if item.get("change_type") == "DELETED" and item.get("entity_id"))
    invalidation = {
        "meta": {"artifact_kind": "requirement_semantic_invalidation", "schema_version": "1.0", "generated_at": now()},
        "source_artifacts": {
            "before_graph": str(args.before_graph.resolve()), "before_graph_sha256": sha256(args.before_graph),
            "refreshed_graph": str(refreshed_path.resolve()), "refreshed_graph_sha256": sha256(refreshed_path),
            "change_impact": str(impact_path.resolve()), "change_impact_sha256": sha256(impact_path),
        },
        "strategy": "full deterministic extraction; incremental semantic review and retest",
        "source_unit_invalidation": {"mode": unit_change_mode, "changes": unit_changes, "changed_count": len(unit_changes)},
        "stale_entities_removed": deleted,
        "review_invalidation": {
            "atomic_ids": sorted(affected & (old_atomic_ids | new_atomic_ids)),
            "rule_ids": sorted(affected & (old_rule_ids | new_rule_ids)),
        },
        "test_invalidation": {
            "case_ids": sorted(affected & case_ids),
            "required_status": "RETEST_REQUIRED",
        },
        "unchanged_test_case_count": len(case_ids - affected),
        "release_policy": "READY_DIMENSIONS_ONLY; preserve unaffected cases and regenerate changed or newly READY slices",
        "acceptance": {
            "stale_cleanup": "PASS" if all(item not in entity_ids(refreshed) for item in deleted) else "FAIL",
            "semantic_review_complete": False,
            "affected_scope_downstream_eligible": False,
            "unaffected_test_case_count": len(case_ids - affected),
        },
    }
    invalidation_path = args.out_dir / f"{args.source.stem}_semantic_invalidation.json"
    invalidation_path.write_text(json.dumps(invalidation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    validation_path = args.out_dir / f"{args.source.stem}_refreshed_graph_validation.json"
    validation = run([sys.executable, str(SCRIPTS / "validate_mapping.py"), "--mapping", str(refreshed_path), "--source", str(args.source)])
    validation_path.write_text(validation.stdout, encoding="utf-8")
    result_summary = {
        "refreshed_graph": str(refreshed_path), "change_impact": str(impact_path),
        "semantic_invalidation": str(invalidation_path), "validation": str(validation_path),
        "changed_source_units": len(unit_changes), "source_unit_invalidation_mode": unit_change_mode,
        "changed_entities": len(changed), "affected_entities": len(affected),
        "stale_entities_removed": len(deleted), "test_cases_invalidated": len(affected & case_ids),
    }
    if args.review:
        result_summary["reviewed_graph"] = str(pipeline_out / f"{args.source.stem}_reviewed_graph.json")
        result_summary["ready_test_design_input"] = str(pipeline_out / f"{args.source.stem}_test_design_input.json")
    print(json.dumps(result_summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
