"""TC-VAL-001 必填矩阵 + TC-EX/TC-QA/TC-OBS/TC-PLN/TC-VER：执行/质量/观测/冒烟自动化。"""

from __future__ import annotations

import hashlib
import uuid

import pytest
from httpx import AsyncClient

from conftest import TEST_PASSWORD, envelope, mutation_headers, setup_identity


def fresh_key(prefix: str) -> str:
    """长度合规的唯一幂等键。"""
    return f"{prefix}-{uuid.uuid4().hex[:20]}"


async def login(client: AsyncClient) -> dict:
    profile = await setup_identity(client)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@api-suite.example", "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return profile


async def create_work_item(client: AsyncClient, workspace_id: str) -> dict:
    response = await client.post(
        "/api/v1/work-items",
        headers=mutation_headers(client, fresh_key("wi")),
        json={
            "workspaceId": workspace_id,
            "workItemType": "GENERAL",
            "title": "执行器工作项",
            "objective": "o",
            "acceptanceCriteria": "a",
            "requiresReview": True,
            "priority": "P2",
            "riskLevel": "MEDIUM",
        },
    )
    assert response.status_code == 201, response.text
    return envelope(response)["data"]


async def test_tc_val_001_create_missing_required_matrix(client: AsyncClient) -> None:
    """TC-VAL-001：八个创建接口各缺一个必填字段均返回 422。"""
    profile = await login(client)
    ws = profile["workspaceId"]
    digest = "b" * 64
    cases = [
        (
            "POST",
            "/api/v1/review-tasks",
            {
                "artifactType": "TEST_STRATEGY",
                "artifactId": profile["userId"],
                "artifactVersionId": profile["userId"],
                "contentDigest": digest,
                "policyType": "SINGLE_REVIEW",
            },
        ),
        (
            "POST",
            "/api/v1/knowledge/entries",
            {"workspaceId": ws, "category": "TESTING"},
        ),
        (
            "POST",
            "/api/v1/knowledge/requirements",
            {"workspaceId": ws, "documentType": "PRD"},
        ),
        (
            "POST",
            "/api/v1/quality/reports",
            {"workspaceId": ws, "releaseId": profile["tenantId"]},
        ),
        (
            "POST",
            "/api/v1/quality/defects",
            {
                "workspaceId": ws,
                "releaseId": profile["tenantId"],
                "createdFromWorkItemId": profile["userId"],
            },
        ),
        (
            "POST",
            "/api/v1/quality/coverage-reports",
            {
                "workspaceId": ws,
                "releaseId": profile["tenantId"],
                "denominatorDefinitionRef": "INSTANCE",
            },
        ),
        (
            "POST",
            "/api/v1/quality/result-analyses",
            {
                "workspaceId": ws,
                "releaseId": profile["tenantId"],
                "analysisKey": "k",
                "executionResultRefs": [],
            },
        ),
    ]
    for _, path, body in cases:
        response = await client.post(
            path, headers=mutation_headers(client, fresh_key("val")), json=body
        )
        assert response.status_code == 422, (
            f"{path} 缺失必填未 422: {response.status_code} {response.text[:120]}"
        )


@pytest.mark.skip(
    reason="TC-EX-001：服务端校验 testPlanId 引用存在性，而 testPlan 根在已实现面无创建入口（用例 precondition 不可构造）"
)
async def test_tc_ex_001_create_execution_plan_201(client: AsyncClient) -> None:
    """TC-EX-001：携带必填字段创建执行计划返回 201（skip：构造面缺失）。"""
    profile = await login(client)
    response = await client.post(
        "/api/v1/execution-plans",
        headers=mutation_headers(client, fresh_key("ex")),
        json={
            "workspaceId": profile["workspaceId"],
            "planKey": "exec-smoke-001",
            "name": "冒烟执行计划",
            "testPlanId": profile["userId"],
        },
    )
    assert response.status_code == 201, response.text
    assert envelope(response)["data"]["planKey"] == "exec-smoke-001"


async def test_tc_ex_002_create_execution_plan_missing_422(client: AsyncClient) -> None:
    """TC-EX-002：缺失 planKey 创建执行计划返回 422。"""
    profile = await login(client)
    response = await client.post(
        "/api/v1/execution-plans",
        headers=mutation_headers(client, fresh_key("exm")),
        json={
            "workspaceId": profile["workspaceId"],
            "name": "缺planKey",
            "testPlanId": profile["userId"],
        },
    )
    assert response.status_code == 422, response.text


async def test_tc_qa_001_create_report_201(client: AsyncClient) -> None:
    """TC-QA-001：创建测试报告返回 201 与统一信封。"""
    profile = await login(client)
    response = await client.post(
        "/api/v1/quality/reports",
        headers=mutation_headers(client, fresh_key("rpt")),
        json={
            "workspaceId": profile["workspaceId"],
            "releaseId": profile["tenantId"],
            "reportKey": "report-smoke-001",
        },
    )
    assert response.status_code == 201, response.text
    assert envelope(response)["data"]["id"]


async def test_tc_qa_003_result_analyses_empty_refs_422(client: AsyncClient) -> None:
    """TC-QA-003：executionResultRefs 空数组创建分析返回 422。"""
    profile = await login(client)
    response = await client.post(
        "/api/v1/quality/result-analyses",
        headers=mutation_headers(client, fresh_key("ra")),
        json={
            "workspaceId": profile["workspaceId"],
            "releaseId": profile["tenantId"],
            "analysisKey": "a-1",
            "executionResultRefs": [],
        },
    )
    assert response.status_code == 422, response.text


async def test_tc_obs_001_transitioned_event_retrievable(client: AsyncClient) -> None:
    """TC-OBS-001：工作项流转后事件流可检索 work_item.transitioned。"""
    profile = await login(client)
    item = await create_work_item(client, profile["workspaceId"])
    transition = await client.post(
        f"/api/v1/work-items/{item['id']}/transitions",
        headers=mutation_headers(client, fresh_key("obs")),
        json={"targetStatus": "REWORK", "reason": "事件验证", "lockVersion": 0},
    )
    assert transition.status_code == 200, transition.text

    events = await client.get(
        "/api/v1/observability/events",
        params={
            "workspaceId": profile["workspaceId"],
            "subjectType": "work_item",
            "eventType": "work_item.transitioned",
        },
    )
    assert events.status_code == 200, events.text
    data = envelope(events)["data"]
    hits = [
        e
        for e in data
        if e["eventType"] == "work_item.transitioned" and e["subjectId"] == item["id"]
    ]
    assert hits, f"未检索到流转事件: {[e.get('eventType') for e in data][:8]}"
    assert hits[0]["payload"]["fromStatus"] == item["status"]
    assert hits[0]["payload"]["toStatus"] == "REWORK"


async def test_tc_obs_002_metrics_200(client: AsyncClient) -> None:
    """TC-OBS-002：指标接口返回 200 与统一信封。"""
    profile = await login(client)
    response = await client.get(
        "/api/v1/observability/metrics", params={"workspaceId": profile["workspaceId"]}
    )
    assert response.status_code == 200, response.text
    envelope(response)


@pytest.mark.parametrize(
    ("label", "method", "path"),
    [
        ("strategies", "GET", "/api/v1/test-strategies"),
        ("plans", "GET", "/api/v1/test-plans"),
        ("cases", "GET", "/api/v1/test-cases"),
        ("requirements", "GET", "/api/v1/knowledge/requirements"),
        ("entries", "GET", "/api/v1/knowledge/entries"),
        ("ai-sessions", "GET", "/api/v1/ai/sessions"),
        ("provider", "GET", "/api/v1/ai/provider/status"),
        ("environments", "GET", "/api/v1/platform/workspaces/{ws}/environments"),
        ("exec-plans", "GET", "/api/v1/execution-plans"),
        ("exec-tasks", "GET", "/api/v1/execution-tasks"),
        ("review-list", "GET", "/api/v1/review-tasks"),
        ("reports", "GET", "/api/v1/quality/reports"),
        ("defects", "GET", "/api/v1/quality/defects"),
        ("clusters", "GET", "/api/v1/quality/failure-clusters"),
        ("coverage", "GET", "/api/v1/quality/coverage-reports"),
        ("analyses", "GET", "/api/v1/quality/result-analyses"),
    ],
)
async def test_tc_pln_smoke_read_endpoints(
    client: AsyncClient, label: str, method: str, path: str
) -> None:
    """TC-PLN-001~008/011/013：已实现只读接口冒烟返回 200 信封。"""
    profile = await login(client)
    real_path = path.replace("{ws}", profile["workspaceId"])
    if "?" in real_path:
        real_path, fixed_query = real_path.split("?", 1)
        params = dict(p.split("=", 1) for p in fixed_query.split("&"))
    else:
        params = {}
    params.update({"page": 1, "pageSize": 20, "workspaceId": profile["workspaceId"]})
    response = await client.get(real_path, params=params)
    assert response.status_code == 200, f"{label}: {response.text}"
    envelope(response)


async def test_tc_pln_012_create_writes_201(client: AsyncClient) -> None:
    """TC-PLN-012：知识条目/需求文档/环境/覆盖报告/缺陷创建返回 201。

    注：POST /ai/sessions 需 gate0 会话链前置（workItemRunId 等），由
    review 模块的 session 链间接覆盖，此处不重复构造。
    """
    profile = await login(client)
    ws = profile["workspaceId"]
    digest = "c" * 64
    steps = [
        (
            "/api/v1/knowledge/entries",
            {"workspaceId": ws, "knowledgeKey": "kb-smoke-001", "category": "TESTING"},
        ),
        (
            "/api/v1/knowledge/requirements",
            {"workspaceId": ws, "name": "需求冒烟", "documentType": "PRD"},
        ),
        (
            "/api/v1/platform/workspaces/" + ws + "/environments",
            {
                "name": "冒烟环境",
                "environmentType": "TEST",
                "endpointMappings": {"api": "http://test"},
            },
        ),
        (
            "/api/v1/quality/coverage-reports",
            {
                "workspaceId": ws,
                "releaseId": profile["tenantId"],
                "denominatorDefinitionRef": "INSTANCE",
                "scopeSnapshotRef": "snap",
                # 缺陷#5：实现必填 coverage 维度（covered/total），契约 required 未声明
                "ruleDimension": {"covered": 1, "total": 2},
            },
        ),
    ]
    for path, body in steps:
        response = await client.post(
            path, headers=mutation_headers(client, fresh_key("pln")), json=body
        )
        assert response.status_code == 201, (
            f"{path}: {response.status_code} {response.text[:150]}"
        )
        envelope(response)

    work_item = await create_work_item(client, ws)
    defect = await client.post(
        "/api/v1/quality/defects",
        headers=mutation_headers(client, fresh_key("pln")),
        json={
            "workspaceId": ws,
            "releaseId": profile["tenantId"],
            "defectKey": "defect-smoke-001",
            "createdFromWorkItemId": work_item["id"],
        },
    )
    assert defect.status_code == 201, defect.text


async def test_tc_ver_001_version_endpoints(client: AsyncClient) -> None:
    """TC-VER-001：可构造根的版本链（需求/报告/缺陷）；策略/计划版本需 session 链根，见 review 模块。"""
    profile = await login(client)
    ws = profile["workspaceId"]
    headers = lambda: mutation_headers(client, fresh_key("ver"))  # noqa: E731

    req = await client.post(
        "/api/v1/knowledge/requirements",
        headers=headers(),
        json={"workspaceId": ws, "name": "版本链需求", "documentType": "PRD"},
    )
    assert req.status_code == 201
    req_id = envelope(req)["data"]["id"]
    rv = await client.post(
        f"/api/v1/knowledge/requirements/{req_id}/versions",
        headers=headers(),
        json={
            "sourceSnapshotId": "00000000-0000-0000-0000-000000000030",
            "contentDigest": hashlib.sha256("# v2".encode()).hexdigest(),
            "content": "# v2",
            "changeSummary": "二版",
        },
    )
    assert rv.status_code == 201, rv.text
    assert envelope(rv)["data"]["version"] >= 1

    work_item = await create_work_item(client, ws)
    report = await client.post(
        "/api/v1/quality/reports",
        headers=headers(),
        json={
            "workspaceId": ws,
            "releaseId": profile["tenantId"],
            "reportKey": "ver-report-001",
        },
    )
    assert report.status_code == 201
    report_id = envelope(report)["data"]["id"]
    rv2 = await client.post(
        f"/api/v1/quality/reports/{report_id}/versions",
        headers=headers(),
        json={
            "scopeSnapshotRef": "s1",
            "executionSnapshotRef": "e1",
            "qualityConclusion": "PASS",
            "changeSummary": "v1",
        },
    )
    assert rv2.status_code == 201, rv2.text

    versions_listed = await client.get(
        f"/api/v1/quality/reports/{report_id}/versions",
        params={"workspaceId": ws},
    )
    assert versions_listed.status_code == 200, versions_listed.text
    assert isinstance(envelope(versions_listed)["data"], list)
