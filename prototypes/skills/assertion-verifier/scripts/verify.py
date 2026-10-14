#!/usr/bin/env python3
"""
Assertion 验证器——三阶段流水线中的确定性阶段。

  static-check   阶段 1：assertion 与 IR 契约一致性。
  mutation-score 阶段 3 裁定：给定 killed/total + 风险等级，计算得分。

mutation gate 的机制（变异体生成 + 执行）不在本脚本内；
那需要真实系统。本脚本只消费统计结果。
"""
from __future__ import annotations
import argparse, datetime as _dt, json, sys, re

MUTATION_THRESHOLD = {"low": 0.5, "medium": 0.7, "high": 0.85}
DEGRADE_PENALTY = 0.05


def _index_ir(ir):
    contracts = {c["contract_id"]: c for c in ir.get("interface_contracts", [])}
    entities = {e["entity_id"]: e for e in ir.get("entities", [])}
    rules = {r["rule_id"]: r for r in ir.get("business_rules", [])}
    state_machines = {sm["sm_id"]: sm for sm in ir.get("state_machines", [])}
    return {"contracts": contracts, "entities": entities, "rules": rules, "state_machines": state_machines}


def _response_fields(contract):
    schema = contract.get("response_schema") or {}
    props = schema.get("properties") or schema.get("fields") or {}
    if isinstance(props, dict): return set(props.keys())
    if isinstance(props, list): return {p.get("name") for p in props if isinstance(p, dict)}
    return set()


def _referenced_fields(assertion):
    text = str(assertion.get("target", ""))
    tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
    stop = {"body", "response", "request", "header", "headers"}
    return tokens - stop


def static_check_one(assertion, irx):
    v = []
    aid = assertion.get("assertion_id", "<no-id>")
    rule_id = assertion.get("rule_id"); req_id = assertion.get("req_id")
    contract_id = assertion.get("contract_id")
    if not rule_id:
        v.append({"assertion_id": aid, "severity": "REJECT", "code": "ORPHAN_NO_RULE", "msg": "缺少 rule_id"})
    elif rule_id not in irx["rules"]:
        v.append({"assertion_id": aid, "severity": "REJECT", "code": "RULE_NOT_IN_IR", "msg": f"rule_id {rule_id} 不在 IR 中"})
    if not req_id:
        v.append({"assertion_id": aid, "severity": "REJECT", "code": "ORPHAN_NO_REQ", "msg": "缺少 req_id"})
    if contract_id and contract_id in irx["contracts"]:
        valid = _response_fields(irx["contracts"][contract_id])
        if valid:
            referenced = _referenced_fields(assertion)
            unknown = referenced - valid
            if unknown:
                v.append({"assertion_id": aid, "severity": "REJECT", "code": "FIELD_NOT_IN_CONTRACT", "msg": f"字段不在 contract 中：{sorted(unknown)}"})
    sm_id = assertion.get("state_machine_id"); target_state = assertion.get("expected_state")
    if sm_id and target_state:
        sm = irx["state_machines"].get(sm_id)
        if not sm:
            v.append({"assertion_id": aid, "severity": "REJECT", "code": "SM_NOT_IN_IR", "msg": f"状态机 {sm_id} 不在 IR 中"})
        elif target_state not in set(sm.get("states", [])):
            v.append({"assertion_id": aid, "severity": "REJECT", "code": "INVALID_STATE", "msg": f"state {target_state} 无效"})
    return v


def static_check(assertions, ir):
    irx = _index_ir(ir)
    all_violations = []; clean = 0
    for a in assertions:
        vs = static_check_one(a, irx)
        if vs: all_violations.extend(vs)
        else: clean += 1
    has_reject = any(v["severity"] == "REJECT" for v in all_violations)
    return {"stage": 1, "stage_name": "static_check", "total_assertions": len(assertions),
            "clean_assertions": clean, "violations": all_violations,
            "verdict": "REJECT" if has_reject else ("PASS" if assertions else "REJECT"),
            "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat()}


def mutation_score(killed, total, risk_class, *, stage2_status="ran"):
    if risk_class not in MUTATION_THRESHOLD:
        raise ValueError(f"risk_class 必须是 {list(MUTATION_THRESHOLD)} 之一")
    if total <= 0:
        return {"stage": 3, "stage_name": "mutation_gate", "killed": killed, "total": total,
                "mutation_score": None, "risk_class": risk_class, "threshold": None,
                "verdict": "REJECT", "reason": "无变异体（total=0）；gate 未运行"}
    if killed < 0 or killed > total:
        raise ValueError(f"killed={killed} 超出范围 [0, {total}]")
    score = killed / total
    threshold = MUTATION_THRESHOLD[risk_class]
    effective = threshold
    note = ""
    if stage2_status == "skipped":
        effective = round(threshold + DEGRADE_PENALTY, 3)
        note = f"（stage2 跳过；阈值上调 -> {effective}）"
    passed = score >= effective
    return {"stage": 3, "stage_name": "mutation_gate", "killed": killed, "total": total,
            "mutation_score": round(score, 3), "risk_class": risk_class,
            "threshold": effective, "base_threshold": threshold, "stage2_status": stage2_status,
            "verdict": "PASS" if passed else "REJECT",
            "reason": f"得分 {score:.2f} {'>=' if passed else '<'} {effective}{note}；{'击杀充分' if passed else '虚假覆盖'}"}


def _cmd_static_check(args):
    try:
        assertions = json.load(open(args.assertions)); ir = json.load(open(args.ir))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr); return 3
    if isinstance(assertions, dict): assertions = [assertions]
    result = static_check(assertions, ir)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out: open(args.out, "w").write(out)
    else: print(out)
    return 2 if result["verdict"] == "REJECT" else 0


def _cmd_mutation_score(args):
    try:
        result = mutation_score(args.killed, args.total, args.risk_class, stage2_status=args.stage2_status)
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr); return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["verdict"] == "REJECT" else 0


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("static-check")
    s1.add_argument("--assertions", required=True); s1.add_argument("--ir", required=True); s1.add_argument("--out", default=None)
    s1.set_defaults(func=_cmd_static_check)
    s3 = sub.add_parser("mutation-score")
    s3.add_argument("--killed", type=int, required=True); s3.add_argument("--total", type=int, required=True)
    s3.add_argument("--risk-class", required=True, choices=list(MUTATION_THRESHOLD))
    s3.add_argument("--stage2-status", default="ran", choices=["ran", "skipped"])
    s3.set_defaults(func=_cmd_mutation_score)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
