#!/usr/bin/env python3
"""变更影响分析校验器。"""
from __future__ import annotations
import argparse, datetime as _dt, json, sys


def finding(code, severity, target, msg):
    return {"code": code, "severity": severity, "target": target, "msg": msg}


def check_analysis(report):
    findings = []
    if not isinstance(report, dict):
        return {"skill": "26", "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "total_impacted": 0, "max_depth": 0, "total_findings": 1,
                "findings": [finding("INVALID_IMPACT_REPORT", "REJECT", "root",
                                     "影响报告根节点必须是对象")],
                "verdict": "REJECT",
                "routing": "PASS -> 送入回归选择；REJECT -> 重新执行分析"}
    max_depth = report.get("max_depth_reached", 0)
    # graph_available 必须显式断言。默认为 True 会让一份从未接触过图的报告
    # 被解读为健康的全图遍历——这正是本 skill 要捕获的静默退化。
    graph_available = report.get("graph_available")
    used_static_fallback = report.get("used_static_fallback", False)
    impacted = [a for a in (report.get("impacted_assets", []) or []) if isinstance(a, dict)]

    if graph_available is None:
        findings.append(finding("GRAPH_AVAILABILITY_UNDECLARED", "REJECT", "analysis",
                                "缺少 graph_available；无法确认遍历完整性"))
        graph_available = False
    if not isinstance(max_depth, int) or isinstance(max_depth, bool):
        findings.append(finding("SHALLOW_PROPAGATION", "REJECT", "analysis",
                                f"max_depth_reached 必须是整数，实际为 {max_depth!r}"))
        max_depth = 0

    # 检查 1：至少 2 跳
    elif max_depth < 2:
        findings.append(finding("SHALLOW_PROPAGATION", "REJECT", "analysis",
                                f"max_depth_reached={max_depth}；需要 >=2 才能捕获间接影响"))

    # 检查 2：每个受影响资产必须分类为 direct/indirect
    for asset in impacted:
        aid = asset.get("asset_id", "?")
        cls = asset.get("impact_class")
        if cls not in ("direct", "indirect"):
            findings.append(finding("UNCLASSIFIED_IMPACT", "REJECT", aid,
                                    f"资产 {aid!r} 的 impact_class={cls!r}；必须是 direct 或 indirect"))

    # 检查 3：静默静态回退
    if used_static_fallback and not report.get("degraded_confidence_flagged"):
        findings.append(finding("SILENT_STATIC_FALLBACK", "REJECT", "analysis",
                                "使用了静态代码回退但未标记置信度退化；"
                                "间接影响可能缺失"))

    # 附加：图不可用时必须标记退化
    if not graph_available and not report.get("degraded_confidence_flagged"):
        findings.append(finding("SILENT_STATIC_FALLBACK", "REJECT", "analysis",
                                "图数据不可用但未标记置信度退化"))

    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {"skill": "26", "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "total_impacted": len(impacted), "max_depth": max_depth,
            "total_findings": len(findings), "findings": findings,
            "verdict": "REJECT" if has_reject else "PASS",
            "routing": "PASS -> 送入回归选择；REJECT -> 重新执行分析"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True); p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        report = json.load(open(args.report))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr); return 3
    result = check_analysis(report)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out: open(args.out, "w").write(out)
    else: print(out)
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
