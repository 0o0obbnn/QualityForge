"""Local JWT authentication backed by the same service-free SQLite file."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast

import jwt

from qf.config import settings
from qf.db.sqlite_store import SQLiteWorkflowStore
from qf.services.planning_workflow import DomainError

ACCESS_COOKIE = "qf_access"
CSRF_COOKIE = "qf_csrf"
ALL_LOCAL_CAPABILITIES = [
    "requirement.write",
    "work_item.create",
    "work_item.transition",
    "work_item.assign",
    "workflow.start",
    "review.create",
    "execution.start",
    "evidence.approve",
    # M4：质量域（分析/缺陷/报告/覆盖率）+ 外部同步 + 缺陷版本批准 + 知识回流
    "quality.write",
    "quality.sync",
    "artifact.defect_version.approve",
    "knowledge.publish",
    "artifact.test_strategy.approve",
    "artifact.test_strategy.submit",
    "artifact.test_plan.approve",
    "artifact.test_plan.submit",
    "artifact.test_case.approve",
    # WP-05 切片一：资产发布链（批次六十四；publishAutomationScriptVersion/publishKnowledgeCandidate
    # 上游 create 面未实现，能力键随其实现切片登记）
    "artifact.test_strategy.publish",
    "artifact.test_plan.publish",
    "artifact.test_case.publish",
    # P0-1 裁决闭合：测试报告版本批准（对齐 defect_version 审核链）
    "artifact.test_report_version.approve",
    # 批次四十六：平台域环境创建（前端真实模式联调面补齐）
    "environment.create",
    # WP-01：常用项目置顶 + Release 归档（批次五十二）
    "workspace.pin",
    "release.archive",
    # WP-03：协作对话（批次五十四）
    "conversation.write",
    "conversation.read",
    # WP-03 切片二：澄清（raise 仅 AGENT/SERVICE 角色面，USER 由角色门拒绝）
    "clarification.raise",
    "clarification.respond",
    # WP-03 切片三：任务卡与 AgentPlan
    "task_card.create",
    "task_card.read",
    "agent_plan.create",
    "agent_plan.read",
    "agent_plan.decide",
    # WP-04 切片一：运行命令
    "run_command.issue",
    "run_command.read",
    # WP-04 切片二：授权 / 预算 / 检查点
    "runtime_authorization.read",
    "runtime_authorization.manage",
    "budget.read",
    "budget.manage",
    "checkpoint.read",
]
PASSWORD_N = 2**14
PASSWORD_R = 8
PASSWORD_P = 1
LOGIN_WINDOW_SECONDS = 60
LOGIN_MAX_ATTEMPTS = 5


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    tenant_id: uuid.UUID
    actor_id: uuid.UUID
    actor_type: Literal["USER", "AGENT", "SERVICE"]
    workspace_id: uuid.UUID
    email: str
    capabilities: frozenset[str]
    csrf_token: str


@dataclass(frozen=True, slots=True)
class IssuedSession:
    identity: AuthIdentity
    token: str


def _now() -> datetime:
    return datetime.now(UTC)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=PASSWORD_N, r=PASSWORD_R, p=PASSWORD_P)
    return f"scrypt${PASSWORD_N}${PASSWORD_R}${PASSWORD_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_unb64(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(_unb64(expected)),
        )
        return hmac.compare_digest(actual, _unb64(expected))
    except (ValueError, TypeError):
        return False


class AuthService:
    """Create the first local user, sign JWTs and re-check membership per request."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._store = SQLiteWorkflowStore(db_path or settings.sqlite_path)
        self._signing_key = secrets.token_bytes(32)
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def reconfigure(self, db_path: str) -> None:
        self._store = SQLiteWorkflowStore(Path(db_path))
        self._signing_key = secrets.token_bytes(32)
        self._attempts.clear()

    def reset_for_tests(self) -> None:
        self._store.clear_auth()
        self._signing_key = secrets.token_bytes(32)
        self._attempts.clear()

    def setup_required(self) -> bool:
        return self._store.auth_user_count() == 0

    def setup(
        self,
        *,
        email: str,
        password: str,
        tenant_name: str,
        workspace_name: str,
    ) -> IssuedSession:
        if not self.setup_required():
            raise DomainError(409, "SETUP_ALREADY_COMPLETED", "本地管理员已完成初始化")
        tenant_id = str(uuid.uuid4())
        workspace_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        now = _now().isoformat()
        try:
            self._store.create_initial_identity(
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                workspace_id=workspace_id,
                workspace_name=workspace_name,
                user_id=user_id,
                email=email,
                password_hash=hash_password(password),
                capabilities=ALL_LOCAL_CAPABILITIES,
                created_at=now,
            )
        except ValueError as exc:
            raise DomainError(409, "SETUP_ALREADY_COMPLETED", "本地管理员已完成初始化") from exc
        return self._issue(user_id, tenant_id)

    def login(self, *, email: str, password: str, client_key: str) -> IssuedSession:
        self._enforce_rate_limit(f"{client_key}:{email.casefold()}")
        user = self._store.get_user_by_email(email)
        if user is None or not bool(user["is_active"]) or not verify_password(password, str(user["password_hash"])):
            raise DomainError(401, "INVALID_CREDENTIALS", "邮箱或密码错误")
        membership = self._store.first_membership(str(user["id"]))
        if membership is None:
            raise DomainError(403, "FORBIDDEN", "用户没有有效租户成员资格")
        self._attempts.pop(f"{client_key}:{email.casefold()}", None)
        return self._issue(str(user["id"]), str(membership["tenant_id"]))

    def switch_workspace(self, user_id: str, tenant_id: str, workspace_id: str) -> IssuedSession:
        """WP-01A 专用切换命令：校验目标工作区成员关系后重签 JWT（新 cookie + 新 CSRF）。"""
        membership = self._store.get_membership_for_workspace(user_id, tenant_id, workspace_id)
        if membership is None:
            raise DomainError(403, "FORBIDDEN", "当前身份无权切换到该Workspace")
        return self._issue(user_id, tenant_id, workspace_id)

    def _enforce_rate_limit(self, key: str) -> None:
        now = time.monotonic()
        attempts = self._attempts[key]
        while attempts and attempts[0] <= now - LOGIN_WINDOW_SECONDS:
            attempts.popleft()
        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            raise DomainError(429, "RATE_LIMITED", "登录尝试过多，请稍后再试")
        attempts.append(now)

    def _issue(self, user_id: str, tenant_id: str, workspace_id: str | None = None) -> IssuedSession:
        user = self._store.get_user(user_id)
        if workspace_id is None:
            # WP-01 登录默认工作区：最近置顶的常用项目，未置顶回退首行成员关系
            pinned = self._store.default_workspace_for_user(tenant_id, user_id)
            membership = (
                self._store.get_membership_for_workspace(user_id, tenant_id, pinned)
                if pinned is not None
                else self._store.get_membership(user_id, tenant_id)
            )
        else:
            membership = self._store.get_membership_for_workspace(user_id, tenant_id, workspace_id)
        if user is None or membership is None or not bool(user["is_active"]) or not bool(membership["is_active"]):
            raise DomainError(401, "UNAUTHORIZED", "身份已失效")
        csrf_token = secrets.token_urlsafe(24)
        now = _now()
        payload = {
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "sub": user_id,
            "tenantId": tenant_id,
            "workspaceId": str(membership["workspace_id"]),
            "actorType": membership["actor_type"],
            "csrf": csrf_token,
            "iat": now,
            "exp": now + timedelta(seconds=settings.jwt_ttl_seconds),
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(payload, self._signing_key, algorithm="HS256")
        identity = self._identity(user, membership, csrf_token)
        return IssuedSession(identity=identity, token=token)

    def authenticate(self, token: str) -> AuthIdentity:
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._signing_key,
                algorithms=["HS256"],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer,
                options={"require": ["exp", "iat", "sub", "tenantId", "actorType", "csrf"]},
            )
            user_id = str(payload["sub"])
            tenant_id = str(payload["tenantId"])
            csrf_token = str(payload["csrf"])
        except (jwt.PyJWTError, KeyError, TypeError) as exc:
            raise DomainError(401, "UNAUTHORIZED", "登录状态无效或已过期") from exc
        user = self._store.get_user(user_id)
        claimed_workspace = payload.get("workspaceId")
        if claimed_workspace is not None:
            membership = self._store.get_membership_for_workspace(user_id, tenant_id, str(claimed_workspace))
        else:
            membership = self._store.get_membership(user_id, tenant_id)
        if user is None or membership is None or not bool(user["is_active"]) or not bool(membership["is_active"]):
            raise DomainError(401, "UNAUTHORIZED", "身份或租户成员资格已失效")
        if payload["actorType"] != membership["actor_type"]:
            raise DomainError(401, "UNAUTHORIZED", "身份类型已发生变化")
        return self._identity(user, membership, csrf_token)

    @staticmethod
    def _identity(user: dict[str, Any], membership: dict[str, Any], csrf_token: str) -> AuthIdentity:
        actor_type = cast(Literal["USER", "AGENT", "SERVICE"], membership["actor_type"])
        return AuthIdentity(
            tenant_id=uuid.UUID(str(membership["tenant_id"])),
            actor_id=uuid.UUID(str(user["id"])),
            actor_type=actor_type,
            workspace_id=uuid.UUID(str(membership["workspace_id"])),
            email=str(user["email"]),
            capabilities=frozenset(str(item) for item in membership["capabilities"]),
            csrf_token=csrf_token,
        )


auth_service = AuthService()
