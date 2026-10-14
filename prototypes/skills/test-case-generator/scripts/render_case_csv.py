#!/usr/bin/env python3
"""Render a validated Test Case IR as a human-readable UTF-8 CSV view."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HEADERS = [
    "case_id", "module", "function_name", "minimum_function", "title", "objective",
    "priority", "test_level", "test_techniques", "covered_dimensions",
    "execution_semantics", "candidate_channels", "fixture_category", "preconditions",
    "test_steps", "expected_results", "data_requirements", "traceability", "case_status",
]


def _join(values: Any) -> str:
    return "\n".join(str(value) for value in values) if isinstance(values, list) else ""


def _rows(packet: dict[str, Any]) -> list[dict[str, str]]:
    data_index = {
        item.get("data_requirement_id"): item
        for item in packet.get("data_requirements", []) if isinstance(item, dict)
    }
    rows: list[dict[str, str]] = []
    for case in packet.get("cases", []):
        trace = case.get("traceability", {})
        execution = case.get("execution", {})
        preconditions = [
            f"{item.get('precondition_id', '-')}: {item.get('description', '')} [{item.get('provenance_type', '')}]"
            for item in case.get("preconditions", [])
        ]
        steps: list[str] = []
        expected: list[str] = []
        for step in case.get("steps", []):
            number = step.get("step_no")
            refs = ",".join(step.get("data_requirement_refs", [])) or "无"
            steps.append(f"{number}. {step.get('action', '')}｜目标={step.get('target', '')}｜数据={refs}")
            for offset, oracle in enumerate(step.get("expected_results", []), 1):
                sources = oracle.get("oracle_rule_ids", []) + oracle.get("oracle_evidence_ids", [])
                expected.append(f"{number}.{offset} {oracle.get('description', '')}｜来源={','.join(sources)}｜机器可判定={'是' if oracle.get('machine_checkable') else '否'}")
        data_lines = []
        for ref in case.get("data_requirement_refs", []):
            item = data_index.get(ref, {})
            data_lines.append(f"{ref}: {item.get('business_name', '')}｜{item.get('value_class', '')}｜{item.get('purpose', '')}")
        trace_line = (
            f"snapshot={trace.get('graph_snapshot_id', '')}; item={trace.get('test_design_item_id', '')}; "
            f"atomic={trace.get('atomic_id', '')}; req={','.join(trace.get('requirement_ids', []))}; "
            f"rule={','.join(trace.get('rule_ids', []))}; field={','.join(trace.get('field_usage_ids', []))}; "
            f"evidence={','.join(trace.get('evidence_ids', []))}"
        )
        rows.append({
            "case_id": case.get("case_id", ""), "module": case.get("module", ""),
            "function_name": case.get("function_name", ""), "minimum_function": case.get("minimum_function", ""),
            "title": case.get("title", ""), "objective": case.get("objective", ""),
            "priority": case.get("priority", ""), "test_level": case.get("test_level", ""),
            "test_techniques": _join(case.get("test_techniques", [])),
            "covered_dimensions": _join(case.get("covered_dimensions", [])),
            "execution_semantics": execution.get("semantics", ""),
            "candidate_channels": _join(execution.get("candidate_channels", [])),
            "fixture_category": execution.get("fixture_category", ""),
            "preconditions": _join(preconditions), "test_steps": _join(steps),
            "expected_results": _join(expected), "data_requirements": _join(data_lines),
            "traceability": trace_line, "case_status": packet.get("acceptance", {}).get("verdict", ""),
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--validation", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        case_bytes = Path(args.cases).read_bytes()
        packet = json.loads(case_bytes)
        validation = json.loads(Path(args.validation).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"读取输入失败：{exc}", file=sys.stderr)
        return 3
    if validation.get("verdict") != "PASS" or validation.get("artifact_sha256") != hashlib.sha256(case_bytes).hexdigest():
        print("拒绝投影：校验未通过或 JSON 在校验后发生变化", file=sys.stderr)
        return 2
    with Path(args.out).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(_rows(packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())

