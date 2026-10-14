#!/usr/bin/env python3
"""安全测试用例契约检查器。"""
from __future__ import annotations
import argparse, datetime as _dt, json, re, sys

VULN_DETAIL_RE = re.compile(r'(payload|exploit|proof.of.concept|poc|command|attack.vector)\s*[:=]', re.IGNORECASE)
SENSITIVE_PATTERNS_RE = re.compile(r'(DROP\s+TABLE|UNION\s+SELECT|<script)', re.IGNORECASE)


def finding(code, target, msg):
    return {"code": code, "severity": "REJECT", "target": target, "msg": msg}


def check_cases(packet):
    findings = []
    if not isinstance(packet, dict):
        return {"skill": "22", "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "total_cases": 0, "total_findings": 1,
                "findings": [finding("INVALID_SECURITY_PACKET", "root",
                                     "安全 packet 根节点必须是对象")],
                "verdict": "REJECT",
                "routing": "PASS -> finding 走安全上报通道；REJECT -> 修复范围/授权/脱敏问题"}
    cases = [c for c in (packet.get("cases", []) or []) if isinstance(c, dict)]
    in_scope = set(packet.get("in_scope_endpoints", []) or [])
    permission_rules = set(packet.get("permission_rule_ids", []) or [])
    report = packet.get("report", {})

    # 未声明的范围无法授权扫描。若把缺失当作"全部在范围内"，
    # 恰好会在 strategy 契约缺失时关闭范围 gate。
    if cases and not in_scope:
        findings.append(finding("SCOPE_UNDECLARED", "in_scope_endpoints",
                                "未声明 in_scope_endpoints；无法确认扫描目标已获授权"))

    for case in cases:
        cid = case.get("case_id", "?")
        target_endpoint = case.get("target_endpoint", "")
        case_type = case.get("type", "")

        # 检查 1：只允许范围内目标
        if not target_endpoint:
            findings.append(finding("OUT_OF_SCOPE_TARGET", cid,
                                    f"用例 {cid!r} 未声明 target_endpoint；无法核实范围"))
        elif in_scope and target_endpoint not in in_scope:
            findings.append(finding("OUT_OF_SCOPE_TARGET", cid,
                                    f"目标 {target_endpoint!r} 不在 strategy 的 In_Scope 中；属于未授权扫描"))
        # 检查 2：授权类测试必须绑定 permission rule
        if case_type in ("authorization_bypass", "privilege_escalation", "authz"):
            rule_binding = case.get("permission_rule_id")
            if not rule_binding:
                findings.append(finding("AUTHZ_WITHOUT_RULE_BINDING", cid,
                                        f"authz 测试 {cid!r} 未绑定 permission_rule_id"))
            elif not permission_rules:
                findings.append(finding("AUTHZ_WITHOUT_RULE_BINDING", cid,
                                        f"authz 测试 {cid!r} 绑定了 {rule_binding!r}，但未提供已知 "
                                        "permission rules；绑定无法核实"))
            elif rule_binding not in permission_rules:
                findings.append(finding("AUTHZ_WITHOUT_RULE_BINDING", cid,
                                        f"permission_rule_id {rule_binding!r} 不在已知 permission rules 中"))

    # 检查 3：报告中不得出现明文漏洞细节
    report_text = json.dumps(report)
    if VULN_DETAIL_RE.search(report_text) and SENSITIVE_PATTERNS_RE.search(report_text):
        findings.append(finding("PLAINTEXT_VULN_DETAIL", "report",
                                "报告包含可利用的明文漏洞细节；请按安全上报规范脱敏"))

    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {"skill": "22", "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "total_cases": len(cases), "total_findings": len(findings), "findings": findings,
            "verdict": "REJECT" if has_reject else "PASS",
            "routing": "PASS -> finding 走安全上报通道；REJECT -> 修复范围/授权/脱敏问题"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--packet", required=True); p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        packet = json.load(open(args.packet))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"input: {e}"}), file=sys.stderr); return 3
    result = check_cases(packet)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out: open(args.out, "w").write(out)
    else: print(out)
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
