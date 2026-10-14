"""M2 后端工作板增强 TDD 测试（红→绿）。

覆盖开发计划 v1.1 §M2 后端轨最小纵向切片：
- 新 operation：getWorkItem / listWorkItemRuns / createReviewTask（手工审核任务入口，分派语义）；
- 看板查询增强：listWorkItems 支持 status 过滤与 page/pageSize 分页（GenericListResponse 分页信封）；
- listReviewTasks 支持 assigneeId 与 status 过滤（待我审核视图数据面）；
- createReviewTask 幂等重放与 contentDigest 不匹配 409。
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from tests.test_planning_workflow import mutation_headers, setup_identity, start_session


def _data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


async def test_get_work_item_returns_detail_and_404_for_unknown(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    work_item_id = session["workItemId"]

    detail = _data(await client.get(f"/api/v1/work-items/{work_item_id}"))
    assert detail["id"] == work_item_id
    assert detail["status"] == "PENDING_REVIEW"
    assert detail["tenantId"] == profile["tenantId"]

    missing = await client.get("/api/v1/work-items/00000000-0000-4000-8000-000000000000")
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"


async def test_list_work_item_runs_tracks_session_history(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    work_item_id = session["workItemId"]

    runs = _data(await client.get(f"/api/v1/work-items/{work_item_id}/runs"))
    assert len(runs) == 1
    run = runs[0]
    assert run["sessionId"] == session["id"]
    assert run["status"] == "BLOCKED"
    assert run["workflowKey"] == "gate0-planning-slice"
    assert run["startedAt"]
    assert "tenantId" not in run

    empty = _data(
        await client.get("/api/v1/work-items/00000000-0000-4000-8000-000000000000/runs")
    )
    assert empty == []


async def test_create_review_task_manual_entry_with_digest_and_idempotency(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    await start_session(client, profile)
    tasks = _data(await client.get("/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]}))
    source = next(task for task in tasks if task["artifactType"] == "TEST_STRATEGY")

    payload = {
        "workItemId": source["workItemId"],
        "artifactType": source["artifactType"],
        "artifactId": source["artifactId"],
        "artifactVersionId": source["artifactVersionId"],
        "contentDigest": source["contentDigest"],
        "policyType": "SINGLE_REVIEW",
        "assignees": [
            {
                "userId": profile["userId"],
                "reviewRole": "REVIEWER",
                "requiredCapability": "artifact.test_strategy.approve",
            }
        ],
    }
    headers = mutation_headers(client, idempotency_key="manual-review-000001")
    created = await client.post("/api/v1/review-tasks", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    task = _data(created)
    assert task["status"] == "OPEN"
    assert task["artifactVersionId"] == source["artifactVersionId"]
    assert task["assignments"][0]["userId"] == profile["userId"]

    replayed = await client.post(
        "/api/v1/review-tasks", headers=mutation_headers(client, idempotency_key="manual-review-000001"), json=payload
    )
    assert replayed.status_code == 201
    assert _data(replayed)["id"] == task["id"]

    stale_digest = dict(payload, contentDigest="0" * 64)
    mismatch = await client.post(
        "/api/v1/review-tasks",
        headers=mutation_headers(client, idempotency_key="manual-review-000002"),
        json=stale_digest,
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["code"] == "STALE_ARTIFACT_VERSION"


async def test_list_work_items_supports_status_filter_and_pagination(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    await start_session(client, profile)
    for index in range(3):
        created = await client.post(
            "/api/v1/work-items",
            headers=mutation_headers(client),
            json={
                "workspaceId": profile["workspaceId"],
                "workItemType": "GENERAL",
                "title": f"看板补充项{index}",
                "objective": "看板筛选测试",
                "acceptanceCriteria": "可筛可分页",
                "requiresReview": False,
                "priority": "P2",
                "riskLevel": "LOW",
            },
        )
        assert created.status_code == 201, created.text

    ready = _data(
        await client.get(
            "/api/v1/work-items", params={"workspaceId": profile["workspaceId"], "status": "READY"}
        )
    )
    assert len(ready) == 3
    assert all(item["status"] == "READY" for item in ready)

    response = await client.get(
        "/api/v1/work-items",
        params={"workspaceId": profile["workspaceId"], "page": 1, "pageSize": 2},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert body["total"] == 4
    assert body["page"] == 1
    assert body["pageSize"] == 2

    second = await client.get(
        "/api/v1/work-items",
        params={"workspaceId": profile["workspaceId"], "page": 2, "pageSize": 2},
    )
    assert len(second.json()["data"]) == 2


async def test_list_review_tasks_supports_assignee_and_status_filters(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    await start_session(client, profile)
    tasks = _data(await client.get("/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]}))
    source = next(task for task in tasks if task["artifactType"] == "TEST_PLAN")
    created = await client.post(
        "/api/v1/review-tasks",
        headers=mutation_headers(client, idempotency_key="assign-filter-000001"),
        json={
            "workItemId": source["workItemId"],
            "artifactType": source["artifactType"],
            "artifactId": source["artifactId"],
            "artifactVersionId": source["artifactVersionId"],
            "contentDigest": source["contentDigest"],
            "policyType": "SINGLE_REVIEW",
            "assignees": [
                {
                    "userId": profile["userId"],
                    "reviewRole": "APPROVER",
                    "requiredCapability": "artifact.test_plan.approve",
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    manual_task = _data(created)

    mine = _data(
        await client.get(
            "/api/v1/review-tasks",
            params={"workspaceId": profile["workspaceId"], "assigneeId": profile["userId"]},
        )
    )
    assert manual_task["id"] in [task["id"] for task in mine]

    stranger = _data(
        await client.get(
            "/api/v1/review-tasks",
            params={"workspaceId": profile["workspaceId"], "assigneeId": "00000000-0000-4000-8000-000000000099"},
        )
    )
    assert stranger == []

    open_tasks = _data(
        await client.get(
            "/api/v1/review-tasks",
            params={"workspaceId": profile["workspaceId"], "status": "OPEN", "assigneeId": profile["userId"]},
        )
    )
    assert manual_task["id"] in [task["id"] for task in open_tasks]
    assert all(task["status"] == "OPEN" for task in open_tasks)

    approved = _data(
        await client.get(
            "/api/v1/review-tasks",
            params={"workspaceId": profile["workspaceId"], "status": "APPROVED"},
        )
    )
    assert approved == []


async def test_create_review_task_requires_review_capability(client: AsyncClient) -> None:
    """未知产出物版本 → 404；能力缺失由全局能力集保障，此处覆盖资源校验路径。"""
    profile = await setup_identity(client)
    await start_session(client, profile)
    response = await client.post(
        "/api/v1/review-tasks",
        headers=mutation_headers(client, idempotency_key="unknown-version-00001"),
        json={
            "workItemId": "00000000-0000-4000-8000-000000000001",
            "artifactType": "TEST_STRATEGY",
            "artifactId": "00000000-0000-4000-8000-000000000002",
            "artifactVersionId": "00000000-0000-4000-8000-000000000003",
            "contentDigest": "a" * 64,
            "policyType": "SINGLE_REVIEW",
        },
    )
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


async def test_get_review_artifact_diff_first_version_degrades_second_version_field_level(client: AsyncClient) -> None:
    """审核队列版本 Diff 数据面（10 号 PRD §3）：首版无基线降级 + 二版字段级 diff。"""
    profile = await setup_identity(client)
    await start_session(client, profile)
    tasks = _data(await client.get("/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]}))
    source = next(task for task in tasks if task["artifactType"] == "TEST_STRATEGY")

    # 首版无同根上一版：降级 hasBaseline=false，fields 空数组，不报错
    first = _data(await client.get(f"/api/v1/review-tasks/{source['id']}/artifact/diff"))
    assert first["artifactType"] == "TEST_STRATEGY"
    assert first["artifactId"] == source["artifactId"]
    assert first["artifactVersionId"] == source["artifactVersionId"]
    assert first["headDigest"] == source["contentDigest"]
    assert first["hasBaseline"] is False
    assert first["baseVersionId"] is None
    assert first["baseDigest"] is None
    assert first["changedCount"] == 0
    assert first["fields"] == []

    # 创建二版策略 → 手工审核任务绑定新版本 → diff 以首版为 base
    new_version = _data(
        await client.post(
            f"/api/v1/test-strategies/{source['artifactId']}/versions",
            headers=mutation_headers(client),
            json={
                "objective": "Diff 专项修订版策略",
                "inScope": ["版本 Diff 数据面"],
                "outOfScope": ["未实现 operation"],
                "riskAssessment": [{"risk": "基线缺失降级", "level": "LOW", "treatment": "同根兄弟版本推导"}],
                "testTypes": ["FUNCTIONAL"],
                "approach": "风险驱动",
                "entryCriteria": ["首版已存在"],
                "exitCriteria": ["字段级 diff 可查"],
                "environmentStrategy": "本地运行时",
                "dataStrategy": "临时 SQLite",
                "automationStrategy": "pytest",
                "defectStrategy": "先分析后立 Defect",
                "changeSummary": "Diff 专项修订",
            },
        )
    )
    assert new_version["version"] == 2
    manual_task = _data(
        await client.post(
            "/api/v1/review-tasks",
            headers=mutation_headers(client, idempotency_key="diff-review-000001"),
            json={
                "workItemId": source["workItemId"],
                "artifactType": source["artifactType"],
                "artifactId": source["artifactId"],
                "artifactVersionId": new_version["id"],
                "contentDigest": new_version["contentDigest"],
                "policyType": "SINGLE_REVIEW",
                "assignees": [
                    {
                        "userId": profile["userId"],
                        "reviewRole": "REVIEWER",
                        "requiredCapability": "artifact.test_strategy.approve",
                    }
                ],
            },
        )
    )

    second = _data(await client.get(f"/api/v1/review-tasks/{manual_task['id']}/artifact/diff"))
    assert second["artifactVersionId"] == new_version["id"]
    assert second["headDigest"] == new_version["contentDigest"]
    assert second["hasBaseline"] is True
    assert second["baseVersionId"] == source["artifactVersionId"]
    assert second["baseDigest"] == source["contentDigest"]
    assert second["changedCount"] == len(second["fields"])
    assert second["changedCount"] >= 1

    # 字段名字典序 + changeType 枚举 + 确定性字段断言
    names = [field["field"] for field in second["fields"]]
    assert names == sorted(names)
    assert all(field["changeType"] in {"ADDED", "REMOVED", "CHANGED"} for field in second["fields"])
    assert "tenantId" not in names and "workspaceId" not in names
    by_field = {field["field"]: field for field in second["fields"]}
    assert by_field["version"]["changeType"] == "CHANGED"
    assert by_field["version"]["oldValue"] == 1
    assert by_field["version"]["newValue"] == 2
    assert by_field["changeSummary"]["changeType"] == "CHANGED"
    assert by_field["changeSummary"]["newValue"] == "Diff 专项修订"
    assert by_field["objective"]["changeType"] == "CHANGED"

    # 负例：未知审核任务 → 404 NOT_FOUND
    missing = await client.get("/api/v1/review-tasks/00000000-0000-4000-8000-000000000000/artifact/diff")
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"
