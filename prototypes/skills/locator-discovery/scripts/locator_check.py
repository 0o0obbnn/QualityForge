#!/usr/bin/env python3
"""
UI locator 稳定性校验器。

五项检查（见 references/locator_rules.md）：
  1. SINGLE_STRATEGY_LOCATOR：locator 策略数 <2。
  2. INDEX_XPATH_PRIMARY：主策略是索引型 XPath（最脆）。
  3. MISSING_STABILITY_SCORE：缺少 stability_score。
  4. INVALID_STABILITY_SCORE：分数不在 [0,1] 内。
  5. LOW_STABILITY（REVIEW）：分数低于 0.6 监控阈值。

CLI:
  python locator_check.py --locator path/to/locator.json [--out path]

退出码：0 PASS | 1 REVIEW | 2 REJECT | 3 输入无效
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys

STABILITY_THRESHOLD = 0.6
# 索引型 XPath：//*[3]、tbody[2]、(//div)[1] —— 任何兄弟节点重排都会失效。
INDEX_XPATH_RE = re.compile(r"\[\s*\d+\s*\]")


def finding(code, target, msg, severity="REJECT"):
    return {"code": code, "severity": severity, "target": target, "msg": msg}


def _is_index_based(strategy):
    """显式标记为索引型，或 value 中含位置谓词，即视为索引型。"""
    if strategy.get("index_based"):
        return True
    value = strategy.get("value", "")
    return bool(isinstance(value, str) and INDEX_XPATH_RE.search(value))


def check_locator(payload):
    """校验单个 locator 条目。返回 findings 列表。"""
    findings = []
    if not isinstance(payload, dict):
        return [finding("INVALID_LOCATOR_PACKET", "root", "locator 根节点必须是对象")]

    raw_strategies = payload.get("strategies", [])
    if not isinstance(raw_strategies, list):
        return [finding("INVALID_LOCATOR_PACKET", "strategies", "strategies 必须是数组")]
    strategies = [s for s in raw_strategies if isinstance(s, dict)]
    if len(strategies) != len(raw_strategies):
        findings.append(
            finding("INVALID_LOCATOR_PACKET", "strategies", "每个 strategy 都必须是对象")
        )

    # 检查 1：必须具备回退策略
    if len(strategies) < 2:
        findings.append(
            finding(
                "SINGLE_STRATEGY_LOCATOR",
                "strategies",
                f"locator 仅声明了 {len(strategies)} 个策略；回退需要 >=2 个",
            )
        )

    # 检查 2：索引型 XPath 绝不能作为主策略
    if strategies:
        primary = strategies[0]
        if str(primary.get("type", "")).lower() == "xpath" and _is_index_based(primary):
            findings.append(
                finding(
                    "INDEX_XPATH_PRIMARY",
                    primary.get("value", "strategies[0]"),
                    "主策略是索引型 XPath；禁止作为主策略（兄弟节点重排即失效）",
                )
            )

    # 检查 3-5：稳定性分数
    score = payload.get("stability_score")
    if score is None:
        findings.append(
            finding("MISSING_STABILITY_SCORE", "stability_score", "未声明 stability_score")
        )
    elif isinstance(score, bool) or not isinstance(score, (int, float)):
        findings.append(
            finding(
                "INVALID_STABILITY_SCORE",
                "stability_score",
                f"stability_score 必须是数字，实际为 {score!r}",
            )
        )
    elif not 0 <= score <= 1:
        findings.append(
            finding("INVALID_STABILITY_SCORE", "stability_score", f"分数 {score} 超出 [0,1]")
        )
    elif score < STABILITY_THRESHOLD:
        findings.append(
            finding(
                "LOW_STABILITY",
                "stability_score",
                f"分数 {score} 低于 {STABILITY_THRESHOLD}；标记进入自愈监控",
                severity="REVIEW",
            )
        )

    return findings


def check_locator_report(payload):
    """将 findings 列表包装为带 verdict 的信封。"""
    findings = check_locator(payload)
    has_reject = any(f["severity"] == "REJECT" for f in findings)
    has_review = any(f["severity"] == "REVIEW" for f in findings)
    verdict = "REJECT" if has_reject else ("REVIEW" if has_review else "PASS")
    return {
        "skill": "20",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "locator_id": payload.get("locator_id") if isinstance(payload, dict) else None,
        "total_findings": len(findings),
        "findings": findings,
        "verdict": verdict,
        "routing": {
            "PASS": "locator 可入库",
            "REVIEW": "locator 可用，但需监控并在 DOM 变化时修复",
            "REJECT": "入库前必须修复策略/分数",
        }[verdict],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="UI locator 稳定性校验器")
    p.add_argument("--locator", required=True, help="locator JSON")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        with open(args.locator, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr)
        return 3
    result = check_locator_report(payload)
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
    return {"PASS": 0, "REVIEW": 1, "REJECT": 2}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
