#!/usr/bin/env python3
import json
import subprocess
import tempfile
import sys
import os

def run_evals():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    evals_path = os.path.join(script_dir, '..', 'assets', 'evals', 'evals.json')
    compliance_check = os.path.join(script_dir, 'compliance_check.py')
    
    try:
        with open(evals_path, 'r') as f:
            evals = json.load(f)
    except Exception as e:
        print(f"加载 evals 失败：{e}")
        return 1

    success = True
    for ev in evals.get("evaluations", []):
        print(f"运行 eval：{ev['id']} - {ev['description']}")
        
        with tempfile.NamedTemporaryFile('w', delete=False) as pkt_f:
            json.dump(ev['inputs']['packet'], pkt_f)
        with tempfile.NamedTemporaryFile('w', delete=False) as ir_f:
            json.dump(ev['inputs']['ir'], ir_f)
            
        try:
            res = subprocess.run([sys.executable, compliance_check, '--packet', pkt_f.name, '--ir', ir_f.name], capture_output=True, text=True)
            output = json.loads(res.stdout)
            
            verdict = output.get('verdict')
            expected_verdict = ev['expected'].get('verdict')
            
            if verdict != expected_verdict:
                print(f"  FAILED：期望 {expected_verdict}，实际 {verdict}")
                success = False
            else:
                finding_code = ev['expected'].get('finding_code')
                if finding_code:
                    has_code = any(f.get('code') == finding_code for f in output.get('findings', []))
                    if not has_code:
                        print(f"  FAILED：期望 finding {finding_code}，未找到。")
                        print(f"  实际 findings：{output.get('findings')}")
                        success = False
                    else:
                        print("  PASSED")
                else:
                    print("  PASSED")
        finally:
            os.remove(pkt_f.name)
            os.remove(ir_f.name)
            
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(run_evals())
