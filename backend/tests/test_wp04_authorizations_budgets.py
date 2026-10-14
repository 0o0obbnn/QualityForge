"""WP-04 授权/预算/检查点专项（批次五十九，39 号 §5 切片二）。

覆盖：授权决定只追加与 REVOKE 联动、有效期校验、预算合成默认（读无副作用）与更新、
检查点（PAUSE 落点 + 目标校验）、角色门与事件登记。
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from qf.services.planning_workflow import DomainError, planning_workflow_service
from tests.test_planning_workflow import active_release_id, mutation_headers, setup_identity
from tests.test_wp01a_workspace_context import _work_item_body


async def _seed_work_item(client: AsyncClient, profile: dict) -> str:
    release_id = await active_release_id(client, profile["workspaceId"])
    created = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client),
        json=_work_item_body(profile["workspaceId"], release_id),
    )
    assert created.status_code == 201
    return created.json()["data"]["id"]


def _seed_execution_task(profile: dict, status: str = "RUNNING") -> str:
    task_id = str(uuid.uuid4())
    planning_workflow_service.execution_tasks[task_id] = {
        "id": task_id,
        "tenantId": profile["tenantId"],
        "workspaceId": profile["workspaceId"],
        "executionPlanVersionId": None,
        "status": status,
        "createdAt": "2026-08-31T00:00:00+00:00",
        "updatedAt": "2026-08-31T00:00:00+00:00",
    }
    return task_id


async def test_runtime_authorization_decisions(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    work_item_id = await _seed_work_item(client, profile)

    granted = await client.post(
        f"/api/v1/work-items/{work_item_id}/authorizations",
        headers=mutation_headers(client, idempotency_key="wp59-auth-000000001"),
        json={"action": "AUTHORIZE", "permissionKeys": ["requirement.write", "work_item.create"]},
    )
    assert granted.status_code == 201, granted.text
    grant = granted.json()["data"]
    assert grant["status"] == "ACTIVE" and grant["decidedBy"] == profile["userId"]

    # 幂等重放
    replay = await client.post(
        f"/api/v1/work-items/{work_item_id}/authorizations",
        headers=mutation_headers(client, idempotency_key="wp59-auth-000000001"),
        json={"action": "AUTHORIZE", "permissionKeys": ["requirement.write", "work_item.create"]},
    )
    assert replay.json()["data"]["id"] == grant["id"]

    # REVOKE 交叠键：匹配的 ACTIVE 授权置 REVOKED，决定只追加
    revoked = await client.post(
        f"/api/v1/work-items/{work_item_id}/authorizations",
        headers=mutation_headers(client, idempotency_key="wp59-auth-000000002"),
        json={"action": "REVOKE", "permissionKeys": ["requirement.write"]},
    )
    assert revoked.status_code == 201
    assert revoked.json()["data"]["status"] == "REVOKED"
    listed = await client.get(
        f"/api/v1/work-items/{work_item_id}/authorizations",
        params={"workspaceId": profile["workspaceId"]},
    )
    decisions = listed.json()["data"]
    assert len(decisions) == 2  # 只追加，授权与撤销都留痕
    assert planning_workflow_service.runtime_authorizations[grant["id"]]["status"] == "REVOKED"

    # 有效期倒置 422；工作项不存在 404；Agent 决定 403（服务面）
    inverted = await client.post(
        f"/api/v1/work-items/{work_item_id}/authorizations",
        headers=mutation_headers(client, idempotency_key="wp59-auth-000000003"),
        json={
            "action": "AUTHORIZE",
            "permissionKeys": ["x"],
            "validFrom": "2026-09-02T00:00:00+00:00",
            "validUntil": "2026-09-01T00:00:00+00:00",
        },
    )
    assert inverted.status_code == 422
    assert (
        await client.post(
            f"/api/v1/work-items/{uuid.uuid4()}/authorizations",
            headers=mutation_headers(client, idempotency_key="wp59-auth-000000004"),
            json={"action": "AUTHORIZE", "permissionKeys": ["x"]},
        )
    ).status_code == 404
    with pytest.raises(DomainError) as agent_denied:
        await planning_workflow_service.create_runtime_authorization(
            str(profile["tenantId"]),
            str(profile["workspaceId"]),
            "agent-runner",
            "AGENT",
            frozenset(["runtime_authorization.manage"]),
            "wp59-auth-000000005",
            work_item_id,
            {"action": "AUTHORIZE", "permissionKeys": ["x"]},
        )
    assert agent_denied.value.status_code == 403

    events = await client.get(
        "/api/v1/observability/events",
        params={"workspaceId": profile["workspaceId"], "pageSize": 100},
    )
    event_types = {event["eventType"] for event in events.json()["data"]}
    assert "runtime_authorization.decided" in event_types


async def test_budget_policy_default_and_update(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    work_item_id = await _seed_work_item(client, profile)

    # 无策略时合成默认（读无副作用：两次 GET 一致且不落库）
    first = await client.get(
        f"/api/v1/work-items/{work_item_id}/budgets", params={"workspaceId": profile["workspaceId"]}
    )
    assert first.status_code == 200
    default = first.json()["data"]
    assert default["status"] == "NORMAL" and default["limits"]["concurrencyLimit"] == 1
    assert default["id"] is None
    assert not any(p.get("workItemId") == work_item_id for p in planning_workflow_service.budget_policies.values())

    updated = await client.post(
        f"/api/v1/work-items/{work_item_id}/budgets",
        headers=mutation_headers(client, idempotency_key="wp59-budget-000001"),
        json={"tokenLimit": 500_000, "timeLimitMinutes": 120},
    )
    assert updated.status_code == 201 or updated.status_code == 200, updated.text
    policy = updated.json()["data"]
    assert policy["limits"]["tokenLimit"] == 500_000
    assert policy["limits"]["timeLimitMinutes"] == 120
    assert policy["limits"]["retryLimit"] == 3  # 未提供项保持默认

    # GET 反映持久化策略
    after = await client.get(
        f"/api/v1/work-items/{work_item_id}/budgets", params={"workspaceId": profile["workspaceId"]}
    )
    assert after.json()["data"]["id"] == policy["id"]

    # 幂等重放返回原策略；非法值 422；Agent 调整 403（服务面）
    replay = await client.post(
        f"/api/v1/work-items/{work_item_id}/budgets",
        headers=mutation_headers(client, idempotency_key="wp59-budget-000001"),
        json={"tokenLimit": 500_000, "timeLimitMinutes": 120},
    )
    assert replay.json()["data"]["id"] == policy["id"]
    invalid = await client.post(
        f"/api/v1/work-items/{work_item_id}/budgets",
        headers=mutation_headers(client, idempotency_key="wp59-budget-000002"),
        json={"timeLimitMinutes": 0},
    )
    assert invalid.status_code == 422
    with pytest.raises(DomainError) as agent_denied:
        await planning_workflow_service.update_work_item_budget(
            str(profile["tenantId"]),
            str(profile["workspaceId"]),
            "agent-runner",
            "AGENT",
            frozenset(["budget.manage"]),
            "wp59-budget-000003",
            work_item_id,
            {"tokenLimit": 999_999_999},
        )
    assert agent_denied.value.status_code == 403

    # 事件登记（本测试只产生预算事件；授权事件在授权专项中验证）
    events = await client.get(
        "/api/v1/observability/events",
        params={"workspaceId": profile["workspaceId"], "pageSize": 100},
    )
    event_types = {event["eventType"] for event in events.json()["data"]}
    assert "budget.updated" in event_types


async def test_checkpoints_written_on_pause(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    task_id = _seed_execution_task(profile, "RUNNING")

    paused = await client.post(
        f"/api/v1/execution-tasks/{task_id}/commands",
        headers=mutation_headers(client, idempotency_key="wp59-ckpt-00000001"),
        json={"commandType": "PAUSE", "reason": "落检查点"},
    )
    assert paused.status_code == 201

    checkpoints = await client.get(
        f"/api/v1/runs/EXECUTION_TASK/{task_id}/checkpoints",
        params={"workspaceId": profile["workspaceId"]},
    )
    assert checkpoints.status_code == 200
    data = checkpoints.json()["data"]
    assert len(data) == 1
    assert len(data[0]["inputDigest"]) == 64
    assert data[0]["stage"] == "RUNNING"

    # 非法 targetType 422；目标不存在 404
    assert (
        await client.get(
            f"/api/v1/runs/UNKNOWN/{task_id}/checkpoints",
            params={"workspaceId": profile["workspaceId"]},
        )
    ).status_code == 422
    assert (
        await client.get(
            f"/api/v1/runs/EXECUTION_TASK/{uuid.uuid4()}/checkpoints",
            params={"workspaceId": profile["workspaceId"]},
        )
    ).status_code == 404
