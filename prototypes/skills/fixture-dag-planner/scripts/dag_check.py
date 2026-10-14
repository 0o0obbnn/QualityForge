#!/usr/bin/env python3
"""
Fixture DAG 校验器。四项检查：
  1. ACYCLIC：拓扑排序成功（Kahn 算法）。
  2. REVERSIBLE：每个带 `creates` 的节点都声明非空 teardown。
  3. DEPS_EXIST：每个 depends_on id 都能解析到图中的节点。
  4. SCOPE_TYPE_VALID：scope 属于 {session,module,function}，type 属于 {Static,Dynamic,Hybrid}。

另含：Static 节点的 baseline 声明交叉核对。

CLI:
  python dag_check.py --dag path/to/dag.json [--out path]

退出码：0 PASS | 2 REJECT | 3 输入无效
"""
from __future__ import annotations
import argparse, datetime as _dt, json, sys
from collections import defaultdict, deque

VALID_SCOPES = frozenset({"session", "module", "function"})
VALID_TYPES = frozenset({"Static", "Dynamic", "Hybrid"})


def finding(check, code, severity, target, msg):
    return {"check": check, "code": code, "severity": severity, "target": target, "msg": msg}


def _topo_sort(nodes):
    """Kahn 算法。返回 (order, cycle_path)。
    若存在环，cycle_path 是以 node_id 列表表示的问题环。"""
    node_ids = {n["node_id"] for n in nodes}
    adj = defaultdict(list)  # 节点 -> 它指向的节点（depends_on 表示“在其后”）
    in_deg = defaultdict(int)
    for n in nodes:
        nid = n["node_id"]
        for dep in n.get("depends_on", []) or []:
            if dep in node_ids:  # 悬空依赖在检查 3 中处理
                adj[dep].append(nid)
                in_deg[nid] += 1
    # 以入度为零的节点作为起点
    queue = deque(sorted(nid for nid in node_ids if in_deg[nid] == 0))
    order = []
    while queue:
        cur = queue.popleft()
        order.append(cur)
        for nxt in sorted(adj[cur]):
            in_deg[nxt] -= 1
            if in_deg[nxt] == 0:
                queue.append(nxt)
    if len(order) == len(node_ids):
        return order, None
    # 检测到环：找一个仍在图中的节点并回溯
    remaining = {n for n in node_ids if n not in set(order)}
    # 任选一个剩余节点，沿 adj 寻找环
    cycle = _find_cycle(remaining, adj)
    return order, cycle


def _find_cycle(remaining, adj):
    """在剩余（拓扑排序后）子图中查找环。"""
    visited = set()
    stack = []
    def dfs(node):
        if node in stack:
            idx = stack.index(node)
            return stack[idx:] + [node]
        if node in visited:
            return None
        visited.add(node); stack.append(node)
        for nxt in adj[node]:
            if nxt in remaining:
                c = dfs(nxt)
                if c: return c
        stack.pop()
        return None
    for start in sorted(remaining):
        c = dfs(start)
        if c: return c
    return list(remaining)[:1]  # 兜底


def check_dag(dag):
    findings = []
    nodes = dag.get("nodes", [])
    node_ids = {n.get("node_id") for n in nodes if n.get("node_id")}
    baseline_refs = set(dag.get("baseline_refs", []) or [])

    # 先做检查 4（代价低，在图分析前先捕获畸形节点）
    seen_ids = set()
    for n in nodes:
        nid = n.get("node_id", "<no id>")
        if not n.get("node_id"):
            findings.append(finding(4, "MISSING_NODE_ID", "REJECT", nid, "节点缺少 node_id")); continue
        if nid in seen_ids:
            findings.append(finding(4, "DUPLICATE_NODE_ID", "REJECT", nid, f"node_id {nid!r} 出现多次"))
        seen_ids.add(nid)
        scope = n.get("scope")
        if not scope:
            findings.append(finding(4, "MISSING_SCOPE", "REJECT", nid, "缺少 scope"))
        elif scope not in VALID_SCOPES:
            findings.append(finding(4, "INVALID_SCOPE", "REJECT", nid, f"scope {scope!r} 不在 {sorted(VALID_SCOPES)} 中"))
        ntype = n.get("type")
        if not ntype:
            findings.append(finding(4, "MISSING_TYPE", "REJECT", nid, "缺少 type"))
        elif ntype not in VALID_TYPES:
            findings.append(finding(4, "INVALID_TYPE", "REJECT", nid, f"type {ntype!r} 不在 {sorted(VALID_TYPES)} 中"))

    # 检查 3：依赖存在
    for n in nodes:
        nid = n.get("node_id", "?")
        for dep in n.get("depends_on", []) or []:
            if dep not in node_ids:
                findings.append(finding(3, "DANGLING_DEPENDENCY", "REJECT", nid, f"depends_on {dep!r} 不在图中"))

    # 检查 2：可逆（存在 creates 时必须有 teardown）
    for n in nodes:
        nid = n.get("node_id", "?")
        creates = n.get("creates")
        teardown = n.get("teardown")
        if creates and not teardown:
            findings.append(finding(2, "MISSING_TEARDOWN", "REJECT", nid, f"节点创建了 {creates!r} 但没有 teardown；状态泄漏"))
        # Static 节点的 baseline 声明交叉核对
        if n.get("type") == "Static":
            bref = n.get("baseline_ref")
            if bref and bref not in baseline_refs:
                findings.append(finding(2, "BASELINE_NOT_DECLARED", "REJECT", nid, f"Static 节点引用的 baseline {bref!r} 不在图的 baseline_refs 中"))

    # 检查 1：无环
    order, cycle = _topo_sort(nodes)
    if cycle:
        findings.append(finding(1, "CYCLE_DETECTED", "REJECT", "graph",
                                f"依赖环：{' -> '.join(cycle)}"))

    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {
        "skill": "14",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "dag_id": dag.get("dag_id"),
        "total_nodes": len(nodes),
        "topological_order": order if not cycle else None,
        "verdict": "REJECT" if has_reject else ("PASS" if nodes else "REJECT"),
        "total_findings": len(findings),
        "findings": findings,
        "routing": "PASS -> 可按拓扑顺序安全执行；REJECT -> 构建前必须修复",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Fixture DAG 校验器")
    p.add_argument("--dag", required=True, help="Fixture DAG JSON")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        dag = json.load(open(args.dag))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr); return 3
    result = check_dag(dag)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out: open(args.out, "w").write(out)
    else: print(out)
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
