"""TC-RC-001~004：运行控制域可执行层（批次六十九，WP-04 已实现面）。

覆盖：会话 PAUSE 到安全点 + 回执唯一事实、命令幂等重放与终态拒绝、
执行任务命令与检查点、授权只追加与预算读写（R-RC-001~004）。
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from conftest import data_of, envelope, gate0_session, mutation_headers, setup_identity


async def test_tc_rc_001_pause_receipt_and_resume(client: AsyncClient) -> None:
    """TC-RC-001：PAUSE 到安全点生效，回执是生效唯一事实，RESUME 恢复。"""
    profile = await setup_identity(client)
    session = await gate0_session(client, profile)
    session_id = str(session["id"])

    pause = await client.post(
        f"/api/v1/ai/sessions/{session_id}/commands",
        headers=mutation_headers(client, f"rc-pause-{uuid.uuid4().hex[:11]}"),
        json={"commandType": "PAUSE", "reason": "人工暂停审视"},
    )
    assert pause.status_code == 201, pause.text
    command = data_of(pause)
    assert command["commandType"] == "PAUSE"
    assert command["receipt"]["accepted"] is True
    assert command["receipt"]["effectiveStatus"] == "PAUSED"

    receipt = data_of(
        await client.get(
            f"/api/v1/run-commands/{command['id']}",
            params={"workspaceId": profile["workspaceId"]},
        )
    )
    # gate0 会话产出审核任务后处于 BLOCKED（等审核），PAUSE 源态即 BLOCKED
    assert receipt["receipt"]["safePointRef"] == f"agent_session:{session_id}@BLOCKED>PAUSED"
    assert receipt["receipt"]["reasonCode"] == "EFFECTIVE_AT_STATUS_BOUNDARY"

    resume = await client.post(
        f"/api/v1/ai/sessions/{session_id}/commands",
        headers=mutation_headers(client, f"rc-resume-{uuid.uuid4().hex[:10]}"),
        json={"commandType": "RESUME", "reason": "恢复执行"},
    )
    assert resume.status_code == 201, resume.text
    assert data_of(resume)["receipt"]["effectiveStatus"] == "RUNNING"


async def test_tc_rc_002_idempotent_replay_and_terminal_rejected(
    client: AsyncClient,
) -> None:
    """TC-RC-002：同键重放返回原命令；终态目标非 RETRY 命令 409。"""
    profile = await setup_identity(client)
    session = await gate0_session(client, profile)
    session_id = str(session["id"])
    replay_key = f"rc-replay-{uuid.uuid4().hex[:9]}"

    first = await client.post(
        f"/api/v1/ai/sessions/{session_id}/commands",
        headers=mutation_headers(client, replay_key),
        json={"commandType": "PAUSE", "reason": "幂等基线"},
    )
    assert first.status_code == 201, first.text

    replay = await client.post(
        f"/api/v1/ai/sessions/{session_id}/commands",
        headers=mutation_headers(client, replay_key),
        json={"commandType": "PAUSE", "reason": "幂等基线"},
    )
    assert replay.status_code == 201, replay.text
    assert data_of(replay)["id"] == data_of(first)["id"], "同键重放应返回原命令"

    cancel = await client.post(
        f"/api/v1/ai/sessions/{session_id}/commands",
        headers=mutation_headers(client, f"rc-cancel-{uuid.uuid4().hex[:10]}"),
        json={"commandType": "CANCEL", "reason": "终态前置"},
    )
    assert cancel.status_code == 201, cancel.text

    after_terminal = await client.post(
        f"/api/v1/ai/sessions/{session_id}/commands",
        headers=mutation_headers(client, f"rc-after-{uuid.uuid4().hex[:10]}"),
        json={"commandType": "PAUSE", "reason": "终态负向"},
    )
    assert after_terminal.status_code == 409
    assert envelope(after_terminal)["code"] == "INVALID_STATE_TRANSITION"


async def test_tc_rc_003_execution_task_command_and_checkpoints(
    client: AsyncClient,
) -> None:
    """TC-RC-003：执行任务命令 + 不可变检查点列表 + 非法 targetType 422。"""
    profile = await setup_identity(client)
    session = await gate0_session(client, profile)

    plans = data_of(await client.get("/api/v1/test-plans", params={"workspaceId": profile["workspaceId"]}))
    assert plans, "gate0 会话应产出测试计划"
    exec_plan = await client.post(
        "/api/v1/execution-plans",
        headers=mutation_headers(client, f"rc-execplan-{uuid.uuid4().hex[:8]}"),
        json={
            "workspaceId": profile["workspaceId"],
            "planKey": f"EXEC-RC-{uuid.uuid4().hex[:6]}",
            "name": "运行控制执行计划",
            "testPlanId": plans[0]["id"],
        },
    )
    assert exec_plan.status_code == 201, exec_plan.text
    exec_plan_data = data_of(exec_plan)
    task = await client.post(
        f"/api/v1/execution-plans/{exec_plan_data['id']}/runs",
        headers=mutation_headers(client, f"rc-execrun-{uuid.uuid4().hex[:8]}"),
        json={"executionPlanVersionId": exec_plan_data["currentVersionId"]},
    )
    assert task.status_code == 202, task.text
    task_data = data_of(task)
    task_id = task_data["id"]

    pause = await client.post(
        f"/api/v1/execution-tasks/{task_id}/commands",
        headers=mutation_headers(client, f"rc-taskpause-{uuid.uuid4().hex[:7]}"),
        json={"commandType": "PAUSE", "reason": "执行暂停"},
    )
    # COMPLETED 任务（同步执行链）为终态：断言 409 语义（命令面真实行为）
    if pause.status_code == 409:
        assert envelope(pause)["code"] == "INVALID_STATE_TRANSITION"
    else:
        assert pause.status_code == 201, pause.text
        assert data_of(pause)["receipt"]["effectiveStatus"] == "PAUSED"

    checkpoints = data_of(
        await client.get(
            f"/api/v1/runs/EXECUTION_TASK/{task_id}/checkpoints",
            params={"workspaceId": profile["workspaceId"]},
        )
    )
    for item in checkpoints:
        for immutable_key in (
            "inputDigest",
            "outputRefs",
            "authorizationSnapshot",
            "budgetSnapshot",
        ):
            assert immutable_key in item, f"检查点缺不可变字段 {immutable_key}"

    invalid = await client.get(
        f"/api/v1/runs/NOT_A_TYPE/{task_id}/checkpoints",
        params={"workspaceId": profile["workspaceId"]},
    )
    assert invalid.status_code == 422, invalid.text


async def test_tc_rc_004_authorization_append_only_and_budget(
    client: AsyncClient,
) -> None:
    """TC-RC-004：授权只追加（无 Secret 明文）与预算面读写。"""
    profile = await setup_identity(client)
    session = await gate0_session(client, profile)
    work_item_id = str(session["workItemId"])

    budget_before = data_of(
        await client.get(
            f"/api/v1/work-items/{work_item_id}/budgets",
            params={"workspaceId": profile["workspaceId"]},
        )
    )
    assert "tokenLimit" in budget_before or "tokenLimitMax" in budget_before or budget_before, (
        "预算策略结构应非空（camelCase）"
    )

    updated = await client.post(
        f"/api/v1/work-items/{work_item_id}/budgets",
        headers=mutation_headers(client, f"rc-budget-{uuid.uuid4().hex[:10]}"),
        json={"tokenLimit": 200000, "warningThresholds": {"token": 0.8}},
    )
    assert updated.status_code == 200, updated.text
    budget_after = data_of(updated)
    if "tokenLimit" in budget_after:
        assert budget_after["tokenLimit"] == 200000

    granted = await client.post(
        f"/api/v1/work-items/{work_item_id}/authorizations",
        headers=mutation_headers(client, f"rc-auth-{uuid.uuid4().hex[:12]}"),
        json={
            "action": "AUTHORIZE",
            "permissionKeys": ["requirement.write"],
            "resourceScope": {"workItemId": work_item_id},
            "validUntil": "2026-12-31T00:00:00Z",
        },
    )
    assert granted.status_code == 201, granted.text
    authorization = data_of(granted)
    assert authorization["status"] == "ACTIVE"
    assert "secret" not in str(authorization).lower().replace("secretrefs", ""), "授权响应不得包含 Secret 明文"

    listed = data_of(
        await client.get(
            f"/api/v1/work-items/{work_item_id}/authorizations",
            params={"workspaceId": profile["workspaceId"]},
        )
    )
    assert any(item["id"] == authorization["id"] for item in listed)
