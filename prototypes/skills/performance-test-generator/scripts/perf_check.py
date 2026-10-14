#!/usr/bin/env python3
"""
性能测试脚本契约检查器。

三项检查（见 references/perf_contract.md）：
  1. MOCK_DEP_PERF_ASSERT：对被 mock 的依赖做性能断言。
  2. SHARED_DATA_NAMESPACE：load 数据与功能测试共用命名空间。
  3. THRESHOLD_NOT_FROM_STRATEGY：阈值无法追溯到 strategy 契约。

CLI：
  python perf_check.py --script path/to/perf_script.json [--strategy path] [--out path]

退出码：0 PASS | 2 REJECT | 3 输入无效
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys

FUNCTIONAL_NAMESPACES = frozenset({"functional", "default", "shared", "main"})


def finding(code, target, msg):
    return {"code": code, "severity": "REJECT", "target": target, "msg": msg}


def check_perf_script(payload, strategy_thresholds=None):
    """校验一个性能脚本 packet，返回 findings 列表。"""
    findings = []
    if not isinstance(payload, dict):
        return [finding("INVALID_PERF_PACKET", "root", "perf 脚本根节点必须是对象")]

    # None 表示"未提供 strategy 契约"——与空契约含义不同。
    known_thresholds = None if strategy_thresholds is None else set(strategy_thresholds)

    # 检查 1：对 mock 做性能断言，测的是 mock 而非真实依赖。
    if payload.get("uses_mocked_dependency") and payload.get("asserts_performance"):
        findings.append(
            finding(
                "MOCK_DEP_PERF_ASSERT",
                payload.get("script_id", "script"),
                "性能断言运行在被 mock 的依赖上；测的是 stub，不是真实服务",
            )
        )

    # 检查 2：load 数据必须与功能测试的 fixture 做命名空间隔离。
    namespace = payload.get("namespace")
    if not namespace:
        findings.append(
            finding(
                "SHARED_DATA_NAMESPACE",
                "namespace",
                "未声明 namespace；无法确认 load 数据隔离",
            )
        )
    elif str(namespace).lower() in FUNCTIONAL_NAMESPACES:
        findings.append(
            finding(
                "SHARED_DATA_NAMESPACE",
                namespace,
                f"namespace {namespace!r} 与功能测试共用；load 数据量与功能侧数据变更会互相污染",
            )
        )

    # 检查 3：每个阈值都必须能追溯到 strategy 契约。脚本里凭空发明的
    # 阈值是无凭据的 SLO。
    raw_thresholds = payload.get("thresholds", []) or []
    if not isinstance(raw_thresholds, list):
        findings.append(finding("INVALID_PERF_PACKET", "thresholds", "thresholds 必须是数组"))
        raw_thresholds = []
    if payload.get("asserts_performance") and not raw_thresholds:
        findings.append(
            finding(
                "THRESHOLD_NOT_FROM_STRATEGY",
                "thresholds",
                "脚本声明了性能断言但未声明阈值；SLO 无法追溯",
            )
        )
    for index, threshold in enumerate(raw_thresholds):
        if not isinstance(threshold, dict):
            findings.append(
                finding("INVALID_PERF_PACKET", f"thresholds[{index}]", "threshold 必须是对象")
            )
            continue
        name = threshold.get("name") or threshold.get("metric") or f"thresholds[{index}]"
        source = threshold.get("strategy_ref") or threshold.get("source")
        if not source:
            findings.append(
                finding(
                    "THRESHOLD_NOT_FROM_STRATEGY",
                    name,
                    f"threshold {name!r} 未声明 strategy_ref；凭空发明的 SLO 无法问责",
                )
            )
        elif known_thresholds is None:
            findings.append(
                finding(
                    "THRESHOLD_NOT_FROM_STRATEGY",
                    name,
                    f"threshold {name!r} 声称 strategy_ref 为 {source!r}，但未提供 strategy 契约；"
                    "该声称无法核实",
                )
            )
        elif source not in known_thresholds:
            findings.append(
                finding(
                    "THRESHOLD_NOT_FROM_STRATEGY",
                    name,
                    f"strategy_ref {source!r} 在 strategy 契约中不存在",
                )
            )

    return findings


def check_perf_report(payload, strategy_thresholds=None):
    """把 findings 列表包装为 verdict 信封。"""
    findings = check_perf_script(payload, strategy_thresholds)
    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {
        "skill": "21",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "script_id": payload.get("script_id") if isinstance(payload, dict) else None,
        "total_findings": len(findings),
        "findings": findings,
        "verdict": "REJECT" if has_reject else "PASS",
        "routing": "PASS -> 可在真实环境执行；REJECT -> 修复 mock/命名空间/阈值问题",
    }


def _load_strategy_refs(path):
    """从 strategy 契约中收集可引用的 gate 名称。"""
    with open(path, encoding="utf-8") as handle:
        strategy = json.load(handle)
    refs = set()
    for gate in strategy.get("Quality_Gates", []) or []:
        if isinstance(gate, dict):
            for key in ("gate_name", "metric"):
                if gate.get(key):
                    refs.add(gate[key])
    for name in (strategy.get("performance_thresholds", {}) or {}):
        refs.add(name)
    return refs


def main(argv=None):
    p = argparse.ArgumentParser(description="性能测试脚本契约检查器")
    p.add_argument("--script", required=True, help="perf 脚本 packet JSON")
    p.add_argument("--strategy", default=None, help="strategy 契约 JSON（阈值来源）")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        with open(args.script, encoding="utf-8") as handle:
            payload = json.load(handle)
        refs = _load_strategy_refs(args.strategy) if args.strategy else None
    except (OSError, json.JSONDecodeError, AttributeError) as e:
        print(json.dumps({"error": f"读取输入失败：{e}"}), file=sys.stderr)
        return 3
    result = check_perf_report(payload, refs)
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
