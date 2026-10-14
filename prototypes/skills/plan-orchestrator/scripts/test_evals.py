#!/usr/bin/env python3
"""plan-orchestrator 的确定性 eval runner，调用真实 checker。

import 刻意不加保护：checker 缺失时必须响亮地失败，
而不是被裸 `except` 吸收成一个 REJECT verdict。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plan_check import check_plan_report


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
        result = check_plan_report(test["input"])

        expected_verdict = test.get("expected_verdict")
        if result["verdict"] != expected_verdict:
            print(f"  FAIL：期望 verdict 为 {expected_verdict}，实际为 {result['verdict']}")
            all_passed = False
            continue

        expected_findings = test.get("expected_findings", [])
        actual_findings = [f["code"] for f in result.get("findings", [])]
        missing = set(expected_findings) - set(actual_findings)
        if missing:
            print(f"  FAIL：缺少期望的 findings：{missing}。实际：{actual_findings}")
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
