"""TC-AUTH-001~010：认证链自动化执行。每个测试独立空库（conftest function 级隔离）。"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from conftest import TEST_PASSWORD, envelope, mutation_headers, setup_identity


async def test_tc_auth_001_first_setup_201(client: AsyncClient) -> None:
    """TC-AUTH-001：空库首次 setup 用 12 字符合规密码初始化成功。"""
    status = await client.get("/api/v1/auth/status")
    assert status.status_code == 200
    assert status.json()["data"]["setupRequired"] is True

    response = await client.post(
        "/api/v1/auth/setup",
        json={
            "email": "admin@api-suite.example",
            "password": "a-12-char-pw!!",
            "tenantName": "租户A",
            "workspaceName": "工作区A",
        },
    )
    assert response.status_code == 201, response.text
    data = envelope(response)["data"]
    assert data["email"] == "admin@api-suite.example"
    assert data["userId"]


async def test_tc_auth_002_login_200_issues_session(client: AsyncClient) -> None:
    """TC-AUTH-002：正确凭据登录返回 200 并签发会话。"""
    await setup_identity(client)
    response = await client.post(
        "/api/v1/auth/login", json={"email": "admin@api-suite.example", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    envelope(response)
    assert response.json()["data"]["userId"]


@pytest.mark.xfail(strict=True, reason="缺陷#1：契约 B14 裁决要求 actorType=HUMAN（LocalAuthProfile 枚举），实现返回 USER")
async def test_tc_auth_003_me_returns_profile(client: AsyncClient) -> None:
    """TC-AUTH-003：携带有效会话读取 /auth/me 档案。"""
    profile = await setup_identity(client)
    await client.post("/api/v1/auth/login", json={"email": "admin@api-suite.example", "password": TEST_PASSWORD})
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200, response.text
    data = envelope(response)["data"]
    assert data["email"] == profile["email"]
    assert data["actorType"] == "HUMAN"
    assert isinstance(data["capabilities"], list)


async def test_tc_auth_004_duplicate_setup_409(client: AsyncClient) -> None:
    """TC-AUTH-004：setup 完成后重复初始化返回 409 SETUP_ALREADY_COMPLETED。"""
    await setup_identity(client)
    response = await client.post(
        "/api/v1/auth/setup",
        json={
            "email": "another@api-suite.example",
            "password": "another-12char!",
            "tenantName": "t2",
            "workspaceName": "w2",
        },
    )
    assert response.status_code == 409, response.text
    assert envelope(response)["code"] == "SETUP_ALREADY_COMPLETED"
    # 未创建新身份：另一邮箱登录仍 401
    login = await client.post(
        "/api/v1/auth/login", json={"email": "another@api-suite.example", "password": "another-12char!"}
    )
    assert login.status_code == 401


async def test_tc_auth_005_wrong_password_401(client: AsyncClient) -> None:
    """TC-AUTH-005：错误密码登录返回 401 INVALID_CREDENTIALS。"""
    await setup_identity(client)
    response = await client.post(
        "/api/v1/auth/login", json={"email": "admin@api-suite.example", "password": "wrong-password-1"}
    )
    assert response.status_code == 401, response.text
    assert envelope(response)["code"] == "INVALID_CREDENTIALS"


async def test_tc_auth_006_rate_limit_429_after_5_failures(client: AsyncClient) -> None:
    """TC-AUTH-006：60 秒窗口内 5 次失败后第 6 次触发 429（C-006）。"""
    await setup_identity(client)
    for _ in range(5):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@api-suite.example", "password": "bad-password-01"},
        )
        assert r.status_code == 401
    sixth = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@api-suite.example", "password": TEST_PASSWORD},
    )
    assert sixth.status_code == 429, sixth.text
    assert envelope(sixth)["code"] == "RATE_LIMITED"


@pytest.mark.parametrize(
    ("label", "password", "expected"),
    [
        ("11-char", "12345678901", 422),
        ("12-char", "123456789012", 201),
        ("256-char", "x" * 256, 201),
        ("257-char", "x" * 257, 422),
    ],
)
async def test_tc_auth_007_password_boundaries(client: AsyncClient, label: str, password: str, expected: int) -> None:
    """TC-AUTH-007（C-002）：setup password 长度边界 11/12/256/257。"""
    response = await client.post(
        "/api/v1/auth/setup",
        json={"email": "admin@api-suite.example", "password": password, "tenantName": "t", "workspaceName": "w"},
    )
    assert response.status_code == expected, f"{label}: {response.text}"


async def test_tc_auth_008_anonymous_me_401(anon_client: AsyncClient) -> None:
    """TC-AUTH-008：无会话凭据访问 /auth/me 返回 401 且响应仍为统一信封。"""
    response = await anon_client.get("/api/v1/auth/me")
    assert response.status_code == 401, response.text
    assert envelope(response)["code"] == "UNAUTHORIZED"


async def test_tc_auth_009_logout_invalidates_session(client: AsyncClient) -> None:
    """TC-AUTH-009：logout 后原会话访问 /auth/me 返回 401。"""
    await setup_identity(client)
    await client.post("/api/v1/auth/login", json={"email": "admin@api-suite.example", "password": TEST_PASSWORD})
    out = await client.post("/api/v1/auth/logout", headers=mutation_headers(client))
    assert out.status_code == 200
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401


async def test_tc_auth_010_unknown_email_401(client: AsyncClient) -> None:
    """TC-AUTH-010：不存在的邮箱登录返回 401（与错误密码同码，不泄漏存在性）。"""
    response = await client.post(
        "/api/v1/auth/login", json={"email": "ghost@api-suite.example", "password": "whatever-12ch"}
    )
    assert response.status_code == 401
    assert envelope(response)["code"] == "INVALID_CREDENTIALS"


async def test_tc_auth_setup_name_boundary_rejected(client: AsyncClient) -> None:
    """R-AUTH-002 附加面：tenantName 超长（>120）返回 422。"""
    response = await client.post(
        "/api/v1/auth/setup",
        json={"email": "a@b.test", "password": "a-12-char-pw!!", "tenantName": "t" * 121, "workspaceName": "w"},
    )
    assert response.status_code == 422
