"""TC-WI-001~019：工作板自动化执行（创建/查询/流转/分派/SLA/幂等/并发）。"""

from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from conftest import envelope, mutation_headers, setup_identity

WORK_ITEM_BODY = {
    "workItemType": "GENERAL",
    "title": "自动化-工作项",
    "objective": "验证工作板链路",
    "acceptanceCriteria": "返回201且可查询",
    "requiresReview": True,
    "priority": "P2",
    "riskLevel": "MEDIUM",
}


async def create_work_item(client: AsyncClient, workspace_id: str, **overrides) -> dict:
    body = {**WORK_ITEM_BODY, "workspaceId": workspace_id, **overrides}
    response = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client, "wi-create-key-000001"),
        json=body,
    )
    assert response.status_code == 201, response.text
    return envelope(response)["data"]


@pytest.mark.xfail(strict=True, reason="缺陷#2：33号Schema work_items.status DEFAULT 'BACKLOG'，实现创建路径写死 READY（planning_workflow.py:507）")
async def test_tc_wi_001_create_201_defaults(client: AsyncClient) -> None:
    """TC-WI-001：携带全部必填字段创建工作项返回 201。"""
    profile = await setup_identity(client)
    item = await create_work_item(client, profile["workspaceId"])
    assert item["id"]
    assert item["status"] == "BACKLOG"
    assert item["lockVersion"] == 0
    assert item["createdAt"]


async def test_tc_wi_002_list_pagination_envelope(client: AsyncClient) -> None:
    """TC-WI-002：工作项列表分页返回 page/pageSize/total。"""
    profile = await setup_identity(client)
    await create_work_item(client, profile["workspaceId"])
    response = await client.get(
        "/api/v1/work-items",
        params={"page": 1, "pageSize": 20, "workspaceId": profile["workspaceId"]},
    )
    assert response.status_code == 200
    body = envelope(response)
    assert isinstance(body["data"], list)
    assert body["total"] >= 1


async def test_tc_wi_003_get_detail_fields(client: AsyncClient) -> None:
    """TC-WI-003：按 ID 读取新建工作项返回完整字段。"""
    profile = await setup_identity(client)
    item = await create_work_item(client, profile["workspaceId"])
    response = await client.get(f"/api/v1/work-items/{item['id']}")
    assert response.status_code == 200
    data = envelope(response)["data"]
    for field in (
        "title",
        "objective",
        "acceptanceCriteria",
        "requiresReview",
        "priority",
        "riskLevel",
        "status",
        "lockVersion",
    ):
        assert field in data, f"缺字段 {field}"


async def test_tc_wi_004_sla_overview_structure(client: AsyncClient) -> None:
    """TC-WI-004（C-004）：SLA 汇总分组 P0/P1/P2 与 overall 口径。"""
    profile = await setup_identity(client)
    ws = profile["workspaceId"]
    for priority in ("P0", "P1", "P2", "P3"):
        await create_work_item(client, ws, priority=priority, title=f"SLA-{priority}")
    response = await client.get(
        "/api/v1/work-items/sla-overview", params={"workspaceId": ws}
    )
    assert response.status_code == 200, response.text
    data = envelope(response)["data"]
    groups = {g["priority"]: g for g in data["groups"]}
    assert set(groups) == {"P0", "P1", "P2"}, "P3 不得单独成组"
    for g in groups.values():
        assert g["met"] + g["overdue"] <= g["total"]
        assert 0 <= g["metRate"] <= 1
    assert data["overall"]["total"] >= 4


async def test_tc_wi_005_transition_backlog_to_rework(client: AsyncClient) -> None:
    """TC-WI-005：BACKLOG 工作项流转到 REWORK 并推进 lockVersion。"""
    profile = await setup_identity(client)
    item = await create_work_item(client, profile["workspaceId"])
    response = await client.post(
        f"/api/v1/work-items/{item['id']}/transitions",
        headers=mutation_headers(client, "wi-trans-key-000001"),
        json={"targetStatus": "REWORK", "reason": "退回返工", "lockVersion": 0},
    )
    assert response.status_code == 200, response.text
    data = envelope(response)["data"]
    assert data["status"] == "REWORK"
    assert data["lockVersion"] == 1


async def test_tc_wi_006_assign_200(client: AsyncClient) -> None:
    """TC-WI-006：分派合法 assignee 成功且响应携带 assigneeId。"""
    profile = await setup_identity(client)
    item = await create_work_item(client, profile["workspaceId"])
    response = await client.post(
        f"/api/v1/work-items/{item['id']}/assign",
        headers=mutation_headers(client),
        json={"workspaceId": profile["workspaceId"], "assigneeId": profile["userId"]},
    )
    assert response.status_code == 200, response.text
    assert envelope(response)["data"]["assigneeId"] == profile["userId"]


async def test_tc_wi_007_assign_same_assignee_idempotent(client: AsyncClient) -> None:
    """TC-WI-007：重复分派同一 assignee 幂等 no-op 返回 200。"""
    profile = await setup_identity(client)
    item = await create_work_item(client, profile["workspaceId"])
    body = {"workspaceId": profile["workspaceId"], "assigneeId": profile["userId"]}
    headers = mutation_headers(client)
    first = await client.post(f"/api/v1/work-items/{item['id']}/assign", headers=headers, json=body)
    assert first.status_code == 200
    lock_before = envelope(first)["data"]["lockVersion"]
    second = await client.post(f"/api/v1/work-items/{item['id']}/assign", headers=headers, json=body)
    assert second.status_code == 200, second.text
    assert envelope(second)["data"]["lockVersion"] == lock_before


async def test_tc_wi_008_create_missing_title_422(client: AsyncClient) -> None:
    """TC-WI-008：缺失 title 创建工作项返回 422。"""
    profile = await setup_identity(client)
    body = {
        k: v
        for k, v in {**WORK_ITEM_BODY, "workspaceId": profile["workspaceId"]}.items()
        if k != "title"
    }
    response = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client, "wi-miss-key-0000001"),
        json=body,
    )
    assert response.status_code == 422, response.text
    listed = await client.get(
        "/api/v1/work-items",
        params={"page": 1, "pageSize": 20, "workspaceId": profile["workspaceId"]},
    )
    assert envelope(listed)["total"] == 0


async def test_tc_wi_009_get_unknown_404(client: AsyncClient) -> None:
    """TC-WI-009：读取随机不存在的工作项 ID 返回 404。"""
    await setup_identity(client)
    response = await client.get(
        "/api/v1/work-items/00000000-0000-4000-8000-000000000000"
    )
    assert response.status_code == 404
    assert envelope(response)["code"] == "NOT_FOUND"


async def test_tc_wi_010_stale_lock_version_409(client: AsyncClient) -> None:
    """TC-WI-010：lockVersion 陈旧时流转返回 409 STALE_LOCK_VERSION。"""
    profile = await setup_identity(client)
    item = await create_work_item(client, profile["workspaceId"])
    response = await client.post(
        f"/api/v1/work-items/{item['id']}/transitions",
        headers=mutation_headers(client, "wi-stale-key-0000001"),
        json={"targetStatus": "REWORK", "reason": "过期", "lockVersion": 99},
    )
    assert response.status_code == 409, response.text
    assert envelope(response)["code"] == "STALE_LOCK_VERSION"
    detail = await client.get(f"/api/v1/work-items/{item['id']}")
    assert envelope(detail)["data"]["status"] == item["status"]


async def test_tc_wi_011_expected_status_mismatch_409(client: AsyncClient) -> None:
    """TC-WI-011：expectedCurrentStatus 不符时流转返回 409。"""
    profile = await setup_identity(client)
    item = await create_work_item(client, profile["workspaceId"])
    response = await client.post(
        f"/api/v1/work-items/{item['id']}/transitions",
        headers=mutation_headers(client, "wi-expc-key-00000001"),
        json={
            "targetStatus": "REWORK",
            "reason": "预期不符",
            "expectedCurrentStatus": "IN_PROGRESS",
            "lockVersion": 0,
        },
    )
    assert response.status_code == 409
    assert envelope(response)["code"] == "INVALID_STATE_TRANSITION"


async def test_tc_wi_012_target_done_422(client: AsyncClient) -> None:
    """TC-WI-012：targetStatus=DONE 时流转返回 422（M1 仅支持 REWORK）。"""
    profile = await setup_identity(client)
    item = await create_work_item(client, profile["workspaceId"])
    response = await client.post(
        f"/api/v1/work-items/{item['id']}/transitions",
        headers=mutation_headers(client, "wi-done-key-00000001"),
        json={"targetStatus": "DONE", "reason": "不支持", "lockVersion": 0},
    )
    assert response.status_code == 422, response.text


async def test_tc_wi_013_assign_invalid_uuid_422(client: AsyncClient) -> None:
    """TC-WI-013：assigneeId 非法字符串分派返回 422。"""
    profile = await setup_identity(client)
    item = await create_work_item(client, profile["workspaceId"])
    response = await client.post(
        f"/api/v1/work-items/{item['id']}/assign",
        headers=mutation_headers(client),
        json={"workspaceId": profile["workspaceId"], "assigneeId": "not-a-uuid"},
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    ("label", "length", "expected"), [("256", 256, 201), ("257", 257, 422)]
)
async def test_tc_wi_014_title_boundary(
    client: AsyncClient, label: str, length: int, expected: int
) -> None:
    """TC-WI-014（C-001）：title 边界 256 通过、257 拒绝。"""
    profile = await setup_identity(client)
    response = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client, f"wi-t{label}-key-0000001"),
        json={**WORK_ITEM_BODY, "workspaceId": profile["workspaceId"], "title": "标" * length},
    )
    assert response.status_code == expected, f"title len={label}: {response.text}"


async def test_tc_wi_014_title_257_rejected(client: AsyncClient) -> None:
    """TC-WI-014（C-001）：257 字符 title 被拒绝。"""
    profile = await setup_identity(client)
    body = {
        **WORK_ITEM_BODY,
        "workspaceId": profile["workspaceId"],
        "title": "标" * 257,
    }
    response = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client, "wi-t257-key-0000001"),
        json=body,
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    ("label", "page_size", "expected"),
    [("1", 1, 200), ("200", 200, 200), ("0", 0, 422), ("201", 201, 422)],
)
async def test_tc_wi_015_pagesize_boundaries(
    client: AsyncClient, label: str, page_size: int, expected: int
) -> None:
    """TC-WI-015（C-003）：pageSize 边界 1/200 通过、0/201 拒绝。"""
    profile = await setup_identity(client)
    response = await client.get(
        "/api/v1/work-items",
        params={
            "page": 1,
            "pageSize": page_size,
            "workspaceId": profile["workspaceId"],
        },
    )
    assert response.status_code == expected, f"pageSize={label}: {response.text}"


async def test_tc_wi_016_sla_total_zero_metrate_zero(client: AsyncClient) -> None:
    """TC-WI-016：仅 P3/CANCELLED 工作项时分组 metRate 为 0 不误报 overdue。"""
    profile = await setup_identity(client)
    ws = profile["workspaceId"]
    await create_work_item(client, ws, priority="P3", title="仅P3")
    response = await client.get(
        "/api/v1/work-items/sla-overview", params={"workspaceId": ws}
    )
    assert response.status_code == 200
    data = envelope(response)["data"]
    groups = {g["priority"]: g for g in data["groups"]}
    assert "P3" not in groups
    assert data["overall"]["total"] == 1
    for g in groups.values():
        if g["total"] == 0:
            assert g["metRate"] == 0


@pytest.mark.skip(
    reason="TC-WI-017：本地单 workspace 实现无法构造跨 workspace 工作项（用例 precondition 不可满足）"
)
async def test_tc_wi_017_cross_workspace_404(client: AsyncClient) -> None:
    """TC-WI-017：跨 workspace 访问返回 404（环境不可构造，skip）。"""


async def test_tc_wi_018_list_work_item_runs(client: AsyncClient) -> None:
    """TC-WI-018：查询工作项运行记录列表返回 200 信封。"""
    profile = await setup_identity(client)
    item = await create_work_item(client, profile["workspaceId"])
    response = await client.get(f"/api/v1/work-items/{item['id']}/runs")
    assert response.status_code == 200, response.text
    assert envelope(response)["data"] == []
    missing = await client.get(
        "/api/v1/work-items/00000000-0000-4000-8000-000000000000/runs"
    )
    assert missing.status_code == 200
    assert envelope(missing)["data"] == []  # 实现为宽松语义：不存在的工作项 runs 返回空列表


@pytest.mark.xfail(strict=True, reason="缺陷#4：契约要求 createWorkItem 必填 Idempotency-Key 并幂等，实现端点未声明该 header（planning.py:219 无 idempotency_key 参数），同键重放创建两条")
async def test_tc_wi_019_idempotent_create_same_id(client: AsyncClient) -> None:
    """TC-WI-019：同一幂等键重放工作项创建返回同一 id。"""
    profile = await setup_identity(client)
    headers = mutation_headers(client, "wi-idem-key-00000001")
    body = {
        **WORK_ITEM_BODY,
        "workspaceId": profile["workspaceId"],
        "title": "幂等重放",
    }
    first = await client.post("/api/v1/work-items", headers=headers, json=body)
    assert first.status_code == 201
    second = await client.post("/api/v1/work-items", headers=headers, json=body)
    assert second.status_code == 201, second.text
    assert envelope(second)["data"]["id"] == envelope(first)["data"]["id"]
    listed = await client.get(
        "/api/v1/work-items",
        params={"page": 1, "pageSize": 20, "workspaceId": profile["workspaceId"]},
    )
    assert envelope(listed)["total"] == 1


async def test_tc_err_003_concurrent_transition_exactly_one_wins(
    client: AsyncClient,
) -> None:
    """TC-ERR-003：两个并发同 lockVersion 流转恰好一个 200 一个 409。"""
    profile = await setup_identity(client)
    item = await create_work_item(client, profile["workspaceId"])
    body = {"targetStatus": "REWORK", "reason": "并发竞争", "lockVersion": 0}

    async def fire(key: str):
        return await client.post(
            f"/api/v1/work-items/{item['id']}/transitions",
            headers=mutation_headers(client, key),
            json=body,
        )

    r1, r2 = await asyncio.gather(
        fire("cc-key-a-00000000001"), fire("cc-key-b-00000000001")
    )
    statuses = sorted([r1.status_code, r2.status_code])
    assert statuses == [200, 409], f"并发结果异常: {statuses} {r1.text} {r2.text}"
    detail = await client.get(f"/api/v1/work-items/{item['id']}")
    assert envelope(detail)["data"]["lockVersion"] == 1
