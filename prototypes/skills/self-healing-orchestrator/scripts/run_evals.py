#!/usr/bin/env python3
"""self-healing-orchestrator 的确定性 eval runner，调用真实 gate。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from healing_gate import evaluate


def run_evals():
    evals_path = os.path.join(
        os.path.dirname(__file__), "..", "assets", "evals", "evals.json"
    )
    if not os.path.exists(evals_path):
        print(f"未找到 evals 文件：{evals_path}")
        sys.exit(1)

    with open(evals_path, "r", encoding="utf-8") as f:
        evals = json.load(f)

    all_passed = True
    for test in evals.get("test_cases", []):
        print(f"运行测试：{test['name']}")
        result = evaluate(**test["input"])

        expected_decision = test.get("expected_decision")
        if result["decision"] != expected_decision:
            print(f"  FAIL：期望 decision 为 {expected_decision}，实际为 {result['decision']}")
            all_passed = False
            continue

        if "expected_vetoed_by" in test and result.get("vetoed_by") != test["expected_vetoed_by"]:
            print(
                f"  FAIL：期望 vetoed_by 为 {test['expected_vetoed_by']!r}，"
                f"实际为 {result.get('vetoed_by')!r}"
            )
            all_passed = False
            continue

        print("  PASS")

    if all_passed:
        print("全部测试通过。")
        sys.exit(0)
    print("部分测试未通过。")
    sys.exit(1)


if __name__ == "__main__":
    run_evals()
