#!/usr/bin/env python3
"""状态机抽取检查器。"""

from __future__ import annotations
import argparse
import datetime as _dt
import json
import sys


def finding(code, target, msg):
    return {"code": code, "severity": "REJECT", "target": target, "msg": msg}


def check_state_machines(packet):
    findings = []
    if not isinstance(packet, dict):
        packet = {}
        findings.append(
            finding(
                "INVALID_STATE_MACHINE_PACKET",
                "root",
                "状态机 packet 根节点必须是对象",
            )
        )
    raw_sms = packet.get("state_machines", []) or []
    if not isinstance(raw_sms, list):
        findings.append(
            finding(
                "INVALID_STATE_MACHINE_COLLECTION",
                "state_machines",
                "state_machines 必须是数组",
            )
        )
        raw_sms = []
    raw_entity_ids = packet.get("known_entity_ids", []) or []
    if not isinstance(raw_entity_ids, list):
        findings.append(
            finding(
                "INVALID_ENTITY_ID_COLLECTION",
                "known_entity_ids",
                "known_entity_ids 必须是数组",
            )
        )
        raw_entity_ids = []
    if any(
        not isinstance(entity_id, str) or not entity_id for entity_id in raw_entity_ids
    ):
        findings.append(
            finding(
                "INVALID_ENTITY_ID_COLLECTION",
                "known_entity_ids",
                "known_entity_ids 必须是非空字符串",
            )
        )
    known_entity_ids = {
        entity_id
        for entity_id in raw_entity_ids
        if isinstance(entity_id, str) and entity_id
    }
    sms = []
    for index, sm in enumerate(raw_sms):
        if not isinstance(sm, dict):
            findings.append(
                finding(
                    "INVALID_STATE_MACHINE",
                    f"state_machines[{index}]",
                    "状态机必须是对象",
                )
            )
        else:
            sms.append(sm)

    if sms and not known_entity_ids:
        findings.append(
            finding(
                "EMPTY_ENTITY_SET",
                "known_entity_ids",
                "实体集合非空才能绑定状态机",
            )
        )

    for sm in sms:
        sid = sm.get("sm_id", "<no id>")
        # 检查 2：绑定到实体
        eid = sm.get("entity_id")
        if not isinstance(eid, str) or not eid:
            findings.append(
                finding(
                    "UNBOUND_STATE_MACHINE",
                    sid,
                    "状态机的 entity_id 必须是非空字符串",
                )
            )
        elif known_entity_ids and eid not in known_entity_ids:
            findings.append(
                finding(
                    "UNBOUND_STATE_MACHINE",
                    sid,
                    f"entity_id {eid!r} 不在已知实体中",
                )
            )
        # 显式 initial state、逐 transition 的 guard、端点有效性与可达性。
        raw_states = sm.get("states", []) or []
        if not isinstance(raw_states, list) or any(
            not isinstance(state, str) for state in raw_states
        ):
            findings.append(
                finding("INVALID_STATE_SET", sid, "states 必须是字符串数组")
            )
            raw_states = []
        declared_states = set(raw_states)
        initial_state = sm.get("initial_state")
        if not declared_states:
            findings.append(
                finding(
                    "EMPTY_STATE_SET", sid, "状态机的 states[] 不能为空"
                )
            )
        if not isinstance(initial_state, str) or not initial_state:
            findings.append(
                finding(
                    "MISSING_INITIAL_STATE",
                    sid,
                    "initial_state 必须是非空字符串",
                )
            )
        elif initial_state not in declared_states:
            findings.append(
                finding(
                    "INITIAL_STATE_NOT_DECLARED",
                    sid,
                    f"initial_state {initial_state!r} 不在声明的 states 中",
                )
            )
        seen_transitions = set()
        adjacency = {state: set() for state in declared_states}
        raw_transitions = sm.get("transitions", []) or []
        if not isinstance(raw_transitions, list):
            findings.append(
                finding(
                    "INVALID_TRANSITION_COLLECTION", sid, "transitions 必须是数组"
                )
            )
            raw_transitions = []
        for i, tr in enumerate(raw_transitions):
            if not isinstance(tr, dict):
                findings.append(
                    finding(
                        "INVALID_TRANSITION",
                        f"{sid}.transitions[{i}]",
                        "transition 必须是对象",
                    )
                )
                continue
            # guard 必须显式存在（键必须存在，即使值为 null）
            if "guard" not in tr:
                findings.append(
                    finding(
                        "MISSING_GUARD",
                        f"{sid}.transitions[{i}]",
                        "transition 缺少 'guard' 键；若无 guard 请显式标注为 null",
                    )
                )
            frm = tr.get("from")
            to = tr.get("to")
            if not isinstance(frm, str) or not frm or not isinstance(to, str) or not to:
                findings.append(
                    finding(
                        "MISSING_TRANSITION_ENDPOINT",
                        f"{sid}.transitions[{i}]",
                        "transition.from 与 transition.to 为必填项",
                    )
                )
                continue
            signature = (frm, to, repr(tr.get("guard")))
            if signature in seen_transitions:
                findings.append(
                    finding(
                        "DUPLICATE_TRANSITION",
                        f"{sid}.transitions[{i}]",
                        f"transition {frm!r}->{to!r} 与已有 guard 重复",
                    )
                )
            seen_transitions.add(signature)
            # states[] 为空也不能跳过端点校验。
            for key in ("from", "to"):
                st = tr.get(key)
                if st and st not in declared_states:
                    findings.append(
                        finding(
                            "STATE_NOT_IN_DECLARED_SET",
                            f"{sid}:{st}",
                            f"transition.{key} {st!r} 不在声明的 states {sorted(declared_states)} 中",
                        )
                    )
            if frm in declared_states and to in declared_states:
                adjacency[frm].add(to)

        if isinstance(initial_state, str) and initial_state in declared_states:
            reached = {initial_state}
            frontier = [initial_state]
            while frontier:
                current = frontier.pop()
                for target in adjacency[current] - reached:
                    reached.add(target)
                    frontier.append(target)
            for unreachable in sorted(declared_states - reached):
                findings.append(
                    finding(
                        "UNREACHABLE_STATE",
                        f"{sid}:{unreachable}",
                        f"状态 {unreachable!r} 无法从 {initial_state!r} 到达",
                    )
                )

    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {
        "skill": "04",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "total_state_machines": len(sms),
        "total_findings": len(findings),
        "findings": findings,
        "verdict": "REJECT" if has_reject else ("PASS" if sms else "REJECT"),
        "routing": "PASS -> 状态机可进入融合；REJECT -> 重新抽取被标记的状态机",
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--packet", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        with open(args.packet, encoding="utf-8") as handle:
            packet = json.load(handle)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"读取输入失败：{e}"}), file=sys.stderr)
        return 3
    result = check_state_machines(packet)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    try:
        if args.out:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(out)
        else:
            print(out)
    except OSError as e:
        print(json.dumps({"error": f"写入输出失败：{e}"}), file=sys.stderr)
        return 3
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
