"""TC-RT-001~014：审核链自动化执行（任务/产物/Diff/决策状态机/幂等）。

需要真实产物三元组（artifactId/artifactVersionId/contentDigest）的用例
通过 /ai/sessions 的 gate0 会话链构造（与 backend/tests/test_m2 同模式）。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from conftest import envelope, mutation_headers, setup_identity

DIGEST_64 = "a" * 64


async def session_strategy_task(client: AsyncClient, profile: dict) -> dict:
    """跑一次 gate0 会话，返回其自动创建的 TEST_STRATEGY 审核任务。"""
    from conftest import gate0_session

    await gate0_session(client, profile)
    listed = await client.get(
        "/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]}
    )
    assert listed.status_code == 200, listed.text
    tasks = envelope(listed)["data"]
    return next(task for task in tasks if task["artifactType"] == "TEST_STRATEGY")


async def manual_review_task(
    client: AsyncClient, source: dict, profile: dict, key: str = "rt-manual-key-000001"
) -> dict:
    payload = {
        "workItemId": source["workItemId"],
        "artifactType": source["artifactType"],
        "artifactId": source["artifactId"],
        "artifactVersionId": source["artifactVersionId"],
        "contentDigest": source["contentDigest"],
        "policyType": "SINGLE_REVIEW",
    }
    response = await client.post(
        "/api/v1/review-tasks", headers=mutation_headers(client, key), json=payload
    )
    assert response.status_code == 201, response.text
    return envelope(response)["data"]


async def test_tc_rt_001_manual_create_201_open(client: AsyncClient) -> None:
    """TC-RT-001：携带幂等键创建绑定精确版本的审核任务返回 201。"""
    profile = await setup_identity(client)
    source = await session_strategy_task(client, profile)
    task = await manual_review_task(client, source, profile)
    assert task["status"] == "OPEN"
    assert task["contentDigest"] == source["contentDigest"]


async def test_tc_rt_002_artifact_immutable_digest(client: AsyncClient) -> None:
    """TC-RT-002：读取审核产物返回不可变版本与 64 位摘要。"""
    profile = await setup_identity(client)
    source = await session_strategy_task(client, profile)
    response = await client.get(f"/api/v1/review-tasks/{source['id']}/artifact")
    assert response.status_code == 200, response.text
    data = envelope(response)["data"]
    assert data["artifactVersionId"] == source["artifactVersionId"]
    import re

    assert re.fullmatch(r"[a-f0-9]{64}", data["contentDigest"]), data["contentDigest"]


async def test_tc_rt_003_diff_first_version_no_baseline(client: AsyncClient) -> None:
    """TC-RT-003：首版产物 Diff 无基线降级返回 hasBaseline=false。"""
    profile = await setup_identity(client)
    source = await session_strategy_task(client, profile)
    response = await client.get(f"/api/v1/review-tasks/{source['id']}/artifact/diff")
    assert response.status_code == 200, response.text
    data = envelope(response)["data"]
    assert data["hasBaseline"] is False
    assert data["fields"] == []
    assert data["baseVersionId"] is None


async def test_tc_rt_004_decision_idempotent_replay(client: AsyncClient) -> None:
    """TC-RT-004：同一幂等键重放审核决策返回首次结果。"""
    profile = await setup_identity(client)
    task = await session_strategy_task(client, profile)
    headers = mutation_headers(client, "rt-idem-key-00000001")
    body = {"decision": "APPROVE", "contentDigest": task["contentDigest"]}
    first = await client.post(
        f"/api/v1/review-tasks/{task['id']}/decisions", headers=headers, json=body
    )
    assert first.status_code == 200, first.text
    replay = await client.post(
        f"/api/v1/review-tasks/{task['id']}/decisions", headers=headers, json=body
    )
    assert replay.status_code == 200
    assert envelope(replay)["data"]["id"] == envelope(first)["data"]["id"]
    assert envelope(replay)["data"]["status"] == "APPROVED"


async def test_tc_rt_005_approve_transitions(client: AsyncClient) -> None:
    """TC-RT-005：APPROVE 决策使 OPEN 任务迁移到 APPROVED。"""
    profile = await setup_identity(client)
    task = await session_strategy_task(client, profile)
    response = await client.post(
        f"/api/v1/review-tasks/{task['id']}/decisions",
        headers=mutation_headers(client, "rt-ap-key-0000000001"),
        json={"decision": "APPROVE", "contentDigest": task["contentDigest"]},
    )
    assert response.status_code == 200, response.text
    data = envelope(response)["data"]
    assert data["status"] == "APPROVED"


async def test_tc_rt_006_request_changes_transitions(client: AsyncClient) -> None:
    """TC-RT-006：REQUEST_CHANGES 决策使 OPEN 任务迁移到 CHANGES_REQUESTED。"""
    profile = await setup_identity(client)
    task = await session_strategy_task(client, profile)
    response = await client.post(
        f"/api/v1/review-tasks/{task['id']}/decisions",
        headers=mutation_headers(client, "rt-rc-key-0000000001"),
        json={
            "decision": "REQUEST_CHANGES",
            "contentDigest": task["contentDigest"],
            "comments": "请补充",
        },
    )
    assert response.status_code == 200, response.text
    assert envelope(response)["data"]["status"] == "CHANGES_REQUESTED"


async def test_tc_rt_007_reject_transitions(client: AsyncClient) -> None:
    """TC-RT-007：REJECT 决策使 OPEN 任务迁移到 REJECTED。"""
    profile = await setup_identity(client)
    task = await session_strategy_task(client, profile)
    response = await client.post(
        f"/api/v1/review-tasks/{task['id']}/decisions",
        headers=mutation_headers(client, "rt-rj-key-0000000001"),
        json={"decision": "REJECT", "contentDigest": task["contentDigest"]},
    )
    assert response.status_code == 200, response.text
    assert envelope(response)["data"]["status"] == "REJECTED"


async def test_tc_rt_008_reject_reverts_version_to_draft(client: AsyncClient) -> None:
    """TC-RT-008：退回决策后任务迁移（版本回 DRAFT 无独立读取面，断言任务面）。"""
    profile = await setup_identity(client)
    task = await session_strategy_task(client, profile)
    response = await client.post(
        f"/api/v1/review-tasks/{task['id']}/decisions",
        headers=mutation_headers(client, "rt-rd-key-0000000001"),
        json={"decision": "REQUEST_CHANGES", "contentDigest": task["contentDigest"]},
    )
    assert response.status_code == 200
    data = envelope(response)["data"]
    assert data["status"] == "CHANGES_REQUESTED"


async def test_tc_rt_009_terminal_task_decision_409(client: AsyncClient) -> None:
    """TC-RT-009：终态审核任务再决策返回 409。"""
    profile = await setup_identity(client)
    task = await session_strategy_task(client, profile)
    approve = await client.post(
        f"/api/v1/review-tasks/{task['id']}/decisions",
        headers=mutation_headers(client, "rt-t1-key-0000000001"),
        json={"decision": "APPROVE", "contentDigest": task["contentDigest"]},
    )
    assert approve.status_code == 200
    again = await client.post(
        f"/api/v1/review-tasks/{task['id']}/decisions",
        headers=mutation_headers(client, "rt-t2-key-0000000001"),
        json={"decision": "REJECT", "contentDigest": task["contentDigest"]},
    )
    assert again.status_code == 409, again.text
    assert envelope(again)["code"] == "INVALID_STATE_TRANSITION"


async def test_tc_rt_010_stale_digest_409(client: AsyncClient) -> None:
    """TC-RT-010：contentDigest 不一致时决策返回 409 STALE_ARTIFACT_VERSION。"""
    profile = await setup_identity(client)
    task = await session_strategy_task(client, profile)
    response = await client.post(
        f"/api/v1/review-tasks/{task['id']}/decisions",
        headers=mutation_headers(client, "rt-sd-key-0000000001"),
        json={"decision": "APPROVE", "contentDigest": DIGEST_64},
    )
    assert response.status_code == 409, response.text
    assert envelope(response)["code"] == "STALE_ARTIFACT_VERSION"


@pytest.mark.skip(reason="TC-RT-011：本地认证仅签发 USER 会话，无法构造 AGENT 主体调用")
async def test_tc_rt_011_agent_actor_403(client: AsyncClient) -> None:
    """TC-RT-011：非人类主体提交决策返回 403（环境不可构造，skip）。"""


@pytest.mark.skip(
    reason="TC-RT-012：本地单管理员 capabilities 为全集，无法构造受限会话"
)
async def test_tc_rt_012_missing_capability_403(client: AsyncClient) -> None:
    """TC-RT-012：缺少审批能力时决策返回 403（环境不可构造，skip）。"""


async def test_tc_rt_013_get_review_task_roundtrip(client: AsyncClient) -> None:
    """TC-RT-013：创建审核任务后读回详情字段一致。"""
    profile = await setup_identity(client)
    source = await session_strategy_task(client, profile)
    task = await manual_review_task(client, source, profile, key="rt-rt-key-0000000001")
    response = await client.get(f"/api/v1/review-tasks/{task['id']}")
    assert response.status_code == 200, response.text
    data = envelope(response)["data"]
    assert data["artifactVersionId"] == task["artifactVersionId"]
    assert data["contentDigest"] == task["contentDigest"]
    assert data["policyType"] == "SINGLE_REVIEW"
    missing = await client.get(
        "/api/v1/review-tasks/00000000-0000-4000-8000-000000000000"
    )
    assert missing.status_code == 404
