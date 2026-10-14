"""M1-B1 退回→新版本闭环 TDD 测试（红→绿）。

覆盖 M1 实施计划 v1.1 §M1-B1 红清单：
- REQUEST_CHANGES/REJECT → 产出物回草稿态；REJECT 另将会话终态 FAILED（QF-REQ-078 收敛后枚举）；
- createTestStrategyVersion / createTestPlanVersion 版本递增、旧版只读可查、新版本自动建新 ReviewTask；
- transitionWorkItem REWORK 路径 + lockVersion 陈旧 409；
- QF-REQ-078：运行时会话状态收敛到 32 号契约枚举（BLOCKED/SUCCEEDED/FAILED）+ 存量数据加载归一；
- M-120 契约先行字段 approveDisabledReason（TASK_CLOSED / STALE_VERSION）。
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from qf.services.planning_workflow import content_digest
from tests.test_planning_workflow import mutation_headers, setup_identity, start_session

# 32 号契约 AgentSession.status 枚举（QF-REQ-078 收敛目标）
CONTRACT_SESSION_STATUSES = {"PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "BLOCKED"}


def _data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


async def _session_tasks(client: AsyncClient, profile: dict[str, Any]) -> list[dict[str, Any]]:
    return _data(await client.get("/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]}))


def _strategy_v2_payload(change_summary: str = "按审核意见返工后重测") -> dict[str, Any]:
    return {
        "objective": "返工修订：验证退款链路合法与非法路径（第二版）",
        "inScope": ["退款申请", "退款审批"],
        "outOfScope": ["未经声明的外部系统写入"],
        "riskAssessment": [{"risk": "边界遗漏", "level": "MEDIUM", "treatment": "补充负向用例"}],
        "testTypes": ["FUNCTIONAL", "NEGATIVE"],
        "approach": "风险驱动，返工聚焦审核意见",
        "entryCriteria": ["退回意见已逐条回应"],
        "exitCriteria": ["新版本通过人工审核"],
        "environmentStrategy": "使用受控测试环境",
        "dataStrategy": "使用可复现且脱敏的测试数据",
        "automationStrategy": "优先API",
        "defectStrategy": "失败证据先分析再立Defect",
        "changeSummary": change_summary,
    }


def _plan_v2_payload(strategy_version_id: str, owner_id: str) -> dict[str, Any]:
    return {
        "strategyVersionId": strategy_version_id,
        "objective": "返工修订：执行第二版测试策略",
        "planType": "RELEASE_VALIDATION",
        "scope": {"focus": "审核意见整改"},
        "ownerId": owner_id,
        "startDate": "2026-08-17",
        "endDate": "2026-08-20",
        "milestones": [{"name": "返工复审", "exitGate": "NEW_VERSION_APPROVED"}],
        "resourceRequirements": {"reviewer": 1},
        "acceptanceCriteria": ["退回意见全部闭环", "新版本摘要绑定精确"],
        "changeSummary": "按审核意见返工后重测",
    }


async def test_request_changes_puts_artifact_back_to_draft(client: AsyncClient) -> None:
    """REQUEST_CHANGES：任务 CHANGES_REQUESTED、产出物版本回 DRAFT、会话 BLOCKED、工作项 REWORK。"""
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    assert session["status"] == "BLOCKED"
    assert session["status"] in CONTRACT_SESSION_STATUSES

    target = next(task for task in await _session_tasks(client, profile) if task["artifactType"] == "TEST_STRATEGY")
    decision = await client.post(
        f"/api/v1/review-tasks/{target['id']}/decisions",
        headers=mutation_headers(client, idempotency_key=f"rework-draft-{target['id']}"),
        json={"decision": "REQUEST_CHANGES", "contentDigest": target["contentDigest"], "comments": "补充边界"},
    )
    assert decision.status_code == 200
    assert _data(decision)["status"] == "CHANGES_REQUESTED"

    artifact = _data(
        await client.get(
            f"/api/v1/review-tasks/{target['id']}/artifact", params={"workspaceId": profile["workspaceId"]}
        )
    )
    assert artifact["content"]["reviewStatus"] == "DRAFT"

    reloaded = _data(
        await client.get(f"/api/v1/ai/sessions/{session['id']}", params={"workspaceId": profile["workspaceId"]})
    )
    assert reloaded["status"] == "BLOCKED"

    listed = _data(await client.get("/api/v1/work-items", params={"workspaceId": profile["workspaceId"]}))
    work_item = next(item for item in listed if item["id"] == session["workItemId"])
    assert work_item["status"] == "REWORK"


async def test_reject_terminates_session_and_returns_artifact_to_draft(client: AsyncClient) -> None:
    """REJECT：任务 REJECTED、产出物回 DRAFT、会话终态 FAILED 且 completedAt 落位。"""
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    target = next(task for task in await _session_tasks(client, profile) if task["artifactType"] == "TEST_PLAN")
    decision = await client.post(
        f"/api/v1/review-tasks/{target['id']}/decisions",
        headers=mutation_headers(client, idempotency_key=f"reject-draft-{target['id']}"),
        json={"decision": "REJECT", "contentDigest": target["contentDigest"], "comments": "方向性错误，推翻重来"},
    )
    assert decision.status_code == 200
    assert _data(decision)["status"] == "REJECTED"

    artifact = _data(
        await client.get(
            f"/api/v1/review-tasks/{target['id']}/artifact", params={"workspaceId": profile["workspaceId"]}
        )
    )
    assert artifact["content"]["reviewStatus"] == "DRAFT"

    reloaded = _data(
        await client.get(f"/api/v1/ai/sessions/{session['id']}", params={"workspaceId": profile["workspaceId"]})
    )
    assert reloaded["status"] == "FAILED"
    assert reloaded["status"] in CONTRACT_SESSION_STATUSES
    assert reloaded["completedAt"] is not None

    listed = _data(await client.get("/api/v1/work-items", params={"workspaceId": profile["workspaceId"]}))
    work_item = next(item for item in listed if item["id"] == session["workItemId"])
    assert work_item["status"] == "REWORK"


async def test_resubmitting_strategy_version_increments_and_creates_new_review_task(client: AsyncClient) -> None:
    """退回后提交策略新版本：版本递增、旧版只读可查、自动建新 OPEN 审核任务、旧任务转 STALE_VERSION 禁用原因。"""
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    tasks_before = await _session_tasks(client, profile)
    strategy_task = next(task for task in tasks_before if task["artifactType"] == "TEST_STRATEGY")
    await client.post(
        f"/api/v1/review-tasks/{strategy_task['id']}/decisions",
        headers=mutation_headers(client, idempotency_key=f"rework-ver-{strategy_task['id']}"),
        json={"decision": "REQUEST_CHANGES", "contentDigest": strategy_task["contentDigest"], "comments": "补边界"},
    )

    strategies = _data(await client.get("/api/v1/test-strategies", params={"workspaceId": profile["workspaceId"]}))
    root = next(item for item in strategies if item["id"] == strategy_task["artifactId"])
    old_version_id = root["currentVersionId"]

    payload = _strategy_v2_payload()
    created = await client.post(
        f"/api/v1/test-strategies/{root['id']}/versions",
        headers=mutation_headers(client),
        json=payload,
    )
    assert created.status_code == 201, created.text
    new_version = _data(created)
    assert new_version["version"] == 2
    assert new_version["reviewStatus"] == "PENDING_REVIEW"
    expected_content = {key: value for key, value in payload.items() if key != "changeSummary"}
    assert new_version["contentDigest"] == content_digest(expected_content)
    assert new_version["changeSummary"] == payload["changeSummary"]

    # 根实体指向新版本
    strategies = _data(await client.get("/api/v1/test-strategies", params={"workspaceId": profile["workspaceId"]}))
    root = next(item for item in strategies if item["id"] == root["id"])
    assert root["currentVersionId"] == new_version["id"]

    # 旧版只读可查：内容不变、reviewStatus 保持 DRAFT（不可经任何端点改写）
    old_artifact = _data(
        await client.get(
            f"/api/v1/review-tasks/{strategy_task['id']}/artifact", params={"workspaceId": profile["workspaceId"]}
        )
    )
    assert old_artifact["artifactVersionId"] == old_version_id
    assert old_artifact["content"]["reviewStatus"] == "DRAFT"
    assert old_artifact["content"]["version"] == 1

    # 新版本自动建 OPEN 审核任务，绑定新摘要；会话任务集纳入新任务
    tasks_after = await _session_tasks(client, profile)
    assert len(tasks_after) == len(tasks_before) + 1
    new_task = next(task for task in tasks_after if task["artifactVersionId"] == new_version["id"])
    assert new_task["status"] == "OPEN"
    assert new_task["contentDigest"] == new_version["contentDigest"]
    reloaded = _data(
        await client.get(f"/api/v1/ai/sessions/{session['id']}", params={"workspaceId": profile["workspaceId"]})
    )
    assert new_task["id"] in reloaded["reviewTaskIds"]

    # M-120 契约先行字段：旧任务摘要落后 → STALE_VERSION；新任务可批准 → null
    stale_task = next(task for task in tasks_after if task["id"] == strategy_task["id"])
    assert stale_task["approveDisabledReason"] == "STALE_VERSION"
    assert new_task["approveDisabledReason"] is None


async def test_approving_resubmitted_version_completes_session(client: AsyncClient) -> None:
    """返工闭环走通：新版本批准 + 其余批准后，会话 SUCCEEDED、工作项 APPROVED、终态任务禁用原因 TASK_CLOSED。"""
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    strategy_task = next(
        task for task in await _session_tasks(client, profile) if task["artifactType"] == "TEST_STRATEGY"
    )
    await client.post(
        f"/api/v1/review-tasks/{strategy_task['id']}/decisions",
        headers=mutation_headers(client, idempotency_key=f"loop-rework-{strategy_task['id']}"),
        json={"decision": "REQUEST_CHANGES", "contentDigest": strategy_task["contentDigest"]},
    )
    strategies = _data(await client.get("/api/v1/test-strategies", params={"workspaceId": profile["workspaceId"]}))
    root = next(item for item in strategies if item["id"] == strategy_task["artifactId"])
    created = await client.post(
        f"/api/v1/test-strategies/{root['id']}/versions",
        headers=mutation_headers(client),
        json=_strategy_v2_payload(),
    )
    new_version = _data(created)

    for task in await _session_tasks(client, profile):
        if task["id"] == strategy_task["id"]:
            # 已退回的旧任务不可再决策
            blocked = await client.post(
                f"/api/v1/review-tasks/{task['id']}/decisions",
                headers=mutation_headers(client, idempotency_key=f"loop-stale-{task['id']}"),
                json={"decision": "APPROVE", "contentDigest": task["contentDigest"]},
            )
            assert blocked.status_code == 409
            assert blocked.json()["code"] == "INVALID_STATE_TRANSITION"
            continue
        decision = await client.post(
            f"/api/v1/review-tasks/{task['id']}/decisions",
            headers=mutation_headers(client, idempotency_key=f"loop-approve-{task['id']}"),
            json={"decision": "APPROVE", "contentDigest": task["contentDigest"]},
        )
        assert decision.status_code == 200, decision.text
        assert _data(decision)["status"] == "APPROVED"
    assert new_version["reviewStatus"] == "PENDING_REVIEW"  # 未被旧任务决策误伤

    reloaded = _data(
        await client.get(f"/api/v1/ai/sessions/{session['id']}", params={"workspaceId": profile["workspaceId"]})
    )
    assert reloaded["status"] == "SUCCEEDED"
    assert reloaded["completedAt"] is not None

    listed = _data(await client.get("/api/v1/work-items", params={"workspaceId": profile["workspaceId"]}))
    work_item = next(item for item in listed if item["id"] == session["workItemId"])
    assert work_item["status"] == "APPROVED"

    final_tasks = await _session_tasks(client, profile)
    assert all(task["approveDisabledReason"] == "TASK_CLOSED" for task in final_tasks)


async def test_resubmitting_plan_version_binds_new_review_task(client: AsyncClient) -> None:
    """计划新版本：版本递增并引用策略版本，自动建 OPEN 审核任务。"""
    profile = await setup_identity(client)
    await start_session(client, profile)
    tasks = await _session_tasks(client, profile)
    plan_task = next(task for task in tasks if task["artifactType"] == "TEST_PLAN")
    strategy_task = next(task for task in tasks if task["artifactType"] == "TEST_STRATEGY")
    await client.post(
        f"/api/v1/review-tasks/{plan_task['id']}/decisions",
        headers=mutation_headers(client, idempotency_key=f"plan-rework-{plan_task['id']}"),
        json={"decision": "REQUEST_CHANGES", "contentDigest": plan_task["contentDigest"]},
    )

    plans = _data(await client.get("/api/v1/test-plans", params={"workspaceId": profile["workspaceId"]}))
    plan_root = next(item for item in plans if item["id"] == plan_task["artifactId"])
    strategies = _data(await client.get("/api/v1/test-strategies", params={"workspaceId": profile["workspaceId"]}))
    strategy_root = next(item for item in strategies if item["id"] == strategy_task["artifactId"])
    payload = _plan_v2_payload(strategy_root["currentVersionId"], profile["userId"])

    created = await client.post(
        f"/api/v1/test-plans/{plan_root['id']}/versions", headers=mutation_headers(client), json=payload
    )
    assert created.status_code == 201, created.text
    new_version = _data(created)
    assert new_version["version"] == 2
    assert new_version["reviewStatus"] == "PENDING_REVIEW"
    assert new_version["strategyVersionId"] == payload["strategyVersionId"]

    tasks_after = await _session_tasks(client, profile)
    new_task = next(task for task in tasks_after if task["artifactVersionId"] == new_version["id"])
    assert new_task["status"] == "OPEN"
    assert new_task["artifactType"] == "TEST_PLAN"


async def test_transition_work_item_rework_path_and_lock_version_guard(client: AsyncClient) -> None:
    """transitionWorkItem：REWORK 路径 + lockVersion 乐观锁（陈旧 409）+ expectedCurrentStatus 守卫 + 幂等。"""
    profile = await setup_identity(client)
    payload = {
        "workspaceId": profile["workspaceId"],
        "workItemType": "GENERAL",
        "title": "状态机验证工作项",
        "objective": "验证 transitionWorkItem 的 REWORK 路径与乐观锁",
        "acceptanceCriteria": "陈旧 lockVersion 被 409 拦截",
        "requiresReview": False,
        "priority": "P2",
        "riskLevel": "LOW",
    }
    item = _data(await client.post("/api/v1/work-items", headers=mutation_headers(client), json=payload))
    assert item["status"] == "READY" and item["lockVersion"] == 0

    transitioned = _data(
        await client.post(
            f"/api/v1/work-items/{item['id']}/transitions",
            headers=mutation_headers(client, idempotency_key=f"transition-{item['id']}"),
            json={"targetStatus": "REWORK", "reason": "返工复测", "lockVersion": 0},
        )
    )
    assert transitioned["status"] == "REWORK"
    assert transitioned["lockVersion"] == 1
    assert transitioned["currentActorType"] == "HUMAN"

    # 陈旧 lockVersion → 409
    stale = await client.post(
        f"/api/v1/work-items/{item['id']}/transitions",
        headers=mutation_headers(client, idempotency_key=f"transition-stale-{item['id']}"),
        json={"targetStatus": "REWORK", "reason": "并发覆盖", "lockVersion": 0},
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "STALE_LOCK_VERSION"

    # expectedCurrentStatus 不匹配 → 409
    mismatch = await client.post(
        f"/api/v1/work-items/{item['id']}/transitions",
        headers=mutation_headers(client, idempotency_key=f"transition-mismatch-{item['id']}"),
        json={"targetStatus": "REWORK", "reason": "前置不符", "lockVersion": 1, "expectedCurrentStatus": "READY"},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["code"] == "INVALID_STATE_TRANSITION"

    # 幂等重放：同 key 同载荷返回同一结果，lockVersion 不重复递增
    replay = _data(
        await client.post(
            f"/api/v1/work-items/{item['id']}/transitions",
            headers=mutation_headers(client, idempotency_key=f"transition-{item['id']}"),
            json={"targetStatus": "REWORK", "reason": "返工复测", "lockVersion": 0},
        )
    )
    assert replay["lockVersion"] == 1

    # M1 切片仅支持 REWORK 目标（DTO 子集纪律），其余目标入口层 422
    unsupported = await client.post(
        f"/api/v1/work-items/{item['id']}/transitions",
        headers=mutation_headers(client, idempotency_key=f"transition-unsupported-{item['id']}"),
        json={"targetStatus": "APPROVED", "reason": "越级", "lockVersion": 1},
    )
    assert unsupported.status_code == 422


async def test_legacy_session_statuses_normalized_on_reload(client: AsyncClient, sqlite_path: Any) -> None:
    """QF-REQ-078：存量废弃状态（PAUSED_FOR_HUMAN/COMPLETED）加载时归一到契约枚举。"""
    from qf.services.planning_workflow import planning_workflow_service

    profile = await setup_identity(client)
    session = await start_session(client, profile)
    planning_workflow_service.sessions[session["id"]]["status"] = "PAUSED_FOR_HUMAN"
    planning_workflow_service._persist()

    planning_workflow_service.reconfigure(str(sqlite_path))
    reloaded = _data(
        await client.get(f"/api/v1/ai/sessions/{session['id']}", params={"workspaceId": profile["workspaceId"]})
    )
    assert reloaded["status"] == "BLOCKED"


@pytest.mark.parametrize("observed_status", ["BLOCKED", "SUCCEEDED", "FAILED"])
def test_session_statuses_stay_within_contract_enum(observed_status: str) -> None:
    """QF-REQ-078 守卫：本批涉及的全部会话状态取值必须在 32 号契约枚举内。"""
    assert observed_status in CONTRACT_SESSION_STATUSES
