#!/usr/bin/env python3
"""
测试数据合规 gate。四条硬规则：
  R1：SENSITIVE 字段必须声明 masking_policy
  R2：日志/IR 中不得出现 SENSITIVE 明文值
  R3：目标环境绝不能是生产
  R4：每次运行都必须声明 seed
"""
from __future__ import annotations
import argparse, datetime as _dt, json, sys

VALID_MASKING_POLICIES = frozenset({"pseudonymize", "tokenize", "synthesize", "suppress"})
PRODUCTION_ALIASES = frozenset({"production", "prod", "prd", "live", "production-readonly", "prod-readonly"})
SENSITIVE_LEVEL = "SENSITIVE"


def finding(rule, code, severity, target, msg):
    return {"rule": rule, "code": code, "severity": severity, "target": target, "msg": msg}


def _sensitivity_map(ir):
    rank = {"SENSITIVE": 3, "INTERNAL": 2, "PUBLIC": 1}
    out = {}
    for ent in ir.get("entities", []):
        for fld in ent.get("fields", []):
            name = fld.get("name"); level = fld.get("sensitivity_level", "PUBLIC")
            if name:
                prev = out.get(name)
                if prev is None or rank.get(level, 0) > rank.get(prev, 0):
                    out[name] = level
    return out


def check_packet(packet, ir):
    findings = []
    sens = _sensitivity_map(ir)
    if packet.get("seed") is None:
        findings.append(finding(4, "MISSING_SEED", "REJECT", "run", "缺少 seed；结果不可复现"))
    target = packet.get("target_environment", "")
    if target and str(target).lower() in PRODUCTION_ALIASES:
        findings.append(finding(3, "PRODUCTION_TARGET", "REJECT", f"target_environment={target}", "目标为生产环境"))
    fields = packet.get("fields", [])
    for fld in fields:
        fname = fld.get("name", "<no name>")
        level = sens.get(fname)
        value = fld.get("value"); policy = fld.get("masking_policy")
        masked = fld.get("masked", False); logged = fld.get("logged", False); ir_bound = fld.get("ir_bound", False)
        if level == SENSITIVE_LEVEL:
            if not policy:
                findings.append(finding(1, "SENSITIVE_NO_POLICY", "REJECT", fname, f"SENSITIVE 字段缺少 masking_policy"))
            elif policy not in VALID_MASKING_POLICIES:
                findings.append(finding(1, "INVALID_MASKING_POLICY", "REJECT", fname, f"policy {policy!r} 无效"))
            if value is not None and not masked:
                if logged:
                    findings.append(finding(2, "PLAINTEXT_IN_LOG", "REJECT", fname, f"SENSITIVE 值在 logged 字段中未脱敏"))
                if ir_bound:
                    findings.append(finding(2, "PLAINTEXT_IN_IR", "REJECT", fname, f"SENSITIVE 值在 IR 绑定字段中未脱敏"))
    has_reject = any(x["severity"] == "REJECT" for x in findings)
    return {"skill": "16", "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "run_id": packet.get("run_id"), "target_environment": packet.get("target_environment"),
            "total_fields": len(fields),
            "sensitive_fields": sum(1 for f in fields if sens.get(f.get("name")) == SENSITIVE_LEVEL),
            "total_findings": len(findings), "findings": findings,
            "verdict": "REJECT" if has_reject else ("PASS" if fields else "REJECT"),
            "routing": "REJECT -> 严禁注入" if has_reject else "PASS -> 可以注入"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--packet", required=True); p.add_argument("--ir", required=True); p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        packet = json.load(open(args.packet)); ir = json.load(open(args.ir))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"读取输入失败：{e}"}), file=sys.stderr); return 3
    result = check_packet(packet, ir)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out: open(args.out, "w").write(out)
    else: print(out)
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
