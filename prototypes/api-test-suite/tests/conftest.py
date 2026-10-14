"""api-test-suite 执行器基座。

复用 backend/tests/conftest.py 的隔离模式：function 级独立 SQLite + in-process
ASGI client（无端口、无进程管理）。每个测试天然空库，使初始化态用例
（首次 setup 201、重复 setup 409）无需多实例编排。

配置全部来自环境变量（api-test-generator 契约：禁止硬编码 URL/密钥）：
- QF_TEST_PASSWORD：测试管理员密码（默认仅为本仓库本地测试占位）
"""

from __future__ import annotations

import os
import sys
import uuid
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
for _entry in (_BACKEND, _BACKEND / "src"):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from qf.main import app  # noqa: E402
from qf.services.auth_service import auth_service  # noqa: E402
from qf.services.planning_workflow import planning_workflow_service  # noqa: E402

CSRF_COOKIE = "qf_csrf"
TEST_PASSWORD = os.environ.get("QF_TEST_PASSWORD", "Local-review-password-2026")


@pytest.fixture(autouse=True)
def sqlite_path(tmp_path: Path) -> Generator[Path, None, None]:
    path = tmp_path / "api-suite.sqlite3"
    planning_workflow_service.reconfigure(str(path))
    auth_service.reconfigure(str(path))
    planning_workflow_service.reset()
    auth_service.reset_for_tests()
    yield path


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as api_client:
        yield api_client


@pytest.fixture
async def anon_client() -> AsyncGenerator[AsyncClient, None]:
    """无任何凭据的客户端（未认证路径用例）。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as api_client:
        yield api_client


async def setup_identity(client: AsyncClient, email: str = "admin@api-suite.example") -> dict:
    """空库初始化管理员并返回 profile；会话 cookie 落在 client 上。"""
    response = await client.post(
        "/api/v1/auth/setup",
        json={
            "email": email,
            "password": TEST_PASSWORD,
            "tenantName": "接口测试租户",
            "workspaceName": "接口测试工作区",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def mutation_headers(client: AsyncClient, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {"X-CSRF-Token": client.cookies[CSRF_COOKIE]}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def envelope(response) -> dict:
    """统一信封断言（R-ENV-001）：code/message/traceId 必填。"""
    body = response.json()
    for key in ("code", "message", "traceId"):
        assert key in body and body[key] is not None, f"信封缺 {key}: {body}"
    return body


def data_of(response) -> dict:
    return envelope(response)["data"]


SOURCE_SNAPSHOT_ID = "00000000-0000-0000-0000-000000000030"


async def gate0_session(client: AsyncClient, profile: dict) -> dict:
    """自包含 gate0 会话链：需求文档→版本→/ai/sessions，返回会话数据。

    backend/tests 的同名链不可 import（tests 包同名冲突），此处等价实现。
    """
    import hashlib

    ws = profile["workspaceId"]
    requirement = await client.post(
        "/api/v1/knowledge/requirements",
        headers=mutation_headers(client, f"gate0-{uuid.uuid4().hex[:16]}"),
        json={"workspaceId": ws, "name": "执行器需求", "documentType": "PRD"},
    )
    assert requirement.status_code == 201, requirement.text
    requirement_id = data_of(requirement)["id"]

    content = "# 执行器需求\n接口测试自动化链路。"
    version = await client.post(
        f"/api/v1/knowledge/requirements/{requirement_id}/versions",
        headers=mutation_headers(client, f"gate0-{uuid.uuid4().hex[:16]}"),
        json={
            "sourceSnapshotId": SOURCE_SNAPSHOT_ID,
            "contentDigest": hashlib.sha256(content.encode()).hexdigest(),
            "content": content,
            "changeSummary": "首版",
        },
    )
    assert version.status_code == 201, version.text
    version_id = data_of(version)["id"]

    releases = await client.get(f"/api/v1/workspaces/{ws}/releases")
    assert releases.status_code == 200, releases.text
    release_id = envelope(releases)["data"][0]["id"]  # 认证种子 ACTIVE Release（WP-01A 归属门）

    work_item = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client, f"gate0-{uuid.uuid4().hex[:16]}"),
        json={
            "workspaceId": ws,
            "releaseId": release_id,
            "workItemType": "STRATEGY",
            "title": "执行器策略工作项",
            "objective": "o",
            "acceptanceCriteria": "a",
            "requiresReview": True,
            "priority": "P2",
            "riskLevel": "MEDIUM",
        },
    )
    assert work_item.status_code == 201, work_item.text
    work_item_id = data_of(work_item)["id"]

    # 批次五十七批准门前置：工作项需先走 任务卡→AgentPlan→人工批准 链（QF-PD-003 计划先确认）
    nonce = uuid.uuid4().hex[:16]
    card = await client.post(
        f"/api/v1/work-items/{work_item_id}/task-cards",
        headers=mutation_headers(client, f"gate0-card-{nonce}"),
        json={
            "objective": "执行器任务卡",
            "scope": "接口测试自动化链路",
            "acceptanceCriteria": "会话可启动",
            "constraints": "无",
            "requestedPermissions": [],
            "budget": {},
        },
    )
    assert card.status_code == 201, card.text
    plan = await client.post(
        f"/api/v1/work-items/{work_item_id}/agent-plans",
        headers=mutation_headers(client, f"gate0-plan-{nonce}"),
        json={
            "taskCardId": data_of(card)["id"],
            "steps": [{"stepKey": "run", "agentRole": "coordinator", "description": "执行器步骤"}],
        },
    )
    assert plan.status_code == 201, plan.text
    decision = await client.post(
        f"/api/v1/agent-plans/{data_of(plan)['id']}/decisions",
        headers=mutation_headers(client, f"gate0-decide-{nonce}"),
        json={
            "decision": "APPROVE",
            "expectedContentDigest": data_of(plan)["contentDigest"],
            "reason": "执行器链批准",
        },
    )
    assert decision.status_code == 201, decision.text

    session = await client.post(
        "/api/v1/ai/sessions",
        headers=mutation_headers(client, f"gate0-{nonce}"),
        json={
            "workspaceId": ws,
            "workItemId": work_item_id,
            "workflowKey": "gate0-planning-slice",
            "requirementVersionId": version_id,
            "releaseId": release_id,
            "ownerId": profile["userId"],
        },
    )
    assert session.status_code == 202, session.text
    return data_of(session)
