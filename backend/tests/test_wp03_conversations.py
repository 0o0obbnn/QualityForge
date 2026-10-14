"""WP-03 协作对话最小切片专项（批次五十四，39 号 §3 承载）。

覆盖：会话创建/列表/跨 Workspace 隔离、幂等重放、消息只追加与排序、
dataClass/digest 校验负向、404 资源域、事件登记与 lastBusinessUpdatedAt 联动。
"""

from __future__ import annotations

import hashlib
import uuid

from httpx import AsyncClient

from qf.services.planning_workflow import planning_workflow_service
from tests.test_planning_workflow import mutation_headers, setup_identity


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _message_body(text: str, *, data_class: str = "INTERNAL", digest: str | None = None) -> dict[str, object]:
    return {
        "messageType": "TEXT",
        "contentRef": f"conv-ref://{hashlib.sha1(text.encode()).hexdigest()}",
        "contentDigest": digest if digest is not None else _digest(text),
        "dataClass": data_class,
    }


async def test_conversation_lifecycle_and_isolation(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    ws1 = profile["workspaceId"]

    created = await client.post(
        "/api/v1/conversations",
        headers=mutation_headers(client, idempotency_key="wp03-conv-create-0001"),
        json={"workspaceId": ws1, "title": "退款策略协作"},
    )
    assert created.status_code == 201, created.text
    conversation = created.json()["data"]
    assert conversation["status"] == "ACTIVE" and conversation["createdBy"] == profile["userId"]

    # 幂等重放：同键同指纹 → 同一会话
    replay = await client.post(
        "/api/v1/conversations",
        headers=mutation_headers(client, idempotency_key="wp03-conv-create-0001"),
        json={"workspaceId": ws1, "title": "退款策略协作"},
    )
    assert replay.status_code == 201
    assert replay.json()["data"]["id"] == conversation["id"]

    listed = await client.get("/api/v1/conversations", params={"workspaceId": ws1})
    assert listed.status_code == 200
    assert any(item["id"] == conversation["id"] for item in listed.json()["data"])

    # 跨 Workspace 查询 403；第二工作区看不到 ws1 会话
    assert (
        await client.get("/api/v1/conversations", params={"workspaceId": str(uuid.uuid4())})
    ).status_code == 403
    seeded = planning_workflow_service.seed_workspace(profile["tenantId"], profile["userId"], "第二项目")
    switched = await client.post(
        "/api/v1/auth/switch-workspace",
        headers=mutation_headers(client),
        json={"workspaceId": seeded["id"]},
    )
    assert switched.status_code == 200
    ws2_list = await client.get("/api/v1/conversations", params={"workspaceId": seeded["id"]})
    assert ws2_list.status_code == 200 and ws2_list.json()["data"] == []
    back = await client.post(
        "/api/v1/auth/switch-workspace",
        headers=mutation_headers(client),
        json={"workspaceId": ws1},
    )
    assert back.status_code == 200


async def test_message_append_rules_and_events(client: AsyncClient) -> None:
    profile = await setup_identity(client)
    ws1 = profile["workspaceId"]
    conversation = (
        await client.post(
            "/api/v1/conversations",
            headers=mutation_headers(client, idempotency_key="wp03-msg-conv-00001"),
            json={"workspaceId": ws1, "title": "消息规则验证"},
        )
    ).json()["data"]

    first = await client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=mutation_headers(client, idempotency_key="wp03-msg-append-0001"),
        json=_message_body("第一条约制消息"),
    )
    assert first.status_code == 201, first.text
    assert first.json()["data"]["actorType"] == "USER"

    second = await client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=mutation_headers(client, idempotency_key="wp03-msg-append-0002"),
        json=_message_body("第二条：请确认退款风控口径", data_class="CONFIDENTIAL"),
    )
    assert second.status_code == 201

    # 幂等重放同条消息 → 同 id（只追加日志不重复）
    replay = await client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=mutation_headers(client, idempotency_key="wp03-msg-append-0002"),
        json=_message_body("第二条：请确认退款风控口径", data_class="CONFIDENTIAL"),
    )
    assert replay.status_code == 201
    assert replay.json()["data"]["id"] == second.json()["data"]["id"]

    messages = await client.get(f"/api/v1/conversations/{conversation['id']}/messages")
    assert messages.status_code == 200
    data = messages.json()["data"]
    assert len(data) == 2
    # 只追加日志按 createdAt 升序
    assert data[0]["createdAt"] <= data[1]["createdAt"]

    # lastActivityAt 随消息推进
    refreshed = await client.get("/api/v1/conversations", params={"workspaceId": ws1})
    conv_row = next(item for item in refreshed.json()["data"] if item["id"] == conversation["id"])
    assert conv_row["lastActivityAt"] >= data[1]["createdAt"]

    # 负向：digest 非法 / dataClass 越界 → 422
    bad_digest = await client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=mutation_headers(client, idempotency_key="wp03-msg-append-0003"),
        json=_message_body("坏摘要", digest="0" * 63),
    )
    assert bad_digest.status_code == 422
    bad_class = await client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=mutation_headers(client, idempotency_key="wp03-msg-append-0004"),
        json=_message_body("坏分级", data_class="SECRET"),
    )
    assert bad_class.status_code == 422

    # 负向：不存在的会话 → 404
    missing = await client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/messages",
        headers=mutation_headers(client, idempotency_key="wp03-msg-append-0005"),
        json=_message_body("孤儿"),
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"

    # 事件登记：conversation.message.appended 进领域事件，且刷新 lastBusinessUpdatedAt
    events = await client.get("/api/v1/observability/events", params={"workspaceId": ws1, "pageSize": 100})
    event_types = {event["eventType"] for event in events.json()["data"]}
    assert "conversation.message.appended" in event_types
    workspaces = (await client.get("/api/v1/workspaces")).json()["data"]
    ws_row = next(item for item in workspaces if item["id"] == ws1)
    assert ws_row["lastBusinessUpdatedAt"] >= data[0]["createdAt"]
