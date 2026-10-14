"""TC-COL-001~006：协作域可执行层（批次六十九，WP-03 已实现面）。

覆盖：对话创建与只追加消息、澄清答复闭环（重复答复 409）、任务卡固化、
AgentPlan 摘要漂移 409 与批准联动、终态重复裁决 409、批准门（R-COL-001~005）。

澄清种子（createClarificationRequest 的 raise 面归 AGENT/SERVICE 服务面）
经 planning_workflow_service 服务面构造——真实 HTTP 面随 agent 运行时开放。
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from conftest import data_of, envelope, gate0_session, mutation_headers, setup_identity

from qf.services.planning_workflow import planning_workflow_service


async def _seeded_work_item(client: AsyncClient, profile: dict) -> str:
    """复用 gate0 链的工作项（其任务卡/计划已批准，无未解澄清）。"""
    session = await gate0_session(client, profile)
    return str(session["workItemId"])


async def _raise_clarification(profile: dict, session_id: str) -> str:
    """服务面种子 OPEN 澄清（AGENT 角色门承载，HTTP raise 面随 agent 运行时开放）。"""
    clarification = await planning_workflow_service.create_clarification_request(
        str(profile["tenantId"]),
        "agent-runner",
        "AGENT",
        frozenset({"clarification.raise"}),
        f"col-clarify-{uuid.uuid4().hex[:12]}",
        session_id,
        {
            "question": "退款金额上限按订单实付还是应付口径？",
            "reason": "需求口径歧义，影响断言上限",
            "impact": "HIGH",
        },
    )
    return str(clarification["id"])


async def test_tc_col_001_conversation_append_only(client: AsyncClient) -> None:
    """TC-COL-001：协作会话创建 + 消息只追加两面。"""
    profile = await setup_identity(client)

    created = await client.post(
        "/api/v1/conversations",
        headers=mutation_headers(client, f"col-conv-{uuid.uuid4().hex[:12]}"),
        json={"workspaceId": profile["workspaceId"], "title": "退款链路澄清协作"},
    )
    assert created.status_code == 201, created.text
    conversation = data_of(created)
    assert conversation["id"]
    assert conversation["status"] == "ACTIVE"

    listed = data_of(
        await client.get(
            "/api/v1/conversations", params={"workspaceId": profile["workspaceId"]}
        )
    )
    assert any(item["id"] == conversation["id"] for item in listed)

    content_ref = "请归纳退款异常路径的业务规则"
    import hashlib as _hashlib

    message = await client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=mutation_headers(client, f"col-msg-{uuid.uuid4().hex[:12]}"),
        json={
            "messageType": "TEXT",
            "contentRef": content_ref,
            "contentDigest": _hashlib.sha256(content_ref.encode()).hexdigest(),
            "dataClass": "INTERNAL",
        },
    )
    assert message.status_code == 201, message.text
    body = data_of(message)
    assert len(body["contentDigest"]) == 64
    assert body["actorType"] == "USER"

    messages = data_of(
        await client.get(f"/api/v1/conversations/{conversation['id']}/messages")
    )
    assert len(messages) == 1
    assert messages[0]["contentRef"] == content_ref


async def test_tc_col_002_clarification_response_and_duplicate_rejected(
    client: AsyncClient,
) -> None:
    """TC-COL-002：澄清答复形成 CONFIRMED 证据，重复答复 409。"""
    profile = await setup_identity(client)
    session = await gate0_session(client, profile)
    clarification_id = await _raise_clarification(profile, str(session["id"]))

    listed = await client.get(
        f"/api/v1/ai/sessions/{session['id']}/clarifications",
        params={"workspaceId": profile["workspaceId"]},
    )
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == clarification_id for item in data_of(listed)), listed.text

    answer_ref = "按订单实付金额口径"
    answered = await client.post(
        f"/api/v1/clarifications/{clarification_id}/responses",
        headers=mutation_headers(client, f"col-resp-{uuid.uuid4().hex[:12]}"),
        json={
            "answerRef": answer_ref,
            "answerDigest": "c" * 64,
        },
    )
    assert answered.status_code == 201, answered.text  # 实现返回 201（设计用例 200 已同步修正）
    assert data_of(answered)["evidenceClass"] == "CONFIRMED"

    duplicate = await client.post(
        f"/api/v1/clarifications/{clarification_id}/responses",
        headers=mutation_headers(client, f"col-resp2-{uuid.uuid4().hex[:11]}"),
        json={"answerRef": "重复答复", "answerDigest": "d" * 64},
    )
    assert duplicate.status_code == 409
    assert envelope(duplicate)["code"] == "CLARIFICATION_ALREADY_ANSWERED"


async def test_tc_col_003_task_card_submit_and_list(client: AsyncClient) -> None:
    """TC-COL-003：任务卡固化提交即 SUBMITTED 并可回读。"""
    profile = await setup_identity(client)
    work_item_id = await _seeded_work_item(client, profile)

    card = await client.post(
        f"/api/v1/work-items/{work_item_id}/task-cards",
        headers=mutation_headers(client, f"col-card-{uuid.uuid4().hex[:12]}"),
        json={
            "objective": "生成退款链路回归资产",
            "scope": "合法与非法路径各一批",
            "acceptanceCriteria": "策略/计划/用例三层齐备",
            "constraints": "不引入外部服务",
            "requestedPermissions": ["requirement.write"],
            "budget": {"maxMinutes": 30},
        },
    )
    assert card.status_code == 201, card.text
    assert data_of(card)["status"] == "SUBMITTED"

    listed = data_of(await client.get(f"/api/v1/work-items/{work_item_id}/task-cards"))
    assert any(item["id"] == data_of(card)["id"] for item in listed)


async def test_tc_col_004_agent_plan_digest_drift_and_approval(
    client: AsyncClient,
) -> None:
    """TC-COL-004：摘要漂移 409 + 正确摘要批准联动任务卡 ACTIVE。"""
    profile = await setup_identity(client)
    session = await gate0_session(client, profile)
    work_item_id = str(session["workItemId"])

    card = await client.post(
        f"/api/v1/work-items/{work_item_id}/task-cards",
        headers=mutation_headers(client, f"col-card4-{uuid.uuid4().hex[:10]}"),
        json={
            "objective": "摘要漂移验证任务",
            "scope": "计划裁决链",
            "acceptanceCriteria": "漂移拒绝",
            "constraints": "无",
            "requestedPermissions": [],
            "budget": {},
        },
    )
    assert card.status_code == 201, card.text
    submitted = data_of(card)
    assert submitted["status"] == "SUBMITTED"

    plan = await client.post(
        f"/api/v1/work-items/{work_item_id}/agent-plans",
        headers=mutation_headers(client, f"col-plan-{uuid.uuid4().hex[:12]}"),
        json={
            "taskCardId": submitted["id"],
            "steps": [
                {
                    "stepKey": "summarize",
                    "agentRole": "coordinator",
                    "description": "需求归纳",
                },
                {
                    "stepKey": "cases",
                    "agentRole": "case-designer",
                    "description": "用例编制",
                },
            ],
        },
    )
    assert plan.status_code == 201, plan.text
    plan_data = data_of(plan)
    assert plan_data["status"] == "PENDING_APPROVAL"

    drift = await client.post(
        f"/api/v1/agent-plans/{plan_data['id']}/decisions",
        headers=mutation_headers(client, f"col-drift-{uuid.uuid4().hex[:11]}"),
        json={
            "decision": "APPROVE",
            "expectedContentDigest": "b" * 64,
            "reason": "摘要漂移负向",
        },
    )
    assert drift.status_code == 409
    assert envelope(drift)["code"] == "STALE_ARTIFACT_VERSION"

    approved = await client.post(
        f"/api/v1/agent-plans/{plan_data['id']}/decisions",
        headers=mutation_headers(client, f"col-approve-{uuid.uuid4().hex[:10]}"),
        json={
            "decision": "APPROVE",
            "expectedContentDigest": plan_data["contentDigest"],
            "reason": "计划确认",
        },
    )
    assert approved.status_code == 201, approved.text
    assert data_of(approved)["decision"] == "APPROVE"

    plans_state = data_of(
        await client.get(
            f"/api/v1/work-items/{work_item_id}/agent-plans",
            params={"workspaceId": profile["workspaceId"]},
        )
    )
    assert any(
        p["id"] == plan_data["id"] and p["status"] == "APPROVED" for p in plans_state
    )

    cards_after = data_of(
        await client.get(
            f"/api/v1/work-items/{work_item_id}/task-cards",
            params={"workspaceId": profile["workspaceId"]},
        )
    )
    assert (
        next(c for c in cards_after if c["id"] == submitted["id"])["status"] == "ACTIVE"
    )


async def test_tc_col_005_terminal_plan_decision_rejected(client: AsyncClient) -> None:
    """TC-COL-005：终态计划重复裁决 409 与版本链回读。"""
    profile = await setup_identity(client)
    session = await gate0_session(client, profile)
    work_item_id = str(session["workItemId"])

    plans = data_of(
        await client.get(
            f"/api/v1/work-items/{work_item_id}/agent-plans",
            params={"workspaceId": profile["workspaceId"]},
        )
    )
    approved_plan = next(p for p in plans if p["status"] == "APPROVED")

    re_decided = await client.post(
        f"/api/v1/agent-plans/{approved_plan['id']}/decisions",
        headers=mutation_headers(client, f"col-redecide-{uuid.uuid4().hex[:9]}"),
        json={
            "decision": "REJECT",
            "expectedContentDigest": approved_plan["contentDigest"],
            "reason": "重复裁决负向",
        },
    )
    assert re_decided.status_code == 409
    assert envelope(re_decided)["code"] == "INVALID_STATE_TRANSITION"

    plans_after = data_of(
        await client.get(
            f"/api/v1/work-items/{work_item_id}/agent-plans",
            params={"workspaceId": profile["workspaceId"]},
        )
    )
    assert any(
        p["id"] == approved_plan["id"] and p["status"] == "APPROVED"
        for p in plans_after
    ), "重复裁决不得改变终态"


async def test_tc_col_006_session_requires_approved_plan(client: AsyncClient) -> None:
    """TC-COL-006：无已批准计划的工作项启动会话 409 AGENT_PLAN_NOT_APPROVED。"""
    import hashlib

    profile = await setup_identity(client)
    ws = profile["workspaceId"]
    releases = data_of(await client.get(f"/api/v1/workspaces/{ws}/releases"))
    release_id = releases[0]["id"]

    requirement = await client.post(
        "/api/v1/knowledge/requirements",
        headers=mutation_headers(client, f"col-req-{uuid.uuid4().hex[:12]}"),
        json={"workspaceId": ws, "name": "批准门需求", "documentType": "PRD"},
    )
    requirement_id = data_of(requirement)["id"]
    content = "# 批准门\n未经计划确认不得启动。"
    version = await client.post(
        f"/api/v1/knowledge/requirements/{requirement_id}/versions",
        headers=mutation_headers(client, f"col-ver-{uuid.uuid4().hex[:12]}"),
        json={
            "sourceSnapshotId": "00000000-0000-0000-0000-000000000030",
            "contentDigest": hashlib.sha256(content.encode()).hexdigest(),
            "content": content,
            "changeSummary": "首版",
        },
    )
    version_id = data_of(version)["id"]
    work_item = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client, f"col-wi-{uuid.uuid4().hex[:13]}"),
        json={
            "workspaceId": ws,
            "releaseId": release_id,
            "workItemType": "STRATEGY",
            "title": "无计划工作项",
            "objective": "验证批准门",
            "acceptanceCriteria": "409",
            "requiresReview": True,
            "priority": "P2",
            "riskLevel": "MEDIUM",
        },
    )
    work_item_id = data_of(work_item)["id"]

    rejected = await client.post(
        "/api/v1/ai/sessions",
        headers=mutation_headers(client, f"col-sess-{uuid.uuid4().hex[:12]}"),
        json={
            "workspaceId": ws,
            "workItemId": work_item_id,
            "workflowKey": "gate0-planning-slice",
            "requirementVersionId": version_id,
            "releaseId": release_id,
            "ownerId": profile["userId"],
        },
    )
    assert rejected.status_code == 409
    assert envelope(rejected)["code"] == "AGENT_PLAN_NOT_APPROVED"
