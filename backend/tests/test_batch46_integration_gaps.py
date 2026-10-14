"""批次四十六：前端真实模式联调面补齐专项测试（TDD 红→绿）。

覆盖盘点 §三 缺口的服务端口径：
- 契约已有补路由四 op：listExecutionPlans / listKnowledgeEntries / listEnvironments / createEnvironment；
- 契约新增两面：listResultAnalyses（前端 fetchAnalyses 在调）/ getProviderStatus（回应墙 M-136）；
- 403 跨工作区门控与 Provider DEGRADED 观察窗口（24h，过期回落 NOMINAL）。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient

from qf.services.planning_workflow import planning_workflow_service
from tests.test_planning_workflow import mutation_headers, setup_identity

OTHER_WORKSPACE = "00000000-0000-4000-8000-000000000bad"


def _data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


async def test_batch46_list_endpoints_gate_cross_workspace_with_403(client: AsyncClient) -> None:
    """四张新增只读面对非本工作区一律 403（与其他 list 面同口径）。"""
    profile = await setup_identity(client)
    params = {"workspaceId": OTHER_WORKSPACE}
    for path in (
        "/api/v1/execution-plans",
        "/api/v1/knowledge/entries",
        "/api/v1/quality/result-analyses",
    ):
        response = await client.get(path, params=params)
        assert response.status_code == 403, f"{path}: {response.status_code} {response.text}"
        assert response.json()["code"] == "FORBIDDEN"
    environment_list = await client.get(f"/api/v1/platform/workspaces/{OTHER_WORKSPACE}/environments")
    assert environment_list.status_code == 403
    assert profile["workspaceId"] != OTHER_WORKSPACE


async def test_batch46_environment_create_and_list_roundtrip(client: AsyncClient) -> None:
    """环境创建→列表回环：workspaceId 取路径参数，可选字段缺省落默认值。"""
    profile = await setup_identity(client)
    workspace_id = profile["workspaceId"]

    created = _data(
        await client.post(
            f"/api/v1/platform/workspaces/{workspace_id}/environments",
            headers=mutation_headers(client),
            json={
                "name": "联调环境",
                "environmentType": "STAGING",
                "endpointMappings": {"api": "https://staging.example/api"},
            },
        )
    )
    assert created["workspaceId"] == workspace_id
    assert created["capabilities"] == {} and created["secretRefs"] == []

    listed = _data(await client.get(f"/api/v1/platform/workspaces/{workspace_id}/environments"))
    assert [item["id"] for item in listed] == [created["id"]]

    missing_field = await client.post(
        f"/api/v1/platform/workspaces/{workspace_id}/environments",
        headers=mutation_headers(client),
        json={"name": "缺 endpointMappings", "environmentType": "TEST"},
    )
    assert missing_field.status_code == 422


async def test_batch46_provider_status_nominal_then_degraded_window(client: AsyncClient) -> None:
    """Provider 状态口径：默认 NOMINAL；24h 内 failover 记录→DEGRADED；窗口外回落 NOMINAL。"""
    await setup_identity(client)

    nominal = _data(await client.get("/api/v1/ai/provider/status"))
    assert nominal["status"] == "NOMINAL"
    assert nominal["providerId"] == "deterministic-local" and nominal["providerVersion"]
    assert "fallbackProviderId" not in nominal

    occurred = datetime.now(UTC) - timedelta(hours=1)
    planning_workflow_service._store.append_provider_call_record(  # noqa: SLF001 - 测试直注台账模拟降级
        {
            "providerId": "deterministic-local",
            "providerVersion": "1.0.0",
            "method": "strategy",
            "durationMs": 12,
            "status": "SUCCESS",
            "failover": True,
            "occurredAt": occurred.isoformat(),
        }
    )
    degraded = _data(await client.get("/api/v1/ai/provider/status"))
    assert degraded["status"] == "DEGRADED"
    assert degraded["fallbackProviderId"] == "deterministic-local"
    assert degraded["since"] == occurred.isoformat() and "strategy" in degraded["reason"]

    stale = datetime.now(UTC) - timedelta(hours=48)
    planning_workflow_service._store.append_provider_call_record(  # noqa: SLF001 - 窗口外的降级应不再呈现
        {
            "providerId": "deterministic-local",
            "providerVersion": "1.0.0",
            "method": "cases",
            "durationMs": 9,
            "status": "SUCCESS",
            "failover": True,
            "occurredAt": stale.isoformat(),
        }
    )
    recovered = _data(await client.get("/api/v1/ai/provider/status"))
    assert recovered["status"] == "NOMINAL" and "fallbackProviderId" not in recovered


async def test_batch46_list_execution_plans_and_knowledge_entries_isolated(client: AsyncClient) -> None:
    """两张补路由列表面只回本工作区数据（空工作区返回空数组不报错）。"""
    profile = await setup_identity(client)
    params = {"workspaceId": profile["workspaceId"]}

    assert _data(await client.get("/api/v1/execution-plans", params=params)) == []
    assert _data(await client.get("/api/v1/knowledge/entries", params=params)) == []
    assert _data(await client.get("/api/v1/quality/result-analyses", params=params)) == []
    assert uuid.UUID(profile["workspaceId"])
