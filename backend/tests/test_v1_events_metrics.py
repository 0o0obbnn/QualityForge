"""V1 事件管道与 D3 指标计算（契约 listEvents/listMetrics，20 号 §1.1 O3 ✅ 项）。

覆盖：append-only 哈希链防篡改（直写检出）、无客户端写入面断言、
25 项 metricKey 全量存在性、fixture 已知事件序列口径测试。
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

from qf.main import app
from qf.services.events import EVENT_TYPES
from qf.services.metrics import METRIC_KEYS, compute_metrics
from qf.services.planning_workflow import DomainError, planning_workflow_service
from tests.test_planning_workflow import LOCAL_PASSWORD, mutation_headers, setup_identity

TENANT_ID = "tenant-v1-events"
WORKSPACE_ID = "11111111-1111-1111-1111-111111111111"


def _emit(event_type: str, *, subject_type: str, subject_id: str, payload: dict[str, Any] | None = None) -> None:
    planning_workflow_service.events.emit(
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        actor_id="actor-v1",
        subject_type=subject_type,
        subject_id=subject_id,
        event_type=event_type,
        payload=payload,
    )


def test_event_registry_pins_instrumentation_catalog() -> None:
    """埋点登记表钉死：新增/删减事件类型必须显式改动本断言（契约面通告）。"""
    assert (
        frozenset(
            {
                "artifact.version.generated",
                "asset.published",
                "stage.invalidated",
                "review.decided",
                "work_item.transitioned",
                "work_item.assigned",
                "session.converged",
                "execution.started",
                "execution.finished",
                "evidence.appended",
                "defect.version.created",
                "conversation.message.appended",
                "clarification.requested",
                "clarification.responded",
                "task_card.created",
                "agent_plan.decided",
                "run_command.recorded",
                "runtime_authorization.decided",
                "budget.updated",
                "provider.switched",
                "provider.failover",
            }
        )
        == EVENT_TYPES
    )


def test_emit_rejects_unregistered_event_type() -> None:
    with pytest.raises(DomainError) as excinfo:
        _emit("rogue.event", subject_type="x", subject_id="y")
    assert excinfo.value.code == "VALIDATION_FAILED"


def test_event_chain_detects_direct_write_tampering(sqlite_path: Path) -> None:
    _emit("artifact.version.generated", subject_type="TEST_STRATEGY", subject_id="s1")
    _emit("review.decided", subject_type="review_task", subject_id="r1", payload={"decision": "APPROVE"})
    _emit("work_item.transitioned", subject_type="work_item", subject_id="w1")
    planning_workflow_service.events.verify_chain()  # 干净链通过

    # 直写篡改载荷 → 摘要失配被检出
    connection = sqlite3.connect(sqlite_path)
    try:
        original = connection.execute("SELECT payload_json FROM domain_events ORDER BY rowid LIMIT 1").fetchone()[0]
        connection.execute(
            "UPDATE domain_events SET payload_json = '{\"forged\": true}' WHERE rowid = ("
            "SELECT MIN(rowid) FROM domain_events)"
        )
        connection.commit()
        with pytest.raises(DomainError) as tampered:
            planning_workflow_service.events.verify_chain()
        assert tampered.value.code == "EVENT_CHAIN_TAMPERED"
        # 还原载荷后链恢复
        connection.execute(
            "UPDATE domain_events SET payload_json = ? WHERE rowid = (SELECT MIN(rowid) FROM domain_events)",
            (original,),
        )
        connection.commit()
        planning_workflow_service.events.verify_chain()

        # 删行破坏 prevDigest 链 → 同样被检出
        connection.execute("DELETE FROM domain_events WHERE rowid = (SELECT MIN(rowid) + 1 FROM domain_events)")
        connection.commit()
        with pytest.raises(DomainError) as broken:
            planning_workflow_service.events.verify_chain()
        assert broken.value.code == "EVENT_CHAIN_TAMPERED"
    finally:
        connection.close()


def test_observability_contract_has_no_client_write_surface() -> None:
    """防伪基线：/observability/* 仅 GET，无 POST/PUT/PATCH/DELETE 写入面（AC-04）。"""
    generated = app.openapi()
    for path, path_item in generated["paths"].items():
        if not path.startswith("/api/v1/observability"):
            continue
        assert set(path_item) <= {"get"}, f"{path} 出现写入面: {set(path_item) - {'get'}}"


def test_metrics_fixture_known_event_sequence() -> None:
    """已知事件序列 → 断言计算值（fixture 口径测试，无手工录入）。"""
    now = datetime.now(UTC).isoformat()
    # 台账侧：一个已批准又被重开的工作项（lead/reopen 分母）
    planning_workflow_service.work_items["wi-v1"] = {
        "id": "wi-v1",
        "tenantId": TENANT_ID,
        "workspaceId": WORKSPACE_ID,
        "status": "APPROVED",
        "createdAt": now,
        "updatedAt": now,
    }
    # 事件侧：版本生成 → 首审即批准（first_pass/draft_accept/gen_to_approve）
    _emit(
        "artifact.version.generated",
        subject_type="TEST_STRATEGY",
        subject_id="s1",
        payload={"versionId": "v1", "version": 1, "reviewTaskId": "rt1"},
    )
    _emit(
        "review.decided",
        subject_type="review_task",
        subject_id="rt1",
        payload={
            "decision": "APPROVE",
            "status": "APPROVED",
            "artifactType": "TEST_STRATEGY",
            "artifactId": "s1",
            "artifactVersionId": "v1",
        },
    )
    # 重开事件（reopen 分子）
    _emit(
        "work_item.transitioned",
        subject_type="work_item",
        subject_id="wi-v1",
        payload={"fromStatus": "APPROVED", "toStatus": "REWORK"},
    )

    metrics = {item["metricKey"]: item for item in compute_metrics(planning_workflow_service, WORKSPACE_ID)}
    assert set(metrics) == set(METRIC_KEYS)
    assert len(metrics) == 25
    assert metrics["qual_first_pass_rate"]["value"] == 1.0
    assert metrics["ai_draft_accept_rate"]["value"] == 1.0
    assert metrics["qual_rework_rate"]["value"] == 0.0
    assert metrics["qual_reopen_rate"]["value"] == 1.0
    assert metrics["eff_gen_to_approve_time"]["value"] is not None
    assert metrics["eff_lead_time"]["value"] is not None
    # AC-04：任何指标不得携带目标值字段
    assert all("target" not in item and "targetValue" not in item for item in metrics.values())
    # 每项显式声明分母口径
    assert all(item["basis"] and item["window"] and item["computedAt"] for item in metrics.values())


async def test_http_list_events_and_metrics(client: AsyncClient) -> None:
    profile = await setup_identity(client, "events-observer@qualityforge.example")
    workspace_id = profile["workspaceId"]
    planning_workflow_service.events.emit(
        tenant_id=str(profile["tenantId"]),
        workspace_id=workspace_id,
        actor_id=str(profile["userId"]),
        subject_type="agent_session",
        subject_id="session-http",
        event_type="session.converged",
        payload={"status": "SUCCEEDED"},
    )
    headers = mutation_headers(client)

    events_body = (
        await client.get("/api/v1/observability/events", params={"workspaceId": workspace_id}, headers=headers)
    ).json()
    assert events_body["code"] == "OK" and events_body["total"] >= 1
    assert events_body["data"][0]["eventType"] == "session.converged"

    metrics_body = (
        await client.get("/api/v1/observability/metrics", params={"workspaceId": workspace_id}, headers=headers)
    ).json()
    assert metrics_body["code"] == "OK"
    assert {item["metricKey"] for item in metrics_body["data"]} == set(METRIC_KEYS)


async def test_http_events_fail_closed_on_tampered_chain(client: AsyncClient, sqlite_path: Path) -> None:
    profile = await setup_identity(client, "events-tamper@qualityforge.example")
    workspace_id = profile["workspaceId"]
    planning_workflow_service.events.emit(
        tenant_id=str(profile["tenantId"]),
        workspace_id=workspace_id,
        actor_id=str(profile["userId"]),
        subject_type="work_item",
        subject_id="wi-http",
        event_type="work_item.transitioned",
        payload={"fromStatus": "DRAFT", "toStatus": "REWORK"},
    )
    connection = sqlite3.connect(sqlite_path)
    try:
        connection.execute("UPDATE domain_events SET actor_id = 'intruder'")
        connection.commit()
    finally:
        connection.close()
    response = await client.get(
        "/api/v1/observability/events",
        params={"workspaceId": workspace_id},
        headers=mutation_headers(client),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "EVENT_CHAIN_TAMPERED"


def test_login_password_not_hardcoded_weak() -> None:
    """卫生断言：本地口令常量保持强口令（与既有认证测试同口径）。"""
    assert len(LOCAL_PASSWORD) >= 16
