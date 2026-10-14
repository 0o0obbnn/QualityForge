"""I-1 集成验收——后端侧演示冒烟：对运行中的真实服务走通三类产出物闭环。

用法：先启动服务（make dev 或 uvicorn qf.main:app --port 8000，全新库），
再 `cd backend && uv run python scripts/i1_backend_smoke.py`。

覆盖（对齐 M1 实施计划 v1.1 §四 集成层 + GWT-5.5.12-2）：
- TEST_STRATEGY / TEST_PLAN：退回→产出物回 DRAFT→新版本递增+新审核任务→旧任务 STALE_VERSION→批准
- TEST_CASE：批准链路；会话收敛 SUCCEEDED、工作项 APPROVED、终态任务 TASK_CLOSED
"""

from __future__ import annotations

import hashlib
import os
import uuid
from typing import Any

import httpx

# 与 qf.services.auth_service.CSRF_COOKIE 保持一致（脚本自包含，不引后端包）
CSRF_COOKIE = "qf_csrf"

BASE = os.environ.get("QF_SMOKE_BASE", "http://127.0.0.1:8000")
RELEASE_ID = uuid.UUID("00000000-0000-0000-0000-000000000020")
SOURCE_SNAPSHOT_ID = uuid.UUID("00000000-0000-0000-0000-000000000030")
PASSWORD = "Local-review-password-2026"

PASSED: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    assert condition, f"FAIL: {name} {detail}"
    PASSED.append(name)
    print(f"  ✓ {name}")


def key(prefix: str) -> dict[str, str]:
    # Idempotency-Key min_length=16
    return {"Idempotency-Key": f"{prefix}-{uuid.uuid4().hex[:16]}"}


def strategy_v2() -> dict[str, Any]:
    return {
        "objective": "I-1 冒烟：退款链路第二版策略",
        "inScope": ["退款申请", "退款审批"],
        "outOfScope": ["未声明的外部写入"],
        "riskAssessment": [{"risk": "边界遗漏", "level": "MEDIUM", "treatment": "补负向用例"}],
        "testTypes": ["FUNCTIONAL", "NEGATIVE"],
        "approach": "风险驱动",
        "entryCriteria": ["退回意见已回应"],
        "exitCriteria": ["新版本通过审核"],
        "environmentStrategy": "受控测试环境",
        "dataStrategy": "可复现脱敏数据",
        "automationStrategy": "优先API",
        "defectStrategy": "先分析再立Defect",
        "changeSummary": "I-1 冒烟返工",
    }


def plan_v2(strategy_version_id: str, owner_id: str) -> dict[str, Any]:
    return {
        "strategyVersionId": strategy_version_id,
        "objective": "I-1 冒烟：执行第二版策略",
        "planType": "RELEASE_VALIDATION",
        "scope": {"focus": "审核意见整改"},
        "ownerId": owner_id,
        "startDate": "2026-08-17",
        "endDate": "2026-08-20",
        "milestones": [{"name": "返工复审", "exitGate": "NEW_VERSION_APPROVED"}],
        "resourceRequirements": {"reviewer": 1},
        "acceptanceCriteria": ["退回意见闭环"],
        "changeSummary": "I-1 冒烟返工",
    }


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE) as client:

        def csrf() -> dict[str, str]:
            return {"X-CSRF-Token": client.cookies[CSRF_COOKIE]}

        print("1) 身份初始化（首跑 setup，重跑 login）")
        status = await client.get("/api/v1/auth/status")
        identity = {
            "email": "i1-smoke@qualityforge.example",
            "password": PASSWORD,
        }
        if status.json()["data"]["setupRequired"]:
            resp = await client.post(
                "/api/v1/auth/setup",
                json={**identity, "tenantName": "I-1冒烟团队", "workspaceName": "I-1集成验收"},
            )
            check("auth/setup 201", resp.status_code == 201, resp.text)
        else:
            resp = await client.post("/api/v1/auth/login", json=identity)
            check("auth/login 200", resp.status_code == 200, resp.text)
        profile = resp.json()["data"]

        print("2) 需求源 + 工作项 + 会话")
        content = "# 订单退款\n用户可对已支付订单申请退款。"
        req = await client.post(
            "/api/v1/knowledge/requirements",
            headers={**csrf(), **key("i1req")},
            json={"workspaceId": profile["workspaceId"], "name": "订单退款需求", "documentType": "PRD"},
        )
        check("requirement 201", req.status_code == 201, req.text)
        ver = await client.post(
            f"/api/v1/knowledge/requirements/{req.json()['data']['id']}/versions",
            headers={**csrf(), **key("i1ver")},
            json={
                "sourceSnapshotId": str(SOURCE_SNAPSHOT_ID),
                "contentDigest": hashlib.sha256(content.encode()).hexdigest(),
                "content": content,
                "changeSummary": "首版",
            },
        )
        check("requirement version 201", ver.status_code == 201, ver.text)
        wi = await client.post(
            "/api/v1/work-items",
            headers={**csrf(), **key("i1wi")},
            json={
                "workspaceId": profile["workspaceId"],
                "releaseId": str(RELEASE_ID),
                "workItemType": "STRATEGY",
                "title": "I-1 冒烟：生成退款测试资产",
                "objective": "三类产出物全闭环",
                "acceptanceCriteria": "退回→新版本→复核→批准全部走通",
                "requiresReview": True,
                "priority": "P0",
                "riskLevel": "HIGH",
            },
        )
        check("work item 201", wi.status_code == 201, wi.text)
        work_item_id = wi.json()["data"]["id"]
        sess = await client.post(
            "/api/v1/ai/sessions",
            headers={**csrf(), **key("i1sess")},
            json={
                "workspaceId": profile["workspaceId"],
                "workItemId": work_item_id,
                "workflowKey": "gate0-planning-slice",
                "requirementVersionId": ver.json()["data"]["id"],
                "releaseId": str(RELEASE_ID),
                "ownerId": profile["userId"],
            },
        )
        check("ai/sessions 202", sess.status_code == 202, sess.text)
        session = sess.json()["data"]

        async def tasks() -> list[dict[str, Any]]:
            listed = await client.get("/api/v1/review-tasks", params={"workspaceId": profile["workspaceId"]})
            data: list[dict[str, Any]] = listed.json()["data"]
            return data

        async def decide(task_id: str, decision: str, digest: str) -> httpx.Response:
            return await client.post(
                f"/api/v1/review-tasks/{task_id}/decisions",
                headers={**csrf(), **key("i1dec")},
                json={"decision": decision, "contentDigest": digest},
            )

        initial = await tasks()
        current = [t for t in initial if t["workItemId"] == work_item_id]
        types = {t["artifactType"] for t in current}
        # deterministic-local provider 生成 4 条任务：strategy/plan 各 1 + case 2（见 test_planning_workflow）
        check(
            "三类产出物齐备（共 4 条任务）",
            types == {"TEST_STRATEGY", "TEST_PLAN", "TEST_CASE"} and len(current) == 4,
            str(sorted(types)),
        )
        by_type = {t["artifactType"]: t for t in current if t["artifactType"] != "TEST_CASE"}
        case_tasks = [t for t in current if t["artifactType"] == "TEST_CASE"]

        print("3) TEST_STRATEGY 闭环：退回→新版本→批准")
        strat_task = by_type["TEST_STRATEGY"]
        resp = await decide(strat_task["id"], "REQUEST_CHANGES", strat_task["contentDigest"])
        check("strategy REQUEST_CHANGES 200", resp.status_code == 200, resp.text)
        art = await client.get(
            f"/api/v1/review-tasks/{strat_task['id']}/artifact", params={"workspaceId": profile["workspaceId"]}
        )
        check("strategy 产出物回 DRAFT", art.json()["data"]["content"]["reviewStatus"] == "DRAFT")
        strategies = (
            await client.get("/api/v1/test-strategies", params={"workspaceId": profile["workspaceId"]})
        ).json()["data"]
        strat_root = next(item for item in strategies if item["id"] == strat_task["artifactId"])
        created = await client.post(
            f"/api/v1/test-strategies/{strat_root['id']}/versions",
            headers={**csrf(), **key("i1sv2")},
            json=strategy_v2(),
        )
        check("strategy v2 201", created.status_code == 201, created.text)
        strat_v2 = created.json()["data"]
        check("strategy 版本递增=2", strat_v2["version"] == 2)
        after = await tasks()
        current = [t for t in after if t["workItemId"] == work_item_id]
        new_strat_task = next(t for t in current if t["artifactVersionId"] == strat_v2["id"])
        old_strat_task = next(t for t in current if t["id"] == strat_task["id"])
        check(
            "strategy 新任务 OPEN 且可批准",
            new_strat_task["status"] == "OPEN" and new_strat_task["approveDisabledReason"] is None,
        )
        check("strategy 旧任务 STALE_VERSION", old_strat_task["approveDisabledReason"] == "STALE_VERSION")

        print("4) TEST_PLAN 闭环：退回→新版本（绑策略 v2）→批准")
        plan_task = by_type["TEST_PLAN"]
        resp = await decide(plan_task["id"], "REQUEST_CHANGES", plan_task["contentDigest"])
        check("plan REQUEST_CHANGES 200", resp.status_code == 200, resp.text)
        plans = (await client.get("/api/v1/test-plans", params={"workspaceId": profile["workspaceId"]})).json()["data"]
        plan_root = next(item for item in plans if item["id"] == plan_task["artifactId"])
        strategies = (
            await client.get("/api/v1/test-strategies", params={"workspaceId": profile["workspaceId"]})
        ).json()["data"]
        strat_root = next(item for item in strategies if item["id"] == strat_task["artifactId"])
        created = await client.post(
            f"/api/v1/test-plans/{plan_root['id']}/versions",
            headers={**csrf(), **key("i1pv2")},
            json=plan_v2(strat_root["currentVersionId"], profile["userId"]),
        )
        check("plan v2 201", created.status_code == 201, created.text)
        plan_v2_data = created.json()["data"]
        check(
            "plan 版本递增=2 且绑策略新版本",
            plan_v2_data["version"] == 2 and plan_v2_data["strategyVersionId"] == strat_v2["id"],
        )
        after = await tasks()
        current = [t for t in after if t["workItemId"] == work_item_id]
        new_plan_task = next(t for t in current if t["artifactVersionId"] == plan_v2_data["id"])
        check(
            "plan 新任务 OPEN 且可批准",
            new_plan_task["status"] == "OPEN" and new_plan_task["approveDisabledReason"] is None,
        )

        print("5) 批准新任务（strategy/plan）+ TEST_CASE 批准链路")
        stale = await decide(old_strat_task["id"], "APPROVE", old_strat_task["contentDigest"])
        check(
            "陈旧 strategy 任务决策被 409 拦截",
            stale.status_code == 409 and stale.json()["code"] == "INVALID_STATE_TRANSITION",
        )
        for task in [new_strat_task, new_plan_task, *case_tasks]:
            resp = await decide(task["id"], "APPROVE", task["contentDigest"])
            check(f"APPROVE {task['artifactType']} 200", resp.status_code == 200, resp.text)

        print("6) 收敛断言")
        reloaded = (
            await client.get(f"/api/v1/ai/sessions/{session['id']}", params={"workspaceId": profile["workspaceId"]})
        ).json()["data"]
        check("会话收敛 SUCCEEDED", reloaded["status"] == "SUCCEEDED" and reloaded["completedAt"] is not None)
        listed = (await client.get("/api/v1/work-items", params={"workspaceId": profile["workspaceId"]})).json()["data"]
        check("工作项 APPROVED", next(w for w in listed if w["id"] == work_item_id)["status"] == "APPROVED")
        final = await tasks()
        current = [t for t in final if t["workItemId"] == work_item_id]
        check("终态任务全部 TASK_CLOSED", all(t["approveDisabledReason"] == "TASK_CLOSED" for t in current))

        print("7) Journey C 执行链：执行计划→启动→结果→证据")
        exec_plan = await client.post(
            "/api/v1/execution-plans",
            headers={**csrf(), **key("i1ep")},
            json={
                "workspaceId": profile["workspaceId"],
                "planKey": "EXEC-I1-SMOKE-001",
                "name": "I-1 冒烟执行计划",
                "testPlanId": plan_root["id"],
            },
        )
        check("execution plan 201", exec_plan.status_code == 201, exec_plan.text)
        exec_plan_data = exec_plan.json()["data"]
        exec_run = await client.post(
            f"/api/v1/execution-plans/{exec_plan_data['id']}/runs",
            headers={**csrf(), **key("i1run")},
            json={"executionPlanVersionId": exec_plan_data["currentVersionId"]},
        )
        check("execution run 202", exec_run.status_code == 202, exec_run.text)
        check("执行任务 COMPLETED", exec_run.json()["data"]["status"] == "COMPLETED")
        exec_task_id = exec_run.json()["data"]["id"]
        results = await client.get("/api/v1/execution-results", params={"executionTaskId": exec_task_id})
        check("执行结果非空且带证据摘要", len(results.json()["data"]) > 0)

        print("8) D3 事件管道：事件流非空 + 事件流型 metricKey 全部有值")
        events_body = (
            await client.get(
                "/api/v1/observability/events",
                params={"workspaceId": profile["workspaceId"], "pageSize": 100},
            )
        ).json()
        check("事件流非空", events_body["total"] > 0 and len(events_body["data"]) > 0)
        present_types = {event["eventType"] for event in events_body["data"]}
        check(
            "核心生命周期事件齐备",
            {
                "artifact.version.generated",
                "review.decided",
                "session.converged",
                "execution.started",
                "execution.finished",
                "evidence.appended",
            }
            <= present_types,
            str(sorted(present_types)),
        )
        metrics_body = (
            await client.get("/api/v1/observability/metrics", params={"workspaceId": profile["workspaceId"]})
        ).json()
        metrics = {item["metricKey"]: item for item in metrics_body["data"]}
        check("25 项 ✅ metricKey 全量存在", len(metrics) == 25)
        event_stream_keys = (
            "eff_lead_time",
            "eff_cycle_time",
            "eff_gen_to_approve_time",
            "eff_review_wait_time",
            "eff_blocked_time",
        )
        check(
            "事件流型 metricKey 全部有值（无手工录入）",
            all(metrics[mk]["value"] is not None for mk in event_stream_keys),
            str({mk: metrics[mk]["value"] for mk in event_stream_keys}),
        )

        print(f"\nI-1 后端侧冒烟全绿：{len(PASSED)}/{len(PASSED)} 项断言通过")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
