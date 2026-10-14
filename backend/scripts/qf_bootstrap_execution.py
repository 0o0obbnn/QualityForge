"""对运行中的本地后端(127.0.0.1:8000)走完 需求→工作项→Agent会话→测试计划→执行计划→启动执行 全链路,产生真实数据供 UI 走查。

复刻 backend/tests/test_m3_execution.py 的 bootstrap 序列,但针对已存在的本地库(跳过 setup)。
"""

import hashlib
import sys

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
EMAIL = "liuyibin@cs.cn"
PASSWORD = "admin123456"
SOURCE_SNAPSHOT_ID = "00000000-0000-0000-0000-000000000030"
RELEASE_ID = "00000000-0000-0000-0000-000000000020"


def data(resp: httpx.Response):
    return resp.json().get("data")


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=30) as c:
        login = c.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
        login.raise_for_status()
        profile = data(login)
        csrf = c.cookies.get("qf_csrf")
        headers = {"X-CSRF-Token": csrf or ""}
        print("profile:", profile["email"], profile["workspaceId"][:8])
        ws = profile["workspaceId"]

        # 1. 需求文档 + 版本
        req = c.post(
            "/knowledge/requirements",
            headers=headers,
            json={"workspaceId": ws, "name": "订单退款需求", "documentType": "PRD"},
        )
        req.raise_for_status()
        req_id = data(req)["id"]
        content = "# 订单退款\n用户可对已支付订单申请退款。\n非法状态和越权请求必须被拒绝。"
        ver = c.post(
            f"/knowledge/requirements/{req_id}/versions",
            headers=headers,
            json={
                "sourceSnapshotId": SOURCE_SNAPSHOT_ID,
                "contentDigest": hashlib.sha256(content.encode()).hexdigest(),
                "content": content,
                "changeSummary": "首版",
            },
        )
        ver.raise_for_status()
        req_version_id = data(ver)["id"]
        print("requirement:", req_id[:8], "version:", req_version_id[:8])

        # 2. 工作项
        wi = c.post(
            "/work-items",
            headers=headers,
            json={
                "workspaceId": ws,
                "releaseId": RELEASE_ID,
                "workItemType": "STRATEGY",
                "title": "生成退款测试资产(走查)",
                "objective": "验证退款链路合法与非法路径",
                "acceptanceCriteria": "非法状态与越权全部被拒绝",
                "requiresReview": True,
                "priority": "P0",
                "riskLevel": "HIGH",
            },
        )
        wi.raise_for_status()
        wi_id = data(wi)["id"]
        print("work-item:", wi_id[:8])

        # 3. Agent 会话(生成 策略/计划/用例)
        sess = c.post(
            "/ai/sessions",
            headers={**headers, "Idempotency-Key": "walkthrough-session-0001"},
            json={
                "workspaceId": ws,
                "workItemId": wi_id,
                "workflowKey": "gate0-planning-slice",
                "requirementVersionId": req_version_id,
                "releaseId": RELEASE_ID,
                "ownerId": profile["userId"],
            },
        )
        print("ai/sessions status:", sess.status_code, sess.text[:200])

        # 4. 取测试计划
        plans = data(c.get("/test-plans", params={"workspaceId": ws}))
        if not plans:
            print("ERROR: 无测试计划生成")
            return 1
        plan = plans[0]
        print("test-plan:", plan["id"][:8], "name:", plan.get("name"), "status:", plan.get("status"))

        # 5. 建执行计划
        ep = c.post(
            "/execution-plans",
            headers=headers,
            json={"workspaceId": ws, "planKey": "EP-WALK-001", "name": "走查执行计划", "testPlanId": plan["id"]},
        )
        ep.raise_for_status()
        ep_data = data(ep)
        print(
            "execution-plan:", ep_data["id"][:8], "status:", ep_data["status"], "versionId:", ep_data["currentVersionId"][:8]
        )

        # 6. 启动执行(唯一能产生任务/事件/结果的入口)
        run = c.post(
            f"/execution-plans/{ep_data['id']}/runs",
            headers={**headers, "Idempotency-Key": "walkthrough-run-0001"},
            json={"executionPlanVersionId": ep_data["currentVersionId"]},
        )
        print("startExecutionPlan status:", run.status_code, run.text[:200])
        if run.status_code in (200, 201, 202):
            task = data(run)
            print("task:", task["id"][:8], "status:", task["status"])

        # 7. 汇总
        events = data(c.get("/observability/events", params={"workspaceId": ws, "pageSize": 100}))
        print("events total:", events.get("total") if isinstance(events, dict) else len(events))
        items = events.get("items", events) if isinstance(events, dict) else events
        for e in items[:12]:
            print("  event:", e.get("eventId", "")[:8], e.get("eventType"), e.get("subjectType"), e.get("occurredAt", "")[11:19])

        tasks = data(c.get("/execution-tasks", params={"workspaceId": ws}))
        print("execution-tasks:", len(tasks))
        for t in tasks[:5]:
            print("  task:", t["id"][:8], t.get("status"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
