#!/usr/bin/env python3
"""knowledge-memory 的确定性 eval runner。调用真实检查器。

import 故意不加保护：检查器缺失时必须大声失败，
而不是被裸 `except` 吞成一个 REJECT verdict。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memory_check import check_entry, content_hash


def run_evals():
    evals_path = os.path.join(
        os.path.dirname(__file__), "..", "assets", "evals", "evals.json"
    )
    if not os.path.exists(evals_path):
        print(f"未找到 evals 文件：{evals_path}")
        sys.exit(1)

    with open(evals_path, "r", encoding="utf-8") as f:
        evals = json.load(f)

    default_hashes = evals.get("known_hashes", [])
    all_passed = True
    for test in evals.get("test_cases", []):
        print(f"运行用例：{test['name']}")
        known = test.get("known_hashes_override", default_hashes)
        # 哨兵值：用该条目自身的 hash 预置存储，以演练
        # 重复检测，而无需把摘要硬编码进 fixture。
        known = [content_hash(test["input"]) if h == "__COMPUTED__" else h for h in known]
        result = check_entry(test["input"], known)

        expected_verdict = test.get("expected_verdict")
        if result["verdict"] != expected_verdict:
            print(f"  FAIL: 期望 verdict {expected_verdict}，实际 {result['verdict']}")
            all_passed = False
            continue

        expected_findings = test.get("expected_findings", [])
        actual_findings = [f["code"] for f in result.get("findings", [])]
        missing = set(expected_findings) - set(actual_findings)
        if missing:
            print(f"  FAIL: 缺少期望的 findings：{missing}。实际：{actual_findings}")
            all_passed = False
            continue

        print("  PASS")

    if all_passed:
        print("全部用例通过。")
        sys.exit(0)
    print("部分用例失败。")
    sys.exit(1)


if __name__ == "__main__":
    run_evals()
