"""Observability slice：领域事件流与受控指标（D3/O3 裁决承载面）。

只读双面：GET /observability/events（listEvents）与 GET /observability/metrics
（listMetrics）；无客户端写入面（事件由服务端独占生成，防伪基线 AC-04）。
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from qf.api.dependencies import ActorContext, actor_context
from qf.schemas.common import success_paged
from qf.services.metrics import compute_metrics
from qf.services.planning_workflow import DomainError, planning_workflow_service

router = APIRouter(prefix="/api/v1", tags=["Observability"])
Actor = Annotated[ActorContext, Depends(actor_context)]


def _trace_id(request: Request) -> str:
    return str(request.state.trace_id)


def _require_workspace(actor: ActorContext, workspace_id: uuid.UUID) -> None:
    if workspace_id != actor.workspace_id:
        raise DomainError(403, "FORBIDDEN", "当前身份无权访问该Workspace")


@router.get("/observability/events", operation_id="listEvents")
async def list_events(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
    subject_type: Annotated[str | None, Query(alias="subjectType")] = None,
    event_type: Annotated[str | None, Query(alias="eventType")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    items, total = planning_workflow_service.events.list_events(
        str(workspace_id),
        subject_type=subject_type,
        event_type=event_type,
        page=page,
        page_size=page_size,
    )
    return success_paged(items, _trace_id(request), page=page, page_size=page_size, total=total)


@router.get("/observability/metrics", operation_id="listMetrics")
async def list_metrics(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    planning_workflow_service.events.verify_chain()
    items = compute_metrics(planning_workflow_service, str(workspace_id))
    return success_paged(items, _trace_id(request), page=1, page_size=len(items), total=len(items))
