"""M5 Provider 切换评估闸门（C2/C8：真实模型接入前必须先过黄金集 + 结构判分）。

deterministic-local 既是 failover 也是评估锚点：黄金集参考输出由它生成并归档为
baseline（prototypes/skills/evals/baseline/planning-golden-baseline.json）。候选
provider 必须通过结构判分且负例零容忍（false-accept＝0）才允许切换，不达标走
Plan B（保留 deterministic-local），切换尝试留不可变台账（provider_call_records）。
本模块零 LLM-judge：全部判分为确定性结构校验与规范化摘要比对。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qf.providers.hardening import _OUTPUT_VALIDATORS, InvalidOutputError
from qf.providers.planning import (
    GeneratedCase,
    PlanningGenerationProvider,
    deterministic_planning_provider,
)

# 仓库根目录（backend/src/qf/providers → parents[4]）
REPO_ROOT = Path(__file__).resolve().parents[4]
BASELINE_PATH = REPO_ROOT / "prototypes" / "skills" / "evals" / "baseline" / "planning-golden-baseline.json"

# 黄金集固定来源语料（锚定回放样本，变更即视为新基线，须重新归档）
GOLDEN_SOURCE = (
    "# 订单退款审核\n"
    "用户在订单完成 7 天内可申请退款，退款金额不得超过实付金额。\n"
    "审核通过后原路退回，审核拒绝必须给出原因并通知用户。\n"
    "非法订单号与越权操作必须被拒绝且不留副作用。"
)
# 黄金集固定 ID（uuid5 保证合法 UUID 且逐次运行一致）
GOLDEN_STRATEGY_VERSION_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "qualityforge:golden-strategy-version"))
GOLDEN_REQUIREMENT_VERSION_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "qualityforge:golden-requirement-version"))
GOLDEN_OWNER_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "qualityforge:golden-owner"))
GOLDEN_PLAN_VERSION_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "qualityforge:golden-plan-version"))

# plan 中的日期字段随天变化，不得参与基线摘要（否则基线每天漂移）
_VOLATILE_PLAN_KEYS = ("startDate", "endDate")


def _canonical_digest(payload: Any) -> str:
    from qf.services.planning_workflow import content_digest

    return content_digest(payload)


def _golden_outputs(provider: PlanningGenerationProvider) -> dict[str, Any]:
    """用给定 provider 回放黄金集四步生成，输出规范化字典。"""
    summary = provider.summarize(GOLDEN_SOURCE)
    strategy = provider.strategy(summary)
    plan = provider.plan(summary, GOLDEN_STRATEGY_VERSION_ID, GOLDEN_REQUIREMENT_VERSION_ID, GOLDEN_OWNER_ID)
    cases = [asdict(case) for case in provider.cases(summary, GOLDEN_PLAN_VERSION_ID)]
    return {"summary": summary, "strategy": strategy, "plan": plan, "cases": cases}


def _score_structure(provider: PlanningGenerationProvider) -> tuple[bool, list[str]]:
    """结构判分：黄金集四步输出逐一过硬化层同一套契约校验器。"""
    failures: list[str] = []
    summary = provider.summarize(GOLDEN_SOURCE)
    try:
        _OUTPUT_VALIDATORS["summarize"](summary)
    except InvalidOutputError as exc:
        failures.append(f"summarize: {exc}")
    strategy = provider.strategy(summary)
    try:
        _OUTPUT_VALIDATORS["strategy"](strategy)
    except InvalidOutputError as exc:
        failures.append(f"strategy: {exc}")
    try:
        plan = provider.plan(
            summary, GOLDEN_STRATEGY_VERSION_ID, GOLDEN_REQUIREMENT_VERSION_ID, GOLDEN_OWNER_ID
        )
        _OUTPUT_VALIDATORS["plan"](plan)
    except InvalidOutputError as exc:
        failures.append(f"plan: {exc}")
    try:
        cases = provider.cases(summary, GOLDEN_PLAN_VERSION_ID)
        _OUTPUT_VALIDATORS["cases"](cases)
    except InvalidOutputError as exc:
        failures.append(f"cases: {exc}")
    return not failures, failures


class _NegativeCase:
    """负例：坏 provider 必须被结构判分拒绝；接受即 false-accept。"""

    def __init__(self, name: str, provider: PlanningGenerationProvider) -> None:
        self.name = name
        self.provider = provider


class _EmptySummaryProvider:
    """负例 1：summarize 返回空串（结构判分必须拒绝）。"""

    provider_id = "negative-empty-summary"
    provider_version = "0.0.1"

    def summarize(self, source_content: str) -> str:
        return "   "

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


class _BrokenStrategyProvider:
    """负例 2：strategy 缺少契约必填字段（结构判分必须拒绝）。"""

    provider_id = "negative-broken-strategy"
    provider_version = "0.0.1"

    def summarize(self, source_content: str) -> str:
        return deterministic_planning_provider.summarize(source_content)

    def strategy(self, source_summary: str) -> dict[str, Any]:
        return {"objective": f"验证需求：{source_summary}"}  # 缺 inScope/testTypes 等必填项

    def plan(
        self, source_summary: str, strategy_version_id: str, requirement_version_id: str, owner_id: str
    ) -> dict[str, Any]:
        return deterministic_planning_provider.plan(
            source_summary, strategy_version_id, requirement_version_id, owner_id
        )

    def cases(self, source_summary: str, plan_version_id: str) -> list[GeneratedCase]:
        return deterministic_planning_provider.cases(source_summary, plan_version_id)


NEGATIVE_CASES = (
    _NegativeCase("empty-summary", _EmptySummaryProvider()),
    _NegativeCase("broken-strategy", _BrokenStrategyProvider()),
)


def evaluate_provider(provider: PlanningGenerationProvider) -> dict[str, Any]:
    """对候选 provider 执行黄金集评估：结构判分 + 负例零容忍，返回评估报告。"""
    structure_ok, structure_failures = _score_structure(provider)
    false_accepts: list[str] = []
    for case in NEGATIVE_CASES:
        negative_ok, _ = _score_structure(case.provider)
        if negative_ok:
            false_accepts.append(case.name)
    return {
        "providerId": provider.provider_id,
        "providerVersion": provider.provider_version,
        "goldenSourceDigest": _canonical_digest(GOLDEN_SOURCE),
        "structureScoring": {"passed": structure_ok, "failures": structure_failures},
        "negativeCases": {"count": len(NEGATIVE_CASES), "falseAccepts": false_accepts},
        "gatePassed": structure_ok and not false_accepts,
    }


def build_baseline() -> dict[str, Any]:
    """由 deterministic-local 锚点生成基线（确定性、可逐字节复现）。"""
    outputs = _golden_outputs(deterministic_planning_provider)
    stable_plan = {key: value for key, value in outputs["plan"].items() if key not in _VOLATILE_PLAN_KEYS}
    return {
        "baselineVersion": 1,
        "anchorProviderId": deterministic_planning_provider.provider_id,
        "anchorProviderVersion": deterministic_planning_provider.provider_version,
        "goldenSourceDigest": _canonical_digest(GOLDEN_SOURCE),
        "outputsDigest": _canonical_digest(
            {
                "summary": outputs["summary"],
                "strategy": outputs["strategy"],
                "plan": stable_plan,
                "cases": outputs["cases"],
            }
        ),
        "outputs": outputs,
    }


def archive_baseline(path: Path | None = None) -> Path:
    """归档基线文件（规范 JSON，确定性内容，可直接入库）。"""
    target = path or BASELINE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(build_baseline(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    target.write_text(payload, encoding="utf-8")
    return target


def check_baseline(path: Path | None = None) -> tuple[bool, str]:
    """校验基线存在且与锚点当前重算一致（防基线静默漂移）。"""
    target = path or BASELINE_PATH
    if not target.is_file():
        return False, f"基线缺失: {target}（先运行 make eval --write-baseline 归档）"
    try:
        archived = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"基线不可解析: {exc}"
    current = build_baseline()
    if archived.get("outputsDigest") != current["outputsDigest"]:
        return False, "基线与 deterministic-local 锚点重算不一致（锚点或黄金集已变更，须重新归档）"
    return True, "基线与锚点一致"
