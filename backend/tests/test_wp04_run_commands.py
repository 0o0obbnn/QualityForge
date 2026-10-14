"""WP-04 运行命令专项（批次五十八，39 号 §5 切片一）。

覆盖：PAUSE/RESUME/CANCEL 状态迁移与回执、终态 409、未实装命令 422、
幂等重放、回执查询与跨 Workspace 门、事件登记。
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from qf.services.planning_workflow import DomainError, planning_workflow_service
from tests.test_planning_workflow import mutation_headers, setup_identity

SESSION_TERMINAL = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})


def _seed_session(profile: dict, status: str = "RUNNING") -> str:
    session_id = str(uuid.uuid4())
    planning_workflow_service.sessions[session_id] = {
        "id": session_id,
        "tenantId": profile["tenantId"],
        "workspaceId": profile["workspaceId"],
        "workItemId": None,
        "status": status,
        "createdAt": "2026-08-31T00:00:00+00:00",
        "updatedAt": "2026-08-31T00:00:00+00:00",
    }
    return session_id


def _seed_execution_task(profile: dict, status: str = "RUNNING") -> str:
    task_id = str(uuid.uuid4())
    planning_workflow_service.execution_tasks[task_id] = {
        "id": task_id,
        "tenantId": profile["tenantId"],
        "workspaceId": profile["workspaceId"],
        "status": status,
        "createdAt": "2026-08-31T00:00:00+00:00",
        "updatedAt": "2026-08-31T00:00:00+00:00",
    }
    return task_id


async def _command(client: AsyncClient, path: str, key: str, command_type: str, reason: str = "测试") -> object:
    return await client.post(
        path,
        headers=mutation_headers(client, idempotency_key=key),
        json={"commandType": command_type, "reason": reason},
    )


async def test_session_run_command_transitions_and_receipts(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    session_id = _seed_session(profile, "RUNNING")

    paused = await _command(client, f"/api/v1/ai/sessions/{session_id}/commands", "wp58-cmd-0000000001", "PAUSE")
    assert paused.status_code == 201, paused.text
    command = paused.json()["data"]
    assert command["status"] == "EFFECTIVE"
    assert command["receipt"]["accepted"] is True
    assert command["receipt"]["effectiveStatus"] == "PAUSED"
    assert command["receipt"]["completedAt"]
    assert planning_workflow_service.sessions[session_id]["status"] == "PAUSED"

    # 幂等重放返回原命令
    replay = await _command(client, f"/api/v1/ai/sessions/{session_id}/commands", "wp58-cmd-0000000001", "PAUSE")
    assert replay.status_code == 201
    assert replay.json()["data"]["id"] == command["id"]

    # RESUME：PAUSED → RUNNING
    resumed = await _command(client, f"/api/v1/ai/sessions/{session_id}/commands", "wp58-cmd-0000000002", "RESUME")
    assert resumed.status_code == 201
    assert resumed.json()["data"]["receipt"]["effectiveStatus"] == "RUNNING"

    # CANCEL：BLOCKED → CANCELLED
    _seed_session(profile)  # 另一个 RUNNING 会话
    planning_workflow_service.sessions[session_id]["status"] = "BLOCKED"
    cancelled = await _command(client, f"/api/v1/ai/sessions/{session_id}/commands", "wp58-cmd-0000000003", "CANCEL")
    assert cancelled.status_code == 201
    assert planning_workflow_service.sessions[session_id]["status"] == "CANCELLED"

    # 终态 409
    terminal = await _command(client, f"/api/v1/ai/sessions/{session_id}/commands", "wp58-cmd-0000000004", "PAUSE")
    assert terminal.status_code == 409
    assert terminal.json()["code"] == "INVALID_STATE_TRANSITION"

    # 未实装命令 422 显式拒绝
    unimplemented = await _command(client, f"/api/v1/ai/sessions/{session_id}/commands", "wp58-cmd-0000000005", "RETRY")
    assert unimplemented.status_code == 422
    assert "未实装" in unimplemented.json()["message"]

    # 不存在目标 404；Agent 下发 403（服务面角色门）
    missing = await _command(client, f"/api/v1/ai/sessions/{uuid.uuid4()}/commands", "wp58-cmd-0000000006", "PAUSE")
    assert missing.status_code == 404
    target = _seed_session(profile)
    with pytest.raises(DomainError) as agent_denied:
        await planning_workflow_service.issue_run_command(
            str(profile["tenantId"]),
            str(profile["workspaceId"]),
            "agent-runner",
            "AGENT",
            frozenset(["run_command.issue"]),
            "wp58-cmd-0000000007",
            "AGENT_SESSION",
            target,
            {"commandType": "PAUSE", "reason": "自令"},
        )
    assert agent_denied.value.status_code == 403

    # 回执查询：命令+回执成对；跨 Workspace 403；不存在 404
    receipt = await client.get(f"/api/v1/run-commands/{command['id']}", params={"workspaceId": profile["workspaceId"]})
    assert receipt.status_code == 200
    body = receipt.json()["data"]
    assert body["command"]["id"] == command["id"]
    assert body["receipt"]["commandId"] == command["id"]
    assert (
        await client.get(f"/api/v1/run-commands/{command['id']}", params={"workspaceId": str(uuid.uuid4())})
    ).status_code == 403
    assert (
        await client.get(f"/api/v1/run-commands/{uuid.uuid4()}", params={"workspaceId": profile["workspaceId"]})
    ).status_code == 404


async def test_execution_task_run_commands_and_events(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    task_id = _seed_execution_task(profile, "RUNNING")

    paused = await _command(client, f"/api/v1/execution-tasks/{task_id}/commands", "wp58-exec-00000000001", "PAUSE")
    assert paused.status_code == 201
    assert paused.json()["data"]["receipt"]["effectiveStatus"] == "PAUSED"

    resumed = await _command(client, f"/api/v1/execution-tasks/{task_id}/commands", "wp58-exec-00000000002", "RESUME")
    assert resumed.status_code == 201

    cancelled = await _command(client, f"/api/v1/execution-tasks/{task_id}/commands", "wp58-exec-00000000003", "CANCEL")
    assert cancelled.status_code == 201
    assert planning_workflow_service.execution_tasks[task_id]["status"] == "CANCELLED"

    # 终态 409 + 事件登记
    assert (
        await _command(client, f"/api/v1/execution-tasks/{task_id}/commands", "wp58-exec-00000000004", "PAUSE")
    ).status_code == 409
    events = await client.get(
        "/api/v1/observability/events",
        params={"workspaceId": profile["workspaceId"], "pageSize": 100},
    )
    event_types = {event["eventType"] for event in events.json()["data"]}
    assert "run_command.recorded" in event_types
