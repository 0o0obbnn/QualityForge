"""TC-ENV/TC-ERR/TC-VAL：全局契约自动化执行（信封/camelCase/幂等键边界/畸形输入/必填矩阵/401）。"""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient

from conftest import TEST_PASSWORD, envelope, mutation_headers, setup_identity

WORK_ITEM_BODY = {
    "workItemType": "GENERAL",
    "title": "契约用例",
    "objective": "o",
    "acceptanceCriteria": "a",
    "requiresReview": True,
    "priority": "P2",
    "riskLevel": "MEDIUM",
}


async def test_tc_env_001_envelope_on_success_and_error(client: AsyncClient) -> None:
    """TC-ENV-001：成功与错误响应均含 code/message/traceId。"""
    profile = await setup_identity(client)
    ok = await client.get(
        "/api/v1/work-items", params={"page": 1, "workspaceId": profile["workspaceId"]}
    )
    assert ok.status_code == 200
    envelope(ok)
    err = await client.get("/api/v1/work-items/00000000-0000-4000-8000-000000000000")
    assert err.status_code == 404
    envelope(err)


async def test_tc_env_002_camel_case_no_snake_leak(client: AsyncClient) -> None:
    """TC-ENV-002：工作项响应字段为 camelCase 无 snake_case 泄漏。"""
    profile = await setup_identity(client)
    response = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client, "env-wi-key-0000000001"),
        json={**WORK_ITEM_BODY, "workspaceId": profile["workspaceId"]},
    )
    assert response.status_code == 201, response.text
    data = envelope(response)["data"]
    snake_keys = [k for k in data if "_" in k]
    assert snake_keys == [], f"snake_case 泄漏: {snake_keys}"


@pytest.mark.parametrize(
    ("label", "key_len", "expected"),
    [
        pytest.param(
            "15",
            15,
            422,
            marks=pytest.mark.xfail(
                strict=True,
                reason="缺陷#4：createWorkItem 未声明 Idempotency-Key header，长度约束未实施",
            ),
        ),
        ("16", 16, 201),
        ("128", 128, 201),
        pytest.param(
            "129",
            129,
            422,
            marks=pytest.mark.xfail(
                strict=True,
                reason="缺陷#4：createWorkItem 未声明 Idempotency-Key header，长度约束未实施",
            ),
        ),
    ],
)
async def test_tc_err_002_idempotency_key_boundaries(
    client: AsyncClient, label: str, key_len: int, expected: int
) -> None:
    """TC-ERR-002（C-005）：Idempotency-Key 15/16/128/129 边界。"""
    profile = await setup_identity(client)
    response = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client, "k" * key_len),
        json={
            **WORK_ITEM_BODY,
            "workspaceId": profile["workspaceId"],
            "title": f"idm-{label}",
        },
    )
    assert response.status_code == expected, f"key len={label}: {response.text}"


async def test_tc_err_001_malformed_bodies_rejected(client: AsyncClient) -> None:
    """TC-ERR-001：空对象/畸形 JSON/纯文本 Content-Type 均被 4xx 拒绝。"""
    profile = await setup_identity(client)
    headers = mutation_headers(client, "err-mb-key-0000000001")
    empty = await client.post("/api/v1/work-items", headers=headers, json={})
    assert empty.status_code == 422, empty.text

    malformed = await client.post(
        "/api/v1/work-items",
        headers={**headers, "Content-Type": "application/json"},
        content=b"{not-json",
    )
    assert malformed.status_code in (400, 422), malformed.text

    plain = await client.post(
        "/api/v1/work-items",
        headers={**headers, "Content-Type": "text/plain"},
        content=b'{"title":"x"}',
    )
    assert plain.status_code in (400, 422), plain.text
    listed = await client.get(
        "/api/v1/work-items",
        params={"page": 1, "pageSize": 20, "workspaceId": profile["workspaceId"]},
    )
    assert envelope(listed)["total"] == 0


async def test_tc_err_004_special_chars_ok_10kb_rejected(client: AsyncClient) -> None:
    """TC-ERR-004（C-001）：title 含 emoji/引号/换行通过且读回一致，10KB 拒绝。"""
    profile = await setup_identity(client)
    weird = '标题🚀含"引号"与\n换行'
    ok = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client, "err-sc-key-0000000001"),
        json={**WORK_ITEM_BODY, "workspaceId": profile["workspaceId"], "title": weird},
    )
    assert ok.status_code == 201, ok.text
    assert envelope(ok)["data"]["title"] == weird

    huge = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client, "err-10k-key-000000001"),
        json={
            **WORK_ITEM_BODY,
            "workspaceId": profile["workspaceId"],
            "title": "x" * 10_000,
        },
    )
    assert huge.status_code == 422, huge.text


async def test_tc_val_002_invalid_enum_and_non_uuid_422(client: AsyncClient) -> None:
    """TC-VAL-002：非法枚举值与非 UUID 路径参数返回 422。"""
    profile = await setup_identity(client)
    bad_type = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client, "val-en-key-0000000001"),
        json={
            **WORK_ITEM_BODY,
            "workspaceId": profile["workspaceId"],
            "workItemType": "NOT_A_TYPE",
            "priority": "P9",
            "riskLevel": "EXTREME",
        },
    )
    assert bad_type.status_code == 422, bad_type.text

    non_uuid = await client.get("/api/v1/work-items/not-a-uuid")
    assert non_uuid.status_code == 422, non_uuid.text


async def test_tc_val_003_unknown_resource_ids_404(client: AsyncClient) -> None:
    """TC-VAL-003：未占用资源 ID 访问审核/报告路径端点返回 404。"""
    profile = await setup_identity(client)
    missing = "00000000-0000-4000-8000-000000000000"
    for method, path in (
        ("GET", f"/api/v1/review-tasks/{missing}"),
        ("GET", f"/api/v1/review-tasks/{missing}/artifact"),
        ("GET", f"/api/v1/quality/reports/{missing}/versions"),
    ):
        response = await client.get(path, params={"workspaceId": profile["workspaceId"]})
        assert response.status_code == 404, f"{path}: {response.text}"
        envelope(response)


async def test_tc_val_004_anonymous_write_401(anon_client: AsyncClient) -> None:
    """TC-VAL-004：无会话凭据调用核心写接口返回 401。"""
    wi = await anon_client.post(
        "/api/v1/work-items",
        headers={"Idempotency-Key": "anon-key-000000000001"},
        json={**WORK_ITEM_BODY, "workspaceId": "00000000-0000-4000-8000-000000000000"},
    )
    assert wi.status_code == 401, wi.text
    assert envelope(wi)["code"] == "UNAUTHORIZED"


async def test_tc_val_005_login_missing_fields_422(client: AsyncClient) -> None:
    """TC-VAL-005：登录空对象与缺失 password 均返回 422 且不消耗限流窗口。"""
    empty = await client.post("/api/v1/auth/login", json={})
    assert empty.status_code == 422, empty.text
    no_password = await client.post(
        "/api/v1/auth/login", json={"email": "admin@api-suite.example"}
    )
    assert no_password.status_code == 422

    await setup_identity(client)
    normal_fail = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@api-suite.example", "password": "bad-password-01"},
    )
    assert normal_fail.status_code == 401, "校验失败不应消耗限流窗口导致 429"
