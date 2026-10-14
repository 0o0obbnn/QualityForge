"""TC-PUB-001~004 + TC-RT-015：资产发布链与双人复核可执行层（批次六十九，WP-05 已实现面）。

覆盖：APPROVED 发布成功回填指针、非 APPROVED 409 与幂等重放、计划/用例发布两面、
发布取代级联失效（stage.invalidated 事件断言）、CRITICAL 工作项 FOUR_EYES 双人门。
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from conftest import data_of, envelope, gate0_session, mutation_headers, setup_identity

from qf.services.planning_workflow import planning_workflow_service


async def _strategy_task(client: AsyncClient, profile: dict) -> dict:
    """gate0 会话产出的 TEST_STRATEGY 审核任务。"""
    await gate0_session(client, profile)
    tasks = data_of(
        await client.get(
            "/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]}
        )
    )
    return next(task for task in tasks if task["artifactType"] == "TEST_STRATEGY")


async def _approve(client: AsyncClient, task: dict, key: str) -> None:
    decided = await client.post(
        f"/api/v1/review-tasks/{task['id']}/decisions",
        headers=mutation_headers(client, key),
        json={"decision": "APPROVE", "contentDigest": task["contentDigest"]},
    )
    assert decided.status_code == 200, decided.text


async def test_tc_pub_001_publish_approved_strategy_backfills_pointer(
    client: AsyncClient,
) -> None:
    """TC-PUB-001：APPROVED 策略发布 PUBLISHED，根 publishedVersionId 回填。"""
    profile = await setup_identity(client)
    task = await _strategy_task(client, profile)
    await _approve(client, task, f"pub-approve-{uuid.uuid4().hex[:10]}")

    published = await client.post(
        f"/api/v1/test-strategies/{task['artifactId']}/versions/{task['artifactVersionId']}/publish",
        headers=mutation_headers(client, f"pub-publish-{uuid.uuid4().hex[:9]}"),
    )
    assert published.status_code == 200, published.text
    body = data_of(published)
    assert body["reviewStatus"] == "PUBLISHED"
    assert body["id"] == task["artifactVersionId"]

    strategies = data_of(
        await client.get(
            "/api/v1/test-strategies", params={"workspaceId": profile["workspaceId"]}
        )
    )
    root = next(item for item in strategies if item["id"] == task["artifactId"])
    assert root["publishedVersionId"] == task["artifactVersionId"]


async def test_tc_pub_002_not_approved_and_idempotent_replay(
    client: AsyncClient,
) -> None:
    """TC-PUB-002：PENDING_REVIEW 发布 409；同键重放返回原结果；新键再发布 409。"""
    profile = await setup_identity(client)
    task = await _strategy_task(client, profile)

    early = await client.post(
        f"/api/v1/test-strategies/{task['artifactId']}/versions/{task['artifactVersionId']}/publish",
        headers=mutation_headers(client, f"pub-early-{uuid.uuid4().hex[:11]}"),
    )
    assert early.status_code == 409
    assert envelope(early)["code"] == "ASSET_NOT_APPROVED"

    await _approve(client, task, f"pub-approve-{uuid.uuid4().hex[:10]}")
    replay_key = f"pub-replay-{uuid.uuid4().hex[:10]}"
    first = await client.post(
        f"/api/v1/test-strategies/{task['artifactId']}/versions/{task['artifactVersionId']}/publish",
        headers=mutation_headers(client, replay_key),
    )
    assert first.status_code == 200, first.text

    replay = await client.post(
        f"/api/v1/test-strategies/{task['artifactId']}/versions/{task['artifactVersionId']}/publish",
        headers=mutation_headers(client, replay_key),
    )
    assert replay.status_code == 200
    assert data_of(replay)["id"] == data_of(first)["id"], "同键重放返回原发布结果"

    again = await client.post(
        f"/api/v1/test-strategies/{task['artifactId']}/versions/{task['artifactVersionId']}/publish",
        headers=mutation_headers(client, f"pub-again-{uuid.uuid4().hex[:10]}"),
    )
    assert again.status_code == 409
    assert envelope(again)["code"] == "ASSET_NOT_APPROVED"


async def test_tc_pub_003_plan_and_case_publish(client: AsyncClient) -> None:
    """TC-PUB-003：计划与用例版本发布两面（各自 APPROVED 后发布）。"""
    profile = await setup_identity(client)
    await gate0_session(client, profile)
    tasks = data_of(
        await client.get(
            "/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]}
        )
    )

    for artifact_type, path_prefix in (
        ("TEST_PLAN", "test-plans"),
        ("TEST_CASE", "test-cases"),
    ):
        task = next(item for item in tasks if item["artifactType"] == artifact_type)
        await _approve(
            client, task, f"pub-approve-{artifact_type}-{uuid.uuid4().hex[:6]}"
        )
        published = await client.post(
            f"/api/v1/{path_prefix}/{task['artifactId']}/versions/{task['artifactVersionId']}/publish",
            headers=mutation_headers(
                client, f"pub-{artifact_type}-{uuid.uuid4().hex[:8]}"
            ),
        )
        assert published.status_code == 200, published.text
        assert data_of(published)["reviewStatus"] == "PUBLISHED"


async def test_tc_pub_004_supersede_invalidates_downstream(client: AsyncClient) -> None:
    """TC-PUB-004：发布取代 → 旧版本 STALE + 下游计划版本 STALE + stage.invalidated 事件。"""
    profile = await setup_identity(client)
    task = await _strategy_task(client, profile)
    plan_task = None
    tasks = data_of(
        await client.get(
            "/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]}
        )
    )
    plan_task = next(item for item in tasks if item["artifactType"] == "TEST_PLAN")

    # v1 批准并发布
    await _approve(client, task, f"pub4-approve1-{uuid.uuid4().hex[:8]}")
    first = await client.post(
        f"/api/v1/test-strategies/{task['artifactId']}/versions/{task['artifactVersionId']}/publish",
        headers=mutation_headers(client, f"pub4-publish1-{uuid.uuid4().hex[:8]}"),
    )
    assert first.status_code == 200, first.text

    # v2 提交→批准→发布，取代 v1
    created = await client.post(
        f"/api/v1/test-strategies/{task['artifactId']}/versions",
        headers=mutation_headers(client, f"pub4-newver-{uuid.uuid4().hex[:9]}"),
        json=_strategy_v2_payload(),
    )
    assert created.status_code == 201, created.text
    new_version = data_of(created)
    tasks_after = data_of(
        await client.get(
            "/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]}
        )
    )
    new_task = next(
        item
        for item in tasks_after
        if item["artifactType"] == "TEST_STRATEGY"
        and item["artifactVersionId"] == new_version["id"]
    )
    await _approve(client, new_task, f"pub4-approve2-{uuid.uuid4().hex[:8]}")
    second = await client.post(
        f"/api/v1/test-strategies/{task['artifactId']}/versions/{new_version['id']}/publish",
        headers=mutation_headers(client, f"pub4-publish2-{uuid.uuid4().hex[:8]}"),
    )
    assert second.status_code == 200, second.text

    # 级联断言：v1 STALE、下游计划版本 STALE、未决任务 CANCELLED
    versions = planning_workflow_service.strategy_versions
    assert versions[task["artifactVersionId"]]["reviewStatus"] == "STALE"
    plan_versions = planning_workflow_service.plan_versions
    assert plan_versions[plan_task["artifactVersionId"]]["reviewStatus"] == "STALE", (
        "引用被取代策略版本的下游计划版本应 STALE"
    )
    plan_task_after = data_of(
        await client.get(
            f"/api/v1/review-tasks/{plan_task['id']}",
            params={"workspaceId": profile["workspaceId"]},
        )
    )
    assert plan_task_after["status"] == "CANCELLED"

    events = data_of(
        await client.get(
            "/api/v1/observability/events",
            params={
                "workspaceId": profile["workspaceId"],
                "eventType": "stage.invalidated",
            },
        )
    )
    invalidated = next(
        event
        for event in events
        if event["payload"]["invalidatedVersionId"] == plan_task["artifactVersionId"]
    )
    assert invalidated["payload"]["trigger"] == "UPSTREAM_PUBLISHED_VERSION_SUPERSEDED"
    assert invalidated["payload"]["supersededVersionId"] == task["artifactVersionId"]


def _strategy_v2_payload() -> dict:
    return {
        "objective": "执行器取代验证目标",
        "inScope": ["发布取代下游失效"],
        "outOfScope": ["未实现 operation"],
        "riskAssessment": [
            {"risk": "级联遗漏", "level": "LOW", "treatment": "逐版本断言"}
        ],
        "testTypes": ["FUNCTIONAL"],
        "approach": "风险驱动",
        "entryCriteria": ["v1 已发布"],
        "exitCriteria": ["v2 发布后下游 STALE"],
        "environmentStrategy": "本地运行时",
        "dataStrategy": "临时 SQLite",
        "automationStrategy": "pytest",
        "defectStrategy": "先分析后立 Defect",
        "changeSummary": "执行器取代链验证新版本",
    }


async def test_tc_rt_015_four_eyes_same_approver_rejected(client: AsyncClient) -> None:
    """TC-RT-015：CRITICAL 工作项 FOUR_EYES——部分批准 IN_PROGRESS，同人二次批准 409。"""
    import hashlib

    profile = await setup_identity(client)
    ws = profile["workspaceId"]
    releases = data_of(await client.get(f"/api/v1/workspaces/{ws}/releases"))
    release_id = releases[0]["id"]

    requirement = await client.post(
        "/api/v1/knowledge/requirements",
        headers=mutation_headers(client, f"rt15-req-{uuid.uuid4().hex[:10]}"),
        json={"workspaceId": ws, "name": "CRITICAL 需求", "documentType": "PRD"},
    )
    requirement_id = data_of(requirement)["id"]
    content = "# CRITICAL\n资金路径高风险需双人复核。"
    version = await client.post(
        f"/api/v1/knowledge/requirements/{requirement_id}/versions",
        headers=mutation_headers(client, f"rt15-ver-{uuid.uuid4().hex[:10]}"),
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
        headers=mutation_headers(client, f"rt15-wi-{uuid.uuid4().hex[:12]}"),
        json={
            "workspaceId": ws,
            "releaseId": release_id,
            "workItemType": "STRATEGY",
            "title": "CRITICAL 双人复核工作项",
            "objective": "验证 FOUR_EYES 门",
            "acceptanceCriteria": "单人无法绕过双审",
            "requiresReview": True,
            "priority": "P0",
            "riskLevel": "CRITICAL",
        },
    )
    work_item_id = data_of(work_item)["id"]

    nonce = uuid.uuid4().hex[:12]
    card = await client.post(
        f"/api/v1/work-items/{work_item_id}/task-cards",
        headers=mutation_headers(client, f"rt15-card-{nonce}"),
        json={
            "objective": "双人门任务卡",
            "scope": "CRITICAL 资产",
            "acceptanceCriteria": "FOUR_EYES 生效",
            "constraints": "无",
            "requestedPermissions": [],
            "budget": {},
        },
    )
    plan = await client.post(
        f"/api/v1/work-items/{work_item_id}/agent-plans",
        headers=mutation_headers(client, f"rt15-plan-{nonce}"),
        json={
            "taskCardId": data_of(card)["id"],
            "steps": [
                {
                    "stepKey": "run",
                    "agentRole": "coordinator",
                    "description": "双人门步骤",
                }
            ],
        },
    )
    await client.post(
        f"/api/v1/agent-plans/{data_of(plan)['id']}/decisions",
        headers=mutation_headers(client, f"rt15-decide-{nonce}"),
        json={
            "decision": "APPROVE",
            "expectedContentDigest": data_of(plan)["contentDigest"],
            "reason": "双人门批准",
        },
    )
    await client.post(
        "/api/v1/ai/sessions",
        headers=mutation_headers(client, f"rt15-sess-{nonce}"),
        json={
            "workspaceId": ws,
            "workItemId": work_item_id,
            "workflowKey": "gate0-planning-slice",
            "requirementVersionId": version_id,
            "releaseId": release_id,
            "ownerId": profile["userId"],
        },
    )

    tasks = data_of(
        await client.get("/api/v1/review-tasks", params={"workspaceId": ws})
    )
    critical = next(item for item in tasks if item["artifactType"] == "TEST_STRATEGY")
    assert critical["policyType"] == "FOUR_EYES"
    assert critical["minApprovers"] == 2

    first = await client.post(
        f"/api/v1/review-tasks/{critical['id']}/decisions",
        headers=mutation_headers(client, f"rt15-ap1-{uuid.uuid4().hex[:10]}"),
        json={"decision": "APPROVE", "contentDigest": critical["contentDigest"]},
    )
    assert first.status_code == 200, first.text
    body = data_of(first)
    assert body["status"] == "IN_PROGRESS"
    assert len(body["approvals"]) == 1

    bypass = await client.post(
        f"/api/v1/review-tasks/{critical['id']}/decisions",
        headers=mutation_headers(client, f"rt15-ap2-{uuid.uuid4().hex[:10]}"),
        json={"decision": "APPROVE", "contentDigest": critical["contentDigest"]},
    )
    assert bypass.status_code == 409
    assert envelope(bypass)["code"] == "FOUR_EYES_SAME_APPROVER"
