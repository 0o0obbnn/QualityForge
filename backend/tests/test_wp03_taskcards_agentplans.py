"""WP-03 任务卡与 AgentPlan 专项（批次五十六，39 号 §3 切片三）。

覆盖：任务卡固化（提交即 SUBMITTED、新版本取代旧卡、澄清阻塞、无 Release 409）、
计划版本链（新版本 SUPERSEDED 旧待审计划）、人工裁决（摘要漂移 409、
批准联动 TaskCard ACTIVE、重复裁决 409、AGENT 自批 403 服务面）。
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from qf.services.planning_workflow import DomainError, planning_workflow_service
from tests.test_planning_workflow import active_release_id, mutation_headers, setup_identity
from tests.test_wp01a_workspace_context import _work_item_body


def _task_card_body() -> dict[str, object]:
    return {
        "objective": "生成退款链路回归资产",
        "scope": "合法与非法路径各一批",
        "acceptanceCriteria": "策略/计划/用例三层齐备且过人工门",
        "constraints": "不引入外部服务",
        "requestedPermissions": ["requirement.write"],
        "budget": {"maxMinutes": 30},
    }


def _plan_body(card_id: str) -> dict[str, object]:
    return {
        "taskCardId": card_id,
        "steps": [
            {"stepKey": "summarize", "agentRole": "coordinator", "description": "需求归纳"},
            {"stepKey": "cases", "agentRole": "case-designer", "description": "用例编制"},
        ],
    }


async def _seed_work_item(client: AsyncClient, profile: dict, *, with_release: bool = True) -> str:
    release_id = await active_release_id(client, profile["workspaceId"]) if with_release else None
    created = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client),
        json=_work_item_body(profile["workspaceId"], release_id)
        if release_id
        else {
            **_work_item_body(profile["workspaceId"], "00000000-0000-0000-0000-000000000099"),
            "releaseId": None,
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["data"]["id"]


async def test_task_card_lifecycle_and_plan_decision_chain(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    work_item_id = await _seed_work_item(client, profile)

    card = await client.post(
        f"/api/v1/work-items/{work_item_id}/task-cards",
        headers=mutation_headers(client, idempotency_key="wp56-card-0000000001"),
        json=_task_card_body(),
    )
    assert card.status_code == 201, card.text
    card_data = card.json()["data"]
    assert card_data["status"] == "SUBMITTED"
    assert len(card_data["contentDigest"]) == 64

    # 幂等重放
    replay = await client.post(
        f"/api/v1/work-items/{work_item_id}/task-cards",
        headers=mutation_headers(client, idempotency_key="wp56-card-0000000001"),
        json=_task_card_body(),
    )
    assert replay.json()["data"]["id"] == card_data["id"]

    # 新卡取代旧卡（不可静默扩展 → 走新版本）
    card2 = await client.post(
        f"/api/v1/work-items/{work_item_id}/task-cards",
        headers=mutation_headers(client, idempotency_key="wp56-card-0000000002"),
        json={**_task_card_body(), "scope": "扩展：补充风控边界"},
    )
    assert card2.status_code == 201
    card2_data = card2.json()["data"]
    assert planning_workflow_service.task_cards[card_data["id"]]["status"] == "SUPERSEDED"

    plan = await client.post(
        f"/api/v1/work-items/{work_item_id}/agent-plans",
        headers=mutation_headers(client, idempotency_key="wp56-plan-0000000001"),
        json=_plan_body(card2_data["id"]),
    )
    assert plan.status_code == 201, plan.text
    plan_data = plan.json()["data"]
    assert plan_data["planVersion"] == 1 and plan_data["status"] == "PENDING_APPROVAL"

    # 新版本计划使旧待审计划 SUPERSEDED
    plan2 = await client.post(
        f"/api/v1/work-items/{work_item_id}/agent-plans",
        headers=mutation_headers(client, idempotency_key="wp56-plan-0000000002"),
        json=_plan_body(card2_data["id"]),
    )
    assert plan2.status_code == 201
    plan2_data = plan2.json()["data"]
    assert plan2_data["planVersion"] == 2
    assert planning_workflow_service.agent_plans[plan_data["id"]]["status"] == "SUPERSEDED"

    listed = await client.get(
        f"/api/v1/work-items/{work_item_id}/agent-plans",
        params={"workspaceId": profile["workspaceId"]},
    )
    assert listed.status_code == 200
    assert [item["planVersion"] for item in listed.json()["data"]] == [1, 2]

    # 摘要漂移 → 409 STALE_ARTIFACT_VERSION
    drifted = await client.post(
        f"/api/v1/agent-plans/{plan2_data['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="wp56-decide-00000001"),
        json={
            "decision": "APPROVE",
            "expectedContentDigest": "0" * 64,
            "reason": "漂移测试",
        },
    )
    assert drifted.status_code == 409
    assert drifted.json()["code"] == "STALE_ARTIFACT_VERSION"

    # 正确摘要批准：计划 APPROVED + TaskCard ACTIVE
    approved = await client.post(
        f"/api/v1/agent-plans/{plan2_data['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="wp56-decide-00000002"),
        json={
            "decision": "APPROVE",
            "expectedContentDigest": plan2_data["contentDigest"],
            "reason": "方案与任务卡一致",
        },
    )
    assert approved.status_code == 201, approved.text
    assert approved.json()["data"]["planStatus"] == "APPROVED"
    assert planning_workflow_service.task_cards[card2_data["id"]]["status"] == "ACTIVE"

    # 幂等重放裁决
    replay_decision = await client.post(
        f"/api/v1/agent-plans/{plan2_data['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="wp56-decide-00000002"),
        json={
            "decision": "APPROVE",
            "expectedContentDigest": plan2_data["contentDigest"],
            "reason": "方案与任务卡一致",
        },
    )
    assert replay_decision.status_code == 201
    assert replay_decision.json()["data"]["id"] == approved.json()["data"]["id"]

    # 重复裁决（新键）→ 409
    again = await client.post(
        f"/api/v1/agent-plans/{plan2_data['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="wp56-decide-00000003"),
        json={
            "decision": "REJECT",
            "expectedContentDigest": plan2_data["contentDigest"],
            "reason": "二次裁决",
        },
    )
    assert again.status_code == 409
    assert again.json()["code"] == "INVALID_STATE_TRANSITION"

    # 不存在工作项 → 404；不存在计划 → 404
    assert (
        await client.post(
            f"/api/v1/work-items/{uuid.uuid4()}/task-cards",
            headers=mutation_headers(client, idempotency_key="wp56-card-0000000003"),
            json=_task_card_body(),
        )
    ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/agent-plans/{uuid.uuid4()}/decisions",
            headers=mutation_headers(client, idempotency_key="wp56-decide-00000004"),
            json={
                "decision": "APPROVE",
                "expectedContentDigest": "0" * 64,
                "reason": "孤儿",
            },
        )
    ).status_code == 404

    # 事件登记
    events = await client.get(
        "/api/v1/observability/events",
        params={"workspaceId": profile["workspaceId"], "pageSize": 100},
    )
    event_types = {event["eventType"] for event in events.json()["data"]}
    assert {"task_card.created", "agent_plan.decided"} <= event_types


async def test_task_card_blocked_by_open_clarification_and_release_gate(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    work_item_id = await _seed_work_item(client, profile)

    # 未解澄清阻塞固化
    session_id = str(uuid.uuid4())
    planning_workflow_service.sessions[session_id] = {
        "id": session_id,
        "tenantId": profile["tenantId"],
        "workspaceId": profile["workspaceId"],
        "workItemId": work_item_id,
        "status": "RUNNING",
        "createdAt": "2026-08-31T00:00:00+00:00",
        "updatedAt": "2026-08-31T00:00:00+00:00",
    }
    clarification = await planning_workflow_service.create_clarification_request(
        str(profile["tenantId"]),
        "agent-runner",
        "SERVICE",
        frozenset(["clarification.raise"]),
        "wp56-raise-000000000001",
        session_id,
        {"question": "口径?", "reason": "冲突", "impact": "验收判据"},
    )
    blocked = await client.post(
        f"/api/v1/work-items/{work_item_id}/task-cards",
        headers=mutation_headers(client, idempotency_key="wp56-card-0000000010"),
        json=_task_card_body(),
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "CLARIFICATION_OPEN"

    # 答复解除后可固化
    import hashlib

    answered = await client.post(
        f"/api/v1/clarifications/{clarification['id']}/responses",
        headers=mutation_headers(client, idempotency_key="wp56-respond-000001"),
        json={
            "answerRef": "evidence://v3",
            "answerDigest": hashlib.sha256("以 v3 为准".encode()).hexdigest(),
        },
    )
    assert answered.status_code == 201
    unblocked = await client.post(
        f"/api/v1/work-items/{work_item_id}/task-cards",
        headers=mutation_headers(client, idempotency_key="wp56-card-0000000011"),
        json=_task_card_body(),
    )
    assert unblocked.status_code == 201, unblocked.text

    # 无 Release 交付任务 → 409（工作项与卡都不带 Release）
    bare_item = await _seed_work_item(client, profile, with_release=False)
    assert planning_workflow_service.work_items[bare_item].get("releaseId") is None
    denied = await client.post(
        f"/api/v1/work-items/{bare_item}/task-cards",
        headers=mutation_headers(client, idempotency_key="wp56-card-0000000012"),
        json=_task_card_body(),
    )
    assert denied.status_code == 409
    assert denied.json()["code"] == "TASK_CARD_REQUIRES_RELEASE"

    # AGENT 自批拒绝（服务面角色门）
    plan = await client.post(
        f"/api/v1/work-items/{work_item_id}/agent-plans",
        headers=mutation_headers(client, idempotency_key="wp56-plan-0000000010"),
        json=_plan_body(unblocked.json()["data"]["id"]),
    )
    assert plan.status_code == 201
    with pytest.raises(DomainError) as agent_denied:
        await planning_workflow_service.decide_agent_plan(
            str(profile["tenantId"]),
            str(profile["workspaceId"]),
            "agent-runner",
            "AGENT",
            frozenset(["agent_plan.decide"]),
            "wp56-decide-0000000010",
            plan.json()["data"]["id"],
            {
                "decision": "APPROVE",
                "expectedContentDigest": plan.json()["data"]["contentDigest"],
                "reason": "自批",
            },
        )
    assert agent_denied.value.status_code == 403


async def test_session_requires_approved_plan(client: AsyncClient) -> None:
    """QF-PD-003 强制门：无已批准 AgentPlan 的工作项不能启动 Session（批次五十七）。"""
    import hashlib as _hashlib

    from tests.test_planning_workflow import SOURCE_SNAPSHOT_ID

    profile = await setup_identity(client)
    work_item_id = await _seed_work_item(client, profile)

    requirement = await client.post(
        "/api/v1/knowledge/requirements",
        headers=mutation_headers(client),
        json={"workspaceId": profile["workspaceId"], "name": "批准门需求", "documentType": "PRD"},
    )
    assert requirement.status_code == 201
    content = "# 批准门\n无计划不得启动。"
    version = await client.post(
        f"/api/v1/knowledge/requirements/{requirement.json()['data']['id']}/versions",
        headers=mutation_headers(client),
        json={
            "sourceSnapshotId": str(SOURCE_SNAPSHOT_ID),
            "contentDigest": _hashlib.sha256(content.encode()).hexdigest(),
            "content": content,
            "changeSummary": "首版",
        },
    )
    assert version.status_code == 201

    denied = await client.post(
        "/api/v1/ai/sessions",
        headers=mutation_headers(client, idempotency_key="wp57-session-00001"),
        json={
            "workspaceId": profile["workspaceId"],
            "workItemId": work_item_id,
            "workflowKey": "gate0-planning-slice",
            "requirementVersionId": version.json()["data"]["id"],
            "releaseId": await active_release_id(client, profile["workspaceId"]),
            "ownerId": profile["userId"],
        },
    )
    assert denied.status_code == 409
    assert denied.json()["code"] == "AGENT_PLAN_NOT_APPROVED"
