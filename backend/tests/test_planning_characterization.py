"""Characterization tests pinning current planning-chain behavior (M1-B0 基线).

目的（整改 P1-1）：在 M1-B1 退回/新版本改造前固化现状行为——任何非预期
行为变化都会在此处红灯。覆盖：工作项创建形状、会话生成三类产出物、
审核批准/退回后的状态机走向、摘要与状态守卫、列表端点可见性。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from httpx import AsyncClient

from tests.test_planning_workflow import (
    mutation_headers,
    setup_identity,
    start_session,
)


def _data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    body = response.json()
    assert "data" in body, body
    return body["data"]


async def test_work_item_creation_current_shape(client: AsyncClient) -> None:
    """创建工作项的现状形状：READY 起点、HUMAN 责任主体、六关键字段落库、严格拒收未知字段。"""
    profile = await setup_identity(client)
    payload = {
        "workspaceId": profile["workspaceId"],
        "workItemType": "STRATEGY",
        "title": "基线固化用工作项",
        "objective": "固化创建工作项的现状形状",
        "acceptanceCriteria": "六关键字段全部可见且默认值稳定",
        "requiresReview": True,
        "constraints": "仅限本地运行时",
        "priority": "P1",
        "riskLevel": "MEDIUM",
    }
    response = await client.post("/api/v1/work-items", headers=mutation_headers(client), json=payload)
    assert response.status_code == 201, response.text
    item = _data(response)
    assert item["status"] == "READY"
    assert item["currentActorType"] == "HUMAN"
    assert item["ownerId"] == item["assigneeId"] == profile["userId"]
    for key, value in payload.items():
        assert item[key] == value
    assert item["releaseId"] is None
    assert item["agentId"] is None
    assert item["lockVersion"] == 0

    # QF-REQ-001：契约 required 三字段缺失时入口层 422
    incomplete = {key: value for key, value in payload.items() if key != "acceptanceCriteria"}
    rejected_required = await client.post(
        "/api/v1/work-items", headers=mutation_headers(client), json=incomplete
    )
    assert rejected_required.status_code == 422

    rejected = await client.post(
        "/api/v1/work-items", headers=mutation_headers(client), json={**payload, "unknownField": True}
    )
    assert rejected.status_code == 422


async def test_session_run_generates_three_artifact_types_and_pauses(client: AsyncClient) -> None:
    """会话跑完 Gate 0 切片：三类产出物各至少一版，停在人工门禁。"""
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    # QF-REQ-078（M1-B1 有意变更）：PAUSED_FOR_HUMAN → 契约枚举 BLOCKED
    assert session["status"] == "BLOCKED"

    artifact_types = {ref["artifactType"] for ref in session["artifactRefs"]}
    assert artifact_types == {"TEST_STRATEGY", "TEST_PLAN", "TEST_CASE"}
    assert len(session["reviewTaskIds"]) == len(session["artifactRefs"])

    listed = _data(await client.get("/api/v1/work-items", params={"workspaceId": profile["workspaceId"]}))
    work_item = next(item for item in listed if item["id"] == session["workItemId"])
    assert work_item["status"] == "PENDING_REVIEW"
    assert work_item["currentActorType"] == "HUMAN"

    trace = _data(
        await client.get(f"/api/v1/ai/sessions/{session['id']}/trace", params={"workspaceId": profile["workspaceId"]})
    )
    node_ids = [event["nodeId"] for event in trace]
    assert node_ids[0] == "requirement_source_check"
    assert "human_gate" in node_ids
    sequences = [event["sequence"] for event in trace]
    assert sequences == list(range(1, len(trace) + 1))


async def test_approving_all_artifacts_completes_session(client: AsyncClient) -> None:
    """逐一审批通过：任务 APPROVED、会话 SUCCEEDED、工作项 APPROVED。"""
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    tasks = _data(
        await client.get("/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]})
    )
    assert len(tasks) == len(session["reviewTaskIds"])
    assert all(task["status"] == "OPEN" for task in tasks)

    for task in tasks:
        decision = await client.post(
            f"/api/v1/review-tasks/{task['id']}/decisions",
            headers=mutation_headers(client, idempotency_key=f"approve-{task['id']}"),
            json={"decision": "APPROVE", "contentDigest": task["contentDigest"], "comments": "基线批准"},
        )
        assert decision.status_code == 200, decision.text
        assert _data(decision)["status"] == "APPROVED"

    reloaded = _data(
        await client.get(
            f"/api/v1/ai/sessions/{session['id']}", params={"workspaceId": profile["workspaceId"]}
        )
    )
    # QF-REQ-078（M1-B1 有意变更）：COMPLETED → 契约枚举 SUCCEEDED
    assert reloaded["status"] == "SUCCEEDED"
    assert reloaded["completedAt"] is not None

    listed = _data(await client.get("/api/v1/work-items", params={"workspaceId": profile["workspaceId"]}))
    work_item = next(item for item in listed if item["id"] == session["workItemId"])
    assert work_item["status"] == "APPROVED"
    assert work_item["currentActorType"] == "NONE"


async def test_request_changes_puts_work_item_into_rework(client: AsyncClient) -> None:
    """任一任务退回：工作项进入 REWORK，会话保持人工阻塞态。"""
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    tasks = _data(
        await client.get("/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]})
    )
    target = tasks[0]
    decision = await client.post(
        f"/api/v1/review-tasks/{target['id']}/decisions",
        headers=mutation_headers(client, idempotency_key=f"rework-{target['id']}"),
        json={"decision": "REQUEST_CHANGES", "contentDigest": target["contentDigest"], "comments": "需补充边界"},
    )
    assert decision.status_code == 200, decision.text
    assert _data(decision)["status"] == "CHANGES_REQUESTED"

    reloaded = _data(
        await client.get(
            f"/api/v1/ai/sessions/{session['id']}", params={"workspaceId": profile["workspaceId"]}
        )
    )
    # QF-REQ-078（M1-B1 有意变更）：PAUSED_FOR_HUMAN → 契约枚举 BLOCKED
    assert reloaded["status"] == "BLOCKED"

    listed = _data(await client.get("/api/v1/work-items", params={"workspaceId": profile["workspaceId"]}))
    work_item = next(item for item in listed if item["id"] == session["workItemId"])
    assert work_item["status"] == "REWORK"
    assert work_item["currentActorType"] == "HUMAN"


async def test_decide_guards_stale_digest_and_closed_task(client: AsyncClient) -> None:
    """摘要不一致 409 STALE_ARTIFACT_VERSION；已决策任务 409 INVALID_STATE_TRANSITION。"""
    profile = await setup_identity(client)
    await start_session(client, profile)
    tasks = _data(
        await client.get("/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]})
    )
    target = tasks[0]

    # 现状行为：Idempotency-Key 短于 16 字符在入口层即 422（不进业务层）
    short_key = await client.post(
        f"/api/v1/review-tasks/{target['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="short-key"),
        json={"decision": "APPROVE", "contentDigest": target["contentDigest"]},
    )
    assert short_key.status_code == 422

    stale = await client.post(
        f"/api/v1/review-tasks/{target['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="stale-digest-key-001"),
        json={"decision": "APPROVE", "contentDigest": hashlib.sha256(b"tampered").hexdigest()},
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "STALE_ARTIFACT_VERSION"

    approved = await client.post(
        f"/api/v1/review-tasks/{target['id']}/decisions",
        headers=mutation_headers(client, idempotency_key=f"close-{target['id']}"),
        json={"decision": "APPROVE", "contentDigest": target["contentDigest"]},
    )
    assert approved.status_code == 200

    second = await client.post(
        f"/api/v1/review-tasks/{target['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="second-attempt-key-001"),
        json={"decision": "APPROVE", "contentDigest": target["contentDigest"]},
    )
    assert second.status_code == 409
    assert second.json()["code"] == "INVALID_STATE_TRANSITION"


async def test_list_endpoints_expose_generated_artifacts(client: AsyncClient) -> None:
    """生成后各列表端点可见对应实体；产出物正文可经审核任务取回。"""
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    params = {"workspaceId": profile["workspaceId"]}

    requirements = _data(await client.get("/api/v1/knowledge/requirements", params=params))
    assert len(requirements) == 1
    strategies = _data(await client.get("/api/v1/test-strategies", params=params))
    plans = _data(await client.get("/api/v1/test-plans", params=params))
    cases = _data(await client.get("/api/v1/test-cases", params=params))
    assert len(strategies) == 1 and len(plans) == 1 and len(cases) >= 1

    case_versions = _data(
        await client.get(f"/api/v1/test-cases/{cases[0]['id']}/versions", params=params)
    )
    assert len(case_versions) == 1 and case_versions[0]["version"] == 1

    sessions = _data(await client.get("/api/v1/ai/sessions", params=params))
    assert any(entry["id"] == session["id"] for entry in sessions)

    tasks = _data(await client.get("/api/v1/review-tasks", params=params))
    strategy_task = next(task for task in tasks if task["artifactType"] == "TEST_STRATEGY")
    single = _data(await client.get(f"/api/v1/review-tasks/{strategy_task['id']}", params=params))
    assert single["id"] == strategy_task["id"]
    artifact = _data(
        await client.get(f"/api/v1/review-tasks/{strategy_task['id']}/artifact", params=params)
    )
    assert artifact["contentDigest"] == strategy_task["contentDigest"]
    assert artifact["content"]


async def test_planning_chain_survives_reload_within_same_store(client: AsyncClient, sqlite_path: Path) -> None:
    """基线锚点：同一 SQLite 文件上重挂服务后审批链仍可继续（防改造破坏持久化）。"""
    from qf.services.planning_workflow import planning_workflow_service

    profile = await setup_identity(client)
    session = await start_session(client, profile)
    tasks_before = _data(
        await client.get("/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]})
    )

    planning_workflow_service.reconfigure(str(sqlite_path))

    tasks_after = _data(
        await client.get("/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]})
    )
    assert {task["id"] for task in tasks_before} == {task["id"] for task in tasks_after}
    target = tasks_after[0]
    decision = await client.post(
        f"/api/v1/review-tasks/{target['id']}/decisions",
        headers=mutation_headers(client, idempotency_key=f"reload-{target['id']}"),
        json={"decision": "APPROVE", "contentDigest": target["contentDigest"]},
    )
    assert decision.status_code == 200
    reloaded = _data(
        await client.get(
            f"/api/v1/ai/sessions/{session['id']}", params={"workspaceId": profile["workspaceId"]}
        )
    )
    assert reloaded["id"] == session["id"]
