"""JWT + SQLite end-to-end tests for the local planning and review slice."""

from __future__ import annotations

import hashlib
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from httpx import AsyncClient

from qf.services.auth_service import CSRF_COOKIE, hash_password
from qf.services.planning_workflow import PlanningWorkflowService

SOURCE_SNAPSHOT_ID = uuid.UUID("00000000-0000-0000-0000-000000000030")
LOCAL_PASSWORD = "Local-review-password-2026"


async def active_release_id(client: AsyncClient, workspace_id: str) -> str:
    """认证初始化为工作区种子一条 ACTIVE Release；用例必须使用该真实归属 id（WP-01A 门控）。"""
    response = await client.get(f"/api/v1/workspaces/{workspace_id}/releases")
    assert response.status_code == 200, response.text
    releases = response.json()["data"]
    assert releases, "认证初始化应至少种子一条 ACTIVE Release"
    return str(releases[0]["id"])


async def setup_identity(client: AsyncClient, email: str = "reviewer@qualityforge.example") -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/setup",
        json={
            "email": email,
            "password": LOCAL_PASSWORD,
            "tenantName": "本地质量团队",
            "workspaceName": "退款项目",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def mutation_headers(client: AsyncClient, *, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {"X-CSRF-Token": client.cookies[CSRF_COOKIE]}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


async def prepare_source_and_work_item(client: AsyncClient, profile: dict[str, Any]) -> tuple[str, str]:
    workspace_id = profile["workspaceId"]
    requirement_response = await client.post(
        "/api/v1/knowledge/requirements",
        headers=mutation_headers(client),
        json={"workspaceId": workspace_id, "name": "订单退款需求", "documentType": "PRD"},
    )
    assert requirement_response.status_code == 201
    requirement_id = requirement_response.json()["data"]["id"]

    content = "# 订单退款\n用户可对已支付订单申请退款。\n非法状态和越权请求必须被拒绝。"
    version_response = await client.post(
        f"/api/v1/knowledge/requirements/{requirement_id}/versions",
        headers=mutation_headers(client),
        json={
            "sourceSnapshotId": str(SOURCE_SNAPSHOT_ID),
            "contentDigest": hashlib.sha256(content.encode()).hexdigest(),
            "content": content,
            "changeSummary": "首版",
        },
    )
    assert version_response.status_code == 201
    requirement_version_id = version_response.json()["data"]["id"]

    work_item_response = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client),
        json={
            "workspaceId": workspace_id,
            "releaseId": await active_release_id(client, workspace_id),
            "workItemType": "STRATEGY",
            "title": "生成退款测试资产",
            "objective": "验证退款链路的合法与非法路径均被正确处理",
            "acceptanceCriteria": "非法状态与越权请求全部被拒绝，合法退款路径全程可走通",
            "requiresReview": True,
            "priority": "P0",
            "riskLevel": "HIGH",
        },
    )
    assert work_item_response.status_code == 201
    work_item_id = work_item_response.json()["data"]["id"]

    # 批次五十七批准门前置：助手链自动固化任务卡并批准计划（QF-PD-003 计划先确认）
    import uuid as _uuid

    nonce = _uuid.uuid4().hex
    card = await client.post(
        f"/api/v1/work-items/{work_item_id}/task-cards",
        headers=mutation_headers(client, idempotency_key=f"helper-card-{nonce}"),
        json={
            "objective": "助手链任务卡",
            "scope": "测试助手自动固化",
            "acceptanceCriteria": "会话可启动",
            "constraints": "无",
            "requestedPermissions": [],
            "budget": {},
        },
    )
    assert card.status_code == 201, card.text
    plan = await client.post(
        f"/api/v1/work-items/{work_item_id}/agent-plans",
        headers=mutation_headers(client, idempotency_key=f"helper-plan-{nonce}"),
        json={
            "taskCardId": card.json()["data"]["id"],
            "steps": [{"stepKey": "run", "agentRole": "coordinator", "description": "助手链步骤"}],
        },
    )
    assert plan.status_code == 201, plan.text
    decision = await client.post(
        f"/api/v1/agent-plans/{plan.json()['data']['id']}/decisions",
        headers=mutation_headers(client, idempotency_key=f"helper-decide-{nonce}"),
        json={
            "decision": "APPROVE",
            "expectedContentDigest": plan.json()["data"]["contentDigest"],
            "reason": "助手链批准",
        },
    )
    assert decision.status_code == 201, decision.text
    return requirement_version_id, work_item_id


async def start_session(
    client: AsyncClient,
    profile: dict[str, Any],
    idempotency_key: str = "session-key-00000001",
) -> dict[str, Any]:
    requirement_version_id, work_item_id = await prepare_source_and_work_item(client, profile)
    response = await client.post(
        "/api/v1/ai/sessions",
        headers=mutation_headers(client, idempotency_key=idempotency_key),
        json={
            "workspaceId": profile["workspaceId"],
            "workItemId": work_item_id,
            "workflowKey": "gate0-planning-slice",
            "requirementVersionId": requirement_version_id,
            "releaseId": await active_release_id(client, profile["workspaceId"]),
            "ownerId": profile["userId"],
        },
    )
    assert response.status_code == 202, response.text
    return response.json()["data"]


async def test_local_setup_login_cookie_and_csrf_are_enforced(client: AsyncClient) -> None:
    status_response = await client.get("/api/v1/auth/status")
    assert status_response.json()["data"]["setupRequired"] is True
    assert status_response.json()["data"]["authenticated"] is False
    assert status_response.json()["data"]["profile"] is None

    setup_response = await client.post(
        "/api/v1/auth/setup",
        json={
            "email": "reviewer@qualityforge.example",
            "password": LOCAL_PASSWORD,
            "tenantName": "本地质量团队",
            "workspaceName": "退款项目",
        },
    )
    assert setup_response.status_code == 201
    profile = setup_response.json()["data"]
    assert profile["actorType"] == "USER"
    set_cookies = setup_response.headers.get_list("set-cookie")
    assert any("qf_access=" in value and "HttpOnly" in value and "SameSite=strict" in value for value in set_cookies)
    assert client.cookies.get(CSRF_COOKIE)

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["workspaceId"] == profile["workspaceId"]

    authenticated_status = await client.get("/api/v1/auth/status")
    assert authenticated_status.status_code == 200
    assert authenticated_status.json()["data"]["authenticated"] is True
    assert authenticated_status.json()["data"]["profile"]["userId"] == profile["userId"]

    csrf_failure = await client.post(
        "/api/v1/work-items",
        json={
            "workspaceId": profile["workspaceId"],
            "workItemType": "GENERAL",
            "title": "缺少CSRF",
            "priority": "P2",
            "riskLevel": "LOW",
        },
    )
    assert csrf_failure.status_code == 403
    assert csrf_failure.json()["code"] == "CSRF_VALIDATION_FAILED"

    second_setup = await client.post(
        "/api/v1/auth/setup",
        json={
            "email": "another@qualityforge.example",
            "password": LOCAL_PASSWORD,
            "tenantName": "另一个租户",
            "workspaceName": "另一个项目",
        },
    )
    assert second_setup.status_code == 409


async def test_full_flow_persists_across_service_restart(client: AsyncClient, sqlite_path: Path) -> None:
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    # QF-REQ-078（M1-B1 有意变更）：PAUSED_FOR_HUMAN → 契约枚举 BLOCKED
    assert session["status"] == "BLOCKED"
    assert len(session["artifactRefs"]) == 4
    assert len(session["reviewTaskIds"]) == 4
    assert session["traceCount"] == 6

    reloaded = PlanningWorkflowService(str(sqlite_path))
    persisted_session = await reloaded.get_session(profile["tenantId"], profile["workspaceId"], session["id"])
    assert persisted_session["reviewTaskIds"] == session["reviewTaskIds"]
    assert len(await reloaded.get_trace(profile["tenantId"], profile["workspaceId"], session["id"])) == 6

    reviews = (await client.get("/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]})).json()["data"]
    for index, review in enumerate(reviews, start=1):
        artifact_response = await client.get(f"/api/v1/review-tasks/{review['id']}/artifact")
        assert artifact_response.status_code == 200
        assert artifact_response.json()["data"]["contentDigest"] == review["contentDigest"]
        decision_response = await client.post(
            f"/api/v1/review-tasks/{review['id']}/decisions",
            headers=mutation_headers(client, idempotency_key=f"review-key-{index:08d}"),
            json={"decision": "APPROVE", "contentDigest": review["contentDigest"], "comments": "审核通过"},
        )
        assert decision_response.status_code == 200

    completed = await client.get(f"/api/v1/ai/sessions/{session['id']}")
    # QF-REQ-078（M1-B1 有意变更）：COMPLETED → 契约枚举 SUCCEEDED
    assert completed.json()["data"]["status"] == "SUCCEEDED"
    completed_trace = await client.get(f"/api/v1/ai/sessions/{session['id']}/trace")
    assert completed_trace.status_code == 200
    assert completed_trace.json()["data"][-1]["nodeId"] == "human_gate_completed"
    assert completed_trace.json()["data"][-1]["status"] == "SUCCEEDED"
    restarted_again = PlanningWorkflowService(str(sqlite_path))
    assert (await restarted_again.get_session(profile["tenantId"], profile["workspaceId"], session["id"]))[
        "status"
    ] == "SUCCEEDED"


async def test_agent_jwt_cannot_approve_formal_artifact(client: AsyncClient, sqlite_path: Path) -> None:
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    review = (await client.get(f"/api/v1/review-tasks/{session['reviewTaskIds'][0]}")).json()["data"]

    with sqlite3.connect(sqlite_path) as connection:
        connection.execute("UPDATE tenant_memberships SET actor_type = 'AGENT'")
    client.cookies.clear()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "reviewer@qualityforge.example", "password": LOCAL_PASSWORD},
    )
    assert login.status_code == 200
    response = await client.post(
        f"/api/v1/review-tasks/{review['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="agent-review-0001"),
        json={"decision": "APPROVE", "contentDigest": review["contentDigest"]},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


async def test_digest_idempotency_and_workspace_scope_fail_closed(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    review_id = session["reviewTaskIds"][0]
    stale = await client.post(
        f"/api/v1/review-tasks/{review_id}/decisions",
        headers=mutation_headers(client, idempotency_key="stale-review-0001"),
        json={"decision": "APPROVE", "contentDigest": "0" * 64},
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "STALE_ARTIFACT_VERSION"

    wrong_workspace = await client.get("/api/v1/work-items", params={"workspaceId": str(uuid.uuid4())})
    assert wrong_workspace.status_code == 403

    requirement_version_id, work_item_id = await prepare_source_and_work_item(client, profile)
    body = {
        "workspaceId": profile["workspaceId"],
        "workItemId": work_item_id,
        "workflowKey": "gate0-planning-slice",
        "requirementVersionId": requirement_version_id,
        "releaseId": await active_release_id(client, profile["workspaceId"]),
        "ownerId": profile["userId"],
    }
    headers = mutation_headers(client, idempotency_key="session-replay-0001")
    first = await client.post("/api/v1/ai/sessions", headers=headers, json=body)
    second = await client.post("/api/v1/ai/sessions", headers=headers, json=body)
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    conflict = await client.post(
        "/api/v1/ai/sessions",
        headers=headers,
        json={**body, "ownerId": str(uuid.uuid4())},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_second_tenant_cannot_read_first_tenant_session(client: AsyncClient, sqlite_path: Path) -> None:
    first_profile = await setup_identity(client)
    first_session = await start_session(client, first_profile)
    second_tenant = str(uuid.uuid4())
    second_workspace = str(uuid.uuid4())
    second_user = str(uuid.uuid4())
    second_email = "isolated@qualityforge.example"
    with sqlite3.connect(sqlite_path) as connection:
        connection.execute("INSERT INTO tenants VALUES (?, ?, datetime('now'))", (second_tenant, "隔离租户"))
        connection.execute(
            "INSERT INTO workspaces VALUES (?, ?, ?, datetime('now'))",
            (second_workspace, second_tenant, "隔离项目"),
        )
        connection.execute(
            "INSERT INTO users(id, email, password_hash, is_active, created_at) VALUES (?, ?, ?, 1, datetime('now'))",
            (second_user, second_email, hash_password(LOCAL_PASSWORD)),
        )
        connection.execute(
            "INSERT INTO tenant_memberships VALUES (?, ?, ?, 'USER', ?, 1)",
            (second_tenant, second_user, second_workspace, "[]"),
        )
    client.cookies.clear()
    login = await client.post("/api/v1/auth/login", json={"email": second_email, "password": LOCAL_PASSWORD})
    assert login.status_code == 200
    response = await client.get(f"/api/v1/ai/sessions/{first_session['id']}")
    assert response.status_code == 404


async def test_missing_login_and_requirement_digest_tampering_are_rejected(client: AsyncClient) -> None:
    missing_login = await client.get("/api/v1/work-items", params={"workspaceId": str(uuid.uuid4())})
    assert missing_login.status_code == 401
    profile = await setup_identity(client)
    requirement = await client.post(
        "/api/v1/knowledge/requirements",
        headers=mutation_headers(client),
        json={"workspaceId": profile["workspaceId"], "name": "摘要校验", "documentType": "PRD"},
    )
    tampered = await client.post(
        f"/api/v1/knowledge/requirements/{requirement.json()['data']['id']}/versions",
        headers=mutation_headers(client),
        json={
            "sourceSnapshotId": str(SOURCE_SNAPSHOT_ID),
            "contentDigest": "0" * 64,
            "content": "真实正文",
        },
    )
    assert tampered.status_code == 422
    assert tampered.json()["code"] == "VALIDATION_FAILED"
