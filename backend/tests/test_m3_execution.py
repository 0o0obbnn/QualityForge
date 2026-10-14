"""M3 执行与证据：createExecutionPlan / startExecutionPlan / listExecutionResults。

覆盖不可变证据（stdout/stderr/exit-code＋contentDigest）、人工批准生效、
三条隔离验证用例（直写 store / 伪造 digest / 重放旧摘要 → fail-closed）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any

from httpx import AsyncClient

from tests.test_planning_workflow import mutation_headers, setup_identity, start_session


def _data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


async def _bootstrap(client: AsyncClient) -> dict[str, Any]:
    profile = await setup_identity(client)
    await start_session(client, profile)
    plans = _data(await client.get("/api/v1/test-plans", params={"workspaceId": profile["workspaceId"]}))
    return {"profile": profile, "plan": plans[0]}


async def _create_execution_plan(client: AsyncClient, ctx: dict[str, Any]) -> dict[str, Any]:
    created = await client.post(
        "/api/v1/execution-plans",
        headers=mutation_headers(client),
        json={
            "workspaceId": ctx["profile"]["workspaceId"],
            "planKey": "EXEC-M3-001",
            "name": "M3 执行链验证计划",
            "testPlanId": ctx["plan"]["id"],
        },
    )
    assert created.status_code == 201, created.text
    return _data(created)


async def test_execution_chain_run_results_and_evidence_approval(client: AsyncClient) -> None:
    ctx = await _bootstrap(client)
    plan = await _create_execution_plan(client, ctx)
    assert plan["status"] == "ACTIVE"
    assert plan["currentVersionId"]

    started = await client.post(
        f"/api/v1/execution-plans/{plan['id']}/runs",
        headers=mutation_headers(client, idempotency_key="exec-run-0000000001"),
        json={"executionPlanVersionId": plan["currentVersionId"]},
    )
    assert started.status_code == 202, started.text
    task = _data(started)
    assert task["status"] == "COMPLETED"
    assert task["startedAt"] and task["completedAt"]

    replayed = await client.post(
        f"/api/v1/execution-plans/{plan['id']}/runs",
        headers=mutation_headers(client, idempotency_key="exec-run-0000000001"),
        json={"executionPlanVersionId": plan["currentVersionId"]},
    )
    assert replayed.status_code == 202
    assert _data(replayed)["id"] == task["id"]

    results = _data(
        await client.get("/api/v1/execution-results", params={"executionTaskId": task["id"]})
    )
    assert len(results) >= 1
    assert all(result["executionTaskId"] == task["id"] for result in results)
    assert all(result["status"] in {"PASSED", "FAILED", "SKIPPED", "ERROR", "INCONCLUSIVE"} for result in results)
    assert all(result["evidenceDigest"] for result in results)
    assert all(result["resultDigest"] and result["assertionResultsRef"] for result in results)
    evidence_digest = results[0]["evidenceDigest"]
    assert len(evidence_digest) == 64

    # 证据人工批准：decideReviewTask 绑定 EXECUTION_EVIDENCE（digest 一致才放行）
    tasks = _data(
        await client.get(
            "/api/v1/review-tasks",
            params={"workspaceId": ctx["profile"]["workspaceId"], "status": "OPEN"},
        )
    )
    evidence_task = next(t for t in tasks if t["artifactType"] == "EXECUTION_EVIDENCE")
    assert evidence_task["contentDigest"] == evidence_digest
    approved = await client.post(
        f"/api/v1/review-tasks/{evidence_task['id']}/decisions",
        headers=mutation_headers(client, idempotency_key=f"evidence-{evidence_task['id']}"),
        json={"decision": "APPROVE", "contentDigest": evidence_task["contentDigest"]},
    )
    assert approved.status_code == 200, approved.text
    assert _data(approved)["status"] == "APPROVED"


async def test_execution_result_carries_server_computed_digest_and_assertion_ref(client: AsyncClient) -> None:
    """B1：ExecutionResult 携带 resultDigest/assertionResultsRef 且非空，可回溯到断言明细。

    响应模型 extra=forbid 校验三层一致；resultDigest 可由状态+断言统计+结果文本重放（服务端计算）；
    assertionResultsRef 可解析回证据存储中的断言结果 JSON 条目。
    """
    from qf.schemas.execution import ExecutionResult
    from qf.services.planning_workflow import content_digest, planning_workflow_service

    ctx = await _bootstrap(client)
    plan = await _create_execution_plan(client, ctx)
    started = await client.post(
        f"/api/v1/execution-plans/{plan['id']}/runs",
        headers=mutation_headers(client, idempotency_key="exec-run-b1-digest-01"),
        json={"executionPlanVersionId": plan["currentVersionId"]},
    )
    task = _data(started)
    results = _data(
        await client.get("/api/v1/execution-results", params={"executionTaskId": task["id"]})
    )
    assert results, "执行完成后必须存在结果"

    for result in results:
        # 响应模型即三层契约：多余/缺失字段会直接抛校验错误
        ExecutionResult.model_validate(result)
        assert len(result["resultDigest"]) == 64
        assert result["assertionResultsRef"].startswith("evidence:")
        assert result["assertionResultsRef"].endswith("/assertions")

    for result in results:
        evidence_id = result["assertionResultsRef"].removeprefix("evidence:").removesuffix("/assertions")
        # 引用与 logRef 指向同一条不可变证据
        assert result["logRef"] == f"evidence:{evidence_id}"
        evidence = planning_workflow_service.execution_evidence[evidence_id]
        assertions = evidence["assertions"]
        assert assertions, "断言结果明细必须非空"
        assert all({"key", "expectation", "actual", "outcome"} <= set(entry) for entry in assertions)
        outcomes = [entry["outcome"] for entry in assertions]
        assert all(outcome in {"PASSED", "FAILED"} for outcome in outcomes)
        if result["status"] == "FAILED":
            assert "FAILED" in outcomes, "失败结果必须至少一条失败断言（与 stderr 口径一致）"
        else:
            assert outcomes.count("FAILED") == 0, "通过结果不允许失败断言"
        # resultDigest 服务端规范化：由状态+断言统计+结果文本重放必须一致
        recomputed = content_digest(
            {
                "status": result["status"],
                "assertionStats": {
                    "total": len(assertions),
                    "passed": outcomes.count("PASSED"),
                    "failed": outcomes.count("FAILED"),
                },
                "resultText": (evidence["stdout"] + evidence["stderr"]).strip(),
            }
        )
        assert result["resultDigest"] == recomputed


async def test_result_digest_is_not_client_injectable(client: AsyncClient) -> None:
    """B1 防伪：resultDigest/assertionResultsRef 不由客户端提供——注入即被 422 拒绝。"""
    ctx = await _bootstrap(client)
    plan = await _create_execution_plan(client, ctx)
    forged = await client.post(
        f"/api/v1/execution-plans/{plan['id']}/runs",
        headers=mutation_headers(client, idempotency_key="exec-run-b1-forge-01"),
        json={
            "executionPlanVersionId": plan["currentVersionId"],
            "resultDigest": "0" * 64,
            "assertionResultsRef": "evidence:attacker/assertions",
        },
    )
    assert forged.status_code == 422, forged.text


async def test_result_digest_fields_survive_reload_and_column_persist(client: AsyncClient) -> None:
    """B1 落库：模拟重启后两字段仍在（payload_json 权威）且 v8 列投影已写入。"""
    from qf.services.planning_workflow import planning_workflow_service

    ctx = await _bootstrap(client)
    plan = await _create_execution_plan(client, ctx)
    started = await client.post(
        f"/api/v1/execution-plans/{plan['id']}/runs",
        headers=mutation_headers(client, idempotency_key="exec-run-b1-persist-01"),
        json={"executionPlanVersionId": plan["currentVersionId"]},
    )
    task = _data(started)

    # 列投影已写入（schema v8）
    with planning_workflow_service._store.connect() as connection:
        rows = connection.execute(
            "SELECT result_digest, assertion_results_ref FROM execution_results"
        ).fetchall()
    assert rows and all(row["result_digest"] and row["assertion_results_ref"] for row in rows)

    # 模拟进程重启：重载后列表读取仍带出两字段
    planning_workflow_service._reload_store_state()
    results = _data(
        await client.get("/api/v1/execution-results", params={"executionTaskId": task["id"]})
    )
    assert results
    assert all(result["resultDigest"] and result["assertionResultsRef"] for result in results)


async def test_replay_same_plan_version_is_rejected(client: AsyncClient) -> None:
    """重放旧摘要向量之一：同一执行计划版本不允许二次执行（409）。"""
    ctx = await _bootstrap(client)
    plan = await _create_execution_plan(client, ctx)
    first = await client.post(
        f"/api/v1/execution-plans/{plan['id']}/runs",
        headers=mutation_headers(client, idempotency_key="exec-run-replay-001"),
        json={"executionPlanVersionId": plan["currentVersionId"]},
    )
    assert first.status_code == 202, first.text
    second = await client.post(
        f"/api/v1/execution-plans/{plan['id']}/runs",
        headers=mutation_headers(client, idempotency_key="exec-run-replay-002"),
        json={"executionPlanVersionId": plan["currentVersionId"]},
    )
    assert second.status_code == 409
    assert second.json()["code"] == "EXECUTION_ALREADY_RUN"


async def test_stale_evidence_digest_approval_is_rejected(client: AsyncClient) -> None:
    """重放旧摘要向量之二：批准证据时 digest 与当前证据不一致 → 409 STALE_ARTIFACT_VERSION。"""
    ctx = await _bootstrap(client)
    plan = await _create_execution_plan(client, ctx)
    await client.post(
        f"/api/v1/execution-plans/{plan['id']}/runs",
        headers=mutation_headers(client, idempotency_key="exec-run-stale-0001"),
        json={"executionPlanVersionId": plan["currentVersionId"]},
    )
    tasks = _data(
        await client.get(
            "/api/v1/review-tasks",
            params={"workspaceId": ctx["profile"]["workspaceId"], "status": "OPEN"},
        )
    )
    evidence_task = next(t for t in tasks if t["artifactType"] == "EXECUTION_EVIDENCE")
    forged = await client.post(
        f"/api/v1/review-tasks/{evidence_task['id']}/decisions",
        headers=mutation_headers(client, idempotency_key="evidence-stale-000001"),
        json={"decision": "APPROVE", "contentDigest": "0" * 64},
    )
    assert forged.status_code == 409
    assert forged.json()["code"] == "STALE_ARTIFACT_VERSION"


async def test_direct_store_write_tampering_fails_closed(client: AsyncClient) -> None:
    """直写 store 向量：绕过服务层直接篡改证据行 → 完整性校验 fail-closed。"""
    from qf.services.planning_workflow import DomainError, planning_workflow_service

    ctx = await _bootstrap(client)
    plan = await _create_execution_plan(client, ctx)
    await client.post(
        f"/api/v1/execution-plans/{plan['id']}/runs",
        headers=mutation_headers(client, idempotency_key="exec-run-tamper-001"),
        json={"executionPlanVersionId": plan["currentVersionId"]},
    )

    store = planning_workflow_service._store
    with store.connect() as connection:
        # 强制改为与任何真实证据都不同的退出码（真实值只会是 0/1），保证必然触发篡改
        updated = connection.execute(
            "UPDATE execution_evidence SET payload_json = json_set(payload_json, '$.exitCode', 42)"
        ).rowcount
    assert updated >= 1, "tampering setup must touch at least one evidence row"

    try:
        with open("/dev/null", "w", encoding="utf-8"):
            pass
        planning_workflow_service.verify_evidence_integrity()
        raise AssertionError("篡改后的证据必须触发完整性校验失败")
    except DomainError as exc:
        assert exc.code == "EVIDENCE_TAMPERED"

    # 恢复被篡改的行（用内存态回写），保证后续测试与持久化状态一致
    planning_workflow_service._restore_evidence_from_memory()
    planning_workflow_service.verify_evidence_integrity()


async def test_concurrent_start_and_recovery_integrity(client: AsyncClient) -> None:
    """C3 并发回归＋最薄恢复证据：并发同键启动收敛为一个任务；重载后证据完整性仍然成立。"""
    from qf.services.planning_workflow import planning_workflow_service

    ctx = await _bootstrap(client)
    plan = await _create_execution_plan(client, ctx)

    async def run() -> int:
        response = await client.post(
            f"/api/v1/execution-plans/{plan['id']}/runs",
            headers=mutation_headers(client, idempotency_key="exec-run-conc-0001"),
            json={"executionPlanVersionId": plan["currentVersionId"]},
        )
        assert response.status_code == 202, response.text
        return response.json()["data"]["id"]

    task_ids = await asyncio.gather(run(), run(), run())
    assert len(set(task_ids)) == 1

    tasks = _data(await client.get("/api/v1/execution-tasks", params={"workspaceId": ctx["profile"]["workspaceId"]}))
    assert len(tasks) == 1

    # 最薄恢复证据口径：模拟进程重启（重载存储）后完整性校验通过
    planning_workflow_service._reload_store_state()
    planning_workflow_service.verify_evidence_integrity()
    results = _data(
        await client.get("/api/v1/execution-results", params={"executionTaskId": task_ids[0]})
    )
    assert len(results) >= 1


async def test_evidence_digest_is_canonical_and_server_side(client: AsyncClient) -> None:
    """伪造 digest 向量：证据摘要由服务端对 stdout/stderr/exitCode 规范化计算，客户端无从注入。"""
    from qf.services.planning_workflow import planning_workflow_service

    ctx = await _bootstrap(client)
    plan = await _create_execution_plan(client, ctx)
    started = await client.post(
        f"/api/v1/execution-plans/{plan['id']}/runs",
        headers=mutation_headers(client, idempotency_key="exec-run-digest-001"),
        json={"executionPlanVersionId": plan["currentVersionId"]},
    )
    task = _data(started)
    evidences = [
        evidence
        for evidence in planning_workflow_service.execution_evidence.values()
        if evidence["executionTaskId"] == task["id"]
    ]
    assert evidences, "每次执行必须落不可变证据"
    for evidence in evidences:
        payload = {
            "stdout": evidence["stdout"],
            "stderr": evidence["stderr"],
            "exitCode": evidence["exitCode"],
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        assert evidence["contentDigest"] == hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def test_store_performance_baseline_is_recorded(client: AsyncClient) -> None:
    """C3 最薄性能基线：全量快照 save/load 与证据追加写在本地 SQLite 形态下保持毫秒级。

    口径：只记录不断言硬阈值（基线先行，目标值待试点后批准，见方案-v1.1 §四 D4）；
    但设置宽松哨兵防止数量级退化（单项 > 1s 视为异常）。
    """
    from qf.services.planning_workflow import planning_workflow_service

    ctx = await _bootstrap(client)
    plan = await _create_execution_plan(client, ctx)
    await client.post(
        f"/api/v1/execution-plans/{plan['id']}/runs",
        headers=mutation_headers(client, idempotency_key="exec-run-perf-00001"),
        json={"executionPlanVersionId": plan["currentVersionId"]},
    )

    started = time.perf_counter()
    planning_workflow_service._persist()
    save_ms = (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    planning_workflow_service._reload_store_state()
    load_ms = (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    evidence = next(iter(planning_workflow_service.execution_evidence.values()))
    planning_workflow_service._store.append_evidence({**evidence, "id": hashlib.sha256(b"baseline").hexdigest()})
    append_ms = (time.perf_counter() - started) * 1000

    baseline = {"save_ms": round(save_ms, 3), "load_ms": round(load_ms, 3), "evidence_append_ms": round(append_ms, 3)}
    print(f"\n[M3-C3 performance baseline] {baseline}")
    assert save_ms < 1000 and load_ms < 1000 and append_ms < 1000, f"存储基线数量级退化: {baseline}"

    # 清理基线哨兵行，保证后续测试与持久化状态一致
    planning_workflow_service._restore_evidence_from_memory()
    planning_workflow_service.verify_evidence_integrity()
