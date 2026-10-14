"""WP-05 实施切片一：资产发布链专项（批次六十四，40 号 Backlog WP-05）。

覆盖：三个 TestPlanning 发布 op（publishTestStrategyVersion/publishTestPlanVersion/publishTestCaseVersion）——
发布前必须 APPROVED（409 ASSET_NOT_APPROVED）、发布后 PUBLISHED 并回填根 publishedVersionId、
同资产旧 PUBLISHED 版本转 STALE、幂等重放同键返回原结果、AGENT 服务面 403、
未知版本 404（跨 Workspace 资源隐藏同口径）、asset.published 领域事件登记。
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from qf.services.planning_workflow import DomainError, planning_workflow_service
from tests.test_planning_workflow import mutation_headers, setup_identity, start_session


def _data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


_PUBLISH_PATHS = {"TEST_STRATEGY": "test-strategies", "TEST_PLAN": "test-plans", "TEST_CASE": "test-cases"}
_ROOT_LIST_PATHS = {"TEST_STRATEGY": "test-strategies", "TEST_PLAN": "test-plans", "TEST_CASE": "test-cases"}


def _publish_url(task: dict[str, Any]) -> str:
    return (
        f"/api/v1/{_PUBLISH_PATHS[task['artifactType']]}/{task['artifactId']}"
        f"/versions/{task['artifactVersionId']}/publish"
    )


async def _approve(client: AsyncClient, task: dict[str, Any], key: str) -> None:
    decided = await client.post(
        f"/api/v1/review-tasks/{task['id']}/decisions",
        headers=mutation_headers(client, idempotency_key=key),
        json={"decision": "APPROVE", "contentDigest": task["contentDigest"]},
    )
    assert decided.status_code == 200, decided.text


async def _tasks_by_type(client: AsyncClient, profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    params = {"workspaceId": profile["workspaceId"]}
    tasks = _data(await client.get("/api/v1/review-tasks", params=params))
    return {task["artifactType"]: task for task in tasks if task["artifactType"] in _PUBLISH_PATHS}


async def test_publish_chain_requires_approved_and_backfills_root(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    await start_session(client, profile)
    tasks = await _tasks_by_type(client, profile)
    assert set(tasks) == {"TEST_STRATEGY", "TEST_PLAN", "TEST_CASE"}

    # 未批准先发布 → 409 ASSET_NOT_APPROVED（AI 不得自批自发布）
    strategy_task = tasks["TEST_STRATEGY"]
    early = await client.post(
        _publish_url(strategy_task),
        headers=mutation_headers(client, idempotency_key="wp63-publish-00000001"),
    )
    assert early.status_code == 409
    assert early.json()["code"] == "ASSET_NOT_APPROVED"

    # 逐类型 批准 → 发布 → 根 publishedVersionId 回填
    for index, artifact_type in enumerate(("TEST_STRATEGY", "TEST_PLAN", "TEST_CASE")):
        task = tasks[artifact_type]
        await _approve(client, task, f"wp63-approve-{index:012d}")
        published = await client.post(
            _publish_url(task),
            headers=mutation_headers(client, idempotency_key=f"wp63-publish-{index:012d}"),
        )
        assert published.status_code == 200, published.text
        version = published.json()["data"]
        assert version["reviewStatus"] == "PUBLISHED"
        assert version["id"] == task["artifactVersionId"]
        roots = _data(
            await client.get(f"/api/v1/{_ROOT_LIST_PATHS[artifact_type]}?workspaceId={profile['workspaceId']}")
        )
        root = next(item for item in roots if item["id"] == task["artifactId"])
        assert root["publishedVersionId"] == task["artifactVersionId"]

    # 幂等重放：同键同指纹返回原发布结果（版本已 PUBLISHED 不再触发状态校验）
    replayed = await client.post(
        _publish_url(tasks["TEST_STRATEGY"]),
        headers=mutation_headers(client, idempotency_key="wp63-publish-000000000000"),
    )
    assert replayed.status_code == 200
    assert replayed.json()["data"]["id"] == tasks["TEST_STRATEGY"]["artifactVersionId"]

    # AGENT 自批自发布拒绝（服务面角色门）
    with pytest.raises(DomainError) as agent_denied:
        await planning_workflow_service.publish_strategy_version(
            str(profile["tenantId"]),
            str(profile["workspaceId"]),
            "agent-runner",
            "AGENT",
            frozenset({"artifact.test_strategy.publish"}),
            str(tasks["TEST_STRATEGY"]["artifactId"]),
            str(tasks["TEST_STRATEGY"]["artifactVersionId"]),
            "wp63-agent-000000001",
        )
    assert agent_denied.value.status_code == 403

    # 未知版本 404（跨 Workspace 资源隐藏同口径）
    missing = await client.post(
        f"/api/v1/test-strategies/{tasks['TEST_STRATEGY']['artifactId']}"
        f"/versions/00000000-0000-4000-8000-000000000000/publish",
        headers=mutation_headers(client, idempotency_key="wp63-publish-00000002"),
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"


async def test_publish_supersedes_old_published_version_and_emits_event(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    await start_session(client, profile)
    tasks = await _tasks_by_type(client, profile)
    strategy_task = tasks["TEST_STRATEGY"]

    # v1 批准并发布
    await _approve(client, strategy_task, "wp63-approve-v10000001")
    first = await client.post(
        _publish_url(strategy_task),
        headers=mutation_headers(client, idempotency_key="wp63-publish-v10000001"),
    )
    assert first.status_code == 200, first.text

    # v2 提交（自动建新审核任务）→ 批准 → 发布，旧 PUBLISHED 版本转 STALE
    created = await client.post(
        f"/api/v1/test-strategies/{strategy_task['artifactId']}/versions",
        headers=mutation_headers(client, idempotency_key="wp63-newver-00000001"),
        json={
            "objective": "发布链取代验证目标",
            "inScope": ["新旧版本发布取代语义"],
            "outOfScope": ["未实现 operation"],
            "riskAssessment": [{"risk": "状态误判", "level": "LOW", "treatment": "状态逐项断言"}],
            "testTypes": ["FUNCTIONAL"],
            "approach": "风险驱动",
            "entryCriteria": ["v1 已发布"],
            "exitCriteria": ["v2 发布后 v1 转 STALE"],
            "environmentStrategy": "本地运行时",
            "dataStrategy": "临时 SQLite",
            "automationStrategy": "pytest",
            "defectStrategy": "先分析后立 Defect",
            "changeSummary": "WP-05 取代链验证新版本",
        },
    )
    assert created.status_code == 201, created.text
    new_version = created.json()["data"]
    refreshed = await _tasks_by_type(client, profile)
    assert refreshed["TEST_STRATEGY"]["artifactVersionId"] == new_version["id"]
    await _approve(client, refreshed["TEST_STRATEGY"], "wp63-approve-v20000001")
    second = await client.post(
        _publish_url(refreshed["TEST_STRATEGY"]),
        headers=mutation_headers(client, idempotency_key="wp63-publish-v20000001"),
    )
    assert second.status_code == 200, second.text

    roots = _data(await client.get(f"/api/v1/test-strategies?workspaceId={profile['workspaceId']}"))
    root = next(item for item in roots if item["id"] == strategy_task["artifactId"])
    assert root["publishedVersionId"] == new_version["id"]

    # 旧版本 STALE / 新版本 PUBLISHED（策略无版本列表读面，经服务面内省核对状态迁移）
    versions = planning_workflow_service.strategy_versions
    assert versions[strategy_task["artifactVersionId"]]["reviewStatus"] == "STALE"
    assert versions[new_version["id"]]["reviewStatus"] == "PUBLISHED"

    # asset.published 领域事件登记（subjectType=TEST_STRATEGY，含取代指针；listEvents 新事件在前）
    events = _data(
        await client.get(
            "/api/v1/observability/events",
            params={"workspaceId": profile["workspaceId"], "eventType": "asset.published"},
        )
    )
    strategy_events = [event for event in events if event["subjectType"] == "TEST_STRATEGY"]
    assert len(strategy_events) == 2
    superseding = next(event for event in strategy_events if event["payload"]["versionId"] == new_version["id"])
    assert superseding["payload"]["supersededVersionId"] == strategy_task["artifactVersionId"]


async def test_publish_supersede_invalidates_downstream_plans(client: AsyncClient) -> None:
    """WP-05 切片三：发布取代上游基线 → 引用旧发布版本的计划版本转 STALE，未决任务 CANCELLED（39 §4）。"""
    profile = await setup_identity(client)
    await start_session(client, profile)
    params = {"workspaceId": profile["workspaceId"]}
    tasks = await _tasks_by_type(client, profile)
    strategy_task = tasks["TEST_STRATEGY"]
    plan_task = tasks["TEST_PLAN"]

    # 策略 v1 批准并发布（计划版本仍 PENDING_REVIEW，引用策略 v1）
    await _approve(client, strategy_task, "wp66-approve-v10000001")
    first = await client.post(
        _publish_url(strategy_task),
        headers=mutation_headers(client, idempotency_key="wp66-publish-v10000001"),
    )
    assert first.status_code == 200, first.text

    # 策略 v2 提交 → 批准 → 发布 → 取代 v1 触发下游失效
    created = await client.post(
        f"/api/v1/test-strategies/{strategy_task['artifactId']}/versions",
        headers=mutation_headers(client, idempotency_key="wp66-newver-00000001"),
        json={
            "objective": "下游失效验证目标",
            "inScope": ["发布取代联动"],
            "outOfScope": ["未实现 operation"],
            "riskAssessment": [{"risk": "级联遗漏", "level": "LOW", "treatment": "逐版本断言"}],
            "testTypes": ["FUNCTIONAL"],
            "approach": "风险驱动",
            "entryCriteria": ["v1 已发布"],
            "exitCriteria": ["v2 发布后下游计划版本 STALE"],
            "environmentStrategy": "本地运行时",
            "dataStrategy": "临时 SQLite",
            "automationStrategy": "pytest",
            "defectStrategy": "先分析后立 Defect",
            "changeSummary": "WP-05 下游失效验证新版本",
        },
    )
    assert created.status_code == 201, created.text
    new_version = created.json()["data"]
    refreshed = await _tasks_by_type(client, profile)
    assert refreshed["TEST_STRATEGY"]["artifactVersionId"] == new_version["id"]
    await _approve(client, refreshed["TEST_STRATEGY"], "wp66-approve-v20000001")
    second = await client.post(
        _publish_url(refreshed["TEST_STRATEGY"]),
        headers=mutation_headers(client, idempotency_key="wp66-publish-v20000001"),
    )
    assert second.status_code == 200, second.text

    # 下游计划版本转 STALE，其未决审核任务 CANCELLED
    assert (
        planning_workflow_service.plan_versions[plan_task["artifactVersionId"]]["reviewStatus"] == "STALE"
    )
    plan_task_after = _data(await client.get(f"/api/v1/review-tasks/{plan_task['id']}", params=params))
    assert plan_task_after["status"] == "CANCELLED"

    # stage.invalidated 事件逐版本登记（指明触发源与取代指针）
    events = _data(
        await client.get(
            "/api/v1/observability/events",
            params={"workspaceId": profile["workspaceId"], "eventType": "stage.invalidated"},
        )
    )
    invalidated = next(
        event for event in events if event["payload"]["invalidatedVersionId"] == plan_task["artifactVersionId"]
    )
    assert invalidated["subjectType"] == "TEST_PLAN"
    assert invalidated["payload"]["trigger"] == "UPSTREAM_PUBLISHED_VERSION_SUPERSEDED"
    assert invalidated["payload"]["supersededVersionId"] == strategy_task["artifactVersionId"]
    assert invalidated["payload"]["publishedVersionId"] == new_version["id"]

    # 只失效不删除：历史版本仍可读
    assert strategy_task["artifactVersionId"] in planning_workflow_service.strategy_versions
    assert plan_task["artifactVersionId"] in planning_workflow_service.plan_versions
