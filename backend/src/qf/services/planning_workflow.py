"""Provider-neutral Gate 0 planning workflow reference runtime.

The reference generator is deterministic on purpose. It proves orchestration,
immutable artifact versions, exact digest review bindings and human-only approval
without pretending that a model has been evaluated or configured.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qf.config import settings
from qf.db.sqlite_store import SQLiteWorkflowStore
from qf.orchestration.planning_graph import build_planning_graph
from qf.providers.hardening import GenerationUnavailableError, HardenedPlanningProvider
from qf.providers.planning import GeneratedCase, PlanningGenerationProvider, deterministic_planning_provider

WORKFLOW_KEY = "gate0-planning-slice"
REFERENCE_AGENT_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "qualityforge:qf-test-design-reference"))
APPROVAL_CAPABILITIES = {
    "TEST_STRATEGY": "artifact.test_strategy.approve",
    "TEST_PLAN": "artifact.test_plan.approve",
    "TEST_CASE": "artifact.test_case.approve",
    # M3：执行证据人工批准（execution-workflow.json evidence_gate 的 HITL 绑定）
    "EXECUTION_EVIDENCE": "evidence.approve",
    # M4：缺陷版本人工批准（外部同步 B2-4 的批准前置）
    "DEFECT_VERSION": "artifact.defect_version.approve",
    # P0-1 裁决闭合：测试报告版本人工批准（批准回填根 currentVersionId）
    "TEST_REPORT_VERSION": "artifact.test_report_version.approve",
}
# QF-REQ-078：废弃运行时会话状态 → 32 号契约枚举映射（PAUSED_FOR_HUMAN/COMPLETED 废弃，见 03 §13.13）
_LEGACY_SESSION_STATUS_MAP = {"PAUSED_FOR_HUMAN": "BLOCKED", "COMPLETED": "SUCCEEDED"}

# M2：看板 SLA 面板（32 号 listWorkItemSlaOverview）——简单可解释口径：
# 截止时间 = created_at + 优先级窗口；P3 无 SLA 承诺；无窗口即"无 due"，不计 overdue。
SLA_WINDOW_HOURS: dict[str, int] = {"P0": 24, "P1": 48, "P2": 72}
SLA_PRIORITIES: tuple[str, ...] = ("P0", "P1", "P2")
# 已完成口径：DONE/APPROVED（本运行时审核收敛终态为 APPROVED）；CANCELLED 只计入 total。
SLA_COMPLETED_STATUSES = frozenset({"DONE", "APPROVED"})


class DomainError(Exception):
    """Expected domain/API failure with a stable contract error code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(UTC).isoformat()


def content_digest(content: Any) -> str:
    """Hash canonical JSON so review bindings are deterministic."""
    canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def raw_content_digest(content: str) -> str:
    """Hash source text exactly as submitted."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _serialize_entry(entry: Any) -> Any:
    """嵌套值 JSON 化（UUID→str），供幂等指纹计算。"""
    if isinstance(entry, uuid.UUID):
        return str(entry)
    if isinstance(entry, dict):
        return {key: _serialize_entry(value) for key, value in entry.items()}
    return entry


class PlanningWorkflowService:
    """Concurrency-safe Stage 4 local service backed by a SQLite file."""

    def __init__(
        self,
        db_path: str | None = None,
        provider: PlanningGenerationProvider = deterministic_planning_provider,
    ) -> None:
        self._lock = asyncio.Lock()
        self._provider = provider
        self._store = SQLiteWorkflowStore(settings.sqlite_path if db_path is None else Path(db_path))
        # M1-P1：生成链默认经加固层（超时/重试/降级/成本）+ LangGraph 编排图执行
        self._hardened = HardenedPlanningProvider(provider, recorder=self._record_provider_call)
        self._graph = build_planning_graph(self._hardened)
        # V1 事件管道（D3/O3）：领域事件只追加，延迟导入避免与 events.py 循环依赖
        from qf.services.events import DomainEventService

        self._events = DomainEventService(self._store)
        self._load()

    def override_provider(self, provider: PlanningGenerationProvider) -> None:
        """切换生成 provider 并重建加固层与编排图（测试注入坏 provider/未来替换 provider）。"""
        self._provider = provider
        self._hardened = HardenedPlanningProvider(provider, recorder=self._record_provider_call)
        self._graph = build_planning_graph(self._hardened)

    @property
    def events(self) -> Any:
        """V1 事件管道只读/计算入口（DomainEventService，延迟类型避免循环导入）。"""
        return self._events

    def switch_provider(self, provider: PlanningGenerationProvider) -> dict[str, Any]:
        """M5 切换面（C2/C8）：候选 provider 必须先过黄金集闸门，不达标 fail-closed 拒绝切换。

        deterministic-local 作为 failover 与评估锚点始终可用；每次切换尝试（无论成败）
        落不可变台账（method=PROVIDER_SWITCH），供版本门禁 AI 类证据审计。
        """
        from qf.providers.golden_eval import evaluate_provider

        report = evaluate_provider(provider)
        self._store.append_provider_call_record(
            {
                "providerId": provider.provider_id,
                "providerVersion": provider.provider_version,
                "method": "PROVIDER_SWITCH",
                "durationMs": 0,
                "status": "SUCCESS" if report["gatePassed"] else "REJECTED",
                "failover": False,
                "occurredAt": _now(),
            }
        )
        if not report["gatePassed"]:
            raise DomainError(
                422,
                "PROVIDER_GATE_REJECTED",
                "候选 provider 未通过黄金集评估闸门，保持当前 provider（Plan B）",
                {
                    "structureFailures": report["structureScoring"]["failures"],
                    "falseAccepts": report["negativeCases"]["falseAccepts"],
                },
            )
        self.override_provider(provider)
        self._emit(
            "provider.switched",
            tenant_id="SYSTEM",
            workspace_id=None,
            actor_id="SYSTEM",
            subject_type="provider",
            subject_id=provider.provider_id,
            payload={"providerVersion": provider.provider_version, "gatePassed": report["gatePassed"]},
        )
        return report

    def _record_provider_call(self, record: dict[str, Any]) -> None:
        self._store.append_provider_call_record(record)
        if record["failover"]:
            self._emit(
                "provider.failover",
                tenant_id="SYSTEM",
                workspace_id=None,
                actor_id="SYSTEM",
                subject_type="provider",
                subject_id=record["providerId"],
                payload={"method": record["method"], "status": record["status"]},
            )

    def _emit(
        self,
        event_type: str,
        *,
        tenant_id: str,
        workspace_id: str | None,
        actor_id: str,
        subject_type: str,
        subject_id: str,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """V1 事件管道埋点：生命周期状态变迁 → append-only 领域事件（服务端独占写入面）。"""
        self._events.emit(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            subject_type=subject_type,
            subject_id=subject_id,
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
        )

    def _empty(self) -> None:
        self.requirements: dict[str, dict[str, Any]] = {}
        self.requirement_versions: dict[str, dict[str, Any]] = {}
        self.requirement_contents: dict[str, str] = {}
        self.work_items: dict[str, dict[str, Any]] = {}
        self.strategies: dict[str, dict[str, Any]] = {}
        self.strategy_versions: dict[str, dict[str, Any]] = {}
        self.plans: dict[str, dict[str, Any]] = {}
        self.plan_versions: dict[str, dict[str, Any]] = {}
        self.test_cases: dict[str, dict[str, Any]] = {}
        self.test_case_versions: dict[str, dict[str, Any]] = {}
        self.review_tasks: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.traces: dict[str, list[dict[str, Any]]] = {}
        self.version_index: dict[str, tuple[str, dict[str, Any]]] = {}
        self.review_to_session: dict[str, str] = {}
        self.idempotency: dict[tuple[str, str, str], tuple[str, str]] = {}
        # M3：执行链集合（证据只追加，不参与全量快照 save）
        self.execution_plans: dict[str, dict[str, Any]] = {}
        self.execution_plan_versions: dict[str, dict[str, Any]] = {}
        self.execution_tasks: dict[str, dict[str, Any]] = {}
        self.execution_results: dict[str, dict[str, Any]] = {}
        self.execution_evidence: dict[str, dict[str, Any]] = {}
        # M4：质量域集合 + 知识回流
        self.result_analyses: dict[str, dict[str, Any]] = {}
        self.failure_clusters: dict[str, dict[str, Any]] = {}
        self.defects: dict[str, dict[str, Any]] = {}
        self.defect_versions: dict[str, dict[str, Any]] = {}
        self.defect_sync_attempts: dict[str, dict[str, Any]] = {}
        self.test_reports: dict[str, dict[str, Any]] = {}
        self.test_report_versions: dict[str, dict[str, Any]] = {}
        self.coverage_reports: dict[str, dict[str, Any]] = {}
        self.knowledge_entries: dict[str, dict[str, Any]] = {}
        # 批次四十六：平台域环境集合（契约已有 listEnvironments/createEnvironment，本批补后端路由）
        self.environments: dict[str, dict[str, Any]] = {}
        self.conversations: dict[str, dict[str, Any]] = {}
        self.conversation_messages: dict[str, dict[str, Any]] = {}
        self.clarifications: dict[str, dict[str, Any]] = {}
        self.clarification_responses: dict[str, dict[str, Any]] = {}
        self.task_cards: dict[str, dict[str, Any]] = {}
        self.agent_plans: dict[str, dict[str, Any]] = {}
        self.agent_plan_decisions: dict[str, dict[str, Any]] = {}
        self.run_commands: dict[str, dict[str, Any]] = {}
        self.runtime_authorizations: dict[str, dict[str, Any]] = {}
        self.budget_policies: dict[str, dict[str, Any]] = {}
        self.run_checkpoints: dict[str, dict[str, Any]] = {}

    def _load(self) -> None:
        self._empty()
        state = self._store.load()
        for name in (
            "requirements",
            "requirement_versions",
            "requirement_contents",
            "work_items",
            "strategies",
            "strategy_versions",
            "plans",
            "plan_versions",
            "test_cases",
            "test_case_versions",
            "review_tasks",
            "sessions",
            "traces",
            "review_to_session",
            "idempotency",
            "execution_plans",
            "execution_plan_versions",
            "execution_tasks",
            "execution_results",
            "execution_evidence",
            "result_analyses",
            "failure_clusters",
            "defects",
            "defect_versions",
            "defect_sync_attempts",
            "test_reports",
            "test_report_versions",
            "coverage_reports",
            "knowledge_entries",
            "environments",
            "conversations",
            "conversation_messages",
            "clarifications",
            "clarification_responses",
            "task_cards",
            "agent_plans",
            "agent_plan_decisions",
            "run_commands",
            "runtime_authorizations",
            "budget_policies",
            "run_checkpoints",
        ):
            setattr(self, name, state[name])
        version_collections = {
            "TEST_STRATEGY": self.strategy_versions,
            "TEST_PLAN": self.plan_versions,
            "TEST_CASE": self.test_case_versions,
            "DEFECT_VERSION": self.defect_versions,
            "TEST_REPORT_VERSION": self.test_report_versions,
        }
        for version_id, (artifact_type, _artifact_id) in state["version_metadata"].items():
            version = version_collections.get(artifact_type, {}).get(version_id)
            if version is not None:
                self.version_index[version_id] = (artifact_type, version)
        # QF-REQ-078：存量废弃会话状态加载时归一到契约枚举（见 03 §13.13）
        for session in self.sessions.values():
            if session["status"] in _LEGACY_SESSION_STATUS_MAP:
                session["status"] = _LEGACY_SESSION_STATUS_MAP[session["status"]]
        # M3 fail-closed：启动加载时校验证据完整性，篡改过的存储拒绝服务
        self.verify_evidence_integrity()
        # V1 fail-closed：领域事件链同样启动校验（哈希链断裂即直写篡改）
        self._events.verify_chain()

    def reconfigure(self, db_path: str) -> None:
        """Point the service at another SQLite file, primarily for isolated tests."""
        from qf.services.events import DomainEventService

        self._store = SQLiteWorkflowStore(Path(db_path))
        self._events = DomainEventService(self._store)
        self._load()

    def reset(self, *, clear_storage: bool = True) -> None:
        """Clear test state; production code never calls this method."""
        if clear_storage:
            self._store.clear_workflow()
        self._empty()

    def _state(self) -> dict[str, Any]:
        return {
            "requirements": self.requirements,
            "requirement_versions": self.requirement_versions,
            "requirement_contents": self.requirement_contents,
            "work_items": self.work_items,
            "strategies": self.strategies,
            "strategy_versions": self.strategy_versions,
            "plans": self.plans,
            "plan_versions": self.plan_versions,
            "test_cases": self.test_cases,
            "test_case_versions": self.test_case_versions,
            "review_tasks": self.review_tasks,
            "sessions": self.sessions,
            "traces": self.traces,
            "execution_plans": self.execution_plans,
            "execution_plan_versions": self.execution_plan_versions,
            "execution_tasks": self.execution_tasks,
            "execution_results": self.execution_results,
            "result_analyses": self.result_analyses,
            "failure_clusters": self.failure_clusters,
            "defects": self.defects,
            "defect_versions": self.defect_versions,
            "defect_sync_attempts": self.defect_sync_attempts,
            "test_reports": self.test_reports,
            "test_report_versions": self.test_report_versions,
            "coverage_reports": self.coverage_reports,
            "knowledge_entries": self.knowledge_entries,
            "environments": self.environments,
            "conversations": self.conversations,
            "conversation_messages": self.conversation_messages,
            "clarifications": self.clarifications,
            "clarification_responses": self.clarification_responses,
            "task_cards": self.task_cards,
            "agent_plans": self.agent_plans,
            "agent_plan_decisions": self.agent_plan_decisions,
            "run_commands": self.run_commands,
            "runtime_authorizations": self.runtime_authorizations,
            "budget_policies": self.budget_policies,
            "run_checkpoints": self.run_checkpoints,
            "version_index": {
                version_id: (artifact_type, self._artifact_id(version), version)
                for version_id, (artifact_type, version) in self.version_index.items()
            },
            "review_to_session": self.review_to_session,
            "idempotency": self.idempotency,
        }

    @staticmethod
    def _artifact_id(version: dict[str, Any]) -> str:
        for key in ("testStrategyId", "testPlanId", "testCaseId", "defectId", "testReportId"):
            if key in version:
                return str(version[key])
        raise RuntimeError("formal artifact version has no root id")

    def _persist(self) -> None:
        self._store.save(self._state())

    @staticmethod
    def _require_capability(capabilities: frozenset[str], capability: str) -> None:
        if capability not in capabilities:
            raise DomainError(403, "FORBIDDEN", f"缺少能力: {capability}")

    @staticmethod
    def _owned(record: dict[str, Any], tenant_id: str) -> bool:
        return record.get("tenantId") == tenant_id

    @staticmethod
    def _owned_workspace(record: dict[str, Any], tenant_id: str, workspace_id: str) -> bool:
        return record.get("tenantId") == tenant_id and record.get("workspaceId") == workspace_id

    @staticmethod
    def _copy(record: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(record)

    @staticmethod
    def _idempotency_fingerprint(payload: dict[str, Any]) -> str:
        return content_digest(payload)

    def _resolve_idempotency(
        self,
        tenant_id: str,
        operation: str,
        key: str,
        payload: dict[str, Any],
    ) -> str | None:
        if len(key) < 16 or len(key) > 128:
            raise DomainError(422, "VALIDATION_FAILED", "Idempotency-Key长度必须为16到128")
        map_key = (tenant_id, operation, key)
        fingerprint = self._idempotency_fingerprint(payload)
        previous = self.idempotency.get(map_key)
        if not previous:
            return None
        previous_fingerprint, resource_id = previous
        if previous_fingerprint != fingerprint:
            raise DomainError(409, "IDEMPOTENCY_CONFLICT", "幂等键已绑定其他请求内容")
        return resource_id

    def _remember_idempotency(
        self,
        tenant_id: str,
        operation: str,
        key: str,
        payload: dict[str, Any],
        resource_id: str,
    ) -> None:
        self.idempotency[(tenant_id, operation, key)] = (
            self._idempotency_fingerprint(payload),
            resource_id,
        )

    async def create_requirement(
        self,
        tenant_id: str,
        capabilities: frozenset[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_capability(capabilities, "requirement.write")
        async with self._lock:
            now = _now()
            record = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": str(payload["workspaceId"]),
                "name": payload["name"],
                "documentType": payload["documentType"],
                "currentVersionId": None,
                "publishedVersionId": None,
                "status": "ACTIVE",
                "createdAt": now,
            }
            self.requirements[record["id"]] = record
            self._persist()
            return self._copy(record)

    async def create_requirement_version(
        self,
        tenant_id: str,
        workspace_id: str,
        capabilities: frozenset[str],
        requirement_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_capability(capabilities, "requirement.write")
        async with self._lock:
            requirement = self.requirements.get(requirement_id)
            if not requirement or not self._owned_workspace(requirement, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "需求文档不存在")
            submitted_digest = payload["contentDigest"]
            actual_digest = raw_content_digest(payload["content"])
            if submitted_digest != actual_digest:
                raise DomainError(
                    422,
                    "VALIDATION_FAILED",
                    "需求正文摘要不匹配",
                    {"expectedDigest": actual_digest},
                )
            version_number = 1 + sum(
                item["requirementDocumentId"] == requirement_id for item in self.requirement_versions.values()
            )
            version = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": requirement["workspaceId"],
                "requirementDocumentId": requirement_id,
                "version": version_number,
                "sourceSnapshotId": str(payload["sourceSnapshotId"]),
                "parseStatus": "COMPLETED",
                "reviewStatus": "DRAFT",
                "contentDigest": submitted_digest,
                "changeSummary": payload.get("changeSummary"),
                "createdAt": _now(),
            }
            self.requirement_versions[version["id"]] = version
            self.requirement_contents[version["id"]] = payload["content"]
            requirement["currentVersionId"] = version["id"]
            self._persist()
            return self._public_requirement_version(version)

    @staticmethod
    def _public_requirement_version(version: dict[str, Any]) -> dict[str, Any]:
        return {key: deepcopy(value) for key, value in version.items() if key not in {"tenantId", "workspaceId"}}

    async def create_work_item(
        self,
        tenant_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_capability(capabilities, "work_item.create")
        release_id = str(payload["releaseId"]) if payload.get("releaseId") else None
        if release_id is not None and not self._store.active_release_exists(
            tenant_id, str(payload["workspaceId"]), release_id
        ):
            raise DomainError(409, "RELEASE_NOT_IN_WORKSPACE", "Release 不存在、非 ACTIVE 或不属于当前 Workspace")
        async with self._lock:
            now = _now()
            work_item = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": str(payload["workspaceId"]),
                "releaseId": release_id,
                "workItemType": payload["workItemType"],
                "title": payload["title"],
                "description": payload.get("description"),
                # QF-REQ-001 四源对齐：六关键字段落库（requiresReview/lockVersion 语义接线归 M1-B1）
                "objective": payload["objective"],
                "acceptanceCriteria": payload["acceptanceCriteria"],
                "requiresReview": payload["requiresReview"],
                "constraints": payload.get("constraints"),
                "agentId": str(payload["agentId"]) if payload.get("agentId") else None,
                "lockVersion": 0,
                "status": "READY",
                "currentActorType": "HUMAN",
                "currentActorId": actor_id,
                "priority": payload["priority"],
                "riskLevel": payload["riskLevel"],
                "ownerId": actor_id,
                "assigneeId": actor_id,
                "createdAt": now,
                "updatedAt": now,
            }
            self.work_items[work_item["id"]] = work_item
            self._persist()
            return self._copy(work_item)

    async def start_session(
        self,
        tenant_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_capability(capabilities, "workflow.start")
        if actor_type not in {"USER", "SERVICE"}:
            raise DomainError(403, "FORBIDDEN", "Agent不能自行启动正式产出物工作流")
        serializable_payload = {key: str(value) for key, value in payload.items()}
        async with self._lock:
            previous_id = self._resolve_idempotency(
                tenant_id, "createAgentSession", idempotency_key, serializable_payload
            )
            if previous_id:
                return self._copy(self.sessions[previous_id])

            work_item = self.work_items.get(str(payload["workItemId"]))
            requirement_version = self.requirement_versions.get(str(payload["requirementVersionId"]))
            if not work_item or not self._owned(work_item, tenant_id):
                raise DomainError(404, "NOT_FOUND", "工作项不存在")
            if not requirement_version or not self._owned(requirement_version, tenant_id):
                raise DomainError(404, "NOT_FOUND", "需求版本不存在")
            workspace_id = str(payload["workspaceId"])
            if work_item["workspaceId"] != workspace_id or requirement_version["workspaceId"] != workspace_id:
                raise DomainError(403, "FORBIDDEN", "资源不属于当前Workspace")
            # QF-PD-003 计划先确认：仅已批准的 AgentPlan 可启动 Session（批次五十七强制门）
            has_approved_plan = any(
                plan["workItemId"] == str(payload["workItemId"])
                and self._owned(plan, tenant_id)
                and plan["status"] == "APPROVED"
                for plan in self.agent_plans.values()
            )
            if not has_approved_plan:
                raise DomainError(409, "AGENT_PLAN_NOT_APPROVED", "工作项无已批准的 AgentPlan，不能启动 Session")
            if payload["workflowKey"] != WORKFLOW_KEY:
                raise DomainError(422, "VALIDATION_FAILED", "工作流不受支持")

            session_id = _new_id()
            now = _now()
            session = {
                "id": session_id,
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "workItemId": work_item["id"],
                "workflowKey": WORKFLOW_KEY,
                "requirementVersionId": requirement_version["id"],
                "releaseId": str(payload["releaseId"]),
                "ownerId": str(payload["ownerId"]),
                "status": "RUNNING",
                "artifactRefs": [],
                "reviewTaskIds": [],
                "traceCount": 0,
                "startedAt": now,
                "completedAt": None,
                "initiatedBy": actor_id,
            }
            self.sessions[session_id] = session
            self.traces[session_id] = []
            work_item.update(
                {
                    "status": "IN_PROGRESS",
                    "currentActorType": "AGENT",
                    "currentActorId": REFERENCE_AGENT_ID,
                    "updatedAt": now,
                }
            )

            source_content = self.requirement_contents[requirement_version["id"]]
            self._trace(session_id, "requirement_source_check", "qf-requirement-ir", "requirement-quality-gate")
            artifacts = self._generate_artifacts(session, source_content)
            session["artifactRefs"] = artifacts
            self._trace(session_id, "human_gate", "qf-independent-verifier", "hitl-gatekeeper", "BLOCK_HUMAN")
            session["reviewTaskIds"] = [
                self._create_review_task(
                    tenant_id=session["tenantId"],
                    workspace_id=session["workspaceId"],
                    work_item_id=session["workItemId"],
                    session_id=session_id,
                    owner_id=session["ownerId"],
                    artifact=artifact,
                )
                for artifact in artifacts
            ]
            # QF-REQ-078：等待人工门禁收敛为契约枚举 BLOCKED（原 PAUSED_FOR_HUMAN）
            session["status"] = "BLOCKED"
            session["traceCount"] = len(self.traces[session_id])
            work_item.update(
                {
                    "status": "PENDING_REVIEW",
                    "currentActorType": "HUMAN",
                    "currentActorId": str(payload["ownerId"]),
                    "updatedAt": _now(),
                }
            )
            self._remember_idempotency(
                tenant_id, "createAgentSession", idempotency_key, serializable_payload, session_id
            )
            self._persist()
            return self._copy(session)

    def _generate_artifacts(self, session: dict[str, Any], source_content: str) -> list[dict[str, Any]]:
        # M1-P1：版本 ID 预分配后经 state 注入，LangGraph 四节点一次性跑完生成链，
        # 产出物落库与审核语义保持原状；失败（降级目标也失败）时 fail-closed 抛错。
        strategy_root_id, strategy_version_id = _new_id(), _new_id()
        plan_root_id, plan_version_id = _new_id(), _new_id()
        try:
            state = self._graph.invoke(
                {
                    "source_content": source_content,
                    "strategy_version_id": strategy_version_id,
                    "plan_version_id": plan_version_id,
                    "requirement_version_id": session["requirementVersionId"],
                    "owner_id": session["ownerId"],
                }
            )
        except GenerationUnavailableError as exc:
            raise DomainError(503, "GENERATION_UNAVAILABLE", "生成服务暂时不可用，请稍后重试") from exc
        # 产出物 providerId/providerVersion 按方法追溯实际成功提供者（failover 后为 deterministic-local）
        providers = self._store.latest_successful_provider_by_method()
        default_provider = (self._provider.provider_id, self._provider.provider_version)
        strategy_provider = providers.get("strategy", default_provider)
        plan_provider = providers.get("plan", default_provider)
        cases_provider = providers.get("cases", default_provider)

        strategy = self._create_strategy(
            session, strategy_root_id, strategy_version_id, state["strategy_content"], strategy_provider
        )
        self._trace(
            session["id"],
            "strategy",
            "qf-test-design",
            "strategy-planner",
            artifact=strategy,
        )
        plan = self._create_plan(session, plan_root_id, plan_version_id, state["plan_content"], plan_provider)
        self._trace(
            session["id"],
            "test_plan",
            "qf-test-design",
            "plan-orchestrator",
            artifact=plan,
        )
        cases = self._create_test_cases(session, state["generated_cases"], cases_provider)
        for case in cases:
            self._trace(
                session["id"],
                "test_cases",
                "qf-test-design",
                "test-case-generator",
                artifact=case,
            )
        return [strategy, plan, *cases]

    def _create_strategy(
        self,
        session: dict[str, Any],
        root_id: str,
        version_id: str,
        content: dict[str, Any],
        provider: tuple[str, str],
    ) -> dict[str, Any]:
        digest = content_digest(content)
        root = {
            "id": root_id,
            "tenantId": session["tenantId"],
            "workspaceId": session["workspaceId"],
            "releaseId": session["releaseId"],
            "strategyKey": f"STR-{session['id'][:8]}",
            "name": "AI生成测试策略草稿",
            "currentVersionId": version_id,
            "publishedVersionId": None,
            "status": "ACTIVE",
            "createdAt": _now(),
        }
        version = {
            "id": version_id,
            "tenantId": session["tenantId"],
            "workspaceId": session["workspaceId"],
            "testStrategyId": root_id,
            "version": 1,
            "reviewStatus": "PENDING_REVIEW",
            "contentDigest": digest,
            **content,
            "changeSummary": "参考生成器创建首版草稿",
            "generatedByAgentId": REFERENCE_AGENT_ID,
            "agentRunId": session["id"],
            "providerId": provider[0],
            "providerVersion": provider[1],
            "createdAt": _now(),
        }
        self.strategies[root_id] = root
        self.strategy_versions[version_id] = version
        return self._index_version("TEST_STRATEGY", root_id, version)

    def _create_plan(
        self,
        session: dict[str, Any],
        root_id: str,
        version_id: str,
        content: dict[str, Any],
        provider: tuple[str, str],
    ) -> dict[str, Any]:
        digest = content_digest(content)
        root = {
            "id": root_id,
            "tenantId": session["tenantId"],
            "workspaceId": session["workspaceId"],
            "releaseId": session["releaseId"],
            "planKey": f"PLAN-{session['id'][:8]}",
            "name": "AI生成测试计划草稿",
            "currentVersionId": version_id,
            "publishedVersionId": None,
            "lifecycleStatus": "NOT_STARTED",
            "createdAt": _now(),
        }
        version = {
            "id": version_id,
            "tenantId": session["tenantId"],
            "workspaceId": session["workspaceId"],
            "testPlanId": root_id,
            "version": 1,
            "reviewStatus": "PENDING_REVIEW",
            "contentDigest": digest,
            **content,
            "changeSummary": "参考生成器创建首版草稿",
            "generatedByAgentId": REFERENCE_AGENT_ID,
            "agentRunId": session["id"],
            "providerId": provider[0],
            "providerVersion": provider[1],
            "createdAt": _now(),
        }
        self.plans[root_id] = root
        self.plan_versions[version_id] = version
        return self._index_version("TEST_PLAN", root_id, version)

    def _create_test_cases(
        self,
        session: dict[str, Any],
        definitions: list[GeneratedCase],
        provider: tuple[str, str],
    ) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        for index, generated in enumerate(definitions, start=1):
            root_id = _new_id()
            version_id = _new_id()
            content = generated.content
            digest = content_digest(content)
            root = {
                "id": root_id,
                "tenantId": session["tenantId"],
                "workspaceId": session["workspaceId"],
                "caseKey": f"TC-{session['id'][:8]}-{index:03d}",
                "title": generated.title,
                "fromDesignTestCaseId": None,
                "currentVersionId": version_id,
                "publishedVersionId": None,
                "status": "ACTIVE",
                "createdAt": _now(),
            }
            version = {
                "id": version_id,
                "tenantId": session["tenantId"],
                "workspaceId": session["workspaceId"],
                "testCaseId": root_id,
                "version": 1,
                "reviewStatus": "PENDING_REVIEW",
                "contentDigest": digest,
                **content,
                "changeSummary": "参考生成器创建首版草稿",
                "generatedByAgentId": REFERENCE_AGENT_ID,
                "agentRunId": session["id"],
                "providerId": provider[0],
                "providerVersion": provider[1],
                "createdAt": _now(),
            }
            self.test_cases[root_id] = root
            self.test_case_versions[version_id] = version
            artifacts.append(self._index_version("TEST_CASE", root_id, version))
        return artifacts

    def _index_version(
        self,
        artifact_type: str,
        artifact_id: str,
        version: dict[str, Any],
    ) -> dict[str, Any]:
        self.version_index[version["id"]] = (artifact_type, version)
        return {
            "artifactType": artifact_type,
            "artifactId": artifact_id,
            "artifactVersionId": version["id"],
            "contentDigest": version["contentDigest"],
        }

    def _trace(
        self,
        session_id: str,
        node_id: str,
        agent_id: str,
        skill_id: str,
        status: str = "SUCCEEDED",
        artifact: dict[str, Any] | None = None,
    ) -> None:
        events = self.traces[session_id]
        event: dict[str, Any] = {
            "sequence": len(events) + 1,
            "nodeId": node_id,
            "agentId": agent_id,
            "skillId": skill_id,
            "status": status,
            "occurredAt": _now(),
        }
        if artifact:
            event.update(
                {
                    "artifactType": artifact["artifactType"],
                    "artifactVersionId": artifact["artifactVersionId"],
                    "contentDigest": artifact["contentDigest"],
                }
            )
        events.append(event)

    def _create_review_task(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        work_item_id: str | None,
        session_id: str | None,
        owner_id: str,
        artifact: dict[str, Any],
    ) -> str:
        review_id = _new_id()
        # WP-05 切片二：风险分级审核政策（04 号 ReviewPolicy 平台最低基线，服务端钉死——
        # CRITICAL 双人复核，其余单人；ReviewPolicy 配置面 CRUD 后置）
        work_item = self.work_items.get(str(work_item_id)) if work_item_id else None
        if work_item is not None and work_item.get("riskLevel") == "CRITICAL":
            policy_type, min_approvers = "FOUR_EYES", 2
        else:
            policy_type, min_approvers = "SINGLE_REVIEW", 1
        task = {
            "id": review_id,
            "tenantId": tenant_id,
            "workspaceId": workspace_id,
            "workItemId": work_item_id,
            "agentSessionId": session_id,
            **artifact,
            "policyType": policy_type,
            "minApprovers": min_approvers,
            "approvals": [],
            "status": "OPEN",
            "assignments": [
                {
                    "userId": owner_id,
                    "reviewRole": "APPROVER",
                    "requiredCapability": APPROVAL_CAPABILITIES[artifact["artifactType"]],
                }
            ],
            "createdAt": _now(),
            "expiresAt": None,
            "decision": None,
        }
        self.review_tasks[review_id] = task
        if session_id:
            self.review_to_session[review_id] = session_id
        return review_id

    async def decide_review(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        review_task_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if actor_type != "USER":
            raise DomainError(403, "FORBIDDEN", "正式产出物只能由具备能力的人类审核")
        serializable_payload = {
            key: str(value) if isinstance(value, uuid.UUID) else value for key, value in payload.items()
        }
        serializable_payload["actorId"] = actor_id
        async with self._lock:
            previous_id = self._resolve_idempotency(
                tenant_id, f"decideReviewTask:{review_task_id}", idempotency_key, serializable_payload
            )
            if previous_id:
                return self._public_review_task(self.review_tasks[previous_id])
            task = self.review_tasks.get(review_task_id)
            if not task or not self._owned_workspace(task, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "审核任务不存在")
            capability = APPROVAL_CAPABILITIES.get(task["artifactType"])
            if capability is None:
                raise DomainError(422, "VALIDATION_FAILED", "不支持的审核产出物类型")
            self._require_capability(capabilities, capability)
            if task["status"] not in {"OPEN", "IN_PROGRESS"}:
                raise DomainError(409, "INVALID_STATE_TRANSITION", "审核任务已结束")
            if payload["contentDigest"] != task["contentDigest"]:
                raise DomainError(409, "STALE_ARTIFACT_VERSION", "审核摘要与当前版本不一致")

            decision = payload["decision"]
            if decision == "APPROVE":
                # WP-05 切片二：双人复核（FOUR_EYES）——同一审批人不得二次批准（单人绕过双审 409）
                if task["policyType"] == "FOUR_EYES" and any(
                    entry.get("actorId") == actor_id for entry in task.get("approvals", [])
                ):
                    raise DomainError(409, "FOUR_EYES_SAME_APPROVER", "双人复核需要两名不同审批人")
                task["approvals"] = [
                    *task.get("approvals", []),
                    {"actorId": actor_id, "comments": payload.get("comments"), "decidedAt": _now()},
                ]

            if decision == "APPROVE" and len(task.get("approvals", [])) < task.get("minApprovers", 1):
                # 部分批准：任务挂起等待其余审批人；版本保持 PENDING_REVIEW，会话保持 BLOCKED。
                # 退回（REQUEST_CHANGES/REJECT）不要求双人——阻断项单人即可直接退回（06 号 §9）。
                task["status"] = "IN_PROGRESS"
                self._emit(
                    "review.decided",
                    tenant_id=tenant_id,
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    subject_type="review_task",
                    subject_id=review_task_id,
                    payload={
                        "decision": decision,
                        "status": task["status"],
                        "approvals": len(task["approvals"]),
                        "minApprovers": task["minApprovers"],
                        "artifactType": task["artifactType"],
                        "artifactId": task["artifactId"],
                        "artifactVersionId": task["artifactVersionId"],
                    },
                )
                self._remember_idempotency(
                    tenant_id,
                    f"decideReviewTask:{review_task_id}",
                    idempotency_key,
                    serializable_payload,
                    review_task_id,
                )
                self._persist()
                return self._public_review_task(task)

            task["status"] = {
                "APPROVE": "APPROVED",
                "REQUEST_CHANGES": "CHANGES_REQUESTED",
                "REJECT": "REJECTED",
            }[decision]
            task["decision"] = {
                "decision": decision,
                "actorId": actor_id,
                "comments": payload.get("comments"),
                "decidedAt": _now(),
            }
            _, version_or_none = self.version_index.get(task["artifactVersionId"], (None, None))
            # M1-B1：退回（REQUEST_CHANGES/REJECT）使产出物版本回草稿态，供修订后提交新版本
            # M3：执行证据不在正式版本索引中，跳过 reviewStatus 更新
            if version_or_none is not None:
                version_or_none["reviewStatus"] = "APPROVED" if decision == "APPROVE" else "DRAFT"
            # M4：缺陷版本批准后挂钩根记录的 approvedVersionId 指针（外部同步 B2-4 前置）
            if task["artifactType"] == "DEFECT_VERSION" and decision == "APPROVE" and version_or_none is not None:
                defect_root = self.defects.get(str(version_or_none["defectId"]))
                if defect_root is not None:
                    defect_root["approvedVersionId"] = str(version_or_none["id"])
            # P0-1 裁决闭合：报告版本批准后回填根 currentVersionId（publishedVersionId 归后续签署切片）
            if task["artifactType"] == "TEST_REPORT_VERSION" and decision == "APPROVE" and version_or_none is not None:
                report_root = self.test_reports.get(str(version_or_none["testReportId"]))
                if report_root is not None:
                    report_root["currentVersionId"] = str(version_or_none["id"])
                    report_root["updatedAt"] = _now()
            self._emit(
                "review.decided",
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type="review_task",
                subject_id=review_task_id,
                payload={
                    "decision": decision,
                    "status": task["status"],
                    "artifactType": task["artifactType"],
                    "artifactId": task["artifactId"],
                    "artifactVersionId": task["artifactVersionId"],
                },
            )
            # M2：手工创建的审核任务无会话链接，跳过会话收敛
            session_id = self.review_to_session.get(review_task_id)
            if session_id:
                self._advance_session_after_review(session_id)
            self._remember_idempotency(
                tenant_id,
                f"decideReviewTask:{review_task_id}",
                idempotency_key,
                serializable_payload,
                review_task_id,
            )
            self._persist()
            return self._public_review_task(task)

    def _advance_session_after_review(self, session_id: str) -> None:
        session = self.sessions[session_id]
        tasks = [self.review_tasks[task_id] for task_id in session["reviewTaskIds"]]
        work_item = self.work_items[session["workItemId"]]
        # M1-B1：已被同产出物更新版本任务取代的旧任务不再参与收敛判定
        # （契约 ReviewTaskStatus 无 SUPERSEDED 态，旧任务状态保持不变，仅排除出判定）
        statuses = [task["status"] for task in tasks if not self._is_superseded(task, tasks)]
        if all(status == "APPROVED" for status in statuses):
            # QF-REQ-078：成功完成收敛为契约枚举 SUCCEEDED（原 COMPLETED）
            session["status"] = "SUCCEEDED"
            session["completedAt"] = _now()
            self._trace(
                session_id,
                "human_gate_completed",
                "human-reviewer",
                "hitl-gatekeeper",
                "SUCCEEDED",
            )
            session["traceCount"] = len(self.traces[session_id])
            self._emit(
                "session.converged",
                tenant_id=session["tenantId"],
                workspace_id=session["workspaceId"],
                actor_id="SYSTEM",
                subject_type="agent_session",
                subject_id=session_id,
                payload={"status": "SUCCEEDED"},
            )
            work_item.update(
                {"status": "APPROVED", "currentActorType": "NONE", "currentActorId": None, "updatedAt": _now()}
            )
        elif any(status == "REJECTED" for status in statuses):
            # M1-B1/QF-REQ-078：REJECT 终态会话（契约枚举 FAILED，见 03 §13.13），产出物已回草稿态待重建
            session["status"] = "FAILED"
            session["completedAt"] = _now()
            self._trace(session_id, "human_gate_rejected", "human-reviewer", "hitl-gatekeeper", "FAILED")
            session["traceCount"] = len(self.traces[session_id])
            self._emit(
                "session.converged",
                tenant_id=session["tenantId"],
                workspace_id=session["workspaceId"],
                actor_id="SYSTEM",
                subject_type="agent_session",
                subject_id=session_id,
                payload={"status": "FAILED"},
            )
            work_item.update({"status": "REWORK", "currentActorType": "HUMAN", "updatedAt": _now()})
        else:
            # QF-REQ-078：等待人工收敛为契约枚举 BLOCKED（原 PAUSED_FOR_HUMAN）
            session["status"] = "BLOCKED"
            self._emit(
                "session.converged",
                tenant_id=session["tenantId"],
                workspace_id=session["workspaceId"],
                actor_id="SYSTEM",
                subject_type="agent_session",
                subject_id=session_id,
                payload={"status": "BLOCKED"},
            )
            if any(status == "CHANGES_REQUESTED" for status in statuses):
                work_item.update({"status": "REWORK", "currentActorType": "HUMAN", "updatedAt": _now()})
            else:
                work_item.update({"status": "PENDING_REVIEW", "currentActorType": "HUMAN", "updatedAt": _now()})

    def _is_superseded(self, task: dict[str, Any], session_tasks: list[dict[str, Any]]) -> bool:
        """同会话内存在同产出物的更高版本任务，则本任务已被取代。"""

        def version_number(candidate: dict[str, Any]) -> int:
            indexed = self.version_index.get(candidate["artifactVersionId"])
            return int(indexed[1].get("version", 0)) if indexed else 0

        return any(
            other["id"] != task["id"]
            and other["artifactId"] == task["artifactId"]
            and version_number(other) > version_number(task)
            for other in session_tasks
        )

    async def create_strategy_version(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        strategy_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """M1-B1：退回后提交测试策略新版本（版本不可变，自动建新 ReviewTask）。"""
        self._require_capability(capabilities, "artifact.test_strategy.submit")
        async with self._lock:
            root = self.strategies.get(strategy_id)
            if not root or not self._owned_workspace(root, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "测试策略不存在")
            content = self._version_content(payload)
            version = self._append_artifact_version(
                "TEST_STRATEGY", root, self.strategy_versions, "testStrategyId", actor_id, content, payload
            )
            self._persist()
            return self._copy(version)

    async def create_plan_version(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        plan_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """M1-B1：退回后提交测试计划新版本（strategyVersionId 必须指向既有策略版本）。"""
        self._require_capability(capabilities, "artifact.test_plan.submit")
        async with self._lock:
            root = self.plans.get(plan_id)
            if not root or not self._owned_workspace(root, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "测试计划不存在")
            indexed = self.version_index.get(str(payload["strategyVersionId"]))
            if indexed is None or indexed[0] != "TEST_STRATEGY":
                raise DomainError(422, "VALIDATION_FAILED", "strategyVersionId必须指向既有测试策略版本")
            content = self._version_content(payload)
            version = self._append_artifact_version(
                "TEST_PLAN", root, self.plan_versions, "testPlanId", actor_id, content, payload
            )
            self._persist()
            return self._copy(version)

    async def publish_strategy_version(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        strategy_id: str,
        version_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """WP-05 切片一：测试策略版本发布（APPROVED → PUBLISHED，QF-PD-007/039）。"""
        return await self._publish_artifact_version(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=actor_type,
            capabilities=capabilities,
            operation="publishTestStrategyVersion",
            capability="artifact.test_strategy.publish",
            artifact_type="TEST_STRATEGY",
            root_label="测试策略",
            root_store=self.strategies,
            version_store=self.strategy_versions,
            parent_key="testStrategyId",
            root_id=strategy_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def publish_plan_version(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        plan_id: str,
        version_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """WP-05 切片一：测试计划版本发布（APPROVED → PUBLISHED，QF-PD-007/039）。"""
        return await self._publish_artifact_version(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=actor_type,
            capabilities=capabilities,
            operation="publishTestPlanVersion",
            capability="artifact.test_plan.publish",
            artifact_type="TEST_PLAN",
            root_label="测试计划",
            root_store=self.plans,
            version_store=self.plan_versions,
            parent_key="testPlanId",
            root_id=plan_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def publish_test_case_version(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        test_case_id: str,
        version_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """WP-05 切片一：测试用例版本发布（APPROVED → PUBLISHED，正式执行只选 PUBLISHED 版本）。"""
        return await self._publish_artifact_version(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=actor_type,
            capabilities=capabilities,
            operation="publishTestCaseVersion",
            capability="artifact.test_case.publish",
            artifact_type="TEST_CASE",
            root_label="测试用例",
            root_store=self.test_cases,
            version_store=self.test_case_versions,
            parent_key="testCaseId",
            root_id=test_case_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def _publish_artifact_version(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        operation: str,
        capability: str,
        artifact_type: str,
        root_label: str,
        root_store: dict[str, dict[str, Any]],
        version_store: dict[str, dict[str, Any]],
        parent_key: str,
        root_id: str,
        version_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """发布命令公共语义（39 号 §10）：仅 USER；幂等重放先于状态校验；
        仅 APPROVED 可发布（APPROVED → PUBLISHED）；新发布使同资产旧 PUBLISHED 版本转 STALE，
        回填根 publishedVersionId；发布不自动改写已激活下游（StageInvalidated 联动随后续批次）。"""
        if actor_type != "USER":
            raise DomainError(403, "FORBIDDEN", "正式产出物只能由具备能力的人类发布")
        idempotency_payload = {"versionId": version_id, "actorId": actor_id}
        async with self._lock:
            previous_id = self._resolve_idempotency(
                tenant_id, f"{operation}:{version_id}", idempotency_key, idempotency_payload
            )
            if previous_id:
                return self._copy(version_store[previous_id])
            root = root_store.get(root_id)
            if not root or not self._owned_workspace(root, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", f"{root_label}不存在")
            version = version_store.get(version_id)
            if not version or version.get(parent_key) != root["id"]:
                raise DomainError(404, "NOT_FOUND", f"{root_label}版本不存在")
            self._require_capability(capabilities, capability)
            if version["reviewStatus"] != "APPROVED":
                raise DomainError(409, "ASSET_NOT_APPROVED", "仅 APPROVED 版本可发布")
            superseded_version_id = root.get("publishedVersionId")
            if superseded_version_id and superseded_version_id != version_id:
                superseded = version_store.get(str(superseded_version_id))
                if superseded is not None:
                    superseded["reviewStatus"] = "STALE"
            version["reviewStatus"] = "PUBLISHED"
            root["publishedVersionId"] = version_id
            self._remember_idempotency(
                tenant_id, f"{operation}:{version_id}", idempotency_key, idempotency_payload, version_id
            )
            self._emit(
                "asset.published",
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type=artifact_type,
                subject_id=root["id"],
                payload={
                    "versionId": version_id,
                    "version": version["version"],
                    "supersededVersionId": superseded_version_id,
                },
            )
            if artifact_type == "TEST_STRATEGY" and superseded_version_id:
                self._invalidate_downstream_plans(
                    tenant_id=tenant_id,
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    superseded_version_id=str(superseded_version_id),
                    published_version_id=version_id,
                )
            self._persist()
            return self._copy(version)

    def _invalidate_downstream_plans(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        superseded_version_id: str,
        published_version_id: str,
    ) -> int:
        """WP-05 切片三：发布取代上游基线时按 39 号 §4 StageInvalidated 语义失效下游。

        引用被取代策略版本的测试计划版本转 STALE，其未决审核任务 CANCELLED；
        只失效不删除（历史任务与版本保留）。执行计划级联随 WP-06 ExecutionPlanVersion
        冻结字段落地，本切片不虚构其状态迁移。返回受影响计划版本数。
        """
        affected = 0
        for downstream in self.plan_versions.values():
            if downstream.get("strategyVersionId") != superseded_version_id:
                continue
            if not self._owned_workspace(downstream, tenant_id, workspace_id):
                continue
            if downstream["reviewStatus"] not in {"DRAFT", "PENDING_REVIEW", "APPROVED", "PUBLISHED"}:
                continue
            downstream["reviewStatus"] = "STALE"
            affected += 1
            for task in self.review_tasks.values():
                if task["artifactVersionId"] == downstream["id"] and task["status"] in {"OPEN", "IN_PROGRESS"}:
                    task["status"] = "CANCELLED"
            self._emit(
                "stage.invalidated",
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type="TEST_PLAN",
                subject_id=downstream["testPlanId"],
                payload={
                    "invalidatedVersionId": downstream["id"],
                    "trigger": "UPSTREAM_PUBLISHED_VERSION_SUPERSEDED",
                    "supersededVersionId": superseded_version_id,
                    "publishedVersionId": published_version_id,
                },
            )
        return affected

    @staticmethod
    def _version_content(payload: dict[str, Any]) -> dict[str, Any]:
        """剔除 changeSummary 并将 UUID 归一为字符串，保证摘要计算可序列化且与提交端一致。"""
        return {
            key: str(value) if isinstance(value, uuid.UUID) else value
            for key, value in payload.items()
            if key != "changeSummary"
        }

    def _append_artifact_version(
        self,
        artifact_type: str,
        root: dict[str, Any],
        version_store: dict[str, dict[str, Any]],
        parent_key: str,
        actor_id: str,
        content: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        version_number = 1 + sum(1 for item in version_store.values() if item[parent_key] == root["id"])
        version: dict[str, Any] = {
            "id": _new_id(),
            "tenantId": root["tenantId"],
            "workspaceId": root["workspaceId"],
            parent_key: root["id"],
            "version": version_number,
            "reviewStatus": "PENDING_REVIEW",
            "contentDigest": content_digest(content),
            **content,
            "changeSummary": payload.get("changeSummary"),
            "submittedByUserId": actor_id,
            "createdAt": _now(),
        }
        version_store[version["id"]] = version
        root["currentVersionId"] = version["id"]
        artifact_ref = self._index_version(artifact_type, root["id"], version)
        work_item_id, session_id = self._review_context_of_artifact(root["id"])
        task_id = self._create_review_task(
            tenant_id=root["tenantId"],
            workspace_id=root["workspaceId"],
            work_item_id=work_item_id,
            session_id=session_id,
            owner_id=actor_id,
            artifact=artifact_ref,
        )
        if session_id:
            self.sessions[session_id]["reviewTaskIds"].append(task_id)
        self._emit(
            "artifact.version.generated",
            tenant_id=root["tenantId"],
            workspace_id=root["workspaceId"],
            actor_id=actor_id,
            subject_type=artifact_type,
            subject_id=root["id"],
            payload={"versionId": version["id"], "version": version_number, "reviewTaskId": task_id},
        )
        return version

    def _review_context_of_artifact(self, artifact_id: str) -> tuple[str, str | None]:
        """经既有审核任务反查产出物所属工作项与会话（新版本任务沿用同一审核上下文）。"""
        for task in self.review_tasks.values():
            if task["artifactId"] == artifact_id:
                return task["workItemId"], self.review_to_session.get(task["id"])
        raise DomainError(409, "INVALID_STATE_TRANSITION", "产出物不在任何审核会话中，无法提交新版本")

    async def transition_work_item(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        work_item_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """M1-B1：工作项状态迁移（切片仅支持 REWORK）+ lockVersion 乐观锁。"""
        self._require_capability(capabilities, "work_item.transition")
        serializable_payload = {
            key: str(value) if isinstance(value, uuid.UUID) else value for key, value in payload.items()
        }
        async with self._lock:
            previous_id = self._resolve_idempotency(
                tenant_id, f"transitionWorkItem:{work_item_id}", idempotency_key, serializable_payload
            )
            if previous_id:
                return self._copy(self.work_items[previous_id])
            item = self.work_items.get(work_item_id)
            if not item or not self._owned_workspace(item, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "工作项不存在")
            if payload["lockVersion"] != item["lockVersion"]:
                raise DomainError(409, "STALE_LOCK_VERSION", "乐观锁版本陈旧，请刷新后重试")
            expected = payload.get("expectedCurrentStatus")
            if expected and item["status"] != expected:
                raise DomainError(409, "INVALID_STATE_TRANSITION", "当前状态与预期不符")
            if payload["targetStatus"] != "REWORK":
                raise DomainError(422, "VALIDATION_FAILED", "M1切片仅支持REWORK迁移")
            previous_status = item["status"]
            item.update(
                {
                    "status": "REWORK",
                    "currentActorType": "HUMAN",
                    "currentActorId": actor_id,
                    "lockVersion": item["lockVersion"] + 1,
                    "updatedAt": _now(),
                }
            )
            self._emit(
                "work_item.transitioned",
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type="work_item",
                subject_id=work_item_id,
                payload={"fromStatus": previous_status, "toStatus": "REWORK"},
            )
            self._remember_idempotency(
                tenant_id,
                f"transitionWorkItem:{work_item_id}",
                idempotency_key,
                serializable_payload,
                work_item_id,
            )
            self._persist()
            return self._copy(item)

    def _approve_disabled_reason(self, task: dict[str, Any]) -> str | None:
        """M1-B1 契约先行（墙 M-120）：批准禁用原因，null 表示可批准。

        优先级（M-120 裁决）：会话终态 TASK_CLOSED 最高（会话已终，任务全部关闭）；
        非终态会话内 STALE_VERSION 先于 TASK_CLOSED——陈旧任务的可行
        动作是去审新版本，提示摘要落后比提示已关闭更有指导性。
        """
        session_id = self.review_to_session.get(task["id"])
        session = self.sessions.get(session_id) if session_id else None
        if session and session["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            return "TASK_CLOSED"
        root = self._artifact_roots(task["artifactType"]).get(task["artifactId"])
        if root:
            current = self.version_index.get(root["currentVersionId"])
            if current and current[1]["contentDigest"] != task["contentDigest"]:
                return "STALE_VERSION"
        if task["status"] not in {"OPEN", "IN_PROGRESS"}:
            return "TASK_CLOSED"
        return None

    def _artifact_roots(self, artifact_type: str) -> dict[str, dict[str, Any]]:
        # M3：非正式产出物类型（如 EXECUTION_EVIDENCE）无根集合，返回空 dict 容错
        return {
            "TEST_STRATEGY": self.strategies,
            "TEST_PLAN": self.plans,
            "TEST_CASE": self.test_cases,
            "DEFECT_VERSION": self.defects,
            "TEST_REPORT_VERSION": self.test_reports,
        }.get(artifact_type, {})

    def _public_review_task(self, task: dict[str, Any]) -> dict[str, Any]:
        public = {
            key: deepcopy(value) for key, value in task.items() if key not in {"tenantId", "workspaceId", "decision"}
        }
        public["approveDisabledReason"] = self._approve_disabled_reason(task)
        return public

    async def list_requirements(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        return [
            self._copy(item)
            for item in self.requirements.values()
            if self._owned(item, tenant_id) and item["workspaceId"] == workspace_id
        ]

    async def list_workspaces(self, tenant_id: str, actor_id: str) -> list[dict[str, Any]]:
        return self._store.list_workspaces_for_user(tenant_id, actor_id)

    def set_workspace_pin(self, tenant_id: str, actor_id: str, workspace_id: str, *, pinned: bool) -> dict[str, Any]:
        """WP-01 常用项目固定（用户偏好，天然幂等，不产生领域事件）。

        授权按成员关系校验（可置顶任意成员工作区，不限于当前绑定）。
        """
        if self._store.get_membership_for_workspace(actor_id, tenant_id, workspace_id) is None:
            raise DomainError(403, "FORBIDDEN", "当前身份无权置顶该Workspace")
        self._store.set_workspace_pin(tenant_id, actor_id, workspace_id, pinned, pinned_at=_now())
        return {"workspaceId": workspace_id, "pinned": pinned}

    def archive_release(
        self,
        tenant_id: str,
        capabilities: frozenset[str],
        workspace_id: str,
        release_id: str,
    ) -> dict[str, Any]:
        """WP-01 归档 Release：ACTIVE→ARCHIVED 单向；归档后从切换面消失且建项同码 409。"""
        self._require_capability(capabilities, "release.archive")
        status = self._store.release_status(tenant_id, workspace_id, release_id)
        if status is None:
            raise DomainError(404, "NOT_FOUND", "Release 不存在")
        if status == "ARCHIVED":
            raise DomainError(409, "RELEASE_ALREADY_ARCHIVED", "Release 已归档")
        self._store.archive_release(tenant_id, workspace_id, release_id, updated_at=_now())
        return {"id": release_id, "status": "ARCHIVED", "archivedAt": _now()}

    async def get_project_context_projection(self, tenant_id: str, user_id: str, workspace_id: str) -> dict[str, Any]:
        """WP-01 项目驾驶舱上下文投影（39 号 §7.2 最小切片，只读）。"""
        workspaces = self._store.list_workspaces_for_user(tenant_id, user_id)
        current = next((w for w in workspaces if w["id"] == workspace_id), None)
        if current is None:
            raise DomainError(403, "FORBIDDEN", "当前身份无权访问该Workspace")
        releases = self._store.list_active_releases(tenant_id, workspace_id)
        return {
            "workspace": {
                "id": current["id"],
                "name": current["name"],
                "lastBusinessUpdatedAt": current["lastBusinessUpdatedAt"],
            },
            "currentRelease": (
                {"id": releases[0]["id"], "name": releases[0]["name"], "status": releases[0]["status"]}
                if releases
                else None
            ),
            "pinnedWorkspaces": [
                {"id": w["id"], "name": w["name"], "lastBusinessUpdatedAt": w["lastBusinessUpdatedAt"]}
                for w in workspaces
                if w["pinned"]
            ],
            "openReviewCount": self._store.collection_count(
                "review_tasks", tenant_id, workspace_id, status_in=("OPEN",)
            ),
            "activeWorkItemCount": self._store.collection_count(
                "work_items",
                tenant_id,
                workspace_id,
                status_in=("READY", "IN_PROGRESS", "PENDING_REVIEW", "REWORK", "BLOCKED"),
            ),
            "runningExecutionCount": self._store.collection_count(
                "execution_tasks", tenant_id, workspace_id, status_in=("RUNNING",)
            ),
        }

    def seed_workspace(self, tenant_id: str, user_id: str, workspace_name: str) -> dict[str, Any]:
        """本地联调/测试种子面：为既有用户加第二个工作区（成员关系复制能力集 + 默认 ACTIVE Release）。"""
        workspace_id = self._store.seed_workspace_for_user(tenant_id, user_id, workspace_name, created_at=_now())
        return {"id": workspace_id, "name": workspace_name}

    async def list_releases(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        return self._store.list_active_releases(tenant_id, workspace_id)

    async def list_work_items(
        self,
        tenant_id: str,
        workspace_id: str,
        *,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            self._copy(item)
            for item in self.work_items.values()
            if self._owned(item, tenant_id)
            and item["workspaceId"] == workspace_id
            and (status is None or item["status"] == status)
        ]

    async def sla_overview(
        self,
        tenant_id: str,
        workspace_id: str,
        *,
        now: str | None = None,
    ) -> dict[str, Any]:
        """看板 SLA 面板（M2/U3）：按优先级（P0/P1/P2）分组 + 整体汇总。

        口径（契约描述同步）：SLA 截止 = created_at + 优先级窗口（P0 24h / P1 48h / P2 72h）；
        DONE/APPROVED 且 updatedAt（完成时间）不晚于截止 = met；未完成且当前时间已过截止 = overdue；
        P3 或缺失创建时间（无 due）只计入 total，不计 met/overdue；CANCELLED 只计入 total。
        """
        current = datetime.fromisoformat(now) if now else datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        groups: list[dict[str, Any]] = [
            {"priority": priority, "total": 0, "met": 0, "overdue": 0} for priority in SLA_PRIORITIES
        ]
        group_by_priority = {str(group["priority"]): group for group in groups}
        overall: dict[str, Any] = {"total": 0, "met": 0, "overdue": 0}
        for item in self.work_items.values():
            if not self._owned(item, tenant_id) or item["workspaceId"] != workspace_id:
                continue
            overall["total"] += 1
            priority = item.get("priority")
            if not isinstance(priority, str) or priority not in SLA_WINDOW_HOURS:
                continue  # P3 / 未知优先级：无 SLA 窗口（无 due），不算 overdue
            group = group_by_priority[priority]
            try:
                created = datetime.fromisoformat(item["createdAt"])
            except (KeyError, TypeError, ValueError):
                continue  # 无有效创建时间：无 due，不算 overdue
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            deadline = created + timedelta(hours=SLA_WINDOW_HOURS[priority])
            group["total"] += 1
            if item.get("status") in SLA_COMPLETED_STATUSES:
                try:
                    completed = datetime.fromisoformat(item["updatedAt"])
                except (KeyError, TypeError, ValueError):
                    continue
                if completed.tzinfo is None:
                    completed = completed.replace(tzinfo=UTC)
                if completed <= deadline:
                    group["met"] += 1
                    overall["met"] += 1
            elif item.get("status") != "CANCELLED" and current > deadline:
                group["overdue"] += 1
                overall["overdue"] += 1
        for group in groups:
            group["metRate"] = round(group["met"] / group["total"], 4) if group["total"] else 0.0
        overall["metRate"] = round(overall["met"] / overall["total"], 4) if overall["total"] else 0.0
        return {"overall": overall, "groups": groups}

    async def assign_work_item(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        work_item_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """M2/U4：工作项分派（落库 assigneeId）。

        约束：工作项必须存在且属于该 workspace（否则 404）；重复分派同一 assignee 为幂等
        no-op（返回当前状态，不产生事件）；变更分派时落 updatedAt 并追加 work_item.assigned
        事件（append-only 审计面）。
        """
        self._require_capability(capabilities, "work_item.assign")
        async with self._lock:
            item = self.work_items.get(work_item_id)
            if not item or not self._owned_workspace(item, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "工作项不存在")
            assignee_id = str(payload["assigneeId"])
            previous = item.get("assigneeId")
            if previous != assignee_id:
                item["assigneeId"] = assignee_id
                item["updatedAt"] = _now()
                self._emit(
                    "work_item.assigned",
                    tenant_id=tenant_id,
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    subject_type="work_item",
                    subject_id=work_item_id,
                    payload={"fromAssigneeId": previous, "toAssigneeId": assignee_id},
                )
                self._persist()
            return self._copy(item)

    async def get_work_item(self, tenant_id: str, workspace_id: str, work_item_id: str) -> dict[str, Any]:
        item = self.work_items.get(work_item_id)
        if not item or not self._owned_workspace(item, tenant_id, workspace_id):
            raise DomainError(404, "NOT_FOUND", "工作项不存在")
        return self._copy(item)

    async def list_work_item_runs(self, tenant_id: str, workspace_id: str, work_item_id: str) -> list[dict[str, Any]]:
        """工作项的运行历史（看板 Diff/追溯数据面）：关联 Agent Session 按启动时间倒序。"""
        runs = [
            {
                "sessionId": session["id"],
                "workflowKey": session["workflowKey"],
                "status": session["status"],
                "startedAt": session["startedAt"],
                "completedAt": session["completedAt"],
                "initiatedBy": session["initiatedBy"],
            }
            for session in self.sessions.values()
            if self._owned(session, tenant_id)
            and session["workspaceId"] == workspace_id
            and session["workItemId"] == work_item_id
        ]
        runs.sort(key=lambda run: run["startedAt"], reverse=True)
        return runs

    async def list_review_tasks(
        self,
        tenant_id: str,
        workspace_id: str,
        *,
        assignee_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            self._public_review_task(item)
            for item in self.review_tasks.values()
            if self._owned(item, tenant_id)
            and item["workspaceId"] == workspace_id
            and (status is None or item["status"] == status)
            and (
                assignee_id is None
                or any(str(entry.get("userId")) == assignee_id for entry in item.get("assignments", []))
            )
        ]

    async def create_review_task(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """M2：手工创建审核任务（分派入口）——digest 必须与当前版本一致，否则 409。"""
        self._require_capability(capabilities, "review.create")
        serializable_payload = {
            key: [_serialize_entry(entry) for entry in value] if isinstance(value, list) else _serialize_entry(value)
            for key, value in payload.items()
        }
        async with self._lock:
            previous_id = self._resolve_idempotency(
                tenant_id, "createReviewTask", idempotency_key, serializable_payload
            )
            if previous_id:
                return self._public_review_task(self.review_tasks[previous_id])

            work_item = self.work_items.get(str(payload["workItemId"]))
            if not work_item or not self._owned_workspace(work_item, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "工作项不存在")
            indexed = self.version_index.get(str(payload["artifactVersionId"]))
            if indexed is None or not self._owned(indexed[1], tenant_id):
                raise DomainError(404, "NOT_FOUND", "产出物版本不存在")
            artifact_type, version = indexed
            if artifact_type != payload["artifactType"] or str(version["id"]) != str(payload["artifactVersionId"]):
                raise DomainError(404, "NOT_FOUND", "产出物版本不存在")
            if version["contentDigest"] != payload["contentDigest"]:
                raise DomainError(409, "STALE_ARTIFACT_VERSION", "审核摘要与当前版本不一致")

            review_id = _new_id()
            task = {
                "id": review_id,
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "workItemId": work_item["id"],
                "agentSessionId": None,
                "artifactType": artifact_type,
                "artifactId": str(payload["artifactId"]),
                "artifactVersionId": str(payload["artifactVersionId"]),
                "contentDigest": payload["contentDigest"],
                "policyType": payload["policyType"],
                "minApprovers": 2 if payload["policyType"] == "FOUR_EYES" else 1,
                "approvals": [],
                "status": "OPEN",
                "assignments": [
                    {
                        "userId": str(entry["userId"]),
                        "reviewRole": entry["reviewRole"],
                        "requiredCapability": entry["requiredCapability"],
                    }
                    for entry in payload.get("assignees", [])
                ],
                "createdBy": actor_id,
                "createdAt": _now(),
                "expiresAt": None,
                "decision": None,
            }
            self.review_tasks[review_id] = task
            self._remember_idempotency(tenant_id, "createReviewTask", idempotency_key, serializable_payload, review_id)
            self._persist()
            return self._public_review_task(task)

    async def get_review_task(self, tenant_id: str, workspace_id: str, review_task_id: str) -> dict[str, Any]:
        item = self.review_tasks.get(review_task_id)
        if not item or not self._owned_workspace(item, tenant_id, workspace_id):
            raise DomainError(404, "NOT_FOUND", "审核任务不存在")
        return self._public_review_task(item)

    async def get_review_artifact(self, tenant_id: str, workspace_id: str, review_task_id: str) -> dict[str, Any]:
        task = self.review_tasks.get(review_task_id)
        if not task or not self._owned_workspace(task, tenant_id, workspace_id):
            raise DomainError(404, "NOT_FOUND", "审核任务不存在")
        indexed = self.version_index.get(task["artifactVersionId"])
        if indexed is None:
            raise DomainError(404, "NOT_FOUND", "审核产出物版本不存在")
        artifact_type, version = indexed
        return {
            "artifactType": artifact_type,
            "artifactId": task["artifactId"],
            "artifactVersionId": task["artifactVersionId"],
            "contentDigest": task["contentDigest"],
            "content": {
                key: deepcopy(value) for key, value in version.items() if key not in {"tenantId", "workspaceId"}
            },
        }

    async def get_review_artifact_diff(self, tenant_id: str, workspace_id: str, review_task_id: str) -> dict[str, Any]:
        """审核队列版本 Diff 数据面（10 号 PRD §3）：以任务绑定版本为 head，
        同根兄弟版本中取版本号最大的上一版为 base，服务端计算顶层字段级 diff。
        首版或 base 链断裂时降级 hasBaseline=false（不报错）；只读投影不产生事件。"""
        task = self.review_tasks.get(review_task_id)
        if not task or not self._owned_workspace(task, tenant_id, workspace_id):
            raise DomainError(404, "NOT_FOUND", "审核任务不存在")
        indexed = self.version_index.get(task["artifactVersionId"])
        if indexed is None:
            raise DomainError(404, "NOT_FOUND", "审核产出物版本不存在")
        artifact_type, head = indexed
        root_id = self._artifact_id(head)
        head_number = int(head["version"])
        base: dict[str, Any] | None = None
        for candidate_type, candidate in self.version_index.values():
            if candidate_type != artifact_type or self._artifact_id(candidate) != root_id:
                continue
            number = int(candidate["version"])
            if number >= head_number:
                continue
            if base is None or number > int(base["version"]):
                base = candidate
        result: dict[str, Any] = {
            "artifactType": artifact_type,
            "artifactId": task["artifactId"],
            "artifactVersionId": task["artifactVersionId"],
            "headDigest": head["contentDigest"],
        }
        if base is None:
            result.update(
                {
                    "baseVersionId": None,
                    "baseDigest": None,
                    "hasBaseline": False,
                    "changedCount": 0,
                    "fields": [],
                }
            )
            return result
        excluded = {"tenantId", "workspaceId"}
        base_content = {key: value for key, value in base.items() if key not in excluded}
        head_content = {key: value for key, value in head.items() if key not in excluded}
        fields: list[dict[str, Any]] = []
        for name in sorted(set(base_content) | set(head_content)):
            if name not in base_content:
                fields.append({"field": name, "changeType": "ADDED", "newValue": deepcopy(head_content[name])})
            elif name not in head_content:
                fields.append({"field": name, "changeType": "REMOVED", "oldValue": deepcopy(base_content[name])})
            elif base_content[name] != head_content[name]:
                fields.append(
                    {
                        "field": name,
                        "changeType": "CHANGED",
                        "oldValue": deepcopy(base_content[name]),
                        "newValue": deepcopy(head_content[name]),
                    }
                )
        result.update(
            {
                "baseVersionId": base["id"],
                "baseDigest": base["contentDigest"],
                "hasBaseline": True,
                "changedCount": len(fields),
                "fields": fields,
            }
        )
        return result

    async def list_sessions(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        return [
            self._copy(item)
            for item in self.sessions.values()
            if self._owned(item, tenant_id) and item["workspaceId"] == workspace_id
        ]

    async def get_session(self, tenant_id: str, workspace_id: str, session_id: str) -> dict[str, Any]:
        item = self.sessions.get(session_id)
        if not item or not self._owned_workspace(item, tenant_id, workspace_id):
            raise DomainError(404, "NOT_FOUND", "Agent Session不存在")
        return self._copy(item)

    async def get_trace(self, tenant_id: str, workspace_id: str, session_id: str) -> list[dict[str, Any]]:
        await self.get_session(tenant_id, workspace_id, session_id)
        return deepcopy(self.traces[session_id])

    async def list_strategies(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        return [
            self._copy(item)
            for item in self.strategies.values()
            if self._owned(item, tenant_id) and item["workspaceId"] == workspace_id
        ]

    async def list_plans(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        return [
            self._copy(item)
            for item in self.plans.values()
            if self._owned(item, tenant_id) and item["workspaceId"] == workspace_id
        ]

    async def list_test_cases(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        return [
            self._copy(item)
            for item in self.test_cases.values()
            if self._owned(item, tenant_id) and item["workspaceId"] == workspace_id
        ]

    async def list_test_case_versions(
        self, tenant_id: str, workspace_id: str, test_case_id: str
    ) -> list[dict[str, Any]]:
        root = self.test_cases.get(test_case_id)
        if not root or not self._owned_workspace(root, tenant_id, workspace_id):
            raise DomainError(404, "NOT_FOUND", "测试用例不存在")
        return [
            self._copy(item)
            for item in self.test_case_versions.values()
            if item["testCaseId"] == test_case_id and self._owned(item, tenant_id)
        ]

    # ==================== M3：执行链（计划→启动→结果→不可变证据→人工批准） ====================

    @staticmethod
    def _evidence_digest(stdout: str, stderr: str, exit_code: int) -> str:
        """证据摘要：服务端对 stdout/stderr/exitCode 规范化后计算，客户端无从注入。"""
        return content_digest({"stdout": stdout, "stderr": stderr, "exitCode": exit_code})

    def verify_evidence_integrity(self) -> None:
        """逐条重算存储中证据的摘要；任何不一致即 fail-closed（直写篡改检测）。"""
        for evidence in self._store.load_evidence().values():
            recomputed = self._evidence_digest(evidence["stdout"], evidence["stderr"], evidence["exitCode"])
            if recomputed != evidence["contentDigest"]:
                raise DomainError(409, "EVIDENCE_TAMPERED", "执行证据完整性校验失败")

    def _restore_evidence_from_memory(self) -> None:
        """测试恢复路径：用内存态整体回写证据表，使持久化状态与内存一致。"""
        self._store.replace_evidence(self.execution_evidence)

    def _reload_store_state(self) -> None:
        """模拟进程重启：从存储重新加载全部状态（含证据完整性校验）。"""
        self._load()

    async def create_execution_plan(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_capability(capabilities, "execution.start")
        async with self._lock:
            test_plan = self.plans.get(str(payload["testPlanId"]))
            if not test_plan or not self._owned_workspace(test_plan, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "测试计划不存在")
            now = _now()
            plan_id = _new_id()
            version_id = _new_id()
            content = {
                "testPlanId": test_plan["id"],
                "testPlanVersionId": test_plan["currentVersionId"],
                "planKey": payload["planKey"],
            }
            version = {
                "id": version_id,
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "executionPlanId": plan_id,
                "version": 1,
                "contentDigest": content_digest(content),
                **content,
                "frozenBaselineRef": f"exec-baseline:{version_id[:8]}",
                "status": "FROZEN",
                "createdBy": actor_id,
                "createdAt": now,
            }
            record = {
                "id": plan_id,
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "planKey": payload["planKey"],
                "name": payload["name"],
                "testPlanId": test_plan["id"],
                "currentVersionId": version_id,
                "status": "ACTIVE",
                "createdBy": actor_id,
                "createdAt": now,
            }
            self.execution_plans[plan_id] = record
            self.execution_plan_versions[version_id] = version
            self._persist()
            return self._copy(record)

    async def start_execution(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        execution_plan_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_capability(capabilities, "execution.start")
        serializable_payload = _serialize_entry({**payload, "actorId": actor_id})
        async with self._lock:
            previous_id = self._resolve_idempotency(
                tenant_id, f"startExecutionPlan:{execution_plan_id}", idempotency_key, serializable_payload
            )
            if previous_id:
                return self._copy(self.execution_tasks[previous_id])
            plan = self.execution_plans.get(execution_plan_id)
            if not plan or not self._owned_workspace(plan, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "执行计划不存在")
            version = self.execution_plan_versions.get(str(payload["executionPlanVersionId"]))
            if not version or version["executionPlanId"] != plan["id"]:
                raise DomainError(422, "VALIDATION_FAILED", "执行计划版本不存在或不属于该计划")
            if any(task["executionPlanVersionId"] == version["id"] for task in self.execution_tasks.values()):
                raise DomainError(409, "EXECUTION_ALREADY_RUN", "该执行计划版本已执行，重放被拒绝")

            now = _now()
            task_id = _new_id()
            task = {
                "id": task_id,
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "executionPlanId": plan["id"],
                "executionPlanVersionId": version["id"],
                "runnerId": actor_id,
                "status": "COMPLETED",
                "startedAt": now,
                "completedAt": now,
            }
            work_item_id = self._work_item_of_test_plan(str(plan["testPlanId"]))
            self._emit(
                "execution.started",
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type="execution_task",
                subject_id=task_id,
                payload={"executionPlanId": plan["id"], "executionPlanVersionId": version["id"]},
            )
            for index, case_version in enumerate(
                self._case_versions_for_plan_version(tenant_id, workspace_id, version), start=1
            ):
                result, evidence = self._run_case(task, case_version, index)
                self.execution_results[result["id"]] = result
                self.execution_evidence[evidence["id"]] = evidence
                self._store.append_evidence(evidence)
                self._emit(
                    "evidence.appended",
                    tenant_id=tenant_id,
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    subject_type="execution_evidence",
                    subject_id=evidence["id"],
                    payload={
                        "executionTaskId": task_id,
                        "caseIndex": index,
                        "exitCode": evidence["exitCode"],
                    },
                )
                self._create_evidence_review_task(task, evidence, work_item_id, actor_id)
            self.execution_tasks[task_id] = task
            self._emit(
                "execution.finished",
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type="execution_task",
                subject_id=task_id,
                payload={"status": "COMPLETED"},
            )
            self._remember_idempotency(
                tenant_id,
                f"startExecutionPlan:{execution_plan_id}",
                idempotency_key,
                serializable_payload,
                task_id,
            )
            self._persist()
            return self._copy(task)

    def _work_item_of_test_plan(self, test_plan_id: str) -> str:
        """经既有审核任务反查测试计划所属工作项（证据审核任务挂载同一工作项）。"""
        for task in self.review_tasks.values():
            if task["artifactId"] == test_plan_id:
                return str(task["workItemId"])
        raise DomainError(409, "INVALID_STATE_TRANSITION", "测试计划不在任何审核上下文中，无法绑定证据审核")

    def _case_versions_for_plan_version(
        self, tenant_id: str, workspace_id: str, execution_version: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """按生成会话（agentRunId）圈定基线用例版本；无会话锚点时回退到工作区全量。"""
        plan_version = self.plan_versions.get(str(execution_version["testPlanVersionId"]))
        run_id = plan_version.get("agentRunId") if plan_version else None
        selected = [
            item
            for item in self.test_case_versions.values()
            if self._owned(item, tenant_id)
            and item["workspaceId"] == workspace_id
            and (run_id is None or item.get("agentRunId") == run_id)
        ]
        return sorted(selected, key=lambda item: (item["createdAt"], item["id"]))

    def _run_case(
        self, task: dict[str, Any], case_version: dict[str, Any], index: int
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """确定性参考执行：状态/时长/证据/断言明细均由用例版本摘要推导（C2 不接真实 runner）。"""
        digest = case_version["contentDigest"]
        passed = int(digest[-1], 16) % 2 == 0
        case_status = "PASSED" if passed else "FAILED"
        stdout = f"case={case_version['testCaseId']} step=run result={case_status}\n"
        stderr = "" if passed else f"case={case_version['testCaseId']} assertion mismatch\n"
        exit_code = 0 if passed else 1
        assertions = self._deterministic_assertions(digest, passed)
        evidence_id = _new_id()
        evidence = {
            "id": evidence_id,
            "tenantId": task["tenantId"],
            "workspaceId": task["workspaceId"],
            "executionTaskId": task["id"],
            "caseIndex": index,
            "stdout": stdout,
            "stderr": stderr,
            "exitCode": exit_code,
            # B1：断言结果明细随不可变证据一起只追加落库，供 assertionResultsRef 回溯
            "assertions": assertions,
            "contentDigest": self._evidence_digest(stdout, stderr, exit_code),
            "createdAt": _now(),
        }
        result = {
            "id": _new_id(),
            "tenantId": task["tenantId"],
            "workspaceId": task["workspaceId"],
            "executionTaskId": task["id"],
            "testCaseVersionId": case_version["id"],
            "status": case_status,
            "durationMs": 10 + int(digest[:8], 16) % 41,
            "logRef": f"evidence:{evidence_id}",
            "evidenceDigest": evidence["contentDigest"],
            "resultDigest": self._result_digest(case_status, assertions, stdout, stderr),
            "assertionResultsRef": f"evidence:{evidence_id}/assertions",
            "createdAt": _now(),
        }
        return result, evidence

    @staticmethod
    def _deterministic_assertions(digest: str, passed: bool) -> list[dict[str, Any]]:
        """B1 断言结果明细：与确定性参考执行同源，全部由用例版本摘要推导。

        通过用例断言全部 PASSED；失败用例至少一条 FAILED，与 stderr 的 assertion
        mismatch 口径一致，保证 assertionResultsRef 可回溯且语义自洽。
        """
        total = 1 + int(digest[:4], 16) % 5  # 1..5 条断言
        failed_count = 0 if passed else 1 + int(digest[4:8], 16) % total
        return [
            {
                "key": f"assert-{position}",
                "expectation": f"step-{position} matches reference",
                "actual": (
                    f"step-{position} matches reference"
                    if position > failed_count
                    else f"step-{position} diverges from reference"
                ),
                "outcome": "PASSED" if position > failed_count else "FAILED",
            }
            for position in range(1, total + 1)
        ]

    @staticmethod
    def _result_digest(status: str, assertions: list[dict[str, Any]], stdout: str, stderr: str) -> str:
        """B1 结果摘要：服务端基于断言统计与结果状态/文本规范化计算，客户端不可注入。"""
        passed_count = sum(1 for assertion in assertions if assertion["outcome"] == "PASSED")
        return content_digest(
            {
                "status": status,
                "assertionStats": {
                    "total": len(assertions),
                    "passed": passed_count,
                    "failed": len(assertions) - passed_count,
                },
                "resultText": (stdout + stderr).strip(),
            }
        )

    def _create_evidence_review_task(
        self,
        task: dict[str, Any],
        evidence: dict[str, Any],
        work_item_id: str,
        owner_id: str,
    ) -> str:
        """内联构造证据审核任务（不复用 _create_review_task，避免会话/快照交叉写入）。"""
        review_id = _new_id()
        review_task = {
            "id": review_id,
            "tenantId": task["tenantId"],
            "workspaceId": task["workspaceId"],
            "workItemId": work_item_id,
            "agentSessionId": None,
            "artifactType": "EXECUTION_EVIDENCE",
            "artifactId": task["id"],
            "artifactVersionId": evidence["id"],
            "contentDigest": evidence["contentDigest"],
            "policyType": "SINGLE_REVIEW",
            "minApprovers": 1,
            "approvals": [],
            "status": "OPEN",
            "assignments": [
                {
                    "userId": owner_id,
                    "reviewRole": "APPROVER",
                    "requiredCapability": APPROVAL_CAPABILITIES["EXECUTION_EVIDENCE"],
                }
            ],
            "createdBy": owner_id,
            "createdAt": _now(),
            "expiresAt": None,
            "decision": None,
        }
        self.review_tasks[review_id] = review_task
        return review_id

    async def list_execution_tasks(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        return [
            self._copy(item)
            for item in self.execution_tasks.values()
            if self._owned(item, tenant_id) and item["workspaceId"] == workspace_id
        ]

    async def list_execution_plans(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        """批次四十六：执行计划列表（契约已有 listExecutionPlans，补后端路由）。"""
        return [
            self._copy(item)
            for item in self.execution_plans.values()
            if self._owned(item, tenant_id) and item["workspaceId"] == workspace_id
        ]

    async def list_execution_results(
        self, tenant_id: str, workspace_id: str, execution_task_id: str
    ) -> list[dict[str, Any]]:
        task = self.execution_tasks.get(execution_task_id)
        if not task or not self._owned_workspace(task, tenant_id, workspace_id):
            raise DomainError(404, "NOT_FOUND", "执行任务不存在")
        return [
            self._copy(item)
            for item in self.execution_results.values()
            if item["executionTaskId"] == execution_task_id and self._owned(item, tenant_id)
        ]

    # ==================== M4：质量域（分析→聚类→缺陷→同步→报告→覆盖率→知识回流） ====================

    # 覆盖率五类口径维度字段（分母互不推导，必须客户端显式提供）
    COVERAGE_DIMENSION_KEYS = (
        "ruleDimension",
        "scenarioDimension",
        "stateDimension",
        "assertionDimension",
        "apiDimension",
    )

    # 同步回执摘要参与字段（B2-4：回执可验证、不可伪造）
    _RECEIPT_DIGEST_FIELDS = (
        "id",
        "defectId",
        "defectVersionId",
        "integrationId",
        "operation",
        "payloadDigest",
        "createdAt",
    )

    async def create_result_analysis(
        self,
        tenant_id: str,
        workspace_id: str,
        capabilities: frozenset[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """结果分析：只引用执行结果读证据；结论（事实/推断/决定）确定性推导，摘要服务端算。"""
        self._require_capability(capabilities, "quality.write")
        async with self._lock:
            refs = [str(ref) for ref in payload["executionResultRefs"]]
            results: list[dict[str, Any]] = []
            for ref in refs:
                result = self.execution_results.get(ref)
                if not result or not self._owned_workspace(result, tenant_id, workspace_id):
                    raise DomainError(404, "NOT_FOUND", "执行结果不存在")
                results.append(result)
            status_counts: dict[str, int] = {}
            for result in results:
                status_counts[result["status"]] = status_counts.get(result["status"], 0) + 1
            failed = [item for item in results if item["status"] in {"FAILED", "ERROR"}]
            cluster_keys = self._upsert_failure_clusters(tenant_id, workspace_id, failed)
            conclusion = {
                "facts": {"resultCount": len(results), "statusCounts": status_counts, "executionResultRefs": refs},
                "inferences": {"failureClusterKeys": sorted(set(cluster_keys))},
                "decisions": {"recommendation": "OPEN_DEFECT_REVIEW" if failed else "ACCEPT_AS_IS"},
            }
            now = _now()
            record = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "releaseId": str(payload["releaseId"]),
                "analysisKey": payload["analysisKey"],
                "executionResultRefs": refs,
                "conclusion": conclusion,
                "conclusionRef": None,
                "status": "ACTIVE",
                "reviewStatus": "DRAFT",
                "contentDigest": content_digest(conclusion),
                "createdAt": now,
            }
            record["conclusionRef"] = f"analysis:{record['id'][:8]}"
            self.result_analyses[record["id"]] = record
            self._persist()
            return self._copy(record)

    def _upsert_failure_clusters(
        self, tenant_id: str, workspace_id: str, failed_results: list[dict[str, Any]]
    ) -> list[str]:
        """失败聚类（与 Defect 分离）：status+stderr 签名确定性派生 clusterKey，同签名归并。"""
        keys: list[str] = []
        for result in sorted(failed_results, key=lambda item: (item["createdAt"], item["id"])):
            evidence_id = str(result["logRef"]).removeprefix("evidence:")
            evidence = self.execution_evidence.get(evidence_id)
            cluster_key = content_digest({"status": result["status"], "stderr": evidence["stderr"] if evidence else ""})
            existing = next(
                (
                    cluster
                    for cluster in self.failure_clusters.values()
                    if cluster["tenantId"] == tenant_id
                    and cluster["workspaceId"] == workspace_id
                    and cluster["clusterKey"] == cluster_key
                ),
                None,
            )
            if existing is not None:
                existing["memberCount"] += 1
            else:
                cluster_id = _new_id()
                self.failure_clusters[cluster_id] = {
                    "id": cluster_id,
                    "tenantId": tenant_id,
                    "workspaceId": workspace_id,
                    "executionTaskId": result["executionTaskId"],
                    "clusterKey": cluster_key,
                    "memberCount": 1,
                    "status": "OPEN",
                    "createdAt": _now(),
                }
            keys.append(cluster_key)
        return keys

    async def list_failure_clusters(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        return [
            self._copy(item)
            for item in self.failure_clusters.values()
            if self._owned(item, tenant_id) and item["workspaceId"] == workspace_id
        ]

    async def list_defects(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        return [
            self._copy(item)
            for item in self.defects.values()
            if self._owned(item, tenant_id) and item["workspaceId"] == workspace_id
        ]

    async def create_defect(
        self,
        tenant_id: str,
        workspace_id: str,
        capabilities: frozenset[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """立 Defect：createdFromWorkItemId 必须存在；根生命周期从 NEW 起步。"""
        self._require_capability(capabilities, "quality.write")
        async with self._lock:
            work_item = self.work_items.get(str(payload["createdFromWorkItemId"]))
            if not work_item or not self._owned_workspace(work_item, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "来源工作项不存在")
            now = _now()
            record = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "releaseId": str(payload["releaseId"]),
                "defectKey": payload["defectKey"],
                "createdFromWorkItemId": work_item["id"],
                "lifecycleStatus": "NEW",
                "currentVersionId": None,
                "approvedVersionId": None,
                "assigneeId": None,
                "duplicateOfDefectId": None,
                "createdAt": now,
            }
            self.defects[record["id"]] = record
            self._persist()
            return self._copy(record)

    async def create_defect_version(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        defect_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """缺陷版本（不可变）：自动创建 DEFECT_VERSION 审核任务，批准后才可外部同步。"""
        self._require_capability(capabilities, "quality.write")
        async with self._lock:
            root = self.defects.get(defect_id)
            if not root or not self._owned_workspace(root, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "缺陷不存在")
            content = json.loads(json.dumps(payload, default=str))
            version_number = 1 + sum(1 for item in self.defect_versions.values() if item["defectId"] == root["id"])
            version: dict[str, Any] = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "defectId": root["id"],
                "version": version_number,
                "reviewStatus": "PENDING_REVIEW",
                "contentDigest": content_digest(content),
                **content,
                "submittedByUserId": actor_id,
                "createdAt": _now(),
            }
            self.defect_versions[version["id"]] = version
            root["currentVersionId"] = version["id"]
            artifact_ref = self._index_version("DEFECT_VERSION", root["id"], version)
            self._create_review_task(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                work_item_id=str(root["createdFromWorkItemId"]),
                session_id=None,
                owner_id=actor_id,
                artifact=artifact_ref,
            )
            self._emit(
                "defect.version.created",
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type="defect",
                subject_id=defect_id,
                payload={
                    "versionId": version["id"],
                    "version": version_number,
                    "lifecycleStatus": root["lifecycleStatus"],
                },
            )
            self._persist()
            return self._copy(version)

    async def create_defect_sync_attempt(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        defect_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """外部同步尝试（B2-4）：必须引用已批准的缺陷版本审核；payload 摘要服务端重算；
        deterministic-local 运行时直接回执 ACKNOWLEDGED + receiptDigest；payload 只写不落库。"""
        self._require_capability(capabilities, "quality.sync")
        serializable_payload = _serialize_entry({**payload, "actorId": actor_id})
        async with self._lock:
            previous_id = self._resolve_idempotency(
                tenant_id, f"createDefectSyncAttempt:{defect_id}", idempotency_key, serializable_payload
            )
            if previous_id:
                return self._copy(self.defect_sync_attempts[previous_id])
            root = self.defects.get(defect_id)
            if not root or not self._owned_workspace(root, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "缺陷不存在")
            version = self.defect_versions.get(str(payload["defectVersionId"]))
            if not version or version["defectId"] != root["id"]:
                raise DomainError(422, "VALIDATION_FAILED", "缺陷版本不存在或不属于该缺陷")
            approval = self.review_tasks.get(str(payload["approvalId"]))
            if (
                not approval
                or not self._owned_workspace(approval, tenant_id, workspace_id)
                or approval["status"] != "APPROVED"
                or str(approval["artifactVersionId"]) != str(payload["defectVersionId"])
            ):
                raise DomainError(403, "FORBIDDEN", "外部同步必须引用已批准的缺陷版本审核")
            expected_digest = content_digest(payload.get("payload") or {})
            if payload["payloadDigest"] != expected_digest:
                raise DomainError(
                    422,
                    "PAYLOAD_DIGEST_MISMATCH",
                    "同步载荷摘要与服务端重算不一致",
                    {"expectedDigest": expected_digest},
                )
            now = _now()
            attempt: dict[str, Any] = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "defectId": root["id"],
                "defectVersionId": str(payload["defectVersionId"]),
                "integrationId": str(payload["integrationId"]),
                "externalDefectLinkId": (
                    str(payload["externalDefectLinkId"]) if payload.get("externalDefectLinkId") else None
                ),
                "operation": payload["operation"],
                "payloadDigest": payload["payloadDigest"],
                "approvalId": str(payload["approvalId"]),
                "status": "ACKNOWLEDGED",
                "receiptDigest": None,
                "requestedBy": actor_id,
                "createdAt": now,
            }
            attempt["receiptDigest"] = content_digest({key: attempt[key] for key in self._RECEIPT_DIGEST_FIELDS})
            self.defect_sync_attempts[attempt["id"]] = attempt
            self._remember_idempotency(
                tenant_id,
                f"createDefectSyncAttempt:{defect_id}",
                idempotency_key,
                serializable_payload,
                attempt["id"],
            )
            self._persist()
            return self._copy(attempt)

    async def list_test_reports(
        self, tenant_id: str, workspace_id: str, *, release_id: str | None = None
    ) -> list[dict[str, Any]]:
        return [
            self._copy(item)
            for item in self.test_reports.values()
            if self._owned(item, tenant_id)
            and item["workspaceId"] == workspace_id
            and (release_id is None or item["releaseId"] == release_id)
        ]

    async def create_test_report(
        self,
        tenant_id: str,
        workspace_id: str,
        capabilities: frozenset[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """测试报告根：ACTIVE + currentVersionId/publishedVersionId 双指针（签署对象归后续切片）。
        P0-1 裁决：根层仅承载身份与状态指针，快照引用下沉版本层。"""
        self._require_capability(capabilities, "quality.write")
        async with self._lock:
            now = _now()
            record = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "releaseId": str(payload["releaseId"]),
                "reportKey": payload["reportKey"],
                "status": "ACTIVE",
                "currentVersionId": None,
                "publishedVersionId": None,
                "createdAt": now,
                "updatedAt": now,
            }
            self.test_reports[record["id"]] = record
            self._persist()
            return self._copy(record)

    async def list_test_report_versions(
        self, tenant_id: str, workspace_id: str, test_report_id: str
    ) -> list[dict[str, Any]]:
        root = self.test_reports.get(test_report_id)
        if not root or not self._owned_workspace(root, tenant_id, workspace_id):
            raise DomainError(404, "NOT_FOUND", "测试报告不存在")
        return [
            self._copy(item)
            for item in self.test_report_versions.values()
            if item["testReportId"] == test_report_id and self._owned(item, tenant_id)
        ]

    async def create_test_report_version(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        test_report_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """报告版本（不可变）：自动创建 TEST_REPORT_VERSION 审核任务，批准后回填根 currentVersionId。
        报告版本不入事件登记表（10 类 EVENT_TYPES 钉死，指标无依赖）。"""
        self._require_capability(capabilities, "quality.write")
        async with self._lock:
            root = self.test_reports.get(test_report_id)
            if not root or not self._owned_workspace(root, tenant_id, workspace_id):
                raise DomainError(404, "NOT_FOUND", "测试报告不存在")
            content = json.loads(json.dumps(payload, default=str))
            siblings = [item for item in self.test_report_versions.values() if item["testReportId"] == root["id"]]
            version_number = 1 + len(siblings)
            supersedes = max(siblings, key=lambda item: int(item["version"])) if siblings else None
            version: dict[str, Any] = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "testReportId": root["id"],
                "version": version_number,
                "reviewStatus": "PENDING_REVIEW",
                "contentDigest": content_digest(content),
                "supersedesVersionId": str(supersedes["id"]) if supersedes else None,
                **content,
                "generatedByAgentId": None,
                "agentRunId": None,
                "createdBy": actor_id,
                "createdAt": _now(),
            }
            self.test_report_versions[version["id"]] = version
            artifact_ref = self._index_version("TEST_REPORT_VERSION", root["id"], version)
            # 报告根无工作项归属：审核任务 workItemId 为 None（不参会话收敛）
            self._create_review_task(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                work_item_id=None,
                session_id=None,
                owner_id=actor_id,
                artifact=artifact_ref,
            )
            self._persist()
            return self._copy(version)

    async def list_coverage_reports(
        self, tenant_id: str, workspace_id: str, *, release_id: str | None = None
    ) -> list[dict[str, Any]]:
        return [
            self._copy(item)
            for item in self.coverage_reports.values()
            if self._owned(item, tenant_id)
            and item["workspaceId"] == workspace_id
            and (release_id is None or item["releaseId"] == release_id)
        ]

    async def create_coverage_report(
        self,
        tenant_id: str,
        workspace_id: str,
        capabilities: frozenset[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """覆盖率报告：五类口径分母互不推导——维度必须显式提供；EFFECTIVE 强制 ruleDimension；
        verdict 由服务端基于维度汇总计算，不接受客户端传入。"""
        self._require_capability(capabilities, "quality.write")
        async with self._lock:
            dimensions = {key: payload[key] for key in self.COVERAGE_DIMENSION_KEYS if payload.get(key)}
            if not dimensions:
                raise DomainError(422, "VALIDATION_FAILED", "覆盖率维度必须显式提供，不得由服务端推导")
            denominator = payload["denominatorDefinitionRef"]
            if denominator == "EFFECTIVE" and "ruleDimension" not in dimensions:
                raise DomainError(422, "VALIDATION_FAILED", "EFFECTIVE口径必须显式提供ruleDimension")
            covered = sum(int(dim.get("covered", 0)) for dim in dimensions.values())
            total = sum(int(dim.get("total", 0)) for dim in dimensions.values())
            if total > 0 and covered == total:
                verdict = "SATISFIED"
            elif covered > 0:
                verdict = "PARTIAL"
            else:
                verdict = "INSUFFICIENT"
            now = _now()
            record: dict[str, Any] = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "releaseId": str(payload["releaseId"]),
                "denominatorDefinitionRef": denominator,
                "scopeSnapshotRef": payload["scopeSnapshotRef"],
                **dimensions,
                "verdict": verdict,
                "contentDigest": content_digest(
                    {
                        "denominatorDefinitionRef": denominator,
                        "scopeSnapshotRef": payload["scopeSnapshotRef"],
                        "dimensions": dimensions,
                        "verdict": verdict,
                    }
                ),
                "createdAt": now,
            }
            self.coverage_reports[record["id"]] = record
            self._persist()
            return self._copy(record)

    async def create_knowledge_entry(
        self,
        tenant_id: str,
        workspace_id: str,
        capabilities: frozenset[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """知识回流切片：沉淀质量域经验为可检索知识条目。"""
        self._require_capability(capabilities, "knowledge.publish")
        async with self._lock:
            record = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "knowledgeKey": payload["knowledgeKey"],
                "category": payload["category"],
                "status": "ACTIVE",
                "createdAt": _now(),
            }
            self.knowledge_entries[record["id"]] = record
            self._persist()
            return self._copy(record)

    async def list_knowledge_entries(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        """批次四十六：知识条目列表（契约已有 listKnowledgeEntries，补后端路由）。"""
        return [
            self._copy(item)
            for item in self.knowledge_entries.values()
            if self._owned(item, tenant_id) and item["workspaceId"] == workspace_id
        ]

    # ==================== 平台域：环境（批次四十六联调面补齐） ====================

    async def list_environments(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        """环境列表（契约 listEnvironments，只读投影不产生事件）。"""
        return [
            self._copy(item)
            for item in self.environments.values()
            if self._owned(item, tenant_id) and item["workspaceId"] == workspace_id
        ]

    async def create_environment(
        self,
        tenant_id: str,
        workspace_id: str,
        capabilities: frozenset[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """环境创建（契约 createEnvironment）：workspaceId 取自路径参数，请求体不带工作区字段。"""
        self._require_capability(capabilities, "environment.create")
        async with self._lock:
            record = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "name": payload["name"],
                "environmentType": payload["environmentType"],
                "endpointMappings": payload["endpointMappings"],
                "capabilities": payload.get("capabilities") or {},
                "secretRefs": payload.get("secretRefs") or [],
                "createdAt": _now(),
            }
            self.environments[record["id"]] = record
            self._persist()
            return self._copy(record)

    # ==================== WP-03 协作对话（批次五十四，39 号 §3 最小切片） ====================

    async def create_conversation(
        self,
        tenant_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_capability(capabilities, "conversation.write")
        workspace_id = str(payload["workspaceId"])
        serializable_payload = {key: str(value) for key, value in payload.items()}
        async with self._lock:
            previous_id = self._resolve_idempotency(
                tenant_id, "createConversation", idempotency_key, serializable_payload
            )
            if previous_id:
                return self._copy(self.conversations[previous_id])
            now = _now()
            record: dict[str, Any] = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "releaseId": str(payload["releaseId"]) if payload.get("releaseId") else None,
                "workItemId": str(payload["workItemId"]) if payload.get("workItemId") else None,
                "title": str(payload.get("title") or "未命名会话"),
                "status": "ACTIVE",
                "createdBy": actor_id,
                "lastActivityAt": now,
                "createdAt": now,
            }
            self.conversations[record["id"]] = record
            self._persist()
            self._remember_idempotency(
                tenant_id, "createConversation", idempotency_key, serializable_payload, record["id"]
            )
            return self._copy(record)

    async def list_conversations(
        self, tenant_id: str, workspace_id: str, *, release_id: str | None = None
    ) -> list[dict[str, Any]]:
        return [
            self._copy(item)
            for item in self.conversations.values()
            if self._owned(item, tenant_id)
            and item["workspaceId"] == workspace_id
            and item["status"] == "ACTIVE"
            and (release_id is None or item.get("releaseId") == release_id)
        ]

    def conversation_in_workspace(self, tenant_id: str, workspace_id: str, conversation_id: str) -> dict[str, Any]:
        record = self.conversations.get(conversation_id)
        if record is None or not self._owned(record, tenant_id) or record["workspaceId"] != workspace_id:
            raise DomainError(404, "NOT_FOUND", "会话不存在")
        return record

    async def create_conversation_message(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        conversation_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """追加对话消息（只追加）。

        actorType=USER 由令牌决定；AGENT 消息需归属会话的 Session 证明，
        本切片无会话映射面，AGENT 一律 403（fail-closed，契约描述一致）。
        """
        self._require_capability(capabilities, "conversation.write")
        if actor_type == "AGENT":
            raise DomainError(403, "FORBIDDEN", "AGENT 消息需归属会话的 Session 证明（本切片未开放）")
        self.conversation_in_workspace(tenant_id, workspace_id, conversation_id)
        serializable_payload = {key: str(value) for key, value in payload.items()}
        async with self._lock:
            previous_id = self._resolve_idempotency(
                tenant_id, "createConversationMessage", idempotency_key, serializable_payload
            )
            if previous_id:
                return self._copy(self.conversation_messages[previous_id])
            now = _now()
            record = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "conversationId": conversation_id,
                "actorType": actor_type,
                "actorId": actor_id,
                "messageType": payload["messageType"],
                "contentRef": payload["contentRef"],
                "contentDigest": payload["contentDigest"],
                "dataClass": payload["dataClass"],
                "createdAt": now,
            }
            self.conversation_messages[record["id"]] = record
            self.conversations[conversation_id]["lastActivityAt"] = now
            self._persist()
            self._remember_idempotency(
                tenant_id,
                "createConversationMessage",
                idempotency_key,
                serializable_payload,
                record["id"],
            )
            self._events.emit(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type="conversation",
                subject_id=conversation_id,
                event_type="conversation.message.appended",
                payload={"messageId": record["id"], "messageType": record["messageType"]},
            )
            return self._copy(record)

    async def list_conversation_messages(
        self, tenant_id: str, workspace_id: str, conversation_id: str
    ) -> list[dict[str, Any]]:
        self.conversation_in_workspace(tenant_id, workspace_id, conversation_id)
        return [
            self._copy(item)
            for item in sorted(self.conversation_messages.values(), key=lambda m: (m["createdAt"], m["id"]))
            if self._owned(item, tenant_id)
            and item["workspaceId"] == workspace_id
            and item["conversationId"] == conversation_id
        ]

    # ==================== WP-03 澄清链路（批次五十五，39 号 §3 切片二） ====================

    def _session_in_tenant(self, tenant_id: str, session_id: str) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        if session is None or not self._owned(session, tenant_id):
            raise DomainError(404, "NOT_FOUND", "Session 不存在")
        return session

    async def create_clarification_request(
        self,
        tenant_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        idempotency_key: str,
        session_id: str,
        payload: dict[str, Any],
        *,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """AI 发起澄清并阻塞会话（AGENT/SERVICE 角色面；USER 冒用 403）。

        HTTP raise 路由保持延期：本地认证只签发 USER 令牌，正路经 agent 运行时内部调用。
        """
        self._require_capability(capabilities, "clarification.raise")
        if actor_type not in {"AGENT", "SERVICE"}:
            raise DomainError(403, "FORBIDDEN", "澄清只能由 Agent 会话链路发起")
        session = self._session_in_tenant(tenant_id, session_id)
        if session["status"] in {"SUCCEEDED", "FAILED"}:
            raise DomainError(409, "INVALID_STATE_TRANSITION", "Session 已终态，不能发起澄清")
        if conversation_id is not None:
            conversation = self.conversations.get(conversation_id)
            if conversation is None or not self._owned(conversation, tenant_id):
                raise DomainError(404, "NOT_FOUND", "会话不存在")
            if conversation["workspaceId"] != session["workspaceId"]:
                raise DomainError(403, "FORBIDDEN", "会话不属于该 Session 的 Workspace")
        serializable_payload = {key: str(value) for key, value in payload.items()}
        async with self._lock:
            previous_id = self._resolve_idempotency(
                tenant_id, "createClarificationRequest", idempotency_key, serializable_payload
            )
            if previous_id:
                return self._copy(self.clarifications[previous_id])
            record: dict[str, Any] = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": session["workspaceId"],
                "conversationId": conversation_id,
                "agentSessionId": session_id,
                "workItemId": session.get("workItemId"),
                "question": payload["question"],
                "reason": payload["reason"],
                "impact": payload["impact"],
                "requiredBy": payload.get("requiredBy"),
                "status": "OPEN",
                "createdAt": _now(),
            }
            self.clarifications[record["id"]] = record
            # 提出后归属 Session 转 BLOCKED（已在 BLOCKED 保持）
            if session["status"] == "RUNNING":
                session["status"] = "BLOCKED"
                session["updatedAt"] = _now()
            self._persist()
            self._remember_idempotency(
                tenant_id, "createClarificationRequest", idempotency_key, serializable_payload, record["id"]
            )
            self._events.emit(
                tenant_id=tenant_id,
                workspace_id=session["workspaceId"],
                actor_id=actor_id,
                subject_type="clarification",
                subject_id=record["id"],
                event_type="clarification.requested",
                payload={"agentSessionId": session_id, "question": payload["question"]},
            )
            return self._copy(record)

    async def list_clarification_requests(
        self, tenant_id: str, workspace_id: str, session_id: str
    ) -> list[dict[str, Any]]:
        session = self._session_in_tenant(tenant_id, session_id)
        if session["workspaceId"] != workspace_id:
            raise DomainError(403, "FORBIDDEN", "Session 不属于当前Workspace")
        return [
            self._copy(item)
            for item in sorted(self.clarifications.values(), key=lambda c: (c["createdAt"], c["id"]))
            if self._owned(item, tenant_id)
            and item["agentSessionId"] == session_id
            and item["workspaceId"] == workspace_id
        ]

    async def respond_clarification(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        clarification_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """人工答复澄清并形成 CONFIRMED 证据（仅 USER；答复后解除 Session BLOCKED）。"""
        self._require_capability(capabilities, "clarification.respond")
        if actor_type != "USER":
            raise DomainError(403, "FORBIDDEN", "澄清只能由人工答复")
        clarification = self.clarifications.get(clarification_id)
        if clarification is None or not self._owned(clarification, tenant_id):
            raise DomainError(404, "NOT_FOUND", "澄清请求不存在")
        if clarification["workspaceId"] != workspace_id:
            raise DomainError(403, "FORBIDDEN", "澄清请求不属于当前Workspace")
        serializable_payload = {key: str(value) for key, value in payload.items()}
        async with self._lock:
            # 幂等重放先于状态校验：同键同指纹返回原结果（状态已推进不打断重放）
            previous_id = self._resolve_idempotency(
                tenant_id, "respondClarification", idempotency_key, serializable_payload
            )
            if previous_id:
                return self._copy(self.clarification_responses[previous_id])
            if clarification["status"] == "ANSWERED":
                raise DomainError(409, "CLARIFICATION_ALREADY_ANSWERED", "澄清已答复")
            if clarification["status"] != "OPEN":
                raise DomainError(409, "CLARIFICATION_NOT_OPEN", f"澄清状态为 {clarification['status']}，不可答复")
            now = _now()
            response: dict[str, Any] = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "requestId": clarification_id,
                "answerRef": payload["answerRef"],
                "answerDigest": payload["answerDigest"],
                "respondedBy": actor_id,
                "respondedAt": now,
                "evidenceClass": "CONFIRMED",
            }
            self.clarification_responses[response["id"]] = response
            clarification["status"] = "ANSWERED"
            # 答复后解除 BLOCKED：归属 Session 无其他 OPEN 澄清则回到 RUNNING
            session = self.sessions.get(str(clarification["agentSessionId"]))
            if session is not None and session["status"] == "BLOCKED":
                still_open = any(
                    item["agentSessionId"] == clarification["agentSessionId"] and item["status"] == "OPEN"
                    for item in self.clarifications.values()
                )
                if not still_open:
                    session["status"] = "RUNNING"
                    session["updatedAt"] = now
            self._persist()
            self._remember_idempotency(
                tenant_id, "respondClarification", idempotency_key, serializable_payload, response["id"]
            )
            self._events.emit(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type="clarification",
                subject_id=clarification_id,
                event_type="clarification.responded",
                payload={"evidenceClass": "CONFIRMED"},
            )
            return self._copy(response)

    # ==================== WP-03 任务卡与 AgentPlan（批次五十六，39 号 §3 切片三） ====================

    def _work_item_in_workspace(self, tenant_id: str, workspace_id: str, work_item_id: str) -> dict[str, Any]:
        item = self.work_items.get(work_item_id)
        if item is None or not self._owned(item, tenant_id):
            raise DomainError(404, "NOT_FOUND", "工作项不存在")
        if item["workspaceId"] != workspace_id:
            raise DomainError(403, "FORBIDDEN", "工作项不属于当前Workspace")
        return item

    async def create_task_card(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        capabilities: frozenset[str],
        idempotency_key: str,
        work_item_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """固化正式任务输入：提交即 SUBMITTED（对话生成或人工填写），后续变更走新版本取代。"""
        self._require_capability(capabilities, "task_card.create")
        work_item = self._work_item_in_workspace(tenant_id, workspace_id, work_item_id)
        release_id = str(payload["releaseId"]) if payload.get("releaseId") else work_item.get("releaseId")
        if not release_id:
            raise DomainError(409, "TASK_CARD_REQUIRES_RELEASE", "交付任务的任务卡必须携带 Release")
        # 未解澄清阻塞固化（高风险假设不得静默进入正式输入）
        open_clarifications = [
            item
            for item in self.clarifications.values()
            if item["status"] == "OPEN"
            and item["workspaceId"] == workspace_id
            and self.sessions.get(str(item["agentSessionId"]), {}).get("workItemId") == work_item_id
        ]
        if open_clarifications:
            raise DomainError(409, "CLARIFICATION_OPEN", "存在未解澄清，先答复再固化任务卡")
        serializable_payload = {key: str(value) for key, value in payload.items()}
        async with self._lock:
            previous_id = self._resolve_idempotency(tenant_id, "createTaskCard", idempotency_key, serializable_payload)
            if previous_id:
                return self._copy(self.task_cards[previous_id])
            now = _now()
            body = {
                "objective": payload["objective"],
                "scope": payload["scope"],
                "inputRefs": payload.get("inputRefs") or [],
                "deliverables": payload.get("deliverables") or [],
                "acceptanceCriteria": payload["acceptanceCriteria"],
                "constraints": payload["constraints"],
                "riskClass": payload.get("riskClass"),
                "requestedPermissions": payload["requestedPermissions"],
                "budget": payload["budget"],
            }
            record: dict[str, Any] = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "conversationId": str(payload["conversationId"]) if payload.get("conversationId") else None,
                "workItemId": work_item_id,
                "releaseId": release_id,
                **body,
                "status": "SUBMITTED",
                "contentDigest": content_digest(body),
                "createdAt": now,
            }
            # 提交后不可静默扩展：同工作项旧卡（SUBMITTED/ACTIVE）被新版本取代
            for card in self.task_cards.values():
                if (
                    card["workItemId"] == work_item_id
                    and self._owned(card, tenant_id)
                    and card["status"] in {"SUBMITTED", "ACTIVE"}
                ):
                    card["status"] = "SUPERSEDED"
            self.task_cards[record["id"]] = record
            self._persist()
            self._remember_idempotency(tenant_id, "createTaskCard", idempotency_key, serializable_payload, record["id"])
            self._events.emit(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type="task_card",
                subject_id=record["id"],
                event_type="task_card.created",
                payload={"workItemId": work_item_id, "contentDigest": record["contentDigest"]},
            )
            return self._copy(record)

    async def list_task_cards(self, tenant_id: str, workspace_id: str, work_item_id: str) -> list[dict[str, Any]]:
        """工作项的任务卡版本列表（SUPERSEDED 留痕，批次六十一）。"""
        self._work_item_in_workspace(tenant_id, workspace_id, work_item_id)
        return [
            self._copy(item)
            for item in sorted(self.task_cards.values(), key=lambda c: (c["createdAt"], c["id"]))
            if self._owned(item, tenant_id)
            and item["workspaceId"] == workspace_id
            and item["workItemId"] == work_item_id
        ]

    async def list_agent_plans(self, tenant_id: str, workspace_id: str, work_item_id: str) -> list[dict[str, Any]]:
        self._require_workspace_scope(tenant_id, workspace_id, work_item_id)
        return [
            self._copy(item)
            for item in sorted(self.agent_plans.values(), key=lambda p: (p["planVersion"], p["id"]))
            if self._owned(item, tenant_id)
            and item["workspaceId"] == workspace_id
            and item["workItemId"] == work_item_id
        ]

    def _require_workspace_scope(self, tenant_id: str, workspace_id: str, work_item_id: str) -> dict[str, Any]:
        return self._work_item_in_workspace(tenant_id, workspace_id, work_item_id)

    async def create_agent_plan(
        self,
        tenant_id: str,
        workspace_id: str,
        capabilities: frozenset[str],
        idempotency_key: str,
        work_item_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """创建执行计划版本：基于 SUBMITTED/ACTIVE TaskCard，落地即 PENDING_APPROVAL 等人工裁决。"""
        self._require_capability(capabilities, "agent_plan.create")
        self._work_item_in_workspace(tenant_id, workspace_id, work_item_id)
        card = self.task_cards.get(str(payload["taskCardId"]))
        if card is None or not self._owned(card, tenant_id) or card["workspaceId"] != workspace_id:
            raise DomainError(404, "NOT_FOUND", "TaskCard 不存在")
        if card["workItemId"] != work_item_id:
            raise DomainError(403, "FORBIDDEN", "TaskCard 不属于该工作项")
        if card["status"] not in {"SUBMITTED", "ACTIVE"}:
            raise DomainError(409, "TASK_CARD_NOT_SUBMITTED", f"TaskCard 状态为 {card['status']}，不可编制计划")
        serializable_payload = {key: str(value) for key, value in payload.items()}
        async with self._lock:
            previous_id = self._resolve_idempotency(tenant_id, "createAgentPlan", idempotency_key, serializable_payload)
            if previous_id:
                return self._copy(self.agent_plans[previous_id])
            now = _now()
            existing_versions = [
                plan["planVersion"]
                for plan in self.agent_plans.values()
                if plan["workItemId"] == work_item_id and self._owned(plan, tenant_id)
            ]
            body = {
                "taskCardId": card["id"],
                "steps": payload["steps"],
                "outputs": payload.get("outputs") or [],
                "permissions": payload.get("permissions") or [],
                "budget": payload.get("budget") or {},
                "risks": payload.get("risks") or [],
            }
            record: dict[str, Any] = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "workItemId": work_item_id,
                **body,
                "planVersion": (max(existing_versions) + 1) if existing_versions else 1,
                "status": "PENDING_APPROVAL",
                "contentDigest": content_digest(body),
                "createdAt": now,
            }
            # 新版本使旧的非终态计划 SUPERSEDED（已 APPROVED/REJECTED 保留审计）
            for plan in self.agent_plans.values():
                if (
                    plan["workItemId"] == work_item_id
                    and self._owned(plan, tenant_id)
                    and plan["status"] in {"DRAFT", "PENDING_APPROVAL"}
                ):
                    plan["status"] = "SUPERSEDED"
            self.agent_plans[record["id"]] = record
            self._persist()
            self._remember_idempotency(
                tenant_id, "createAgentPlan", idempotency_key, serializable_payload, record["id"]
            )
            return self._copy(record)

    async def decide_agent_plan(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        idempotency_key: str,
        plan_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """人工批准或拒绝计划：摘要漂移 409；批准后 TaskCard 转 ACTIVE。"""
        self._require_capability(capabilities, "agent_plan.decide")
        if actor_type != "USER":
            raise DomainError(403, "FORBIDDEN", "Agent 不得自批计划")
        plan = self.agent_plans.get(plan_id)
        if plan is None or not self._owned(plan, tenant_id):
            raise DomainError(404, "NOT_FOUND", "计划不存在")
        if plan["workspaceId"] != workspace_id:
            raise DomainError(403, "FORBIDDEN", "计划不属于当前Workspace")
        if payload["expectedContentDigest"] != plan["contentDigest"]:
            raise DomainError(409, "STALE_ARTIFACT_VERSION", "计划摘要漂移，请刷新后重试")
        serializable_payload = {key: str(value) for key, value in payload.items()}
        async with self._lock:
            previous_id = self._resolve_idempotency(tenant_id, "decideAgentPlan", idempotency_key, serializable_payload)
            if previous_id:
                return self._copy(self.agent_plan_decisions[previous_id])
            if plan["status"] != "PENDING_APPROVAL":
                raise DomainError(409, "INVALID_STATE_TRANSITION", f"计划状态为 {plan['status']}，不可裁决")
            now = _now()
            decision = payload["decision"]
            plan["status"] = "APPROVED" if decision == "APPROVE" else "REJECTED"
            plan["updatedAt"] = now
            if decision == "APPROVE":
                card = self.task_cards.get(str(plan["taskCardId"]))
                if card is not None and card["status"] == "SUBMITTED":
                    card["status"] = "ACTIVE"
            record: dict[str, Any] = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "agentPlanId": plan_id,
                "decision": decision,
                "reason": payload["reason"],
                "decidedBy": actor_id,
                "decidedAt": now,
                "planStatus": plan["status"],
            }
            self.agent_plan_decisions[record["id"]] = record
            self._persist()
            self._remember_idempotency(
                tenant_id, "decideAgentPlan", idempotency_key, serializable_payload, record["id"]
            )
            self._events.emit(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type="agent_plan",
                subject_id=plan_id,
                event_type="agent_plan.decided",
                payload={"decision": decision, "planVersion": plan["planVersion"]},
            )
            return self._copy(record)

    # ==================== WP-04 运行命令（批次五十八，39 号 §5 切片一） ====================

    _COMMAND_TARGETS: dict[str, dict[str, Any]] = {
        "AGENT_SESSION": {
            "transitions": {
                "PAUSE": {"RUNNING", "BLOCKED"},
                "RESUME": {"PAUSED"},
                "CANCEL": {"RUNNING", "BLOCKED", "PAUSED"},
            },
            "next_status": {"PAUSE": "PAUSED", "RESUME": "RUNNING", "CANCEL": "CANCELLED"},
        },
        "EXECUTION_TASK": {
            "transitions": {
                "PAUSE": {"RUNNING"},
                "RESUME": {"PAUSED"},
                "CANCEL": {"RUNNING", "PAUSED"},
            },
            "next_status": {"PAUSE": "PAUSED", "RESUME": "RUNNING", "CANCEL": "CANCELLED"},
        },
    }

    async def issue_run_command(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        idempotency_key: str,
        target_type: str,
        target_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """下发统一运行命令（PAUSE/RESUME/CANCEL 实装；命令只追加，回执是生效唯一事实）。

        RETRY/AUTHORIZE/REVOKE 契约枚举保留、运行时未实装（422 显式拒绝，不虚报）。
        同步运行时的"安全点"为状态迁移边界：受理即生效，回执 completedAt 即时落定。
        """
        self._require_capability(capabilities, "run_command.issue")
        if actor_type != "USER":
            raise DomainError(403, "FORBIDDEN", "运行命令只能由人工下发")
        spec = self._COMMAND_TARGETS.get(target_type)
        if spec is None:
            raise DomainError(422, "VALIDATION_FAILED", f"非法命令目标类型：{target_type}")
        command_type = str(payload["commandType"])
        if command_type not in {"PAUSE", "RESUME", "CANCEL"}:
            raise DomainError(422, "VALIDATION_FAILED", f"命令类型 {command_type} 本切片未实装（契约枚举保留）")
        collections: dict[str, dict[str, dict[str, Any]]] = {
            "AGENT_SESSION": self.sessions,
            "EXECUTION_TASK": self.execution_tasks,
        }
        target = collections[target_type].get(target_id)
        if target is None or not self._owned(target, tenant_id):
            raise DomainError(404, "NOT_FOUND", "命令目标不存在")
        if target["workspaceId"] != workspace_id:
            raise DomainError(403, "FORBIDDEN", "命令目标不属于当前Workspace")
        serializable_payload = {key: str(value) for key, value in payload.items()}
        async with self._lock:
            previous_id = self._resolve_idempotency(tenant_id, "issueRunCommand", idempotency_key, serializable_payload)
            if previous_id:
                return self._copy(self.run_commands[previous_id])
            if target["status"] not in spec["transitions"][command_type]:
                raise DomainError(
                    409,
                    "INVALID_STATE_TRANSITION",
                    f"{target_type} 状态为 {target['status']}，不接受 {command_type}",
                )
            now = _now()
            next_status = spec["next_status"][command_type]
            command_record: dict[str, Any] = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "targetType": target_type,
                "targetId": target_id,
                "commandType": command_type,
                "requestedBy": actor_id,
                "reason": payload["reason"],
                "scope": payload.get("scope"),
                "idempotencyKey": idempotency_key,
                "status": "EFFECTIVE",
                "createdAt": now,
                # 同步运行时：受理即在状态迁移安全点生效，回执即时落定
                "receipt": {
                    "commandId": None,  # 创建后回填
                    "accepted": True,
                    "effectiveStatus": next_status,
                    "safePointRef": f"{target_type.lower()}:{target_id}@{target['status']}>{next_status}",
                    "attemptId": None,
                    "reasonCode": "EFFECTIVE_AT_STATUS_BOUNDARY",
                    "completedAt": now,
                },
            }
            target["status"] = next_status
            target["updatedAt"] = now
            command_record["receipt"]["commandId"] = command_record["id"]
            self.run_commands[command_record["id"]] = command_record
            # 暂停到安全点即落检查点（39 号 §5：Checkpoint 不可变，恢复前重新预检）
            if command_type == "PAUSE":
                previous_status = command_record["receipt"]["safePointRef"].split(">")[0].split("@")[-1]
                checkpoint_id = _new_id()
                self.run_checkpoints[checkpoint_id] = {
                    "id": checkpoint_id,
                    "tenantId": tenant_id,
                    "workspaceId": workspace_id,
                    "targetType": target_type,
                    "targetId": target_id,
                    "stage": previous_status,
                    "inputDigest": content_digest(
                        {"targetId": target_id, "statusBefore": previous_status, "command": command_type}
                    ),
                    "outputRefs": [],
                    "authorizationSnapshot": {},
                    "budgetSnapshot": {},
                    "createdAt": now,
                }
            self._persist()
            self._remember_idempotency(
                tenant_id, "issueRunCommand", idempotency_key, serializable_payload, command_record["id"]
            )
            self._events.emit(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type=target_type.lower(),
                subject_id=target_id,
                event_type="run_command.recorded",
                payload={"commandType": command_type, "effectiveStatus": next_status},
            )
            return self._copy(command_record)

    async def get_run_command(self, tenant_id: str, workspace_id: str, command_id: str) -> dict[str, Any]:
        record = self.run_commands.get(command_id)
        if record is None or not self._owned(record, tenant_id):
            raise DomainError(404, "NOT_FOUND", "命令不存在")
        if record["workspaceId"] != workspace_id:
            raise DomainError(403, "FORBIDDEN", "命令不属于当前Workspace")
        result = self._copy(record)
        return {"command": result, "receipt": result["receipt"]}

    # ==================== WP-04 授权/预算/检查点（批次五十九，39 号 §5 切片二） ====================

    _DEFAULT_BUDGET_LIMITS: dict[str, Any] = {
        "tokenLimit": 1_000_000,
        "costLimit": 100.0,
        "timeLimitMinutes": 480,
        "concurrencyLimit": 1,
        "retryLimit": 3,
    }

    async def create_runtime_authorization(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        idempotency_key: str,
        work_item_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """运行时授权/撤销决定（只追加；REVOKE 将匹配的 ACTIVE 授权置 REVOKED，不删历史）。"""
        self._require_capability(capabilities, "runtime_authorization.manage")
        if actor_type != "USER":
            raise DomainError(403, "FORBIDDEN", "运行时授权只能由人工决定")
        self._work_item_in_workspace(tenant_id, workspace_id, work_item_id)
        action = str(payload["action"])
        if (
            action == "AUTHORIZE"
            and payload.get("validFrom")
            and payload.get("validUntil")
            and str(payload["validFrom"]) >= str(payload["validUntil"])
        ):
            raise DomainError(422, "VALIDATION_FAILED", "validFrom 必须早于 validUntil")
        serializable_payload = {key: str(value) for key, value in payload.items()}
        async with self._lock:
            previous_id = self._resolve_idempotency(
                tenant_id, "createRuntimeAuthorization", idempotency_key, serializable_payload
            )
            if previous_id:
                return self._copy(self.runtime_authorizations[previous_id])
            now = _now()
            record: dict[str, Any] = {
                "id": _new_id(),
                "tenantId": tenant_id,
                "workspaceId": workspace_id,
                "workItemId": work_item_id,
                "action": action,
                "permissionKeys": payload["permissionKeys"],
                "resourceScope": payload.get("resourceScope") or {},
                "secretRefs": payload.get("secretRefs") or [],
                "budgetDelta": payload.get("budgetDelta") or {},
                "validFrom": payload.get("validFrom"),
                "validUntil": payload.get("validUntil"),
                "decidedBy": actor_id,
                "status": "ACTIVE" if action == "AUTHORIZE" else "REVOKED",
                "createdAt": now,
            }
            if action == "REVOKE":
                revoke_keys = set(payload["permissionKeys"])
                for auth in self.runtime_authorizations.values():
                    if (
                        auth["workItemId"] == work_item_id
                        and self._owned(auth, tenant_id)
                        and auth["status"] == "ACTIVE"
                        and revoke_keys & set(auth["permissionKeys"])
                    ):
                        auth["status"] = "REVOKED"
                        auth["updatedAt"] = now
            self.runtime_authorizations[record["id"]] = record
            self._persist()
            self._remember_idempotency(
                tenant_id,
                "createRuntimeAuthorization",
                idempotency_key,
                serializable_payload,
                record["id"],
            )
            self._events.emit(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type="work_item",
                subject_id=work_item_id,
                event_type="runtime_authorization.decided",
                payload={"action": action, "permissionKeys": payload["permissionKeys"]},
            )
            return self._copy(record)

    async def list_runtime_authorizations(
        self, tenant_id: str, workspace_id: str, work_item_id: str
    ) -> list[dict[str, Any]]:
        self._work_item_in_workspace(tenant_id, workspace_id, work_item_id)
        return [
            self._copy(item)
            for item in sorted(self.runtime_authorizations.values(), key=lambda a: (a["createdAt"], a["id"]))
            if self._owned(item, tenant_id)
            and item["workspaceId"] == workspace_id
            and item["workItemId"] == work_item_id
        ]

    def _budget_for(self, tenant_id: str, workspace_id: str, work_item_id: str) -> dict[str, Any] | None:
        for policy in self.budget_policies.values():
            if (
                self._owned(policy, tenant_id)
                and policy["workspaceId"] == workspace_id
                and policy.get("workItemId") == work_item_id
            ):
                return policy
        return None

    def _default_budget(self, tenant_id: str, workspace_id: str, work_item_id: str) -> dict[str, Any]:
        return {
            "id": None,
            "tenantId": tenant_id,
            "workspaceId": workspace_id,
            "workItemId": work_item_id,
            "limits": dict(self._DEFAULT_BUDGET_LIMITS),
            "warningThresholds": {"token": 0.8, "cost": 0.8, "time": 0.8},
            "consumed": {},
            "status": "NORMAL",
        }

    async def get_work_item_budget(self, tenant_id: str, workspace_id: str, work_item_id: str) -> dict[str, Any]:
        """预算策略与消耗快照：无持久化策略时合成默认值返回（读无副作用）。"""
        self._work_item_in_workspace(tenant_id, workspace_id, work_item_id)
        policy = self._budget_for(tenant_id, workspace_id, work_item_id)
        return self._copy(policy) if policy else self._default_budget(tenant_id, workspace_id, work_item_id)

    async def update_work_item_budget(
        self,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        actor_type: str,
        capabilities: frozenset[str],
        idempotency_key: str,
        work_item_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """更新预算策略（仅 USER；Agent 上调 403；本切片无消耗追踪，收紧/放宽即时生效）。"""
        self._require_capability(capabilities, "budget.manage")
        if actor_type != "USER":
            raise DomainError(403, "FORBIDDEN", "预算调整只能由人工执行")
        self._work_item_in_workspace(tenant_id, workspace_id, work_item_id)
        serializable_payload = {key: str(value) for key, value in payload.items()}
        async with self._lock:
            previous_id = self._resolve_idempotency(
                tenant_id, "updateWorkItemBudget", idempotency_key, serializable_payload
            )
            if previous_id:
                return self._copy(self.budget_policies[previous_id])
            policy = self._budget_for(tenant_id, workspace_id, work_item_id)
            if policy is None:
                policy = self._default_budget(tenant_id, workspace_id, work_item_id)
                policy["id"] = _new_id()
                self.budget_policies[str(policy["id"])] = policy
            limits = policy["limits"]
            for key in ("tokenLimit", "costLimit", "timeLimitMinutes", "concurrencyLimit", "retryLimit"):
                if payload.get(key) is not None:
                    limits[key] = payload[key]
            if payload.get("warningThresholds") is not None:
                policy["warningThresholds"] = payload["warningThresholds"]
            policy["updatedAt"] = _now()
            self._persist()
            self._remember_idempotency(
                tenant_id, "updateWorkItemBudget", idempotency_key, serializable_payload, str(policy["id"])
            )
            self._events.emit(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                actor_id=actor_id,
                subject_type="work_item",
                subject_id=work_item_id,
                event_type="budget.updated",
                payload={"limits": limits},
            )
            return self._copy(policy)

    async def list_run_checkpoints(
        self, tenant_id: str, workspace_id: str, target_type: str, target_id: str
    ) -> list[dict[str, Any]]:
        if target_type not in {"AGENT_SESSION", "EXECUTION_TASK"}:
            raise DomainError(422, "VALIDATION_FAILED", f"非法检查点目标类型：{target_type}")
        collection = self.sessions if target_type == "AGENT_SESSION" else self.execution_tasks
        target = collection.get(target_id)
        if target is None or not self._owned(target, tenant_id):
            raise DomainError(404, "NOT_FOUND", "检查点目标不存在")
        if target["workspaceId"] != workspace_id:
            raise DomainError(403, "FORBIDDEN", "检查点目标不属于当前Workspace")
        return [
            self._copy(item)
            for item in sorted(self.run_checkpoints.values(), key=lambda c: (c["createdAt"], c["id"]))
            if self._owned(item, tenant_id)
            and item["workspaceId"] == workspace_id
            and item["targetType"] == target_type
            and item["targetId"] == target_id
        ]

    # ==================== 质量域只读面与 Provider 状态（批次四十六） ====================

    async def list_result_analyses(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        """结果分析列表（契约新增 listResultAnalyses，前端 fetchAnalyses 已在调用的只读面）。"""
        return [
            self._copy(item)
            for item in self.result_analyses.values()
            if self._owned(item, tenant_id) and item["workspaceId"] == workspace_id
        ]

    # DEGRADED 观察窗口：最近一次 failover 发生在该窗口内才对外呈现降级态（过期自动回落 NOMINAL）。
    PROVIDER_DEGRADED_WINDOW_HOURS = 24

    async def provider_status(self) -> dict[str, Any]:
        """Provider 运行状态（契约新增 getProviderStatus，服务端独占口径，前端直接呈现勿重算）。

        NOMINAL＝现行 provider 正常；DEGRADED＝最近 24h 内硬化层记录到 failover（降级到
        deterministic-local 承接生成）；V1 deterministic-local 默认链路恒 NOMINAL。
        """
        status_payload: dict[str, Any] = {
            "status": "NOMINAL",
            "providerId": self._provider.provider_id,
            "providerVersion": self._provider.provider_version,
        }
        failovers = [record for record in self._store.load_provider_call_records() if record["failover"]]
        if failovers:
            latest = failovers[-1]
            occurred = datetime.fromisoformat(latest["occurredAt"])
            if occurred.tzinfo is None:
                occurred = occurred.replace(tzinfo=UTC)
            if datetime.now(UTC) - occurred <= timedelta(hours=self.PROVIDER_DEGRADED_WINDOW_HOURS):
                status_payload.update(
                    {
                        "status": "DEGRADED",
                        "fallbackProviderId": latest["providerId"],
                        "reason": f"provider {latest['method']} 调用失败，已降级到 fallback provider",
                        "since": latest["occurredAt"],
                    }
                )
        return status_payload


planning_workflow_service = PlanningWorkflowService()
