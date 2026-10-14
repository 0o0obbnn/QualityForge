#!/usr/bin/env python3
"""对 impact_check.py 运行 evals.json。"""
import json
import sys
from pathlib import Path

from impact_check import check_analysis

def main():
    skill_dir = Path(__file__).resolve().parent.parent
    evals_path = skill_dir / "assets" / "evals" / "evals.json"
    
    if not evals_path.exists():
        print(f"错误：未找到 {evals_path}。")
        sys.exit(1)
        
    with open(evals_path) as f:
        evals = json.load(f)
        
    passed = 0
    failed = 0
    
    for case in evals:
        result = check_analysis(case["input"])
        verdict = result["verdict"]
        if verdict == case["expected_verdict"]:
            print(f"PASS: {case['name']}")
            passed += 1
        else:
            print(f"FAIL: {case['name']} - 期望 {case['expected_verdict']}，实际 {verdict}")
            failed += 1
            
    print(f"\n总计：{len(evals)}，通过：{passed}，失败：{failed}")
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
