#!/usr/bin/env python3
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scripts.requirement_check import check_requirements

def run_evals():
    evals_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'evals', 'evals.json')
    if not os.path.exists(evals_path):
        print(f"错误：未找到 {evals_path}")
        sys.exit(1)
        
    with open(evals_path, 'r') as f:
        evals = json.load(f)
        
    passed = 0
    total = len(evals)
    
    for eval_case in evals:
        inputs = eval_case.get('inputs', {})
        expected = eval_case.get('expected_verdict')
        
        reqs = inputs.get('requirements', [])
        ir = inputs.get('ir', {})
        cases = inputs.get('cases', [])
        baselines = set(inputs.get('baselines', []))
        
        result = check_requirements(reqs, ir, cases, baselines)
        actual = result.get('verdict')
        
        if actual == expected:
            print(f"✅ {eval_case['id']}: PASS（verdict: {actual}）")
            passed += 1
        else:
            print(f"❌ {eval_case['id']}: FAIL（期望 {expected}，实际 {actual}）")
            if actual == 'REJECT':
                print(f"findings：{json.dumps(result.get('findings', []), indent=2)}")

    print(f"\n汇总：{passed}/{total} 个 eval 通过。")
    sys.exit(0 if passed == total else 1)

if __name__ == '__main__':
    run_evals()
