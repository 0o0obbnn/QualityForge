"""M4 质量域纵向切片：结果分析 → 失败聚类（与 Defect 分离）→ Defect 立项/版本/批准
→ 外部同步（批准+回执，B2-4）→ 测试报告 → 覆盖率（effective 口径强制）→ 知识回流。

11 个 operation：createResultAnalysis / listFailureClusters / listDefects / createDefect /
createDefectVersion / createDefectSyncAttempt / listTestReports / createTestReport /
listCoverageReports / createCoverageReport / createKnowledgeEntry。
"""

from __future__ import annotations

import uuid
from typing import Any

from httpx import AsyncClient

from qf.services.planning_workflow import content_digest
from tests.test_planning_workflow import mutation_headers, setup_identity, start_session


def _data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


async def _bootstrap_execution(client: AsyncClient) -> dict[str, Any]:
    """身份 → 会话产出物 → 执行计划 → 执行 → 结果，作为质量域分析的事实来源。"""
    profile = await setup_identity(client)
    session = await start_session(client, profile)
    plans = _data(await client.get("/api/v1/test-plans", params={"workspaceId": profile["workspaceId"]}))
    plan = _data(
        await client.post(
            "/api/v1/execution-plans",
            headers=mutation_headers(client),
            json={
                "workspaceId": profile["workspaceId"],
                "planKey": "EXEC-M4-001",
                "name": "M4 质量域验证计划",
                "testPlanId": plans[0]["id"],
            },
        )
    )
    task = _data(
        await client.post(
            f"/api/v1/execution-plans/{plan['id']}/runs",
            headers=mutation_headers(client, idempotency_key="m4-exec-run-0000001"),
            json={"executionPlanVersionId": plan["currentVersionId"]},
        )
    )
    results = _data(await client.get("/api/v1/execution-results", params={"executionTaskId": task["id"]}))
    return {
        "profile": profile,
        "session": session,
        "workspace_id": profile["workspaceId"],
        "release_id": session["releaseId"],
        "work_item_id": session["workItemId"],
        "task": task,
        "results": results,
    }


def _defect_version_payload(release_id: str) -> dict[str, Any]:
    return {
        "title": "退款金额计算偏差",
        "description": "部分退款场景金额多扣 1 分",
        "expectedResult": "退款金额精确到分",
        "actualResult": "实际多扣 1 分",
        "severity": "HIGH",
        "priority": "P1",
        "defectType": "PRODUCT",
        "environmentSnapshotRef": "env:stage4-local",
        "affectedReleaseIds": [release_id],
        "evidence": [{"type": "LOG", "ref": "evidence:m4"}],
    }


async def test_quality_chain_analysis_to_knowledge(client: AsyncClient) -> None:
    ctx = await _bootstrap_execution(client)
    workspace_id, release_id = ctx["workspace_id"], ctx["release_id"]
    result_ids = [result["id"] for result in ctx["results"]]

    # 1) 结果分析：引用全部执行结果，结论摘要服务端计算
    analysis = _data(
        await client.post(
            "/api/v1/quality/result-analyses",
            headers=mutation_headers(client),
            json={
                "workspaceId": workspace_id,
                "releaseId": release_id,
                "analysisKey": "RA-M4-001",
                "executionResultRefs": result_ids,
            },
        )
    )
    assert analysis["status"] == "ACTIVE"
    assert len(analysis["contentDigest"]) == 64
    assert analysis["conclusionRef"]

    # 2) 失败聚类：与 Defect 分离的独立集合，成员数与失败结果一一对应
    clusters = _data(await client.get("/api/v1/quality/failure-clusters", params={"workspaceId": workspace_id}))
    failed_count = sum(1 for result in ctx["results"] if result["status"] in {"FAILED", "ERROR"})
    assert sum(cluster["memberCount"] for cluster in clusters) == failed_count
    assert all(cluster["clusterKey"] for cluster in clusters)

    # 3) 立 Defect（createdFromWorkItemId 必须存在）+ 首版缺陷版本
    defect = _data(
        await client.post(
            "/api/v1/quality/defects",
            headers=mutation_headers(client),
            json={
                "workspaceId": workspace_id,
                "releaseId": release_id,
                "defectKey": "DEF-M4-001",
                "createdFromWorkItemId": ctx["work_item_id"],
            },
        )
    )
    assert defect["lifecycleStatus"] == "NEW"
    defects = _data(await client.get("/api/v1/quality/defects", params={"workspaceId": workspace_id}))
    assert any(item["id"] == defect["id"] for item in defects)

    version = _data(
        await client.post(
            f"/api/v1/quality/defects/{defect['id']}/versions",
            headers=mutation_headers(client),
            json=_defect_version_payload(release_id),
        )
    )
    assert version["version"] == 1 and version["reviewStatus"] == "PENDING_REVIEW"

    # 4) 缺陷版本人工批准（DEFECT_VERSION 审核任务自动创建）
    tasks = _data(
        await client.get(
            "/api/v1/review-tasks",
            params={"workspaceId": workspace_id, "status": "OPEN"},
        )
    )
    defect_task = next(t for t in tasks if t["artifactType"] == "DEFECT_VERSION")
    assert defect_task["artifactVersionId"] == version["id"]
    approved = _data(
        await client.post(
            f"/api/v1/review-tasks/{defect_task['id']}/decisions",
            headers=mutation_headers(client, idempotency_key=f"m4-defect-{defect_task['id']}"),
            json={"decision": "APPROVE", "contentDigest": defect_task["contentDigest"]},
        )
    )
    assert approved["status"] == "APPROVED"
    approved_root = next(
        item for item in _data(await client.get("/api/v1/quality/defects", params={"workspaceId": workspace_id}))
        if item["id"] == defect["id"]
    )
    assert approved_root["approvedVersionId"] == version["id"]

    # 5) 外部同步（B2-4）：批准后提交，payload 摘要服务端重算，回执即 attempt 记录
    sync_payload = {"title": "外部系统缺陷标题", "body": "同步正文"}
    attempt = _data(
        await client.post(
            f"/api/v1/quality/defects/{defect['id']}/sync-attempts",
            headers=mutation_headers(client, idempotency_key="m4-sync-000000000001"),
            json={
                "defectVersionId": version["id"],
                "integrationId": str(uuid.uuid4()),
                "operation": "CREATE",
                "payloadDigest": content_digest(sync_payload),
                "approvalId": defect_task["id"],
                "payload": sync_payload,
            },
        )
    )
    assert attempt["status"] == "ACKNOWLEDGED"
    assert len(attempt["receiptDigest"]) == 64
    assert "payload" not in attempt  # writeOnly 字段不得回显
    replayed = _data(
        await client.post(
            f"/api/v1/quality/defects/{defect['id']}/sync-attempts",
            headers=mutation_headers(client, idempotency_key="m4-sync-000000000001"),
            json={
                "defectVersionId": version["id"],
                "integrationId": attempt["integrationId"],
                "operation": "CREATE",
                "payloadDigest": content_digest(sync_payload),
                "approvalId": defect_task["id"],
                "payload": sync_payload,
            },
        )
    )
    assert replayed["id"] == attempt["id"]

    # 6) 测试报告：根层仅身份与指针（P0-1 下沉），版本层承载快照引用 + 完整审核链
    report = _data(
        await client.post(
            "/api/v1/quality/reports",
            headers=mutation_headers(client),
            json={
                "workspaceId": workspace_id,
                "releaseId": release_id,
                "reportKey": "RPT-M4-001",
            },
        )
    )
    assert report["status"] == "ACTIVE"
    assert report["currentVersionId"] is None and report["publishedVersionId"] is None
    assert "scopeSnapshotRef" not in report  # 根层字段已下沉版本层
    reports = _data(
        await client.get("/api/v1/quality/reports", params={"workspaceId": workspace_id, "releaseId": release_id})
    )
    assert any(item["id"] == report["id"] for item in reports)

    # 6.1) 报告版本（TEST_REPORT_VERSION 审核任务自动创建，批准前根指针维持 None）
    report_version = _data(
        await client.post(
            f"/api/v1/quality/reports/{report['id']}/versions",
            headers=mutation_headers(client),
            json={
                "scopeSnapshotRef": "scope:m4-v1",
                "executionSnapshotRef": f"exec:{ctx['task']['id']}",
                "qualityConclusion": "M4 质量结论：准入达标，遗留风险已登记",
                "changeSummary": "首版报告：执行结果 + 覆盖率 + 缺陷收敛",
            },
        )
    )
    assert report_version["version"] == 1 and report_version["reviewStatus"] == "PENDING_REVIEW"
    assert report_version["supersedesVersionId"] is None
    assert len(report_version["contentDigest"]) == 64

    # 6.2) 审核任务出现 → APPROVE → 根 currentVersionId 回填 + 版本 reviewStatus APPROVED
    report_task = next(
        t
        for t in _data(
            await client.get("/api/v1/review-tasks", params={"workspaceId": workspace_id, "status": "OPEN"})
        )
        if t["artifactType"] == "TEST_REPORT_VERSION"
    )
    assert report_task["artifactVersionId"] == report_version["id"]
    decided = _data(
        await client.post(
            f"/api/v1/review-tasks/{report_task['id']}/decisions",
            headers=mutation_headers(client, idempotency_key=f"m4-report-{report_task['id']}"),
            json={"decision": "APPROVE", "contentDigest": report_task["contentDigest"]},
        )
    )
    assert decided["status"] == "APPROVED"
    approved_report = next(
        item
        for item in _data(await client.get("/api/v1/quality/reports", params={"workspaceId": workspace_id}))
        if item["id"] == report["id"]
    )
    assert approved_report["currentVersionId"] == report_version["id"]
    # 签署（publishedVersionId/REPORT_SIGNOFF）归后续切片，维持 None
    assert approved_report["publishedVersionId"] is None
    approved_version = next(
        item
        for item in _data(
            await client.get(
                f"/api/v1/quality/reports/{report['id']}/versions", params={"workspaceId": workspace_id}
            )
        )
        if item["id"] == report_version["id"]
    )
    assert approved_version["reviewStatus"] == "APPROVED"

    # 6.3) 陈旧/越界 testReportId 一律 404
    stale = await client.post(
        f"/api/v1/quality/reports/{uuid.uuid4()}/versions",
        headers=mutation_headers(client),
        json={
            "scopeSnapshotRef": "scope:x",
            "executionSnapshotRef": "exec:x",
            "qualityConclusion": "x",
            "changeSummary": "x",
        },
    )
    assert stale.status_code == 404, stale.text
    stale_list = await client.get(
        f"/api/v1/quality/reports/{uuid.uuid4()}/versions", params={"workspaceId": workspace_id}
    )
    assert stale_list.status_code == 404, stale_list.text

    # 7) 覆盖率：EFFECTIVE 口径必须显式提供 ruleDimension，verdict 服务端计算
    coverage = _data(
        await client.post(
            "/api/v1/quality/coverage-reports",
            headers=mutation_headers(client),
            json={
                "workspaceId": workspace_id,
                "releaseId": release_id,
                "denominatorDefinitionRef": "EFFECTIVE",
                "scopeSnapshotRef": "scope:m4-v1",
                "ruleDimension": {"covered": 8, "total": 10},
            },
        )
    )
    assert coverage["verdict"] in {"SATISFIED", "PARTIAL", "INSUFFICIENT"}
    assert len(coverage["contentDigest"]) == 64
    coverages = _data(
        await client.get("/api/v1/quality/coverage-reports", params={"workspaceId": workspace_id})
    )
    assert any(item["id"] == coverage["id"] for item in coverages)

    # 8) 知识回流
    entry = _data(
        await client.post(
            "/api/v1/knowledge/entries",
            headers=mutation_headers(client),
            json={"workspaceId": workspace_id, "knowledgeKey": "KB-M4-001", "category": "FAILURE_PATTERN"},
        )
    )
    assert entry["knowledgeKey"] == "KB-M4-001" and entry["category"] == "FAILURE_PATTERN"


async def test_sync_attempt_requires_approved_review(client: AsyncClient) -> None:
    """B2-4：无批准/批准未通过的外部同步一律 403。"""
    ctx = await _bootstrap_execution(client)
    defect = _data(
        await client.post(
            "/api/v1/quality/defects",
            headers=mutation_headers(client),
            json={
                "workspaceId": ctx["workspace_id"],
                "releaseId": ctx["release_id"],
                "defectKey": "DEF-M4-403",
                "createdFromWorkItemId": ctx["work_item_id"],
            },
        )
    )
    version = _data(
        await client.post(
            f"/api/v1/quality/defects/{defect['id']}/versions",
            headers=mutation_headers(client),
            json=_defect_version_payload(ctx["release_id"]),
        )
    )
    tasks = _data(
        await client.get(
            "/api/v1/review-tasks", params={"workspaceId": ctx["workspace_id"], "status": "OPEN"}
        )
    )
    open_task = next(t for t in tasks if t["artifactType"] == "DEFECT_VERSION")
    body = {
        "defectVersionId": version["id"],
        "integrationId": str(uuid.uuid4()),
        "operation": "CREATE",
        "payloadDigest": content_digest({"a": 1}),
        "payload": {"a": 1},
    }
    # 未批准的审核任务 → 403
    denied = await client.post(
        f"/api/v1/quality/defects/{defect['id']}/sync-attempts",
        headers=mutation_headers(client, idempotency_key="m4-sync-403-000000001"),
        json={**body, "approvalId": open_task["id"]},
    )
    assert denied.status_code == 403, denied.text
    # 不存在的批准引用 → 403
    missing = await client.post(
        f"/api/v1/quality/defects/{defect['id']}/sync-attempts",
        headers=mutation_headers(client, idempotency_key="m4-sync-403-000000002"),
        json={**body, "approvalId": str(uuid.uuid4())},
    )
    assert missing.status_code == 403, missing.text


async def test_sync_attempt_rejects_forged_payload_digest(client: AsyncClient) -> None:
    """payloadDigest 由服务端对 payload 重算校验，伪造摘要 422。"""
    ctx = await _bootstrap_execution(client)
    defect = _data(
        await client.post(
            "/api/v1/quality/defects",
            headers=mutation_headers(client),
            json={
                "workspaceId": ctx["workspace_id"],
                "releaseId": ctx["release_id"],
                "defectKey": "DEF-M4-422",
                "createdFromWorkItemId": ctx["work_item_id"],
            },
        )
    )
    version = _data(
        await client.post(
            f"/api/v1/quality/defects/{defect['id']}/versions",
            headers=mutation_headers(client),
            json=_defect_version_payload(ctx["release_id"]),
        )
    )
    tasks = _data(
        await client.get(
            "/api/v1/review-tasks", params={"workspaceId": ctx["workspace_id"], "status": "OPEN"}
        )
    )
    defect_task = next(t for t in tasks if t["artifactType"] == "DEFECT_VERSION")
    _data(
        await client.post(
            f"/api/v1/review-tasks/{defect_task['id']}/decisions",
            headers=mutation_headers(client, idempotency_key=f"m4-defect422-{defect_task['id']}"),
            json={"decision": "APPROVE", "contentDigest": defect_task["contentDigest"]},
        )
    )
    forged = await client.post(
        f"/api/v1/quality/defects/{defect['id']}/sync-attempts",
        headers=mutation_headers(client, idempotency_key="m4-sync-422-000000001"),
        json={
            "defectVersionId": version["id"],
            "integrationId": str(uuid.uuid4()),
            "operation": "CREATE",
            "payloadDigest": "0" * 64,
            "approvalId": defect_task["id"],
            "payload": {"title": "真实正文"},
        },
    )
    assert forged.status_code == 422, forged.text


async def test_coverage_dimensions_are_mandatory_and_effective_requires_rule(client: AsyncClient) -> None:
    """覆盖率强制 effective 口径：维度不得推导，EFFECTIVE 必须提供 ruleDimension。"""
    profile = await setup_identity(client)
    workspace_id = profile["workspaceId"]
    release_id = str(uuid.uuid4())
    base = {"workspaceId": workspace_id, "releaseId": release_id, "scopeSnapshotRef": "scope:v1"}

    no_dimension = await client.post(
        "/api/v1/quality/coverage-reports",
        headers=mutation_headers(client),
        json={**base, "denominatorDefinitionRef": "EFFECTIVE"},
    )
    assert no_dimension.status_code == 422, no_dimension.text

    effective_without_rule = await client.post(
        "/api/v1/quality/coverage-reports",
        headers=mutation_headers(client),
        json={**base, "denominatorDefinitionRef": "EFFECTIVE", "scenarioDimension": {"covered": 1, "total": 1}},
    )
    assert effective_without_rule.status_code == 422, effective_without_rule.text

    instance_ok = _data(
        await client.post(
            "/api/v1/quality/coverage-reports",
            headers=mutation_headers(client),
            json={**base, "denominatorDefinitionRef": "INSTANCE", "apiDimension": {"covered": 3, "total": 3}},
        )
    )
    assert instance_ok["verdict"] == "SATISFIED"


async def test_result_analysis_requires_existing_execution_results(client: AsyncClient) -> None:
    ctx = await _bootstrap_execution(client)
    response = await client.post(
        "/api/v1/quality/result-analyses",
        headers=mutation_headers(client),
        json={
            "workspaceId": ctx["workspace_id"],
            "releaseId": ctx["release_id"],
            "analysisKey": "RA-M4-404",
            "executionResultRefs": [str(uuid.uuid4())],
        },
    )
    assert response.status_code == 404, response.text


async def test_defect_requires_existing_work_item(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    response = await client.post(
        "/api/v1/quality/defects",
        headers=mutation_headers(client),
        json={
            "workspaceId": profile["workspaceId"],
            "releaseId": str(uuid.uuid4()),
            "defectKey": "DEF-M4-NOTFOUND",
            "createdFromWorkItemId": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 404, response.text
