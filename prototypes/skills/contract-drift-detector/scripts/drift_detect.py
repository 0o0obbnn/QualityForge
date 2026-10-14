#!/usr/bin/env python3
"""
契约漂移检测器。把观察值与契约比对并分类为 COMPATIBLE 或 BREAKING；
歧义变更默认按 BREAKING 处理。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys

WIDENING = {
    ("int", "str"): True,
    ("int", "float"): True,
    ("bool", "str"): True,
    ("VARCHAR", "TEXT"): True,
    ("INTEGER", "BIGINT"): True,
}


def finding(kind, severity, target, msg):
    return {"drift_kind": kind, "severity": severity, "target": target, "msg": msg}


def _type_change_compatible(old, new):
    if old == new:
        return True
    if WIDENING.get((old, new)):
        return True
    if WIDENING.get((new, old)):
        return False
    return None


def _schema_fields(schema):
    props = (schema or {}).get("properties") or {}
    if isinstance(props, dict):
        return {k: v.get("type", "?") for k, v in props.items() if isinstance(v, dict)}
    return {}


def _state_set(raw, side, sid, findings):
    """把声明的状态列表规整为集合，同时报告畸形输入。

    裸字符串绝不能被静默拆成字符集：对漂移检测器而言，畸形快照
    产出 NO_DRIFT 正是本 skill 要杜绝的假阴性。
    """
    if isinstance(raw, list):
        bad = [s for s in raw if not isinstance(s, str)]
        if bad:
            findings.append(
                finding(
                    "MALFORMED_SNAPSHOT",
                    "BREAKING",
                    f"{sid}.{side}.states",
                    f"states 必须是字符串数组；实际含 {bad!r}",
                )
            )
        return {s for s in raw if isinstance(s, str)}
    findings.append(
        finding(
            "MALFORMED_SNAPSHOT",
            "BREAKING",
            f"{sid}.{side}.states",
            f"states 必须是数组，实际为 {type(raw).__name__}；无法判定漂移",
        )
    )
    return set()


def _transition_keys(raw, side, sid, findings):
    """构建迁移键集合，同时报告非对象条目。"""
    if not isinstance(raw, list):
        findings.append(
            finding(
                "MALFORMED_SNAPSHOT",
                "BREAKING",
                f"{sid}.{side}.transitions",
                f"transitions 必须是数组，实际为 {type(raw).__name__}；无法判定漂移",
            )
        )
        return set()
    keys = set()
    for index, t in enumerate(raw):
        if not isinstance(t, dict):
            findings.append(
                finding(
                    "MALFORMED_SNAPSHOT",
                    "BREAKING",
                    f"{sid}.{side}.transitions[{index}]",
                    f"transition 必须是对象，实际为 {t!r}",
                )
            )
            continue
        keys.add(f"{t.get('from')}->{t.get('to')}")
    return keys


def detect_interface_drift(contract, observed):
    f = []
    cid = contract.get("contract_id", "<no id>")
    for side in ("response_schema", "request_schema"):
        c_fields = _schema_fields(contract.get(side))
        o_fields = _schema_fields(observed.get(side))
        c_names = set(c_fields)
        o_names = set(o_fields)
        for name in sorted(o_names - c_names):
            f.append(
                finding(
                    "FIELD_ADDED",
                    "COMPATIBLE",
                    f"{cid}.{side}.{name}",
                    f"新增字段 {name!r}；additive 兼容",
                )
            )
        for name in sorted(c_names - o_names):
            f.append(
                finding(
                    "FIELD_REMOVED",
                    "BREAKING",
                    f"{cid}.{side}.{name}",
                    f"字段 {name!r} 缺失；破坏消费方",
                )
            )
        for name in sorted(c_names & o_names):
            old_t = c_fields[name]
            new_t = o_fields[name]
            if old_t == new_t:
                continue
            compat = _type_change_compatible(old_t, new_t)
            if compat is True:
                f.append(
                    finding(
                        "TYPE_WIDENED",
                        "COMPATIBLE",
                        f"{cid}.{side}.{name}",
                        f"类型放宽 {old_t!r}->{new_t!r}",
                    )
                )
            elif compat is False:
                f.append(
                    finding(
                        "TYPE_NARROWED",
                        "BREAKING",
                        f"{cid}.{side}.{name}",
                        f"类型收窄 {old_t!r}->{new_t!r}",
                    )
                )
            else:
                f.append(
                    finding(
                        "TYPE_CHANGED",
                        "BREAKING",
                        f"{cid}.{side}.{name}",
                        f"类型变更 {old_t!r}->{new_t!r}；歧义按 breaking 处理",
                    )
                )
    return f


def detect_state_machine_drift(contract, observed):
    f = []
    sid = contract.get("sm_id", "<no id>")
    c_states = _state_set(contract.get("states", []), "contract", sid, f)
    o_states = _state_set(observed.get("states", []), "observed", sid, f)
    for s in sorted(o_states - c_states):
        f.append(finding("STATE_ADDED", "COMPATIBLE", f"{sid}:{s}", f"新增状态 {s!r}"))
    for s in sorted(c_states - o_states):
        f.append(finding("STATE_REMOVED", "BREAKING", f"{sid}:{s}", f"状态 {s!r} 缺失"))
    c_trans = _transition_keys(contract.get("transitions", []), "contract", sid, f)
    o_trans = _transition_keys(observed.get("transitions", []), "observed", sid, f)
    for t in sorted(o_trans - c_trans):
        f.append(
            finding("TRANSITION_ADDED", "COMPATIBLE", f"{sid}:{t}", f"新增迁移 {t!r}")
        )
    for t in sorted(c_trans - o_trans):
        f.append(
            finding(
                "TRANSITION_REMOVED",
                "BREAKING",
                f"{sid}:{t}",
                f"迁移 {t!r} 缺失",
            )
        )
    return f


def detect(contract, observed):
    # 非对象包是畸形快照，不是「无漂移」。
    if not isinstance(contract, dict):
        return {"error": "contract 必须是对象"}
    if not isinstance(observed, dict):
        return {"error": "observed 必须是对象"}
    ctype = contract.get("type")
    if ctype == "interface_contract":
        findings = detect_interface_drift(contract, observed)
    elif ctype == "state_machine":
        findings = detect_state_machine_drift(contract, observed)
    else:
        return {"error": f"未知契约类型 {ctype!r}"}
    has_breaking = any(x["severity"] == "BREAKING" for x in findings)
    has_compatible = any(x["severity"] == "COMPATIBLE" for x in findings)
    verdict = (
        "BREAKING_DRIFT"
        if has_breaking
        else ("COMPATIBLE_DRIFT" if has_compatible else "NO_DRIFT")
    )
    return {
        "skill": "25",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "contract_type": ctype,
        "contract_id": contract.get("contract_id") or contract.get("sm_id"),
        "verdict": verdict,
        "total_findings": len(findings),
        "breaking_count": sum(1 for x in findings if x["severity"] == "BREAKING"),
        "compatible_count": sum(1 for x in findings if x["severity"] == "COMPATIBLE"),
        "findings": findings,
        "routing": {
            "NO_DRIFT": "继续",
            "COMPATIBLE_DRIFT": "继续并告警",
            "BREAKING_DRIFT": "阻断并转人工检查点",
        }[verdict],
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--contract", required=True)
    p.add_argument("--observed", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        with open(args.contract, encoding="utf-8") as handle:
            contract = json.load(handle)
        with open(args.observed, encoding="utf-8") as handle:
            observed = json.load(handle)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr)
        return 3
    result = detect(contract, observed)
    if "error" in result:
        print(json.dumps(result), file=sys.stderr)
        return 3
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
    return {"NO_DRIFT": 0, "COMPATIBLE_DRIFT": 1, "BREAKING_DRIFT": 2}[
        result["verdict"]
    ]


if __name__ == "__main__":
    sys.exit(main())
