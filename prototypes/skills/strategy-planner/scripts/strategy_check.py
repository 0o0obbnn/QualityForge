#!/usr/bin/env python3
"""确定性 Strategy Contract 校验器。"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import sys
from collections import Counter


CORE_LAYERS = frozenset(
    {"database", "db", "internal_service", "repository", "data_layer"}
)
VALID_RISK_LEVELS = frozenset({"low", "medium", "high", "critical"})
VALID_DISPOSITIONS = frozenset({"IN_SCOPE", "OUT_OF_SCOPE"})
PYRAMID_KEYS = ("unit", "integration", "e2e")


def finding(check, code, severity, target, msg):
    return {
        "check": check,
        "code": code,
        "severity": severity,
        "target": target,
        "msg": msg,
    }


def _nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def _object_list(strategy, key, findings, *, required=False):
    value = strategy[key] if key in strategy else []
    if not isinstance(value, list):
        findings.append(
            finding(
                0,
                "INVALID_STRATEGY_COLLECTION",
                "REJECT",
                key,
                f"{key} 必须是数组",
            )
        )
        return []
    if required and not value:
        findings.append(
            finding(
                0,
                "EMPTY_STRATEGY_COLLECTION",
                "REJECT",
                key,
                f"{key} 不能为空",
            )
        )
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            findings.append(
                finding(
                    0,
                    "INVALID_STRATEGY_ITEM",
                    "REJECT",
                    f"{key}[{index}]",
                    "条目必须是对象",
                )
            )
        else:
            result.append(item)
    return result


def check_strategy(strategy):
    findings = []
    if not isinstance(strategy, dict):
        strategy = {}
        findings.append(
            finding(
                0,
                "INVALID_STRATEGY",
                "REJECT",
                "root",
                "strategy 根节点必须是对象",
            )
        )

    in_scope = _object_list(strategy, "In_Scope", findings, required=True)
    out_scope = _object_list(strategy, "Out_Of_Scope", findings)
    gates = _object_list(strategy, "Quality_Gates", findings, required=True)
    critical_paths = _object_list(strategy, "Critical_Paths", findings, required=True)

    feature_ids = []
    for index, feature in enumerate(in_scope):
        feature_id = feature.get("feature_id")
        target = feature_id if _nonempty_string(feature_id) else f"In_Scope[{index}]"
        if not _nonempty_string(feature_id):
            findings.append(
                finding(
                    5,
                    "MISSING_FEATURE_ID",
                    "REJECT",
                    target,
                    "feature_id 必须是非空字符串",
                )
            )
        else:
            feature_ids.append(feature_id)
        risk = feature.get("risk_level")
        if not isinstance(risk, str) or risk not in VALID_RISK_LEVELS:
            findings.append(
                finding(
                    5,
                    "INVALID_RISK_LEVEL",
                    "REJECT",
                    target,
                    f"risk_level 必须是 {sorted(VALID_RISK_LEVELS)} 之一",
                )
            )
    for feature_id, count in sorted(Counter(feature_ids).items()):
        if count > 1:
            findings.append(
                finding(
                    5,
                    "DUPLICATE_FEATURE_ID",
                    "REJECT",
                    feature_id,
                    "feature_id 出现多次",
                )
            )
    in_scope_ids = set(feature_ids)

    for index, item in enumerate(out_scope):
        target = f"Out_Of_Scope[{index}]"
        if not _nonempty_string(item.get("item")):
            findings.append(
                finding(
                    1,
                    "INVALID_OUT_OF_SCOPE_ITEM",
                    "REJECT",
                    target,
                    "item 必须是非空字符串",
                )
            )
        if (
            not isinstance(item.get("exclusion_reason"), str)
            or not item["exclusion_reason"].strip()
        ):
            findings.append(
                finding(
                    1,
                    "MISSING_EXCLUSION_REASON",
                    "REJECT",
                    target,
                    "exclusion_reason 为必填项",
                )
            )

    path_ids = []
    for index, path in enumerate(critical_paths):
        path_id = path.get("path_id")
        target = path_id if _nonempty_string(path_id) else f"Critical_Paths[{index}]"
        if not _nonempty_string(path_id):
            findings.append(
                finding(
                    1,
                    "MISSING_CRITICAL_PATH_ID",
                    "REJECT",
                    target,
                    "path_id 必须是非空字符串",
                )
            )
        else:
            path_ids.append(path_id)
        disposition = path.get("disposition")
        if not isinstance(disposition, str) or disposition not in VALID_DISPOSITIONS:
            findings.append(
                finding(
                    1,
                    "INVALID_CRITICAL_PATH_DISPOSITION",
                    "REJECT",
                    target,
                    f"disposition 必须是 {sorted(VALID_DISPOSITIONS)} 之一",
                )
            )
            continue
        if disposition == "IN_SCOPE":
            bound_features = path.get("feature_ids", [])
            if (
                not isinstance(bound_features, list)
                or not bound_features
                or any(not _nonempty_string(item) for item in bound_features)
            ):
                findings.append(
                    finding(
                        1,
                        "INVALID_CRITICAL_PATH_FEATURES",
                        "REJECT",
                        target,
                        "IN_SCOPE 路径需要非空字符串 feature_ids",
                    )
                )
            else:
                for feature_id in sorted(set(bound_features) - in_scope_ids):
                    findings.append(
                        finding(
                            1,
                            "CRITICAL_PATH_FEATURE_NOT_IN_SCOPE",
                            "REJECT",
                            target,
                            f"feature_id {feature_id!r} 未在 In_Scope 中声明",
                        )
                    )
        elif (
            not isinstance(path.get("exclusion_reason"), str)
            or not path["exclusion_reason"].strip()
        ):
            findings.append(
                finding(
                    1,
                    "MISSING_CRITICAL_PATH_EXCLUSION_REASON",
                    "REJECT",
                    target,
                    "OUT_OF_SCOPE 路径需要 exclusion_reason",
                )
            )
    for path_id, count in sorted(Counter(path_ids).items()):
        if count > 1:
            findings.append(
                finding(
                    1,
                    "DUPLICATE_CRITICAL_PATH_ID",
                    "REJECT",
                    path_id,
                    "path_id 出现多次",
                )
            )

    gate_names = []
    for index, gate in enumerate(gates):
        gate_name = gate.get("gate_name") or gate.get("name")
        target = gate_name if _nonempty_string(gate_name) else f"Quality_Gates[{index}]"
        if not _nonempty_string(gate_name):
            findings.append(
                finding(
                    2,
                    "MISSING_GATE_NAME",
                    "REJECT",
                    target,
                    "gate_name 必须是非空字符串",
                )
            )
        else:
            gate_names.append(gate_name)
        threshold = gate.get("threshold")
        if threshold is None:
            findings.append(
                finding(
                    2,
                    "GATE_NOT_QUANTIFIED",
                    "REJECT",
                    target,
                    "gate 缺少数值 threshold",
                )
            )
        elif (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold)
        ):
            findings.append(
                finding(
                    2,
                    "GATE_THRESHOLD_NON_NUMERIC",
                    "REJECT",
                    target,
                    "threshold 必须是有限的非布尔数值",
                )
            )
        elif not 0 <= threshold <= 1:
            findings.append(
                finding(
                    2,
                    "GATE_THRESHOLD_OUT_OF_RANGE",
                    "REJECT",
                    target,
                    "threshold 必须在 [0,1] 范围内",
                )
            )
    for gate_name, count in sorted(Counter(gate_names).items()):
        if count > 1:
            findings.append(
                finding(
                    2,
                    "DUPLICATE_GATE_NAME",
                    "REJECT",
                    gate_name,
                    "gate_name 出现多次",
                )
            )

    pyramid = strategy.get("Pyramid_Distribution")
    pyramid_values = {}
    if not isinstance(pyramid, dict):
        findings.append(
            finding(
                3,
                "INVALID_PYRAMID",
                "REJECT",
                "Pyramid_Distribution",
                "pyramid 必须是对象",
            )
        )
    else:
        for key in PYRAMID_KEYS:
            value = pyramid.get(key)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                findings.append(
                    finding(
                        3,
                        "INVALID_PYRAMID_VALUE",
                        "REJECT",
                        f"pyramid:{key}",
                        "pyramid 值必须是 [0,1] 内的有限数值",
                    )
                )
            else:
                pyramid_values[key] = value
        if len(pyramid_values) == len(PYRAMID_KEYS):
            total = sum(pyramid_values.values())
            if abs(total - 1.0) > 0.001:
                findings.append(
                    finding(
                        3,
                        "PYRAMID_SUM_INVALID",
                        "REJECT",
                        "pyramid",
                        f"pyramid 占比之和为 {total}，应为 1.0 ± 0.001",
                    )
                )
            unit = pyramid_values["unit"]
            integration = pyramid_values["integration"]
            e2e = pyramid_values["e2e"]
            if e2e > unit:
                findings.append(
                    finding(
                        3,
                        "PYRAMID_INVERTED",
                        "REJECT",
                        "pyramid",
                        f"e2e ({e2e}) 大于 unit ({unit})",
                    )
                )
            elif integration > unit:
                findings.append(
                    finding(
                        3,
                        "PYRAMID_TROPHY",
                        "REVIEW",
                        "pyramid",
                        f"integration ({integration}) 大于 unit ({unit})",
                    )
                )

    mock_policy = strategy.get("Mock_Policy")
    if not isinstance(mock_policy, dict):
        findings.append(
            finding(
                4,
                "INVALID_MOCK_POLICY",
                "REJECT",
                "Mock_Policy",
                "mock policy 必须是对象",
            )
        )
    else:
        for key in ("mock_targets", "no_mock_targets"):
            targets = mock_policy.get(key, [])
            if not isinstance(targets, list) or any(
                not _nonempty_string(item) for item in targets
            ):
                findings.append(
                    finding(
                        4,
                        "INVALID_MOCK_TARGETS",
                        "REJECT",
                        f"Mock_Policy.{key}",
                        "targets 必须是非空字符串数组",
                    )
                )
                continue
            if key == "mock_targets":
                for layer in sorted(
                    CORE_LAYERS & {item.strip().lower() for item in targets}
                ):
                    findings.append(
                        finding(
                            4,
                            "CORE_LAYER_MOCKED",
                            "REJECT",
                            f"mock_targets:{layer}",
                            f"核心层 {layer!r} 被 mock",
                        )
                    )

    has_reject = any(item["severity"] == "REJECT" for item in findings)
    has_review = any(item["severity"] == "REVIEW" for item in findings)
    verdict = "REJECT" if has_reject else ("PASS_WITH_REVIEW" if has_review else "PASS")
    return {
        "skill": "06",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "verdict": verdict,
        "total_findings": len(findings),
        "reject_count": sum(1 for item in findings if item["severity"] == "REJECT"),
        "review_count": sum(1 for item in findings if item["severity"] == "REVIEW"),
        "findings": findings,
        "routing": {
            "PASS": "strategy 就绪；gate 是下游覆盖率检查的基准",
            "PASS_WITH_REVIEW": "strategy 就绪 + 标记待评审项",
            "REJECT": "在测试设计开始前重新起草 strategy",
        }[verdict],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Strategy Contract 校验器")
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    try:
        with open(args.strategy, encoding="utf-8") as handle:
            strategy = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": f"读取输入失败：{exc}"}), file=sys.stderr)
        return 3
    result = check_strategy(strategy)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    try:
        if args.out:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(output)
        else:
            print(output)
    except OSError as exc:
        print(json.dumps({"error": f"写入输出失败：{exc}"}), file=sys.stderr)
        return 3
    return {"PASS": 0, "PASS_WITH_REVIEW": 1, "REJECT": 2}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
