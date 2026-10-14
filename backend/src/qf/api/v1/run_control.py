"""WP-04 运行命令路由（39 号 §5 切片一，批次五十八）。

实装 commandAgentSession / commandExecutionTask / getRunCommandReceipt 三 op；
命令只追加，内嵌回执（CommandReceipt）是生效唯一事实。
RETRY/AUTHORIZE/REVOKE 契约枚举保留、运行时 422 显式拒绝。
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Path, Query, Request, status

from qf.api.dependencies import ActorContext, actor_context
from qf.schemas.collaboration import (
    BudgetPolicyUpdate,
    RunCommandCreate,
    RuntimeAuthorizationCreate,
)
from qf.schemas.common import success
from qf.services.planning_workflow import DomainError, planning_workflow_service

router = APIRouter(prefix="/api/v1", tags=["RunControl"])
Actor = Annotated[ActorContext, Depends(actor_context)]


def _trace_id(request: Request) -> str:
    return str(request.state.trace_id)


def _require_workspace(actor: ActorContext, workspace_id: uuid.UUID) -> None:
    if workspace_id != actor.workspace_id:
        raise DomainError(403, "FORBIDDEN", "当前身份无权访问该Workspace")


@router.post(
    "/ai/sessions/{agentSessionId}/commands",
    status_code=status.HTTP_201_CREATED,
    operation_id="commandAgentSession",
)
async def command_agent_session(
    request: Request,
    agent_session_id: Annotated[uuid.UUID, Path(alias="agentSessionId")],
    payload: RunCommandCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.issue_run_command(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        str(actor.actor_type),
        actor.capabilities,
        idempotency_key,
        "AGENT_SESSION",
        str(agent_session_id),
        payload.model_dump(mode="json"),
    )
    return success(data, _trace_id(request), "命令已生效")


@router.post(
    "/execution-tasks/{executionTaskId}/commands",
    status_code=status.HTTP_201_CREATED,
    operation_id="commandExecutionTask",
)
async def command_execution_task(
    request: Request,
    execution_task_id: Annotated[uuid.UUID, Path(alias="executionTaskId")],
    payload: RunCommandCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.issue_run_command(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        str(actor.actor_type),
        actor.capabilities,
        idempotency_key,
        "EXECUTION_TASK",
        str(execution_task_id),
        payload.model_dump(mode="json"),
    )
    return success(data, _trace_id(request), "命令已生效")


@router.get("/run-commands/{runCommandId}", operation_id="getRunCommandReceipt")
async def get_run_command_receipt(
    request: Request,
    run_command_id: Annotated[uuid.UUID, Path(alias="runCommandId")],
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.get_run_command(str(actor.tenant_id), str(workspace_id), str(run_command_id))
    return success(data, _trace_id(request))


@router.get("/work-items/{workItemId}/authorizations", operation_id="listRuntimeAuthorizations")
async def list_runtime_authorizations(
    request: Request,
    work_item_id: Annotated[uuid.UUID, Path(alias="workItemId")],
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_runtime_authorizations(
        str(actor.tenant_id), str(workspace_id), str(work_item_id)
    )
    return success(data, _trace_id(request))


@router.post(
    "/work-items/{workItemId}/authorizations",
    status_code=status.HTTP_201_CREATED,
    operation_id="createRuntimeAuthorization",
)
async def create_runtime_authorization(
    request: Request,
    work_item_id: Annotated[uuid.UUID, Path(alias="workItemId")],
    payload: RuntimeAuthorizationCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.create_runtime_authorization(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        str(actor.actor_type),
        actor.capabilities,
        idempotency_key,
        str(work_item_id),
        payload.model_dump(mode="json"),
    )
    return success(data, _trace_id(request), "授权决定已记录")


@router.get("/work-items/{workItemId}/budgets", operation_id="getWorkItemBudget")
async def get_work_item_budget(
    request: Request,
    work_item_id: Annotated[uuid.UUID, Path(alias="workItemId")],
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.get_work_item_budget(
        str(actor.tenant_id), str(workspace_id), str(work_item_id)
    )
    return success(data, _trace_id(request))


@router.post("/work-items/{workItemId}/budgets", operation_id="updateWorkItemBudget")
async def update_work_item_budget(
    request: Request,
    work_item_id: Annotated[uuid.UUID, Path(alias="workItemId")],
    payload: BudgetPolicyUpdate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.update_work_item_budget(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        str(actor.actor_type),
        actor.capabilities,
        idempotency_key,
        str(work_item_id),
        payload.model_dump(mode="json"),
    )
    return success(data, _trace_id(request), "预算已更新")


@router.get("/runs/{targetType}/{targetId}/checkpoints", operation_id="listRunCheckpoints")
async def list_run_checkpoints(
    request: Request,
    target_type: Annotated[str, Path(alias="targetType")],
    target_id: Annotated[uuid.UUID, Path(alias="targetId")],
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_run_checkpoints(
        str(actor.tenant_id), str(workspace_id), target_type, str(target_id)
    )
    return success(data, _trace_id(request))
