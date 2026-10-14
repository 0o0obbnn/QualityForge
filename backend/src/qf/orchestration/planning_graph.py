"""M1-P1：gate0-planning-slice 生成链的 LangGraph 编排图。

四节点确定性链：summarize → strategy → plan → cases。
节点只返回 partial update；节点挂 RetryPolicy 兜底加固层之外的意外异常；
failover 已在 `HardenedPlanningProvider` 装饰器内完成，图负责编排顺序与
failover 事件留痕（写入 state，经 reducer 追加）。

版本 ID 由服务层在 invoke 前预分配并经 state 注入，保证 plan/cases 生成时
引用关系成立；产出物落库与审核语义仍归 `PlanningWorkflowService`，图不改。
"""

from __future__ import annotations

import operator
from typing import Annotated, Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy
from typing_extensions import TypedDict

from qf.providers.planning import GeneratedCase, PlanningGenerationProvider

# 节点级兜底重试：加固层内部已做业务重试与 failover，此处只防意外泄漏异常
_NODE_RETRY = RetryPolicy(max_attempts=3)


class PlanningState(TypedDict, total=False):
    """生成链共享状态：原始输入 + 各节点产出 + failover 留痕。"""

    source_content: str
    strategy_version_id: str
    plan_version_id: str
    requirement_version_id: str
    owner_id: str
    source_summary: str
    strategy_content: dict[str, Any]
    plan_content: dict[str, Any]
    generated_cases: list[GeneratedCase]
    failover_events: Annotated[list[dict[str, Any]], operator.add]


def _drain_failover_events(provider: PlanningGenerationProvider) -> list[dict[str, Any]]:
    """加固层暴露 failover 留痕则取走；普通 provider 返回空列表。"""
    pop = getattr(provider, "pop_failover_events", None)
    if callable(pop):
        events = pop()
        if isinstance(events, list):
            return events
    return []


def build_planning_graph(provider: PlanningGenerationProvider) -> Any:
    """编译生成链编排图（provider 注入点保持可替换，测试可注入坏 provider）。"""

    def summarize(state: PlanningState) -> dict[str, Any]:
        return {
            "source_summary": provider.summarize(state["source_content"]),
            "failover_events": _drain_failover_events(provider),
        }

    def strategy(state: PlanningState) -> dict[str, Any]:
        return {
            "strategy_content": provider.strategy(state["source_summary"]),
            "failover_events": _drain_failover_events(provider),
        }

    def plan(state: PlanningState) -> dict[str, Any]:
        content = provider.plan(
            state["source_summary"],
            state["strategy_version_id"],
            state["requirement_version_id"],
            state["owner_id"],
        )
        return {"plan_content": content, "failover_events": _drain_failover_events(provider)}

    def cases(state: PlanningState) -> dict[str, Any]:
        return {
            "generated_cases": provider.cases(state["source_summary"], state["plan_version_id"]),
            "failover_events": _drain_failover_events(provider),
        }

    return (
        StateGraph(PlanningState)
        .add_node("summarize", summarize, retry_policy=_NODE_RETRY)
        .add_node("strategy", strategy, retry_policy=_NODE_RETRY)
        .add_node("plan", plan, retry_policy=_NODE_RETRY)
        .add_node("cases", cases, retry_policy=_NODE_RETRY)
        .add_edge(START, "summarize")
        .add_edge("summarize", "strategy")
        .add_edge("strategy", "plan")
        .add_edge("plan", "cases")
        .add_edge("cases", END)
        .compile()
    )
