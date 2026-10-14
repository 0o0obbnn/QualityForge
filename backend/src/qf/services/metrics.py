"""受控 metricKey 计算服务（V1 D3/O3 裁决 ✅ 可计算项，20 号 §1.1 登记表）。

纯服务端计算、零手工录入；每项输出 metricKey/value/numerator/denominator/
window/computedAt/basis，其中 basis 显式声明分母口径与代理口径（AC-04：
无基线不立目标——本模块不产出任何目标值字段）。
数据源分两类：事件流型（domain_events 生命周期时间戳）与既有台账型
（provider_call_records / execution_evidence / defects / knowledge_entries /
golden_eval 黄金集评估）。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from qf.services.planning_workflow import _now

if TYPE_CHECKING:
    from qf.services.planning_workflow import PlanningWorkflowService

WINDOW_FULL_HISTORY = "FULL_HISTORY"

# 20 号 §1.1 登记表 ✅ 可计算项全集（25 项）；存在性断言以本常量为权威
METRIC_KEYS = (
    "eff_lead_time",
    "eff_cycle_time",
    "eff_gen_to_approve_time",
    "eff_ai_process_time",
    "eff_review_wait_time",
    "eff_blocked_time",
    "qual_first_pass_rate",
    "qual_rework_rate",
    "qual_rework_count_avg",
    "qual_reopen_rate",
    "qual_static_pass_rate",
    "qual_bug_valid_rate",
    "qual_bug_dup_rate",
    "qual_knowledge_stale_rate",
    "ai_gs_accuracy",
    "ai_gs_recall",
    "ai_violation_rate",
    "ai_false_block_rate",
    "ai_draft_accept_rate",
    "ai_task_success_rate",
    "ai_timeout_rate",
    "ai_retry_count",
    "ai_skill_error_rate",
    "trace_version_summary_completeness",
    "ops_degrade_rate",
)


def _ts(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def _seconds_between(start: str, end: str) -> float:
    return (_ts(end) - _ts(start)).total_seconds()


def _metric(
    key: str, *, numerator: float, denominator: float, basis: str, value: float | None
) -> dict[str, Any]:
    return {
        "metricKey": key,
        "value": value,
        "numerator": numerator,
        "denominator": denominator,
        "window": WINDOW_FULL_HISTORY,
        "computedAt": _now(),
        "basis": basis,
    }


def _ratio_metric(key: str, *, numerator: float, denominator: float, basis: str) -> dict[str, Any]:
    value = round(numerator / denominator, 4) if denominator else None
    return _metric(key, numerator=numerator, denominator=denominator, basis=basis, value=value)


def _mean_metric(key: str, *, samples: list[float], basis: str) -> dict[str, Any]:
    value = round(sum(samples) / len(samples), 4) if samples else None
    return _metric(key, numerator=float(len(samples)), denominator=float(len(samples)), basis=basis, value=value)


def _events_of(events: list[dict[str, Any]], event_type: str) -> list[dict[str, Any]]:
    return [event for event in events if event["eventType"] == event_type]


def compute_metrics(service: PlanningWorkflowService, workspace_id: str) -> list[dict[str, Any]]:
    """计算全部 25 项 ✅ metricKey（事件流型走 domain_events，台账型走既有台账）。"""
    events = service.events.load_events(workspace_id)
    records = service._store.load_provider_call_records()  # noqa: SLF001 - 同包服务层共享台账读取

    ws_items = [item for item in service.work_items.values() if item.get("workspaceId") == workspace_id]
    ws_defects = [item for item in service.defects.values() if item.get("workspaceId") == workspace_id]
    ws_knowledge = [item for item in service.knowledge_entries.values() if item.get("workspaceId") == workspace_id]
    ws_evidence = [item for item in service.execution_evidence.values() if item.get("workspaceId") == workspace_id]
    ws_results = [item for item in service.execution_results.values() if item.get("workspaceId") == workspace_id]
    ws_reviews = [item for item in service.review_tasks.values() if item.get("workspaceId") == workspace_id]

    decided = _events_of(events, "review.decided")
    generated = _events_of(events, "artifact.version.generated")

    # ===== eff_*：事件流型效率指标（秒） =====
    approved_items = [item for item in ws_items if item["status"] == "APPROVED"]
    lead_samples = [_seconds_between(item["createdAt"], item["updatedAt"]) for item in approved_items]
    metrics = [
        _mean_metric(
            "eff_lead_time",
            samples=lead_samples,
            basis="分母=达 APPROVED 终态的工作项数；口径=createdAt→批准后 updatedAt 秒数均值（事件流型）",
        )
    ]

    started = {event["subjectId"]: event for event in _events_of(events, "execution.started")}
    cycle_samples = [
        _seconds_between(started[event["subjectId"]]["occurredAt"], event["occurredAt"])
        for event in _events_of(events, "execution.finished")
        if event["subjectId"] in started
    ]
    metrics.append(
        _mean_metric(
            "eff_cycle_time",
            samples=cycle_samples,
            basis="分母=execution.started/finished 事件配对成功的执行任务数；口径=启动→终态秒数均值",
        )
    )

    gen_by_version = {event["payload"].get("versionId"): event for event in generated}
    gen_to_approve_samples = [
        _seconds_between(gen_by_version[version_id]["occurredAt"], event["occurredAt"])
        for event in decided
        if event["payload"].get("decision") == "APPROVE"
        and (version_id := event["payload"].get("artifactVersionId")) in gen_by_version
    ]
    metrics.append(
        _mean_metric(
            "eff_gen_to_approve_time",
            samples=gen_to_approve_samples,
            basis="分母=版本生成事件与 APPROVE 决定事件配对成功的产出物版本数；口径=生成→批准秒数均值",
        )
    )

    success_calls = [record for record in records if record["status"] == "SUCCESS"]
    metrics.append(
        _mean_metric(
            "eff_ai_process_time",
            samples=[float(record["durationMs"]) for record in success_calls],
            basis="分母=provider_call_records 中 SUCCESS 调用数；口径=durationMs 均值（全局台账，不按工作区切分）",
        )
    )

    wait_samples = [
        _seconds_between(task["createdAt"], task["decision"]["decidedAt"])
        for task in ws_reviews
        if task["decision"] is not None
    ]
    metrics.append(
        _mean_metric(
            "eff_review_wait_time",
            samples=wait_samples,
            basis="分母=已决定的审核任务数；口径=任务 createdAt→decidedAt 秒数均值",
        )
    )

    converged = _events_of(events, "session.converged")
    blocked_samples: list[float] = []
    per_session: dict[str, list[dict[str, Any]]] = {}
    for event in converged:
        per_session.setdefault(event["subjectId"], []).append(event)
    for series in per_session.values():
        for index, event in enumerate(series[:-1]):
            if event["payload"].get("status") == "BLOCKED":
                blocked_samples.append(_seconds_between(event["occurredAt"], series[index + 1]["occurredAt"]))
    metrics.append(
        _mean_metric(
            "eff_blocked_time",
            samples=blocked_samples,
            basis="分母=BLOCKED 收敛事件且其后存在下一次收敛事件的会话段数；口径=BLOCKED→下次收敛秒数均值",
        )
    )

    # ===== qual_*：质量指标 =====
    decisions_by_artifact: dict[str, list[dict[str, Any]]] = {}
    for event in decided:
        decisions_by_artifact.setdefault(str(event["payload"].get("artifactId")), []).append(event)
    first_pass = sum(
        1 for series in decisions_by_artifact.values() if series[0]["payload"].get("decision") == "APPROVE"
    )
    metrics.append(
        _ratio_metric(
            "qual_first_pass_rate",
            numerator=float(first_pass),
            denominator=float(len(decisions_by_artifact)),
            basis="分母=有过审核决定的产出物数；口径=首个决定即 APPROVE 的产出物占比",
        )
    )

    rework_series = [
        series
        for series in decisions_by_artifact.values()
        if any(event["payload"].get("decision") in {"REQUEST_CHANGES", "REJECT"} for event in series)
    ]
    metrics.append(
        _ratio_metric(
            "qual_rework_rate",
            numerator=float(len(rework_series)),
            denominator=float(len(decisions_by_artifact)),
            basis="分母=有过审核决定的产出物数；口径=曾收到 REQUEST_CHANGES/REJECT 的产出物占比",
        )
    )

    rework_count = sum(
        1
        for series in rework_series
        for event in series
        if event["payload"].get("decision") in {"REQUEST_CHANGES", "REJECT"}
    )
    metrics.append(
        _metric(
            "qual_rework_count_avg",
            numerator=float(rework_count),
            denominator=float(len(rework_series)),
            basis="分母=曾被退回的产出物数；口径=退回决定总数/退回产出物数",
            value=round(rework_count / len(rework_series), 4) if rework_series else None,
        )
    )

    transitions = _events_of(events, "work_item.transitioned")
    reopened_items = {
        event["subjectId"] for event in transitions if event["payload"].get("fromStatus") == "APPROVED"
    }
    ever_approved = {item["id"] for item in approved_items} | reopened_items
    metrics.append(
        _ratio_metric(
            "qual_reopen_rate",
            numerator=float(len(reopened_items)),
            denominator=float(len(ever_approved)),
            basis="分母=曾达 APPROVED 的工作项数；口径=从 APPROVED 迁回 REWORK（重开）的工作项占比",
        )
    )

    static_passed = sum(1 for evidence in ws_evidence if evidence["exitCode"] == 0)
    metrics.append(
        _ratio_metric(
            "qual_static_pass_rate",
            numerator=float(static_passed),
            denominator=float(len(ws_evidence)),
            basis="分母=本工作区执行证据条数；口径=exitCode==0 证据占比（参考执行静态口径声明）",
        )
    )

    valid_defects = sum(1 for defect in ws_defects if defect.get("approvedVersionId") is not None)
    metrics.append(
        _ratio_metric(
            "qual_bug_valid_rate",
            numerator=float(valid_defects),
            denominator=float(len(ws_defects)),
            basis="分母=已立缺陷数；口径=版本经人工审核批准（approvedVersionId 非空，即确认有效）的缺陷占比",
        )
    )

    dup_defects = sum(1 for defect in ws_defects if defect.get("duplicateOfDefectId") is not None)
    metrics.append(
        _ratio_metric(
            "qual_bug_dup_rate",
            numerator=float(dup_defects),
            denominator=float(len(ws_defects)),
            basis="分母=已立缺陷数；口径=标记 duplicateOfDefectId 的重复缺陷占比",
        )
    )

    stale_entries = sum(1 for entry in ws_knowledge if entry.get("status") == "STALE")
    metrics.append(
        _ratio_metric(
            "qual_knowledge_stale_rate",
            numerator=float(stale_entries),
            denominator=float(len(ws_knowledge)),
            basis="分母=知识条目数；口径=status==STALE 条目占比",
        )
    )

    # ===== ai_*：AI 效果指标（黄金集代理口径显式声明） =====
    from qf.providers.golden_eval import evaluate_provider  # 延迟导入：评估栈较重

    report = evaluate_provider(service._provider)  # noqa: SLF001 - 评估当前在役 provider
    metrics.append(
        _metric(
            "ai_gs_accuracy",
            numerator=1.0 if report["structureScoring"]["passed"] else 0.0,
            denominator=1.0,
            basis="代理口径=黄金集结构判分闸门级通过（1.0/0.0）；分母=单轮黄金集评估（C2 不接真实 LLM）",
            value=1.0 if report["structureScoring"]["passed"] else 0.0,
        )
    )
    negative_count = float(report["negativeCases"]["count"])
    false_accepts = float(len(report["negativeCases"]["falseAccepts"]))
    metrics.append(
        _metric(
            "ai_gs_recall",
            numerator=negative_count - false_accepts,
            denominator=negative_count,
            basis="代理口径=黄金集负例拒绝率=(负例数-误收数)/负例数；分母=负例用例数",
            value=round((negative_count - false_accepts) / negative_count, 4) if negative_count else None,
        )
    )

    decision_total = float(len(decided))
    rejects = [event for event in decided if event["payload"].get("decision") == "REJECT"]
    metrics.append(
        _ratio_metric(
            "ai_violation_rate",
            numerator=float(len(rejects)),
            denominator=decision_total,
            basis="代理口径=AI 草稿被 REJECT 决定占比；分母=审核决定事件总数",
        )
    )

    rejected_artifacts = {
        str(event["payload"].get("artifactId"))
        for event in decided
        if event["payload"].get("decision") in {"REQUEST_CHANGES", "REJECT"}
    }
    later_approved = {
        str(event["payload"].get("artifactId"))
        for event in decided
        if event["payload"].get("decision") == "APPROVE"
    }
    false_blocks = rejected_artifacts & later_approved
    metrics.append(
        _ratio_metric(
            "ai_false_block_rate",
            numerator=float(len(false_blocks)),
            denominator=float(len(rejected_artifacts)),
            basis="代理口径=被退回后新版本终获批准的产出物占比（疑似误拦）；分母=曾被退回的产出物数",
        )
    )

    approves = [event for event in decided if event["payload"].get("decision") == "APPROVE"]
    metrics.append(
        _ratio_metric(
            "ai_draft_accept_rate",
            numerator=float(len(approves)),
            denominator=decision_total,
            basis="口径=APPROVE 决定占全部审核决定事件比例；分母=审核决定事件总数",
        )
    )

    passed_results = sum(1 for result in ws_results if result["status"] == "PASSED")
    metrics.append(
        _ratio_metric(
            "ai_task_success_rate",
            numerator=float(passed_results),
            denominator=float(len(ws_results)),
            basis="口径=执行结果 PASSED 占比（确定性参考执行口径）；分母=执行结果条数",
        )
    )

    record_total = float(len(records))
    timeouts = sum(1 for record in records if record["status"] == "TIMEOUT")
    metrics.append(
        _ratio_metric(
            "ai_timeout_rate",
            numerator=float(timeouts),
            denominator=record_total,
            basis="口径=provider_call_records 中 TIMEOUT 占比（全局台账）；分母=调用记录总数",
        )
    )

    retry_attempts = sum(
        1
        for record in records
        if record["status"] in {"TIMEOUT", "INVALID_OUTPUT", "FAILED"} and not record["failover"]
    )
    metrics.append(
        _ratio_metric(
            "ai_retry_count",
            numerator=float(retry_attempts),
            denominator=record_total,
            basis="口径=触发重试的失败尝试次数占全部调用尝试比例（全局台账）；分母=调用记录总数",
        )
    )

    skill_errors = sum(1 for record in records if record["status"] in {"FAILED", "INVALID_OUTPUT"})
    metrics.append(
        _ratio_metric(
            "ai_skill_error_rate",
            numerator=float(skill_errors),
            denominator=record_total,
            basis="口径=FAILED/INVALID_OUTPUT 调用占比（技能级错误，全局台账）；分母=调用记录总数",
        )
    )

    # ===== trace_* / ops_* =====
    artifact_versions = [
        version
        for artifact_type, version in service.version_index.values()
        if artifact_type in {"TEST_STRATEGY", "TEST_PLAN", "TEST_CASE"}
        and version.get("workspaceId") == workspace_id
    ]
    with_summary = sum(1 for version in artifact_versions if version.get("changeSummary"))
    metrics.append(
        _ratio_metric(
            "trace_version_summary_completeness",
            numerator=float(with_summary),
            denominator=float(len(artifact_versions)),
            basis="口径=策略/计划/用例产出物版本中带 changeSummary 的比例（追溯完整性）；分母=版本数",
        )
    )

    failovers = sum(1 for record in records if record["failover"])
    metrics.append(
        _ratio_metric(
            "ops_degrade_rate",
            numerator=float(failovers),
            denominator=record_total,
            basis="口径=provider_call_records 中 failover=1 占比（降级率，全局台账）；分母=调用记录总数",
        )
    )

    assert {item["metricKey"] for item in metrics} == set(METRIC_KEYS)  # noqa: S101 - 登记表一致性守卫
    return metrics
