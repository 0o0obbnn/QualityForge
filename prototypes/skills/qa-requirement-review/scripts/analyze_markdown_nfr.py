#!/usr/bin/env python3
"""Apply conservative, source-backed checks to Markdown NFR sections."""

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze Markdown non-functional requirements"
    )
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    review = json.loads(args.review.read_text(encoding="utf-8"))
    args.source.read_text(encoding="utf-8")
    findings = list(review.get("findings", []))
    new_by_requirement: dict[str, list[str]] = {}

    nfr_requirements = [
        item
        for item in review.get("requirements", [])
        if item.get("requirement_type") == "non_functional"
        or not item.get("atomic_refs")
    ]

    def add(
        req: dict[str, Any],
        code: str,
        severity: str,
        evidence_type: str,
        quote: str,
        expected: str,
        question: str,
        evidence_line: int | None = None,
    ) -> None:
        source_id = req["source_refs"][0]["source_id"]
        locator = (
            f"L{evidence_line}" if evidence_line else req["source_refs"][0]["locator"]
        )
        finding_id = stable_id("RQF", req["requirement_id"], code, expected)
        item = {
            "finding_id": finding_id,
            "code": code,
            "severity": severity,
            "certainty": "risk",
            "origin": "deterministic_candidate",
            "evidence_type": evidence_type,
            "requirement_ids": [req["requirement_id"]],
            "function_ids": [],
            "atomic_ids": [],
            "affected_test_dimensions": ["nfr"],
            "source_refs": [f"{source_id}:{locator}"],
            "evidence": quote,
            "question": question,
            "recommendation": f"补充{expected}并将其纳入验收测试。",
        }
        if evidence_type == "ABSENCE":
            item["inspected_scope"] = [f"{source_id}:{locator}"]
            item["expected_element"] = expected
        findings.append(item)
        new_by_requirement.setdefault(req["requirement_id"], []).append(finding_id)

    vague = re.compile(
        r"主流|良好|定期|关键角色|稳定响应|高强度|高并发|大数据量|业务连续性|用户体验|开放性|可移植性|平滑|无缝|实时监测|未来"
    )
    for req in nfr_requirements:
        locator = req.get("source_refs", [{}])[0].get("locator", "")
        locator_match = re.fullmatch(r"L(\d+)", locator)
        start = int(locator_match.group(1)) if locator_match else 1
        text = str(
            req.get("summary") or req.get("source_refs", [{}])[0].get("quote") or ""
        )
        vague_terms = sorted(set(vague.findall(text)))
        if vague_terms:
            add(
                req,
                "AMBIGUOUS_LANGUAGE",
                "REVIEW",
                "QUOTE",
                text,
                "可判定的术语定义、适用范围和阈值",
                f"L{start} 定性词「{'、'.join(vague_terms)}」分别如何量化，适用于哪些对象与环境？",
                start,
            )
        if re.search(r"响应时间|可用性", text) and not re.search(
            r"P9[059]|百分位|统计窗口|测量周期", text
        ):
            add(
                req,
                "UNMEASURABLE_NFR",
                "REJECT",
                "ABSENCE",
                f"已检查独立指标：{text}；没有找到百分位或统计窗口",
                "响应时间百分位、统计窗口、负载模型和测量环境",
                f"L{start} 性能与可用性指标按什么统计窗口、负载和百分位验收？",
                start,
            )
        if "MD5加密" in text:
            add(
                req,
                "INCOMPLETE_REQUIREMENT",
                "REVIEW",
                "QUOTE",
                text,
                "密码学用途、算法组合、密钥管理和适用数据范围",
                "MD5在此处用于完整性摘要还是加密？传输与存储分别采用什么机制？",
                start,
            )
        if re.search(
            r"登录失败次数限制|长度、复杂度限制|超时自动销毁", text
        ) and not re.search(
            r"失败\D{0,8}\d+\s*次|长度\D{0,8}\d+|超时\D{0,8}\d+\s*(?:秒|分钟|小时)",
            text,
        ):
            add(
                req,
                "UNMEASURABLE_NFR",
                "REJECT",
                "ABSENCE",
                f"已检查安全约束：{text}；没有找到完整阈值",
                "次数、长度、复杂度或超时的可验收阈值",
                f"L{start} 该安全约束的具体阈值和触发后的处置时长是什么？",
                start,
            )
        if re.search(r"主流现代浏览器", text) and not re.search(
            r"最近\s*\d+\s*个版本|版本矩阵|最低版本", text
        ):
            add(
                req,
                "INCOMPLETE_REQUIREMENT",
                "REVIEW",
                "ABSENCE",
                f"已检查独立兼容性条目：{text}；没有找到版本范围",
                "浏览器与操作系统版本兼容矩阵",
                "每种浏览器支持哪些版本和操作系统组合？",
                start,
            )

    finding_by_id = {item["finding_id"]: item for item in findings}
    dimension_by_code = {
        "AMBIGUOUS_LANGUAGE": "ambiguity",
        "UNMEASURABLE_NFR": "nfr_measurability",
        "INCOMPLETE_REQUIREMENT": "completeness",
    }
    for assessment in review.get("requirement_assessments", []):
        ids = [
            fid
            for fid in new_by_requirement.get(assessment.get("requirement_id"), [])
            if dimension_by_code[finding_by_id[fid]["code"]]
            == assessment.get("dimension")
        ]
        if ids:
            assessment.update(
                status="FINDING",
                rationale="非功能需求文本存在可核验的度量或定义缺口",
                finding_ids=ids,
            )
    for assessment in review.get("assessments", []):
        ids = [
            item["finding_id"]
            for item in findings
            if dimension_by_code.get(item["code"]) == assessment.get("dimension")
        ]
        if ids:
            assessment.update(
                status="FINDING",
                rationale=f"该维度存在 {len(ids)} 个 finding",
                finding_ids=ids,
            )
    review["findings"] = findings
    rejects = sum(item.get("severity") == "REJECT" for item in findings)
    review["meta"]["lifecycle_status"] = "BLOCKED" if rejects else "REVIEW_REQUIRED"
    remaining_assessments = sum(
        item.get("status") == "NOT_REVIEWED"
        for item in review.get("requirement_assessments", [])
    )
    relevant_units = {
        item.get("unit_id"): item
        for item in review.get("source_units", [])
        if isinstance(item, dict) and item.get("relevant") is True and item.get("unit_id")
    }
    dispositions = {
        item.get("unit_id"): item
        for item in review.get("source_unit_dispositions", [])
        if isinstance(item, dict) and item.get("unit_id") in relevant_units
    }
    unresolved_unit_ids = {
        unit_id
        for unit_id, unit in relevant_units.items()
        if unit.get("status") in {"review_required", "unavailable", "skipped"}
    }
    unresolved_unit_ids.update(relevant_units.keys() - dispositions.keys())
    unresolved_unit_ids.update(
        unit_id
        for unit_id, item in dispositions.items()
        if item.get("disposition") in {"unavailable", "review_required"}
    )
    unresolved_units = len(unresolved_unit_ids)
    warnings = []
    if remaining_assessments:
        warnings.append(f"仍有 {remaining_assessments} 个逐需求维度未完成语义评审")
    if unresolved_units:
        warnings.append(f"仍有 {unresolved_units} 个来源单元未完成处置或不可用")
    review["audit"] = {
        "verdict": "REJECT" if rejects else "PASS_WITH_REVIEW",
        "downstream_eligible": False,
        "errors": [f"存在 {rejects} 个阻断 finding"] if rejects else [],
        "warnings": warnings,
    }
    args.out.write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
