"""Local setup and HttpOnly-cookie authentication endpoints."""

from __future__ import annotations

from contextlib import suppress
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status

from qf.api.dependencies import ActorContext, actor_context
from qf.config import settings
from qf.schemas.auth import LocalSetupCreate, LoginCreate, WorkspaceSwitch
from qf.schemas.common import success
from qf.services.auth_service import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    AuthIdentity,
    IssuedSession,
    auth_service,
)
from qf.services.planning_workflow import DomainError

router = APIRouter(prefix="/api/v1/auth", tags=["LocalAuth"])
Actor = Annotated[ActorContext, Depends(actor_context)]


def _trace_id(request: Request) -> str:
    return str(request.state.trace_id)


def _identity_profile(identity: AuthIdentity) -> dict[str, Any]:
    return {
        "userId": str(identity.actor_id),
        "tenantId": str(identity.tenant_id),
        "workspaceId": str(identity.workspace_id),
        "email": identity.email,
        "actorType": identity.actor_type,
        "capabilities": sorted(identity.capabilities),
    }


def _profile(session: IssuedSession) -> dict[str, Any]:
    return _identity_profile(session.identity)


def _set_session_cookies(response: Response, session: IssuedSession) -> None:
    secure = settings.app_env == "production"
    response.set_cookie(
        ACCESS_COOKIE,
        session.token,
        httponly=True,
        secure=secure,
        samesite="strict",
        max_age=settings.jwt_ttl_seconds,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        session.identity.csrf_token,
        httponly=False,
        secure=secure,
        samesite="strict",
        max_age=settings.jwt_ttl_seconds,
        path="/",
    )


@router.get("/status", operation_id="getLocalAuthStatus")
async def auth_status(request: Request) -> dict[str, Any]:
    profile: dict[str, Any] | None = None
    token = request.cookies.get(ACCESS_COOKIE)
    if token:
        # An expired/restart-invalidated cookie means "log in again", not a
        # failed page request, so status probing remains anonymous and 200.
        with suppress(DomainError):
            profile = _identity_profile(auth_service.authenticate(token))
    return success(
        {
            "setupRequired": auth_service.setup_required(),
            "authenticated": profile is not None,
            "profile": profile,
        },
        _trace_id(request),
    )


@router.post("/setup", status_code=status.HTTP_201_CREATED, operation_id="setupLocalAdmin")
async def setup_local_admin(
    request: Request,
    response: Response,
    payload: LocalSetupCreate,
) -> dict[str, Any]:
    session = auth_service.setup(
        email=str(payload.email),
        password=payload.password,
        tenant_name=payload.tenantName,
        workspace_name=payload.workspaceName,
    )
    _set_session_cookies(response, session)
    return success(_profile(session), _trace_id(request), "本地管理员已创建")


@router.post("/login", operation_id="loginLocalUser")
async def login_local_user(
    request: Request,
    response: Response,
    payload: LoginCreate,
) -> dict[str, Any]:
    client_host = request.client.host if request.client else "local"
    session = auth_service.login(email=str(payload.email), password=payload.password, client_key=client_host)
    _set_session_cookies(response, session)
    return success(_profile(session), _trace_id(request), "登录成功")


@router.post("/switch-workspace", operation_id="switchLocalWorkspace")
async def switch_local_workspace(
    request: Request,
    response: Response,
    payload: WorkspaceSwitch,
    actor: Actor,
) -> dict[str, Any]:
    """WP-01A 专用切换命令：成员关系校验后重签 JWT（不落库、无通用 PATCH）。"""
    session = auth_service.switch_workspace(
        str(actor.actor_id), str(actor.tenant_id), str(payload.workspaceId)
    )
    _set_session_cookies(response, session)
    return success(_profile(session), _trace_id(request), "已切换工作区")


@router.get("/me", operation_id="getCurrentLocalUser")
async def current_local_user(request: Request, actor: Actor) -> dict[str, Any]:
    return success(
        {
            "userId": str(actor.actor_id),
            "tenantId": str(actor.tenant_id),
            "workspaceId": str(actor.workspace_id),
            "email": actor.email,
            "actorType": actor.actor_type,
            "capabilities": sorted(actor.capabilities),
        },
        _trace_id(request),
    )


@router.post("/logout", operation_id="logoutLocalUser")
async def logout_local_user(request: Request, response: Response, actor: Actor) -> dict[str, Any]:
    del actor
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return success({"loggedOut": True}, _trace_id(request), "已退出登录")
