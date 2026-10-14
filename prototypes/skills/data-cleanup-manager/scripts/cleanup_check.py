#!/usr/bin/env python3
"""
数据清理校验器——四项检查。

检查项：
  1. REVERSE_ORDER：清理顺序与构建顺序相反（LIFO）。
  2. NO_STATIC_BASELINE：清理列表中不得包含 Static baseline。
  3. FAILURES_REPORTED：每一步都有 status；失败必须附 reason。
  4. RESIDUALS_LISTED：残留必须显式列举并附原因。

CLI:
  python cleanup_check.py --cleanup path/to/cleanup.json [--out path]

退出码：0 PASS | 2 REJECT | 3 输入无效
"""
from __future__ import annotations
import argparse, datetime as _dt, json, sys


def finding(check, code, severity, target, msg):
    return {"check": check, "code": code, "severity": severity, "target": target, "msg": msg}


def check_cleanup(packet):
    findings = []
    construction_order = packet.get("construction_order", []) or []
    cleanup_plan = packet.get("cleanup_plan", []) or []
    static_baselines = set(packet.get("static_baselines", []) or [])
    results = packet.get("results", []) or []
    residuals = packet.get("residuals", None)

    # 检查 1：相反顺序
    expected_reverse = list(reversed(construction_order))
    if cleanup_plan and construction_order:
        if cleanup_plan != expected_reverse:
            # 找到第一个偏差位置，给出清晰信息
            for i, (actual, expected) in enumerate(zip(cleanup_plan, expected_reverse)):
                if actual != expected:
                    findings.append(finding(1, "WRONG_CLEANUP_ORDER", "REJECT", f"position:{i}",
                                            f"cleanup[{i}]={actual!r} 但应为 {expected!r}（构建顺序的逆序）；"
                                            f"违反 LIFO"))
                    break
            else:
                findings.append(finding(1, "WRONG_CLEANUP_ORDER", "REJECT", "cleanup_plan",
                                        f"cleanup 有 {len(cleanup_plan)} 步，但逆序应为 {len(expected_reverse)} 步"))

    # 检查 2：清理中不得含 Static baseline
    for node_id in cleanup_plan:
        if node_id in static_baselines:
            findings.append(finding(2, "STATIC_BASELINE_IN_CLEANUP", "REJECT", node_id,
                                    f"Static baseline {node_id!r} 出现在清理列表中；baseline 是共享的，绝不由某个 phase 拆除"))

    # 检查 3：失败必须上报（每个 result 都有 status，失败的附 reason）
    for r in results:
        rid = r.get("node_id", "?")
        status = r.get("status")
        if not status:
            findings.append(finding(3, "MISSING_CLEANUP_STATUS", "REJECT", rid,
                                    f"清理步骤 {rid!r} 没有 status；结果被静默"))
        elif status in ("failed", "skipped") and not r.get("reason"):
            findings.append(finding(3, "SILENCED_FAILURE", "REJECT", rid,
                                    f"清理步骤 {rid!r} status={status!r} 但未给出 reason"))

    # 检查 4：残留已列举（必须是列表，可为空）
    if residuals is None:
        findings.append(finding(4, "RESIDUALS_NOT_CHECKED", "REJECT", "residuals",
                                "缺少 residuals 字段；无法确认清理完整性"))
    else:
        for res in residuals:
            if not res.get("reason"):
                findings.append(finding(4, "UNTRACKED_RESIDUAL", "REJECT", res.get("node_id", "?"),
                                        f"残留 {res.get('node_id','?')!r} 没有 reason；未跟踪的状态泄漏"))

    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {
        "skill": "17",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "total_cleanup_steps": len(cleanup_plan),
        "total_results": len(results),
        "residual_count": len(residuals) if residuals is not None else None,
        "total_findings": len(findings),
        "findings": findings,
        "verdict": "REJECT" if has_reject else "PASS",
        "routing": "PASS -> phase 可关闭；REJECT -> 进入下一 phase 前必须修复清理（脏状态不得传播）",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="数据清理校验器")
    p.add_argument("--cleanup", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        packet = json.load(open(args.cleanup))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr); return 3
    result = check_cleanup(packet)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out: open(args.out, "w").write(out)
    else: print(out)
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
