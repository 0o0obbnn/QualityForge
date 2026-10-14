"""Provider boundary for planning generation, with a deterministic default."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class GeneratedCase:
    kind: str
    title: str
    content: dict[str, Any]


class PlanningGenerationProvider(Protocol):
    """Generate draft content only; persistence and approval remain application concerns."""

    provider_id: str
    provider_version: str

    def summarize(self, source_content: str) -> str: ...

    def strategy(self, source_summary: str) -> dict[str, Any]: ...

    def plan(
        self,
        source_summary: str,
        strategy_version_id: str,
        requirement_version_id: str,
        owner_id: str,
    ) -> dict[str, Any]: ...

    def cases(self, source_summary: str, plan_version_id: str) -> list[GeneratedCase]: ...


class DeterministicPlanningProvider:
    """Offline reference implementation used for repeatable tests and safe fallback."""

    provider_id = "deterministic-local"
    provider_version = "1.0.0"

    def summarize(self, source_content: str) -> str:
        lines = [line.lstrip("# ").strip() for line in source_content.splitlines() if line.strip()]
        return "；".join(lines[:3])[:500] or "未命名需求"

    def strategy(self, source_summary: str) -> dict[str, Any]:
        return {
            "objective": f"验证需求：{source_summary}",
            "inScope": [source_summary],
            "outOfScope": ["未经声明的外部系统写入"],
            "riskAssessment": [{"risk": "需求歧义", "level": "HIGH", "treatment": "人工审核"}],
            "testTypes": ["FUNCTIONAL", "API", "NEGATIVE"],
            "approach": "风险驱动、来源可追溯、正反场景并行设计",
            "entryCriteria": ["需求版本摘要已固定"],
            "exitCriteria": ["策略、计划和用例均完成人工审核"],
            "environmentStrategy": "使用受控测试环境",
            "dataStrategy": "使用可复现且脱敏的测试数据",
            "automationStrategy": "优先API，稳定后扩展UI",
            "defectStrategy": "失败证据先分析，人工确认后形成Defect",
        }

    def plan(
        self,
        source_summary: str,
        strategy_version_id: str,
        requirement_version_id: str,
        owner_id: str,
    ) -> dict[str, Any]:
        today = datetime.now(UTC).date().isoformat()
        return {
            "strategyVersionId": strategy_version_id,
            "objective": f"执行测试策略覆盖：{source_summary}",
            "planType": "RELEASE_VALIDATION",
            "scope": {"requirementVersionId": requirement_version_id},
            "ownerId": owner_id,
            "startDate": today,
            "endDate": today,
            "milestones": [{"name": "人工审核", "exitGate": "ALL_FORMAL_ARTIFACTS_APPROVED"}],
            "resourceRequirements": {"reviewer": 1, "provider": self.provider_id},
            "acceptanceCriteria": ["所有ReviewTask绑定精确版本和摘要", "Agent不能批准自己的产出"],
        }

    def cases(self, source_summary: str, plan_version_id: str) -> list[GeneratedCase]:
        definitions = [
            ("POSITIVE", f"[{source_summary[:80]}] 正向业务流程", "业务操作成功且状态符合需求"),
            ("NEGATIVE", f"[{source_summary[:80]}] 非法输入与权限校验", "非法输入被拒绝且无越权副作用"),
        ]
        return [
            GeneratedCase(
                kind=kind,
                title=title,
                content={
                    "title": title,
                    "preconditions": ["需求版本摘要保持不变", "测试环境可用"],
                    "steps": [
                        {"sequence": 1, "action": "准备与需求匹配的输入", "kind": kind},
                        {"sequence": 2, "action": "执行目标业务行为", "planVersionId": plan_version_id},
                        {"sequence": 3, "action": "核对结果与副作用"},
                    ],
                    "testDataRefs": [],
                    "expectedResults": [expected],
                    "priority": "P1" if kind == "POSITIVE" else "P0",
                    "testType": "FUNCTIONAL",
                    "assertions": [{"target": "businessOutcome", "operator": "EQUALS", "expected": expected}],
                },
            )
            for kind, title, expected in definitions
        ]


deterministic_planning_provider = DeterministicPlanningProvider()
