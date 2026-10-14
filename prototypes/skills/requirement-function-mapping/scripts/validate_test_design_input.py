#!/usr/bin/env python3
"""Validate provenance, traceability, and dimension gates in test-design input."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


STATUSES = {"READY", "REVIEW_REQUIRED", "BLOCKED", "NOT_APPLICABLE"}


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("meta", {}).get("artifact_kind") != "test_design_input":
        errors.append("meta.artifact_kind must be test_design_input")
    if data.get("meta", {}).get("schema_version") != "2.0":
        errors.append("meta.schema_version must be 2.0")
    if not data.get("graph_snapshot_id"):
        errors.append("graph_snapshot_id is required")
    policy = data.get("fact_policy", {})
    if policy.get("formal_case_dimensions") != "READY_ONLY" or policy.get("assumptions_allowed") is not False:
        errors.append("fact_policy must restrict formal cases to READY dimensions and forbid assumptions")

    evidence = data.get("evidence_registry")
    rules = data.get("rule_registry")
    items = data.get("items")
    if not isinstance(evidence, list) or not isinstance(rules, list) or not isinstance(items, list):
        return [*errors, "evidence_registry, rule_registry, and items must be arrays"]
    evidence_ids = [item.get("evidence_id") for item in evidence if isinstance(item, dict)]
    rule_ids = [item.get("rule_id") for item in rules if isinstance(item, dict)]
    if len(evidence_ids) != len(set(evidence_ids)) or None in evidence_ids:
        errors.append("evidence_registry contains missing or duplicate ids")
    if len(rule_ids) != len(set(rule_ids)) or None in rule_ids:
        errors.append("rule_registry contains missing or duplicate ids")
    evidence_set, rule_set = set(evidence_ids), set(rule_ids)
    for record in evidence:
        if not all(record.get(key) for key in ("evidence_id", "source_id", "locator", "quote")):
            errors.append(f"evidence {record.get('evidence_id', '<missing>')} is incomplete")
    for rule in rules:
        if rule.get("provenance_type") != "REQUIREMENT_FACT":
            errors.append(f"rule {rule.get('rule_id', '<missing>')} has invalid provenance_type")
        refs = rule.get("evidence_ids")
        if not isinstance(refs, list) or not refs or set(refs) - evidence_set:
            errors.append(f"rule {rule.get('rule_id', '<missing>')} lacks valid evidence")

    item_ids: set[str] = set()
    actual_counts = {status: 0 for status in STATUSES}
    ready_dimensions = 0
    for index, item in enumerate(items):
        item_id = item.get("test_design_item_id") if isinstance(item, dict) else None
        if not isinstance(item, dict):
            errors.append(f"item[{index}] must be an object")
            continue
        if not item_id or item_id in item_ids:
            errors.append(f"item[{index}] has missing or duplicate id")
        item_ids.add(item_id)
        item_kind = item.get("item_kind", "functional")
        required_keys = ("function_id", "atomic_id", "title", "action", "graph_snapshot_id") if item_kind == "functional" else ("nfr_id", "title", "action", "graph_snapshot_id")
        if item_kind not in {"functional", "non_functional"}:
            errors.append(f"item {item_id or index} has invalid item_kind")
        for key in required_keys:
            if not item.get(key):
                errors.append(f"item {item_id or index} lacks {key}")
        if item.get("graph_snapshot_id") != data.get("graph_snapshot_id"):
            errors.append(f"item {item_id or index} belongs to another graph snapshot")
        for key in ("requirement_ids", "preconditions", "operation_rule_ids", "field_usages", "outputs", "state_changes",
                    "branches", "evidence_ids", "eligible_dimensions", "excluded_finding_ids", "relation_context", "flow_context"):
            if not isinstance(item.get(key), list):
                errors.append(f"item {item_id or index} {key} must be an array")
        if set(item.get("operation_rule_ids", [])) - rule_set:
            errors.append(f"item {item_id or index} references unknown operation rule")
        if set(item.get("evidence_ids", [])) - evidence_set:
            errors.append(f"item {item_id or index} references unknown evidence")
        gates = item.get("dimension_eligibility")
        if not isinstance(gates, dict) or not gates:
            errors.append(f"item {item_id or index} lacks dimension_eligibility")
            continue
        computed_ready = []
        for dimension, gate in gates.items():
            status = gate.get("status") if isinstance(gate, dict) else None
            if status not in STATUSES or not isinstance(gate.get("reasons"), list) or not isinstance(gate.get("finding_ids"), list):
                errors.append(f"item {item_id or index} has invalid gate {dimension}")
                continue
            actual_counts[status] += 1
            if status == "READY":
                ready_dimensions += 1
                computed_ready.append(dimension)
                if gate.get("reasons") or gate.get("finding_ids"):
                    errors.append(f"READY gate {item_id}/{dimension} contains blockers")
                if not item.get("evidence_ids") and dimension != "field_validation":
                    errors.append(f"READY gate {item_id}/{dimension} lacks evidence")
        if sorted(item.get("eligible_dimensions", [])) != sorted(computed_ready):
            errors.append(f"item {item_id or index} eligible_dimensions does not match gates")
        for usage in item.get("field_usages", []):
            if not isinstance(usage, dict) or not usage.get("field_usage_id") or not usage.get("field_id"):
                errors.append(f"item {item_id or index} contains invalid field usage")
                continue
            if set(usage.get("rule_ids", [])) - rule_set or set(usage.get("evidence_ids", [])) - evidence_set:
                errors.append(f"field usage {usage.get('field_usage_id')} contains dangling references")
        for context_name in ("relation_context", "flow_context"):
            for context in item.get(context_name, []):
                if not isinstance(context, dict) or set(context.get("evidence_ids", [])) - evidence_set:
                    errors.append(f"item {item_id or index} has invalid {context_name}")

    coverage = data.get("coverage", {})
    if coverage.get("item_count") != len(items) or coverage.get("dimension_status_counts") != actual_counts:
        errors.append("coverage does not match items")
    acceptance = data.get("acceptance", {})
    eligible = acceptance.get("downstream_eligible")
    if not isinstance(eligible, bool) or eligible != (ready_dimensions > 0):
        errors.append("acceptance.downstream_eligible must equal presence of READY dimensions")
    expected_verdict = "BLOCKED" if not ready_dimensions else (
        "PASS" if actual_counts["BLOCKED"] == 0 and actual_counts["REVIEW_REQUIRED"] == 0 else "PARTIAL_PASS"
    )
    if acceptance.get("verdict") != expected_verdict:
        errors.append(f"acceptance.verdict must be {expected_verdict}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--require-accepted", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        errors = validate(data) if isinstance(data, dict) else ["root must be an object"]
    except (OSError, ValueError) as exc:
        errors, data = [str(exc)], {}
    eligible = not errors and data.get("acceptance", {}).get("downstream_eligible") is True
    print(json.dumps({"structural_verdict": "PASS" if not errors else "FAIL", "downstream_eligible": eligible, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors and (eligible or not args.require_accepted) else 2


if __name__ == "__main__":
    raise SystemExit(main())
