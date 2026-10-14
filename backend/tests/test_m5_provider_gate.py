"""M5 Provider 切换评估闸门（C2/C8）：黄金集达标＋结构判分通过方可切换。

验收锚点：
1. deterministic-local 锚点自身必过闸门（结构判分 4/4，负例零容忍）；
2. 结构判分不达标的候选 fail-closed 拒绝切换（422 PROVIDER_GATE_REJECTED），当前 provider 不变；
3. 达标候选切换成功并重建加固层/编排图；
4. 每次切换尝试（成/败）落不可变台账（method=PROVIDER_SWITCH），供 AI 类版本门禁证据审计；
5. 基线归档确定性（两次归档逐字节一致）且漂移可检出。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from qf.providers.golden_eval import (
    NEGATIVE_CASES,
    _BrokenStrategyProvider,
    archive_baseline,
    build_baseline,
    check_baseline,
    evaluate_provider,
)
from qf.providers.planning import GeneratedCase, deterministic_planning_provider
from qf.services.planning_workflow import DomainError, planning_workflow_service


class _PassingCandidate:
    """达标候选：输出与锚点等价，仅身份不同（模拟真实 Provider 通过评估后切换）。"""

    provider_id = "candidate-ok"
    provider_version = "2.0.0"

    def summarize(self, source_content: str) -> str:
        return deterministic_planning_provider.summarize(source_content)

    def strategy(self, source_summary: str) -> dict[str, Any]:
        return deterministic_planning_provider.strategy(source_summary)

    def plan(
        self, source_summary: str, strategy_version_id: str, requirement_version_id: str, owner_id: str
    ) -> dict[str, Any]:
        return deterministic_planning_provider.plan(
            source_summary, strategy_version_id, requirement_version_id, owner_id
        )

    def cases(self, source_summary: str, plan_version_id: str) -> list[GeneratedCase]:
        return deterministic_planning_provider.cases(source_summary, plan_version_id)


def _switch_records(sqlite_path: Path) -> list[tuple[str, str]]:
    """读取台账中的 PROVIDER_SWITCH 记录（provider_id, status）。"""
    with sqlite3.connect(sqlite_path) as connection:
        rows = connection.execute(
            "SELECT provider_id, status FROM provider_call_records WHERE method = 'PROVIDER_SWITCH'"
        ).fetchall()
    return [(row[0], row[1]) for row in rows]


def test_golden_gate_accepts_anchor_and_rejects_all_negative_cases() -> None:
    report = evaluate_provider(deterministic_planning_provider)
    assert report["gatePassed"] is True
    assert report["structureScoring"]["passed"] is True
    assert report["negativeCases"]["falseAccepts"] == []
    # 负例本身必须被结构判分拒绝（零容忍前提成立）
    for case in NEGATIVE_CASES:
        negative_report = evaluate_provider(case.provider)
        assert negative_report["structureScoring"]["passed"] is False, case.name


def test_switch_provider_rejects_broken_candidate_fail_closed(sqlite_path: Path) -> None:
    broken = _BrokenStrategyProvider()
    with pytest.raises(DomainError) as exc_info:
        planning_workflow_service.switch_provider(broken)  # type: ignore[arg-type]
    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "PROVIDER_GATE_REJECTED"
    assert error.details is not None and error.details["structureFailures"]
    # fail-closed：当前 provider 保持 deterministic-local，加固层未重建
    assert planning_workflow_service._provider.provider_id == "deterministic-local"
    assert _switch_records(sqlite_path) == [(broken.provider_id, "REJECTED")]


def test_switch_provider_accepts_passing_candidate_and_records_success(sqlite_path: Path) -> None:
    try:
        report = planning_workflow_service.switch_provider(_PassingCandidate())  # type: ignore[arg-type]
        assert report["gatePassed"] is True
        assert planning_workflow_service._provider.provider_id == "candidate-ok"
        # 切换后加固层与编排图围绕新 provider 重建
        assert planning_workflow_service._hardened._inner.provider_id == "candidate-ok"
        assert _switch_records(sqlite_path) == [("candidate-ok", "SUCCESS")]
    finally:
        # 恢复锚点，避免污染后续测试
        planning_workflow_service.override_provider(deterministic_planning_provider)


def test_baseline_archive_is_deterministic_and_drift_is_detected(tmp_path: Path) -> None:
    first = tmp_path / "baseline-a.json"
    second = tmp_path / "baseline-b.json"
    archive_baseline(first)
    archive_baseline(second)
    assert first.read_bytes() == second.read_bytes()
    assert check_baseline(first) == (True, "基线与锚点一致")
    # 漂移：篡改归档内容后核验必须失败
    tampered = first.read_text(encoding="utf-8").replace('"baselineVersion": 1', '"baselineVersion": 2')
    first.write_text(tampered, encoding="utf-8")
    baseline = build_baseline()
    first.write_text(
        first.read_text(encoding="utf-8").replace(baseline["outputsDigest"], "0" * 64),
        encoding="utf-8",
    )
    ok, message = check_baseline(first)
    assert ok is False and "不一致" in message
    # 基线缺失也必须 fail-closed
    ok, message = check_baseline(tmp_path / "missing.json")
    assert ok is False and "基线缺失" in message
