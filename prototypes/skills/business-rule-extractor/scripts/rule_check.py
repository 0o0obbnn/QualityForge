#!/usr/bin/env python3
"""业务规则抽取检查器。"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import sys


def finding(code, target, msg):
    return {"code": code, "severity": "REJECT", "target": target, "msg": msg}


def check_rules(packet):
    findings = []
    if not isinstance(packet, dict):
        packet = {}
        findings.append(
            finding("INVALID_RULE_PACKET", "root", "规则包根节点必须是对象")
        )
    raw_rules = packet.get("rules", []) or []
    if not isinstance(raw_rules, list):
        findings.append(
            finding("INVALID_RULE_COLLECTION", "rules", "rules 必须是数组")
        )
        raw_rules = []
    rules = []
    for index, rule in enumerate(raw_rules):
        if not isinstance(rule, dict):
            findings.append(
                finding("INVALID_RULE", f"rules[{index}]", "rule 必须是对象")
            )
            continue
        rules.append(rule)
        rid = rule.get("rule_id", "?")
        condition = rule.get("condition")
        action = rule.get("action")
        # 检查 1：condition -> action 结构
        if not condition or not action:
            findings.append(
                finding(
                    "UNSTRUCTURED_RULE",
                    rid,
                    f"rule {rid!r} 缺少 {'condition' if not condition else 'action'}；需要 condition->action 结构",
                )
            )
        # 检查 2：推断规则必须人工复核；confidence 只是元数据。
        is_inferred = rule.get("inferred", False) or str(
            rule.get("source", "")
        ).lower() in ("inferred", "guess", "deduced")
        conf = rule.get("confidence")
        if is_inferred:
            if (
                isinstance(conf, bool)
                or not isinstance(conf, (int, float))
                or not math.isfinite(conf)
                or not 0 <= conf <= 1
            ):
                findings.append(
                    finding(
                        "INVALID_INFERRED_CONFIDENCE",
                        rid,
                        "推断规则的 confidence 必须是 [0,1] 内的有限数字",
                    )
                )
            if rule.get("validation_status") != "NEED_HUMAN_REVIEW":
                findings.append(
                    finding(
                        "INFERRED_RULE_MISSING_REVIEW_ROUTE",
                        rid,
                        "推断规则无论 confidence 如何都必须路由到 NEED_HUMAN_REVIEW",
                    )
                )
        # 检查 3：无法结构化 -> NEED_HUMAN_REVIEW
        if (
            rule.get("unstructureable")
            and rule.get("validation_status") != "NEED_HUMAN_REVIEW"
        ):
            findings.append(
                finding(
                    "RULE_FORCED_INTO_SHAPE",
                    rid,
                    "规则标记为 unstructureable 但未路由到 NEED_HUMAN_REVIEW",
                )
            )
        # 检查 4：来源引用
        if not rule.get("source"):
            findings.append(
                finding("RULE_NO_SOURCE", rid, f"rule {rid!r} 没有来源引用")
            )

    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {
        "skill": "02",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "total_rules": len(rules),
        "total_findings": len(findings),
        "findings": findings,
        "verdict": "REJECT" if has_reject else ("PASS" if rules else "REJECT"),
        "routing": "PASS -> 规则可进入融合；REJECT -> 重新抽取被标记的规则",
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--packet", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        with open(args.packet, encoding="utf-8") as handle:
            packet = json.load(handle)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr)
        return 3
    result = check_rules(packet)
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
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
