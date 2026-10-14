"""WP-03 协作对话请求 schema（39 号 §3 最小切片，批次五十四）。"""

import uuid

from pydantic import Field, field_validator

from qf.schemas.planning import StrictRequest

DATA_CLASSES = frozenset({"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"})


class ConversationCreate(StrictRequest):
    workspaceId: uuid.UUID
    releaseId: uuid.UUID | None = None
    workItemId: uuid.UUID | None = None
    title: str = Field(default="未命名会话", max_length=200)


class ConversationMessageCreate(StrictRequest):
    messageType: str = Field(min_length=1, max_length=64)
    contentRef: str = Field(min_length=1, max_length=2048)
    contentDigest: str = Field(pattern=r"^[a-f0-9]{64}$")
    dataClass: str

    @field_validator("dataClass")
    @classmethod
    def _data_class_in_enum(cls, value: str) -> str:
        if value not in DATA_CLASSES:
            raise ValueError("dataClass 必须为 PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED")
        return value


class ClarificationResponseCreate(StrictRequest):
    """人工答复澄清（evidenceClass 固定 CONFIRMED，由服务端钉死）。"""

    answerRef: str = Field(min_length=1, max_length=2048)
    answerDigest: str = Field(pattern=r"^[a-f0-9]{64}$")


class TaskCardCreate(StrictRequest):
    """固化正式任务输入（提交即 SUBMITTED，后续变更走新版本取代）。"""

    conversationId: uuid.UUID | None = None
    releaseId: uuid.UUID | None = None
    objective: str = Field(min_length=1, max_length=2000)
    scope: str = Field(min_length=1, max_length=4000)
    inputRefs: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    acceptanceCriteria: str = Field(min_length=1, max_length=4000)
    constraints: str = Field(max_length=4000)
    riskClass: str | None = None
    requestedPermissions: list[str]
    budget: dict[str, object]


class AgentPlanStepCreate(StrictRequest):
    stepKey: str = Field(min_length=1, max_length=64)
    agentRole: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=2000)
    skillRefs: list[str] = Field(default_factory=list)
    checkpoint: str | None = None


class AgentPlanCreate(StrictRequest):
    taskCardId: uuid.UUID
    steps: list[AgentPlanStepCreate] = Field(min_length=1)
    outputs: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    budget: dict[str, object] = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)


class AgentPlanDecisionCreate(StrictRequest):
    decision: str

    @field_validator("decision")
    @classmethod
    def _decision_in_enum(cls, value: str) -> str:
        if value not in {"APPROVE", "REJECT"}:
            raise ValueError("decision 必须为 APPROVE 或 REJECT")
        return value

    expectedContentDigest: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(min_length=1, max_length=2000)


class RunCommandCreate(StrictRequest):
    """统一运行命令（六类枚举为契约目标面；本切片实装 PAUSE/RESUME/CANCEL）。"""

    commandType: str

    @field_validator("commandType")
    @classmethod
    def _command_in_enum(cls, value: str) -> str:
        if value not in {"PAUSE", "RESUME", "CANCEL", "RETRY", "AUTHORIZE", "REVOKE"}:
            raise ValueError("commandType 必须为 PAUSE/RESUME/CANCEL/RETRY/AUTHORIZE/REVOKE")
        return value

    reason: str = Field(min_length=1, max_length=2000)
    scope: str | None = Field(default=None, max_length=500)


class RuntimeAuthorizationCreate(StrictRequest):
    """运行时授权/撤销决定（只追加；SecretRef 引用不落明文）。"""

    action: str

    @field_validator("action")
    @classmethod
    def _action_in_enum(cls, value: str) -> str:
        if value not in {"AUTHORIZE", "REVOKE"}:
            raise ValueError("action 必须为 AUTHORIZE 或 REVOKE")
        return value

    permissionKeys: list[str] = Field(min_length=1)
    resourceScope: dict[str, object] = Field(default_factory=dict)
    secretRefs: list[uuid.UUID] = Field(default_factory=list)
    budgetDelta: dict[str, object] = Field(default_factory=dict)
    validFrom: str | None = None
    validUntil: str | None = None


class BudgetPolicyUpdate(StrictRequest):
    """预算策略更新（本切片无消耗追踪，收紧/放宽即时生效）。"""

    tokenLimit: int | None = Field(default=None, ge=0)
    costLimit: float | None = Field(default=None, ge=0)
    timeLimitMinutes: int | None = Field(default=None, ge=1)
    concurrencyLimit: int | None = Field(default=None, ge=1)
    retryLimit: int | None = Field(default=None, ge=0)
    warningThresholds: dict[str, float] | None = None
