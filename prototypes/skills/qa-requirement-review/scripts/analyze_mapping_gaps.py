#!/usr/bin/env python3
"""Convert explicit mapping gaps into evidence-scoped QA findings."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def stable_id(prefix: str, *parts: Any) -> str:
    value = "|".join(" ".join(str(part or "").split()).casefold() for part in parts)
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:12].upper()}"


DIMENSION_BY_CODE = {
    "AMBIGUOUS_LANGUAGE": "ambiguity",
    "MISSING_REQUIRED_ACTOR": "role_permission",
    "UNTESTABLE_ACCEPTANCE_CRITERIA": "testability",
    "INCOMPLETE_REQUIREMENT": "completeness",
    "CROSS_SOURCE_CONFLICT": "consistency",
    "MISSING_REFERENCED_ARTIFACT": "completeness",
    "MISSING_EXISTING_BASELINE": "completeness",
    "PENDING_REQUIRED_ARTIFACT": "completeness",
    "UNRESOLVED_INTERNAL_REFERENCE": "consistency",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed QA findings from explicit mapping gaps"
    )
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    review = json.loads(args.review.read_text(encoding="utf-8"))
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    atomics = {
        item.get("atomic_id"): item
        for item in mapping.get("atomic_functions", [])
        if isinstance(item, dict)
    }
    bindings_by_atomic: dict[str, list[dict[str, Any]]] = {}
    for binding in mapping.get("field_bindings", []):
        if isinstance(binding, dict):
            bindings_by_atomic.setdefault(binding.get("atomic_id"), []).append(binding)
    findings = list(review.get("findings", []))
    by_requirement: dict[str, list[str]] = {}

    def add(
        requirement: dict[str, Any],
        atomic: dict[str, Any],
        code: str,
        severity: str,
        expected: str,
        question: str,
        affected_test_dimensions: list[str],
    ) -> None:
        locators = [
            f"{proof.get('source_id')}:{proof.get('locator')}"
            for proof in atomic.get("evidence", [])
            if isinstance(proof, dict)
        ]
        first_locator = locators[0].split(":", 1)[1] if locators else None
        context = atomic.get("name", "")
        if first_locator:
            context = f"{context}（{first_locator}）"
        finding_id = stable_id("RQF", requirement.get("requirement_id"), code)
        findings.append(
            {
                "finding_id": finding_id,
                "code": code,
                "severity": severity,
                "certainty": "risk",
                "origin": "deterministic_candidate",
                "evidence_type": "ABSENCE",
                "requirement_ids": [requirement["requirement_id"]],
                "function_ids": requirement.get("function_refs", []),
                "atomic_ids": requirement.get("atomic_refs", []),
                "affected_test_dimensions": affected_test_dimensions,
                "source_refs": locators,
                "evidence": f"已检查该最小功能的来源证据及结构化属性，未找到{expected}",
                "inspected_scope": locators,
                "expected_element": expected,
                "question": f"{context}：{question}" if context else question,
                "recommendation": f"在需求中补充{expected}并给出可验证示例。",
            }
        )
        by_requirement.setdefault(requirement["requirement_id"], []).append(finding_id)

    for requirement in review.get("requirements", []):
        atomic = atomics.get(next(iter(requirement.get("atomic_refs", [])), None))
        if not atomic:
            continue
        if not atomic.get("actor") or "待确认" in str(atomic.get("actor")):
            add(
                requirement,
                atomic,
                "MISSING_REQUIRED_ACTOR",
                "REVIEW",
                "执行角色及其权限边界",
                "哪个角色可以执行该行为，哪些角色必须被拒绝？",
                ["permission"],
            )
        bindings = bindings_by_atomic.get(atomic.get("atomic_id"), [])
        result_text = " ".join(
            map(
                str,
                [
                    *(atomic.get("outputs") or []),
                    *(atomic.get("state_changes") or []),
                    *(atomic.get("branches") or []),
                    *(atomic.get("processing_rules") or []),
                ],
            )
        )
        explicit_result = bool(result_text) and not any(
            token in result_text for token in ("待语义复核", "待确认", "原文仅确认")
        )
        bound_observable = any(
            set(binding.get("usages", [])) & {"display", "output", "validation"}
            or binding.get("rules")
            for binding in bindings
        )
        if not explicit_result and not bound_observable:
            add(
                requirement,
                atomic,
                "UNTESTABLE_ACCEPTANCE_CRITERIA",
                "REJECT",
                "可观察且可判定的成功/失败结果",
                "该行为完成、失败或被拒绝时分别应观察到什么？",
                ["functional"],
            )
        if (
            atomic.get("status") == "unresolved"
            or atomic.get("origin") == "function_fallback"
            or any(
                token in str(atomic.get("action", ""))
                for token in ("待确认", "待从原文")
            )
        ):
            add(
                requirement,
                atomic,
                "INCOMPLETE_REQUIREMENT",
                "REVIEW",
                "明确触发条件、前置条件和处理规则",
                "该行为在什么条件下触发，执行前需要满足哪些状态与数据条件？",
                ["functional"],
            )
            add(
                requirement,
                atomic,
                "AMBIGUOUS_LANGUAGE",
                "REVIEW",
                "可唯一解释的具体动作及业务结果",
                "该功能标题下具体包含哪些可独立触发并观察结果的行为？",
                ["functional"],
            )

    requirements_by_atomic = {
        atomic_id: requirement
        for requirement in review.get("requirements", [])
        for atomic_id in requirement.get("atomic_refs", [])
    }
    requirements_by_field: dict[str, list[dict[str, Any]]] = {}
    for requirement in review.get("requirements", []):
        for field_id in requirement.get("field_refs", []):
            requirements_by_field.setdefault(field_id, []).append(requirement)
    for conflict in mapping.get("gaps", {}).get("conflicts", []):
        if not isinstance(conflict, dict) or conflict.get("status") == "resolved":
            continue
        atomic_id = next(
            (
                value
                for value in conflict.get("entity_ids", [])
                if value in requirements_by_atomic
            ),
            None,
        )
        affected_requirements = [requirements_by_atomic[atomic_id]] if atomic_id else []
        if not affected_requirements:
            for field_id in conflict.get("entity_ids", []):
                affected_requirements.extend(requirements_by_field.get(field_id, []))
        affected_requirements = list(
            {item["requirement_id"]: item for item in affected_requirements}.values()
        )
        if not affected_requirements:
            continue
        evidence = conflict.get("evidence", [])
        refs = [
            f"{item.get('source_id')}:{item.get('locator')}"
            for item in evidence
            if isinstance(item, dict)
        ]
        for requirement in affected_requirements:
            finding_id = stable_id(
                "RQF",
                requirement["requirement_id"],
                "CROSS_SOURCE_CONFLICT",
                conflict.get("summary"),
            )
            findings.append(
                {
                    "finding_id": finding_id,
                    "code": "CROSS_SOURCE_CONFLICT",
                    "severity": "REJECT",
                    "certainty": "risk",
                    "origin": "deterministic_candidate",
                    "evidence_type": "CONFLICT",
                    "requirement_ids": [requirement["requirement_id"]],
                    "function_ids": requirement.get("function_refs", []),
                    "atomic_ids": requirement.get("atomic_refs", []),
                    "source_refs": refs,
                    "affected_test_dimensions": ["functional"]
                    if atomic_id
                    else ["field_validation"],
                    "evidence": conflict.get("summary"),
                    "question": "冲突两侧哪个值是正式验收口径？",
                    "recommendation": "由需求负责人明确唯一规则并同步正文、原型和导出模板。",
                }
            )
            by_requirement.setdefault(requirement["requirement_id"], []).append(
                finding_id
            )

    finding_by_id = {item["finding_id"]: item for item in findings}
    for assessment in review.get("requirement_assessments", []):
        ids = [
            finding_id
            for finding_id in by_requirement.get(assessment.get("requirement_id"), [])
            if DIMENSION_BY_CODE[finding_by_id[finding_id]["code"]]
            == assessment.get("dimension")
        ]
        if ids:
            assessment["status"] = "FINDING"
            assessment["rationale"] = "图谱中的显式缺口已形成待修复 finding"
            assessment["finding_ids"] = ids
    for assessment in review.get("assessments", []):
        ids = [
            item["finding_id"]
            for item in findings
            if DIMENSION_BY_CODE[item["code"]] == assessment.get("dimension")
        ]
        if ids:
            assessment["status"] = "FINDING"
            assessment["rationale"] = f"该维度存在 {len(ids)} 个已确认问题"
            assessment["finding_ids"] = ids
    review["findings"] = findings
    review["meta"]["lifecycle_status"] = "BLOCKED"
    review["audit"] = {
        "verdict": "REJECT",
        "downstream_eligible": False,
        "errors": [
            f"存在 {sum(item['severity'] == 'REJECT' for item in findings)} 个阻断 finding"
        ],
        "warnings": ["歧义、一致性、非功能可度量性及未映射来源单元仍需继续评审"],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
