#!/usr/bin/env python3
"""make eval：Provider 黄金集评估闸门 + deterministic-local 基线核验（C2/C8，零 LLM-judge）。

默认模式＝校验模式：
1. 基线存在且与 deterministic-local 锚点重算一致（防静默漂移）；
2. 锚点自身过黄金集闸门（结构判分 + 负例零容忍，false-accept 必须为 0）。

--write-baseline：重新归档基线（仅当锚点或黄金集语料有意变更时执行）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 使 backend/src 可导入（与 run_all_evals.py 由 backend uv 环境执行的约定一致）
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from qf.providers.golden_eval import (  # noqa: E402
    BASELINE_PATH,
    archive_baseline,
    check_baseline,
    evaluate_provider,
)
from qf.providers.planning import deterministic_planning_provider  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="重新归档 deterministic-local 黄金集基线（锚点/黄金集变更后使用）",
    )
    args = parser.parse_args()

    if args.write_baseline:
        target = archive_baseline()
        print(f"PASS: 基线已归档 {target.relative_to(REPO_ROOT)}")
        return 0

    baseline_ok, baseline_message = check_baseline()
    if not baseline_ok:
        print(f"FAIL: {baseline_message}")
        return 1

    report = evaluate_provider(deterministic_planning_provider)
    false_accepts = report["negativeCases"]["falseAccepts"]
    if not report["gatePassed"]:
        print("FAIL: deterministic-local 锚点未通过黄金集闸门")
        for failure in report["structureScoring"]["failures"]:
            print(f"- 结构判分: {failure}")
        for name in false_accepts:
            print(f"- 负例 false-accept: {name}")
        return 1

    print(
        "PASS: 基线与锚点一致；锚点黄金集闸门通过"
        f"（结构判分 4/4，负例 {report['negativeCases']['count']} 条 false-accept=0）"
    )
    print(f"baseline: {BASELINE_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
