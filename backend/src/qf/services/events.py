"""领域事件管道（V1 D3/O3 裁决承载面）：服务端独占生成、append-only、哈希链防篡改。

防伪基线：无客户端写入面（契约仅 listEvents 只读 op）；每条事件载荷由服务端
规范化后计算 payloadDigest，并以 prevDigest 串成哈希链——启动加载与查询前
逐条重算校验，直写篡改（改载荷/插行/删行）均会破坏链而被 fail-closed 拒绝。
"""

from __future__ import annotations

import json
from typing import Any

from qf.db.sqlite_store import SQLiteWorkflowStore
from qf.services.planning_workflow import DomainError, _new_id, _now, content_digest

GENESIS_DIGEST = "GENESIS"

# 生命周期状态变迁事件登记表（埋点全集，emit 前强校验，防止野事件类型混入）
EVENT_TYPES = frozenset(
    {
        "artifact.version.generated",  # 产出物版本生成（策略/计划/用例）
        "asset.published",  # 资产版本发布 APPROVED→PUBLISHED（WP-05，旧 PUBLISHED 版本随之 STALE）
        "stage.invalidated",  # 发布取代上游基线触发下游失效（WP-05，39 §4 StageInvalidated 资产层落地）
        "review.decided",  # 审核决定（APPROVE/REQUEST_CHANGES/REJECT）
        "work_item.transitioned",  # 工作项状态迁移
        "work_item.assigned",  # 工作项分派（M2/U4，变更时追加，同人重分派为 no-op）
        "session.converged",  # 会话收敛终态（SUCCEEDED/FAILED）
        "execution.started",  # 执行计划启动
        "execution.finished",  # 执行计划终态
        "evidence.appended",  # 执行证据追加
        "defect.version.created",  # 缺陷版本（状态变迁载体）创建
        "conversation.message.appended",  # 协作对话消息追加（WP-03，只追加写）
        "clarification.requested",  # AI 发起澄清并阻塞会话（WP-03 切片二）
        "clarification.responded",  # 人工答复澄清形成 CONFIRMED 证据（只追加）
        "task_card.created",  # 任务卡固化（提交后不可静默扩展，变更走新版本取代）
        "agent_plan.decided",  # 人工批准/拒绝 AgentPlan（摘要漂移拒绝，只追加裁决）
        "run_command.recorded",  # 人工运行命令落令与生效回执（WP-04，只追加）
        "runtime_authorization.decided",  # 运行时授权/撤销决定（只追加，不泄露 Secret 明文）
        "budget.updated",  # 预算策略更新（Agent 无权上调）
        "provider.switched",  # Provider 黄金集闸门通过后切换
        "provider.failover",  # Provider 重试耗尽降级 failover
    }
)


def _event_digest(record: dict[str, Any]) -> str:
    """事件摘要：对除摘要字段外的全部事件字段规范化后计算（客户端无从注入）。"""
    return content_digest(
        {
            "eventId": record["eventId"],
            "tenantId": record["tenantId"],
            "workspaceId": record["workspaceId"],
            "actorId": record["actorId"],
            "occurredAt": record["occurredAt"],
            "subjectType": record["subjectType"],
            "subjectId": record["subjectId"],
            "eventType": record["eventType"],
            "correlationId": record.get("correlationId"),
            "payload": record["payload"],
        }
    )


class DomainEventService:
    """append-only 领域事件服务：共享 PlanningWorkflowService 的存储实例。"""

    def __init__(self, store: SQLiteWorkflowStore) -> None:
        self._store = store

    def emit(
        self,
        *,
        tenant_id: str,
        workspace_id: str | None,
        actor_id: str,
        subject_type: str,
        subject_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """服务端独占写入面：追加一条事件并延伸哈希链。"""
        if event_type not in EVENT_TYPES:
            raise DomainError(422, "VALIDATION_FAILED", f"未登记的领域事件类型：{event_type}")
        record: dict[str, Any] = {
            "eventId": _new_id(),
            "tenantId": tenant_id,
            "workspaceId": workspace_id,
            "actorId": actor_id,
            "occurredAt": _now(),
            "subjectType": subject_type,
            "subjectId": subject_id,
            "eventType": event_type,
            "correlationId": correlation_id,
            "payload": payload or {},
        }
        record["payloadDigest"] = _event_digest(record)
        record["prevDigest"] = self._store.last_domain_event_digest() or GENESIS_DIGEST
        self._store.append_domain_event(
            {
                **record,
                "payloadJson": json.dumps(record["payload"], ensure_ascii=False, sort_keys=True),
            }
        )
        return record

    def verify_chain(self) -> None:
        """逐条重算摘要并校验 prevDigest 链；任何不一致即 fail-closed（直写篡改检测）。"""
        expected_prev = GENESIS_DIGEST
        for row in self._store.load_domain_event_rows():
            record = {
                "eventId": row["event_id"],
                "tenantId": row["tenant_id"],
                "workspaceId": row["workspace_id"],
                "actorId": row["actor_id"],
                "occurredAt": row["occurred_at"],
                "subjectType": row["subject_type"],
                "subjectId": row["subject_id"],
                "eventType": row["event_type"],
                "correlationId": row["correlation_id"],
                "payload": json.loads(row["payload_json"]),
            }
            if row["prev_digest"] != expected_prev or _event_digest(record) != row["payload_digest"]:
                raise DomainError(409, "EVENT_CHAIN_TAMPERED", "领域事件链完整性校验失败")
            expected_prev = row["payload_digest"]

    def list_events(
        self,
        workspace_id: str,
        *,
        subject_type: str | None = None,
        event_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """只读查询面（查询前校验链完整性），返回 (事件列表, 总数)。"""
        self.verify_chain()
        rows, total = self._store.list_domain_events(
            workspace_id,
            subject_type=subject_type,
            event_type=event_type,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        items = [
            {
                "eventId": row["event_id"],
                "occurredAt": row["occurred_at"],
                "actorId": row["actor_id"],
                "workspaceId": row["workspace_id"],
                "subjectType": row["subject_type"],
                "subjectId": row["subject_id"],
                "eventType": row["event_type"],
                "correlationId": row["correlation_id"],
                "payload": json.loads(row["payload_json"]),
                "payloadDigest": row["payload_digest"],
            }
            for row in rows
        ]
        return items, total

    def load_events(self, workspace_id: str | None = None) -> list[dict[str, Any]]:
        """按插入序读取事件（供指标计算）；可选按工作区过滤。"""
        events: list[dict[str, Any]] = []
        for row in self._store.load_domain_event_rows():
            if workspace_id is not None and row["workspace_id"] != workspace_id:
                continue
            events.append(
                {
                    "eventId": row["event_id"],
                    "occurredAt": row["occurred_at"],
                    "actorId": row["actor_id"],
                    "workspaceId": row["workspace_id"],
                    "subjectType": row["subject_type"],
                    "subjectId": row["subject_id"],
                    "eventType": row["event_type"],
                    "correlationId": row["correlation_id"],
                    "payload": json.loads(row["payload_json"]),
                }
            )
        return events
