#!/usr/bin/env python3
"""
Test Plan 结构校验器。

四项检查（见 references/plan_rules.md）：
  1. PHASE_CYCLE：phase 依赖图必须无环（Kahn 算法）。
  2. MISSING_ENTRY_GATE / MISSING_EXIT_GATE：每个 phase 必须同时声明两个 gate。
  3. BACKWARD_CROSS_PHASE_DEP：任务不得依赖更晚的 phase。
  4. EMPTY_PHASE / MISSING_PHASE_ID：每个 phase 必须有 id 且至少 1 个任务。

只校验 plan 结构。Gate 的*真实性*由下游覆盖率分析器评估；
本检查器只核实 gate 是否存在。

CLI：
  python plan_check.py --plan path/to/plan.json [--out path]

退出码：0 PASS | 2 REJECT | 3 输入无效
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from collections import defaultdict, deque


def finding(check, code, target, msg, severity="REJECT"):
    return {"check": check, "code": code, "severity": severity, "target": target, "msg": msg}


def _topo_sort(phases):
    """对 depends_on_phases 执行 Kahn 算法。返回 (顺序, 环或_None)。"""
    phase_ids = {p.get("phase_id") for p in phases if p.get("phase_id")}
    adj = defaultdict(list)
    in_deg = defaultdict(int)
    for p in phases:
        pid = p.get("phase_id")
        if not pid:
            continue
        for dep in p.get("depends_on_phases", []) or []:
            if dep in phase_ids:  # 悬空依赖单独上报
                adj[dep].append(pid)
                in_deg[pid] += 1
    queue = deque(sorted(pid for pid in phase_ids if in_deg[pid] == 0))
    order = []
    while queue:
        cur = queue.popleft()
        order.append(cur)
        for nxt in sorted(adj[cur]):
            in_deg[nxt] -= 1
            if in_deg[nxt] == 0:
                queue.append(nxt)
    if len(order) == len(phase_ids):
        return order, None
    remaining = {pid for pid in phase_ids if pid not in set(order)}
    return order, _find_cycle(remaining, adj)


def _find_cycle(remaining, adj):
    """在无法完成拓扑排序的子图中找一个环。"""
    visited = set()
    stack = []

    def dfs(node):
        if node in stack:
            return stack[stack.index(node):] + [node]
        if node in visited:
            return None
        visited.add(node)
        stack.append(node)
        for nxt in sorted(adj[node]):
            if nxt in remaining:
                found = dfs(nxt)
                if found:
                    return found
        stack.pop()
        return None

    for start in sorted(remaining):
        found = dfs(start)
        if found:
            return found
    return sorted(remaining)[:1]


def check_plan(payload):
    """校验一份 Test Plan。返回 findings 列表。"""
    findings = []
    if not isinstance(payload, dict):
        return [finding(0, "INVALID_PLAN_PACKET", "root", "plan 根节点必须是对象")]
    raw_phases = payload.get("phases", [])
    if not isinstance(raw_phases, list):
        return [finding(0, "INVALID_PLAN_PACKET", "phases", "phases 必须是数组")]
    phases = [p for p in raw_phases if isinstance(p, dict)]
    if len(phases) != len(raw_phases):
        findings.append(finding(4, "INVALID_PLAN_PACKET", "phases", "每个 phase 必须是对象"))
    # 空 plan 证明不了任何东西；缺少 phase 就是缺少证据。
    if not phases:
        findings.append(finding(4, "EMPTY_PLAN", "phases", "plan 未声明任何 phase"))

    # 检查 4：phase 标识与非空性
    seen_ids = set()
    listed_order = []
    for index, phase in enumerate(phases):
        pid = phase.get("phase_id")
        if not pid:
            findings.append(finding(4, "MISSING_PHASE_ID", f"phases[{index}]", "phase 缺少 phase_id"))
        else:
            if pid in seen_ids:
                findings.append(
                    finding(4, "DUPLICATE_PHASE_ID", pid, f"phase_id {pid!r} 出现多次")
                )
            seen_ids.add(pid)
            listed_order.append(pid)
        target = pid or f"phases[{index}]"
        if not phase.get("tasks"):
            findings.append(finding(4, "EMPTY_PHASE", target, "phase 没有任何任务；会虚增表面工作量"))
        # 检查 2：gate 是否存在
        if not phase.get("entry_gate"):
            findings.append(finding(2, "MISSING_ENTRY_GATE", target, "phase 缺少 entry_gate"))
        if not phase.get("exit_gate"):
            findings.append(finding(2, "MISSING_EXIT_GATE", target, "phase 缺少 exit_gate"))

    phase_ids = {p.get("phase_id") for p in phases if p.get("phase_id")}
    for phase in phases:
        pid = phase.get("phase_id") or "?"
        for dep in phase.get("depends_on_phases", []) or []:
            if dep not in phase_ids:
                findings.append(
                    finding(1, "DANGLING_PHASE_DEPENDENCY", pid, f"depends_on_phases {dep!r} 不在 plan 中")
                )

    # 检查 1：无环。由图计算得出——绝不采用调用方提供的
    # "has_circular_dependency" 标志。
    order, cycle = _topo_sort(phases)
    if cycle:
        findings.append(finding(1, "PHASE_CYCLE", "graph", f"phase 依赖成环：{' -> '.join(cycle)}"))

    # 检查 3：任务不得依赖更晚的 phase（按声明顺序的启发式判断）。
    position = {pid: i for i, pid in enumerate(listed_order)}
    for phase in phases:
        pid = phase.get("phase_id")
        if pid not in position:
            continue
        tasks = phase.get("tasks") or []
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            if not isinstance(task, dict):
                continue
            dep = task.get("phase_dependency")
            if not dep:
                continue
            tid = task.get("task_id", "?")
            if dep not in position:
                findings.append(
                    finding(3, "DANGLING_PHASE_DEPENDENCY", tid, f"phase_dependency {dep!r} 不在 plan 中")
                )
            elif position[dep] >= position[pid]:
                findings.append(
                    finding(
                        3,
                        "BACKWARD_CROSS_PHASE_DEP",
                        tid,
                        f"{pid!r} 中的任务依赖 {dep!r}，而它并不更早；依赖不可满足",
                    )
                )

    return findings


def check_plan_report(payload):
    """把 findings 列表包装为 verdict 信封。"""
    findings = check_plan(payload)
    has_reject = any(f["severity"] == "REJECT" for f in findings)
    order, cycle = (None, None)
    if isinstance(payload, dict) and isinstance(payload.get("phases"), list):
        order, cycle = _topo_sort([p for p in payload["phases"] if isinstance(p, dict)])
    return {
        "skill": "25",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "phase_order": order if not cycle else None,
        "total_findings": len(findings),
        "findings": findings,
        "verdict": "REJECT" if has_reject else "PASS",
        "routing": "PASS -> 按 phase_order 执行各 phase；REJECT -> 修复 plan 结构",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Test Plan 结构校验器")
    p.add_argument("--plan", required=True, help="Test Plan JSON")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        with open(args.plan, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"读取输入失败：{e}"}), file=sys.stderr)
        return 3
    result = check_plan_report(payload)
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
