#!/usr/bin/env python3
"""
Assertion 批次质量检查器——弱断言比例。

基于语法模式将每条 assertion 判定为弱或强，
若弱断言比例超过策略阈值则拒绝整个批次。
这是逐条 assertion 验证（检查单条正确性）的批次级补充。

CLI:
  python batch_check.py --batch path/to/batch.json [--threshold 0.3] [--out path]

退出码：0 PASS | 2 REJECT | 3 输入无效
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys

# 弱断言模式（语法层面）。顺序：最特定的在前。
WEAK_PATTERNS = [
    # 仅状态码：target 引用 status_code（不限运算符）
    (re.compile(r"status[_\-]?code", re.IGNORECASE), "status_code_only"),
    # 仅存在性（not None / exists）
    (
        re.compile(r"is\s+not\s+None|isNotNull|is_present|exists\(\)", re.IGNORECASE),
        "presence_only",
    ),
    # 仅类型检查
    (
        re.compile(r"^isinstance\s*\(|^type\s*\(\s*\w+\s*\)\s*==", re.IGNORECASE),
        "type_only",
    ),
    # 常量真值重言式
    (
        re.compile(r"True\s*==\s*True|1\s*==\s*1|assert\s+True", re.IGNORECASE),
        "constant_true",
    ),
]

DEFAULT_THRESHOLD = 0.3


def classify_assertion(assertion):
    """返回 (is_weak, weak_reason)。"""
    expr = (
        str(assertion.get("expression", ""))
        + " "
        + str(assertion.get("target", ""))
        + " "
        + str(assertion.get("expected", ""))
    )
    # 完全没有字段引用 -> 弱
    if not assertion.get("target") and not assertion.get("field"):
        return True, "no_field_reference"
    for pat, reason in WEAK_PATTERNS:
        if pat.search(expr):
            return True, reason
    return False, None


def check_batch(batch, threshold=DEFAULT_THRESHOLD):
    findings = []
    if isinstance(batch, list):
        assertions = batch
    elif isinstance(batch, dict):
        assertions = batch.get("assertions", []) or []
    else:
        assertions = []
    weak_ids = []

    valid_assertions = []
    for index, a in enumerate(assertions):
        if not isinstance(a, dict):
            findings.append(
                {
                    "code": "INVALID_ASSERTION_STRUCTURE",
                    "severity": "REJECT",
                    "target": f"assertions[{index}]",
                    "msg": "assertion 必须是对象",
                }
            )
            continue
        missing = [
            field
            for field in ("assertion_id", "expression", "expected")
            if field not in a or a[field] in (None, "")
        ]
        if not a.get("target") and not a.get("field"):
            missing.append("target|field")
        if missing:
            findings.append(
                {
                    "code": "INVALID_ASSERTION_STRUCTURE",
                    "severity": "REJECT",
                    "target": a.get("assertion_id", f"assertions[{index}]"),
                    "msg": f"assertion 缺失字段：{missing}",
                }
            )
            continue
        valid_assertions.append(a)

    for a in valid_assertions:
        aid = a.get("assertion_id", "?")
        is_weak, _reason = classify_assertion(a)
        if is_weak:
            weak_ids.append(aid)

    total = len(valid_assertions)
    weak_count = len(weak_ids)
    weak_ratio = weak_count / total if total > 0 else 0.0

    if total == 0:
        findings.append(
            {
                "code": "EMPTY_BATCH",
                "severity": "REJECT",
                "target": "batch",
                "msg": "批次中没有 assertion",
            }
        )
    elif weak_ratio > threshold:
        findings.append(
            {
                "code": "WEAK_RATIO_EXCEEDED",
                "severity": "REJECT",
                "target": "batch",
                "msg": f"弱断言比例 {weak_ratio:.0%}（{weak_count}/{total}）超过阈值 {threshold:.0%}； "
                f"需强化以下弱断言：{weak_ids[:10]}",
            }
        )

    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {
        "skill": "10",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "total_assertions": total,
        "weak_count": weak_count,
        "strong_count": total - weak_count,
        "weak_ratio": round(weak_ratio, 3),
        "threshold": threshold,
        "weak_assertion_ids": weak_ids,
        "verdict": "REJECT" if has_reject else "PASS",
        "total_findings": len(findings),
        "findings": findings,
        "routing": "PASS -> 进入逐条 assertion 验证；REJECT -> 强化弱断言后重新提交",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Assertion 批次质量检查器")
    p.add_argument("--batch", required=True)
    p.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="弱断言比例上限（默认 0.3）",
    )
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    if not (0.0 <= args.threshold <= 1.0):
        print(json.dumps({"error": "threshold 必须在 [0,1] 范围内"}), file=sys.stderr)
        return 3
    try:
        with open(args.batch, encoding="utf-8") as handle:
            batch = json.load(handle)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr)
        return 3
    result = check_batch(batch, args.threshold)
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
