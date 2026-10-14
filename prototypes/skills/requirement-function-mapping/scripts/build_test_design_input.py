#!/usr/bin/env python3
"""Compile reviewed graph facts into hallucination-resistant test-design slices."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DIMENSION_STATUSES = {"READY", "REVIEW_REQUIRED", "BLOCKED", "NOT_APPLICABLE"}


def stable_id(prefix: str, *parts: Any) -> str:
    value = "|".join(" ".join(str(part or "").split()).casefold() for part in parts)
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:12].upper()}"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_record(proof: dict[str, Any]) -> dict[str, Any]:
    evidence_id = stable_id("EVD", proof.get("source_id"), proof.get("locator"), proof.get("quote"))
    return {"evidence_id": evidence_id, "source_id": proof.get("source_id"), "locator": proof.get("locator"), "quote": proof.get("quote")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build test-design slices from a reviewed requirement graph")
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--review", type=Path, help="Deprecated fallback; apply the review to the graph first")
    parser.add_argument("--atomic-id", action="append", help="Compile only this atomic function; repeat for a bounded batch")
    parser.add_argument("--ready-only", action="store_true", help="Keep only items with at least one READY dimension")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    if args.review and not mapping.get("review_projection"):
        raise SystemExit("review is not projected onto the graph; run apply_review_to_mapping.py first")
    graph_snapshot_id = mapping.get("meta", {}).get("graph_snapshot_id") or stable_id("GRAPH", file_hash(args.mapping))
    functions = {item.get("function_id"): item for item in mapping.get("functions", []) if isinstance(item, dict)}
    fields = {item.get("field_id"): item for item in mapping.get("business_fields", []) if isinstance(item, dict)}
    graph_rules = {item.get("rule_id"): item for item in mapping.get("business_rules", []) if isinstance(item, dict)}
    graph_usages: dict[str, list[dict[str, Any]]] = {}
    for usage in mapping.get("field_usages", []):
        if isinstance(usage, dict):
            graph_usages.setdefault(usage.get("atomic_id"), []).append(usage)
    business_flows = [item for item in mapping.get("business_flows", []) if isinstance(item, dict)]
    bindings: dict[str, list[dict[str, Any]]] = {}
    for binding in mapping.get("field_bindings", []):
        if isinstance(binding, dict):
            bindings.setdefault(binding.get("atomic_id"), []).append(binding)

    evidence_registry: dict[str, dict[str, Any]] = {}
    rule_registry: dict[str, dict[str, Any]] = {}

    def register_evidence(proofs: list[dict[str, Any]]) -> list[str]:
        ids: list[str] = []
        for proof in proofs:
            if not isinstance(proof, dict) or not proof.get("source_id") or not proof.get("locator") or not proof.get("quote"):
                continue
            record = evidence_record(proof)
            evidence_registry[record["evidence_id"]] = record
            ids.append(record["evidence_id"])
        return sorted(set(ids))

    def register_rule(kind: str, owner_id: str, statement: Any, proofs: list[dict[str, Any]]) -> str:
        rule_id = stable_id("RULE", kind, owner_id, statement)
        rule_registry[rule_id] = {
            "rule_id": rule_id, "kind": kind, "owner_id": owner_id, "statement": str(statement),
            "evidence_ids": register_evidence(proofs), "provenance_type": "REQUIREMENT_FACT",
        }
        return rule_id

    def register_graph_rule(rule_id: str) -> str:
        rule = graph_rules.get(rule_id, {})
        if not rule:
            return rule_id
        rule_registry[rule_id] = {
            "rule_id": rule_id, "kind": rule.get("category"),
            "owner_id": (rule.get("applies_to_ids") or [None])[0], "statement": rule.get("statement"),
            "evidence_ids": register_evidence(rule.get("evidence", [])), "provenance_type": "REQUIREMENT_FACT",
        }
        return rule_id

    items: list[dict[str, Any]] = []
    dimension_counts = {status: 0 for status in DIMENSION_STATUSES}
    all_atomics = [item for item in mapping.get("atomic_functions", []) if isinstance(item, dict)]
    requested_atomic_ids = set(args.atomic_id or [])
    known_atomic_ids = {item.get("atomic_id") for item in all_atomics}
    unknown_atomic_ids = requested_atomic_ids - known_atomic_ids
    if unknown_atomic_ids:
        raise SystemExit(f"unknown atomic ids: {', '.join(sorted(unknown_atomic_ids))}")
    selected_atomics = [item for item in all_atomics if not requested_atomic_ids or item.get("atomic_id") in requested_atomic_ids]
    for atomic in selected_atomics:
        if not isinstance(atomic, dict):
            continue
        atomic_id = atomic.get("atomic_id")
        quality_review = atomic.get("quality_review") if isinstance(atomic.get("quality_review"), dict) else {}
        gates = quality_review.get("dimension_eligibility")
        if not isinstance(gates, dict):
            gates = {"functional": {"status": "BLOCKED", "reasons": ["图谱尚未应用需求评审结果"], "finding_ids": []}}
        for gate in gates.values():
            status = gate.get("status") if isinstance(gate, dict) else None
            if status in dimension_counts:
                dimension_counts[status] += 1

        atomic_evidence_ids = register_evidence(atomic.get("evidence", []))
        if graph_rules and isinstance(atomic.get("rule_ids"), list):
            atomic_rule_ids = [register_graph_rule(rule_id) for rule_id in atomic.get("rule_ids", [])]
        else:
            atomic_rule_ids = [register_rule("operation", atomic_id, rule, atomic.get("evidence", []))
                               for rule in atomic.get("processing_rules", [])]
        field_usages = []
        source_usages = graph_usages.get(atomic_id) or bindings.get(atomic_id, [])
        for binding in source_usages:
            field = fields.get(binding.get("field_id"), {})
            binding_id = binding.get("field_usage_id") or stable_id("FUSE", atomic_id, binding.get("field_id"), binding.get("direction"), binding.get("usages"))
            evidence_ids = register_evidence(binding.get("evidence", []))
            if graph_rules and binding.get("rule_ids") is not None:
                rule_ids = [register_graph_rule(rule_id) for rule_id in binding.get("rule_ids", [])]
            else:
                rule_ids = [register_rule("field_usage", binding_id, rule, binding.get("evidence", []))
                            for rule in binding.get("rules", [])]
            field_usages.append({
                "field_usage_id": binding_id, "field_id": binding.get("field_id"),
                "business_name": field.get("business_name"), "business_object": field.get("business_object"),
                "data_type": field.get("data_type"), "required_here": binding.get("required_here"),
                "usages": binding.get("usages", []), "direction": binding.get("direction"),
                "rule_ids": rule_ids, "evidence_ids": evidence_ids,
                "unresolved_attributes": field.get("unresolved_attributes", []),
            })

        ready_dimensions = sorted(name for name, gate in gates.items() if gate.get("status") == "READY")
        function_id = atomic.get("function_id")
        relation_context = []
        for relation in mapping.get("relations", []):
            if relation.get("type") not in {"references", "depends_on", "state_flow", "data_flow", "conflict"}:
                continue
            if not ({relation.get("source_id"), relation.get("target_id")} & {atomic_id, function_id}):
                continue
            relation_context.append({
                "relation_id": relation.get("relation_id"), "source_id": relation.get("source_id"),
                "target_id": relation.get("target_id"), "type": relation.get("type"),
                "note": relation.get("note"), "evidence_ids": register_evidence(relation.get("evidence", [])),
            })
        flow_context = [
            {"flow_id": flow.get("flow_id"), "name": flow.get("name"), "step_ids": flow.get("step_ids", []),
             "evidence_ids": register_evidence(flow.get("evidence", []))}
            for flow in business_flows if atomic_id in flow.get("step_ids", [])
        ]
        items.append({
            "test_design_item_id": stable_id("TDI", atomic_id, graph_snapshot_id),
            "item_kind": "functional",
            "graph_snapshot_id": graph_snapshot_id,
            "requirement_ids": quality_review.get("review_requirement_ids", []),
            "function_id": function_id, "function_name": functions.get(function_id, {}).get("name"),
            "module": functions.get(function_id, {}).get("module"),
            "atomic_id": atomic_id, "title": atomic.get("name"), "category": atomic.get("category"),
            "actor": atomic.get("actor"), "trigger": atomic.get("trigger"), "preconditions": atomic.get("preconditions", []),
            "action": atomic.get("action"), "operation_rule_ids": atomic_rule_ids, "field_usages": field_usages,
            "outputs": atomic.get("outputs", []), "state_changes": atomic.get("state_changes", []),
            "branches": atomic.get("branches", []), "evidence_ids": atomic_evidence_ids,
            "dimension_eligibility": gates, "eligible_dimensions": ready_dimensions,
            "excluded_finding_ids": quality_review.get("open_finding_ids", []),
            "relation_context": relation_context, "flow_context": flow_context,
        })

    nfr_nodes = [item for item in mapping.get("non_functional_requirements", []) if isinstance(item, dict)]
    for requirement in nfr_nodes:
        quality_review = requirement.get("quality_review") if isinstance(requirement.get("quality_review"), dict) else {}
        gates = quality_review.get("dimension_eligibility")
        if not isinstance(gates, dict):
            gates = {"nfr": {"status": "BLOCKED", "reasons": ["非功能需求尚未应用评审结果"], "finding_ids": []}}
        for gate in gates.values():
            status = gate.get("status") if isinstance(gate, dict) else None
            if status in dimension_counts:
                dimension_counts[status] += 1
        ready_dimensions = sorted(name for name, gate in gates.items() if gate.get("status") == "READY")
        requirement_id = requirement.get("requirement_id")
        items.append({
            "test_design_item_id": stable_id("TDI", "nfr", requirement_id, graph_snapshot_id),
            "item_kind": "non_functional", "nfr_id": requirement_id,
            "graph_snapshot_id": graph_snapshot_id, "requirement_ids": [requirement_id],
            "title": requirement.get("title"), "category": "nfr",
            "quality_attribute": requirement.get("quality_attribute"),
            "actor": None, "trigger": None, "preconditions": [],
            "action": f"验证非功能要求：{requirement.get('summary')}",
            "operation_rule_ids": [], "field_usages": [], "outputs": [], "state_changes": [],
            "branches": [requirement.get("summary")],
            "evidence_ids": register_evidence(requirement.get("source_refs", [])),
            "dimension_eligibility": gates, "eligible_dimensions": ready_dimensions,
            "excluded_finding_ids": quality_review.get("open_finding_ids", []),
            "relation_context": [], "flow_context": [],
        })

    if args.ready_only:
        items = [item for item in items if item.get("eligible_dimensions")]
        dimension_counts = {status: 0 for status in DIMENSION_STATUSES}
        for item in items:
            for gate in item["dimension_eligibility"].values():
                dimension_counts[gate["status"]] += 1

    used_rule_ids = {
        rule_id for item in items for rule_id in item.get("operation_rule_ids", [])
    } | {
        rule_id for item in items for usage in item.get("field_usages", []) for rule_id in usage.get("rule_ids", [])
    }
    used_evidence_ids = {
        evidence_id for item in items for evidence_id in item.get("evidence_ids", [])
    } | {
        evidence_id for item in items for usage in item.get("field_usages", []) for evidence_id in usage.get("evidence_ids", [])
    } | {
        evidence_id for item in items for relation in item.get("relation_context", []) for evidence_id in relation.get("evidence_ids", [])
    } | {
        evidence_id for item in items for flow in item.get("flow_context", []) for evidence_id in flow.get("evidence_ids", [])
    }
    for rule_id in used_rule_ids:
        used_evidence_ids.update(rule_registry.get(rule_id, {}).get("evidence_ids", []))

    ready_count = dimension_counts["READY"]
    applicable_count = ready_count + dimension_counts["REVIEW_REQUIRED"] + dimension_counts["BLOCKED"]
    if ready_count and ready_count == applicable_count:
        verdict, eligible = "PASS", True
    elif ready_count:
        verdict, eligible = "PARTIAL_PASS", True
    else:
        verdict, eligible = "BLOCKED", False
    review_projection = mapping.get("review_projection", {})
    review_scope = (
        "FULLY_REVIEWED_SOURCE"
        if review_projection.get("review_verdict") == "PASS"
        and review_projection.get("review_downstream_eligible") is True
        and review_projection.get("not_reviewed_assessment_count") == 0
        else "PARTIAL_REVIEW_PROJECTION"
    )
    packet = {
        "meta": {
            "schema_version": "2.0", "artifact_kind": "test_design_input",
            "lifecycle_status": "ACCEPTED" if verdict == "PASS" else ("PARTIALLY_ACCEPTED" if eligible else "BLOCKED"),
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        },
        "source_artifacts": {
            "mapping": args.mapping.name, "mapping_sha256": file_hash(args.mapping),
            "review": review_projection.get("review_id"),
            "review_sha256": review_projection.get("review_sha256"),
            "review_lifecycle_status": review_projection.get("review_lifecycle_status"),
            "review_verdict": review_projection.get("review_verdict"),
            "review_downstream_eligible": review_projection.get("review_downstream_eligible", False),
            "not_reviewed_assessment_count": review_projection.get("not_reviewed_assessment_count"),
        },
        "graph_snapshot_id": graph_snapshot_id,
        "fact_policy": {
            "formal_case_dimensions": "READY_ONLY", "allowed_provenance_types": ["REQUIREMENT_FACT", "TEST_DERIVATION"],
            "assumptions_allowed": False, "missing_oracle_action": "BLOCK_AND_RAISE_QUESTION",
        },
        "evidence_registry": sorted((item for key, item in evidence_registry.items() if key in used_evidence_ids), key=lambda item: item["evidence_id"]),
        "rule_registry": sorted((item for key, item in rule_registry.items() if key in used_rule_ids), key=lambda item: item["rule_id"]),
        "items": items,
        "coverage": {"source_item_count": len(all_atomics) + len(nfr_nodes), "selected_item_count": len(selected_atomics) + len(nfr_nodes), "item_count": len(items), "dimension_status_counts": dimension_counts},
        "acceptance": {
            "verdict": verdict, "downstream_eligible": eligible,
            "source_review_scope": review_scope,
            "scope": "READY_DIMENSIONS_ONLY" if eligible else "NONE",
            "reasons": [] if verdict == "PASS" else [f"仅 {ready_count}/{applicable_count} 个适用测试维度达到 READY"],
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
