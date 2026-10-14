#!/usr/bin/env python3
"""Validate requirement-function-mapping JSON without external dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

STATUS = {"confirmed", "inferred", "unresolved"}
PROVENANCE = {"explicit", "derived", "inferred", "unresolved"}
USAGES = {"input", "query", "display", "output", "derived", "validation", "control", "audit"}
DIRECTIONS = {"read", "write", "read_write"}
SURFACES = {"query_condition", "form_input", "list_column", "detail_field", "result_field", "api_request", "api_response", "persistent_field", "derived_field", "audit_field", "control_field", "file_component"}
FIELD_RELATIONS = {"echo_of", "masked_from", "derived_from", "transformed_from", "copied_from", "same_concept_as"}
ENTITY_RELATIONS = {"contains", "references", "depends_on", "state_flow", "data_flow", "conflict", "uses_field", "field_of", "constrained_by", "has_state", "verifies"}
INPUT_SURFACES = {"query_condition", "form_input", "api_request", "file_component"}
OUTPUT_SURFACES = {"list_column", "detail_field", "result_field", "api_response", "derived_field"}
TOP_LEVEL = {"meta", "sources", "functions", "atomic_functions", "business_fields", "field_contexts", "field_bindings", "field_relations", "relations", "gaps", "coverage", "audit"}
READINESS = {"ready", "review_required", "blocked"}


def check_primary_quote(source_text: str | None, primary_source_id: str | None, proof: dict[str, Any]) -> bool:
    """Visual/media locators belong to the source package, not Markdown text."""
    if source_text is None or proof.get("source_id") != primary_source_id:
        return True
    if re.match(r"^L\d+:", str(proof.get("locator", ""))):
        return True
    return str(proof.get("quote", "")) in source_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate function, atomic function, and field mappings.")
    parser.add_argument("--mapping", required=True, type=Path, help="Mapping JSON file")
    parser.add_argument("--source", type=Path, help="Optional primary Markdown source for quote checks")
    parser.add_argument("--format", choices=("json", "text"), default="json", help="Diagnostic output format")
    return parser.parse_args()


def version_at_least(value: Any, expected: str) -> bool:
    try:
        return tuple(int(part) for part in str(value).split(".")) >= tuple(int(part) for part in expected.split("."))
    except ValueError:
        return False


def structured_diagnostic(message: str, severity: str) -> dict[str, Any]:
    """Add stable repair metadata while retaining legacy human-readable messages."""
    patterns = (
        (r"^duplicate (.+?) ids?:\s*(.+)$", "DUPLICATE_ENTITY_ID", "extraction-contract#实体与稳定标识"),
        (r"^missing top-level keys:\s*(.+)$", "MISSING_REQUIRED_PROPERTY", "extraction-contract#顶层结构"),
        (r"references unknown", "DANGLING_REFERENCE", "typed-graph-contract#边"),
        (r"invalid (status|type|direction|usages|provenance)", "INVALID_ENUM_VALUE", "state-model#状态模型与组合门禁"),
        (r"coverage\.", "COVERAGE_MISMATCH", "extraction-contract#缺口覆盖与去重"),
        (r"evidence|quote not found", "INVALID_EVIDENCE", "extraction-contract#证据"),
        (r"downstream_eligible|semantic review", "INVALID_STATE_COMBINATION", "state-model#不变量"),
    )
    code, anchor = "CONTRACT_VIOLATION", "extraction-contract"
    entity_ids: list[str] = []
    for pattern, candidate, rule_anchor in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            code, anchor = candidate, rule_anchor
            if candidate == "DUPLICATE_ENTITY_ID" and match.lastindex and match.lastindex >= 2:
                entity_ids = [value.strip() for value in match.group(2).split(",") if value.strip()]
            break
    indexed = re.search(r"([a-z_ ]+)\[(\d+)\]", message, re.IGNORECASE)
    diagnostic = {"code": code, "severity": severity, "message": message, "rule_anchor": anchor}
    if entity_ids:
        diagnostic["entity_ids"] = entity_ids
    if indexed:
        diagnostic["json_path"] = f"$.{indexed.group(1).strip().replace(' ', '_')}[{indexed.group(2)}]"
    return diagnostic


def emit_result(result: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"verdict: {result['verdict']}")
    for item in result.get("diagnostics", []):
        location = f" {item['json_path']}" if item.get("json_path") else ""
        print(f"{item['severity'].upper()} {item['code']}{location}: {item['message']} [{item['rule_anchor']}]")


def duplicates(items: list[Any], key: str) -> set[str]:
    values = [item.get(key) for item in items if isinstance(item, dict) and item.get(key)]
    return {value for value in values if values.count(value) > 1}


def validate(data: dict[str, Any], source_text: str | None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    missing = sorted(TOP_LEVEL - data.keys())
    if missing:
        errors.append(f"missing top-level keys: {', '.join(missing)}")

    arrays = ["sources", "functions", "atomic_functions", "business_fields", "field_contexts", "field_bindings", "field_relations", "relations"]
    for name in arrays:
        if not isinstance(data.get(name), list):
            errors.append(f"{name} must be an array")
    if errors:
        return errors, warnings

    sources, functions = data["sources"], data["functions"]
    modules = data.get("modules", [])
    if not isinstance(modules, list):
        errors.append("modules must be an array when present")
        modules = []
    atomics, fields, bindings = data["atomic_functions"], data["business_fields"], data["field_bindings"]
    contexts, field_relations = data["field_contexts"], data["field_relations"]
    for items, key, label in [(sources, "source_id", "source"), (functions, "function_id", "function"), (atomics, "atomic_id", "atomic function"), (fields, "field_id", "business field")]:
        found = duplicates(items, key)
        if found:
            errors.append(f"duplicate {label} ids: {', '.join(sorted(found))}")

    source_ids = {x.get("source_id") for x in sources if isinstance(x, dict)}
    primary_source_id = sources[0].get("source_id") if sources and isinstance(sources[0], dict) else None
    function_ids = {x.get("function_id") for x in functions if isinstance(x, dict)}
    atomic_ids = {x.get("atomic_id") for x in atomics if isinstance(x, dict)}
    field_ids = {x.get("field_id") for x in fields if isinstance(x, dict)}
    module_ids = {x.get("module_id") for x in modules if isinstance(x, dict)}
    if duplicates(modules, "module_id"):
        errors.append("duplicate module ids")
    for module in modules:
        if not isinstance(module, dict) or not module.get("module_id") or not module.get("name"):
            errors.append("module lacks module_id or name")

    business_objects = data.get("business_objects", [])
    field_usages = data.get("field_usages", [])
    business_rules = data.get("business_rules", [])
    business_flows = data.get("business_flows", [])
    states = data.get("states", [])
    flow_candidates = data.get("business_flow_candidates", [])
    typed_arrays = {
        "business_objects": business_objects, "field_usages": field_usages, "business_rules": business_rules,
        "business_flows": business_flows, "states": states,
    }
    for name, values in typed_arrays.items():
        if not isinstance(values, list):
            errors.append(f"{name} must be an array when present")
            typed_arrays[name] = []
    business_objects, field_usages, business_rules = typed_arrays["business_objects"], typed_arrays["field_usages"], typed_arrays["business_rules"]
    states = typed_arrays["states"]
    if not isinstance(flow_candidates, list):
        errors.append("business_flow_candidates must be an array when present")
        flow_candidates = []
    object_ids = {item.get("object_id") for item in business_objects if isinstance(item, dict)}
    usage_ids = {item.get("field_usage_id") for item in field_usages if isinstance(item, dict)}
    rule_ids = {item.get("rule_id") for item in business_rules if isinstance(item, dict)}
    state_ids = {item.get("state_id") for item in states if isinstance(item, dict)}
    for values, key, label in ((business_objects, "object_id", "business object"), (field_usages, "field_usage_id", "field usage"), (business_rules, "rule_id", "business rule")):
        if duplicates(values, key):
            errors.append(f"duplicate {label} ids")
    for usage in field_usages:
        if usage.get("atomic_id") not in atomic_ids or usage.get("field_id") not in field_ids:
            errors.append(f"field usage {usage.get('field_usage_id', '<missing>')} has dangling atomic or field reference")
        if set(usage.get("rule_ids", [])) - rule_ids:
            errors.append(f"field usage {usage.get('field_usage_id', '<missing>')} references unknown rule")
    for rule in business_rules:
        if not rule.get("statement") or not rule.get("category") or not isinstance(rule.get("applies_to_ids"), list):
            errors.append(f"business rule {rule.get('rule_id', '<missing>')} is incomplete")
        if not isinstance(rule.get("evidence"), list) or not rule.get("evidence"):
            errors.append(f"business rule {rule.get('rule_id', '<missing>')} lacks evidence")
    if duplicates(states, "state_id"):
        errors.append("duplicate state ids")
    for state in states:
        if state.get("field_id") not in field_ids or not state.get("value") or not state.get("evidence"):
            errors.append(f"state {state.get('state_id', '<missing>')} is incomplete")
    if duplicates(flow_candidates, "candidate_id"):
        errors.append("duplicate business flow candidate ids")
    for candidate in flow_candidates:
        if candidate.get("function_id") not in function_ids or candidate.get("status") != "review_required" or not candidate.get("evidence"):
            errors.append(f"business flow candidate {candidate.get('candidate_id', '<missing>')} is incomplete")

    def check_entity(item: Any, key: str, label: str) -> None:
        if not isinstance(item, dict):
            errors.append(f"{label} entry must be an object")
            return
        entity_id = item.get(key, "<missing>")
        if not item.get(key):
            errors.append(f"{label} lacks {key}")
        status = item.get("status")
        if status not in STATUS:
            errors.append(f"{label} {entity_id} has invalid status")
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list):
            errors.append(f"{label} {entity_id} evidence must be an array")
            return
        if status == "confirmed" and not evidence:
            errors.append(f"confirmed {label} {entity_id} has no evidence")
        for index, proof in enumerate(evidence):
            if not isinstance(proof, dict):
                errors.append(f"{label} {entity_id} evidence[{index}] must be an object")
                continue
            if proof.get("source_id") not in source_ids:
                errors.append(f"{label} {entity_id} references unknown source_id")
            quote = proof.get("quote")
            if not proof.get("locator") or not quote:
                errors.append(f"{label} {entity_id} evidence[{index}] lacks locator or quote")
            elif not check_primary_quote(source_text, primary_source_id, proof):
                message = f"{label} {entity_id} quote not found in primary source: {quote[:60]}"
                (errors if status == "confirmed" else warnings).append(message)

    for item in functions:
        check_entity(item, "function_id", "function")
        if isinstance(item, dict) and not item.get("name"):
            errors.append(f"function {item.get('function_id', '<missing>')} lacks name")
        if isinstance(item, dict) and item.get("parent_function_id") is not None:
            if item.get("parent_function_id") not in function_ids:
                errors.append(f"function {item.get('function_id', '<missing>')} references unknown parent_function_id")
            elif item.get("parent_function_id") == item.get("function_id"):
                errors.append(f"function {item.get('function_id', '<missing>')} cannot parent itself")

    parents = {item.get("function_id"): item.get("parent_function_id") for item in functions if isinstance(item, dict)}
    for function_id in function_ids:
        seen: set[str] = set()
        current = function_id
        while current in parents and parents[current] is not None:
            current = parents[current]
            if current in seen:
                errors.append(f"function hierarchy contains a cycle at {function_id}")
                break
            seen.add(current)

    for item in atomics:
        check_entity(item, "atomic_id", "atomic function")
        if not isinstance(item, dict):
            continue
        item_id = item.get("atomic_id", "<missing>")
        if item.get("function_id") not in function_ids:
            errors.append(f"atomic function {item_id} references unknown function_id")
        for required in ("name", "action", "trigger"):
            if not item.get(required):
                errors.append(f"atomic function {item_id} lacks {required}")
        if not item.get("outputs") and not item.get("state_changes") and not item.get("branches"):
            errors.append(f"atomic function {item_id} has no observable result")
        if str(data.get("meta", {}).get("schema_version", "1.0")) >= "1.2":
            readiness = item.get("generation_readiness")
            if not isinstance(readiness, dict) or readiness.get("status") not in READINESS:
                errors.append(f"atomic function {item_id} lacks valid generation_readiness")
            elif not isinstance(readiness.get("reasons"), list):
                errors.append(f"atomic function {item_id} generation_readiness.reasons must be an array")
        for key in ("inputs", "outputs"):
            references = item.get(key, [])
            if not isinstance(references, list):
                errors.append(f"atomic function {item_id} {key} must be an array")
            else:
                unknown = set(references) - field_ids
                if unknown:
                    errors.append(f"atomic function {item_id} {key} references unknown field ids: {', '.join(sorted(unknown))}")

    for item in fields:
        check_entity(item, "field_id", "business field")
        if isinstance(item, dict) and (not item.get("business_name") or not item.get("business_object")):
            errors.append(f"business field {item.get('field_id', '<missing>')} lacks business_name or business_object")

    contexts_by_field: dict[str, list[str]] = {field_id: [] for field_id in field_ids}
    for index, context in enumerate(contexts):
        if not isinstance(context, dict):
            errors.append(f"field context[{index}] must be an object")
            continue
        field_id = context.get("field_id")
        surface = context.get("surface")
        if field_id not in field_ids:
            errors.append(f"field context[{index}] references unknown field_id")
        else:
            contexts_by_field[field_id].append(surface)
        if context.get("function_id") not in function_ids:
            errors.append(f"field context[{index}] references unknown function_id")
        if surface not in SURFACES:
            errors.append(f"field context[{index}] has invalid surface")
        if not context.get("location") or not context.get("role"):
            errors.append(f"field context[{index}] lacks location or role")
    for field_id, surfaces in contexts_by_field.items():
        if not surfaces:
            errors.append(f"business field {field_id} has no field context")
        if set(surfaces) & INPUT_SURFACES and set(surfaces) & OUTPUT_SURFACES:
            errors.append(f"business field {field_id} crosses input and output contexts; split fields and add lineage")

    for index, relation in enumerate(field_relations):
        if not isinstance(relation, dict):
            errors.append(f"field relation[{index}] must be an object")
            continue
        source_id, target_id = relation.get("source_field_id"), relation.get("target_field_id")
        if source_id not in field_ids or target_id not in field_ids:
            errors.append(f"field relation[{index}] references unknown field_id")
        if source_id == target_id:
            errors.append(f"field relation[{index}] cannot be a self relation")
        if relation.get("type") not in FIELD_RELATIONS:
            errors.append(f"field relation[{index}] has invalid type")
        evidence = relation.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"field relation[{index}] must contain evidence")
        else:
            for proof_index, proof in enumerate(evidence):
                if not isinstance(proof, dict) or proof.get("source_id") not in source_ids or not proof.get("locator") or not proof.get("quote"):
                    errors.append(f"field relation[{index}] evidence[{proof_index}] is invalid")
                    continue
                if not check_primary_quote(source_text, primary_source_id, proof):
                    errors.append(f"field relation[{index}] quote not found in primary source: {proof['quote'][:60]}")

    test_cases = data.get("test_cases", [])
    if not isinstance(test_cases, list):
        errors.append("test_cases must be an array when present")
        test_cases = []
    test_case_ids = {item.get("case_id") for item in test_cases if isinstance(item, dict) and item.get("case_id")}
    if duplicates(test_cases, "case_id"):
        errors.append("duplicate test case ids")
    for index, test_case in enumerate(test_cases):
        if not isinstance(test_case, dict) or not test_case.get("case_id"):
            errors.append(f"test case[{index}] lacks case_id")

    entity_ids = module_ids | function_ids | atomic_ids | field_ids | object_ids | usage_ids | rule_ids | state_ids | test_case_ids
    relations = data["relations"]
    duplicate_relation_ids = duplicates(relations, "relation_id")
    if duplicate_relation_ids:
        errors.append(f"duplicate relation ids: {', '.join(sorted(duplicate_relation_ids))}")
    for index, relation in enumerate(relations):
        if not isinstance(relation, dict):
            errors.append(f"relation[{index}] must be an object")
            continue
        if not relation.get("relation_id"):
            errors.append(f"relation[{index}] lacks relation_id")
        if relation.get("source_id") not in entity_ids or relation.get("target_id") not in entity_ids:
            errors.append(f"relation[{index}] references unknown entity id")
        if relation.get("type") not in ENTITY_RELATIONS:
            errors.append(f"relation[{index}] has invalid type")
        evidence = relation.get("evidence")
        if relation.get("type") != "contains" and (not isinstance(evidence, list) or not evidence):
            errors.append(f"relation[{index}] must contain evidence")
        elif relation.get("type") == "conflict" and isinstance(evidence, list) and len(evidence) < 2:
            errors.append(f"relation[{index}] conflict must preserve both evidence sides")
        elif isinstance(evidence, list):
            for proof_index, proof in enumerate(evidence):
                if not isinstance(proof, dict) or proof.get("source_id") not in source_ids or not proof.get("locator") or not proof.get("quote"):
                    errors.append(f"relation[{index}] evidence[{proof_index}] is invalid")
                    continue
                if not check_primary_quote(source_text, primary_source_id, proof):
                    errors.append(f"relation[{index}] quote not found in primary source: {proof['quote'][:60]}")

    schema_version = str(data.get("meta", {}).get("schema_version", "1.0"))
    artifact_kind = data.get("meta", {}).get("artifact_kind")
    compatible_kinds = {
        "1.1": {"full_discovery_draft"},
        "1.2": {"normalized_requirement_mapping"},
        "1.3": {"review_projected_mapping"},
        "1.4": {"typed_requirement_graph", "review_projected_typed_graph"},
    }
    if schema_version in compatible_kinds and artifact_kind not in compatible_kinds[schema_version]:
        errors.append(f"meta.artifact_kind {artifact_kind!r} is incompatible with schema {schema_version}")
    if schema_version != "1.0":
        source_units = data.get("source_units")
        if not isinstance(source_units, list):
            errors.append("schema 1.1+ requires source_units array")
            source_units = []
        unit_ids: list[str] = []
        for index, unit in enumerate(source_units):
            if not isinstance(unit, dict):
                errors.append(f"source unit[{index}] must be an object")
                continue
            unit_id = unit.get("unit_id")
            if not unit_id:
                errors.append(f"source unit[{index}] lacks unit_id")
            else:
                unit_ids.append(unit_id)
            if unit.get("source_id") not in source_ids:
                errors.append(f"source unit[{index}] references unknown source_id")
            if unit.get("status") not in {"processed", "review_required", "skipped", "unavailable"}:
                errors.append(f"source unit[{index}] has invalid status")
            if not unit.get("kind") or not unit.get("locator") or not isinstance(unit.get("relevant"), bool):
                errors.append(f"source unit[{index}] lacks kind, locator, or relevant flag")
            if not unit.get("semantic_key") or not re.fullmatch(r"[0-9a-f]{64}", str(unit.get("content_sha256", ""))):
                errors.append(f"source unit[{index}] lacks semantic_key or valid content_sha256")
            if unit.get("status") != "processed" and not unit.get("reason"):
                errors.append(f"source unit[{index}] must explain non-processed status")
            if unit.get("kind") == "reference_dependency":
                if unit.get("reference_type") not in {"internal_reference", "external_artifact", "existing_baseline", "pending_artifact"}:
                    errors.append(f"source unit[{index}] has invalid reference_type")
                if not unit.get("dependency_id") or not unit.get("reference_key") or not unit.get("target_name") or not unit.get("quote") or "blocking_scope" not in unit:
                    errors.append(f"source unit[{index}] reference dependency lacks dependency_id, key, target_name, quote, or blocking_scope")
                if not isinstance(unit.get("finding_ids"), list):
                    errors.append(f"source unit[{index}] reference dependency finding_ids must be an array")
                blocking_scope = unit.get("blocking_scope")
                if not isinstance(blocking_scope, dict) or not blocking_scope.get("source_id") or not blocking_scope.get("locator"):
                    errors.append(f"source unit[{index}] reference dependency has invalid blocking_scope")
                if unit.get("resolution_status") not in {"unresolved", "target_located", "artifact_available", "baseline_available"}:
                    errors.append(f"source unit[{index}] has invalid resolution_status")
                if unit.get("status") == "processed" and unit.get("resolution_status") == "unresolved":
                    errors.append(f"source unit[{index}] processed reference dependency is unresolved")
        repeated_units = {value for value in unit_ids if unit_ids.count(value) > 1}
        if repeated_units:
            errors.append(f"duplicate source unit ids: {', '.join(sorted(repeated_units))}")

        reference_units = [unit for unit in source_units if isinstance(unit, dict) and unit.get("kind") == "reference_dependency"]
        reference_summary = data.get("coverage", {}).get("reference_summary")
        if reference_units and artifact_kind == "full_discovery_draft":
            source_dependency_review = data.get("source_dependency_review")
            if not isinstance(source_dependency_review, dict) or source_dependency_review.get("artifact_kind") != "requirement_source_dependency_review":
                errors.append("reference dependencies require a projected requirement_source_dependency_review")
            expected_reference_summary = {
                "occurrence_count": len(reference_units),
                "distinct_target_count": len({unit.get("reference_key") for unit in reference_units}),
                "by_type": {kind: sum(unit.get("reference_type") == kind for unit in reference_units) for kind in sorted({"internal_reference", "external_artifact", "existing_baseline", "pending_artifact"})},
                "by_status": {status: sum(unit.get("status") == status for unit in reference_units) for status in ("processed", "review_required", "unavailable")},
            }
            if reference_summary != expected_reference_summary:
                errors.append("coverage.reference_summary must be derived from reference_dependency source units")

        occurrences = data.get("field_occurrences")
        if not isinstance(occurrences, list):
            errors.append("schema 1.1+ requires field_occurrences array")
            occurrences = []
        occurrence_ids: list[str] = []
        occurrence_fields: set[str] = set()
        for index, occurrence in enumerate(occurrences):
            if not isinstance(occurrence, dict):
                errors.append(f"field occurrence[{index}] must be an object")
                continue
            occurrence_id = occurrence.get("occurrence_id")
            if not occurrence_id:
                errors.append(f"field occurrence[{index}] lacks occurrence_id")
            else:
                occurrence_ids.append(occurrence_id)
            field_id = occurrence.get("field_id")
            if field_id not in field_ids:
                errors.append(f"field occurrence[{index}] references unknown field_id")
            else:
                occurrence_fields.add(field_id)
            if occurrence.get("function_id") not in function_ids:
                errors.append(f"field occurrence[{index}] references unknown function_id")
            if occurrence.get("surface") not in SURFACES or not occurrence.get("role") or not occurrence.get("name_as_written"):
                errors.append(f"field occurrence[{index}] lacks valid surface, role, or name_as_written")
            evidence = occurrence.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"field occurrence[{index}] must contain evidence")
            else:
                for proof_index, proof in enumerate(evidence):
                    if not isinstance(proof, dict) or proof.get("source_id") not in source_ids or not proof.get("locator") or not proof.get("quote"):
                        errors.append(f"field occurrence[{index}] evidence[{proof_index}] is invalid")
                        continue
                    if not check_primary_quote(source_text, primary_source_id, proof):
                        errors.append(f"field occurrence[{index}] quote not found in primary source: {proof['quote'][:60]}")
        repeated_occurrences = {value for value in occurrence_ids if occurrence_ids.count(value) > 1}
        if repeated_occurrences:
            errors.append(f"duplicate occurrence ids: {', '.join(sorted(repeated_occurrences))}")
        missing_occurrences = field_ids - occurrence_fields
        if missing_occurrences:
            errors.append(f"business fields without raw occurrences: {', '.join(sorted(missing_occurrences))}")

        for field in fields:
            if not isinstance(field, dict):
                continue
            field_id = field.get("field_id", "<missing>")
            provenance = field.get("attribute_provenance")
            if not isinstance(provenance, dict):
                errors.append(f"business field {field_id} lacks attribute_provenance")
                continue
            for attribute in ("business_object", "data_type", "required", "sensitivity"):
                if provenance.get(attribute) not in PROVENANCE:
                    errors.append(f"business field {field_id} has invalid provenance for {attribute}")

    bound_fields: set[str] = set()
    bound_atomics: set[str] = set()
    usages_by_field: dict[str, set[str]] = {field_id: set() for field_id in field_ids}
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            errors.append(f"field binding[{index}] must be an object")
            continue
        atomic_id, field_id = binding.get("atomic_id"), binding.get("field_id")
        if atomic_id not in atomic_ids:
            errors.append(f"field binding[{index}] references unknown atomic_id")
        else:
            bound_atomics.add(atomic_id)
        if field_id not in field_ids:
            errors.append(f"field binding[{index}] references unknown field_id")
        else:
            bound_fields.add(field_id)
        usages = binding.get("usages")
        if not isinstance(usages, list) or not usages or set(usages) - USAGES:
            errors.append(f"field binding[{index}] has invalid usages")
        elif field_id in usages_by_field:
            usages_by_field[field_id].update(usages)
        if binding.get("direction") not in DIRECTIONS:
            errors.append(f"field binding[{index}] has invalid direction")
        evidence = binding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"field binding[{index}] must contain evidence")
        else:
            for proof_index, proof in enumerate(evidence):
                if not isinstance(proof, dict) or proof.get("source_id") not in source_ids or not proof.get("locator") or not proof.get("quote"):
                    errors.append(f"field binding[{index}] evidence[{proof_index}] is invalid")
                    continue
                if not check_primary_quote(source_text, primary_source_id, proof):
                    errors.append(f"field binding[{index}] quote not found in primary source: {proof['quote'][:60]}")

    for field_id, field_usages in usages_by_field.items():
        if field_usages & {"input", "query", "validation"} and field_usages & {"display", "output"}:
            errors.append(f"business field {field_id} is bound as both input/query and display/output; split fields and add lineage")

    gaps = data.get("gaps")
    if not isinstance(gaps, dict):
        errors.append("gaps must be an object")
        gaps = {}
    for key in ("unbound_fields", "fieldless_atomic_functions", "unresolved_references", "conflicts"):
        if not isinstance(gaps.get(key), list):
            errors.append(f"gaps.{key} must be an array")

    actual_unbound = field_ids - bound_fields
    if set(gaps.get("unbound_fields", [])) != actual_unbound:
        errors.append("gaps.unbound_fields does not match actual unbound field ids")
    declared_fieldless = {x.get("atomic_id") for x in gaps.get("fieldless_atomic_functions", []) if isinstance(x, dict)}
    actual_fieldless = atomic_ids - bound_atomics
    if declared_fieldless != actual_fieldless:
        errors.append("gaps.fieldless_atomic_functions does not match actual fieldless atomic ids")

    parent_function_ids = {
        item.get("parent_function_id") for item in data.get("functions", [])
        if isinstance(item, dict) and item.get("parent_function_id")
    }
    for function_id in function_ids:
        if function_id not in parent_function_ids and not any(x.get("function_id") == function_id for x in atomics if isinstance(x, dict)):
            errors.append(f"function {function_id} has no atomic function")

    coverage = data.get("coverage")
    if not isinstance(coverage, dict):
        errors.append("coverage must be an object")
    else:
        expected = {"function_count": len(function_ids), "atomic_function_count": len(atomic_ids), "business_field_count": len(field_ids), "bound_field_count": len(bound_fields), "orphan_count": len(actual_unbound) + len(actual_fieldless)}
        for key, value in expected.items():
            if coverage.get(key) != value:
                errors.append(f"coverage.{key} must be {value}")
        percent = coverage.get("evidence_coverage_percent")
        if not isinstance(percent, (int, float)) or not 0 <= percent <= 100:
            errors.append("coverage.evidence_coverage_percent must be between 0 and 100")
        else:
            auditable = functions + atomics + fields + bindings
            evidenced = sum(1 for item in auditable if isinstance(item, dict) and item.get("evidence"))
            expected_percent = round(evidenced * 100 / len(auditable), 2) if auditable else 0
            if percent != expected_percent:
                errors.append(f"coverage.evidence_coverage_percent must be {expected_percent}")

    audit = data.get("audit")
    semantic_review = audit.get("semantic_review") if isinstance(audit, dict) else None
    if not isinstance(semantic_review, dict) or semantic_review.get("status") not in {"COMPLETED", "REVIEW_REQUIRED"}:
        errors.append("audit.semantic_review.status must be COMPLETED or REVIEW_REQUIRED")
    elif semantic_review.get("status") != "COMPLETED":
        warnings.append("semantic review is not completed; artifact is not downstream eligible")
    if isinstance(semantic_review, dict) and not isinstance(semantic_review.get("cross_context_candidates"), list):
        errors.append("audit.semantic_review.cross_context_candidates must be an array")

    if schema_version != "1.0":
        downstream_eligible = audit.get("downstream_eligible") if isinstance(audit, dict) else None
        if not isinstance(downstream_eligible, bool):
            errors.append("schema 1.1+ requires boolean audit.downstream_eligible")
        source_coverage = coverage.get("source_coverage") if isinstance(coverage, dict) else None
        if not isinstance(source_coverage, dict):
            errors.append("schema 1.1+ requires coverage.source_coverage")
        else:
            claim = source_coverage.get("claim")
            if claim not in {"full", "representative"}:
                errors.append("coverage.source_coverage.claim must be full or representative")
            review_required_count = source_coverage.get("review_required_units", 0) if not version_at_least(schema_version, "1.2") else source_coverage.get("review_required_units")
            counts = [source_coverage.get("relevant_units"), source_coverage.get("processed_units"), review_required_count, source_coverage.get("skipped_units"), source_coverage.get("unavailable_units")]
            if any(not isinstance(value, int) or value < 0 for value in counts):
                errors.append("source coverage counts must be non-negative integers")
            elif sum(counts[1:]) != counts[0]:
                errors.append("processed, review_required, skipped, and unavailable units must equal relevant_units")
            relevant_units = [unit for unit in source_units if isinstance(unit, dict) and unit.get("relevant")]
            actual_counts = {
                "relevant_units": len(relevant_units),
                "processed_units": sum(unit.get("status") == "processed" for unit in relevant_units),
                "review_required_units": sum(unit.get("status") == "review_required" for unit in relevant_units),
                "skipped_units": sum(unit.get("status") == "skipped" for unit in relevant_units),
                "unavailable_units": sum(unit.get("status") == "unavailable" for unit in relevant_units),
            }
            checked_counts = actual_counts if version_at_least(schema_version, "1.2") else {key: value for key, value in actual_counts.items() if key != "review_required_units"}
            for key, value in checked_counts.items():
                if source_coverage.get(key) != value:
                    errors.append(f"coverage.source_coverage.{key} must be {value} from source_units")
            uncovered = source_coverage.get("uncovered_ranges")
            if not isinstance(uncovered, list):
                errors.append("coverage.source_coverage.uncovered_ranges must be an array")
                uncovered = []
            if data.get("meta", {}).get("scope") != claim:
                errors.append("meta.scope must match coverage.source_coverage.claim")
            audit_verdict = audit.get("verdict") if isinstance(audit, dict) else None
            if claim == "representative" and audit_verdict == "PASS":
                errors.append("representative extraction cannot have PASS audit verdict")
            if claim == "full" and audit_verdict == "PASS" and (counts[2] or counts[3] or counts[4] or uncovered):
                errors.append("PASS full extraction cannot contain review_required, skipped, unavailable, or uncovered source units")
            eligible_state = (
                claim == "full"
                and audit_verdict == "PASS"
                and isinstance(semantic_review, dict)
                and semantic_review.get("status") == "COMPLETED"
                and not counts[2]
                and not counts[3]
                and not counts[4]
                and not uncovered
            )
            if downstream_eligible is True and not eligible_state:
                errors.append("audit.downstream_eligible cannot be true before full semantic acceptance")
            if eligible_state and downstream_eligible is not True:
                errors.append("accepted full mapping must set audit.downstream_eligible to true")

    if version_at_least(schema_version, "1.4"):
        for required in ("business_objects", "field_usages", "business_rules", "business_flows", "states"):
            if required not in data:
                errors.append(f"schema 1.4+ requires {required}")
        graph_nodes = coverage.get("graph_nodes") if isinstance(coverage, dict) else None
        if not isinstance(graph_nodes, dict) or coverage.get("graph_edges") != len(relations):
            errors.append("schema 1.4+ graph coverage does not match typed graph")
        elif test_cases and graph_nodes.get("test_cases") != len(test_cases):
            errors.append(f"coverage.graph_nodes.test_cases must be {len(test_cases)}")

    return errors, warnings


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.mapping.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("mapping root must be an object")
        source_text = args.source.read_text(encoding="utf-8") if args.source else None
        errors, warnings = validate(data, source_text)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        message = str(exc)
        emit_result({"verdict": "FAIL", "errors": [message], "warnings": [],
                     "diagnostics": [structured_diagnostic(message, "error")]}, args.format)
        return 2
    artifact_verdict = data.get("audit", {}).get("verdict") if isinstance(data.get("audit"), dict) else None
    if errors:
        verdict = "FAIL"
    elif artifact_verdict in {"PASS", "PARTIAL_PASS"}:
        verdict = artifact_verdict
    else:
        verdict = "STRUCTURAL_PASS"
    diagnostics = [structured_diagnostic(message, "error") for message in errors]
    diagnostics.extend(structured_diagnostic(message, "warning") for message in warnings)
    emit_result({"verdict": verdict, "structural_verdict": "PASS" if not errors else "FAIL",
                 "errors": errors, "warnings": warnings, "diagnostics": diagnostics}, args.format)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
