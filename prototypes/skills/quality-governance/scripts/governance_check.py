#!/usr/bin/env python3
"""治理看板校验器。"""
from __future__ import annotations
import argparse, datetime as _dt, json, sys


def finding(code, target, msg):
    return {"code": code, "severity": "REJECT", "target": target, "msg": msg}


def check_dashboard(report):
    findings = []
    if not isinstance(report, dict):
        return {"skill": "30", "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "total_findings": 1,
                "findings": [finding("INVALID_DASHBOARD_PACKET", "root",
                                     "看板报告根节点必须是对象")],
                "verdict": "REJECT",
                "routing": "PASS -> 发布看板；REJECT -> 修复指标/成本/策略问题"}
    raw_metrics = report.get("metrics", []) or []
    metrics = [m for m in raw_metrics if isinstance(m, dict)]
    raw_costs = report.get("cost_breakdown", {}) or {}
    costs = raw_costs if isinstance(raw_costs, dict) else {}
    raw_budgets = report.get("budgets", {}) or {}
    budgets = raw_budgets if isinstance(raw_budgets, dict) else {}
    raw_alerts = report.get("budget_alerts", {}) or {}
    alerts = raw_alerts if isinstance(raw_alerts, dict) else {}
    strategy_amended = report.get("strategy_amended", False)
    metric_definitions = report.get("metric_definitions_source", "")

    if len(metrics) != len(raw_metrics) or not isinstance(raw_metrics, list):
        findings.append(finding("MALFORMED_METRIC_ENTRY", "metrics",
                                "metrics[] 的每一项都必须是对象"))
    if not isinstance(raw_costs, dict):
        findings.append(finding("MALFORMED_COST_BREAKDOWN", "cost_breakdown",
                                "cost_breakdown 必须是对象"))
    if not isinstance(raw_budgets, dict):
        findings.append(finding("MALFORMED_BUDGETS", "budgets", "budgets 必须是对象"))

    # 检查 1：只认可有效覆盖率。缺失指标集属于证据缺失，
    # 不是干净通过——空看板绝不能让治理 gate 放行。
    if not metrics:
        findings.append(finding("NO_METRICS_REPORTED", "metrics",
                                "未上报任何指标；无法确认覆盖率质量"))
    for m in metrics:
        mname = m.get("name", "")
        if "coverage" in str(mname).lower():
            mtype = m.get("type", "")
            if mtype in ("line", "branch", "statement"):
                findings.append(finding("RAW_LINE_COVERAGE_REPORTED", mname,
                                        f"指标 {mname!r} 使用 {mtype} 覆盖率；必须使用有效覆盖率"))
            elif mtype != "effective":
                findings.append(finding("RAW_LINE_COVERAGE_REPORTED", mname,
                                        f"覆盖率指标 {mname!r} type={mtype!r}；必须为 'effective'"))

    # 检查 2：成本分解 + 预算告警
    if not costs:
        findings.append(finding("COST_NOT_DECOMPOSED", "cost_breakdown", "缺少按 skill 分解的成本"))
    else:
        for skill, cost in costs.items():
            budget = budgets.get(skill)
            # 未声明预算会让超支无法被检测；缺失就是缺口，
            # 不能默认视为"在预算内"。
            if budget is None:
                findings.append(finding("BUDGET_NOT_DECLARED", skill,
                                        f"skill {skill!r} 上报成本 {cost} 但未声明预算；"
                                        "无法检测超支"))
                continue
            if isinstance(budget, bool) or not isinstance(budget, (int, float)):
                findings.append(finding("MALFORMED_BUDGETS", skill,
                                        f"skill {skill!r} 的预算必须是数字，实际为 {budget!r}"))
                continue
            if isinstance(cost, bool) or not isinstance(cost, (int, float)):
                findings.append(finding("MALFORMED_COST_BREAKDOWN", skill,
                                        f"skill {skill!r} 的成本必须是数字，实际为 {cost!r}"))
                continue
            if cost > budget and not alerts.get(skill):
                findings.append(finding("BUDGET_OVERRUN_SILENT", skill,
                                        f"skill {skill!r} 成本 {cost} 超出预算 {budget} 但未触发告警"))

    # 检查 3：仅允许建议
    if strategy_amended:
        findings.append(finding("STRATEGY_AMENDED_BY_DASHBOARD", "report",
                                "报告修改了 strategy 阈值；治理只允许给出建议"))

    # 检查 4：单一事实来源。未声明来源的指标无法核实，
    # 因此不能默认视为权威定义。
    if not metric_definitions:
        findings.append(finding("METRIC_DEFINITIONS_UNDECLARED", "definitions",
                                "metric_definitions_source 缺失；无法确认单一事实来源"))
    elif metric_definitions not in ("canonical", "source-of-truth"):
        findings.append(finding("METRIC_REDEFINED_ADHOC", "definitions",
                                f"metric_definitions_source={metric_definitions!r}；必须为 canonical"))

    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {"skill": "30", "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "total_findings": len(findings), "findings": findings,
            "verdict": "REJECT" if has_reject else "PASS",
            "routing": "PASS -> 发布看板；REJECT -> 修复指标/成本/策略问题"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True); p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        with open(args.report, encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"读取输入失败：{e}"}), file=sys.stderr); return 3
    result = check_dashboard(report)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    try:
        if args.out:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(out)
        else:
            print(out)
    except OSError as e:
        print(json.dumps({"error": f"写入输出失败：{e}"}), file=sys.stderr); return 3
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
