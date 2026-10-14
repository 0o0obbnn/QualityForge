"""Verified JWT identity and CSRF enforcement for protected APIs."""

from __future__ import annotations

import hmac
import uuid
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Header, Request

from qf.services.auth_service import ACCESS_COOKIE, CSRF_COOKIE, auth_service
from qf.services.planning_workflow import DomainError

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass(frozen=True, slots=True)
class ActorContext:
    tenant_id: uuid.UUID
    actor_id: uuid.UUID
    actor_type: Literal["USER", "AGENT", "SERVICE"]
    workspace_id: uuid.UUID
    email: str
    capabilities: frozenset[str]


async def actor_context(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> ActorContext:
    """Verify Bearer/cookie JWT and re-check current SQLite membership."""
    token: str | None = None
    cookie_authenticated = False
    if authorization:
        scheme, separator, credential = authorization.partition(" ")
        if separator and scheme.casefold() == "bearer" and credential:
            token = credential
    if token is None:
        token = request.cookies.get(ACCESS_COOKIE)
        cookie_authenticated = token is not None
    if token is None:
        raise DomainError(401, "UNAUTHORIZED", "请先登录")

    identity = auth_service.authenticate(token)
    if cookie_authenticated and request.method.upper() not in SAFE_METHODS:
        csrf_cookie = request.cookies.get(CSRF_COOKIE)
        if (
            not csrf_header
            or not csrf_cookie
            or not hmac.compare_digest(csrf_header, csrf_cookie)
            or not hmac.compare_digest(csrf_header, identity.csrf_token)
        ):
            raise DomainError(403, "CSRF_VALIDATION_FAILED", "请求安全校验失败")
    return ActorContext(
        tenant_id=identity.tenant_id,
        actor_id=identity.actor_id,
        actor_type=identity.actor_type,
        workspace_id=identity.workspace_id,
        email=identity.email,
        capabilities=identity.capabilities,
    )
