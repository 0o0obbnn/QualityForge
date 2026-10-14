#!/usr/bin/env python3
"""Build a complete, explicitly unreviewed QA work queue from a mapping artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DIMENSIONS = ("ambiguity", "consistency", "testability", "completeness", "nfr_measurability", "role_permission")


def stable_id(prefix: str, *parts: Any) -> str:
    normalized = "|".join(" ".join(str(part).split()).casefold() for part in parts)
    return f"{prefix}-{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:10].upper()}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a QA review draft from a requirement mapping")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--source-version", default="unknown")
    args = parser.parse_args()

    source_bytes = args.source.read_bytes()
    source_text = source_bytes.decode("utf-8")
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    if not isinstance(mapping, dict):
        raise ValueError("mapping root must be an object")
    sources = mapping.get("sources") if isinstance(mapping.get("sources"), list) else []
    if not sources:
        source_id = stable_id("SRC", args.source.name, hashlib.sha256(source_bytes).hexdigest())
        sources = [{"source_id":source_id,"file":args.source.name,"type":"requirement","version":args.source_version,"sha256":hashlib.sha256(source_bytes).hexdigest(),"authority":1}]
    else:
        sources = [dict(item) for item in sources]
        for source in sources:
            source.setdefault("version", args.source_version)
            source.setdefault("authority", 1)
            if source.get("source_id") == sources[0].get("source_id"):
                source["sha256"] = hashlib.sha256(source_bytes).hexdigest()
                source["file"] = args.source.name
    source_ids = [item["source_id"] for item in sources]
    source_units = [dict(item) for item in mapping.get("source_units", []) if isinstance(item, dict)]
    for unit in source_units:
        if unit.get("kind") == "section" and str(unit.get("reason", "")).startswith("超出功能点图谱范围：非功能需求"):
            unit["relevant"] = True
            unit["status"] = "review_required"
            unit["reason"] = "非功能需求属于质量评审范围，等待可度量性与可测试性评审"

    bindings_by_atomic: dict[str, list[str]] = {}
    for binding in mapping.get("field_bindings", []):
        if isinstance(binding, dict):
            bindings_by_atomic.setdefault(binding.get("atomic_id"), []).append(binding.get("field_id"))
    field_evidence = {
        item.get("field_id"): item.get("evidence", [])
        for item in mapping.get("business_fields", []) if isinstance(item, dict)
    }
    requirements = []
    per_requirement = []
    for atomic in mapping.get("atomic_functions", []):
        if not isinstance(atomic, dict) or not atomic.get("atomic_id"):
            continue
        requirement_id = stable_id("REQ", atomic.get("function_id"), atomic.get("name"), atomic.get("action"))
        evidence = list(atomic.get("evidence")) if isinstance(atomic.get("evidence"), list) else []
        for field_id in bindings_by_atomic.get(atomic["atomic_id"], []):
            for proof in field_evidence.get(field_id, []):
                if isinstance(proof, dict) and proof not in evidence:
                    evidence.append(proof)
        requirements.append({
            "requirement_id": requirement_id,
            "title": atomic.get("name") or atomic["atomic_id"],
            "summary": atomic.get("action") or atomic.get("name") or "待评审",
            "function_refs": [atomic.get("function_id")] if atomic.get("function_id") else [],
            "atomic_refs": [atomic["atomic_id"]],
            "field_refs": sorted({value for value in bindings_by_atomic.get(atomic["atomic_id"], []) if value}),
            "rule_refs": [],
            "source_refs": evidence,
        })
        for dimension in DIMENSIONS:
            per_requirement.append({
                "assessment_id": stable_id("ASM", requirement_id, dimension),
                "requirement_id": requirement_id,
                "dimension": dimension,
                "status": "NOT_REVIEWED",
                "rationale": "评审工作队列已建立，尚未完成语义判断",
                "finding_ids": [],
            })

    # The function graph intentionally excludes NFRs, but the QA review must
    # not. A section title is only a container: create one requirement for each
    # independently reviewable criterion so one clear metric cannot hide a
    # vague neighbour in the same section.
    in_nfr = False
    nfr_section = None
    nfr_group = None
    nfr_items: list[tuple[int, str, str, str | None]] = []
    primary_source_id = source_ids[0]
    source_lines = source_text.splitlines()
    for line_no, raw_line in enumerate(source_lines, 1):
        line = raw_line.strip()
        heading = re.match(r"^(#{1,2})\s+(.+)$", line)
        if heading:
            level, title = len(heading.group(1)), heading.group(2).strip(" *")
            if level == 1:
                in_nfr = title in {"非功能需求", "非功能性需求", "质量属性"}
                nfr_section = None
                nfr_group = None
            elif level == 2 and in_nfr:
                nfr_section = title
                nfr_group = None
            continue
        if not in_nfr or not nfr_section or not line:
            continue
        group_match = re.fullmatch(r"\*\*\s*\d+[、.)）]\s*(.+?)\s*\*\*", line)
        plain_group_match = re.fullmatch(r"\d+[、.)）]\s*([^。；;]{1,40})", line)
        if group_match or plain_group_match:
            nfr_group = (group_match or plain_group_match).group(1).strip()
            continue
        criterion = re.sub(r"^-\s+", "", line).strip()
        criterion = re.sub(r"\*\*", "", criterion).strip()
        if not criterion or line.startswith(("<", "|", "![](")):
            continue
        # Bullets are explicit criteria. Standalone prose is retained only
        # when it carries normative or observable content, including compact
        # security statements that omit an explicit modal verb.
        is_bullet = bool(re.match(r"^-\s+", line))
        is_normative = bool(re.search(
            r"应|必须|不得|支持|采用|提供|限制|防止|确保|保证|保留|隔离|加密|认证|校验|监测|备份|恢复|部署|对接|响应|可用性|成功率|RTO|RPO|≤|≥|不低于|不超过",
            criterion,
        ))
        if is_bullet or is_normative:
            nfr_items.append((line_no, nfr_section, criterion, nfr_group))

    for line_no, section, criterion, group in nfr_items:
        requirement_id = stable_id("REQ", primary_source_id, "nfr", section, group or "", criterion)
        title = f"{section} / {group} / {criterion}" if group else f"{section} / {criterion}"
        requirements.append({
            "requirement_id": requirement_id, "title": title, "summary": criterion,
            "function_refs": [], "atomic_refs": [], "field_refs": [], "rule_refs": [],
            "source_refs": [{"source_id": primary_source_id, "locator": f"L{line_no}", "quote": criterion}],
            "requirement_type": "non_functional", "quality_attribute": section,
        })
        for dimension in DIMENSIONS:
            per_requirement.append({"assessment_id": stable_id("ASM", requirement_id, dimension), "requirement_id": requirement_id, "dimension": dimension, "status": "NOT_REVIEWED", "rationale": "非功能需求语义评审尚未完成", "finding_ids": []})

    requirement_refs_by_locator: dict[tuple[str, str], list[str]] = {}
    for requirement in requirements:
        for ref in requirement.get("source_refs", []):
            if isinstance(ref, dict):
                requirement_refs_by_locator.setdefault((ref.get("source_id"), ref.get("locator")), []).append(requirement["requirement_id"])
    requirements_by_function: dict[str, list[dict[str, Any]]] = {}
    requirements_by_atomic: dict[str, dict[str, Any]] = {}
    for requirement in requirements:
        for function_id in requirement.get("function_refs", []):
            requirements_by_function.setdefault(function_id, []).append(requirement)
        for atomic_id in requirement.get("atomic_refs", []):
            requirements_by_atomic[atomic_id] = requirement
    imported_findings = []
    finding_ids_by_unit: dict[str, list[str]] = {}
    for source_unit in source_units:
        for finding_id in source_unit.get("finding_ids", []):
            finding_ids_by_unit.setdefault(finding_id, []).append(source_unit.get("unit_id"))
    source_review_findings = {
        item.get("finding_id"): item for item in mapping.get("source_dependency_review", {}).get("findings", [])
        if isinstance(item, dict) and item.get("finding_id")
    }
    by_requirement_finding: dict[str, list[str]] = {}
    for finding_id, unit_ids in finding_ids_by_unit.items():
        source_finding = source_review_findings.get(finding_id)
        affected_units = [item for item in source_units if item.get("unit_id") in unit_ids]
        affected_functions = sorted({item.get("blocking_scope", {}).get("function_id") for item in affected_units if item.get("blocking_scope", {}).get("function_id")})
        affected_requirements_by_id: dict[str, dict[str, Any]] = {}
        for unit in affected_units:
            scoped_atomic_ids = unit.get("blocking_scope", {}).get("atomic_ids", [])
            scoped = [requirements_by_atomic[atomic_id] for atomic_id in scoped_atomic_ids if atomic_id in requirements_by_atomic]
            if not scoped:
                scoped = requirements_by_function.get(unit.get("blocking_scope", {}).get("function_id"), [])
            for requirement in scoped:
                affected_requirements_by_id[requirement["requirement_id"]] = requirement
        affected_requirements = list(affected_requirements_by_id.values())
        if source_finding is None or not affected_requirements:
            continue
        requirement_ids_for_finding = sorted(item["requirement_id"] for item in affected_requirements)
        atomic_ids_for_finding = sorted({atomic_id for item in affected_requirements for atomic_id in item.get("atomic_refs", [])})
        refs = [f"{item.get('source_id')}:{item.get('locator')}" for item in affected_units]
        imported = {
            **source_finding,
            "requirement_ids": requirement_ids_for_finding,
            "function_ids": affected_functions,
            "atomic_ids": atomic_ids_for_finding,
            "source_refs": refs,
            "inspected_scope": source_finding.get("inspected_scope") or refs,
        }
        imported_findings.append(imported)
        for requirement_id in requirement_ids_for_finding:
            by_requirement_finding.setdefault(requirement_id, []).append(finding_id)
    for assessment in per_requirement:
        finding_ids = by_requirement_finding.get(assessment["requirement_id"], [])
        if finding_ids and assessment["dimension"] == "completeness":
            assessment.update(status="FINDING", rationale="资料依赖评审发现受影响范围内存在未解决依赖", finding_ids=finding_ids)
    unit_dispositions = []
    for unit in source_units:
        if not unit.get("relevant"):
            continue
        requirement_refs = list(requirement_refs_by_locator.get((unit.get("source_id"), unit.get("locator")), []))
        # Section units cover a source range; requirements inside that range
        # must count as dispositions even when their evidence uses an exact
        # line locator rather than the section heading locator.
        if unit.get("kind") == "section" and isinstance(unit.get("line_start"), int) and isinstance(unit.get("line_end"), int):
            for requirement in requirements:
                for ref in requirement.get("source_refs", []):
                    if not isinstance(ref, dict):
                        continue
                    locator_match = re.fullmatch(r"L(\d+)", str(ref.get("locator", "")))
                    if ref.get("source_id") == unit.get("source_id") and locator_match and unit["line_start"] <= int(locator_match.group(1)) <= unit["line_end"]:
                        requirement_refs.append(requirement["requirement_id"])
        unit_finding_ids = unit.get("finding_ids", [])
        finding_requirement_ids = sorted({req_id for finding_id in unit_finding_ids for req_id in next((item["requirement_ids"] for item in imported_findings if item["finding_id"] == finding_id), [])})
        if unit_finding_ids:
            disposition, reason = "finding", "资料依赖评审 Finding 已绑定到受影响需求"
            requirement_refs = finding_requirement_ids
        elif unit.get("status") == "unavailable":
            disposition, reason = "unavailable", unit.get("reason") or "来源单元不可用"
        elif requirement_refs:
            disposition, reason = "requirement", "已关联到候选需求，等待逐需求六维评审"
        elif unit.get("kind") == "reference_dependency" and unit.get("status") == "processed":
            disposition, reason = "no_output", "内部继承或复用已作为图谱关系处理，不重复生成需求条目"
        elif unit.get("kind") == "section" and any(token in str(unit.get("semantic_key", "")) for token in ("功能模块概述", "模块功能描述")):
            disposition, reason = "no_output", "该段为功能背景或范围概述，具体可验收行为由下级需求条目承载"
        elif unit.get("kind") == "section" and isinstance(unit.get("line_start"), int) and isinstance(unit.get("line_end"), int) and any(
            other.get("unit_id") != unit.get("unit_id")
            and other.get("relevant")
            and isinstance(other.get("line_start"), int)
            and unit["line_start"] <= other["line_start"] <= unit["line_end"]
            for other in source_units
        ):
            disposition, reason = "no_output", "该段为结构容器，其可验收内容已由范围内的明细来源单元承载"
        elif unit.get("status") == "review_required":
            disposition, reason = "review_required", unit.get("reason") or "来源单元需要语义评审"
        else:
            disposition, reason = "review_required", "尚未判断该来源单元应形成需求、finding 或无产物结论"
        unit_dispositions.append({"unit_id": unit.get("unit_id"), "disposition": disposition, "requirement_ids": sorted(set(requirement_refs)), "finding_ids": unit_finding_ids, "reason": reason})

    relevant = [unit for unit in source_units if unit.get("relevant")]
    processed = sum(unit.get("status") == "processed" for unit in relevant)
    skipped = sum(unit.get("status") == "skipped" for unit in relevant)
    unavailable = sum(unit.get("status") == "unavailable" for unit in relevant)
    review_required = sum(unit.get("status") == "review_required" for unit in relevant)
    disposition_by_unit = {item["unit_id"]: item for item in unit_dispositions}
    relevant_ids = {unit.get("unit_id") for unit in relevant}
    unresolved_unit_ids = {
        unit.get("unit_id") for unit in relevant
        if unit.get("status") in {"review_required", "unavailable", "skipped"}
    }
    unresolved_unit_ids.update(relevant_ids - disposition_by_unit.keys())
    unresolved_unit_ids.update(
        unit_id for unit_id, item in disposition_by_unit.items()
        if item.get("disposition") in {"unavailable", "review_required"}
    )
    review_id = stable_id("RQR", args.source.name, hashlib.sha256(source_bytes).hexdigest())
    data = {
        "meta": {"schema_version":"1.0","artifact_kind":"requirement_quality_review","review_mode":"full","lifecycle_status":"BLOCKED","generated_at":datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")},
        "review_id": review_id,
        "source_ids": source_ids,
        "sources": sources,
        "source_units": source_units,
        "source_unit_dispositions": unit_dispositions,
        "requirements": requirements,
        "assessments": [{"dimension":dimension,"status":"FINDING" if dimension == "completeness" and imported_findings else "NOT_REVIEWED","rationale":"资料依赖存在未解决 Finding" if dimension == "completeness" and imported_findings else "逐需求语义评审尚未完成","finding_ids":[item["finding_id"] for item in imported_findings] if dimension == "completeness" else []} for dimension in DIMENSIONS],
        "requirement_assessments": per_requirement,
        "findings": imported_findings,
        "test_points": [],
        "coverage": {"requirement_count":len(requirements),"requirement_assessment_count":len(per_requirement),"expected_requirement_assessment_count":len(requirements)*len(DIMENSIONS),"source_unit_disposition_count":len(unit_dispositions),"unresolved_source_unit_count":len(unresolved_unit_ids),"source_coverage":{"claim":"full","relevant_units":len(relevant),"processed_units":processed,"review_required_units":review_required,"skipped_units":skipped,"unavailable_units":unavailable,"uncovered_ranges":[]}},
        "audit": {"verdict":"NOT_RUN","downstream_eligible":False,"errors":["逐需求六维语义评审尚未完成"],"warnings":["这是完整评审工作队列，不是正式评审结论"]},
    }
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
