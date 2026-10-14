"""WP-03 协作对话路由（39 号 §3 最小切片，批次五十四）。

本切片实现契约 11 op 中的 4 个：listConversations / createConversation /
listConversationMessages / createConversationMessage。消息两面按契约不带
workspaceId 参数，工作区取 actor 绑定（资源型端点口径，随切换命令生效）。
澄清、任务卡与 AgentPlan 归后续切片。
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Path, Query, Request, status

from qf.api.dependencies import ActorContext, actor_context
from qf.schemas.collaboration import (
    AgentPlanCreate,
    AgentPlanDecisionCreate,
    ClarificationResponseCreate,
    ConversationCreate,
    ConversationMessageCreate,
    TaskCardCreate,
)
from qf.schemas.common import success
from qf.services.planning_workflow import DomainError, planning_workflow_service

router = APIRouter(prefix="/api/v1", tags=["Collaboration"])
Actor = Annotated[ActorContext, Depends(actor_context)]


def _trace_id(request: Request) -> str:
    return str(request.state.trace_id)


def _require_workspace(actor: ActorContext, workspace_id: uuid.UUID) -> None:
    if workspace_id != actor.workspace_id:
        raise DomainError(403, "FORBIDDEN", "当前身份无权访问该Workspace")


@router.get("/conversations", operation_id="listConversations")
async def list_conversations(
    request: Request,
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
    release_id: Annotated[uuid.UUID | None, Query(alias="releaseId")] = None,
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_conversations(
        str(actor.tenant_id), str(workspace_id), release_id=str(release_id) if release_id else None
    )
    return success(data, _trace_id(request))


@router.post("/conversations", status_code=status.HTTP_201_CREATED, operation_id="createConversation")
async def create_conversation(
    request: Request,
    payload: ConversationCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    _require_workspace(actor, payload.workspaceId)
    data = await planning_workflow_service.create_conversation(
        str(actor.tenant_id),
        str(actor.actor_id),
        actor.capabilities,
        idempotency_key,
        payload.model_dump(mode="json"),
    )
    return success(data, _trace_id(request), "会话已创建")


@router.get("/conversations/{conversationId}/messages", operation_id="listConversationMessages")
async def list_conversation_messages(
    request: Request,
    conversation_id: Annotated[uuid.UUID, Path(alias="conversationId")],
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.list_conversation_messages(
        str(actor.tenant_id), str(actor.workspace_id), str(conversation_id)
    )
    return success(data, _trace_id(request))


@router.post(
    "/conversations/{conversationId}/messages",
    status_code=status.HTTP_201_CREATED,
    operation_id="createConversationMessage",
)
async def create_conversation_message(
    request: Request,
    conversation_id: Annotated[uuid.UUID, Path(alias="conversationId")],
    payload: ConversationMessageCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.create_conversation_message(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        str(actor.actor_type),
        actor.capabilities,
        str(conversation_id),
        idempotency_key,
        payload.model_dump(mode="json"),
    )
    return success(data, _trace_id(request), "消息已追加")


@router.get(
    "/ai/sessions/{agentSessionId}/clarifications", operation_id="listClarificationRequests"
)
async def list_clarification_requests(
    request: Request,
    agent_session_id: Annotated[uuid.UUID, Path(alias="agentSessionId")],
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_clarification_requests(
        str(actor.tenant_id), str(workspace_id), str(agent_session_id)
    )
    return success(data, _trace_id(request))


@router.post(
    "/clarifications/{clarificationId}/responses",
    status_code=status.HTTP_201_CREATED,
    operation_id="respondClarification",
)
async def respond_clarification(
    request: Request,
    clarification_id: Annotated[uuid.UUID, Path(alias="clarificationId")],
    payload: ClarificationResponseCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.respond_clarification(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        str(actor.actor_type),
        actor.capabilities,
        str(clarification_id),
        idempotency_key,
        payload.model_dump(mode="json"),
    )
    return success(data, _trace_id(request), "澄清已答复")


@router.get("/work-items/{workItemId}/task-cards", operation_id="listTaskCards")
async def list_task_cards(
    request: Request,
    work_item_id: Annotated[uuid.UUID, Path(alias="workItemId")],
    actor: Actor,
) -> dict[str, Any]:
    data = await planning_workflow_service.list_task_cards(
        str(actor.tenant_id), str(actor.workspace_id), str(work_item_id)
    )
    return success(data, _trace_id(request))


@router.post(
    "/work-items/{workItemId}/task-cards", status_code=status.HTTP_201_CREATED, operation_id="createTaskCard"
)
async def create_task_card(
    request: Request,
    work_item_id: Annotated[uuid.UUID, Path(alias="workItemId")],
    payload: TaskCardCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.create_task_card(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        actor.capabilities,
        idempotency_key,
        str(work_item_id),
        payload.model_dump(mode="json"),
    )
    return success(data, _trace_id(request), "任务卡已固化")


@router.get("/work-items/{workItemId}/agent-plans", operation_id="listAgentPlans")
async def list_agent_plans(
    request: Request,
    work_item_id: Annotated[uuid.UUID, Path(alias="workItemId")],
    actor: Actor,
    workspace_id: Annotated[uuid.UUID, Query(alias="workspaceId")],
) -> dict[str, Any]:
    _require_workspace(actor, workspace_id)
    data = await planning_workflow_service.list_agent_plans(
        str(actor.tenant_id), str(workspace_id), str(work_item_id)
    )
    return success(data, _trace_id(request))


@router.post(
    "/work-items/{workItemId}/agent-plans", status_code=status.HTTP_201_CREATED, operation_id="createAgentPlan"
)
async def create_agent_plan(
    request: Request,
    work_item_id: Annotated[uuid.UUID, Path(alias="workItemId")],
    payload: AgentPlanCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.create_agent_plan(
        str(actor.tenant_id),
        str(actor.workspace_id),
        actor.capabilities,
        idempotency_key,
        str(work_item_id),
        payload.model_dump(mode="json"),
    )
    return success(data, _trace_id(request), "计划已生成，待人工裁决")


@router.post(
    "/agent-plans/{agentPlanId}/decisions",
    status_code=status.HTTP_201_CREATED,
    operation_id="decideAgentPlan",
)
async def decide_agent_plan(
    request: Request,
    plan_id: Annotated[uuid.UUID, Path(alias="agentPlanId")],
    payload: AgentPlanDecisionCreate,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> dict[str, Any]:
    data = await planning_workflow_service.decide_agent_plan(
        str(actor.tenant_id),
        str(actor.workspace_id),
        str(actor.actor_id),
        str(actor.actor_type),
        actor.capabilities,
        idempotency_key,
        str(plan_id),
        payload.model_dump(mode="json"),
    )
    return success(data, _trace_id(request), "计划已裁决")
