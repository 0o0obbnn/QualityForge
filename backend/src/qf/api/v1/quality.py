"""M4 质量域纵向切片 API（分析/聚类/缺陷/同步/报告/覆盖率/知识回流）。"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Path, Query, Request, status

from qf.api.dependencies import ActorContext, actor_context
from qf.schemas.common import success
from qf.schemas.quality import (
    CoverageReportCreate,
    DefectCreate,
    DefectSyncAttemptCreate,
    DefectVersionCreate,
    KnowledgeEntryCreate,
    ResultAnalysisCreate,
    TestReportCreate,
    TestReportVersionCreate,
)
from qf.services.planning_workflow import DomainError, planning_workflow_service

router = APIRouter(prefix="/api/v1", tags=["QualitySlice"])
Actor = Annotated[ActorContext, Depends(actor_context)]


def _trace_id(request: Request) -> str:
    return str(request.state.trace_id)


def _require_workspace(actor: ActorContext, workspace_id: uuid.UUID) -> None:
    if workspace_id != actor.workspace_id:
        raise DomainError(403, "FORBIDDEN", "当前身份无权访问该Workspace")


@router.get("/quality/result-analyses", operation_id="listResultAnalyses")
async def list_result_analyses(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    """批次四十六：结果分析只读面（契约新增，前端 fetchAnalyses 已在调用）。"""
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_result_analyses(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.post(
    "/quality/result-analyses", status_code=status.HTTP_201_CREATED, operation_id="createResultAnalysis"
)
async def create_result_analysis(
    request: Request,
    payload: ResultAnalysisCreate,
    actor: Actor,
) -> dict[str, Any]:
    _require_workspace(actor, payload.workspaceId)
    data = await planning_workflow_service.create_result_analysis(
        str(actor.tenant_id), str(actor.workspace_id), actor.capabilities, payload.model_dump()
    )
    return success(data, _trace_id(request), "结果分析已创建")


@router.get("/quality/failure-clusters", operation_id="listFailureClusters")
async def list_failure_clusters(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_failure_clusters(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.get("/quality/defects", operation_id="listDefects")
async def list_defects(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_defects(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.post("/quality/defects", status_code=status.HTTP_201_CREATED, operation_id="createDefect")
async def create_defect(
    request: Request,
    payload: DefectCreate,
    actor: Actor,
) -> dict[str, Any]:
    _require_workspace(actor, payload.workspaceId)
    data = await planning_workflow_service.create_defect(
        str(actor.tenant_id), str(actor.workspace_id), actor.capabilities, payload.model_dump()
    )
    return success(data, _trace_id(request), "缺陷已立项")


@router.post(
    "/quality/defects/{defectId}/versions", status_code=status.HTTP_201_CREATED, operation_id="createDefectVersion"
)
async def create_defect_version(
    request: Request,
    defect_id: Annotated[uuid.UUID, Path(alias="defectId")],
    payload: DefectVersionCreate,
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.create_defect_version(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.capabilities,
        str(defect_id),
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "缺陷版本已创建，等待人工批准")


@router.post(
    "/quality/defects/{defectId}/sync-attempts",
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="createDefectSyncAttempt",
)
async def create_defect_sync_attempt(
    request: Request,
    defect_id: Annotated[uuid.UUID, Path(alias="defectId")],
    payload: DefectSyncAttemptCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.create_defect_sync_attempt(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.capabilities,
        str(defect_id),
        idempotency_key,
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "外部同步尝试已受理并回执")


@router.get("/quality/reports", operation_id="listTestReports")
async def list_test_reports(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
    release_id: Annotated[uuid.UUID | None, Query(alias="releaseId")] = None,
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_test_reports(
        str(actor.tenant_id), str(workspace_id), release_id=str(release_id) if release_id else None
    )
    return success(data, _trace_id(request))


@router.post("/quality/reports", status_code=status.HTTP_201_CREATED, operation_id="createTestReport")
async def create_test_report(
    request: Request,
    payload: TestReportCreate,
    actor: Actor,
) -> dict[str, Any]:
    _require_workspace(actor, payload.workspaceId)
    data = await planning_workflow_service.create_test_report(
        str(actor.tenant_id), str(actor.workspace_id), actor.capabilities, payload.model_dump()
    )
    return success(data, _trace_id(request), "测试报告已创建")


@router.get("/quality/reports/{testReportId}/versions", operation_id="listTestReportVersions")
async def list_test_report_versions(
    request: Request,
    test_report_id: Annotated[uuid.UUID, Path(alias="testReportId")],
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_test_report_versions(
        str(actor.tenant_id), str(workspace_id), str(test_report_id)
    )
    return success(data, _trace_id(request))


@router.post(
    "/quality/reports/{testReportId}/versions",
    status_code=status.HTTP_201_CREATED,
    operation_id="createTestReportVersion",
)
async def create_test_report_version(
    request: Request,
    test_report_id: Annotated[uuid.UUID, Path(alias="testReportId")],
    payload: TestReportVersionCreate,
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.create_test_report_version(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.capabilities,
        str(test_report_id),
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "报告版本已创建，等待人工批准")


@router.get("/quality/coverage-reports", operation_id="listCoverageReports")
async def list_coverage_reports(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
    release_id: Annotated[uuid.UUID | None, Query(alias="releaseId")] = None,
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_coverage_reports(
        str(actor.tenant_id), str(workspace_id), release_id=str(release_id) if release_id else None
    )
    return success(data, _trace_id(request))


@router.post(
    "/quality/coverage-reports", status_code=status.HTTP_201_CREATED, operation_id="createCoverageReport"
)
async def create_coverage_report(
    request: Request,
    payload: CoverageReportCreate,
    actor: Actor,
) -> dict[str, Any]:
    _require_workspace(actor, payload.workspaceId)
    data = await planning_workflow_service.create_coverage_report(
        str(actor.tenant_id), str(actor.workspace_id), actor.capabilities, payload.model_dump()
    )
    return success(data, _trace_id(request), "覆盖率报告已创建")


@router.post("/knowledge/entries", status_code=status.HTTP_201_CREATED, operation_id="createKnowledgeEntry")
async def create_knowledge_entry(
    request: Request,
    payload: KnowledgeEntryCreate,
    actor: Actor,
) -> dict[str, Any]:
    _require_workspace(actor, payload.workspaceId)
    data = await planning_workflow_service.create_knowledge_entry(
        str(actor.tenant_id), str(actor.workspace_id), actor.capabilities, payload.model_dump()
    )
    return success(data, _trace_id(request), "知识条目已沉淀")
