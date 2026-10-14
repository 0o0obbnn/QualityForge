#!/usr/bin/env python3
import json
import sys
import os
from cleanup_check import check_cleanup

def main():
    evals_path = os.path.join(os.path.dirname(__file__), "..", "assets", "evals", "evals.json")
    if not os.path.exists(evals_path):
        print(f"未找到 evals 文件：{evals_path}")
        return 1
        
    with open(evals_path) as f:
        evals = json.load(f)
        
    passed = 0
    failed = 0
    for i, tc in enumerate(evals):
        name = tc.get("name", f"用例 {i}")
        input_data = tc.get("input", {})
        expected_verdict = tc.get("expected_verdict", "PASS")
        
        result = check_cleanup(input_data)
        if result["verdict"] == expected_verdict:
            print(f"✅ {name}")
            passed += 1
        else:
            print(f"❌ {name}：期望 {expected_verdict}，实际 {result['verdict']}")
            print(json.dumps(result["findings"], indent=2))
            failed += 1
            
    print(f"\n结果：{passed} 通过，{failed} 失败")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
