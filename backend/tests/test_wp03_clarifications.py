"""WP-03 澄清链路专项（批次五十五，39 号 §3 切片二）。

覆盖：发起的角色门与 BLOCKED 联动（服务面）、列表与跨 Workspace 门控、
人工答复的 CONFIRMED 证据与解除联动、重复答复/非 OPEN/404 负向。
raise 的 HTTP 路由保持延期（本地认证只签 USER 令牌，正路归 agent 运行时）。
"""

from __future__ import annotations

import hashlib
import uuid

import pytest
from httpx import AsyncClient

from qf.services.planning_workflow import DomainError, planning_workflow_service
from tests.test_planning_workflow import mutation_headers, setup_identity

SESSION_TERMINAL = {"SUCCEEDED", "FAILED"}


def _running_session(profile: dict, work_item_id: str) -> str:
    """测试种子：注入一个 RUNNING 态 Session（clarification 承载面）。"""
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
    return session_id


async def _seed_work_item(client: AsyncClient, profile: dict) -> str:
    from tests.test_planning_workflow import active_release_id
    from tests.test_wp01a_workspace_context import _work_item_body

    release_id = await active_release_id(client, profile["workspaceId"])
    created = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client),
        json=_work_item_body(profile["workspaceId"], release_id),
    )
    assert created.status_code == 201
    return created.json()["data"]["id"]


async def _raise(profile: dict, session_id: str, **overrides) -> dict:
    payload = {
        "question": "退款风控阈值以哪个版本为准？",
        "reason": "两份需求文档口径冲突",
        "impact": "影响策略生成的边界用例",
        "requiredBy": "2026-09-02T00:00:00+00:00",
    }
    payload.update(overrides)
    return await planning_workflow_service.create_clarification_request(
        str(profile["tenantId"]),
        "agent-runner",
        "SERVICE",
        frozenset(["clarification.raise"]),
        "wp55-raise-000000000001",
        session_id,
        payload,
    )


async def test_clarification_raise_blocks_session_and_listing(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    work_item_id = await _seed_work_item(client, profile)
    session_id = _running_session(profile, work_item_id)

    # USER 冒用被角色门拒绝
    with pytest.raises(DomainError) as denied:
        await planning_workflow_service.create_clarification_request(
            str(profile["tenantId"]),
            str(profile["userId"]),
            "USER",
            frozenset(["clarification.raise"]),
            "wp55-raise-00000000000x",
            session_id,
            {"question": "q", "reason": "r", "impact": "i"},
        )
    assert denied.value.status_code == 403

    clarification = await _raise(profile, session_id)
    assert clarification["status"] == "OPEN"
    assert clarification["workItemId"] == work_item_id
    # 提出后 Session 转 BLOCKED
    assert planning_workflow_service.sessions[session_id]["status"] == "BLOCKED"

    listed = await client.get(
        f"/api/v1/ai/sessions/{session_id}/clarifications",
        params={"workspaceId": profile["workspaceId"]},
    )
    assert listed.status_code == 200
    assert any(item["id"] == clarification["id"] for item in listed.json()["data"])

    # 跨 Workspace / 不存在 Session
    assert (
        await client.get(
            f"/api/v1/ai/sessions/{session_id}/clarifications",
            params={"workspaceId": str(uuid.uuid4())},
        )
    ).status_code == 403
    assert (
        await client.get(
            f"/api/v1/ai/sessions/{uuid.uuid4()}/clarifications",
            params={"workspaceId": profile["workspaceId"]},
        )
    ).status_code == 404

    # 终态 Session 拒绝再发起
    planning_workflow_service.sessions[session_id]["status"] = "SUCCEEDED"
    with pytest.raises(DomainError) as terminal:
        await _raise(profile, session_id, question="再来一条")
    assert terminal.value.status_code == 409
    planning_workflow_service.sessions[session_id]["status"] = "BLOCKED"


async def test_respond_clarification_forms_evidence_and_unblocks(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    work_item_id = await _seed_work_item(client, profile)
    session_id = _running_session(profile, work_item_id)
    clarification = await _raise(profile, session_id)

    answered = await client.post(
        f"/api/v1/clarifications/{clarification['id']}/responses",
        headers=mutation_headers(client, idempotency_key="wp55-respond-00001"),
        json={
            "answerRef": "evidence://rfi-threshold-v3",
            "answerDigest": hashlib.sha256("以 v3 口径为准".encode()).hexdigest(),
        },
    )
    assert answered.status_code == 201, answered.text
    response = answered.json()["data"]
    assert response["evidenceClass"] == "CONFIRMED"
    assert response["respondedBy"] == profile["userId"]

    # 答复后：请求 ANSWERED + Session 无其他 OPEN → 解除 BLOCKED
    listed = await client.get(
        f"/api/v1/ai/sessions/{session_id}/clarifications",
        params={"workspaceId": profile["workspaceId"]},
    )
    row = next(item for item in listed.json()["data"] if item["id"] == clarification["id"])
    assert row["status"] == "ANSWERED"
    assert planning_workflow_service.sessions[session_id]["status"] == "RUNNING"

    # 幂等重放同条答复
    replay = await client.post(
        f"/api/v1/clarifications/{clarification['id']}/responses",
        headers=mutation_headers(client, idempotency_key="wp55-respond-00001"),
        json={
            "answerRef": "evidence://rfi-threshold-v3",
            "answerDigest": hashlib.sha256("以 v3 口径为准".encode()).hexdigest(),
        },
    )
    assert replay.status_code == 201
    assert replay.json()["data"]["id"] == response["id"]

    # 重复答复（新键）→ 409 已答复
    again = await client.post(
        f"/api/v1/clarifications/{clarification['id']}/responses",
        headers=mutation_headers(client, idempotency_key="wp55-respond-00002"),
        json={
            "answerRef": "evidence://again",
            "answerDigest": hashlib.sha256(b"again").hexdigest(),
        },
    )
    assert again.status_code == 409
    assert again.json()["code"] == "CLARIFICATION_ALREADY_ANSWERED"

    # 不存在 → 404；digest 非法 → 422
    assert (
        await client.post(
            f"/api/v1/clarifications/{uuid.uuid4()}/responses",
            headers=mutation_headers(client, idempotency_key="wp55-respond-00003"),
            json={"answerRef": "x", "answerDigest": "0" * 63},
        )
    ).status_code in {404, 422}
    bad_digest = await client.post(
        f"/api/v1/clarifications/{clarification['id']}/responses",
        headers=mutation_headers(client, idempotency_key="wp55-respond-00004"),
        json={"answerRef": "x", "answerDigest": "0" * 63},
    )
    assert bad_digest.status_code == 422

    # 事件登记
    events = await client.get(
        "/api/v1/observability/events",
        params={"workspaceId": profile["workspaceId"], "pageSize": 100},
    )
    event_types = {event["eventType"] for event in events.json()["data"]}
    assert {"clarification.requested", "clarification.responded"} <= event_types
