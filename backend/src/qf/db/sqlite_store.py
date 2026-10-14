"""Small, service-free SQLite persistence for the Stage 4 local runtime.

The store intentionally keeps the domain payloads as canonical JSON while giving
each aggregate its own tenant-indexed table.  This preserves the existing API
contract without pretending SQLite provides PostgreSQL row-level security.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 16
COLLECTION_TABLES = {
    "requirements": "requirement_documents",
    "requirement_versions": "requirement_document_versions",
    "work_items": "work_items",
    "strategies": "test_strategies",
    "strategy_versions": "test_strategy_versions",
    "plans": "test_plans",
    "plan_versions": "test_plan_versions",
    "test_cases": "test_cases",
    "test_case_versions": "test_case_versions",
    "review_tasks": "review_tasks",
    "sessions": "agent_sessions",
    # M3：执行链集合（与 33 号数据模型的执行域表名对齐）
    "execution_plans": "execution_plans",
    "execution_plan_versions": "execution_plan_versions",
    "execution_tasks": "execution_tasks",
    "execution_results": "execution_results",
    # M4：质量域集合（分析/聚类/缺陷/同步/报告/覆盖率）+ 知识回流
    "result_analyses": "result_analyses",
    "failure_clusters": "failure_clusters",
    "defects": "defects",
    "defect_versions": "defect_versions",
    "defect_sync_attempts": "defect_sync_attempts",
    "test_reports": "test_reports",
    # P0-1 裁决闭合：测试报告版本层（33 号 t_test_report_version 对齐）
    "test_report_versions": "test_report_versions",
    "coverage_reports": "coverage_reports",
    "knowledge_entries": "knowledge_entries",
    # 批次四十六：平台域环境集合（契约 listEnvironments/createEnvironment 补路由；幂等补建存量库）
    "environments": "environments",
    "conversations": "conversations",
    "conversation_messages": "conversation_messages",
    "clarifications": "clarifications",
    "clarification_responses": "clarification_responses",
    "task_cards": "task_cards",
    "agent_plans": "agent_plans",
    "agent_plan_decisions": "agent_plan_decisions",
    "run_commands": "run_commands",
    "runtime_authorizations": "runtime_authorizations",
    "budget_policies": "budget_policies",
    "run_checkpoints": "run_checkpoints",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class SQLiteWorkflowStore:
    """Persist and reload one complete planning state using atomic transactions."""

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()
        os.chmod(self.path, 0o600)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _migrate(self) -> None:
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            current = connection.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()[0]
            if current > SCHEMA_VERSION:
                raise RuntimeError(f"SQLite schema version {current} is newer than supported {SCHEMA_VERSION}")
            if current < 1:
                self._apply_v1(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (1,))
                current = 1
            if current < 2:
                self._apply_v2(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (2,))
            if current < 3:
                self._apply_v3(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (3,))
            if current < 4:
                self._apply_v4(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (4,))
            if current < 5:
                self._apply_v5(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (5,))
            if current < 6:
                self._apply_v6(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (6,))
            if current < 7:
                self._apply_v7(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (7,))
            if current < 8:
                self._apply_v8(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (8,))
            if current < 9:
                self._apply_v9(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (9,))
            if current < 10:
                self._apply_v10(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (10,))
            if current < 11:
                self._apply_v11(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (11,))
            if current < 12:
                self._apply_v12(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (12,))
            if current < 13:
                self._apply_v13(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (13,))
            if current < 14:
                self._apply_v14(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (14,))
            if current < 15:
                self._apply_v15(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (15,))
            if current < 16:
                self._apply_v16(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (16,))
            # 幂等兼修：任何版本下也保证 COLLECTION_TABLES 全量存在（存量库跨版本补建）
            self._ensure_collection_tables(connection)
            self._ensure_domain_events_table(connection)

    @staticmethod
    def _ensure_collection_tables(connection: sqlite3.Connection) -> None:
        for table in COLLECTION_TABLES.values():
            connection.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ("  # noqa: S608 - closed constant map
                "id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT, payload_json TEXT NOT NULL)"
            )
            connection.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{table}_tenant_workspace ON {table}(tenant_id, workspace_id)"  # noqa: S608
            )

    @staticmethod
    def _apply_v1(connection: sqlite3.Connection) -> None:
        for table in COLLECTION_TABLES.values():
            connection.execute(
                f"CREATE TABLE {table} ("  # noqa: S608 - names come from a closed constant map
                "id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT, payload_json TEXT NOT NULL)"
            )
            connection.execute(
                f"CREATE INDEX idx_{table}_tenant_workspace ON {table}(tenant_id, workspace_id)"  # noqa: S608
            )
        connection.executescript(
            """
            CREATE TABLE requirement_contents (
                version_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                content TEXT NOT NULL
            );
            CREATE INDEX idx_requirement_contents_tenant ON requirement_contents(tenant_id);

            CREATE TABLE agent_trace_events (
                session_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                tenant_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY(session_id, sequence)
            );
            CREATE INDEX idx_trace_tenant_session ON agent_trace_events(tenant_id, session_id);

            CREATE TABLE artifact_version_index (
                version_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                artifact_id TEXT NOT NULL
            );
            CREATE INDEX idx_artifact_version_tenant ON artifact_version_index(tenant_id, version_id);

            CREATE TABLE review_session_links (
                review_task_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                session_id TEXT NOT NULL
            );
            CREATE INDEX idx_review_link_tenant ON review_session_links(tenant_id, review_task_id);

            CREATE TABLE idempotency_keys (
                tenant_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                PRIMARY KEY(tenant_id, operation, idempotency_key)
            );
            """
        )

    @staticmethod
    def _apply_v2(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE tenants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE workspaces (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(tenant_id) REFERENCES tenants(id)
            );
            CREATE INDEX idx_workspaces_tenant ON workspaces(tenant_id, id);
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE tenant_memberships (
                tenant_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                actor_type TEXT NOT NULL CHECK(actor_type IN ('USER', 'SERVICE', 'AGENT')),
                capabilities_json TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(tenant_id, user_id),
                FOREIGN KEY(tenant_id) REFERENCES tenants(id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
            );
            CREATE INDEX idx_membership_user ON tenant_memberships(user_id, tenant_id);
            """
        )

    @staticmethod
    def _apply_v3(connection: sqlite3.Connection) -> None:
        # M1-P1：Provider 调用成本记录（只追加，不参与全量快照 save/load）
        connection.executescript(
            """
            CREATE TABLE provider_call_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id TEXT NOT NULL,
                provider_version TEXT NOT NULL,
                method TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                status TEXT NOT NULL,
                failover INTEGER NOT NULL DEFAULT 0,
                occurred_at TEXT NOT NULL
            );
            CREATE INDEX idx_provider_call_method ON provider_call_records(method, id);
            """
        )

    @staticmethod
    def _apply_v16(connection: sqlite3.Connection) -> None:
        """WP-04 切片二：运行时授权决定 / 预算策略 / 检查点集合表，幂等补建锚点。"""
        SQLiteWorkflowStore._ensure_collection_tables(connection)

    @staticmethod
    def _apply_v15(connection: sqlite3.Connection) -> None:
        """WP-04 切片一：运行命令（含内嵌生效回执，只追加）集合表，幂等补建锚点。"""
        SQLiteWorkflowStore._ensure_collection_tables(connection)

    @staticmethod
    def _apply_v14(connection: sqlite3.Connection) -> None:
        """WP-03 切片三：任务卡 / AgentPlan / 裁决记录（裁决只追加）集合表，幂等补建锚点。"""
        SQLiteWorkflowStore._ensure_collection_tables(connection)

    @staticmethod
    def _apply_v13(connection: sqlite3.Connection) -> None:
        """WP-03 切片二：澄清请求与答复（答复只追加）集合表，幂等补建锚点。"""
        SQLiteWorkflowStore._ensure_collection_tables(connection)

    @staticmethod
    def _apply_v12(connection: sqlite3.Connection) -> None:
        """WP-03：协作对话与消息（只追加）集合表，幂等补建锚点。"""
        SQLiteWorkflowStore._ensure_collection_tables(connection)

    @staticmethod
    def _apply_v11(connection: sqlite3.Connection) -> None:
        """WP-01：用户级常用项目置顶（t_workspace_pin 目标层对齐，QF-PD-026）。"""
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS workspace_pins (
                tenant_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                pinned_at TEXT NOT NULL,
                PRIMARY KEY(tenant_id, user_id, workspace_id),
                FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
            );
            CREATE INDEX IF NOT EXISTS idx_workspace_pin_user
                ON workspace_pins(user_id, pinned_at DESC);
            """
        )

    @staticmethod
    def _apply_v10(connection: sqlite3.Connection) -> None:
        """WP-01A：成员关系主键 (tenant_id, user_id) -> (tenant_id, user_id, workspace_id)。

        单用户多工作区（切换承载面）需要按工作区各持一行成员关系；SQLite 无法原地改主键，
        重建表并原样搬数据。能力集按行各自独立（种子面复制既有行）。
        """
        connection.executescript(
            """
            CREATE TABLE tenant_memberships_v10 (
                tenant_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                actor_type TEXT NOT NULL CHECK(actor_type IN ('USER', 'SERVICE', 'AGENT')),
                capabilities_json TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(tenant_id, user_id, workspace_id),
                FOREIGN KEY(tenant_id) REFERENCES tenants(id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
            );
            INSERT INTO tenant_memberships_v10
                (tenant_id, user_id, workspace_id, actor_type, capabilities_json, is_active)
                SELECT tenant_id, user_id, workspace_id, actor_type, capabilities_json, is_active
                FROM tenant_memberships;
            DROP TABLE tenant_memberships;
            ALTER TABLE tenant_memberships_v10 RENAME TO tenant_memberships;
            CREATE INDEX idx_membership_user ON tenant_memberships(user_id, tenant_id);
            """
        )

    @staticmethod
    def _apply_v9(connection: sqlite3.Connection) -> None:
        """Persist real Release context instead of letting clients invent IDs."""
        connection.executescript(
            """
            CREATE TABLE releases (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'ARCHIVED')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
            );
            CREATE INDEX idx_releases_workspace_active
                ON releases(tenant_id, workspace_id, status, updated_at DESC);
            """
        )

    @staticmethod
    def _apply_v4(connection: sqlite3.Connection) -> None:
        # M3：执行证据只追加（append-only），不参与全量快照 save，保证不可变口径；
        # 执行集合表由 _ensure_collection_tables 幂等补建
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS execution_evidence (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT,
                execution_task_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_execution_evidence_task ON execution_evidence(execution_task_id, id);
            CREATE INDEX IF NOT EXISTS idx_execution_evidence_tenant ON execution_evidence(tenant_id, workspace_id);
            """
        )

    @staticmethod
    def _apply_v5(connection: sqlite3.Connection) -> None:
        # M4：质量域 8 张集合表由 _ensure_collection_tables 幂等补建；
        # 此迁移仅作版本锚点，保证 v4 存量库登记升级路径。
        del connection

    @staticmethod
    def _apply_v6(connection: sqlite3.Connection) -> None:
        # V1 事件管道（D3/O3）：领域事件只追加（append-only），不参与全量快照 save/load，
        # payload_digest/prev_digest 构成哈希链供启动与查询时防篡改校验。
        SQLiteWorkflowStore._ensure_domain_events_table(connection)

    @staticmethod
    def _apply_v7(connection: sqlite3.Connection) -> None:
        # P0-1 裁决闭合：test_report_versions 集合表幂等补建（全量快照 save/load 承载）
        SQLiteWorkflowStore._ensure_collection_tables(connection)

    @staticmethod
    def _apply_v8(connection: sqlite3.Connection) -> None:
        # B1：ExecutionResult 补 resultDigest/assertionResultsRef 两列（payload_json 仍为权威全量，
        # 列仅作可查询/可校验的冗余投影；旧行两列为 NULL，load 时回退 payload_json）
        connection.executescript(
            """
            ALTER TABLE execution_results ADD COLUMN result_digest TEXT;
            ALTER TABLE execution_results ADD COLUMN assertion_results_ref TEXT;
            """
        )

    @staticmethod
    def _ensure_domain_events_table(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS domain_events (
                event_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                correlation_id TEXT,
                payload_json TEXT NOT NULL,
                payload_digest TEXT NOT NULL,
                prev_digest TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_domain_events_ws ON domain_events(workspace_id, event_type);
            CREATE INDEX IF NOT EXISTS idx_domain_events_subject ON domain_events(subject_type, subject_id);
            """
        )

    def append_evidence(self, record: Mapping[str, Any]) -> None:
        """追加一条不可变执行证据（camelCase 载荷整体存 payload_json）。"""
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO execution_evidence("
                "id, tenant_id, workspace_id, execution_task_id, payload_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record["id"],
                    record["tenantId"],
                    record.get("workspaceId"),
                    record["executionTaskId"],
                    _canonical_json(dict(record)),
                    record["createdAt"],
                ),
            )

    def load_evidence(self) -> dict[str, dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, payload_json FROM execution_evidence ORDER BY created_at, id"
            ).fetchall()
        return {row["id"]: json.loads(row["payload_json"]) for row in rows}

    def replace_evidence(self, records: Mapping[str, Mapping[str, Any]]) -> None:
        """用内存态整体重写证据表（仅测试恢复路径使用，生产代码不调用）。"""
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM execution_evidence")
            connection.executemany(
                "INSERT INTO execution_evidence("
                "id, tenant_id, workspace_id, execution_task_id, payload_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        record["id"],
                        record["tenantId"],
                        record.get("workspaceId"),
                        record["executionTaskId"],
                        _canonical_json(dict(record)),
                        record["createdAt"],
                    )
                    for record in records.values()
                ],
            )

    def append_domain_event(self, record: Mapping[str, Any]) -> None:
        """追加一条不可变领域事件（camelCase 载荷整体存 payload_json，只进不出快照）。"""
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO domain_events("
                "event_id, tenant_id, workspace_id, actor_id, occurred_at, subject_type, "
                "subject_id, event_type, correlation_id, payload_json, payload_digest, prev_digest) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record["eventId"],
                    record["tenantId"],
                    record["workspaceId"],
                    record["actorId"],
                    record["occurredAt"],
                    record["subjectType"],
                    record["subjectId"],
                    record["eventType"],
                    record.get("correlationId"),
                    record["payloadJson"],
                    record["payloadDigest"],
                    record["prevDigest"],
                ),
            )

    def last_domain_event_digest(self) -> str | None:
        """哈希链尾摘要（按插入序）；空表返回 None。"""
        with self.connect() as connection:
            row = connection.execute("SELECT payload_digest FROM domain_events ORDER BY rowid DESC LIMIT 1").fetchone()
            return row["payload_digest"] if row is not None else None

    def load_domain_event_rows(self) -> list[dict[str, Any]]:
        """按插入序读取全部事件行（供链式完整性校验与指标计算）。"""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT event_id, tenant_id, workspace_id, actor_id, occurred_at, subject_type, "
                "subject_id, event_type, correlation_id, payload_json, payload_digest, prev_digest "
                "FROM domain_events ORDER BY rowid"
            ).fetchall()
            return [dict(row) for row in rows]

    def list_domain_events(
        self,
        workspace_id: str,
        *,
        subject_type: str | None,
        event_type: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """按工作区过滤事件（可叠加 subjectType/eventType），返回 (行列表, 总数)。"""
        conditions = ["workspace_id = ?"]
        params: list[Any] = [workspace_id]
        if subject_type:
            conditions.append("subject_type = ?")
            params.append(subject_type)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        where = " AND ".join(conditions)
        with self.connect() as connection:
            total = int(
                connection.execute(f"SELECT COUNT(*) FROM domain_events WHERE {where}", params).fetchone()[0]  # noqa: S608
            )
            rows = connection.execute(
                f"SELECT event_id, tenant_id, workspace_id, actor_id, occurred_at, subject_type, "  # noqa: S608
                "subject_id, event_type, correlation_id, payload_json, payload_digest, prev_digest "
                f"FROM domain_events WHERE {where} ORDER BY rowid DESC LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
            return [dict(row) for row in rows], total

    def append_provider_call_record(self, record: Mapping[str, Any]) -> None:
        """追加一条 Provider 调用成本记录（camelCase 载荷映射到 snake_case 列）。"""
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO provider_call_records("
                "provider_id, provider_version, method, duration_ms, status, failover, occurred_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    record["providerId"],
                    record["providerVersion"],
                    record["method"],
                    record["durationMs"],
                    record["status"],
                    1 if record["failover"] else 0,
                    record["occurredAt"],
                ),
            )

    def load_provider_call_records(self) -> list[dict[str, Any]]:
        """按插入序读取全部 Provider 调用台账（供 D3 指标计算）。"""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT provider_id, provider_version, method, duration_ms, status, failover, occurred_at "
                "FROM provider_call_records ORDER BY id"
            ).fetchall()
            return [
                {
                    "providerId": row["provider_id"],
                    "providerVersion": row["provider_version"],
                    "method": row["method"],
                    "durationMs": row["duration_ms"],
                    "status": row["status"],
                    "failover": bool(row["failover"]),
                    "occurredAt": row["occurred_at"],
                }
                for row in rows
            ]

    def latest_successful_provider_by_method(self) -> dict[str, tuple[str, str]]:
        """每个生成方法最近一次成功调用的 (provider_id, provider_version)，用于产出物追溯。"""
        result: dict[str, tuple[str, str]] = {}
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT method, provider_id, provider_version FROM provider_call_records "
                "WHERE status = 'SUCCESS' ORDER BY id"
            ).fetchall()
        for row in rows:
            result[row["method"]] = (row["provider_id"], row["provider_version"])
        return result

    def auth_user_count(self) -> int:
        with self.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM users").fetchone()[0])

    def create_initial_identity(
        self,
        *,
        tenant_id: str,
        tenant_name: str,
        workspace_id: str,
        workspace_name: str,
        user_id: str,
        email: str,
        password_hash: str,
        capabilities: list[str],
        created_at: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] != 0:
                raise ValueError("local setup is already complete")
            connection.execute(
                "INSERT INTO tenants(id, name, created_at) VALUES (?, ?, ?)",
                (tenant_id, tenant_name, created_at),
            )
            connection.execute(
                "INSERT INTO workspaces(id, tenant_id, name, created_at) VALUES (?, ?, ?, ?)",
                (workspace_id, tenant_id, workspace_name, created_at),
            )
            connection.execute(
                "INSERT INTO users(id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (user_id, email.casefold(), password_hash, created_at),
            )
            connection.execute(
                "INSERT INTO tenant_memberships(tenant_id, user_id, workspace_id, actor_type, capabilities_json) "
                "VALUES (?, ?, ?, 'USER', ?)",
                (tenant_id, user_id, workspace_id, _canonical_json(capabilities)),
            )
            connection.execute(
                "INSERT INTO releases(id, tenant_id, workspace_id, name, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?)",
                (str(uuid.uuid4()), tenant_id, workspace_id, "默认发布", created_at, created_at),
            )

    def list_workspaces_for_user(self, tenant_id: str, user_id: str) -> list[dict[str, Any]]:
        """成员域内工作区投影（WP-01A）。

        lastBusinessUpdatedAt 口径：该工作区 19 类业务事件
        （artifact/asset.published/stage.invalidated/review/work_item/session/conversation/clarification/task_card/agent_plan/run_command
        /runtime_authorization/budget
        execution/evidence/defect）的最大 occurredAt，排除 provider.switched/provider.failover
        两类运行面事件；无事件时回退 createdAt。只读查询与 Agent Trace 均不产生领域事件，
        故轮询/Trace 不刷新该值（40 号 Backlog §6.2 负向口径）。排序按该值 DESC（最近有效更新优先）。
        """
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT w.id, w.name, w.created_at, "
                "COALESCE((SELECT MAX(e.occurred_at) FROM domain_events e "
                "WHERE e.workspace_id = w.id "
                "AND e.event_type NOT IN ('provider.switched', 'provider.failover')), w.created_at) "
                "AS last_business_at, "
                "EXISTS(SELECT 1 FROM workspace_pins p "
                "WHERE p.tenant_id = w.tenant_id AND p.user_id = ? AND p.workspace_id = w.id) AS pinned "
                "FROM workspaces w "
                "JOIN tenant_memberships m ON m.workspace_id = w.id AND m.tenant_id = w.tenant_id "
                "WHERE m.tenant_id = ? AND m.user_id = ? AND m.is_active = 1 "
                "ORDER BY pinned DESC, last_business_at DESC, w.created_at DESC",
                (user_id, tenant_id, user_id),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "createdAt": row["created_at"],
                "lastBusinessUpdatedAt": row["last_business_at"],
                "pinned": bool(row["pinned"]),
            }
            for row in rows
        ]

    def seed_workspace_for_user(self, tenant_id: str, user_id: str, workspace_name: str, *, created_at: str) -> str:
        """为既有用户种子第二个工作区：成员关系复制既有能力集 + 默认 ACTIVE Release。

        测试与本地联调种子面（WP-01A 切换 e2e 前置）；V1 契约无创建 Workspace 的运行时 op，
        正式创建归后续工作包。
        """
        workspace_id = str(uuid.uuid4())
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO workspaces(id, tenant_id, name, created_at) VALUES (?, ?, ?, ?)",
                (workspace_id, tenant_id, workspace_name, created_at),
            )
            connection.execute(
                "INSERT INTO tenant_memberships(tenant_id, user_id, workspace_id, actor_type, capabilities_json) "
                "SELECT tenant_id, user_id, ?, 'USER', capabilities_json FROM tenant_memberships "
                "WHERE tenant_id = ? AND user_id = ? AND is_active = 1 LIMIT 1",
                (workspace_id, tenant_id, user_id),
            )
            if connection.execute("SELECT changes()").fetchone()[0] == 0:
                raise ValueError("种子失败：该用户在本租户下没有生效成员关系")
            connection.execute(
                "INSERT INTO releases(id, tenant_id, workspace_id, name, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?)",
                (str(uuid.uuid4()), tenant_id, workspace_id, "默认发布", created_at, created_at),
            )
        return workspace_id

    def set_workspace_pin(
        self, tenant_id: str, user_id: str, workspace_id: str, pinned: bool, *, pinned_at: str
    ) -> None:
        """用户级常用项目置顶/取消（幂等：重复同值为 no-op）。"""
        with self.connect() as connection:
            if pinned:
                connection.execute(
                    "INSERT OR IGNORE INTO workspace_pins(tenant_id, user_id, workspace_id, pinned_at) "
                    "VALUES (?, ?, ?, ?)",
                    (tenant_id, user_id, workspace_id, pinned_at),
                )
            else:
                connection.execute(
                    "DELETE FROM workspace_pins WHERE tenant_id = ? AND user_id = ? AND workspace_id = ?",
                    (tenant_id, user_id, workspace_id),
                )

    def default_workspace_for_user(self, tenant_id: str, user_id: str) -> str | None:
        """登录默认工作区：最近置顶的常用项目，未置顶回退 None（由首行成员关系兜底）。"""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT p.workspace_id FROM workspace_pins p "
                "JOIN tenant_memberships m ON m.workspace_id = p.workspace_id "
                "AND m.tenant_id = p.tenant_id AND m.user_id = p.user_id AND m.is_active = 1 "
                "WHERE p.tenant_id = ? AND p.user_id = ? "
                "ORDER BY p.pinned_at DESC LIMIT 1",
                (tenant_id, user_id),
            ).fetchone()
        return str(row["workspace_id"]) if row is not None else None

    def archive_release(self, tenant_id: str, workspace_id: str, release_id: str, *, updated_at: str) -> bool:
        """ACTIVE → ARCHIVED 单向迁移；目标不存在或已归档返回 False（由服务层分流 404/409）。"""
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE releases SET status = 'ARCHIVED', updated_at = ? "
                "WHERE tenant_id = ? AND workspace_id = ? AND id = ? AND status = 'ACTIVE'",
                (updated_at, tenant_id, workspace_id, release_id),
            )
            return cursor.rowcount > 0

    def release_status(self, tenant_id: str, workspace_id: str, release_id: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT status FROM releases WHERE tenant_id = ? AND workspace_id = ? AND id = ?",
                (tenant_id, workspace_id, release_id),
            ).fetchone()
        return str(row["status"]) if row is not None else None

    def collection_count(self, table: str, tenant_id: str, workspace_id: str, *, status_in: tuple[str, ...]) -> int:
        """集合表按 payload_json.status 统计（投影计数，只读）。"""
        placeholders = ",".join("?" for _ in status_in)
        with self.connect() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE tenant_id = ? AND workspace_id = ? "
                f"AND json_extract(payload_json, '$.status') IN ({placeholders})",
                (tenant_id, workspace_id, *status_in),
            ).fetchone()
        return int(row[0])

    def list_active_releases(self, tenant_id: str, workspace_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, status, created_at, updated_at FROM releases "
                "WHERE tenant_id = ? AND workspace_id = ? AND status = 'ACTIVE' ORDER BY updated_at DESC, id DESC",
                (tenant_id, workspace_id),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "status": row["status"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
            for row in rows
        ]

    def active_release_exists(self, tenant_id: str, workspace_id: str, release_id: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM releases WHERE id = ? AND tenant_id = ? AND workspace_id = ? AND status = 'ACTIVE'",
                (release_id, tenant_id, workspace_id),
            ).fetchone()
        return row is not None

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id, email, password_hash, is_active FROM users WHERE email = ? COLLATE NOCASE",
                (email.casefold(),),
            ).fetchone()
            return dict(row) if row is not None else None

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id, email, is_active FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def get_membership(self, user_id: str, tenant_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT tenant_id, user_id, workspace_id, actor_type, capabilities_json, is_active "
                "FROM tenant_memberships WHERE tenant_id = ? AND user_id = ? ORDER BY rowid LIMIT 1",
                (tenant_id, user_id),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["capabilities"] = json.loads(result.pop("capabilities_json"))
            return result

    def get_membership_for_workspace(self, user_id: str, tenant_id: str, workspace_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT tenant_id, user_id, workspace_id, actor_type, capabilities_json, is_active "
                "FROM tenant_memberships "
                "WHERE tenant_id = ? AND user_id = ? AND workspace_id = ? AND is_active = 1",
                (tenant_id, user_id, workspace_id),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["capabilities"] = json.loads(result.pop("capabilities_json"))
            return result

    def first_membership(self, user_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT tenant_id, user_id, workspace_id, actor_type, capabilities_json, is_active "
                "FROM tenant_memberships WHERE user_id = ? AND is_active = 1 ORDER BY tenant_id LIMIT 1",
                (user_id,),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["capabilities"] = json.loads(result.pop("capabilities_json"))
            return result

    def clear_auth(self) -> None:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM tenant_memberships")
            connection.execute("DELETE FROM users")
            connection.execute("DELETE FROM workspaces")
            connection.execute("DELETE FROM tenants")

    def clear_workflow(self) -> None:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for table in COLLECTION_TABLES.values():
                connection.execute(f"DELETE FROM {table}")  # noqa: S608
            for table in (
                "requirement_contents",
                "agent_trace_events",
                "artifact_version_index",
                "review_session_links",
                "idempotency_keys",
                "provider_call_records",
                "execution_evidence",
                "domain_events",
            ):
                connection.execute(f"DELETE FROM {table}")  # noqa: S608

    def load(self) -> dict[str, Any]:
        state: dict[str, Any] = {name: {} for name in COLLECTION_TABLES}
        with self.connect() as connection:
            for name, table in COLLECTION_TABLES.items():
                if name == "execution_results":
                    continue
                rows = connection.execute(f"SELECT id, payload_json FROM {table}").fetchall()  # noqa: S608
                state[name] = {row["id"]: json.loads(row["payload_json"]) for row in rows}
            # B1：执行结果列表读取带出 resultDigest/assertionResultsRef 两列（旧行为 NULL 时回退 payload_json）
            result_rows = connection.execute(
                "SELECT id, payload_json, result_digest, assertion_results_ref FROM execution_results"
            ).fetchall()
            for row in result_rows:
                record = json.loads(row["payload_json"])
                if row["result_digest"] and not record.get("resultDigest"):
                    record["resultDigest"] = row["result_digest"]
                if row["assertion_results_ref"] and not record.get("assertionResultsRef"):
                    record["assertionResultsRef"] = row["assertion_results_ref"]
                state["execution_results"][row["id"]] = record
            contents = connection.execute("SELECT version_id, content FROM requirement_contents").fetchall()
            state["requirement_contents"] = {row["version_id"]: row["content"] for row in contents}
            trace_rows = connection.execute(
                "SELECT session_id, payload_json FROM agent_trace_events ORDER BY session_id, sequence"
            ).fetchall()
            traces: dict[str, list[dict[str, Any]]] = {}
            for row in trace_rows:
                traces.setdefault(row["session_id"], []).append(json.loads(row["payload_json"]))
            state["traces"] = traces
            index_rows = connection.execute(
                "SELECT version_id, artifact_type, artifact_id FROM artifact_version_index"
            ).fetchall()
            state["version_metadata"] = {
                row["version_id"]: (row["artifact_type"], row["artifact_id"]) for row in index_rows
            }
            links = connection.execute("SELECT review_task_id, session_id FROM review_session_links").fetchall()
            state["review_to_session"] = {row["review_task_id"]: row["session_id"] for row in links}
            keys = connection.execute(
                "SELECT tenant_id, operation, idempotency_key, request_fingerprint, resource_id FROM idempotency_keys"
            ).fetchall()
            state["idempotency"] = {
                (row["tenant_id"], row["operation"], row["idempotency_key"]): (
                    row["request_fingerprint"],
                    row["resource_id"],
                )
                for row in keys
            }
        state["execution_evidence"] = self.load_evidence()
        return state

    def save(self, state: Mapping[str, Any]) -> None:
        """Replace the small local snapshot atomically.

        This is deliberately optimized for correctness and recoverability of a
        single-user local spike, not high-volume production throughput.
        """
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for name, table in COLLECTION_TABLES.items():
                connection.execute(f"DELETE FROM {table}")  # noqa: S608
                rows = []
                for record_id, record in state[name].items():
                    rows.append(
                        (
                            record_id,
                            record["tenantId"],
                            record.get("workspaceId"),
                            _canonical_json(record),
                        )
                    )
                connection.executemany(
                    f"INSERT INTO {table}(id, tenant_id, workspace_id, payload_json) VALUES (?, ?, ?, ?)",  # noqa: S608
                    rows,
                )

            # B1：执行结果的两个防伪字段同时投影到独立列（payload_json 仍为权威全量）
            connection.executemany(
                "UPDATE execution_results SET result_digest = ?, assertion_results_ref = ? WHERE id = ?",
                [
                    (record.get("resultDigest"), record.get("assertionResultsRef"), record_id)
                    for record_id, record in state["execution_results"].items()
                ],
            )

            connection.execute("DELETE FROM requirement_contents")
            connection.executemany(
                "INSERT INTO requirement_contents(version_id, tenant_id, content) VALUES (?, ?, ?)",
                [
                    (version_id, state["requirement_versions"][version_id]["tenantId"], content)
                    for version_id, content in state["requirement_contents"].items()
                ],
            )
            connection.execute("DELETE FROM agent_trace_events")
            connection.executemany(
                "INSERT INTO agent_trace_events(session_id, sequence, tenant_id, payload_json) VALUES (?, ?, ?, ?)",
                [
                    (session_id, event["sequence"], state["sessions"][session_id]["tenantId"], _canonical_json(event))
                    for session_id, events in state["traces"].items()
                    for event in events
                ],
            )
            connection.execute("DELETE FROM artifact_version_index")
            connection.executemany(
                "INSERT INTO artifact_version_index(version_id, tenant_id, artifact_type, artifact_id) "
                "VALUES (?, ?, ?, ?)",
                [
                    (version_id, version["tenantId"], artifact_type, artifact_id)
                    for version_id, (artifact_type, artifact_id, version) in state["version_index"].items()
                ],
            )
            connection.execute("DELETE FROM review_session_links")
            connection.executemany(
                "INSERT INTO review_session_links(review_task_id, tenant_id, session_id) VALUES (?, ?, ?)",
                [
                    (review_id, state["review_tasks"][review_id]["tenantId"], session_id)
                    for review_id, session_id in state["review_to_session"].items()
                ],
            )
            connection.execute("DELETE FROM idempotency_keys")
            connection.executemany(
                "INSERT INTO idempotency_keys(tenant_id, operation, idempotency_key, request_fingerprint, resource_id) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (tenant_id, operation, key, fingerprint, resource_id)
                    for (tenant_id, operation, key), (fingerprint, resource_id) in state["idempotency"].items()
                ],
            )
