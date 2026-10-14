"""M3 执行链请求/响应模型（契约 32 号 ExecutionPlanCreate/ExecutionStartRequest/ExecutionResult）。

ExecutionResult 字段与产品域模型 04 §7.2 及契约 32 号 ExecutionResult 对齐：
resultDigest / assertionResultsRef 均由服务端计算与落库，客户端不可注入。
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from qf.schemas.planning import StrictRequest


class ExecutionPlanCreate(StrictRequest):
    workspaceId: uuid.UUID
    planKey: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=256)
    testPlanId: uuid.UUID


class ExecutionStartRequest(StrictRequest):
    executionPlanVersionId: uuid.UUID


class ExecutionResult(BaseModel):
    """执行结果响应模型（B1：补 resultDigest / assertionResultsRef 三层一致）。

    只读响应对象：extra=forbid 让字段漂移在测试期即暴露，杜绝静默不一致。
    """

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenantId: uuid.UUID
    workspaceId: uuid.UUID
    executionTaskId: uuid.UUID
    testCaseVersionId: uuid.UUID
    status: Literal["PASSED", "FAILED", "SKIPPED", "ERROR", "INCONCLUSIVE"]
    durationMs: int
    logRef: str
    evidenceDigest: str = Field(pattern=r"^[a-f0-9]{64}$")
    resultDigest: str = Field(pattern=r"^[a-f0-9]{64}$")
    assertionResultsRef: str
    createdAt: str
