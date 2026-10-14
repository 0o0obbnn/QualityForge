#!/usr/bin/env python3
"""Project requirement-review decisions onto graph nodes without deleting source facts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


DIMENSIONS = ("functional", "field_validation", "sorting", "state_transition", "permission", "integration", "nfr")
REVIEW_TO_TEST_DIMENSIONS = {
    "ambiguity": {"functional", "field_validation", "sorting", "state_transition", "integration"},
    "consistency": {"functional", "field_validation", "sorting", "state_transition", "integration"},
    "testability": {"functional", "field_validation", "sorting", "state_transition", "integration", "nfr"},
    "completeness": {"functional", "state_transition", "integration"},
    "nfr_measurability": {"nfr"},
    "role_permission": {"permission"},
}
PLACEHOLDERS = ("待确认", "对应功能", "相关行为", "具体结果待", "原文触发条件")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    normalized = "|".join(" ".join(str(part or "").split()).casefold() for part in parts)
    return f"{prefix}-{hashlib.sha256(normalized.encode()).hexdigest()[:12].upper()}"


def version_at_least(value: Any, expected: str) -> bool:
    try:
        return tuple(int(part) for part in str(value).split(".")) >= tuple(int(part) for part in expected.split("."))
    except ValueError:
        return False


def finding_open(finding: dict[str, Any]) -> bool:
    return finding.get("lifecycle_status", "OPEN") not in {"RESOLVED", "WITHDRAWN"}


def finding_affects_dimension(
    finding: dict[str, Any], dimension: str, related_assessments: list[dict[str, Any]]
) -> bool:
    """Prefer explicit finding scope; retain legacy assessment mapping as fallback."""
    explicit = finding.get("affected_test_dimensions")
    if isinstance(explicit, list):
        return dimension in explicit
    review_dimensions = {key for key, values in REVIEW_TO_TEST_DIMENSIONS.items() if dimension in values}
    return any(
        assessment.get("dimension") in review_dimensions
        and finding.get("finding_id") in assessment.get("finding_ids", [])
        for assessment in related_assessments
    )


def applicability(atomic: dict[str, Any], bindings: list[dict[str, Any]], relations: list[dict[str, Any]]) -> dict[str, bool]:
    text = " ".join(
        [str(atomic.get("name", "")), str(atomic.get("category", "")), *map(str, atomic.get("processing_rules", []))]
        + [str(rule) for binding in bindings for rule in binding.get("rules", [])]
    ).casefold()
    atomic_id = atomic.get("atomic_id")
    relation_types = {
        relation.get("type") for relation in relations
        if relation.get("source_id") == atomic_id or relation.get("target_id") == atomic_id
    }
    return {
        "functional": True,
        "field_validation": any(binding.get("rules") or "validation" in binding.get("usages", []) for binding in bindings),
        "sorting": any(token in text for token in ("排序", "升序", "降序", "正序", "倒序", "sort", "order by")),
        "state_transition": bool(atomic.get("state_changes")) or "state_flow" in relation_types,
        "permission": atomic.get("category") == "permission" or any(token in text for token in ("权限", "角色", "仅可", "仅能", "禁止", "无权", "暂无权限")),
        "integration": any(token in text for token in ("接口", "api", "服务调用")) or bool(relation_types & {"depends_on", "data_flow"}),
        "nfr": any(token in text for token in ("性能", "并发", "响应时间", "吞吐", "可用性", "安全性")),
    }


def project_atomic(atomic: dict[str, Any], bindings: list[dict[str, Any]], relations: list[dict[str, Any]],
                   requirements: list[dict[str, Any]], assessments: list[dict[str, Any]],
    findings: list[dict[str, Any]]) -> dict[str, Any]:
    atomic_id = atomic.get("atomic_id")
    linked_atomic_ids = {atomic_id}
    if atomic.get("inherited_from_atomic_id"):
        linked_atomic_ids.add(atomic.get("inherited_from_atomic_id"))
    req_ids = {item.get("requirement_id") for item in requirements if linked_atomic_ids.intersection(item.get("atomic_refs", []))}
    req_assessments = [item for item in assessments if item.get("requirement_id") in req_ids]
    req_findings = [item for item in findings if finding_open(item) and (
        linked_atomic_ids.intersection(item.get("atomic_ids", [])) or req_ids.intersection(item.get("requirement_ids", []))
    )]
    applicable = applicability(atomic, bindings, relations)
    gates: dict[str, dict[str, Any]] = {}
    for dimension in DIMENSIONS:
        review_dimensions = {key for key, values in REVIEW_TO_TEST_DIMENSIONS.items() if dimension in values}
        related_assessments = [item for item in req_assessments if item.get("dimension") in review_dimensions]
        related_findings = [
            item for item in req_findings
            if finding_affects_dimension(item, dimension, related_assessments)
        ]
        # A precisely scoped finding is itself evidence that the dimension applies.
        # This matters for gaps such as "a validation rule is missing": the graph
        # cannot infer applicability from a rule that is absent by definition.
        if not applicable[dimension] and not related_findings:
            gates[dimension] = {"status": "NOT_APPLICABLE", "reasons": [], "finding_ids": []}
            continue
        reasons: list[str] = []
        hard_block = False
        if not related_assessments or any(item.get("status") == "NOT_REVIEWED" for item in related_assessments):
            reasons.append("相关需求质量维度尚未完成评审")
        if any(item.get("severity") == "REJECT" for item in related_findings):
            reasons.append("存在未解决的 REJECT finding")
            hard_block = True
        elif related_findings:
            reasons.append("存在未解决的评审问题")

        if dimension == "functional":
            if not atomic.get("evidence"):
                reasons.append("最小功能缺少来源证据")
                hard_block = True
            if not (atomic.get("outputs") or atomic.get("state_changes") or atomic.get("branches")):
                reasons.append("最小功能缺少可观察结果")
                hard_block = True
            if any(token in str(atomic.get("action", "")) + str(atomic.get("trigger", "")) for token in PLACEHOLDERS):
                reasons.append("动作或触发仍包含占位描述")
                hard_block = True
        elif dimension == "field_validation" and not any(binding.get("rules") and binding.get("evidence") for binding in bindings):
            reasons.append("字段校验规则缺少规则或证据")
            hard_block = True
        elif dimension == "permission" and (
            not atomic.get("actor") or any(token in str(atomic.get("actor")) for token in PLACEHOLDERS)
        ):
            reasons.append("执行角色或权限边界未确认")
            hard_block = True

        status = "BLOCKED" if hard_block else ("REVIEW_REQUIRED" if reasons else "READY")
        gates[dimension] = {
            "status": status,
            "reasons": list(dict.fromkeys(reasons)),
            "finding_ids": sorted({item.get("finding_id") for item in related_findings if item.get("finding_id")}),
        }
    return {
        "review_requirement_ids": sorted(value for value in req_ids if value),
        "open_finding_ids": sorted({item.get("finding_id") for item in req_findings if item.get("finding_id")}),
        "dimension_eligibility": gates,
    }


def project_nfr(requirement: dict[str, Any], assessments: list[dict[str, Any]], findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Project a non-functional requirement without fabricating graph functions."""
    requirement_id = requirement.get("requirement_id")
    related_assessments = [item for item in assessments if item.get("requirement_id") == requirement_id]
    related_findings = [item for item in findings if finding_open(item) and requirement_id in item.get("requirement_ids", [])]
    relevant_dimensions = {"ambiguity", "consistency", "testability", "completeness", "nfr_measurability"}
    relevant = [item for item in related_assessments if item.get("dimension") in relevant_dimensions and item.get("status") != "NOT_APPLICABLE"]
    reasons: list[str] = []
    hard = False
    if not relevant or any(item.get("status") == "NOT_REVIEWED" for item in relevant):
        reasons.append("非功能需求仍有相关质量维度未完成评审")
        hard = True
    if any(item.get("severity") == "REJECT" and finding_affects_dimension(item, "nfr", relevant) for item in related_findings):
        reasons.append("存在影响非功能测试的 REJECT finding")
        hard = True
    elif any(finding_affects_dimension(item, "nfr", relevant) for item in related_findings):
        reasons.append("存在影响非功能测试的 REVIEW finding")
    status = "BLOCKED" if hard else ("REVIEW_REQUIRED" if reasons else "READY")
    gates = {
        dimension: ({"status": status, "reasons": reasons, "finding_ids": sorted({item.get("finding_id") for item in related_findings if finding_affects_dimension(item, "nfr", relevant)})}
                    if dimension == "nfr" else {"status": "NOT_APPLICABLE", "reasons": [], "finding_ids": []})
        for dimension in DIMENSIONS
    }
    return {
        **requirement,
        "quality_review": {
            "review_requirement_ids": [requirement_id],
            "open_finding_ids": sorted({item.get("finding_id") for item in related_findings if item.get("finding_id")}),
            "dimension_eligibility": gates,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply requirement-review status to requirement graph nodes")
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    review = json.loads(args.review.read_text(encoding="utf-8"))
    atomic_ids = {item.get("atomic_id") for item in mapping.get("atomic_functions", []) if isinstance(item, dict)}
    dangling = sorted({ref for item in review.get("requirements", []) for ref in item.get("atomic_refs", []) if ref not in atomic_ids})
    if dangling:
        raise SystemExit(f"review references unknown atomic ids: {', '.join(dangling)}")
    mapping_hash, review_hash = sha256(args.mapping), sha256(args.review)
    bindings_by_atomic: dict[str, list[dict[str, Any]]] = {}
    for binding in mapping.get("field_bindings", []):
        bindings_by_atomic.setdefault(binding.get("atomic_id"), []).append(binding)
    for atomic in mapping.get("atomic_functions", []):
        atomic["quality_review"] = project_atomic(
            atomic, bindings_by_atomic.get(atomic.get("atomic_id"), []), mapping.get("relations", []),
            review.get("requirements", []), review.get("requirement_assessments", []), review.get("findings", []),
        )
    mapping["non_functional_requirements"] = [
        project_nfr(requirement, review.get("requirement_assessments", []), review.get("findings", []))
        for requirement in review.get("requirements", [])
        if requirement.get("requirement_type") == "non_functional"
    ]
    reviewable_nodes = [*mapping.get("atomic_functions", []), *mapping["non_functional_requirements"]]
    statuses = [gate["status"] for node in reviewable_nodes
                for gate in node.get("quality_review", {}).get("dimension_eligibility", {}).values()]
    current_schema = str(mapping.setdefault("meta", {}).get("schema_version", "1.2"))
    typed_graph = version_at_least(current_schema, "1.4")
    mapping["meta"]["schema_version"] = "1.4" if typed_graph else "1.3"
    mapping["meta"]["artifact_kind"] = "review_projected_typed_graph" if typed_graph else "review_projected_mapping"
    mapping["meta"]["parent_graph_snapshot_id"] = mapping.get("meta", {}).get("graph_snapshot_id")
    mapping["meta"]["graph_snapshot_id"] = stable_id("GRAPH", mapping_hash, review_hash)
    mapping["review_projection"] = {
        "review_id": review.get("review_id"), "mapping_sha256": mapping_hash, "review_sha256": review_hash,
        "review_lifecycle_status": review.get("meta", {}).get("lifecycle_status"),
        "review_verdict": review.get("audit", {}).get("verdict"),
        "review_downstream_eligible": review.get("audit", {}).get("downstream_eligible", False),
        "not_reviewed_assessment_count": sum(
            item.get("status") == "NOT_REVIEWED" for item in review.get("requirement_assessments", [])
        ),
        "status_counts": {status: statuses.count(status) for status in ("READY", "REVIEW_REQUIRED", "BLOCKED", "NOT_APPLICABLE")},
        "policy": "only READY dimensions may be compiled for formal test design",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
