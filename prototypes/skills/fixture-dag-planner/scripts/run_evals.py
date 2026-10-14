#!/usr/bin/env python3
import json
import sys
import os
from dag_check import check_dag

def run_evals():
    evals_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'evals', 'evals.json')
    if not os.path.exists(evals_path):
        print(f"未找到 evals 文件：{evals_path}")
        sys.exit(1)
        
    with open(evals_path, 'r') as f:
        evals = json.load(f)
        
    all_passed = True
    for test in evals.get("test_cases", []):
        print(f"运行用例：{test['name']}")
        result = check_dag(test["input"])
        
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
    else:
        print("部分用例失败。")
        sys.exit(1)

if __name__ == "__main__":
    run_evals()
