"""M1-P1：Provider 四项加固（超时/重试/降级/成本）+ LangGraph 编排防御测试。

三类坏 provider fixture 验证 failover 到 deterministic-local：
- TimeoutProvider：sleep 超过 generation_timeout_ms
- InvalidOutputProvider：缺字段/错型的产出物内容
- ExplodingProvider：直接抛异常
"""

from __future__ import annotations

import sqlite3
import time
from typing import Any

import pytest
from httpx import AsyncClient

from qf.config import settings
from qf.providers.planning import GeneratedCase, deterministic_planning_provider
from qf.services.planning_workflow import planning_workflow_service
from tests.test_planning_workflow import setup_identity, start_session


class TimeoutProvider:
    """所有生成方法 sleep 超过超时阈值。"""

    provider_id = "timeout-provider"
    provider_version = "1.0.0"

    def summarize(self, source_content: str) -> str:
        time.sleep(0.2)
        return "不会出现的摘要"

    def strategy(self, source_summary: str) -> dict[str, Any]:
        time.sleep(0.2)
        return {}

    def plan(
        self,
        source_summary: str,
        strategy_version_id: str,
        requirement_version_id: str,
        owner_id: str,
    ) -> dict[str, Any]:
        time.sleep(0.2)
        return {}

    def cases(self, source_summary: str, plan_version_id: str) -> list[GeneratedCase]:
        time.sleep(0.2)
        return []


class InvalidOutputProvider:
    """输出结构判分失败的产出物（缺必填字段/类型错误）。"""

    provider_id = "invalid-output-provider"
    provider_version = "1.0.0"

    def summarize(self, source_content: str) -> str:
        return "合法摘要"

    def strategy(self, source_summary: str) -> dict[str, Any]:
        return {"objective": "只有一个字段"}

    def plan(
        self,
        source_summary: str,
        strategy_version_id: str,
        requirement_version_id: str,
        owner_id: str,
    ) -> dict[str, Any]:
        return {"objective": 123, "planType": 456}

    def cases(self, source_summary: str, plan_version_id: str) -> list[GeneratedCase]:
        return [GeneratedCase(kind="POSITIVE", title="", content={"title": ""})]


class ExplodingProvider:
    """所有生成方法直接抛异常。"""

    provider_id = "exploding-provider"
    provider_version = "1.0.0"

    def summarize(self, source_content: str) -> str:
        raise RuntimeError("provider exploded")

    def strategy(self, source_summary: str) -> dict[str, Any]:
        raise RuntimeError("provider exploded")

    def plan(
        self,
        source_summary: str,
        strategy_version_id: str,
        requirement_version_id: str,
        owner_id: str,
    ) -> dict[str, Any]:
        raise RuntimeError("provider exploded")

    def cases(self, source_summary: str, plan_version_id: str) -> list[GeneratedCase]:
        raise RuntimeError("provider exploded")


@pytest.fixture(autouse=True)
def restore_default_provider() -> Any:
    """坏 provider 注入只作用于当前用例，结束后恢复 deterministic-local 默认与默认超时。"""
    yield
    planning_workflow_service.override_provider(deterministic_planning_provider)
    settings.generation_timeout_ms = 5000


def call_records(sqlite_path: Any) -> list[sqlite3.Row]:
    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute("SELECT * FROM provider_call_records ORDER BY id").fetchall()
    finally:
        connection.close()


async def test_timeout_provider_fails_over_to_deterministic(client: AsyncClient, sqlite_path: Any) -> None:
    settings.generation_timeout_ms = 50
    planning_workflow_service.override_provider(TimeoutProvider())
    profile = await setup_identity(client)
    session = await start_session(client, profile)

    assert session["status"] == "BLOCKED"
    assert len(session["artifactRefs"]) == 4
    records = call_records(sqlite_path)
    assert records, "provider_call_records 应记录每次调用"
    failed = [record for record in records if record["status"] != "SUCCESS"]
    assert failed, "超时调用应有失败记录"
    failovers = [record for record in records if record["failover"] == 1]
    assert failovers, "重试耗尽后应有 failover 记录"
    assert all(record["provider_id"] == "deterministic-local" for record in failovers)
    # failover 后产出物落 deterministic-local 语义（providerId 追溯生效提供者）
    response = await client.get(
        f"/api/v1/review-tasks/{session['reviewTaskIds'][0]}/artifact",
    )
    assert response.json()["data"]["content"]["providerId"] == "deterministic-local"


async def test_invalid_output_provider_fails_over_to_deterministic(client: AsyncClient, sqlite_path: Any) -> None:
    planning_workflow_service.override_provider(InvalidOutputProvider())
    profile = await setup_identity(client)
    session = await start_session(client, profile)

    assert session["status"] == "BLOCKED"
    assert len(session["artifactRefs"]) == 4
    records = call_records(sqlite_path)
    failovers = [record for record in records if record["failover"] == 1]
    assert failovers, "结构判分失败应触发 failover"
    assert all(record["provider_id"] == "deterministic-local" for record in failovers)
    # strategy 内容必须是 deterministic-local 的合法形状（而非坏 provider 的残缺输出）
    strategy_task_id: str | None = None
    for task_id in session["reviewTaskIds"]:
        task_data = (await client.get(f"/api/v1/review-tasks/{task_id}")).json()["data"]
        if task_data["artifactType"] == "TEST_STRATEGY":
            strategy_task_id = task_id
            break
    assert strategy_task_id is not None
    artifact = (await client.get(f"/api/v1/review-tasks/{strategy_task_id}/artifact")).json()["data"]["content"]
    assert artifact["approach"] == deterministic_planning_provider.strategy("x")["approach"]
    assert artifact["providerId"] == "deterministic-local"


async def test_exploding_provider_fails_over_to_deterministic(client: AsyncClient, sqlite_path: Any) -> None:
    planning_workflow_service.override_provider(ExplodingProvider())
    profile = await setup_identity(client)
    session = await start_session(client, profile)

    assert session["status"] == "BLOCKED"
    assert len(session["artifactRefs"]) == 4
    assert len(session["reviewTaskIds"]) == 4
    records = call_records(sqlite_path)
    failovers = [record for record in records if record["failover"] == 1]
    assert len(failovers) == 4, "summarize/strategy/plan/cases 四类调用均应 failover"
    assert all(record["provider_id"] == "deterministic-local" for record in failovers)


async def test_happy_path_records_cost_without_failover(client: AsyncClient, sqlite_path: Any) -> None:
    profile = await setup_identity(client)
    session = await start_session(client, profile)

    assert session["status"] == "BLOCKED"
    records = call_records(sqlite_path)
    assert [record["method"] for record in records] == ["summarize", "strategy", "plan", "cases"]
    assert all(record["status"] == "SUCCESS" for record in records)
    assert all(record["failover"] == 0 for record in records)
    assert all(record["duration_ms"] >= 0 for record in records)
    assert all(record["provider_id"] == "deterministic-local" for record in records)


async def test_graph_orchestration_records_node_order_and_failover_events(
    client: AsyncClient, sqlite_path: Any
) -> None:
    planning_workflow_service.override_provider(ExplodingProvider())
    profile = await setup_identity(client)
    session = await start_session(client, profile)

    trace = (
        await client.get(f"/api/v1/ai/sessions/{session['id']}/trace", params={"workspaceId": profile["workspaceId"]})
    ).json()["data"]
    node_ids = [event["nodeId"] for event in trace]
    # 确定性链顺序不变：test_cases 每用例一条事件（既有 6 事件形状，characterization 保护）
    assert node_ids == [
        "requirement_source_check",
        "strategy",
        "test_plan",
        "test_cases",
        "test_cases",
        "human_gate",
    ]
    # failover 留痕：会话 trace 或 provider_call_records 至少一处可见
    records = call_records(sqlite_path)
    assert any(record["failover"] == 1 for record in records)
