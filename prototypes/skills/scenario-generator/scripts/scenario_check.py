#!/usr/bin/env python3
"""对照 Testing IR 确定性校验场景图。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCENARIO_ID_RE = re.compile(r"^S-[A-Za-z0-9_]+-\d{3,}$")
VALID_FACETS = frozenset(
    {"normal", "abnormal", "boundary", "state_transition", "permission"}
)


def finding(code: str, severity: str, target: str, msg: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "target": target, "msg": msg}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _index_ir(ir: Any) -> tuple[dict[str, set[str]], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    index = {"requirements": set(), "rules": set(), "transitions": set()}
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
            target = f"{collection}[{position}]"
            if not isinstance(item, dict) or not _nonempty_string(item.get(id_key)):
                findings.append(
                    finding(
                        "INVALID_IR_ITEM",
                        "REJECT",
                        target,
                        f"{target} 需要字符串 {id_key}",
                    )
                )
                continue
            index[index_key].add(item[id_key])

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
        return index, findings
    for machine_position, machine in enumerate(machines):
        target = f"state_machines[{machine_position}]"
        if not isinstance(machine, dict) or not _nonempty_string(machine.get("sm_id")):
            findings.append(
                finding(
                    "INVALID_IR_STATE_MACHINE",
                    "REJECT",
                    target,
                    "状态机需要字符串 sm_id",
                )
            )
            continue
        transitions = machine.get("transitions", [])
        if not isinstance(transitions, list):
            findings.append(
                finding(
                    "INVALID_IR_TRANSITIONS",
                    "REJECT",
                    target,
                    "transitions 必须是数组",
                )
            )
            continue
        for transition_position, transition in enumerate(transitions):
            transition_target = f"{target}.transitions[{transition_position}]"
            if not isinstance(transition, dict) or not all(
                _nonempty_string(transition.get(key)) for key in ("from", "to")
            ):
                findings.append(
                    finding(
                        "INVALID_IR_TRANSITION",
                        "REJECT",
                        transition_target,
                        "transition 的 from/to 必须是非空字符串",
                    )
                )
                continue
            index["transitions"].add(
                f"{machine['sm_id']}:{transition['from']}->{transition['to']}"
            )
    return index, findings


def _check_one(
    scenario: Any, index: dict[str, set[str]], position: int
) -> list[dict[str, str]]:
    if not isinstance(scenario, dict):
        return [
            finding(
                "INVALID_SCENARIO",
                "REJECT",
                f"scenarios[{position}]",
                "scenario 必须是对象",
            )
        ]

    findings: list[dict[str, str]] = []
    scenario_id = scenario.get("scenario_id")
    target = scenario_id if _nonempty_string(scenario_id) else f"scenarios[{position}]"
    if not _nonempty_string(scenario_id):
        findings.append(
            finding(
                "MISSING_SCENARIO_ID", "REJECT", target, "缺少字符串 scenario_id"
            )
        )
    elif not SCENARIO_ID_RE.fullmatch(scenario_id):
        findings.append(
            finding(
                "MALFORMED_SCENARIO_ID",
                "REJECT",
                target,
                f"scenario_id {scenario_id!r} 格式不正确",
            )
        )

    for key, index_key, code in (
        ("req_id", "requirements", "REQUIREMENT_NOT_IN_IR"),
        ("rule_id", "rules", "RULE_NOT_IN_IR"),
    ):
        value = scenario.get(key)
        if not _nonempty_string(value):
            findings.append(
                finding("ORPHAN_SCENARIO", "REJECT", target, f"缺少字符串 {key}")
            )
        elif value not in index[index_key]:
            findings.append(
                finding(code, "REJECT", target, f"{key} {value!r} 不在 IR 中")
            )

    facet = scenario.get("facet")
    if not _nonempty_string(facet):
        findings.append(
            finding("MISSING_FACET", "REJECT", target, "缺少字符串 facet")
        )
    elif facet not in VALID_FACETS:
        findings.append(
            finding("INVALID_FACET", "REJECT", target, f"facet {facet!r} 无效")
        )
    elif facet == "state_transition":
        transition_ref = scenario.get("transition_ref")
        if (
            not _nonempty_string(transition_ref)
            or transition_ref not in index["transitions"]
        ):
            findings.append(
                finding(
                    "INVALID_TRANSITION_REF",
                    "REJECT",
                    target,
                    f"transition_ref {transition_ref!r} 不在 IR 中",
                )
            )
    return findings


def check_graph(scenarios: Any, ir: Any) -> dict[str, Any]:
    index, findings = _index_ir(ir)
    if not isinstance(scenarios, list):
        findings.append(
            finding(
                "INVALID_SCENARIO_COLLECTION",
                "REJECT",
                "scenarios",
                "scenarios 必须是数组",
            )
        )
        scenario_items: list[Any] = []
    else:
        scenario_items = scenarios
    if not scenario_items:
        findings.append(
            finding(
                "EMPTY_SCENARIO_SET",
                "REJECT",
                "scenarios",
                "至少需要一个场景",
            )
        )

    ids = [
        item.get("scenario_id")
        for item in scenario_items
        if isinstance(item, dict) and _nonempty_string(item.get("scenario_id"))
    ]
    for duplicate_id, count in sorted(Counter(ids).items()):
        if count > 1:
            findings.append(
                finding(
                    "DUPLICATE_SCENARIO_ID",
                    "REJECT",
                    duplicate_id,
                    f"出现 {count} 次",
                )
            )
    for position, item in enumerate(scenario_items):
        findings.extend(_check_one(item, index, position))

    covered = {
        item["transition_ref"]
        for item in scenario_items
        if isinstance(item, dict)
        and item.get("facet") == "state_transition"
        and _nonempty_string(item.get("transition_ref"))
        and item["transition_ref"] in index["transitions"]
    }
    for transition in sorted(index["transitions"] - covered):
        findings.append(
            finding(
                "TRANSITION_UNCOVERED",
                "REJECT",
                transition,
                f"transition {transition!r} 未被覆盖",
            )
        )

    facet_counts = Counter(
        item.get("facet")
        for item in scenario_items
        if isinstance(item, dict)
        and isinstance(item.get("facet"), str)
        and item.get("facet") in VALID_FACETS
    )
    for facet in sorted(VALID_FACETS - {"state_transition"}):
        if facet_counts[facet] == 0:
            findings.append(
                finding(
                    "EMPTY_FACET",
                    "REVIEW",
                    f"facet:{facet}",
                    f"没有任何 {facet!r} 场景",
                )
            )
    valid_facet_total = sum(facet_counts.values())
    if valid_facet_total and facet_counts.get("normal", 0) / valid_facet_total > 0.6:
        findings.append(
            finding(
                "FACET_IMBALANCE",
                "REVIEW",
                "facet:normal",
                f"{facet_counts.get('normal', 0)}/{valid_facet_total} 的场景为 "
                "'normal'（>60%）；面向缺陷的 facet 覆盖不足",
            )
        )

    has_reject = any(item["severity"] == "REJECT" for item in findings)
    has_review = any(item["severity"] == "REVIEW" for item in findings)
    verdict = "REJECT" if has_reject else "PASS_WITH_REVIEW" if has_review else "PASS"
    return {
        "skill": "08",
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_scenarios": len(scenario_items),
        "verdict": verdict,
        "facet_distribution": {
            facet: facet_counts.get(facet, 0) for facet in sorted(VALID_FACETS)
        },
        "transitions_in_ir": len(index["transitions"]),
        "transitions_covered": len(covered),
        "transitions_missing": sorted(index["transitions"] - covered),
        "total_findings": len(findings),
        "reject_findings": sum(item["severity"] == "REJECT" for item in findings),
        "review_findings": sum(item["severity"] == "REVIEW" for item in findings),
        "findings": findings,
        "routing": {
            "PASS": "就绪",
            "PASS_WITH_REVIEW": "就绪 + 标记待评审",
            "REJECT": "退回生成器",
        }[verdict],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", required=True)
    parser.add_argument("--ir", required=True)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        with Path(args.scenarios).open(encoding="utf-8") as handle:
            scenarios = json.load(handle)
        with Path(args.ir).open(encoding="utf-8") as handle:
            ir = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": f"读取输入失败：{exc}"}), file=sys.stderr)
        return 3
    if isinstance(scenarios, dict):
        scenarios = scenarios.get("scenarios", [scenarios])
    result = check_graph(scenarios, ir)
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
