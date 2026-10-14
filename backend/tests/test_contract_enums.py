"""契约枚举防漂移断言（wall VERDICT req-contract-reconciliation 批次结束条件之一）。

32-API规范.yaml 的关键状态枚举必须与 33 号 CHECK 约束字面值一致；
任何一侧改动若未同步另一侧，本测试失败。期望值以 33 号库表 CHECK 为权威基线
（VERDICT D-1 裁决：AgentSession 以 33 为权威；05 §5.8 确立 33 为状态枚举权威源）。
"""

from tests.test_openapi_contract import load_authoritative_spec

# 权威基线：逐字摘自 docs/04-architecture/33-数据库Schema设计.md 对应 CHECK 约束
EXPECTED_ENUMS: dict[tuple[str, str], list[str]] = {
    # (schema 名, 属性名): 33 号 CHECK 值序
    ("PipelineRun", "status"): ["PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"],
    ("PipelineRun", "gateDecision"): ["PASSED", "WARNED", "BLOCKED", "QUARANTINED", "INCONCLUSIVE"],
    ("AgentSession", "status"): ["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "BLOCKED"],
    ("TestReport", "status"): ["ACTIVE", "ARCHIVED"],
    ("ExecutionTask", "status"): [
        "PENDING", "QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT", "BLOCKED",
    ],
    ("ExecutionResult", "status"): ["PASSED", "FAILED", "SKIPPED", "ERROR", "INCONCLUSIVE"],
}

# 已废弃值黑名单：出现在契约中即为漂移复活
FORBIDDEN_VALUES: dict[str, list[str]] = {
    "AgentSession.status": ["COMPLETED", "PAUSED_FOR_HUMAN"],  # 见 03 §13.13
    "PipelineRun.status": ["Running", "Passed", "Warned", "Blocked", "Quarantined"],  # 原 TitleCase 压扁单枚举
}


def _enum_of(schema: str, prop: str) -> list[str]:
    spec = load_authoritative_spec()
    return spec["components"]["schemas"][schema]["properties"][prop]["enum"]


def test_contract_enums_align_with_33_check_constraints() -> None:
    for (schema, prop), expected in EXPECTED_ENUMS.items():
        assert _enum_of(schema, prop) == expected, (
            f"{schema}.{prop} 枚举与 33 号 CHECK 不一致：实际 {_enum_of(schema, prop)}，期望 {expected}"
        )


def test_forbidden_legacy_enum_values_absent() -> None:
    for key, forbidden in FORBIDDEN_VALUES.items():
        schema, prop = key.split(".")
        actual = set(_enum_of(schema, prop))
        leaked = actual & set(forbidden)
        assert not leaked, f"{key} 枚举含已废弃值 {sorted(leaked)}（废弃依据见 03 §13.13 / VERDICT D-2）"


def test_test_report_version_schema_exists_with_version_pointers() -> None:
    spec = load_authoritative_spec()
    schemas = spec["components"]["schemas"]
    assert "TestReportVersion" in schemas, "TestReport 版本层缺失（P0-1）"
    report_props = schemas["TestReport"]["properties"]
    assert "currentVersionId" in report_props and "publishedVersionId" in report_props, (
        "TestReport 缺 current/published 版本指针（P0-1，REPORT_SIGNOFF 签署无法落地）"
    )
    version_props = schemas["TestReportVersion"]["properties"]
    for col in ["scopeSnapshotRef", "executionSnapshotRef", "reviewStatus", "contentDigest", "supersedesVersionId"]:
        assert col in version_props, f"TestReportVersion 缺字段 {col}（与 33 t_test_report_version 不对齐）"
