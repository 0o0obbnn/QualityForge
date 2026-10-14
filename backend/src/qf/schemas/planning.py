"""Validated request DTOs for the Gate 0 planning vertical slice."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictRequest(BaseModel):
    """Reject unknown fields so typos cannot silently alter workflow intent."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RequirementDocumentCreate(StrictRequest):
    workspaceId: uuid.UUID
    name: str = Field(min_length=1, max_length=256)
    documentType: str = Field(min_length=1, max_length=50)


class RequirementDocumentVersionCreate(StrictRequest):
    sourceSnapshotId: uuid.UUID
    contentDigest: str = Field(pattern=r"^[a-f0-9]{64}$")
    content: str = Field(min_length=1, max_length=200_000)
    changeSummary: str | None = Field(default=None, max_length=2_000)


class WorkItemCreate(StrictRequest):
    workspaceId: uuid.UUID
    releaseId: uuid.UUID | None = None
    workItemType: Literal["STRATEGY", "PLAN", "CASE", "GENERAL"]
    title: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=4_000)
    # QF-REQ-001 四源对齐：契约 WorkItemCreate required 六字段（32 号 L840）
    objective: str = Field(min_length=1, max_length=4_000)
    acceptanceCriteria: str = Field(min_length=1, max_length=8_000)
    requiresReview: bool
    constraints: str | None = Field(default=None, max_length=4_000)
    agentId: uuid.UUID | None = None
    priority: Literal["P0", "P1", "P2", "P3"]
    riskLevel: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class AgentSessionCreate(StrictRequest):
    workspaceId: uuid.UUID
    workItemId: uuid.UUID
    workflowKey: Literal["gate0-planning-slice"]
    requirementVersionId: uuid.UUID
    releaseId: uuid.UUID
    ownerId: uuid.UUID


class ReviewDecisionCreate(StrictRequest):
    decision: Literal["APPROVE", "REQUEST_CHANGES", "REJECT"]
    contentDigest: str = Field(pattern=r"^[a-f0-9]{64}$")
    comments: str | None = Field(default=None, max_length=4_000)
    signature: str | None = Field(default=None, max_length=8_000)


# M2：手工创建审核任务（分派入口，契约 32 号 ReviewTaskCreate）
class ReviewTaskAssignee(StrictRequest):
    userId: uuid.UUID
    reviewRole: Literal["REVIEWER", "APPROVER"]
    requiredCapability: str = Field(min_length=1, max_length=120)


class ReviewTaskCreate(StrictRequest):
    workItemId: uuid.UUID
    artifactType: Literal["TEST_STRATEGY", "TEST_PLAN", "TEST_CASE"]
    artifactId: uuid.UUID
    artifactVersionId: uuid.UUID
    contentDigest: str = Field(pattern=r"^[a-f0-9]{64}$")
    policyType: Literal[
        "SINGLE_REVIEW", "FOUR_EYES", "CODE_REVIEW", "EXTERNAL_WRITE", "REPORT_SIGNOFF", "KNOWLEDGE_PUBLISH"
    ]
    assignees: list[ReviewTaskAssignee] = Field(default_factory=list, max_length=16)


# M2：工作项分派（32 号 WorkItemAssignRequest；assigneeId 必填，天然幂等：同人重分派为 no-op）
class WorkspacePin(StrictRequest):
    """WP-01 常用项目置顶命令体。"""

    pinned: bool


class WorkItemAssignRequest(StrictRequest):
    workspaceId: uuid.UUID
    assigneeId: uuid.UUID


# 批次四十六：环境创建（契约 32 号 EnvironmentCreate；workspaceId 取自路径参数不在请求体）
class EnvironmentCreate(StrictRequest):
    name: str = Field(min_length=1, max_length=120)
    environmentType: str = Field(min_length=1, max_length=50)
    endpointMappings: dict[str, Any]
    capabilities: dict[str, Any] | None = None
    secretRefs: list[uuid.UUID] | None = None


# M1-B1：WorkItemTransition 契约（32 号 WorkItemTransition；targetStatus 切片子集仅 REWORK）
class WorkItemTransition(StrictRequest):
    targetStatus: Literal["REWORK"]
    reason: str = Field(min_length=1, max_length=2_000)
    expectedCurrentStatus: Literal[
        "BACKLOG", "READY", "IN_PROGRESS", "PENDING_REVIEW", "REWORK", "APPROVED", "BLOCKED", "DONE", "CANCELLED"
    ] | None = None
    lockVersion: int = Field(ge=0)


# M1-B1：退回→新版本闭环（契约 32 号 TestStrategyVersionCreate/TestPlanVersionCreate；
# 切片 DTO 增加长度/格式约束而契约未约束，口径差异见台账 QF-REQ-080）
class TestStrategyVersionCreate(StrictRequest):
    objective: str = Field(min_length=1, max_length=4_000)
    inScope: list[str]
    outOfScope: list[str]
    riskAssessment: list[dict[str, Any]]
    testTypes: list[str]
    approach: str = Field(min_length=1, max_length=4_000)
    entryCriteria: list[str]
    exitCriteria: list[str]
    environmentStrategy: str = Field(min_length=1, max_length=4_000)
    dataStrategy: str = Field(min_length=1, max_length=4_000)
    automationStrategy: str = Field(min_length=1, max_length=4_000)
    defectStrategy: str = Field(min_length=1, max_length=4_000)
    changeSummary: str | None = Field(default=None, max_length=2_000)


class TestPlanVersionCreate(StrictRequest):
    strategyVersionId: uuid.UUID
    objective: str = Field(min_length=1, max_length=4_000)
    planType: str = Field(min_length=1, max_length=80)
    scope: dict[str, Any]
    ownerId: uuid.UUID
    startDate: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    endDate: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    milestones: list[dict[str, Any]]
    resourceRequirements: dict[str, Any]
    acceptanceCriteria: list[str]
    changeSummary: str | None = Field(default=None, max_length=2_000)


class ApiData(BaseModel):
    """Typed marker for response model generation without accepting unknown input."""

    model_config = ConfigDict(extra="allow")

    data: dict[str, Any]
