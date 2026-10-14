"""Happy-path contract alignment for all implemented operations (M1-B0 起，M2 扩展)。

一条完整业务链依序调用全部已实现 operation：
断言每个端点返回契约成功状态码与 data 信封，并核对覆盖集与
test_openapi_contract.EXPECTED_IMPLEMENTED_OPERATION_IDS 完全一致——
实现集扩缩时本测试强制同步。
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from qf.services.planning_workflow import content_digest, planning_workflow_service
from tests.test_openapi_contract import EXPECTED_IMPLEMENTED_OPERATION_IDS
from tests.test_planning_workflow import (
    LOCAL_PASSWORD,
    SOURCE_SNAPSHOT_ID,
    mutation_headers,
)


@pytest.fixture
def observed() -> dict[str, int]:
    return {}


async def test_all_implemented_operations_have_green_happy_path(client: AsyncClient, observed: dict[str, int]) -> None:
    def record(operation_id: str, response: Any, expected: int) -> Any:
        assert response.status_code == expected, f"{operation_id}: {response.status_code} {response.text}"
        body = response.json()
        assert "data" in body, f"{operation_id} 缺少 data 信封: {body}"
        observed[operation_id] = response.status_code
        return body["data"]

    # ===== 本地认证五件套 =====
    record(
        "getLocalAuthStatus",
        await client.get("/api/v1/auth/status"),
        200,
    )
    profile = record(
        "setupLocalAdmin",
        await client.post(
            "/api/v1/auth/setup",
            json={
                "email": "happy-path@qualityforge.example",
                "password": LOCAL_PASSWORD,
                "tenantName": "基线团队",
                "workspaceName": "基线工作区",
            },
        ),
        201,
    )
    record(
        "loginLocalUser",
        await client.post(
            "/api/v1/auth/login", json={"email": "happy-path@qualityforge.example", "password": LOCAL_PASSWORD}
        ),
        200,
    )
    me = record("getCurrentLocalUser", await client.get("/api/v1/auth/me"), 200)
    assert me["workspaceId"] == profile["workspaceId"]
    workspace_id = profile["workspaceId"]
    params = {"workspaceId": workspace_id}
    workspaces = record("listWorkspaces", await client.get("/api/v1/workspaces"), 200)
    assert any(workspace["id"] == workspace_id for workspace in workspaces)
    releases = record("listReleases", await client.get(f"/api/v1/workspaces/{workspace_id}/releases"), 200)
    assert releases and releases[0]["status"] == "ACTIVE"
    release_id = releases[0]["id"]

    # ===== WP-01 驾驶舱投影（只读，计数允许为零）=====
    projection = record(
        "getProjectContextProjection",
        await client.get(f"/api/v1/workspaces/{workspace_id}/context-projection"),
        200,
    )
    assert projection["workspace"]["id"] == workspace_id
    assert projection["currentRelease"]["id"] == release_id

    # ===== WP-03 协作对话（会话 + 只追加消息）=====
    conversation = record(
        "createConversation",
        await client.post(
            "/api/v1/conversations",
            headers=mutation_headers(client, idempotency_key="happy-conv-00000001"),
            json={"workspaceId": workspace_id, "title": "全链路协作会话", "releaseId": release_id},
        ),
        201,
    )
    record(
        "createConversationMessage",
        await client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            headers=mutation_headers(client, idempotency_key="happy-msg-000000001"),
            json={
                "messageType": "TEXT",
                "contentRef": "conv-ref://happy-001",
                "contentDigest": hashlib.sha256("协作链路消息".encode()).hexdigest(),
                "dataClass": "INTERNAL",
            },
        ),
        201,
    )
    conversations = record("listConversations", await client.get("/api/v1/conversations", params=params), 200)
    assert any(item["id"] == conversation["id"] for item in conversations)
    happy_messages = record(
        "listConversationMessages",
        await client.get(f"/api/v1/conversations/{conversation['id']}/messages"),
        200,
    )
    assert len(happy_messages) == 1

    # ===== WP-03 澄清链路（服务面发起 + HTTP 列表/人工答复）=====
    clar_session_id = str(uuid.uuid4())
    planning_workflow_service.sessions[clar_session_id] = {
        "id": clar_session_id,
        "tenantId": profile["tenantId"],
        "workspaceId": workspace_id,
        "workItemId": None,  # 种子会话位于工作项创建段之前，不绑定工作项
        "status": "RUNNING",
        "createdAt": "2026-08-31T00:00:00+00:00",
        "updatedAt": "2026-08-31T00:00:00+00:00",
    }
    clarification = await planning_workflow_service.create_clarification_request(
        profile["tenantId"],
        "agent-runner",
        "SERVICE",
        frozenset(["clarification.raise"]),
        "happy-clarify-00000001",
        clar_session_id,
        {
            "question": "全链路验收以哪份口径为准？",
            "reason": "链路自检",
            "impact": "验收判据",
            "requiredBy": "2026-09-02T00:00:00+00:00",
        },
    )
    listed_clarifications = record(
        "listClarificationRequests",
        await client.get(f"/api/v1/ai/sessions/{clar_session_id}/clarifications", params=params),
        200,
    )
    assert any(item["id"] == clarification["id"] for item in listed_clarifications)
    record(
        "respondClarification",
        await client.post(
            f"/api/v1/clarifications/{clarification['id']}/responses",
            headers=mutation_headers(client, idempotency_key="happy-respond-000001"),
            json={
                "answerRef": "evidence://happy-rfi",
                "answerDigest": hashlib.sha256("以验收判据为准".encode()).hexdigest(),
            },
        ),
        201,
    )

    # ===== WP-04 运行命令（PAUSE 到安全点 + 回执唯一事实）=====
    run_command = record(
        "commandAgentSession",
        await client.post(
            f"/api/v1/ai/sessions/{clar_session_id}/commands",
            headers=mutation_headers(client, idempotency_key="happy-cmd-000000001"),
            json={"commandType": "PAUSE", "reason": "链路演示暂停"},
        ),
        201,
    )
    assert run_command["receipt"]["effectiveStatus"] == "PAUSED"
    receipt_pair = record(
        "getRunCommandReceipt",
        await client.get(f"/api/v1/run-commands/{run_command['id']}", params=params),
        200,
    )
    assert receipt_pair["receipt"]["commandId"] == run_command["id"]
    seeded_exec_task_id = str(uuid.uuid4())
    planning_workflow_service.execution_tasks[seeded_exec_task_id] = {
        "id": seeded_exec_task_id,
        "tenantId": profile["tenantId"],
        "workspaceId": workspace_id,
        "executionPlanVersionId": None,
        "status": "RUNNING",
        "createdAt": "2026-08-31T00:00:00+00:00",
        "updatedAt": "2026-08-31T00:00:00+00:00",
    }
    exec_command = record(
        "commandExecutionTask",
        await client.post(
            f"/api/v1/execution-tasks/{seeded_exec_task_id}/commands",
            headers=mutation_headers(client, idempotency_key="happy-cmd-000000002"),
            json={"commandType": "CANCEL", "reason": "链路演示取消"},
        ),
        201,
    )
    assert exec_command["receipt"]["effectiveStatus"] == "CANCELLED"

    # ===== WP-01A 工作区切换（专用命令重签 JWT，往返验证）=====
    seeded_ws = planning_workflow_service.seed_workspace(profile["tenantId"], profile["userId"], "链路第二项目")
    switched = record(
        "switchLocalWorkspace",
        await client.post(
            "/api/v1/auth/switch-workspace",
            headers=mutation_headers(client),
            json={"workspaceId": seeded_ws["id"]},
        ),
        200,
    )
    assert switched["workspaceId"] == seeded_ws["id"]
    switched_back = record(
        "switchLocalWorkspace",
        await client.post(
            "/api/v1/auth/switch-workspace",
            headers=mutation_headers(client),
            json={"workspaceId": workspace_id},
        ),
        200,
    )
    assert switched_back["workspaceId"] == workspace_id
    pinned = record(
        "setWorkspacePin",
        await client.post(
            f"/api/v1/workspaces/{workspace_id}/pin",
            headers=mutation_headers(client, idempotency_key="happy-pin-0000000001"),
            json={"pinned": True},
        ),
        200,
    )
    assert pinned["pinned"] is True

    # ===== 需求链 =====
    requirement = record(
        "createRequirementDocument",
        await client.post(
            "/api/v1/knowledge/requirements",
            headers=mutation_headers(client),
            json={"workspaceId": workspace_id, "name": "全链路需求", "documentType": "PRD"},
        ),
        201,
    )
    content = "# 全链路\n覆盖 22 个 operation 的 happy path。"
    record(
        "createRequirementDocumentVersion",
        await client.post(
            f"/api/v1/knowledge/requirements/{requirement['id']}/versions",
            headers=mutation_headers(client),
            json={
                "sourceSnapshotId": str(SOURCE_SNAPSHOT_ID),
                "contentDigest": hashlib.sha256(content.encode()).hexdigest(),
                "content": content,
                "changeSummary": "首版",
            },
        ),
        201,
    )
    requirements = record(
        "listRequirementDocuments", await client.get("/api/v1/knowledge/requirements", params=params), 200
    )
    assert len(requirements) == 1

    # ===== 工作项与会话 =====
    work_item = record(
        "createWorkItem",
        await client.post(
            "/api/v1/work-items",
            headers=mutation_headers(client),
            json={
                "workspaceId": workspace_id,
                "releaseId": release_id,
                "workItemType": "STRATEGY",
                "title": "全链路工作项",
                "objective": "走通全部已实现 operation 的 happy path",
                "acceptanceCriteria": "22 个 operation 均返回契约成功状态码",
                "requiresReview": True,
                "priority": "P0",
                "riskLevel": "HIGH",
            },
        ),
        201,
    )
    items = record("listWorkItems", await client.get("/api/v1/work-items", params=params), 200)
    assert any(item["id"] == work_item["id"] for item in items)

    # ===== WP-03 任务卡 → AgentPlan → 人工裁决 =====
    task_card = record(
        "createTaskCard",
        await client.post(
            f"/api/v1/work-items/{work_item['id']}/task-cards",
            headers=mutation_headers(client, idempotency_key="happy-card-000000001"),
            json={
                "objective": "生成全链路回归资产",
                "scope": "覆盖 66 op 主链",
                "acceptanceCriteria": "策略/计划/用例齐备",
                "constraints": "本地确定性 Provider",
                "requestedPermissions": ["requirement.write"],
                "budget": {"maxMinutes": 30},
            },
        ),
        201,
    )
    assert task_card["status"] == "SUBMITTED"
    listed_cards = record(
        "listTaskCards",
        await client.get(f"/api/v1/work-items/{work_item['id']}/task-cards"),
        200,
    )
    assert any(item["id"] == task_card["id"] for item in listed_cards)
    agent_plan = record(
        "createAgentPlan",
        await client.post(
            f"/api/v1/work-items/{work_item['id']}/agent-plans",
            headers=mutation_headers(client, idempotency_key="happy-plan-000000001"),
            json={
                "taskCardId": task_card["id"],
                "steps": [
                    {"stepKey": "summarize", "agentRole": "coordinator", "description": "需求归纳"},
                    {"stepKey": "cases", "agentRole": "case-designer", "description": "用例编制"},
                ],
            },
        ),
        201,
    )
    assert agent_plan["status"] == "PENDING_APPROVAL"
    listed_plans = record(
        "listAgentPlans",
        await client.get(f"/api/v1/work-items/{work_item['id']}/agent-plans", params=params),
        200,
    )
    assert any(item["id"] == agent_plan["id"] for item in listed_plans)
    decision = record(
        "decideAgentPlan",
        await client.post(
            f"/api/v1/agent-plans/{agent_plan['id']}/decisions",
            headers=mutation_headers(client, idempotency_key="happy-decide-0000001"),
            json={
                "decision": "APPROVE",
                "expectedContentDigest": agent_plan["contentDigest"],
                "reason": "与任务卡一致",
            },
        ),
        201,
    )
    assert decision["planStatus"] == "APPROVED"

    # ===== WP-04 授权/预算/检查点 =====
    authorization = record(
        "createRuntimeAuthorization",
        await client.post(
            f"/api/v1/work-items/{work_item['id']}/authorizations",
            headers=mutation_headers(client, idempotency_key="happy-auth-000000001"),
            json={"action": "AUTHORIZE", "permissionKeys": ["requirement.write"]},
        ),
        201,
    )
    assert authorization["status"] == "ACTIVE"
    listed_authorizations = record(
        "listRuntimeAuthorizations",
        await client.get(f"/api/v1/work-items/{work_item['id']}/authorizations", params=params),
        200,
    )
    assert any(item["id"] == authorization["id"] for item in listed_authorizations)
    record(
        "getWorkItemBudget",
        await client.get(f"/api/v1/work-items/{work_item['id']}/budgets", params=params),
        200,
    )
    budget = record(
        "updateWorkItemBudget",
        await client.post(
            f"/api/v1/work-items/{work_item['id']}/budgets",
            headers=mutation_headers(client, idempotency_key="happy-budget-0000001"),
            json={"timeLimitMinutes": 240},
        ),
        200,
    )
    assert budget["limits"]["timeLimitMinutes"] == 240
    checkpoints = record(
        "listRunCheckpoints",
        await client.get(f"/api/v1/runs/AGENT_SESSION/{clar_session_id}/checkpoints", params=params),
        200,
    )
    assert any(item["targetId"] == clar_session_id for item in checkpoints)

    session = record(
        "createAgentSession",
        await client.post(
            "/api/v1/ai/sessions",
            headers=mutation_headers(client, idempotency_key="happy-path-session"),
            json={
                "workspaceId": workspace_id,
                "workItemId": work_item["id"],
                "workflowKey": "gate0-planning-slice",
                "requirementVersionId": requirements[0]["currentVersionId"],
                "releaseId": release_id,
                "ownerId": profile["userId"],
            },
        ),
        202,
    )
    sessions = record("listAgentSessions", await client.get("/api/v1/ai/sessions", params=params), 200)
    assert any(entry["id"] == session["id"] for entry in sessions)
    reloaded = record("getAgentSession", await client.get(f"/api/v1/ai/sessions/{session['id']}", params=params), 200)
    assert reloaded["id"] == session["id"]
    trace = record(
        "getAgentSessionTrace",
        await client.get(f"/api/v1/ai/sessions/{session['id']}/trace", params=params),
        200,
    )
    assert len(trace) >= 3

    # ===== 看板数据面（M2）=====
    detail = record("getWorkItem", await client.get(f"/api/v1/work-items/{work_item['id']}", params=params), 200)
    assert detail["id"] == work_item["id"]
    runs = record(
        "listWorkItemRuns", await client.get(f"/api/v1/work-items/{work_item['id']}/runs", params=params), 200
    )
    assert any(run["sessionId"] == session["id"] for run in runs)

    # ===== 审核链 =====
    tasks = record("listReviewTasks", await client.get("/api/v1/review-tasks", params=params), 200)
    assert len(tasks) == len(session["reviewTaskIds"])
    target = tasks[0]
    single = record("getReviewTask", await client.get(f"/api/v1/review-tasks/{target['id']}", params=params), 200)
    assert single["id"] == target["id"]
    artifact = record(
        "getReviewArtifact",
        await client.get(f"/api/v1/review-tasks/{target['id']}/artifact", params=params),
        200,
    )
    assert artifact["contentDigest"] == target["contentDigest"]
    diff = record(
        "getReviewArtifactDiff",
        await client.get(f"/api/v1/review-tasks/{target['id']}/artifact/diff", params=params),
        200,
    )
    assert diff["artifactVersionId"] == target["artifactVersionId"]
    manual_task = record(
        "createReviewTask",
        await client.post(
            "/api/v1/review-tasks",
            headers=mutation_headers(client, idempotency_key="happy-manual-review-0001"),
            json={
                "workItemId": work_item["id"],
                "artifactType": target["artifactType"],
                "artifactId": target["artifactId"],
                "artifactVersionId": target["artifactVersionId"],
                "contentDigest": target["contentDigest"],
                "policyType": "SINGLE_REVIEW",
                "assignees": [
                    {
                        "userId": profile["userId"],
                        "reviewRole": "REVIEWER",
                        "requiredCapability": "artifact.test_strategy.approve",
                    }
                ],
            },
        ),
        201,
    )
    assert manual_task["status"] == "OPEN"
    decided = record(
        "decideReviewTask",
        await client.post(
            f"/api/v1/review-tasks/{target['id']}/decisions",
            headers=mutation_headers(client, idempotency_key=f"happy-{target['id']}"),
            json={"decision": "APPROVE", "contentDigest": target["contentDigest"]},
        ),
        200,
    )
    assert decided["status"] == "APPROVED"

    # ===== 资产列表四件套 =====
    strategies = record("listTestStrategies", await client.get("/api/v1/test-strategies", params=params), 200)
    plans = record("listTestPlans", await client.get("/api/v1/test-plans", params=params), 200)
    cases = record("listTestCases", await client.get("/api/v1/test-cases", params=params), 200)
    assert strategies and plans and cases
    record(
        "listTestCaseVersions",
        await client.get(f"/api/v1/test-cases/{cases[0]['id']}/versions", params=params),
        200,
    )

    # ===== WP-05 资产发布链（批次六十四）：审核批准后的 Owner 发布命令 =====
    assert target["artifactType"] == "TEST_STRATEGY"
    published_version = record(
        "publishTestStrategyVersion",
        await client.post(
            f"/api/v1/test-strategies/{target['artifactId']}/versions/{target['artifactVersionId']}/publish",
            headers=mutation_headers(client, idempotency_key="happy-publish-strategy-01"),
        ),
        200,
    )
    assert published_version["reviewStatus"] == "PUBLISHED"
    strategies_after_publish = record(
        "listTestStrategies", await client.get("/api/v1/test-strategies", params=params), 200
    )
    published_root = next(item for item in strategies_after_publish if item["id"] == target["artifactId"])
    assert published_root["publishedVersionId"] == target["artifactVersionId"]
    plan_task = next(task for task in tasks if task["artifactType"] == "TEST_PLAN")
    record(
        "decideReviewTask",
        await client.post(
            f"/api/v1/review-tasks/{plan_task['id']}/decisions",
            headers=mutation_headers(client, idempotency_key=f"happy-{plan_task['id']}"),
            json={"decision": "APPROVE", "contentDigest": plan_task["contentDigest"]},
        ),
        200,
    )
    record(
        "publishTestPlanVersion",
        await client.post(
            f"/api/v1/test-plans/{plan_task['artifactId']}/versions/{plan_task['artifactVersionId']}/publish",
            headers=mutation_headers(client, idempotency_key="happy-publish-plan-000001"),
        ),
        200,
    )
    case_task = next(task for task in tasks if task["artifactType"] == "TEST_CASE")
    record(
        "decideReviewTask",
        await client.post(
            f"/api/v1/review-tasks/{case_task['id']}/decisions",
            headers=mutation_headers(client, idempotency_key=f"happy-{case_task['id']}"),
            json={"decision": "APPROVE", "contentDigest": case_task["contentDigest"]},
        ),
        200,
    )
    record(
        "publishTestCaseVersion",
        await client.post(
            f"/api/v1/test-cases/{case_task['artifactId']}/versions/{case_task['artifactVersionId']}/publish",
            headers=mutation_headers(client, idempotency_key="happy-publish-case-000001"),
        ),
        200,
    )

    # ===== 执行链（M3）=====
    exec_plan = record(
        "createExecutionPlan",
        await client.post(
            "/api/v1/execution-plans",
            headers=mutation_headers(client),
            json={
                "workspaceId": workspace_id,
                "planKey": "EXEC-HAPPY-001",
                "name": "Happy path 执行计划",
                "testPlanId": plans[0]["id"],
            },
        ),
        201,
    )
    exec_task = record(
        "startExecutionPlan",
        await client.post(
            f"/api/v1/execution-plans/{exec_plan['id']}/runs",
            headers=mutation_headers(client, idempotency_key="happy-exec-run-00001"),
            json={"executionPlanVersionId": exec_plan["currentVersionId"]},
        ),
        202,
    )
    assert exec_task["status"] == "COMPLETED"
    exec_tasks = record("listExecutionTasks", await client.get("/api/v1/execution-tasks", params=params), 200)
    assert any(entry["id"] == exec_task["id"] for entry in exec_tasks)
    exec_plans = record("listExecutionPlans", await client.get("/api/v1/execution-plans", params=params), 200)
    assert any(item["id"] == exec_plan["id"] for item in exec_plans)
    exec_results = record(
        "listExecutionResults",
        await client.get("/api/v1/execution-results", params={"executionTaskId": exec_task["id"]}),
        200,
    )
    assert exec_results and all(result["evidenceDigest"] for result in exec_results)
    assert all(result["resultDigest"] and result["assertionResultsRef"] for result in exec_results)

    # ===== 质量域（M4）=====
    analysis = record(
        "createResultAnalysis",
        await client.post(
            "/api/v1/quality/result-analyses",
            headers=mutation_headers(client),
            json={
                "workspaceId": workspace_id,
                "releaseId": release_id,
                "analysisKey": "RA-HAPPY-001",
                "executionResultRefs": [result["id"] for result in exec_results],
            },
        ),
        201,
    )
    assert analysis["contentDigest"] and analysis["conclusionRef"]
    analyses = record("listResultAnalyses", await client.get("/api/v1/quality/result-analyses", params=params), 200)
    assert any(item["id"] == analysis["id"] for item in analyses)
    record("listFailureClusters", await client.get("/api/v1/quality/failure-clusters", params=params), 200)
    defect = record(
        "createDefect",
        await client.post(
            "/api/v1/quality/defects",
            headers=mutation_headers(client),
            json={
                "workspaceId": workspace_id,
                "releaseId": release_id,
                "defectKey": "DEF-HAPPY-001",
                "createdFromWorkItemId": work_item["id"],
            },
        ),
        201,
    )
    assert defect["lifecycleStatus"] == "NEW"
    defects = record("listDefects", await client.get("/api/v1/quality/defects", params=params), 200)
    assert any(item["id"] == defect["id"] for item in defects)
    defect_version = record(
        "createDefectVersion",
        await client.post(
            f"/api/v1/quality/defects/{defect['id']}/versions",
            headers=mutation_headers(client),
            json={
                "title": "全链路验证缺陷",
                "description": "happy path 缺陷描述",
                "expectedResult": "期望结果",
                "actualResult": "实际结果",
                "severity": "MEDIUM",
                "priority": "P2",
                "defectType": "PRODUCT",
                "environmentSnapshotRef": "env:happy-path",
                "affectedReleaseIds": [release_id],
                "evidence": [{"type": "LOG", "ref": "evidence:happy"}],
            },
        ),
        201,
    )
    quality_tasks = record("listReviewTasks", await client.get("/api/v1/review-tasks", params=params), 200)
    defect_task = next(t for t in quality_tasks if t["artifactType"] == "DEFECT_VERSION")
    record(
        "decideReviewTask",
        await client.post(
            f"/api/v1/review-tasks/{defect_task['id']}/decisions",
            headers=mutation_headers(client, idempotency_key=f"happy-{defect_task['id']}"),
            json={"decision": "APPROVE", "contentDigest": defect_task["contentDigest"]},
        ),
        200,
    )
    sync_payload = {"title": "外部缺陷标题"}
    attempt = record(
        "createDefectSyncAttempt",
        await client.post(
            f"/api/v1/quality/defects/{defect['id']}/sync-attempts",
            headers=mutation_headers(client, idempotency_key="happy-sync-00000000001"),
            json={
                "defectVersionId": defect_version["id"],
                "integrationId": str(uuid.uuid4()),
                "operation": "CREATE",
                "payloadDigest": content_digest(sync_payload),
                "approvalId": defect_task["id"],
                "payload": sync_payload,
            },
        ),
        202,
    )
    assert attempt["status"] == "ACKNOWLEDGED" and attempt["receiptDigest"]
    report = record(
        "createTestReport",
        await client.post(
            "/api/v1/quality/reports",
            headers=mutation_headers(client),
            json={
                "workspaceId": workspace_id,
                "releaseId": release_id,
                "reportKey": "RPT-HAPPY-001",
            },
        ),
        201,
    )
    assert report["status"] == "ACTIVE"
    reports = record(
        "listTestReports",
        await client.get("/api/v1/quality/reports", params={**params, "releaseId": release_id}),
        200,
    )
    assert any(item["id"] == report["id"] for item in reports)
    report_version = record(
        "createTestReportVersion",
        await client.post(
            f"/api/v1/quality/reports/{report['id']}/versions",
            headers=mutation_headers(client),
            json={
                "scopeSnapshotRef": "scope:happy-v1",
                "executionSnapshotRef": f"exec:{exec_task['id']}",
                "qualityConclusion": "happy-path 质量结论：全链路达标",
                "changeSummary": "首版报告",
            },
        ),
        201,
    )
    assert report_version["version"] == 1 and report_version["reviewStatus"] == "PENDING_REVIEW"
    report_versions = record(
        "listTestReportVersions",
        await client.get(f"/api/v1/quality/reports/{report['id']}/versions", params=params),
        200,
    )
    assert any(item["id"] == report_version["id"] for item in report_versions)
    coverage = record(
        "createCoverageReport",
        await client.post(
            "/api/v1/quality/coverage-reports",
            headers=mutation_headers(client),
            json={
                "workspaceId": workspace_id,
                "releaseId": release_id,
                "denominatorDefinitionRef": "EFFECTIVE",
                "scopeSnapshotRef": "scope:happy-v1",
                "ruleDimension": {"covered": 10, "total": 10},
            },
        ),
        201,
    )
    assert coverage["verdict"] == "SATISFIED"
    record("listCoverageReports", await client.get("/api/v1/quality/coverage-reports", params=params), 200)
    entry = record(
        "createKnowledgeEntry",
        await client.post(
            "/api/v1/knowledge/entries",
            headers=mutation_headers(client),
            json={"workspaceId": workspace_id, "knowledgeKey": "KB-HAPPY-001", "category": "FAILURE_PATTERN"},
        ),
        201,
    )
    assert entry["knowledgeKey"] == "KB-HAPPY-001"
    entries = record("listKnowledgeEntries", await client.get("/api/v1/knowledge/entries", params=params), 200)
    assert any(item["id"] == entry["id"] for item in entries)

    # ===== 平台域环境 + Provider 状态（批次四十六联调面补齐）=====
    environment = record(
        "createEnvironment",
        await client.post(
            f"/api/v1/platform/workspaces/{workspace_id}/environments",
            headers=mutation_headers(client),
            json={
                "name": "Happy 测试环境",
                "environmentType": "TEST",
                "endpointMappings": {"web": "https://happy.example"},
            },
        ),
        201,
    )
    assert environment["workspaceId"] == workspace_id
    environments = record(
        "listEnvironments",
        await client.get(f"/api/v1/platform/workspaces/{workspace_id}/environments"),
        200,
    )
    assert any(item["id"] == environment["id"] for item in environments)
    provider_status = record("getProviderStatus", await client.get("/api/v1/ai/provider/status"), 200)
    assert provider_status["status"] == "NOMINAL" and provider_status["providerId"]

    # ===== 退回→新版本闭环（M1-B1）=====
    new_strategy_version = record(
        "createTestStrategyVersion",
        await client.post(
            f"/api/v1/test-strategies/{strategies[0]['id']}/versions",
            headers=mutation_headers(client),
            json={
                "objective": "全链路修订版策略",
                "inScope": ["22+3 个 operation 的 happy path"],
                "outOfScope": ["未实现 operation"],
                "riskAssessment": [{"risk": "覆盖缺口", "level": "LOW", "treatment": "清单强同步"}],
                "testTypes": ["FUNCTIONAL"],
                "approach": "风险驱动",
                "entryCriteria": ["基线绿"],
                "exitCriteria": ["新版本通过审核"],
                "environmentStrategy": "本地运行时",
                "dataStrategy": "临时 SQLite",
                "automationStrategy": "pytest",
                "defectStrategy": "先分析后立 Defect",
                "changeSummary": "M1-B1 修订",
            },
        ),
        201,
    )
    assert new_strategy_version["version"] == 2
    new_plan_version = record(
        "createTestPlanVersion",
        await client.post(
            f"/api/v1/test-plans/{plans[0]['id']}/versions",
            headers=mutation_headers(client),
            json={
                "strategyVersionId": new_strategy_version["id"],
                "objective": "全链路修订版计划",
                "planType": "RELEASE_VALIDATION",
                "scope": {"focus": "M1-B1 闭环"},
                "ownerId": profile["userId"],
                "startDate": "2026-08-17",
                "endDate": "2026-08-20",
                "milestones": [{"name": "复审"}],
                "resourceRequirements": {"reviewer": 1},
                "acceptanceCriteria": ["版本递增且新任务自动创建"],
                "changeSummary": "M1-B1 修订",
            },
        ),
        201,
    )
    assert new_plan_version["version"] == 2

    # ===== 工作项状态迁移（乐观锁，M1-B1）=====
    rework_item = record(
        "createWorkItem",
        await client.post(
            "/api/v1/work-items",
            headers=mutation_headers(client),
            json={
                "workspaceId": workspace_id,
                "workItemType": "GENERAL",
                "title": "状态机验证工作项",
                "objective": "验证 transitionWorkItem REWORK 路径",
                "acceptanceCriteria": "乐观锁陈旧提交 409",
                "requiresReview": False,
                "priority": "P2",
                "riskLevel": "LOW",
            },
        ),
        201,
    )
    transitioned = record(
        "transitionWorkItem",
        await client.post(
            f"/api/v1/work-items/{rework_item['id']}/transitions",
            headers=mutation_headers(client, idempotency_key=f"happy-transition-{rework_item['id']}"),
            json={"targetStatus": "REWORK", "reason": "happy-path 状态机验证", "lockVersion": 0},
        ),
        200,
    )
    assert transitioned["status"] == "REWORK" and transitioned["lockVersion"] == 1

    # ===== 工作项分派 + SLA 面板（M2/U3-U4）=====
    assigned = record(
        "assignWorkItem",
        await client.post(
            f"/api/v1/work-items/{rework_item['id']}/assign",
            headers=mutation_headers(client),
            json={"workspaceId": workspace_id, "assigneeId": profile["userId"]},
        ),
        200,
    )
    assert assigned["assigneeId"] == profile["userId"]
    # 同人重分派幂等 no-op：返回当前状态，不产生新事件
    reassigned = record(
        "assignWorkItem",
        await client.post(
            f"/api/v1/work-items/{rework_item['id']}/assign",
            headers=mutation_headers(client),
            json={"workspaceId": workspace_id, "assigneeId": profile["userId"]},
        ),
        200,
    )
    assert reassigned["assigneeId"] == profile["userId"]
    sla_overview = record(
        "listWorkItemSlaOverview",
        await client.get("/api/v1/work-items/sla-overview", params=params),
        200,
    )
    assert sla_overview["overall"]["total"] > 0
    assert [group["priority"] for group in sla_overview["groups"]] == ["P0", "P1", "P2"]

    # ===== Observability 只读面（V1 事件管道 D3/O3：事件流非空 + 25 项 metricKey）=====
    event_page = record(
        "listEvents",
        await client.get("/api/v1/observability/events", params={**params, "pageSize": 100}),
        200,
    )
    assert len(event_page) > 0
    event_types = {event["eventType"] for event in event_page}
    assert "artifact.version.generated" in event_types and "review.decided" in event_types
    metric_page = record("listMetrics", await client.get("/api/v1/observability/metrics", params=params), 200)
    assert len(metric_page) == 25
    assert all("metricKey" in item and "denominator" in item and "basis" in item for item in metric_page)

    # ===== WP-01 归档链（切到第二项目归档其默认 Release，再切回）=====
    await client.post(
        "/api/v1/auth/switch-workspace",
        headers=mutation_headers(client),
        json={"workspaceId": seeded_ws["id"]},
    )
    ws2_releases = await client.get(f"/api/v1/workspaces/{seeded_ws['id']}/releases")
    assert ws2_releases.status_code == 200 and ws2_releases.json()["data"]
    archived = record(
        "archiveRelease",
        await client.post(
            f"/api/v1/workspaces/{seeded_ws['id']}/releases/{ws2_releases.json()['data'][0]['id']}/archive",
            headers=mutation_headers(client, idempotency_key="happy-archive-0000001"),
        ),
        200,
    )
    assert archived["status"] == "ARCHIVED"
    empty_releases = await client.get(f"/api/v1/workspaces/{seeded_ws['id']}/releases")
    assert empty_releases.json()["data"] == []
    await client.post(
        "/api/v1/auth/switch-workspace",
        headers=mutation_headers(client),
        json={"workspaceId": workspace_id},
    )

    # ===== 登出收尾 =====
    record("logoutLocalUser", await client.post("/api/v1/auth/logout", headers=mutation_headers(client)), 200)

    # 覆盖集必须与实现清单完全一致
    assert set(observed) == set(EXPECTED_IMPLEMENTED_OPERATION_IDS), (
        f"happy-path 覆盖缺口: {set(EXPECTED_IMPLEMENTED_OPERATION_IDS) - set(observed)}; "
        f"多余: {set(observed) - set(EXPECTED_IMPLEMENTED_OPERATION_IDS)}"
    )
