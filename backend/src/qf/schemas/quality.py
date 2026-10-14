"""M4 质量域请求模型（契约 32 号 Quality/Knowledge Create schemas）。"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import Field

from qf.schemas.planning import StrictRequest


class ResultAnalysisCreate(StrictRequest):
    workspaceId: uuid.UUID
    releaseId: uuid.UUID
    analysisKey: str = Field(min_length=1, max_length=120)
    executionResultRefs: list[uuid.UUID] = Field(min_length=1)


class DefectCreate(StrictRequest):
    workspaceId: uuid.UUID
    releaseId: uuid.UUID
    defectKey: str = Field(min_length=1, max_length=120)
    createdFromWorkItemId: uuid.UUID


class DefectVersionCreate(StrictRequest):
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1)
    preconditions: list[str] | None = None
    reproductionSteps: list[dict[str, Any]] | None = None
    expectedResult: str = Field(min_length=1)
    actualResult: str = Field(min_length=1)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    priority: Literal["P0", "P1", "P2", "P3"]
    defectType: Literal[
        "PRODUCT", "SCRIPT", "ENVIRONMENT", "DATA", "SECURITY", "PERFORMANCE", "USABILITY", "OTHER"
    ]
    environmentSnapshotRef: str = Field(min_length=1, max_length=256)
    affectedReleaseIds: list[uuid.UUID] = Field(min_length=1)
    evidence: list[dict[str, Any]] = Field(min_length=1)


class DefectSyncAttemptCreate(StrictRequest):
    defectVersionId: uuid.UUID
    integrationId: uuid.UUID
    externalDefectLinkId: uuid.UUID | None = None
    operation: Literal["CREATE", "UPDATE", "COMMENT", "TRANSITION", "ATTACH", "LINK"]
    payload: dict[str, Any] | None = None  # writeOnly：仅用于摘要校验，不落库不回显
    payloadDigest: str = Field(min_length=64, max_length=64)
    approvalId: uuid.UUID


class TestReportCreate(StrictRequest):
    # P0-1 裁决：根层仅承载身份；scopeSnapshotRef/executionSnapshotRef 下沉版本层
    workspaceId: uuid.UUID
    releaseId: uuid.UUID
    reportKey: str = Field(min_length=1, max_length=120)


class TestReportVersionCreate(StrictRequest):
    # version/contentDigest/reviewStatus/supersedesVersionId 服务端产出，不在请求体
    scopeSnapshotRef: str = Field(min_length=1, max_length=256)
    executionSnapshotRef: str = Field(min_length=1, max_length=256)
    coverageReportRefs: list[uuid.UUID] | None = None
    defectVersionRefs: list[uuid.UUID] | None = None
    riskSummary: dict[str, Any] | None = None
    residualRisks: list[dict[str, Any]] | None = None
    qualityConclusion: str = Field(min_length=1)
    changeSummary: str = Field(min_length=1)


class CoverageReportCreate(StrictRequest):
    workspaceId: uuid.UUID
    releaseId: uuid.UUID
    denominatorDefinitionRef: Literal["INSTANCE", "DESIGN", "EXECUTABLE", "EFFECTIVE", "HUMAN_ACCEPTANCE"]
    scopeSnapshotRef: str = Field(min_length=1, max_length=256)
    ruleDimension: dict[str, Any] | None = None
    scenarioDimension: dict[str, Any] | None = None
    stateDimension: dict[str, Any] | None = None
    assertionDimension: dict[str, Any] | None = None
    apiDimension: dict[str, Any] | None = None


class KnowledgeEntryCreate(StrictRequest):
    workspaceId: uuid.UUID
    knowledgeKey: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=120)
