#!/usr/bin/env python3
"""
数据需求契约检查器。对照 cases + IR 验证需求。
敏感字段交叉核对是合规钩子。
"""
from __future__ import annotations
import argparse, datetime as _dt, json, sys


def finding(code, severity, target, msg):
    return {"code": code, "severity": severity, "target": target, "msg": msg}


def _index_ir(ir):
    entities = {e["entity_id"]: e for e in ir.get("entities", [])}
    sensitive = {}
    for eid, e in entities.items():
        sensitive[eid] = {f["name"] for f in e.get("fields", []) if f.get("sensitivity_level") == "SENSITIVE"}
    entity_sm = {}; sms = {}
    for sm in ir.get("state_machines", []):
        sms[sm["sm_id"]] = sm; entity_sm[sm.get("entity_id")] = sm["sm_id"]
    return {"entities": entities, "sensitive": sensitive, "entity_sm": entity_sm, "state_machines": sms}


def _reachable_states(sm):
    states = set(sm.get("states", []))
    froms = {t["from"] for t in sm.get("transitions", []) if "from" in t}
    tos = {t["to"] for t in sm.get("transitions", []) if "to" in t}
    initial = froms - tos
    if not initial and states:
        initial = {next(iter(states))}
    reached = set(initial); frontier = list(initial)
    while frontier:
        cur = frontier.pop()
        for t in sm.get("transitions", []):
            if t.get("from") == cur and t.get("to") not in reached:
                reached.add(t["to"]); frontier.append(t["to"])
    return reached


def check_one(req, irx, cases_by_id, baselines):
    f = []
    rid = req.get("case_id", "<no case_id>")
    if rid not in cases_by_id:
        f.append(finding("ORPHAN_REQUIREMENT", "REJECT", rid, f"case_id {rid!r} 不在 cases 中"))
    case = cases_by_id.get(rid)
    if case:
        req_cat = req.get("fixture_category"); case_cat = case.get("fixture_category")
        if req_cat != case_cat:
            f.append(finding("CATEGORY_MISMATCH", "REJECT", rid, f"requirement={req_cat!r} 与 case={case_cat!r} 不一致"))
    for pre in req.get("state_preconditions", []) or []:
        eid = pre.get("entity_id"); st = pre.get("state")
        if not eid or not st:
            f.append(finding("INVALID_PRECONDITION_STATE", "REJECT", rid, f"前置条件格式错误")); continue
        sm_id = irx["entity_sm"].get(eid)
        if not sm_id:
            f.append(finding("INVALID_PRECONDITION_STATE", "REJECT", rid, f"实体 {eid!r} 没有状态机")); continue
        sm = irx["state_machines"][sm_id]
        if st not in set(sm.get("states", [])):
            f.append(finding("INVALID_PRECONDITION_STATE", "REJECT", rid, f"state {st!r} 无效"))
        elif st not in _reachable_states(sm):
            f.append(finding("UNREACHABLE_TARGET_STATE", "REJECT", rid, f"state {st!r} 不可达"))
    for ent in req.get("entities_needed", []) or []:
        eid = ent.get("entity_id"); tstate = ent.get("target_state")
        if eid and tstate:
            sm_id = irx["entity_sm"].get(eid)
            if sm_id:
                sm = irx["state_machines"][sm_id]
                if tstate not in set(sm.get("states", [])):
                    f.append(finding("UNREACHABLE_TARGET_STATE", "REJECT", rid, f"target_state {tstate!r} 对 {eid} 无效"))
                elif tstate not in _reachable_states(sm):
                    f.append(finding("UNREACHABLE_TARGET_STATE", "REJECT", rid, f"target_state {tstate!r} 不可达"))
    declared_sensitive = set(req.get("sensitive_fields", []) or [])
    for ent in req.get("entities_needed", []) or []:
        eid = ent.get("entity_id")
        if eid and eid in irx["sensitive"]:
            for m in sorted(irx["sensitive"][eid] - declared_sensitive):
                f.append(finding("MISSING_SENSITIVE_FIELD", "REJECT", f"{rid}:{eid}.{m}", f"IR 将 {eid}.{m} 标记为 SENSITIVE 但需求遗漏了它"))
    cat = req.get("fixture_category")
    if cat == "Static":
        for ent in req.get("entities_needed", []) or []:
            inst = ent.get("instance_id", "")
            if baselines and inst and inst not in baselines:
                f.append(finding("STATIC_NOT_IN_BASELINE", "REJECT", rid, f"实例 {inst!r} 不在 baseline 中"))
    elif cat in ("Dynamic", "Hybrid"):
        if not req.get("construction_steps"):
            f.append(finding("DYNAMIC_NO_STEPS", "REJECT", rid, f"{cat} 缺少 construction_steps"))
    return f


def check_requirements(requirements, ir, cases, baselines=None):
    irx = _index_ir(ir)
    cases_by_id = {c["case_id"]: c for c in cases if c.get("case_id")}
    baselines = baselines or set()
    all_findings = []; conformant = 0
    for req in requirements:
        fs = check_one(req, irx, cases_by_id, baselines)
        if fs: all_findings.extend(fs)
        else: conformant += 1
    has_reject = any(x["severity"] == "REJECT" for x in all_findings)
    return {"skill": "13", "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "total_requirements": len(requirements), "conformant": conformant,
            "total_findings": len(all_findings), "findings": all_findings,
            "verdict": "REJECT" if has_reject else ("PASS" if requirements else "REJECT"),
            "routing": "PASS -> 规划 DAG；REJECT -> 退回分析器"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--requirements", required=True); p.add_argument("--ir", required=True)
    p.add_argument("--cases", required=True); p.add_argument("--baselines", default=None); p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        reqs = json.load(open(args.requirements)); ir = json.load(open(args.ir))
        cases = json.load(open(args.cases))
        baselines = set(json.load(open(args.baselines))) if args.baselines else set()
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr); return 3
    if isinstance(reqs, dict): reqs = [reqs]
    if isinstance(cases, dict): cases = [cases]
    result = check_requirements(reqs, ir, cases, baselines)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out: open(args.out, "w").write(out)
    else: print(out)
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
