#!/usr/bin/env python3
import json
import sys
import os
import subprocess

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    evals_path = os.path.join(script_dir, '..', 'assets', 'evals', 'evals.json')
    classify_script = os.path.join(script_dir, 'classify.py')

    try:
        with open(evals_path, 'r') as f:
            evals = json.load(f)
    except Exception as e:
        print(f"加载 evals 失败：{e}")
        return 1

    success = True
    for i, eval_case in enumerate(evals):
        input_data = eval_case.get('input', {})
        expected = eval_case.get('expected', {})

        temp_input = os.path.join(script_dir, f'temp_input_{i}.json')
        with open(temp_input, 'w') as f:
            json.dump(input_data, f)

        result = subprocess.run(
            ['python3', classify_script, '--signal', temp_input],
            capture_output=True, text=True
        )

        os.remove(temp_input)

        if result.returncode != 0:
            print(f"用例 {i} 未能运行 classify.py")
            success = False
            continue

        try:
            output_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"用例 {i} 返回了无效 JSON")
            success = False
            continue
        
        for k, v in expected.items():
            if output_data.get(k) != v:
                print(f"用例 {i} 失败。期望 {k}={v}，实际 {output_data.get(k)}")
                success = False
        
        if success:
            print(f"用例 {i} 通过。")

    if success:
        print("全部 eval 通过。")
        return 0
    else:
        print("部分 eval 失败。")
        return 1

if __name__ == '__main__':
    sys.exit(main())
