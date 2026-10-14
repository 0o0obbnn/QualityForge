"""WP-01A 真实项目/Release 上下文专项（40 号 Backlog §6.2 负向验收承载）。

覆盖五件事：
1. listWorkspaces 投影只含当前成员关系内的 Workspace；
2. createWorkItem 携带的 releaseId 必须存在、ACTIVE 且属于当前 Workspace，否则 409 RELEASE_NOT_IN_WORKSPACE；
3. 认证种子出的 ACTIVE Release 可正常创建工作项（正路不回归）；
4. lastBusinessUpdatedAt 口径与排序：业务事件刷新并反超，无事件回退 createdAt；
5. 负向：轮询/Trace 只读与 provider 运行面事件不刷新排序（QF-PD-020/023）。
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from qf.services.planning_workflow import planning_workflow_service
from tests.test_planning_workflow import (
    active_release_id,
    mutation_headers,
    setup_identity,
)


def _work_item_body(workspace_id: str, release_id: str) -> dict[str, object]:
    return {
        "workspaceId": workspace_id,
        "releaseId": release_id,
        "workItemType": "STRATEGY",
        "title": "WP-01A 上下文验证工作项",
        "objective": "验证 Release 归属门控",
        "acceptanceCriteria": "跨 Workspace/非 ACTIVE/不存在的 releaseId 被服务端拒绝",
        "requiresReview": True,
        "priority": "P1",
        "riskLevel": "MEDIUM",
    }


async def _list_workspaces(client: AsyncClient) -> list[dict[str, object]]:
    response = await client.get("/api/v1/workspaces")
    assert response.status_code == 200
    return response.json()["data"]


async def test_workspaces_projection_is_membership_scoped(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    response = await client.get("/api/v1/workspaces")
    assert response.status_code == 200
    workspaces = response.json()["data"]
    ids = {workspace["id"] for workspace in workspaces}
    assert profile["workspaceId"] in ids
    assert str(uuid.uuid4()) not in ids


async def test_create_work_item_rejects_release_outside_workspace(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    response = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client),
        json=_work_item_body(profile["workspaceId"], str(uuid.uuid4())),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "RELEASE_NOT_IN_WORKSPACE"


async def test_create_work_item_accepts_seeded_active_release(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    release_id = await active_release_id(client, profile["workspaceId"])
    response = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client),
        json=_work_item_body(profile["workspaceId"], release_id),
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["releaseId"] == release_id

async def test_workspaces_order_by_last_business_update(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    ws1 = profile["workspaceId"]
    seeded = planning_workflow_service.seed_workspace(profile["tenantId"], profile["userId"], "第二项目")
    ws2 = seeded["id"]

    # 无业务事件：lastBusinessUpdatedAt 回退 createdAt，后种的第二项目排前
    workspaces = await _list_workspaces(client)
    assert [w["id"] for w in workspaces] == [ws2, ws1]
    assert all(w["lastBusinessUpdatedAt"] for w in workspaces)

    # ws1 发生业务事件（工作项退回迁移）后反超
    release_id = await active_release_id(client, ws1)
    created = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client),
        json=_work_item_body(ws1, release_id),
    )
    assert created.status_code == 201, created.text
    transitioned = await client.post(
        f"/api/v1/work-items/{created.json()['data']['id']}/transitions",
        headers=mutation_headers(client, idempotency_key="wp01a-ordering-0001"),
        json={
            "targetStatus": "REWORK",
            "reason": "排序口径验证",
            "expectedCurrentStatus": "READY",
            "lockVersion": 0,
        },
    )
    assert transitioned.status_code == 200, transitioned.text

    workspaces = await _list_workspaces(client)
    assert [w["id"] for w in workspaces] == [ws1, ws2]
    ws1_row, ws2_row = workspaces[0], workspaces[1]
    assert ws1_row["lastBusinessUpdatedAt"] > str(ws2_row["lastBusinessUpdatedAt"])
    assert ws2_row["lastBusinessUpdatedAt"] == ws2_row["createdAt"]


async def test_reads_and_provider_events_do_not_refresh_ordering(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    ws1 = profile["workspaceId"]
    seeded = planning_workflow_service.seed_workspace(profile["tenantId"], profile["userId"], "第二项目")
    ws2 = seeded["id"]
    before = {w["id"]: w["lastBusinessUpdatedAt"] for w in await _list_workspaces(client)}
    assert [w["id"] for w in await _list_workspaces(client)] == [ws2, ws1]

    # 负向一：高频只读轮询（工作项/事件/指标/会话）不刷新
    for _ in range(3):
        params = {"workspaceId": ws1}
        assert (await client.get("/api/v1/work-items", params=params)).status_code == 200
        assert (await client.get("/api/v1/observability/events", params=params)).status_code == 200
        assert (await client.get("/api/v1/observability/metrics", params=params)).status_code == 200
        assert (await client.get("/api/v1/ai/sessions", params=params)).status_code == 200
    after_reads = {w["id"]: w["lastBusinessUpdatedAt"] for w in await _list_workspaces(client)}
    assert after_reads == before

    # 负向二：provider 运行面事件（即使误挂到工作区）不刷新（口径显式排除）
    planning_workflow_service.events.emit(
        tenant_id=profile["tenantId"],
        workspace_id=ws1,
        actor_id=profile["userId"],
        subject_type="provider",
        subject_id="deterministic-local",
        event_type="provider.switched",
        payload={"providerVersion": "v1.0.0", "gatePassed": True},
    )
    after_provider = {w["id"]: w["lastBusinessUpdatedAt"] for w in await _list_workspaces(client)}
    assert after_provider == before
    assert [w["id"] for w in await _list_workspaces(client)] == [ws2, ws1]


async def test_switch_workspace_command_binding_and_isolation(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    ws1 = profile["workspaceId"]
    ws1_release = await active_release_id(client, ws1)
    seeded = planning_workflow_service.seed_workspace(profile["tenantId"], profile["userId"], "第二项目")
    ws2 = seeded["id"]

    # 非成员工作区：403 拒绝
    denied = await client.post(
        "/api/v1/auth/switch-workspace",
        headers=mutation_headers(client),
        json={"workspaceId": str(uuid.uuid4())},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "FORBIDDEN"

    # 切到 ws2：actor 工作区绑定随之生效
    switched = await client.post(
        "/api/v1/auth/switch-workspace",
        headers=mutation_headers(client),
        json={"workspaceId": ws2},
    )
    assert switched.status_code == 200, switched.text
    assert switched.json()["data"]["workspaceId"] == ws2
    me = await client.get("/api/v1/auth/me")
    assert me.json()["data"]["workspaceId"] == ws2

    ws2_release = await active_release_id(client, ws2)
    created = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client),
        json=_work_item_body(ws2, ws2_release),
    )
    assert created.status_code == 201, created.text

    # 已切换后旧工作区的写入被隔离（不残留上一工作区上下文）
    stale_ws1 = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client),
        json=_work_item_body(ws1, ws1_release),
    )
    assert stale_ws1.status_code == 403
    assert stale_ws1.json()["code"] == "FORBIDDEN"

    # 切回 ws1 恢复
    back = await client.post(
        "/api/v1/auth/switch-workspace",
        headers=mutation_headers(client),
        json={"workspaceId": ws1},
    )
    assert back.status_code == 200
    assert back.json()["data"]["workspaceId"] == ws1


async def test_project_context_projection_counts_and_pins(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    ws1 = profile["workspaceId"]
    release_id = await active_release_id(client, ws1)
    seeded = planning_workflow_service.seed_workspace(profile["tenantId"], profile["userId"], "第二项目")
    ws2 = seeded["id"]

    # 空态投影：计数为零、无置顶
    projection = (await client.get(f"/api/v1/workspaces/{ws1}/context-projection")).json()["data"]
    assert projection["workspace"]["id"] == ws1
    assert projection["currentRelease"]["id"] == release_id
    assert projection["openReviewCount"] == 0
    assert projection["activeWorkItemCount"] == 0
    assert projection["runningExecutionCount"] == 0
    assert projection["pinnedWorkspaces"] == []

    # 建工作项后活跃计数 +1
    created = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client),
        json=_work_item_body(ws1, release_id),
    )
    assert created.status_code == 201
    projection = (await client.get(f"/api/v1/workspaces/{ws1}/context-projection")).json()["data"]
    assert projection["activeWorkItemCount"] == 1

    # 置顶另一成员工作区（不限于当前绑定）+ 列表置顶排序
    pinned = await client.post(
        f"/api/v1/workspaces/{ws2}/pin",
        headers=mutation_headers(client, idempotency_key="wp01a-pin-0000000001"),
        json={"pinned": True},
    )
    assert pinned.status_code == 200, pinned.text
    workspaces = await _list_workspaces(client)
    assert workspaces[0]["id"] == ws2 and workspaces[0]["pinned"] is True
    assert any(w["pinned"] is False for w in workspaces[1:])

    # 非成员工作区置顶被拒
    denied = await client.post(
        f"/api/v1/workspaces/{uuid.uuid4()}/pin",
        headers=mutation_headers(client, idempotency_key="wp01a-pin-0000000002"),
        json={"pinned": True},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "FORBIDDEN"


async def test_login_defaults_to_recently_pinned_workspace(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    ws1 = profile["workspaceId"]
    seeded = planning_workflow_service.seed_workspace(profile["tenantId"], profile["userId"], "第二项目")
    ws2 = seeded["id"]

    from tests.test_planning_workflow import LOCAL_PASSWORD

    # 未置顶：登录默认首行成员工作区
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "reviewer@qualityforge.example", "password": LOCAL_PASSWORD},
    )
    assert login.status_code == 200
    assert login.json()["data"]["workspaceId"] == ws1

    # 置顶 ws2 后重新登录：默认切到常用项目
    pin = await client.post(
        f"/api/v1/workspaces/{ws2}/pin",
        headers=mutation_headers(client, idempotency_key="wp01a-loginpin-0001"),
        json={"pinned": True},
    )
    assert pin.status_code == 200
    login_again = await client.post(
        "/api/v1/auth/login",
        json={"email": "reviewer@qualityforge.example", "password": LOCAL_PASSWORD},
    )
    assert login_again.status_code == 200
    assert login_again.json()["data"]["workspaceId"] == ws2


async def test_archive_release_negative_chain(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    seeded = planning_workflow_service.seed_workspace(profile["tenantId"], profile["userId"], "第二项目")
    ws2 = seeded["id"]

    switched = await client.post(
        "/api/v1/auth/switch-workspace",
        headers=mutation_headers(client),
        json={"workspaceId": ws2},
    )
    assert switched.status_code == 200
    ws2_release = await active_release_id(client, ws2)

    # 归档 → 列表消失 → 建项同码 409 → 重复归档 409 → 不存在 404 → 投影 currentRelease 为空
    archived = await client.post(
        f"/api/v1/workspaces/{ws2}/releases/{ws2_release}/archive",
        headers=mutation_headers(client, idempotency_key="wp01a-archive-0001"),
    )
    assert archived.status_code == 200, archived.text

    releases = (await client.get(f"/api/v1/workspaces/{ws2}/releases")).json()["data"]
    assert releases == []

    rejected = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client),
        json=_work_item_body(ws2, ws2_release),
    )
    assert rejected.status_code == 409
    assert rejected.json()["code"] == "RELEASE_NOT_IN_WORKSPACE"

    again = await client.post(
        f"/api/v1/workspaces/{ws2}/releases/{ws2_release}/archive",
        headers=mutation_headers(client, idempotency_key="wp01a-archive-0002"),
    )
    assert again.status_code == 409
    assert again.json()["code"] == "RELEASE_ALREADY_ARCHIVED"

    missing = await client.post(
        f"/api/v1/workspaces/{ws2}/releases/{uuid.uuid4()}/archive",
        headers=mutation_headers(client, idempotency_key="wp01a-archive-0003"),
    )
    assert missing.status_code == 404

    projection = (await client.get(f"/api/v1/workspaces/{ws2}/context-projection")).json()["data"]
    assert projection["currentRelease"] is None
