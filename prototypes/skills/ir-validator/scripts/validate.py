#!/usr/bin/env python3
"""
测试 IR 校验器——六个确定性检查族。

检查项：schema 完整性、出处绑定、confidence 分层、
冲突解决、状态机可达性、实体字段健全性。
总体 verdict（PASS / PASS_WITH_REVIEW / REJECT）取各族的最差结果。
"""

from __future__ import annotations
import argparse
import datetime as _dt
import json
import math
import re
import sys
from collections import defaultdict

FROZEN_V1_MODELS = frozenset(
    {
        "requirements",
        "entities",
        "business_rules",
        "state_machines",
        "interface_contracts",
        "constraints",
    }
)
ALLOWED_TOPLEVEL = FROZEN_V1_MODELS | {"ir_version"}
FROZEN_VERSION_PREFIX = "1.0"
FROZEN_VERSION_PATTERN = re.compile(r"^1\.0(?:\.\d+)?$")
VALID_SENSITIVITY = frozenset({"PUBLIC", "INTERNAL", "SENSITIVE"})
VALID_VALIDATION_STATUS = frozenset({"PENDING", "VALIDATED", "NEED_HUMAN_REVIEW"})


def finding(family, code, severity, target, msg):
    return {
        "family": family,
        "code": code,
        "severity": severity,
        "target": target,
        "msg": msg,
    }


def _required_missing(item, required):
    return [f for f in required if f not in item or item[f] in (None, "", [])]


def _items(ir, model_class):
    value = ir.get(model_class, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def check_schema(ir):
    f = []
    ver = ir.get("ir_version")
    if not ver:
        f.append(
            finding(
                "schema", "MISSING_IR_VERSION", "REJECT", "root", "缺少 ir_version"
            )
        )
    elif not FROZEN_VERSION_PATTERN.fullmatch(str(ver)):
        f.append(
            finding(
                "schema",
                "UNKNOWN_IR_VERSION",
                "REJECT",
                "root",
                f"ir_version {ver!r} 不是冻结的 {FROZEN_VERSION_PREFIX}.x",
            )
        )
    extra = set(ir.keys()) - ALLOWED_TOPLEVEL
    if extra:
        f.append(
            finding(
                "schema",
                "UNDEFINED_MODEL_CLASS",
                "REJECT",
                "root",
                f"顶层 key 不在冻结范围内：{sorted(extra)}",
            )
        )
    for model_class in sorted(FROZEN_V1_MODELS):
        if model_class not in ir:
            f.append(
                finding(
                    "schema",
                    "MISSING_REQUIRED_MODEL_CLASS",
                    "REJECT",
                    "root",
                    f"必须存在顶层模型类 {model_class!r}",
                )
            )
        elif not isinstance(ir[model_class], list):
            f.append(
                finding(
                    "schema",
                    "INVALID_MODEL_CLASS_TYPE",
                    "REJECT",
                    model_class,
                    "模型类必须是数组",
                )
            )
        else:
            for index, item in enumerate(ir[model_class]):
                if not isinstance(item, dict):
                    f.append(
                        finding(
                            "schema",
                            "INVALID_MODEL_ITEM",
                            "REJECT",
                            f"{model_class}[{index}]",
                            "模型项必须是对象",
                        )
                    )
    if isinstance(ir.get("requirements"), list) and not ir["requirements"]:
        f.append(
            finding(
                "schema",
                "EMPTY_REQUIREMENTS",
                "REJECT",
                "requirements",
                "IR 必须包含至少一条 requirement",
            )
        )
    reqs = [
        (
            "requirements",
            "req_id",
            ["req_id", "title", "description", "validation_status"],
        ),
        ("business_rules", "rule_id", ["rule_id", "condition", "action", "source"]),
        ("entities", "entity_id", ["entity_id", "name", "fields"]),
        ("interface_contracts", "contract_id", ["contract_id", "endpoint", "method"]),
        ("constraints", "constraint_id", ["constraint_id", "target", "expression"]),
    ]
    for cls, id_key, required in reqs:
        for item in _items(ir, cls):
            mid = item.get(id_key, f"<no {id_key}>")
            for miss in _required_missing(item, required):
                f.append(
                    finding(
                        "schema",
                        "MISSING_REQUIRED_FIELD",
                        "REJECT",
                        f"{cls}:{mid}",
                        f"缺少必填字段 {miss!r}",
                    )
                )
            if cls == "requirements":
                vs = item.get("validation_status")
                if vs and vs not in VALID_VALIDATION_STATUS:
                    f.append(
                        finding(
                            "schema",
                            "INVALID_VALIDATION_STATUS",
                            "REJECT",
                            f"requirements:{mid}",
                            f"validation_status {vs!r} 无效",
                        )
                    )
    for sm in _items(ir, "state_machines"):
        sid = sm.get("sm_id", "<no sm_id>")
        for miss in _required_missing(
            sm, ["sm_id", "entity_id", "initial_state", "states", "transitions"]
        ):
            f.append(
                finding(
                    "schema",
                    "MISSING_REQUIRED_FIELD",
                    "REJECT",
                    f"state_machines:{sid}",
                    f"缺少必填字段 {miss!r}",
                )
            )
    return f


def check_provenance(ir):
    f = []
    for cls, id_key in [
        ("business_rules", "rule_id"),
        ("requirements", "req_id"),
        ("constraints", "constraint_id"),
    ]:
        for item in _items(ir, cls):
            mid = item.get(id_key, "<no id>")
            st = item.get("source_trace")
            if st in (None, ""):
                f.append(
                    finding(
                        "provenance",
                        "MISSING_SOURCE_TRACE",
                        "REJECT",
                        f"{cls}:{mid}",
                        "缺少 source_trace",
                    )
                )
    return f


def check_confidence(ir):
    f = []
    buckets = {"ge_0.9": 0, "0.7_0.9": 0, "lt_0.7": 0}
    for cls, id_key in [("business_rules", "rule_id"), ("requirements", "req_id")]:
        for item in _items(ir, cls):
            mid = item.get(id_key, "<no id>")
            c = item.get("confidence")
            if c is None:
                f.append(
                    finding(
                        "confidence",
                        "MISSING_CONFIDENCE",
                        "REJECT",
                        f"{cls}:{mid}",
                        "缺少 confidence 字段",
                    )
                )
                continue
            if (
                isinstance(c, bool)
                or not isinstance(c, (int, float))
                or not math.isfinite(c)
            ):
                f.append(
                    finding(
                        "confidence",
                        "INVALID_CONFIDENCE_TYPE",
                        "REJECT",
                        f"{cls}:{mid}",
                        f"confidence {c!r} 不是数字",
                    )
                )
                continue
            if not (0.0 <= c <= 1.0):
                f.append(
                    finding(
                        "confidence",
                        "CONFIDENCE_OUT_OF_RANGE",
                        "REJECT",
                        f"{cls}:{mid}",
                        f"confidence {c} 不在 [0,1] 内",
                    )
                )
                continue
            if c >= 0.9:
                buckets["ge_0.9"] += 1
            elif c >= 0.7:
                buckets["0.7_0.9"] += 1
            else:
                buckets["lt_0.7"] += 1
    total = sum(buckets.values())
    if total > 0:
        if buckets["ge_0.9"] / total > 0.9:
            f.append(
                finding(
                    "confidence",
                    "SUSPICIOUS_DISTRIBUTION",
                    "REVIEW",
                    "distribution",
                    f"{buckets['ge_0.9']}/{total} >= 0.9（幻觉信号）",
                )
            )
        elif buckets["lt_0.7"] / total > 0.7:
            f.append(
                finding(
                    "confidence",
                    "SUSPICIOUS_DISTRIBUTION",
                    "REVIEW",
                    "distribution",
                    f"{buckets['lt_0.7']}/{total} < 0.7",
                )
            )
    return f


def check_conflicts(ir):
    f = []
    for cls, id_key in [("business_rules", "rule_id"), ("requirements", "req_id")]:
        for item in _items(ir, cls):
            mid = item.get(id_key, "<no id>")
            if (
                item.get("conflict") is True
                and item.get("resolution_status") != "RESOLVED"
            ):
                f.append(
                    finding(
                        "conflict",
                        "UNRESOLVED_CONFLICT",
                        "REJECT",
                        f"{cls}:{mid}",
                        "conflict=true 但未解决",
                    )
                )
    return f


def check_state_machines(ir):
    f = []
    for sm in _items(ir, "state_machines"):
        sid = sm.get("sm_id", "<no sm_id>")
        raw_states = sm.get("states", [])
        if not isinstance(raw_states, list) or any(
            not isinstance(state, str) for state in raw_states
        ):
            f.append(
                finding(
                    "reachability",
                    "INVALID_STATE_SET",
                    "REJECT",
                    f"state_machines:{sid}",
                    "states 必须是字符串数组",
                )
            )
            raw_states = []
        states = set(raw_states)
        raw_transitions = sm.get("transitions", [])
        transitions = raw_transitions if isinstance(raw_transitions, list) else []
        initial_state = sm.get("initial_state")
        if not isinstance(initial_state, str) or not initial_state:
            f.append(
                finding(
                    "reachability",
                    "MISSING_INITIAL_STATE",
                    "REJECT",
                    f"state_machines:{sid}",
                    "initial_state 必须是非空字符串",
                )
            )
        elif initial_state not in states:
            f.append(
                finding(
                    "reachability",
                    "INITIAL_STATE_NOT_DECLARED",
                    "REJECT",
                    f"state_machines:{sid}",
                    f"initial_state {initial_state!r} 不在 states 中",
                )
            )
        tos = defaultdict(set)
        froms = set()
        seen_transitions = set()
        valid_transitions = []
        for index, tr in enumerate(transitions):
            if not isinstance(tr, dict):
                f.append(
                    finding(
                        "reachability",
                        "INVALID_TRANSITION",
                        "REJECT",
                        f"state_machines:{sid}.transitions[{index}]",
                        "transition 必须是对象",
                    )
                )
                continue
            frm = tr.get("from")
            to = tr.get("to")
            if not isinstance(frm, str) or not frm or not isinstance(to, str) or not to:
                f.append(
                    finding(
                        "reachability",
                        "MISSING_TRANSITION_ENDPOINT",
                        "REJECT",
                        f"state_machines:{sid}.transitions[{index}]",
                        "必须提供 transition.from 和 transition.to",
                    )
                )
                continue
            valid_transitions.append(tr)
            signature = (frm, to, repr(tr.get("guard")))
            if signature in seen_transitions:
                f.append(
                    finding(
                        "reachability",
                        "DUPLICATE_TRANSITION",
                        "REJECT",
                        f"state_machines:{sid}",
                        f"重复的 transition {frm!r}->{to!r}",
                    )
                )
            seen_transitions.add(signature)
            if frm and frm not in states:
                f.append(
                    finding(
                        "reachability",
                        "UNDECLARED_TRANSITION_FROM",
                        "REJECT",
                        f"state_machines:{sid}",
                        f"from {frm!r} 不在 states 中",
                    )
                )
            if to and to not in states:
                f.append(
                    finding(
                        "reachability",
                        "UNDECLARED_TRANSITION_TO",
                        "REJECT",
                        f"state_machines:{sid}",
                        f"to {to!r} 不在 states 中",
                    )
                )
            if frm and to:
                tos[to].add(frm)
                froms.add(frm)
        if not states:
            continue
        if not isinstance(initial_state, str) or initial_state not in states:
            continue
        initial = {initial_state}
        reached = set(initial)
        frontier = list(initial)
        while frontier:
            cur = frontier.pop()
            for tr in valid_transitions:
                if tr.get("from") == cur and tr.get("to") not in reached:
                    reached.add(tr["to"])
                    frontier.append(tr["to"])
        for u in sorted(states - reached):
            f.append(
                finding(
                    "reachability",
                    "UNREACHABLE_STATE",
                    "REJECT",
                    f"state_machines:{sid}:{u}",
                    f"state {u!r} 不可达",
                )
            )
        raw_terminal_states = sm.get("terminal_states", {})
        if isinstance(raw_terminal_states, dict):
            terminal_states = set(raw_terminal_states)
        elif isinstance(raw_terminal_states, list) and all(
            isinstance(item, str) for item in raw_terminal_states
        ):
            terminal_states = set(raw_terminal_states)
        else:
            terminal_states = set()
            f.append(
                finding(
                    "reachability",
                    "INVALID_TERMINAL_STATES",
                    "REJECT",
                    f"state_machines:{sid}",
                    "terminal_states 必须是对象或字符串数组",
                )
            )
        for s in sorted(states):
            if s not in froms and s not in terminal_states:
                f.append(
                    finding(
                        "reachability",
                        "DEAD_END_NONTERMINAL",
                        "REJECT",
                        f"state_machines:{sid}:{s}",
                        f"state {s!r} 是死端且非终态",
                    )
                )
    return f


def check_entities(ir):
    f = []
    for ent in _items(ir, "entities"):
        eid = ent.get("entity_id", "<no entity_id>")
        fields = ent.get("fields", [])
        if not isinstance(fields, list):
            f.append(
                finding(
                    "entity",
                    "INVALID_FIELD_COLLECTION",
                    "REJECT",
                    f"entities:{eid}",
                    "fields 必须是数组",
                )
            )
            continue
        if not fields:
            f.append(
                finding(
                    "entity",
                    "ENTITY_NO_FIELDS",
                    "REJECT",
                    f"entities:{eid}",
                    "entity 没有 fields",
                )
            )
            continue
        for index, fld in enumerate(fields):
            if not isinstance(fld, dict):
                f.append(
                    finding(
                        "entity",
                        "INVALID_ENTITY_FIELD",
                        "REJECT",
                        f"entities:{eid}.fields[{index}]",
                        "field 必须是对象",
                    )
                )
                continue
            fname = fld.get("name", "<no name>")
            sens = fld.get("sensitivity_level")
            if sens is None or sens == "":
                f.append(
                    finding(
                        "entity",
                        "MISSING_SENSITIVITY",
                        "REJECT",
                        f"entities:{eid}.{fname}",
                        "缺少 sensitivity_level",
                    )
                )
            elif sens not in VALID_SENSITIVITY:
                f.append(
                    finding(
                        "entity",
                        "INVALID_SENSITIVITY",
                        "REJECT",
                        f"entities:{eid}.{fname}",
                        f"sensitivity {sens!r} 无效",
                    )
                )
            elif sens == "PUBLIC" and not fld.get("sensitivity_rationale"):
                f.append(
                    finding(
                        "entity",
                        "BARE_PUBLIC_NO_RATIONALE",
                        "REJECT",
                        f"entities:{eid}.{fname}",
                        "PUBLIC 但缺少 rationale",
                    )
                )
    return f


def validate(ir):
    if not isinstance(ir, dict):
        ir = {}
    families = {
        "schema": check_schema,
        "provenance": check_provenance,
        "confidence": check_confidence,
        "conflict": check_conflicts,
        "reachability": check_state_machines,
        "entity": check_entities,
    }
    all_findings = []
    by_family = {}
    for name, fn in families.items():
        fs = fn(ir)
        by_family[name] = len(fs)
        all_findings.extend(fs)
    has_reject = any(x["severity"] == "REJECT" for x in all_findings)
    has_review = any(x["severity"] == "REVIEW" for x in all_findings)
    verdict = "REJECT" if has_reject else ("PASS_WITH_REVIEW" if has_review else "PASS")
    review_tasks = [
        {"target": x["target"], "code": x["code"], "msg": x["msg"]}
        for x in all_findings
        if x["severity"] == "REVIEW"
    ]
    return {
        "skill": "05",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "ir_version_seen": ir.get("ir_version"),
        "verdict": verdict,
        "findings_by_family": by_family,
        "total_findings": len(all_findings),
        "reject_findings": sum(1 for x in all_findings if x["severity"] == "REJECT"),
        "review_findings": sum(1 for x in all_findings if x["severity"] == "REVIEW"),
        "findings": all_findings,
        "skill28_review_tasks": review_tasks,
        "routing": {
            "PASS": "发布",
            "PASS_WITH_REVIEW": "发布 + 复核清单",
            "REJECT": "暂缓",
        }[verdict],
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--ir", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        with open(args.ir, encoding="utf-8") as handle:
            ir = json.load(handle)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr)
        return 3
    if not isinstance(ir, dict):
        print(json.dumps({"error": "IR 根节点必须是 JSON 对象"}), file=sys.stderr)
        return 3
    result = validate(ir)
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
    return {"PASS": 0, "PASS_WITH_REVIEW": 1, "REJECT": 2}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
