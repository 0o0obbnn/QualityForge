#!/usr/bin/env python3
"""对照场景与 Testing IR 确定性校验生成的测试用例。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

CASE_ID_RE = re.compile(r"^TC-[A-Za-z0-9_]+-\d{3,}$")
VALID_FIXTURE_CATEGORIES = frozenset({"Static", "Dynamic", "Hybrid"})


def finding(code: str, severity: str, target: str, msg: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "target": target, "msg": msg}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _index_ir(ir: Any) -> tuple[dict[str, Any], list[dict[str, str]]]:
    index: dict[str, Any] = {
        "requirements": set(),
        "rules": set(),
        "endpoints": set(),
        "state_machines": {},
        "entity_sm": {},
    }
    findings: list[dict[str, str]] = []
    if not isinstance(ir, dict):
        findings.append(
            finding("INVALID_IR_PACKET", "REJECT", "ir", "IR 必须是对象")
        )
        return index, findings

    for collection, id_key, index_key in (
        ("requirements", "req_id", "requirements"),
        ("business_rules", "rule_id", "rules"),
    ):
        items = ir.get(collection, [])
        if not isinstance(items, list):
            findings.append(
                finding(
                    "INVALID_IR_COLLECTION",
                    "REJECT",
                    collection,
                    f"{collection} 必须是数组",
                )
            )
            continue
        for position, item in enumerate(items):
            if not isinstance(item, dict) or not _nonempty_string(item.get(id_key)):
                findings.append(
                    finding(
                        "INVALID_IR_ITEM",
                        "REJECT",
                        f"{collection}[{position}]",
                        f"条目需要字符串 {id_key}",
                    )
                )
                continue
            index[index_key].add(item[id_key])

    contracts = ir.get("interface_contracts", [])
    if not isinstance(contracts, list):
        findings.append(
            finding(
                "INVALID_IR_COLLECTION",
                "REJECT",
                "interface_contracts",
                "interface_contracts 必须是数组",
            )
        )
    else:
        for position, contract in enumerate(contracts):
            if not isinstance(contract, dict) or not _nonempty_string(
                contract.get("endpoint")
            ):
                findings.append(
                    finding(
                        "INVALID_IR_CONTRACT",
                        "REJECT",
                        f"interface_contracts[{position}]",
                        "contract 需要字符串 endpoint",
                    )
                )
                continue
            index["endpoints"].add(contract["endpoint"])

    machines = ir.get("state_machines", [])
    if not isinstance(machines, list):
        findings.append(
            finding(
                "INVALID_IR_COLLECTION",
                "REJECT",
                "state_machines",
                "state_machines 必须是数组",
            )
        )
    else:
        for position, machine in enumerate(machines):
            target = f"state_machines[{position}]"
            if not isinstance(machine, dict) or not _nonempty_string(
                machine.get("sm_id")
            ):
                findings.append(
                    finding(
                        "INVALID_IR_STATE_MACHINE",
                        "REJECT",
                        target,
                        "状态机需要字符串 sm_id",
                    )
                )
                continue
            states = machine.get("states")
            if not isinstance(states, list) or not all(
                _nonempty_string(state) for state in states
            ):
                findings.append(
                    finding(
                        "INVALID_IR_STATES",
                        "REJECT",
                        target,
                        "states 必须是字符串数组",
                    )
                )
                continue
            index["state_machines"][machine["sm_id"]] = machine
            entity_id = machine.get("entity_id")
            if _nonempty_string(entity_id):
                index["entity_sm"][entity_id] = machine["sm_id"]
    return index, findings


def _index_scenarios(
    scenarios: Any,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    index: dict[str, dict[str, Any]] = {}
    if scenarios is None:
        return index, findings
    if not isinstance(scenarios, list):
        return index, [
            finding(
                "INVALID_SCENARIO_COLLECTION",
                "REJECT",
                "scenarios",
                "scenarios 必须是数组",
            )
        ]
    for position, scenario in enumerate(scenarios):
        target = f"scenarios[{position}]"
        if not isinstance(scenario, dict) or not all(
            _nonempty_string(scenario.get(key))
            for key in ("scenario_id", "req_id", "rule_id")
        ):
            findings.append(
                finding(
                    "INVALID_SCENARIO",
                    "REJECT",
                    target,
                    "scenario 需要字符串 scenario_id、req_id 和 rule_id",
                )
            )
            continue
        if scenario["scenario_id"] in index:
            findings.append(
                finding(
                    "DUPLICATE_SCENARIO_ID",
                    "REJECT",
                    scenario["scenario_id"],
                    "scenario_id 重复",
                )
            )
            continue
        index[scenario["scenario_id"]] = scenario
    return index, findings


def _resolve_state_machine(
    case: dict[str, Any], index: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    machine_id = case.get("state_machine_id")
    if machine_id is not None:
        if (
            not _nonempty_string(machine_id)
            or machine_id not in index["state_machines"]
        ):
            return None, "STATE_MACHINE_NOT_IN_IR"
        return index["state_machines"][machine_id], None
    entity_id = case.get("entity_id")
    if _nonempty_string(entity_id) and entity_id in index["entity_sm"]:
        return index["state_machines"][index["entity_sm"][entity_id]], None
    return None, None


def _check_one(
    case: Any,
    ir_index: dict[str, Any],
    scenario_index: dict[str, dict[str, Any]],
    position: int,
) -> list[dict[str, str]]:
    if not isinstance(case, dict):
        return [
            finding(
                "INVALID_CASE", "REJECT", f"cases[{position}]", "case 必须是对象"
            )
        ]

    findings: list[dict[str, str]] = []
    case_id = case.get("case_id")
    target = case_id if _nonempty_string(case_id) else f"cases[{position}]"
    if not _nonempty_string(case_id):
        findings.append(
            finding("MISSING_CASE_ID", "REJECT", target, "缺少字符串 case_id")
        )
    elif not CASE_ID_RE.fullmatch(case_id):
        findings.append(
            finding(
                "MALFORMED_CASE_ID", "REJECT", target, f"case_id {case_id!r} 格式不正确"
            )
        )

    bindings: dict[str, Any] = {}
    for key in ("req_id", "rule_id", "scenario_id"):
        value = case.get(key)
        bindings[key] = value
        if not _nonempty_string(value):
            findings.append(
                finding("ORPHAN_CASE", "REJECT", target, f"缺少字符串 {key}")
            )
    if (
        _nonempty_string(bindings["req_id"])
        and bindings["req_id"] not in ir_index["requirements"]
    ):
        findings.append(
            finding(
                "REQUIREMENT_NOT_IN_IR",
                "REJECT",
                target,
                f"req_id {bindings['req_id']!r} 不在 IR 中",
            )
        )
    if (
        _nonempty_string(bindings["rule_id"])
        and bindings["rule_id"] not in ir_index["rules"]
    ):
        findings.append(
            finding(
                "RULE_NOT_IN_IR",
                "REJECT",
                target,
                f"rule_id {bindings['rule_id']!r} 不在 IR 中",
            )
        )

    scenario = (
        scenario_index.get(bindings["scenario_id"])
        if _nonempty_string(bindings["scenario_id"])
        else None
    )
    if _nonempty_string(bindings["scenario_id"]) and scenario is None:
        findings.append(
            finding(
                "SCENARIO_NOT_IN_GRAPH",
                "REJECT",
                target,
                f"scenario_id {bindings['scenario_id']!r} 不在场景图中",
            )
        )
    elif scenario is not None:
        mismatches = [
            key
            for key in ("req_id", "rule_id")
            if _nonempty_string(scenario.get(key))
            and case.get(key) != scenario.get(key)
        ]
        if mismatches:
            findings.append(
                finding(
                    "CASE_SCENARIO_BINDING_MISMATCH",
                    "REJECT",
                    target,
                    f"case 与 scenario 在 {', '.join(mismatches)} 上不一致",
                )
            )

    category = case.get("fixture_category")
    if not _nonempty_string(category):
        findings.append(
            finding(
                "MISSING_FIXTURE_CATEGORY", "REJECT", target, "缺少 fixture_category"
            )
        )
    elif category not in VALID_FIXTURE_CATEGORIES:
        findings.append(
            finding(
                "INVALID_FIXTURE_CATEGORY",
                "REJECT",
                target,
                f"fixture_category {category!r} 无效",
            )
        )

    steps = case.get("steps")
    if not isinstance(steps, list) or not steps:
        findings.append(
            finding(
                "EMPTY_CASE_STEPS", "REJECT", target, "steps 必须是非空数组"
            )
        )
    else:
        for step_position, step in enumerate(steps):
            step_target = f"{target}.steps[{step_position}]"
            if not isinstance(step, dict) or not _nonempty_string(step.get("action")):
                findings.append(
                    finding(
                        "INVALID_CASE_STEP",
                        "REJECT",
                        step_target,
                        "step 需要字符串 action",
                    )
                )
                continue
            endpoint = step.get("endpoint")
            if endpoint is not None and (
                not _nonempty_string(endpoint) or endpoint not in ir_index["endpoints"]
            ):
                findings.append(
                    finding(
                        "STEP_ENDPOINT_NOT_IN_IR",
                        "REJECT",
                        step_target,
                        f"endpoint {endpoint!r} 不在 IR 中",
                    )
                )

    expected_results = case.get("expected_results")
    if not isinstance(expected_results, list) or not expected_results:
        findings.append(
            finding(
                "EMPTY_EXPECTED_RESULTS",
                "REJECT",
                target,
                "expected_results 必须是非空数组",
            )
        )
        expected_items: list[Any] = []
    else:
        expected_items = expected_results

    machine, machine_error = _resolve_state_machine(case, ir_index)
    if machine_error:
        findings.append(
            finding(
                machine_error,
                "REJECT",
                target,
                f"state_machine_id {case.get('state_machine_id')!r} 不在 IR 中",
            )
        )
    valid_states = set(machine["states"]) if machine else set()
    for result_position, expected in enumerate(expected_items):
        result_target = f"{target}.expected_results[{result_position}]"
        if not isinstance(expected, dict) or not expected:
            findings.append(
                finding(
                    "INVALID_EXPECTED_RESULT",
                    "REJECT",
                    result_target,
                    "expected result 必须是非空对象",
                )
            )
            continue
        state = expected.get("state")
        if state is not None:
            if not _nonempty_string(state):
                findings.append(
                    finding(
                        "EXPECTED_STATE_INVALID",
                        "REJECT",
                        result_target,
                        "state 必须是非空字符串",
                    )
                )
            elif valid_states and state not in valid_states:
                findings.append(
                    finding(
                        "EXPECTED_STATE_INVALID",
                        "REJECT",
                        result_target,
                        f"state {state!r} 无效",
                    )
                )
            elif not valid_states and machine_error is None:
                findings.append(
                    finding(
                        "STATE_CHECK_INDETERMINATE",
                        "REVIEW",
                        result_target,
                        f"无法校验 state {state!r}",
                    )
                )
        endpoint = expected.get("endpoint")
        if endpoint is not None and (
            not _nonempty_string(endpoint) or endpoint not in ir_index["endpoints"]
        ):
            findings.append(
                finding(
                    "EXPECTED_ENDPOINT_NOT_IN_IR",
                    "REJECT",
                    result_target,
                    f"endpoint {endpoint!r} 不在 IR 中",
                )
            )
    return findings


def _covered_operations(case_items: list[Any]) -> set[tuple[str | None, str]]:
    covered: set[tuple[str | None, str]] = set()
    for case in case_items:
        if not isinstance(case, dict):
            continue
        steps = case.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            endpoint = step.get("endpoint")
            if not _nonempty_string(endpoint):
                continue
            method = step.get("method")
            covered.add(
                (
                    method.strip().upper() if _nonempty_string(method) else None,
                    endpoint.strip(),
                )
            )
    return covered


def _check_contract_coverage(case_items: list[Any], ir: Any) -> list[dict[str, str]]:
    """反向覆盖：IR 中的每个 interface contract 都必须被某个 case step 执行到。

    结构类检查只校验被引用的 endpoint 是否存在于 IR；
    没有这项检查，整套用例可能静默丢弃整个 operation 却照样通过。
    未显式声明 method 的 step 视为覆盖该 endpoint 的所有已声明 method。
    """
    findings: list[dict[str, str]] = []
    contracts = ir.get("interface_contracts") if isinstance(ir, dict) else None
    if not isinstance(contracts, list):
        return findings
    covered = _covered_operations(case_items)
    for contract in contracts:
        if not isinstance(contract, dict) or not _nonempty_string(
            contract.get("endpoint")
        ):
            continue
        endpoint = contract["endpoint"].strip()
        method = contract.get("method")
        key = (
            method.strip().upper() if _nonempty_string(method) else None,
            endpoint,
        )
        if key in covered or (None, endpoint) in covered:
            continue
        findings.append(
            finding(
                "CONTRACT_UNCOVERED",
                "REJECT",
                f"interface_contracts:{contract.get('contract_id', '<no id>')}",
                f"{key[0] or 'ANY'} {endpoint} 没有任何 case step 覆盖",
            )
        )
    return findings


VAGUE_ASSERTION_RE = re.compile(
    r"([A-Z][A-Z_]{2,}\s*类\b|大约|大概|左右|类似|某种|roughly|approximately"
    r"|kind of|or similar|etc\.)",
    re.IGNORECASE,
)
PURELY_NEGATIVE_RE = re.compile(
    r"^(status|code|http(\s*code)?)\s*!=\s*[\"']?\d{3}[\"']?$|^非\s*2xx$",
    re.IGNORECASE,
)


def _check_assertion_strength(case_items: list[Any]) -> list[dict[str, str]]:
    """标记含糊或纯否定的断言——它们在错误码出现时也可能通过。"""
    findings: list[dict[str, str]] = []
    for case in case_items:
        if not isinstance(case, dict):
            continue
        expected = case.get("expected_results")
        if not isinstance(expected, list):
            continue
        for position, result in enumerate(expected):
            if not isinstance(result, dict):
                continue
            assertion = result.get("assertion")
            if not isinstance(assertion, str) or not assertion.strip():
                continue
            target = f"{case.get('case_id', '<no id>')}.expected_results[{position}]"
            if VAGUE_ASSERTION_RE.search(assertion):
                findings.append(
                    finding(
                        "WEAK_ASSERTION",
                        "REVIEW",
                        target,
                        f"断言措辞含糊：{assertion.strip()[:60]!r}",
                    )
                )
            elif PURELY_NEGATIVE_RE.fullmatch(assertion.strip()):
                findings.append(
                    finding(
                        "WEAK_ASSERTION",
                        "REVIEW",
                        target,
                        "纯否定断言只声明了不期望什么",
                    )
                )
    return findings


BOUNDARY_CONSTRAINT_RE = re.compile(
    r"(<=|>=|<|>)|(\bmin(?:imum)?\b|\bmax(?:imum)?\b|length|\d\s*\.\.\s*\d"
    r"|\d+\s*per\s*\d+|\d+h\b)",
    re.IGNORECASE,
)


def _check_boundary_constraints(case_items: list[Any], ir: Any) -> list[dict[str, str]]:
    """每条带边界特征的 IR constraint 都必须被某个 case 在
    `constraint_refs` 中点名引用。"""
    findings: list[dict[str, str]] = []
    constraints = ir.get("constraints") if isinstance(ir, dict) else None
    if not isinstance(constraints, list):
        return findings
    boundary: list[dict[str, Any]] = []
    for constraint in constraints:
        if not isinstance(constraint, dict):
            continue
        expression = constraint.get("expression")
        if (
            isinstance(expression, str)
            and expression.strip()
            and BOUNDARY_CONSTRAINT_RE.search(expression)
        ):
            boundary.append(constraint)
    if not boundary:
        return findings
    referenced: set[str] = set()
    for case in case_items:
        if not isinstance(case, dict):
            continue
        refs = case.get("constraint_refs")
        if isinstance(refs, list):
            referenced.update(ref for ref in refs if isinstance(ref, str))
    for constraint in boundary:
        cid = constraint.get("constraint_id", "<no id>")
        if cid not in referenced:
            findings.append(
                finding(
                    "BOUNDARY_CONSTRAINT_UNCOVERED",
                    "REVIEW",
                    f"constraints:{cid}",
                    f"边界表达式 {constraint.get('expression', '')!r} "
                    "未被任何 case 的 constraint_refs 引用",
                )
            )
    return findings


def check_cases(cases: Any, ir: Any, scenarios: Any = None) -> dict[str, Any]:
    ir_index, findings = _index_ir(ir)
    scenario_index, scenario_findings = _index_scenarios(scenarios)
    findings.extend(scenario_findings)
    if not isinstance(cases, list):
        findings.append(
            finding(
                "INVALID_CASE_COLLECTION", "REJECT", "cases", "cases 必须是数组"
            )
        )
        case_items: list[Any] = []
    else:
        case_items = cases
    if not case_items:
        findings.append(
            finding(
                "EMPTY_CASE_SET",
                "REJECT",
                "cases",
                "至少需要一个测试用例",
            )
        )

    ids = [
        item.get("case_id")
        for item in case_items
        if isinstance(item, dict) and _nonempty_string(item.get("case_id"))
    ]
    for duplicate_id, count in sorted(Counter(ids).items()):
        if count > 1:
            findings.append(
                finding(
                    "DUPLICATE_CASE_ID",
                    "REJECT",
                    duplicate_id,
                    f"出现 {count} 次",
                )
            )

    conformant = 0
    for position, case in enumerate(case_items):
        item_findings = _check_one(case, ir_index, scenario_index, position)
        findings.extend(item_findings)
        if not item_findings:
            conformant += 1
    findings.extend(_check_contract_coverage(case_items, ir))
    findings.extend(_check_assertion_strength(case_items))
    findings.extend(_check_boundary_constraints(case_items, ir))
    has_reject = any(item["severity"] == "REJECT" for item in findings)
    has_review = any(item["severity"] == "REVIEW" for item in findings)
    verdict = "REJECT" if has_reject else "PASS_WITH_REVIEW" if has_review else "PASS"
    return {
        "skill": "09",
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_cases": len(case_items),
        "conformant_cases": conformant,
        "total_findings": len(findings),
        "findings": findings,
        "verdict": verdict,
        "routing": {
            "PASS": "可供消费",
            "PASS_WITH_REVIEW": "可供消费 + 标记待评审",
            "REJECT": "退回生成器",
        }[verdict],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--ir", required=True)
    parser.add_argument("--scenarios")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        with Path(args.cases).open(encoding="utf-8") as handle:
            cases = json.load(handle)
        with Path(args.ir).open(encoding="utf-8") as handle:
            ir = json.load(handle)
        if args.scenarios:
            with Path(args.scenarios).open(encoding="utf-8") as handle:
                scenarios = json.load(handle)
        else:
            scenarios = None
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": f"读取输入失败：{exc}"}), file=sys.stderr)
        return 3
    if isinstance(cases, dict):
        cases = cases.get("cases", [cases])
    if isinstance(scenarios, dict):
        scenarios = scenarios.get("scenarios", [scenarios])
    result = check_cases(cases, ir, scenarios)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    try:
        if args.out:
            Path(args.out).write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
    except OSError as exc:
        print(json.dumps({"error": f"写入输出失败：{exc}"}), file=sys.stderr)
        return 3
    return {"PASS": 0, "PASS_WITH_REVIEW": 1, "REJECT": 2}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
