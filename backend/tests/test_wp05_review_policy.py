"""WP-05 实施切片二：风险分级审核政策与双人复核专项（批次六十五，40 号 Backlog WP-05 / QF-PD-007）。

覆盖：
- 政策路由（服务端派生，04 号 ReviewPolicy 平台最低基线）：WorkItem riskLevel=CRITICAL →
  ReviewTask policyType=FOUR_EYES/minApprovers=2；其余（HIGH/MEDIUM/LOW）→ SINGLE_REVIEW/1；
- FOUR_EYES 双人门：部分批准任务 IN_PROGRESS、版本保持 PENDING_REVIEW、会话保持 BLOCKED；
  同一审批人二次批准 409 FOUR_EYES_SAME_APPROVER（单人绕过双审被拒）；
  第二名不同审批人批准后任务 APPROVED、版本 APPROVED、会话 SUCCEEDED，发布链可用；
- 手工 createReviewTask 指定 FOUR_EYES 同样受双人门约束；
- 退回不要求双人：REJECT 单人即终态（06 号 §9 阻断项直接退回）。
"""

from __future__ import annotations

import hashlib
from typing import Any

from httpx import AsyncClient

from qf.services.planning_workflow import planning_workflow_service
from tests.test_planning_workflow import (
    SOURCE_SNAPSHOT_ID,
    active_release_id,
    mutation_headers,
    setup_identity,
    start_session,
)


def _data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


async def _prepare_critical_chain(client: AsyncClient, profile: dict[str, Any]) -> tuple[str, str]:
    """复制 prepare_source_and_work_item 助手链，工作项 riskLevel 用 CRITICAL 触发 FOUR_EYES。"""
    import uuid as _uuid

    workspace_id = profile["workspaceId"]
    requirement_response = await client.post(
        "/api/v1/knowledge/requirements",
        headers=mutation_headers(client),
        json={"workspaceId": workspace_id, "name": "高风险退款需求", "documentType": "PRD"},
    )
    assert requirement_response.status_code == 201
    requirement_id = requirement_response.json()["data"]["id"]

    content = "# 高风险退款\n资金路径全链路高风险，需双人复核后发布。"
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
            "title": "生成高风险退款测试资产",
            "objective": "验证资金路径：双人复核政策触发与发布门",
            "acceptanceCriteria": "CRITICAL 工作项的资产发布前必须两名审批人批准",
            "requiresReview": True,
            "priority": "P0",
            "riskLevel": "CRITICAL",
        },
    )
    assert work_item_response.status_code == 201
    work_item_id = work_item_response.json()["data"]["id"]

    nonce = _uuid.uuid4().hex
    card = await client.post(
        f"/api/v1/work-items/{work_item_id}/task-cards",
        headers=mutation_headers(client, idempotency_key=f"wp65-card-{nonce}"),
        json={
            "objective": "双人复核链任务卡",
            "scope": "CRITICAL 风险资产",
            "acceptanceCriteria": "FOUR_EYES 门生效",
            "constraints": "无",
            "requestedPermissions": [],
            "budget": {},
        },
    )
    assert card.status_code == 201, card.text
    plan = await client.post(
        f"/api/v1/work-items/{work_item_id}/agent-plans",
        headers=mutation_headers(client, idempotency_key=f"wp65-plan-{nonce}"),
        json={
            "taskCardId": card.json()["data"]["id"],
            "steps": [{"stepKey": "run", "agentRole": "coordinator", "description": "双人链步骤"}],
        },
    )
    assert plan.status_code == 201, plan.text
    decision = await client.post(
        f"/api/v1/agent-plans/{plan.json()['data']['id']}/decisions",
        headers=mutation_headers(client, idempotency_key=f"wp65-decide-{nonce}"),
        json={
            "decision": "APPROVE",
            "expectedContentDigest": plan.json()["data"]["contentDigest"],
            "reason": "双人链批准",
        },
    )
    assert decision.status_code == 201, decision.text
    return requirement_version_id, work_item_id


async def _start_session_on(
    client: AsyncClient, profile: dict[str, Any], requirement_version_id: str, work_item_id: str
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/ai/sessions",
        headers=mutation_headers(client, idempotency_key="wp65-session-0000001"),
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


async def test_critical_risk_four_eyes_requires_two_distinct_approvers(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    requirement_version_id, work_item_id = await _prepare_critical_chain(client, profile)
    session = await _start_session_on(client, profile, requirement_version_id, work_item_id)
    params = {"workspaceId": profile["workspaceId"]}
    tasks = _data(await client.get("/api/v1/review-tasks", params=params))
    strategy_task = next(task for task in tasks if task["artifactType"] == "TEST_STRATEGY")
    assert strategy_task["policyType"] == "FOUR_EYES"
    assert strategy_task["minApprovers"] == 2
    assert strategy_task["approvals"] == []

    # 第一名审批人批准 → 部分批准：任务 IN_PROGRESS、版本保持 PENDING_REVIEW、会话保持 BLOCKED
    first = await client.post(
        f"/api/v1/review-tasks/{strategy_task['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="wp65-approve-1-0000001"),
        json={"decision": "APPROVE", "contentDigest": strategy_task["contentDigest"]},
    )
    assert first.status_code == 200, first.text
    assert first.json()["data"]["status"] == "IN_PROGRESS"
    assert len(first.json()["data"]["approvals"]) == 1
    assert (
        planning_workflow_service.strategy_versions[strategy_task["artifactVersionId"]]["reviewStatus"]
        == "PENDING_REVIEW"
    )
    assert _data(await client.get(f"/api/v1/ai/sessions/{session['id']}", params=params))["status"] == "BLOCKED"

    # 单人绕过双审：同一审批人换键二次批准 → 409 FOUR_EYES_SAME_APPROVER
    bypass = await client.post(
        f"/api/v1/review-tasks/{strategy_task['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="wp65-approve-1-0000002"),
        json={"decision": "APPROVE", "contentDigest": strategy_task["contentDigest"]},
    )
    assert bypass.status_code == 409
    assert bypass.json()["code"] == "FOUR_EYES_SAME_APPROVER"

    # 第二名不同审批人（服务面）批准 → 任务 APPROVED、版本 APPROVED、会话收敛
    second = await planning_workflow_service.decide_review(
        str(profile["tenantId"]),
        str(profile["workspaceId"]),
        "reviewer-2",
        "USER",
        frozenset({"artifact.test_strategy.approve"}),
        strategy_task["id"],
        "wp65-approve-2-0000001",
        {"decision": "APPROVE", "contentDigest": strategy_task["contentDigest"], "comments": "交叉复核通过"},
    )
    assert second["status"] == "APPROVED"
    assert len(second["approvals"]) == 2
    assert planning_workflow_service.strategy_versions[strategy_task["artifactVersionId"]]["reviewStatus"] == "APPROVED"

    # 会话收敛需要全部任务终态：CRITICAL 工作项下 plan/用例（含多张用例）同为 FOUR_EYES，各需两名审批人
    approval_capabilities = {
        "TEST_PLAN": "artifact.test_plan.approve",
        "TEST_CASE": "artifact.test_case.approve",
    }
    for task in tasks:
        capability = approval_capabilities.get(task["artifactType"])
        if capability is None:
            continue
        first_of_type = await client.post(
            f"/api/v1/review-tasks/{task['id']}/decisions",
            headers=mutation_headers(client, idempotency_key=f"wp65-approve-1-{task['id'][:8]}"),
            json={"decision": "APPROVE", "contentDigest": task["contentDigest"]},
        )
        assert first_of_type.status_code == 200, first_of_type.text
        await planning_workflow_service.decide_review(
            str(profile["tenantId"]),
            str(profile["workspaceId"]),
            "reviewer-2",
            "USER",
            frozenset({capability}),
            task["id"],
            f"wp65-approve-2-{task['id'][:8]}",
            {"decision": "APPROVE", "contentDigest": task["contentDigest"]},
        )
    assert _data(await client.get(f"/api/v1/ai/sessions/{session['id']}", params=params))["status"] == "SUCCEEDED"

    # 发布链在双人批准后可用
    published = await client.post(
        f"/api/v1/test-strategies/{strategy_task['artifactId']}/versions/{strategy_task['artifactVersionId']}/publish",
        headers=mutation_headers(client, idempotency_key="wp65-publish-0000001"),
    )
    assert published.status_code == 200, published.text
    assert published.json()["data"]["reviewStatus"] == "PUBLISHED"


async def test_non_critical_defaults_single_review_and_reject_needs_no_second(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    await start_session(client, profile)
    params = {"workspaceId": profile["workspaceId"]}
    tasks = _data(await client.get("/api/v1/review-tasks", params=params))
    strategy_task = next(task for task in tasks if task["artifactType"] == "TEST_STRATEGY")
    assert strategy_task["policyType"] == "SINGLE_REVIEW"
    assert strategy_task["minApprovers"] == 1

    # 退回不要求双人：REJECT 单人即终态（阻断项直接退回，06 号 §9）
    rejected = await client.post(
        f"/api/v1/review-tasks/{strategy_task['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="wp65-reject-0000001"),
        json={"decision": "REJECT", "contentDigest": strategy_task["contentDigest"]},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["data"]["status"] == "REJECTED"
    assert planning_workflow_service.strategy_versions[strategy_task["artifactVersionId"]]["reviewStatus"] == "DRAFT"


async def test_manual_four_eyes_task_enforces_double_gate(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    await start_session(client, profile)
    params = {"workspaceId": profile["workspaceId"]}
    tasks = _data(await client.get("/api/v1/review-tasks", params=params))
    case_task = next(task for task in tasks if task["artifactType"] == "TEST_CASE")

    manual = await client.post(
        "/api/v1/review-tasks",
        headers=mutation_headers(client, idempotency_key="wp65-manual-0000001"),
        json={
            "workItemId": case_task["workItemId"],
            "artifactType": "TEST_CASE",
            "artifactId": case_task["artifactId"],
            "artifactVersionId": case_task["artifactVersionId"],
            "contentDigest": case_task["contentDigest"],
            "policyType": "FOUR_EYES",
            "assignees": [
                {
                    "userId": profile["userId"],
                    "reviewRole": "APPROVER",
                    "requiredCapability": "artifact.test_case.approve",
                }
            ],
        },
    )
    assert manual.status_code == 201, manual.text
    task = manual.json()["data"]
    assert task["policyType"] == "FOUR_EYES"
    assert task["minApprovers"] == 2

    first = await client.post(
        f"/api/v1/review-tasks/{task['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="wp65-manual-approve-1"),
        json={"decision": "APPROVE", "contentDigest": case_task["contentDigest"]},
    )
    assert first.status_code == 200, first.text
    assert first.json()["data"]["status"] == "IN_PROGRESS"
