#!/usr/bin/env python3
"""对 ui_check.py 运行 evals.json。"""
import json
import sys
import os
from ui_check import check_script

def main():
    evals_path = os.path.join(os.path.dirname(__file__), "../assets/evals/evals.json")
    if not os.path.exists(evals_path):
        print(f"错误：未找到 {evals_path}")
        sys.exit(1)

    with open(evals_path, 'r') as f:
        evals = json.load(f)

    passed = 0
    failed = 0
    for idx, tc in enumerate(evals):
        scenario = tc.get("scenario", f"测试 {idx+1}")
        result = check_script(tc.get("input", {}))
        verdict = result.get("verdict")
        expected = tc.get("expected_verdict")

        if verdict == expected:
            print(f"✅ PASS：{scenario}")
            passed += 1
        else:
            print(f"❌ FAIL：{scenario}")
            print(f"   期望：{expected}，实际：{verdict}")
            failed += 1

    print(f"\n汇总：{passed} 通过，{failed} 失败")
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
