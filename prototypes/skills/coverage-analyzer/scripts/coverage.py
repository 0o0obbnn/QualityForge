#!/usr/bin/env python3
"""
覆盖率分析器——四维覆盖 + gate 裁定。

维度：rule、scenario、state、assertion（有效覆盖）。
每条必需的 assertion 在通过验证之前都留在分母中。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import sys
from collections import Counter

DEFAULT_THRESHOLDS = {"rule": 1.0, "scenario": 0.9, "state": 0.9, "assertion": 0.85}


def _pct(num, denom):
    if denom <= 0:
        return 0.0
    return round(num / denom, 3)


def dim_rule(snapshot):
    ir_rules = {
        r["rule_id"]
        for r in snapshot.get("ir_business_rules", [])
        if isinstance(r, dict) and r.get("rule_id")
    }
    bound = {
        c["rule_id"]
        for c in snapshot.get("cases", [])
        if isinstance(c, dict) and c.get("rule_id")
    }
    covered = ir_rules & bound
    return {
        "dimension": "rule",
        "numerator": len(covered),
        "denominator": len(ir_rules),
        "coverage": _pct(len(covered), len(ir_rules)),
        "missing": sorted(ir_rules - bound),
    }


def dim_scenario(snapshot):
    scenarios = {
        s["scenario_id"]
        for s in snapshot.get("scenarios", [])
        if isinstance(s, dict) and s.get("scenario_id")
    }
    realised = {
        c["scenario_id"]
        for c in snapshot.get("cases", [])
        if isinstance(c, dict) and c.get("scenario_id")
    }
    covered = scenarios & realised
    return {
        "dimension": "scenario",
        "numerator": len(covered),
        "denominator": len(scenarios),
        "coverage": _pct(len(covered), len(scenarios)),
        "missing": sorted(scenarios - realised),
    }


def dim_state(snapshot):
    all_trans = set()
    for sm in snapshot.get("ir_state_machines", []):
        if not isinstance(sm, dict) or not sm.get("sm_id"):
            continue
        for tr in sm.get("transitions", []):
            if isinstance(tr, dict) and tr.get("from") and tr.get("to"):
                all_trans.add(f"{sm['sm_id']}:{tr['from']}->{tr['to']}")
    raw_exercised = snapshot.get("exercised_transitions", [])
    exercised = (
        {item for item in raw_exercised if isinstance(item, str)}
        if isinstance(raw_exercised, list)
        else set()
    )
    covered = all_trans & exercised
    return {
        "dimension": "state",
        "numerator": len(covered),
        "denominator": len(all_trans),
        "coverage": _pct(len(covered), len(all_trans)),
        "missing": sorted(all_trans - exercised),
    }


def dim_assertion(snapshot):
    raw_verdicts = snapshot.get("assertion_verdicts", []) or []
    invalid_verdict_collection = not isinstance(raw_verdicts, list)
    if invalid_verdict_collection:
        raw_verdicts = []
    verdicts = [item for item in raw_verdicts if isinstance(item, dict)]
    malformed_count = len(raw_verdicts) - len(verdicts)
    verdict_counts = Counter(
        item.get("assertion_id") for item in verdicts if item.get("assertion_id")
    )
    duplicate_ids = sorted(
        assertion_id for assertion_id, count in verdict_counts.items() if count > 1
    )

    if "assertions" in snapshot:
        assertions = snapshot.get("assertions", []) or []
        invalid_assertion_collection = not isinstance(assertions, list)
        if invalid_assertion_collection:
            assertions = []
        required_counts = Counter(
            item.get("assertion_id")
            for item in assertions
            if isinstance(item, dict) and item.get("assertion_id")
        )
        required_ids = {
            item.get("assertion_id")
            for item in assertions
            if isinstance(item, dict) and item.get("assertion_id")
        }
        duplicate_required_ids = sorted(
            assertion_id for assertion_id, count in required_counts.items() if count > 1
        )
        malformed_assertion_count = sum(
            1
            for item in assertions
            if not isinstance(item, dict) or not item.get("assertion_id")
        )
        unexpected_ids = sorted(set(verdict_counts) - required_ids)
    else:
        invalid_assertion_collection = False
        required_ids = set(verdict_counts)
        duplicate_required_ids = []
        malformed_assertion_count = 0
        unexpected_ids = []

    verdict_by_id = {
        item["assertion_id"]: item.get("skill11_verdict")
        for item in verdicts
        if item.get("assertion_id") in required_ids
        and verdict_counts[item["assertion_id"]] == 1
    }
    passed = {
        assertion_id
        for assertion_id, verdict in verdict_by_id.items()
        if verdict == "PASS"
    }
    repaired = {
        assertion_id
        for assertion_id, verdict in verdict_by_id.items()
        if verdict == "REPAIR"
    }
    rejected = {
        assertion_id
        for assertion_id, verdict in verdict_by_id.items()
        if verdict == "REJECT"
    }
    unverified_ids = required_ids - passed - repaired - rejected
    missing_required = required_ids - set(verdict_counts)
    num = len(passed)
    unverified_count = len(unverified_ids)
    denom = len(required_ids)
    evidence_errors = (
        malformed_count
        + malformed_assertion_count
        + len(duplicate_ids)
        + len(duplicate_required_ids)
        + len(unexpected_ids)
        + int(invalid_verdict_collection)
        + int(invalid_assertion_collection)
    )
    return {
        "dimension": "assertion",
        "numerator": num,
        "denominator": denom,
        "coverage": _pct(num, denom),
        "passed": num,
        "repair": len(repaired),
        "reject": len(rejected),
        "unverified": unverified_count,
        "missing_verdict_ids": sorted(missing_required),
        "duplicate_verdict_ids": duplicate_ids,
        "duplicate_required_ids": duplicate_required_ids,
        "unexpected_verdict_ids": unexpected_ids,
        "malformed_verdict_count": malformed_count + int(invalid_verdict_collection),
        "malformed_assertion_count": malformed_assertion_count
        + int(invalid_assertion_collection),
        "evidence_errors": evidence_errors,
    }


def analyze(snapshot, strategy):
    input_errors = []
    if not isinstance(snapshot, dict):
        input_errors.append("snapshot 根节点必须是对象")
        snapshot = {}
    if not isinstance(strategy, dict):
        input_errors.append("strategy 根节点必须是对象")
        strategy = {}
    object_collections = {
        "ir_business_rules",
        "cases",
        "scenarios",
        "ir_state_machines",
        "assertions",
        "assertion_verdicts",
    }
    for key in sorted(object_collections):
        if key not in snapshot:
            continue
        value = snapshot[key]
        if not isinstance(value, list):
            input_errors.append(f"snapshot.{key} 必须是数组")
        elif any(not isinstance(item, dict) for item in value):
            input_errors.append(f"snapshot.{key} 的元素必须是对象")
    if "exercised_transitions" in snapshot:
        value = snapshot["exercised_transitions"]
        if not isinstance(value, list) or any(
            not isinstance(item, str) for item in value
        ):
            input_errors.append(
                "snapshot.exercised_transitions 必须是字符串数组"
            )
    thresholds = dict(DEFAULT_THRESHOLDS)
    raw_thresholds = strategy.get("gate_thresholds", {}) or {}
    invalid_thresholds = []
    if isinstance(raw_thresholds, dict):
        for name, value in raw_thresholds.items():
            if (
                name not in DEFAULT_THRESHOLDS
                or isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                invalid_thresholds.append(name)
            else:
                thresholds[name] = value
    else:
        invalid_thresholds.append("gate_thresholds")
    raw_not_applicable = strategy.get("not_applicable_dimensions", []) or []
    invalid_not_applicable = (
        not isinstance(raw_not_applicable, list)
        or any(
            item not in DEFAULT_THRESHOLDS
            for item in raw_not_applicable
            if isinstance(item, str)
        )
        or any(not isinstance(item, str) for item in raw_not_applicable)
    )
    not_applicable = (
        {
            item
            for item in raw_not_applicable
            if isinstance(item, str) and item in DEFAULT_THRESHOLDS
        }
        if isinstance(raw_not_applicable, list)
        else set()
    )
    dims = {
        "rule": dim_rule(snapshot),
        "scenario": dim_scenario(snapshot),
        "state": dim_state(snapshot),
        "assertion": dim_assertion(snapshot),
    }
    failures = []
    for name, d in dims.items():
        thr = thresholds.get(name, DEFAULT_THRESHOLDS[name])
        d["threshold"] = thr
        blocking_rejections = name == "assertion" and d.get("reject", 0) > 0
        evidence_errors = name == "assertion" and d.get("evidence_errors", 0) > 0
        configuration_error = name in invalid_thresholds
        empty_denominator = d["denominator"] == 0
        declared_not_applicable = (
            empty_denominator
            and name in not_applicable
            and not evidence_errors
            and not input_errors
        )
        if declared_not_applicable:
            d["verdict"] = "NOT_APPLICABLE"
        else:
            meets_threshold = (
                not empty_denominator and d["numerator"] / d["denominator"] >= thr
            )
            d["verdict"] = (
                "PASS"
                if (
                    meets_threshold
                    and not blocking_rejections
                    and not evidence_errors
                    and not configuration_error
                )
                else "FAIL"
            )
        if d["verdict"] == "FAIL":
            failures.append(
                {
                    "dimension": name,
                    "coverage": d["coverage"],
                    "threshold": thr,
                    "gap": max(0.0, round(thr - d["coverage"], 3)),
                    "missing_count": len(d.get("missing", [])),
                    "missing_sample": d.get("missing", [])[:10],
                    "blocking_rejections": d.get("reject", 0)
                    if blocking_rejections
                    else 0,
                    "evidence_errors": d.get("evidence_errors", 0),
                    "configuration_error": configuration_error,
                    "empty_denominator": empty_denominator,
                }
            )
    if invalid_not_applicable:
        failures.append(
            {
                "dimension": "configuration",
                "code": "INVALID_NOT_APPLICABLE_DIMENSIONS",
                "msg": "not_applicable_dimensions 必须是数组",
            }
        )
    if invalid_thresholds:
        failures.append(
            {
                "dimension": "configuration",
                "code": "INVALID_GATE_THRESHOLDS",
                "targets": sorted(str(item) for item in invalid_thresholds),
                "msg": "阈值名称与取值必须是已知的 [0,1] 内有限数字",
            }
        )
    if input_errors:
        failures.append(
            {
                "dimension": "configuration",
                "code": "INVALID_SNAPSHOT",
                "messages": input_errors,
            }
        )
    overall = "GATE_FAILURE" if failures else "GATE_PASS"
    return {
        "skill": "12",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "overall_verdict": overall,
        "dimensions": dims,
        "thresholds_used": thresholds,
        "gate_failures": failures,
        "routing": {
            "GATE_PASS": "Phase 可关闭",
            "GATE_FAILURE": "Phase 被阻断；转人工复核",
        }[overall],
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", required=True)
    p.add_argument("--strategy", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        with open(args.snapshot, encoding="utf-8") as handle:
            snapshot = json.load(handle)
        with open(args.strategy, encoding="utf-8") as handle:
            strategy = json.load(handle)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr)
        return 3
    result = analyze(snapshot, strategy)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    try:
        if args.out:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(out)
        else:
            print(out)
    except OSError as e:
        print(json.dumps({"error": f"输出错误：{e}"}), file=sys.stderr)
        return 3
    return 2 if result["overall_verdict"] == "GATE_FAILURE" else 0


if __name__ == "__main__":
    sys.exit(main())
