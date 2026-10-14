"""Request schemas for the local setup and login flow."""

import uuid

from pydantic import EmailStr, Field

from qf.schemas.planning import StrictRequest


class LocalSetupCreate(StrictRequest):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    tenantName: str = Field(min_length=1, max_length=120)
    workspaceName: str = Field(min_length=1, max_length=120)


class LoginCreate(StrictRequest):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class WorkspaceSwitch(StrictRequest):
    """WP-01A 切换工作区命令：目标工作区必须属于当前成员关系。"""

    workspaceId: uuid.UUID
