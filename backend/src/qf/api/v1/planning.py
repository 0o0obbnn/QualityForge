"""Gate 0 planning vertical-slice API."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Path, Query, Request, status

from qf.api.dependencies import ActorContext, actor_context
from qf.schemas.common import success, success_paged
from qf.schemas.execution import ExecutionPlanCreate, ExecutionStartRequest
from qf.schemas.planning import (
    AgentSessionCreate,
    EnvironmentCreate,
    RequirementDocumentCreate,
    RequirementDocumentVersionCreate,
    ReviewDecisionCreate,
    ReviewTaskCreate,
    TestPlanVersionCreate,
    TestStrategyVersionCreate,
    WorkItemAssignRequest,
    WorkItemCreate,
    WorkItemTransition,
    WorkspacePin,
)
from qf.services.planning_workflow import planning_workflow_service

router = APIRouter(prefix="/api/v1", tags=["Gate0PlanningSlice"])
Actor = Annotated[ActorContext, Depends(actor_context)]
WorkItemStatusQuery = (
    Literal[
        "BACKLOG",
        "READY",
        "IN_PROGRESS",
        "PENDING_REVIEW",
        "REWORK",
        "APPROVED",
        "BLOCKED",
        "DONE",
        "CANCELLED",
    ]
    | None
)
ReviewTaskStatusQuery = (
    Literal["OPEN", "IN_PROGRESS", "APPROVED", "CHANGES_REQUESTED", "REJECTED", "EXPIRED", "CANCELLED"] | None
)


def _trace_id(request: Request) -> str:
    return str(request.state.trace_id)


def _require_workspace(actor: ActorContext, workspace_id: uuid.UUID) -> None:
    if workspace_id != actor.workspace_id:
        from qf.services.planning_workflow import DomainError

        raise DomainError(403, "FORBIDDEN", "当前身份无权访问该Workspace")


@router.get("/workspaces", operation_id="listWorkspaces")
async def list_workspaces(request: Request, actor: Actor) -> dict[str, Any]:
    data = await planning_workflow_service.list_workspaces(str(actor.tenant_id), str(actor.actor_id))
    return success(data, _trace_id(request))


@router.get("/workspaces/{workspaceId}/releases", operation_id="listReleases")
async def list_releases(
    request: Request,
    workspace_id: Annotated[uuid.UUID, Path(alias="workspaceId")],
    actor: Actor,
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_releases(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.get("/workspaces/{workspaceId}/context-projection", operation_id="getProjectContextProjection")
async def get_project_context_projection(
    request: Request,
    workspace_id: Annotated[uuid.UUID, Path(alias="workspaceId")],
    actor: Actor,
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.get_project_context_projection(
        str(actor.tenant_id), str(actor.actor_id), str(workspace_id)
    )
    return success(data, _trace_id(request))


@router.post("/workspaces/{workspaceId}/pin", operation_id="setWorkspacePin")
async def set_workspace_pin(
    request: Request,
    workspace_id: Annotated[uuid.UUID, Path(alias="workspaceId")],
    payload: WorkspacePin,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = planning_workflow_service.set_workspace_pin(
        str(actor.tenant_id), str(actor.actor_id), str(workspace_id), pinned=payload.pinned
    )
    return success(data, _trace_id(request), "常用项目已更新")


@router.post("/workspaces/{workspaceId}/releases/{releaseId}/archive", operation_id="archiveRelease")
async def archive_release(
    request: Request,
    workspace_id: Annotated[uuid.UUID, Path(alias="workspaceId")],
    release_id: Annotated[uuid.UUID, Path(alias="releaseId")],
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = planning_workflow_service.archive_release(
        str(actor.tenant_id), actor.capabilities, str(workspace_id), str(release_id)
    )
    return success(data, _trace_id(request), "Release 已归档")


@router.get("/knowledge/requirements", operation_id="listRequirementDocuments")
async def list_requirements(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_requirements(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.post(
    "/knowledge/requirements",
    status_code=status.HTTP_201_CREATED,
    operation_id="createRequirementDocument",
)
async def create_requirement(
    request: Request,
    payload: RequirementDocumentCreate,
    actor: Actor,
) -> dict[str, Any]:
    _require_workspace(actor, payload.workspaceId)
    data = await planning_workflow_service.create_requirement(
        str(actor.tenant_id), actor.capabilities, payload.model_dump()
    )
    return success(data, _trace_id(request), "需求文档已创建")


@router.post(
    "/knowledge/requirements/{requirementId}/versions",
    status_code=status.HTTP_201_CREATED,
    operation_id="createRequirementDocumentVersion",
)
async def create_requirement_version(
    request: Request,
    requirement_id: Annotated[uuid.UUID, Path(alias="requirementId")],
    payload: RequirementDocumentVersionCreate,
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.create_requirement_version(
        str(actor.tenant_id),
        str(actor.workspace_id),
        actor.capabilities,
        str(requirement_id),
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "需求版本已固定")


@router.get("/knowledge/entries", operation_id="listKnowledgeEntries")
async def list_knowledge_entries(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_knowledge_entries(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.get("/work-items", operation_id="listWorkItems")
async def list_work_items(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
    status_filter: WorkItemStatusQuery = Query(default=None, alias="status"),
    page: Annotated[int | None, Query(ge=1)] = None,
    page_size: Annotated[int | None, Query(alias="pageSize", ge=1, le=200)] = None,
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    items = await planning_workflow_service.list_work_items(
        str(actor.tenant_id), str(workspace_id), status=status_filter
    )
    if page is None and page_size is None:
        return success(items, _trace_id(request))
    resolved_page, resolved_size = page or 1, page_size or 20
    window = items[(resolved_page - 1) * resolved_size : resolved_page * resolved_size]
    return success_paged(window, _trace_id(request), page=resolved_page, page_size=resolved_size, total=len(items))


@router.get("/work-items/sla-overview", operation_id="listWorkItemSlaOverview")
async def list_work_item_sla_overview(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    """看板 SLA 面板：按优先级（P0/P1/P2）分组统计 + 整体汇总（见服务端 SLA_WINDOW_HOURS 口径）。"""
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.sla_overview(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.post("/work-items/{workItemId}/assign", operation_id="assignWorkItem")
async def assign_work_item(
    request: Request,
    work_item_id: Annotated[uuid.UUID, Path(alias="workItemId")],
    payload: WorkItemAssignRequest,
    actor: Actor,
) -> dict[str, Any]:
    """工作项分派：落库 assigneeId；同人重分派幂等成功（no-op 返回当前状态）。"""
    _require_workspace(actor, payload.workspaceId)
    data = await planning_workflow_service.assign_work_item(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.capabilities,
        str(work_item_id),
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "工作项已分派")


@router.get("/work-items/{workItemId}", operation_id="getWorkItem")
async def get_work_item(
    request: Request,
    work_item_id: Annotated[uuid.UUID, Path(alias="workItemId")],
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.get_work_item(
        str(actor.tenant_id), str(actor.workspace_id), str(work_item_id)
    )
    return success(data, _trace_id(request))


@router.get("/work-items/{workItemId}/runs", operation_id="listWorkItemRuns")
async def list_work_item_runs(
    request: Request,
    work_item_id: Annotated[uuid.UUID, Path(alias="workItemId")],
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.list_work_item_runs(
        str(actor.tenant_id), str(actor.workspace_id), str(work_item_id)
    )
    return success(data, _trace_id(request))


@router.get("/review-tasks/{reviewTaskId}/artifact", operation_id="getReviewArtifact")
async def get_review_artifact(
    request: Request,
    review_task_id: Annotated[uuid.UUID, Path(alias="reviewTaskId")],
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.get_review_artifact(
        str(actor.tenant_id), str(actor.workspace_id), str(review_task_id)
    )
    return success(data, _trace_id(request))


@router.get("/review-tasks/{reviewTaskId}/artifact/diff", operation_id="getReviewArtifactDiff")
async def get_review_artifact_diff(
    request: Request,
    review_task_id: Annotated[uuid.UUID, Path(alias="reviewTaskId")],
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.get_review_artifact_diff(
        str(actor.tenant_id), str(actor.workspace_id), str(review_task_id)
    )
    return success(data, _trace_id(request))


@router.post("/work-items", status_code=status.HTTP_201_CREATED, operation_id="createWorkItem")
async def create_work_item(
    request: Request,
    payload: WorkItemCreate,
    actor: Actor,
) -> dict[str, Any]:
    _require_workspace(actor, payload.workspaceId)
    data = await planning_workflow_service.create_work_item(
        str(actor.tenant_id),
        str(actor.actor_id),
        actor.capabilities,
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "工作项已创建")


@router.get("/review-tasks", operation_id="listReviewTasks")
async def list_review_tasks(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
    assignee_id: Annotated[uuid.UUID | None, Query(alias="assigneeId")] = None,
    status_filter: ReviewTaskStatusQuery = Query(default=None, alias="status"),
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_review_tasks(
        str(actor.tenant_id),
        str(workspace_id),
        assignee_id=str(assignee_id) if assignee_id else None,
        status=status_filter,
    )
    return success(data, _trace_id(request))


@router.post("/review-tasks", status_code=status.HTTP_201_CREATED, operation_id="createReviewTask")
async def create_review_task(
    request: Request,
    payload: ReviewTaskCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.create_review_task(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.capabilities,
        idempotency_key,
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "审核任务已创建")


@router.get("/review-tasks/{reviewTaskId}", operation_id="getReviewTask")
async def get_review_task(
    request: Request,
    review_task_id: Annotated[uuid.UUID, Path(alias="reviewTaskId")],
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.get_review_task(
        str(actor.tenant_id), str(actor.workspace_id), str(review_task_id)
    )
    return success(data, _trace_id(request))


@router.post("/review-tasks/{reviewTaskId}/decisions", operation_id="decideReviewTask")
async def decide_review_task(
    request: Request,
    review_task_id: Annotated[uuid.UUID, Path(alias="reviewTaskId")],
    payload: ReviewDecisionCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.decide_review(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.actor_type,
        actor.capabilities,
        str(review_task_id),
        idempotency_key,
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "审核决定已记录")


@router.post("/work-items/{workItemId}/transitions", operation_id="transitionWorkItem")
async def transition_work_item(
    request: Request,
    work_item_id: Annotated[uuid.UUID, Path(alias="workItemId")],
    payload: WorkItemTransition,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.transition_work_item(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.capabilities,
        str(work_item_id),
        idempotency_key,
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "工作项状态已迁移")


@router.post(
    "/test-strategies/{testStrategyId}/versions",
    status_code=status.HTTP_201_CREATED,
    operation_id="createTestStrategyVersion",
)
async def create_test_strategy_version(
    request: Request,
    strategy_id: Annotated[uuid.UUID, Path(alias="testStrategyId")],
    payload: TestStrategyVersionCreate,
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.create_strategy_version(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.capabilities,
        str(strategy_id),
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "测试策略新版本已提交并自动创建审核任务")


@router.post(
    "/test-plans/{testPlanId}/versions",
    status_code=status.HTTP_201_CREATED,
    operation_id="createTestPlanVersion",
)
async def create_test_plan_version(
    request: Request,
    plan_id: Annotated[uuid.UUID, Path(alias="testPlanId")],
    payload: TestPlanVersionCreate,
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.create_plan_version(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.capabilities,
        str(plan_id),
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "测试计划新版本已提交并自动创建审核任务")


@router.post(
    "/test-strategies/{testStrategyId}/versions/{versionId}/publish",
    operation_id="publishTestStrategyVersion",
)
async def publish_test_strategy_version(
    request: Request,
    strategy_id: Annotated[uuid.UUID, Path(alias="testStrategyId")],
    version_id: Annotated[uuid.UUID, Path(alias="versionId")],
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    """WP-05 切片一：仅 APPROVED 版本可发布（APPROVED → PUBLISHED），发布是审核通过后的 Owner 命令。"""
    data = await planning_workflow_service.publish_strategy_version(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.actor_type,
        actor.capabilities,
        str(strategy_id),
        str(version_id),
        idempotency_key,
    )
    return success(data, _trace_id(request), "测试策略版本已发布")


@router.post(
    "/test-plans/{testPlanId}/versions/{versionId}/publish",
    operation_id="publishTestPlanVersion",
)
async def publish_test_plan_version(
    request: Request,
    plan_id: Annotated[uuid.UUID, Path(alias="testPlanId")],
    version_id: Annotated[uuid.UUID, Path(alias="versionId")],
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    """WP-05 切片一：仅 APPROVED 版本可发布（APPROVED → PUBLISHED），发布是审核通过后的 Owner 命令。"""
    data = await planning_workflow_service.publish_plan_version(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.actor_type,
        actor.capabilities,
        str(plan_id),
        str(version_id),
        idempotency_key,
    )
    return success(data, _trace_id(request), "测试计划版本已发布")


@router.post(
    "/test-cases/{testCaseId}/versions/{versionId}/publish",
    operation_id="publishTestCaseVersion",
)
async def publish_test_case_version(
    request: Request,
    test_case_id: Annotated[uuid.UUID, Path(alias="testCaseId")],
    version_id: Annotated[uuid.UUID, Path(alias="versionId")],
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    """WP-05 切片一：仅 APPROVED 版本可发布；正式执行只选 PUBLISHED 版本。"""
    data = await planning_workflow_service.publish_test_case_version(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.actor_type,
        actor.capabilities,
        str(test_case_id),
        str(version_id),
        idempotency_key,
    )
    return success(data, _trace_id(request), "测试用例版本已发布")


@router.get("/ai/provider/status", operation_id="getProviderStatus")
async def get_provider_status(request: Request, actor: Actor) -> dict[str, Any]:
    """批次四十六：Provider 运行状态（回应 autoclaw M-136；全局口径无工作区参数）。"""
    data = await planning_workflow_service.provider_status()
    return success(data, _trace_id(request))


@router.get("/ai/sessions", operation_id="listAgentSessions")
async def list_agent_sessions(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_sessions(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.post(
    "/ai/sessions",
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="createAgentSession",
)
async def create_agent_session(
    request: Request,
    payload: AgentSessionCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    _require_workspace(actor, payload.workspaceId)
    data = await planning_workflow_service.start_session(
        str(actor.tenant_id),
        str(actor.actor_id),
        actor.actor_type,
        actor.capabilities,
        idempotency_key,
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "Agent工作流已运行并暂停等待人工审核")


@router.get("/ai/sessions/{agentSessionId}", operation_id="getAgentSession")
async def get_agent_session(
    request: Request,
    session_id: Annotated[uuid.UUID, Path(alias="agentSessionId")],
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.get_session(str(actor.tenant_id), str(actor.workspace_id), str(session_id))
    return success(data, _trace_id(request))


@router.get("/ai/sessions/{agentSessionId}/trace", operation_id="getAgentSessionTrace")
async def get_agent_session_trace(
    request: Request,
    session_id: Annotated[uuid.UUID, Path(alias="agentSessionId")],
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.get_trace(str(actor.tenant_id), str(actor.workspace_id), str(session_id))
    return success(data, _trace_id(request))


@router.get("/test-strategies", operation_id="listTestStrategies")
async def list_test_strategies(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_strategies(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.get("/test-plans", operation_id="listTestPlans")
async def list_test_plans(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_plans(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.get("/test-cases", operation_id="listTestCases")
async def list_test_cases(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_test_cases(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.get("/test-cases/{testCaseId}/versions", operation_id="listTestCaseVersions")
async def list_test_case_versions(
    request: Request,
    test_case_id: Annotated[uuid.UUID, Path(alias="testCaseId")],
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.list_test_case_versions(
        str(actor.tenant_id), str(actor.workspace_id), str(test_case_id)
    )
    return success(data, _trace_id(request))


# ==================== M3：执行链（createExecutionPlan/startExecutionPlan/查询） ====================


@router.get("/execution-plans", operation_id="listExecutionPlans")
async def list_execution_plans(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_execution_plans(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.post("/execution-plans", status_code=status.HTTP_201_CREATED, operation_id="createExecutionPlan")
async def create_execution_plan(
    request: Request,
    payload: ExecutionPlanCreate,
    actor: Actor,
) -> dict[str, Any]:
    _require_workspace(actor, payload.workspaceId)
    data = await planning_workflow_service.create_execution_plan(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.capabilities,
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "执行计划已创建并冻结首版基线")


@router.post(
    "/execution-plans/{executionPlanId}/runs",
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="startExecutionPlan",
)
async def start_execution_plan(
    request: Request,
    execution_plan_id: Annotated[uuid.UUID, Path(alias="executionPlanId")],
    payload: ExecutionStartRequest,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.start_execution(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.capabilities,
        str(execution_plan_id),
        idempotency_key,
        payload.model_dump(),
    )
    return success(data, _trace_id(request), "执行任务已完成并落不可变证据，等待人工批准")


# ==================== 平台域：环境（批次四十六联调面补齐，契约已有本批补路由） ====================


@router.get("/platform/workspaces/{workspaceId}/environments", operation_id="listEnvironments")
async def list_environments(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Path(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_environments(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.post(
    "/platform/workspaces/{workspaceId}/environments",
    status_code=status.HTTP_201_CREATED,
    operation_id="createEnvironment",
)
async def create_environment(
    request: Request,
    actor: Actor,
    payload: EnvironmentCreate,
    workspace_id: Annotated[uuid.UUID, Path(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.create_environment(
        str(actor.tenant_id), str(actor.workspace_id), actor.capabilities, payload.model_dump()
    )
    return success(data, _trace_id(request), "环境已创建")


@router.get("/execution-tasks", operation_id="listExecutionTasks")
async def list_execution_tasks(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_execution_tasks(str(actor.tenant_id), str(workspace_id))
    return success(data, _trace_id(request))


@router.get("/execution-results", operation_id="listExecutionResults")
async def list_execution_results(
    request: Request,
    actor: Actor,
    execution_task_id: Annotated[uuid.UUID, Query(alias="executionTaskId")],
) -> dict[str, Any]:
    data = await planning_workflow_service.list_execution_results(
        str(actor.tenant_id), str(actor.workspace_id), str(execution_task_id)
    )
    return success(data, _trace_id(request))
