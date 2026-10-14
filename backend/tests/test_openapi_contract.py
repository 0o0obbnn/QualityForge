"""Contract checks against the authoritative external OpenAPI document."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from openapi_spec_validator import validate

from qf.main import app

AUTHORITATIVE_SPEC = Path(__file__).parents[2] / "docs" / "04-architecture" / "32-API规范.yaml"
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "options", "head", "trace"})


def load_authoritative_spec() -> dict[str, Any]:
    payload: dict[str, Any] = yaml.safe_load(AUTHORITATIVE_SPEC.read_text(encoding="utf-8"))
    return payload


def test_authoritative_openapi_is_officially_valid() -> None:
    validate(load_authoritative_spec())


def test_runtime_slice_paths_and_operation_ids_match_authoritative_contract() -> None:
    authoritative = load_authoritative_spec()
    generated = app.openapi()

    implemented_count = 0
    for runtime_path, runtime_path_item in generated["paths"].items():
        if runtime_path == "/health":
            continue
        contract_path = runtime_path.removeprefix("/api/v1")
        assert contract_path in authoritative["paths"], contract_path
        for method, runtime_operation in runtime_path_item.items():
            if method not in HTTP_METHODS:
                continue
            implemented_count += 1
            contract_operation = authoritative["paths"][contract_path][method]
            assert runtime_operation["operationId"] == contract_operation["operationId"]

    assert implemented_count == 84


def test_vertical_slice_success_responses_are_not_generic() -> None:
    authoritative = load_authoritative_spec()
    operation_ids = {
        "listRequirementDocuments",
        "createRequirementDocument",
        "createRequirementDocumentVersion",
        "listTestStrategies",
        "createTestStrategy",
        "createTestStrategyVersion",
        "listTestPlans",
        "createTestPlan",
        "createTestPlanVersion",
        "listTestCases",
        "createTestCase",
        "listTestCaseVersions",
        "createTestCaseVersion",
        "listAgentSessions",
        "createAgentSession",
        "getAgentSession",
        "getAgentSessionTrace",
        "getReviewArtifact",
        "getLocalAuthStatus",
        "setupLocalAdmin",
        "loginLocalUser",
        "getCurrentLocalUser",
        "logoutLocalUser",
    }
    checked: set[str] = set()
    for path_item in authoritative["paths"].values():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS or operation.get("operationId") not in operation_ids:
                continue
            checked.add(operation["operationId"])
            for status_code, response in operation["responses"].items():
                if not status_code.startswith("2"):
                    continue
                response_ref = response.get("$ref", "")
                assert "GenericObjectResponse" not in response_ref
                assert "GenericListResponse" not in response_ref
    assert checked == operation_ids


# ===== 契约延期清单：显式跟踪"已实现"与"主动延期"，防止静默漂移 =====
# 运行时实现 84 个 operation；权威契约共 146 个；主动延期 62 个（其余模块未开工）。
# 新增实现 → 加入下方清单并同步 KNOWN_DEFERRED_COUNT；契约新增 operation → 更新 KNOWN_DEFERRED_COUNT。
EXPECTED_IMPLEMENTED_OPERATION_IDS = frozenset(
    {
        "switchLocalWorkspace",
        "getProjectContextProjection",
        "setWorkspacePin",
        "archiveRelease",
        "listConversations",
        "createConversation",
        "listConversationMessages",
        "createConversationMessage",
        "listClarificationRequests",
        "respondClarification",
        "createTaskCard",
        "listTaskCards",
        "listAgentPlans",
        "createAgentPlan",
        "decideAgentPlan",
        "commandAgentSession",
        "commandExecutionTask",
        "getRunCommandReceipt",
        "listRuntimeAuthorizations",
        "createRuntimeAuthorization",
        "getWorkItemBudget",
        "updateWorkItemBudget",
        "listRunCheckpoints",
        "publishTestStrategyVersion",
        "publishTestPlanVersion",
        "publishTestCaseVersion",
        "assignWorkItem",
        "createAgentSession",
        "createCoverageReport",
        "createDefect",
        "createDefectSyncAttempt",
        "createDefectVersion",
        "createEnvironment",
        "createExecutionPlan",
        "createKnowledgeEntry",
        "createRequirementDocument",
        "createRequirementDocumentVersion",
        "createResultAnalysis",
        "createTestPlanVersion",
        "createTestReport",
        "createTestReportVersion",
        "createTestStrategyVersion",
        "createReviewTask",
        "createWorkItem",
        "decideReviewTask",
        "getAgentSession",
        "getAgentSessionTrace",
        "getCurrentLocalUser",
        "getLocalAuthStatus",
        "getProviderStatus",
        "getReviewArtifact",
        "getReviewArtifactDiff",
        "getReviewTask",
        "getWorkItem",
        "listAgentSessions",
        "listCoverageReports",
        "listDefects",
        "listEnvironments",
        "listEvents",
        "listExecutionPlans",
        "listExecutionResults",
        "listExecutionTasks",
        "listFailureClusters",
        "listKnowledgeEntries",
        "listMetrics",
        "listRequirementDocuments",
        "listResultAnalyses",
        "listReviewTasks",
        "listReleases",
        "listTestCaseVersions",
        "listTestCases",
        "listTestPlans",
        "listTestReports",
        "listTestReportVersions",
        "listTestStrategies",
        "listWorkItemRuns",
        "listWorkItemSlaOverview",
        "listWorkItems",
        "listWorkspaces",
        "loginLocalUser",
        "logoutLocalUser",
        "setupLocalAdmin",
        "startExecutionPlan",
        "transitionWorkItem",
    }
)

# 权威契约 operation 总数(146) - 已实现(84) = 主动延期(62)。
# 其中 2 个为 WP-05 资产发布链剩余面（publishAutomationScriptVersion/publishKnowledgeCandidate，
# 批次六十三激活、上游 create 面未实现故留延期，不做空壳）；
# 1 个为 WP-03 剩余 HTTP 面（createClarificationRequest，随 agent 运行时）；
# 三个 TestPlanning 发布 op 已在批次六十四转实现。
KNOWN_DEFERRED_COUNT = 62


def _runtime_operation_ids() -> set[str]:
    """运行时 FastAPI 自省：已实现的业务 operationId（排除 /health 冒烟端点）。"""
    generated = app.openapi()
    ops: set[str] = set()
    for runtime_path, runtime_path_item in generated["paths"].items():
        if runtime_path == "/health":
            continue
        for method, runtime_operation in runtime_path_item.items():
            if method in HTTP_METHODS:
                ops.add(runtime_operation["operationId"])
    return ops


def _authoritative_operation_ids() -> set[str]:
    """权威契约：全部 operationId 集合。"""
    authoritative = load_authoritative_spec()
    ops: set[str] = set()
    for path_item in authoritative["paths"].values():
        for method, operation in path_item.items():
            if method in HTTP_METHODS and "operationId" in operation:
                ops.add(operation["operationId"])
    return ops


def test_implemented_operations_match_expected_manifest() -> None:
    """运行时实现集必须与显式清单完全一致——新增/删除实现都会触发，强制显式更新。"""
    runtime_ops = _runtime_operation_ids()
    assert runtime_ops == EXPECTED_IMPLEMENTED_OPERATION_IDS, (
        f"运行时实现与清单不一致 — "
        f"新增(需加入清单): {runtime_ops - EXPECTED_IMPLEMENTED_OPERATION_IDS}; "
        f"消失(实现被删?): {EXPECTED_IMPLEMENTED_OPERATION_IDS - runtime_ops}"
    )


def test_deferred_operation_count_is_stable() -> None:
    """权威契约中未实现 operation 的数量必须等于 KNOWN_DEFERRED_COUNT。

    契约新增 operation 或实现新切片都会改变延期数量，触发此断言，
    强制开发者显式更新清单与计数，堵住"静默漂移"。
    """
    authoritative_ops = _authoritative_operation_ids()
    deferred = authoritative_ops - EXPECTED_IMPLEMENTED_OPERATION_IDS
    assert len(deferred) == KNOWN_DEFERRED_COUNT, (
        f"延期 operation 数量变化(期望 {KNOWN_DEFERRED_COUNT}, 实际 {len(deferred)}) — "
        f"契约新增 operation 则更新 KNOWN_DEFERRED_COUNT; "
        f"实现新 operation 则加入 EXPECTED_IMPLEMENTED_OPERATION_IDS 并递减 KNOWN_DEFERRED_COUNT"
    )
