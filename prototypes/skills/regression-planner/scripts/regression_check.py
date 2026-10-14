#!/usr/bin/env python3
"""回归选择校验器。"""
from __future__ import annotations
import argparse, datetime as _dt, json, sys


def finding(code, severity, target, msg):
    return {"code": code, "severity": severity, "target": target, "msg": msg}


def check_selection(packet):
    findings = []
    if not isinstance(packet, dict):
        packet = {}
        findings.append(finding("INVALID_SELECTION_PACKET", "REJECT", "root",
                                "选择 packet 根节点必须是对象"))
    all_impacted = [a for a in (packet.get("all_impacted_assets", []) or []) if isinstance(a, str)]
    selected_list = [a for a in (packet.get("selected_assets", []) or []) if isinstance(a, str)]
    selected = set(selected_list)
    exclusions = [e for e in (packet.get("exclusions", []) or []) if isinstance(e, dict)]
    breaking_drift_assets = set(packet.get("breaking_drift_assets", []) or [])
    high_risk_assets = set(packet.get("high_risk_assets", []) or [])
    total_suite_size = packet.get("total_suite_size", 0)

    # 空 packet 证明不了选择的质量；缺少声明的套件规模或选择
    # 就是证据缺失，绝不能算干净 PASS。
    if not selected_list and not exclusions:
        findings.append(finding("EMPTY_SELECTION_PACKET", "REJECT", "selection",
                                "既无 selected_assets 也无 exclusions；选择无法审计"))
    if isinstance(total_suite_size, bool) or not isinstance(total_suite_size, int):
        findings.append(finding("SUITE_SIZE_UNDECLARED", "REJECT", "total_suite_size",
                                f"total_suite_size 必须是整数，实际为 {total_suite_size!r}；"
                                "缺它就无法检测全量回归"))
        total_suite_size = 0
    elif total_suite_size <= 0 and selected_list:
        findings.append(finding("SUITE_SIZE_UNDECLARED", "REJECT", "total_suite_size",
                                "选中了资产时 total_suite_size 必须 > 0；"
                                "缺它就无法检测全量回归"))

    # 检查 1：禁止默认全量回归（比较原始列表长度，而不是去重后的集合）
    if total_suite_size > 0 and len(selected_list) == total_suite_size and total_suite_size > 10:
        findings.append(finding("FULL_REGRESSION_DEFAULT", "REJECT", "selection",
                                f"选中 {len(selected)}/{total_suite_size}；这是全量回归，不是选择"))

    # 检查 2：破坏性 drift 必须被覆盖
    for asset_id in sorted(breaking_drift_assets):
        if asset_id not in selected:
            findings.append(finding("BREAKING_DRIFT_EXCLUDED", "REJECT", asset_id,
                                    f"破坏性 drift 资产 {asset_id!r} 被排除在回归之外；不可协商"))

    # 检查 3：排除必须有理由
    excl_ids = set()
    for excl in exclusions:
        eid = excl.get("asset_id", "?")
        excl_ids.add(eid)
        if not excl.get("reason"):
            findings.append(finding("EXCLUSION_WITHOUT_REASON", "REJECT", eid,
                                    f"被排除的资产 {eid!r} 没有理由；缺口无法问责"))

    # 检查 4：高风险资产必须被覆盖
    for asset_id in sorted(high_risk_assets):
        if asset_id not in selected and asset_id not in excl_ids:
            findings.append(finding("HIGH_RISK_EXCLUDED", "REJECT", asset_id,
                                    f"高风险资产 {asset_id!r} 既未选中也未记录排除理由"))

    # 检查 5：每个受影响资产要么被选中，要么被显式排除。
    # 否则核心承诺——受影响集合的*最小充分*子集——从未被真正验证。
    for asset_id in sorted(set(all_impacted) - selected - excl_ids):
        findings.append(finding("IMPACTED_ASSET_UNACCOUNTED", "REJECT", asset_id,
                                f"受影响资产 {asset_id!r} 既未选中也未记录排除理由；"
                                "静默的覆盖缺口"))

    # 检查 6：声明了受影响集合时，选择必须落在该集合内。
    if all_impacted:
        for asset_id in sorted(selected - set(all_impacted)):
            findings.append(finding("SELECTED_ASSET_NOT_IMPACTED", "REJECT", asset_id,
                                    f"选中的资产 {asset_id!r} 不在 all_impacted_assets 中；"
                                    "选择无法追溯到影响分析"))

    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {"skill": "27", "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "total_impacted": len(all_impacted), "selected_count": len(selected),
            "excluded_count": len(exclusions),
            "total_findings": len(findings), "findings": findings,
            "verdict": "REJECT" if has_reject else "PASS",
            "routing": "PASS -> 执行回归；REJECT -> 修复选择"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--selection", required=True); p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        with open(args.selection, encoding="utf-8") as handle:
            packet = json.load(handle)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"读取输入失败：{e}"}), file=sys.stderr); return 3
    result = check_selection(packet)
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
