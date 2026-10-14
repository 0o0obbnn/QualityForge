#!/usr/bin/env python3
"""Detect intra-document conflicts from structured artifacts and typographic patterns.

Detectors are data-driven: they compare entities already extracted by the
mapping (business field enums) and typographic definition patterns in the
source (ordinal anchors, metric numeric values). No domain vocabulary is
encoded here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def stable_id(prefix: str, *parts: Any) -> str:
    value = "|".join(" ".join(str(part or "").split()).casefold() for part in parts)
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:12].upper()}"


def plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip(" *_`　")


def norm_value(value: str) -> str:
    return re.sub(r"[\s　]", "", width_fold(value))


def width_fold(value: str) -> str:
    return value.translate(str.maketrans("０１２３４５６７８９～（）", "0123456789~()"))


METRIC_UNIT = r"%|ms|s|秒|分钟|分|小时|天|日|万|亿|笔|次|条|MB|GB|KB|个|位"
NUMERIC_WITH_UNIT = re.compile(rf"([≤≥<>=]?)\s*(\d+(?:\.\d+)?)\s*({METRIC_UNIT})")
ABBR = re.compile(r"\b([A-Z]{2,6})\b")
NAME_KEY = re.compile(r"([^，。；:：\s]{2,14})\s*[：:]")
ORDINAL_ANCHOR = re.compile(r"第[0-9０-９]+(?:[～~\-至][0-9０-９]+)?位")
NAME_KEY_STOPWORDS = {"格式", "示例", "其中", "备注", "说明", "注意", "规则", "描述"}


def first_evidence(item: dict[str, Any]) -> tuple[str, str]:
    evidence = item.get("evidence") or []
    if evidence and isinstance(evidence[0], dict):
        return str(evidence[0].get("locator", "")), str(
            evidence[0].get("quote", "")[:60]
        )
    return "", ""


def detect_field_enum_conflicts(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for field in mapping.get("business_fields", []):
        if not isinstance(field, dict):
            continue
        values = field.get("enum_values")
        if field.get("business_name") and isinstance(values, list) and values:
            groups.setdefault(str(field["business_name"]), []).append(field)
    conflicts = []
    for name, fields in sorted(groups.items()):
        if len(fields) < 2:
            continue
        distinct: list[set[str]] = []
        for field in fields:
            values = set(map(str, field["enum_values"]))
            if values not in distinct:
                distinct.append(values)
        if len(distinct) < 2:
            continue
        pairs = []
        seen_values: set[str] = set()
        for field in fields:
            joined = "、".join(map(str, field["enum_values"]))
            if joined in seen_values:
                continue
            seen_values.add(joined)
            locator, quote = first_evidence(field)
            pairs.append({"locator": locator, "quote": quote, "value": joined})
        conflicts.append(
            {
                "kind": "field_enum",
                "key": name,
                "summary": f"字段「{name}」存在多处枚举定义且集合不一致",
                "pairs": pairs[:3],
                "affected_test_dimensions": ["field_validation"],
            }
        )
    return conflicts


def detect_anchor_definition_conflicts(lines: list[str]) -> list[dict[str, Any]]:
    anchors: dict[str, list[dict[str, str]]] = {}
    for line_no, raw in enumerate(lines, 1):
        line = plain_text(raw)
        for match in ORDINAL_ANCHOR.finditer(width_fold(line)):
            anchor = match.group(0)
            start = match.start()
            tail = line[start : start + 60]
            tail = re.split(r"[。；]", tail)[0]
            anchors.setdefault(anchor, []).append(
                {
                    "locator": f"L{line_no}",
                    "quote": line[max(0, start - 12) : start + 40],
                    "value": norm_value(tail),
                }
            )
    conflicts = []
    for anchor, occurrences in sorted(anchors.items()):
        values = {item["value"] for item in occurrences}
        if len(occurrences) < 2 or len(values) < 2:
            continue
        conflicts.append(
            {
                "kind": "anchor_definition",
                "key": anchor,
                "summary": f"锚点「{anchor}」存在多处定义且口径不一致",
                "pairs": [
                    {
                        "locator": item["locator"],
                        "quote": item["quote"],
                        "value": item["value"],
                    }
                    for item in occurrences[:3]
                ],
                "affected_test_dimensions": ["functional", "field_validation"],
            }
        )
    return conflicts


def detect_metric_value_conflicts(lines: list[str]) -> list[dict[str, Any]]:
    metrics: dict[str, list[dict[str, str]]] = {}
    for line_no, raw in enumerate(lines, 1):
        line = plain_text(raw)
        folded = width_fold(line)
        for match in NUMERIC_WITH_UNIT.finditer(folded):
            window = folded[max(0, match.start() - 24) : match.start()]
            keys = ABBR.findall(window)
            name_match = NAME_KEY.search(window)
            if (
                not keys
                and name_match
                and name_match.group(1) not in NAME_KEY_STOPWORDS
            ):
                keys = [name_match.group(1)]
            value = f"{match.group(1)}{match.group(2)}{match.group(3)}"
            for key in keys:
                metrics.setdefault(key, []).append(
                    {
                        "locator": f"L{line_no}",
                        "quote": line.strip()[:80],
                        "value": norm_value(value),
                    }
                )
    conflicts = []
    for key, occurrences in sorted(metrics.items()):
        values = {item["value"] for item in occurrences}
        if len(occurrences) < 2 or len(values) < 2:
            continue
        locators = {item["locator"] for item in occurrences}
        if len(locators) < 2:
            continue
        conflicts.append(
            {
                "kind": "metric_value",
                "key": key,
                "summary": f"指标「{key}」在文中存在多个不同数值口径",
                "pairs": [
                    {
                        "locator": item["locator"],
                        "quote": item["quote"],
                        "value": item["value"],
                    }
                    for item in occurrences[:3]
                ],
                "affected_test_dimensions": ["nfr"],
            }
        )
    return conflicts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect intra-document structural conflicts"
    )
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    review = json.loads(args.review.read_text(encoding="utf-8"))
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    lines = args.source.read_text(encoding="utf-8").splitlines()

    conflicts = [
        *detect_field_enum_conflicts(mapping),
        *detect_anchor_definition_conflicts(lines),
        *detect_metric_value_conflicts(lines),
    ]

    findings = list(review.get("findings", []))
    new_ids: dict[str, list[str]] = {}
    new_ids_by_requirement: dict[str, list[str]] = {}
    source_ids = [str(item) for item in review.get("source_ids", [])]
    primary_source = source_ids[0] if source_ids else "SRC-001"
    requirements = [
        item
        for item in review.get("requirements", [])
        if isinstance(item, dict) and item.get("source_refs")
    ]
    requirements_by_line: list[tuple[int, str]] = []
    for requirement in requirements:
        for ref in requirement["source_refs"]:
            locator_match = re.fullmatch(r"L(\d+)", str(ref.get("locator", "")))
            if locator_match:
                requirements_by_line.append(
                    (int(locator_match.group(1)), requirement["requirement_id"])
                )

    def nearest_requirements(pairs: list[dict[str, Any]]) -> list[str]:
        linked: list[str] = []
        for pair in pairs:
            locator_match = re.fullmatch(r"L(\d+)", str(pair.get("locator", "")))
            if not locator_match:
                continue
            line_no = int(locator_match.group(1))
            candidates = [
                rid for req_line, rid in requirements_by_line if req_line <= line_no
            ]
            if candidates:
                linked.append(candidates[-1])
        return sorted(set(linked))

    for conflict in conflicts:
        finding_id = stable_id(
            "RQF", "INTRA_DOCUMENT_CONFLICT", conflict["kind"], conflict["key"]
        )
        requirement_ids = nearest_requirements(conflict["pairs"])
        findings.append(
            {
                "finding_id": finding_id,
                "code": "INTRA_DOCUMENT_CONFLICT",
                "severity": "REJECT",
                "certainty": "risk",
                "origin": "deterministic_candidate",
                "evidence_type": "CONFLICT",
                "requirement_ids": requirement_ids,
                "function_ids": [],
                "atomic_ids": [],
                "affected_test_dimensions": conflict["affected_test_dimensions"],
                "source_refs": [
                    f"{primary_source}:{pair['locator']}"
                    for pair in conflict["pairs"]
                    if pair["locator"]
                ],
                "evidence": "；".join(
                    f"{pair['locator']}：{pair['value']}" for pair in conflict["pairs"]
                ),
                "expected_element": "唯一且一致的正式口径",
                "question": f"{conflict['summary']}，哪一侧是正式验收口径？",
                "recommendation": "由需求负责人裁定唯一口径并同步全部出现位置。",
                "conflict_kind": conflict["kind"],
            }
        )
        new_ids.setdefault("consistency", []).append(finding_id)
        for requirement_id in requirement_ids:
            new_ids_by_requirement.setdefault(requirement_id, []).append(finding_id)

    finding_by_id = {item["finding_id"]: item for item in findings}
    for assessment in review.get("requirement_assessments", []):
        if (
            assessment.get("dimension") != "consistency"
            or assessment.get("status") == "FINDING"
        ):
            continue
        ids = [
            fid
            for fid in new_ids_by_requirement.get(assessment.get("requirement_id"), [])
            if fid in finding_by_id
        ]
        if ids:
            assessment.update(
                status="FINDING",
                rationale="结构化冲突检测发现文内不一致",
                finding_ids=ids,
            )
    for assessment in review.get("assessments", []):
        if assessment.get("dimension") == "consistency" and new_ids.get("consistency"):
            assessment["status"] = "FINDING"
            assessment["rationale"] = (
                f"该维度存在 {len(new_ids['consistency'])} 个文内冲突 finding"
            )
            assessment["finding_ids"] = sorted(
                set(assessment.get("finding_ids", []) + new_ids["consistency"])
            )

    review["findings"] = findings
    rejects = sum(item.get("severity") == "REJECT" for item in findings)
    review["meta"]["lifecycle_status"] = (
        "BLOCKED"
        if rejects
        else review["meta"].get("lifecycle_status", "REVIEW_REQUIRED")
    )
    review["audit"] = {
        "verdict": "REJECT"
        if rejects
        else review.get("audit", {}).get("verdict", "PASS_WITH_REVIEW"),
        "downstream_eligible": False,
        "errors": [f"存在 {rejects} 个阻断 finding"] if rejects else [],
        "warnings": review.get("audit", {}).get("warnings", []),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
