#!/usr/bin/env python3
"""Validate Test Case IR 1.0 against test_design_input 2.0."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

CASE_ID_RE = re.compile(r"^TC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*-\d{3,}$")
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_SEMANTICS = {"DETERMINISTIC", "HUMAN_JUDGMENT", "MIXED"}
VALID_CHANNELS = {"MANUAL", "API_AUTOMATION", "UI_AUTOMATION"}
VALID_FIXTURES = {"Static", "Dynamic", "Hybrid"}
VALID_PROVENANCE = {"REQUIREMENT_FACT", "TEST_DERIVATION"}
VALID_VALUE_CLASSES = {"VALID", "INVALID", "BOUNDARY", "STATE_SETUP", "REPRESENTATIVE"}
FORBIDDEN_KEYS = {
    "actual_result", "execution_result", "pass_fail", "allure", "screenshot",
    "log_path", "base_url", "endpoint", "locator", "xpath", "css_selector",
    "username", "password", "token", "secret",
}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strings(value: Any) -> bool:
    return isinstance(value, list) and all(_text(item) for item in value)


def _finding(code: str, severity: str, target: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "target": target, "message": message}


def _walk_forbidden(value: Any, path: str = "$") -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key.lower() in FORBIDDEN_KEYS:
                findings.append(_finding("FORBIDDEN_RUNTIME_FIELD", "REJECT", child_path, "测试用例不得包含运行时结果、凭据或实现绑定"))
            findings.extend(_walk_forbidden(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_walk_forbidden(child, f"{path}[{index}]"))
    return findings


def _refs(value: Any, valid: set[str], code: str, target: str) -> list[dict[str, str]]:
    if not _strings(value):
        return [_finding(code, "REJECT", target, "引用必须是字符串数组")]
    return [
        _finding(code, "REJECT", target, f"引用 {ref!r} 不在上游输入中")
        for ref in value if ref not in valid
    ]


def _collect_item_refs(value: Any) -> tuple[set[str], set[str], set[str]]:
    """Collect rule, evidence and field-usage IDs owned by one design item."""
    rule_ids: set[str] = set()
    evidence_ids: set[str] = set()
    field_ids: set[str] = set()

    def walk(node: Any, key: str = "") -> None:
        if isinstance(node, dict):
            for child_key, child in node.items():
                walk(child, child_key)
        elif isinstance(node, list):
            for child in node:
                walk(child, key)
        elif _text(node):
            if key == "rule_id" or key.endswith("_rule_ids") or key == "rule_ids":
                rule_ids.add(node)
            elif key == "evidence_id" or key.endswith("_evidence_ids") or key == "evidence_ids":
                evidence_ids.add(node)
            elif key == "field_usage_id" or key == "field_usage_ids":
                field_ids.add(node)

    walk(value)
    return rule_ids, evidence_ids, field_ids


def validate(packet: Any, source: Any, artifact_sha256: str, source_sha256: str) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    if not isinstance(packet, dict) or not isinstance(source, dict):
        findings.append(_finding("INVALID_ROOT", "REJECT", "$", "用例工件和测试设计输入都必须是对象"))
        return _result(findings, 0, artifact_sha256)

    meta = packet.get("meta", {})
    if not isinstance(meta, dict) or meta.get("schema_version") != "1.0" or meta.get("artifact_kind") != "test_case_ir":
        findings.append(_finding("INVALID_CASE_IR_META", "REJECT", "$.meta", "需要 test_case_ir 1.0 元数据"))
    if source.get("meta", {}).get("schema_version") != "2.0" or source.get("meta", {}).get("artifact_kind") != "test_design_input":
        findings.append(_finding("INVALID_TEST_DESIGN_INPUT", "REJECT", "input.meta", "需要 test_design_input 2.0"))
    if not source.get("acceptance", {}).get("downstream_eligible"):
        findings.append(_finding("INPUT_NOT_DOWNSTREAM_ELIGIBLE", "REJECT", "input.acceptance", "上游输入未放行测试用例生成"))

    snapshot = source.get("graph_snapshot_id")
    source_artifacts = packet.get("source_artifacts", {})
    if not _text(snapshot) or not isinstance(source_artifacts, dict) or source_artifacts.get("graph_snapshot_id") != snapshot:
        findings.append(_finding("GRAPH_SNAPSHOT_MISMATCH", "REJECT", "$.source_artifacts.graph_snapshot_id", "图谱快照与上游不一致"))
    if not isinstance(source_artifacts, dict) or source_artifacts.get("test_design_input_sha256") != source_sha256:
        findings.append(_finding("SOURCE_HASH_MISMATCH", "REJECT", "$.source_artifacts.test_design_input_sha256", "测试设计输入哈希与实际文件不一致"))

    items = source.get("items", [])
    item_index = {item.get("test_design_item_id"): item for item in items if isinstance(item, dict) and _text(item.get("test_design_item_id"))}
    rule_index = {item.get("rule_id"): item for item in source.get("rule_registry", []) if isinstance(item, dict) and _text(item.get("rule_id"))}
    rules = set(rule_index)
    evidence = {item.get("evidence_id") for item in source.get("evidence_registry", []) if isinstance(item, dict) and _text(item.get("evidence_id"))}

    scope = packet.get("generation_scope", {})
    scope_mode = scope.get("mode") if isinstance(scope, dict) else None
    if scope_mode not in {"FULL_READY_SCOPE", "SELECTED_SLICE"}:
        findings.append(_finding("INVALID_SCOPE_MODE", "REJECT", "$.generation_scope.mode", "mode 必须是 FULL_READY_SCOPE 或 SELECTED_SLICE"))
    selected = scope.get("selected_test_design_item_ids", []) if isinstance(scope, dict) else []
    if not _strings(selected) or not selected:
        findings.append(_finding("INVALID_GENERATION_SCOPE", "REJECT", "$.generation_scope", "必须选择至少一个测试设计条目"))
        selected = []
    for item_id in selected:
        if item_id not in item_index:
            findings.append(_finding("SELECTED_ITEM_NOT_IN_INPUT", "REJECT", "$.generation_scope", f"{item_id!r} 不在上游输入中"))
    all_ready_items = {
        item_id for item_id, item in item_index.items()
        if any(isinstance(gate, dict) and gate.get("status") == "READY" for gate in item.get("dimension_eligibility", {}).values())
    }
    if scope_mode == "FULL_READY_SCOPE" and set(selected) != all_ready_items:
        findings.append(_finding("FULL_READY_SCOPE_INCOMPLETE", "REJECT", "$.generation_scope.selected_test_design_item_ids", f"应选择 {sorted(all_ready_items)}，实际选择 {sorted(set(selected))}"))
    if scope.get("policy") != "READY_DIMENSIONS_ONLY":
        findings.append(_finding("INVALID_SCOPE_POLICY", "REJECT", "$.generation_scope.policy", "正式生成只能使用 READY_DIMENSIONS_ONLY"))

    ready_pairs: set[tuple[str, str]] = set()
    nonready_pairs: set[tuple[str, str, str]] = set()
    item_refs: dict[str, tuple[set[str], set[str], set[str]]] = {}
    required_rule_pairs: set[tuple[str, str]] = set()
    for item_id in selected:
        item = item_index.get(item_id, {})
        for dimension, gate in item.get("dimension_eligibility", {}).items():
            status = gate.get("status") if isinstance(gate, dict) else None
            if status == "READY":
                ready_pairs.add((item_id, dimension))
            else:
                nonready_pairs.add((item_id, dimension, status or "UNKNOWN"))
        item_rule_ids, item_evidence_ids, item_field_ids = _collect_item_refs(item)
        item_evidence_ids.update(
            evidence_id
            for rule_id in item_rule_ids & rules
            for evidence_id in rule_index[rule_id].get("evidence_ids", [])
            if evidence_id in evidence
        )
        item_refs[item_id] = (
            item_rule_ids & rules,
            item_evidence_ids & evidence,
            item_field_ids,
        )
        ready_dimensions = {pair[1] for pair in ready_pairs if pair[0] == item_id}
        operation_rules = set(item.get("operation_rule_ids", [])) & rules
        field_rules = {
            rule_id for field in item.get("field_usages", []) if isinstance(field, dict)
            for rule_id in field.get("rule_ids", []) if rule_id in rules
        }
        if "functional" in ready_dimensions:
            required_rule_pairs.update(
                (item_id, rule_id) for rule_id in operation_rules
                if rule_index[rule_id].get("kind") != "sorting"
            )
        if "field_validation" in ready_dimensions:
            required_rule_pairs.update(
                (item_id, rule_id) for rule_id in field_rules
                if rule_index[rule_id].get("kind") != "sorting"
            )
        if "sorting" in ready_dimensions:
            required_rule_pairs.update(
                (item_id, rule_id) for rule_id in (operation_rules | field_rules)
                if rule_index[rule_id].get("kind") == "sorting"
            )

    excluded = scope.get("excluded_dimensions", [])
    excluded_pairs = {
        (entry.get("test_design_item_id"), entry.get("dimension"), entry.get("status"))
        for entry in excluded if isinstance(entry, dict)
    } if isinstance(excluded, list) else set()
    for pair in sorted(nonready_pairs - excluded_pairs):
        findings.append(_finding("EXCLUDED_DIMENSION_NOT_RECORDED", "REJECT", "$.generation_scope.excluded_dimensions", f"未记录未生成维度 {pair}"))

    data_items = packet.get("data_requirements", [])
    if not isinstance(data_items, list):
        findings.append(_finding("INVALID_DATA_REQUIREMENTS", "REJECT", "$.data_requirements", "必须是数组"))
        data_items = []
    data_ids: set[str] = set()
    data_owner: dict[str, str] = {}
    for index, item in enumerate(data_items):
        target = f"$.data_requirements[{index}]"
        if not isinstance(item, dict) or not _text(item.get("data_requirement_id")):
            findings.append(_finding("INVALID_DATA_REQUIREMENT", "REJECT", target, "缺少 data_requirement_id"))
            continue
        data_ids.add(item["data_requirement_id"])
        owner_id = item.get("test_design_item_id")
        data_owner[item["data_requirement_id"]] = owner_id
        if owner_id not in selected:
            findings.append(_finding("DATA_ITEM_NOT_IN_SCOPE", "REJECT", target, "test_design_item_id 不属于生成范围"))
        owner_rules, _, owner_fields = item_refs.get(owner_id, (set(), set(), set()))
        if item.get("field_usage_id") not in owner_fields:
            findings.append(_finding("DATA_FIELD_USAGE_NOT_IN_SCOPE", "REJECT", target, "field_usage_id 不属于所选最小功能"))
        if item.get("value_class") not in VALID_VALUE_CLASSES:
            findings.append(_finding("INVALID_VALUE_CLASS", "REJECT", target, "value_class 无效"))
        if item.get("provenance_type") not in VALID_PROVENANCE:
            findings.append(_finding("INVALID_PROVENANCE", "REJECT", target, "只允许 REQUIREMENT_FACT 或 TEST_DERIVATION"))
        findings.extend(_refs(item.get("constraint_rule_ids", []), owner_rules, "DATA_RULE_NOT_IN_ITEM", target))

    cases = packet.get("cases", [])
    if not isinstance(cases, list) or not cases:
        findings.append(_finding("EMPTY_CASE_SET", "REJECT", "$.cases", "至少需要一个正式测试用例"))
        cases = []
    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict) and _text(case.get("case_id"))]
    for case_id, count in Counter(case_ids).items():
        if count > 1:
            findings.append(_finding("DUPLICATE_CASE_ID", "REJECT", case_id, f"case_id 出现 {count} 次"))

    covered_pairs: set[tuple[str, str]] = set()
    oracle_covered_rule_pairs: set[tuple[str, str]] = set()
    for index, case in enumerate(cases):
        target = f"$.cases[{index}]"
        if not isinstance(case, dict):
            findings.append(_finding("INVALID_CASE", "REJECT", target, "用例必须是对象"))
            continue
        case_id = case.get("case_id")
        if not _text(case_id) or not CASE_ID_RE.fullmatch(case_id):
            findings.append(_finding("INVALID_CASE_ID", "REJECT", target, "case_id 必须符合 TC-<scope>-NNN"))
        for key in ("title", "module", "function_name", "minimum_function", "objective", "test_level"):
            if not _text(case.get(key)):
                findings.append(_finding("MISSING_CASE_FIELD", "REJECT", f"{target}.{key}", f"缺少 {key}"))
        if case.get("priority") not in VALID_PRIORITIES:
            findings.append(_finding("INVALID_PRIORITY", "REJECT", target, "priority 必须是 P0-P3"))
        if not _strings(case.get("test_techniques")) or not case.get("test_techniques"):
            findings.append(_finding("EMPTY_TEST_TECHNIQUES", "REJECT", target, "至少声明一种测试技术"))

        trace = case.get("traceability", {})
        item_id = trace.get("test_design_item_id") if isinstance(trace, dict) else None
        item = item_index.get(item_id)
        if item_id not in selected or item is None:
            findings.append(_finding("CASE_ITEM_NOT_IN_SCOPE", "REJECT", f"{target}.traceability", "用例未绑定所选测试设计条目"))
            item = {}
        item_rule_ids, item_evidence_ids, item_field_ids = item_refs.get(item_id, (set(), set(), set()))
        if trace.get("graph_snapshot_id") != snapshot:
            findings.append(_finding("CASE_SNAPSHOT_MISMATCH", "REJECT", f"{target}.traceability", "用例图谱快照不一致"))
        if trace.get("atomic_id") != item.get("atomic_id"):
            findings.append(_finding("CASE_ATOMIC_MISMATCH", "REJECT", f"{target}.traceability", "atomic_id 与测试设计条目不一致"))
        findings.extend(_refs(trace.get("requirement_ids"), set(item.get("requirement_ids", [])), "CASE_REQUIREMENT_NOT_IN_ITEM", f"{target}.traceability.requirement_ids"))
        findings.extend(_refs(trace.get("rule_ids"), item_rule_ids, "CASE_RULE_NOT_IN_ITEM", f"{target}.traceability.rule_ids"))
        findings.extend(_refs(trace.get("field_usage_ids"), item_field_ids, "CASE_FIELD_USAGE_NOT_IN_ITEM", f"{target}.traceability.field_usage_ids"))
        findings.extend(_refs(trace.get("evidence_ids"), item_evidence_ids, "CASE_EVIDENCE_NOT_IN_ITEM", f"{target}.traceability.evidence_ids"))
        trace_rule_ids = set(trace.get("rule_ids", [])) if _strings(trace.get("rule_ids")) else set()
        trace_evidence_ids = set(trace.get("evidence_ids", [])) if _strings(trace.get("evidence_ids")) else set()

        dimensions = case.get("covered_dimensions")
        if not _strings(dimensions) or not dimensions:
            findings.append(_finding("EMPTY_COVERED_DIMENSIONS", "REJECT", target, "至少覆盖一个 READY 维度"))
        else:
            for dimension in dimensions:
                pair = (item_id, dimension)
                if pair not in ready_pairs:
                    findings.append(_finding("NON_READY_DIMENSION_COVERED", "REJECT", target, f"维度 {dimension!r} 未放行"))
                else:
                    covered_pairs.add(pair)

        execution = case.get("execution", {})
        if not isinstance(execution, dict) or execution.get("semantics") not in VALID_SEMANTICS:
            findings.append(_finding("INVALID_EXECUTION_SEMANTICS", "REJECT", f"{target}.execution", "执行语义无效"))
        channels = execution.get("candidate_channels", []) if isinstance(execution, dict) else []
        if not _strings(channels) or not channels or any(channel not in VALID_CHANNELS for channel in channels):
            findings.append(_finding("INVALID_CANDIDATE_CHANNELS", "REJECT", f"{target}.execution", "候选渠道无效"))
        if not isinstance(execution, dict) or execution.get("fixture_category") not in VALID_FIXTURES:
            findings.append(_finding("INVALID_FIXTURE_CATEGORY", "REJECT", f"{target}.execution", "fixture_category 无效"))

        preconditions = case.get("preconditions", [])
        if not isinstance(preconditions, list):
            findings.append(_finding("INVALID_PRECONDITIONS", "REJECT", target, "preconditions 必须是数组"))
        else:
            for pindex, precondition in enumerate(preconditions):
                ptarget = f"{target}.preconditions[{pindex}]"
                if not isinstance(precondition, dict) or not _text(precondition.get("description")) or precondition.get("provenance_type") not in VALID_PROVENANCE or not _strings(precondition.get("source_refs")) or not precondition.get("source_refs"):
                    findings.append(_finding("INVALID_PRECONDITION", "REJECT", ptarget, "前置条件需要描述、合法来源类型和来源引用"))
                elif any(ref not in (item_rule_ids | item_evidence_ids | item_field_ids) for ref in precondition.get("source_refs", [])):
                    findings.append(_finding("PRECONDITION_SOURCE_NOT_IN_ITEM", "REJECT", ptarget, "前置条件引用不属于当前最小功能"))

        findings.extend(_refs(case.get("data_requirement_refs", []), data_ids, "CASE_DATA_REQUIREMENT_NOT_FOUND", f"{target}.data_requirement_refs"))
        for ref in case.get("data_requirement_refs", []) if _strings(case.get("data_requirement_refs")) else []:
            if data_owner.get(ref) != item_id:
                findings.append(_finding("CASE_DATA_REQUIREMENT_CROSS_ITEM", "REJECT", f"{target}.data_requirement_refs", f"数据需求 {ref!r} 属于其他最小功能"))
        steps = case.get("steps")
        if not isinstance(steps, list) or not steps:
            findings.append(_finding("EMPTY_STEPS", "REJECT", target, "步骤不能为空"))
            continue
        if [step.get("step_no") for step in steps if isinstance(step, dict)] != list(range(1, len(steps) + 1)):
            findings.append(_finding("NON_SEQUENTIAL_STEPS", "REJECT", target, "step_no 必须从 1 连续编号"))
        for sindex, step in enumerate(steps):
            starget = f"{target}.steps[{sindex}]"
            if not isinstance(step, dict) or not _text(step.get("action")) or not _text(step.get("target")):
                findings.append(_finding("INVALID_STEP", "REJECT", starget, "步骤需要 action 和业务 target"))
                continue
            findings.extend(_refs(step.get("data_requirement_refs", []), data_ids, "STEP_DATA_REQUIREMENT_NOT_FOUND", f"{starget}.data_requirement_refs"))
            for ref in step.get("data_requirement_refs", []) if _strings(step.get("data_requirement_refs")) else []:
                if data_owner.get(ref) != item_id:
                    findings.append(_finding("STEP_DATA_REQUIREMENT_CROSS_ITEM", "REJECT", f"{starget}.data_requirement_refs", f"数据需求 {ref!r} 属于其他最小功能"))
            oracles = step.get("expected_results")
            if not isinstance(oracles, list) or not oracles:
                findings.append(_finding("EMPTY_STEP_ORACLES", "REJECT", starget, "每个步骤至少需要一个预期结果"))
                continue
            for oindex, oracle in enumerate(oracles):
                otarget = f"{starget}.expected_results[{oindex}]"
                if not isinstance(oracle, dict) or not _text(oracle.get("oracle_id")) or not _text(oracle.get("description")) or not isinstance(oracle.get("machine_checkable"), bool):
                    findings.append(_finding("INVALID_ORACLE", "REJECT", otarget, "Oracle 需要 ID、描述和 machine_checkable"))
                    continue
                rule_refs = oracle.get("oracle_rule_ids", [])
                evidence_refs = oracle.get("oracle_evidence_ids", [])
                if (not _strings(rule_refs)) or (not _strings(evidence_refs)) or not (rule_refs or evidence_refs):
                    findings.append(_finding("ORACLE_WITHOUT_SOURCE", "REJECT", otarget, "Oracle 必须绑定规则或证据"))
                else:
                    findings.extend(_refs(rule_refs, trace_rule_ids, "ORACLE_RULE_NOT_IN_CASE_TRACE", otarget))
                    findings.extend(_refs(evidence_refs, trace_evidence_ids, "ORACLE_EVIDENCE_NOT_IN_CASE_TRACE", otarget))
                    oracle_covered_rule_pairs.update((item_id, rule_id) for rule_id in rule_refs if rule_id in trace_rule_ids)

    for pair in sorted(ready_pairs - covered_pairs):
        findings.append(_finding("READY_DIMENSION_UNCOVERED", "REJECT", "$.coverage", f"READY 维度未覆盖：{pair}"))
    for pair in sorted(required_rule_pairs - oracle_covered_rule_pairs):
        findings.append(_finding("READY_RULE_WITHOUT_ORACLE", "REJECT", "$.coverage", f"READY 范围规则未被任何 Oracle 覆盖：{pair}"))

    coverage = packet.get("coverage", {})
    expected_counts = (len(item_index), len(set(selected)), len(item_index) - len(all_ready_items), len(ready_pairs), len(covered_pairs), len(cases))
    actual_counts = (
        coverage.get("input_item_count"), coverage.get("selected_item_count"), coverage.get("no_ready_item_count"),
        coverage.get("ready_dimension_count"), coverage.get("covered_ready_dimension_count"), coverage.get("case_count")
    ) if isinstance(coverage, dict) else (None, None, None, None, None, None)
    if actual_counts != expected_counts:
        findings.append(_finding("COVERAGE_COUNT_MISMATCH", "REJECT", "$.coverage", f"期望 {expected_counts}，实际 {actual_counts}"))

    acceptance = packet.get("acceptance", {})
    if not isinstance(acceptance, dict) or acceptance.get("verdict") != "PASS" or acceptance.get("publishable") is not True or acceptance.get("scope") != "READY_DIMENSIONS_ONLY":
        findings.append(_finding("INVALID_PUBLISH_CLAIM", "REJECT", "$.acceptance", "正式工件必须声明 PASS、publishable=true 和 READY_DIMENSIONS_ONLY"))

    findings.extend(_walk_forbidden(packet))
    return _result(findings, len(cases), artifact_sha256)


def _result(findings: list[dict[str, str]], case_count: int, artifact_sha256: str) -> dict[str, Any]:
    verdict = "REJECT" if any(item["severity"] == "REJECT" for item in findings) else "PASS"
    return {
        "validator": "test-case-generator/validate_case_ir.py",
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "artifact_sha256": artifact_sha256,
        "case_count": case_count,
        "finding_count": len(findings),
        "findings": findings,
        "verdict": verdict,
        "routing": "可投影 CSV 并交付下游" if verdict == "PASS" else "退回 test-case-generator，禁止发布",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        case_path = Path(args.cases)
        case_bytes = case_path.read_bytes()
        packet = json.loads(case_bytes)
        source_bytes = Path(args.input).read_bytes()
        source = json.loads(source_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": f"读取输入失败：{exc}"}, ensure_ascii=False), file=sys.stderr)
        return 3
    result = validate(
        packet,
        source,
        hashlib.sha256(case_bytes).hexdigest(),
        hashlib.sha256(source_bytes).hexdigest(),
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
