#!/usr/bin/env python3
"""Review referenced project materials before requirement graph construction."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REFERENCE_TYPES = {
    "internal_reference",
    "external_artifact",
    "existing_baseline",
    "pending_artifact",
}
GENERIC_HEADINGS = {
    "系统功能设计",
    "功能模块概述",
    "模块功能描述",
    "功能描述",
    "网页端",
    "接口端",
    "说明",
}


def stable_id(prefix: str, *parts: Any) -> str:
    value = "|".join(" ".join(str(part or "").split()).casefold() for part in parts)
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:12].upper()}"


def normalize(value: str) -> str:
    return re.sub(r"[\s《》\"'“”]", "", value).casefold()


def plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip(" *_`　")


def looks_like_artifact(value: str) -> bool:
    return bool(
        re.search(
            r"\.(?:xlsx?|csv|docx?|pdf|zip|json|ya?ml)$|附件|模板|标准|规范|文档|说明|清单|字典|权限表|接口",
            value,
            re.IGNORECASE,
        )
    )


def headings_from(lines: list[str]) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    stack: dict[int, str] = {}
    for line_no, line in enumerate(lines, 1):
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if not match:
            continue
        level = len(match.group(1))
        name = match.group(2).strip("* ")
        stack[level] = name
        stack = {key: value for key, value in stack.items() if key <= level}
        headings.append(
            {
                "line": line_no,
                "level": level,
                "name": name,
                "path": [stack[key] for key in sorted(stack)],
            }
        )
    return headings


def owner_before(headings: list[dict[str, Any]], line_no: int) -> dict[str, Any] | None:
    matches = [
        item
        for item in headings
        if item["line"] <= line_no and item["name"] not in GENERIC_HEADINGS
    ]
    return matches[-1] if matches else None


PATH_SEGMENT_LIMIT = 4


def split_reference_path(target: str) -> list[str] | None:
    """排版惯例判据：分隔符路径引用（模块/页面/配置），段名不以数字开头，2~4 段。"""
    segments = [segment.strip() for segment in target.split("/")]
    segments = [segment for segment in segments if segment]
    if not 2 <= len(segments) <= PATH_SEGMENT_LIMIT:
        return None
    if any(segment[0].isdigit() for segment in segments):
        return None
    return segments


def heading_prefix_keys(heading: dict[str, Any]) -> set[str]:
    parts = [part for part in heading["path"] if part not in GENERIC_HEADINGS]
    keys: set[str] = set()
    # 引用路径可能省略上层模块，从任意实义层级起写；为每个起点生成前缀链。
    for start in range(len(parts)):
        for index in range(start + 1, len(parts) + 1):
            keys.add(normalize("/".join(parts[start:index])))
    return keys


def dimensions(reference_type: str, target: str) -> list[str]:
    text = target.casefold()
    if "权限" in text or "角色" in text:
        return ["permission"]
    if "接口" in text:
        return ["integration"]
    if any(token in text for token in ("校验", "标准", "规范", "字典")):
        return ["field_validation", "integration"]
    if "导出" in text or "模板" in text:
        return ["functional", "field_validation", "integration"]
    return (
        ["functional"]
        if reference_type != "internal_reference"
        else ["functional", "integration"]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Review source dependencies before requirement mapping"
    )
    parser.add_argument(
        "--source", required=True, type=Path, help="Primary Markdown requirement"
    )
    parser.add_argument(
        "--provided-source",
        action="append",
        default=[],
        type=Path,
        help="Additional material included in the review; repeatable",
    )
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    missing_inputs = [
        str(path) for path in [args.source, *args.provided_source] if not path.is_file()
    ]
    if missing_inputs:
        raise SystemExit(f"missing review input: {', '.join(missing_inputs)}")
    text = args.source.read_text(encoding="utf-8")
    lines = text.splitlines()
    headings = headings_from(lines)
    heading_names = {normalize(item["name"]) for item in headings}
    named_targets = [
        match.group(1).strip()
        for match in re.finditer(r"《([^》]+)》", text)
        if looks_like_artifact(match.group(1))
    ]
    provided = [
        {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in args.provided_source
    ]
    provided_names = [normalize(path.name) for path in args.provided_source]
    hits: list[dict[str, Any]] = []

    def add(
        line_no: int, quote: str, reference_type: str, target_name: str, **extra: Any
    ) -> None:
        identity = (line_no, reference_type, normalize(target_name), quote)
        if any(item["identity"] == identity for item in hits):
            return
        hits.append(
            {
                "identity": identity,
                "line": line_no,
                "quote": quote,
                "reference_type": reference_type,
                "target_name": target_name.strip(),
                **extra,
            }
        )

    for line_no, raw in enumerate(lines, 1):
        line = plain_text(raw)
        if not line:
            continue
        named = [
            match
            for match in re.finditer(r"《([^》]+)》", line)
            if normalize(match.group(1)) in heading_names
            or looks_like_artifact(match.group(1))
        ]
        for match in named:
            target = match.group(1).strip()
            add(
                line_no,
                match.group(0),
                "internal_reference"
                if normalize(target) in heading_names
                else "external_artifact",
                target,
                location_hint="云盘" if "详见云盘" in line else None,
            )
        if "详见云盘" in line and not named:
            add(
                line_no,
                "详见云盘",
                "external_artifact",
                "云盘中的相关资料",
                location_hint="云盘",
            )
        for match in re.finditer(
            r"详见([^，。；;]{1,20}(?:标准|规范|文档|清单|附件))", line
        ):
            shorthand = match.group(1).strip()
            target = next(
                (
                    item
                    for item in named_targets
                    if normalize(item).endswith(normalize(shorthand))
                ),
                shorthand,
            )
            add(line_no, match.group(0), "external_artifact", target)
        for match in re.finditer(
            r"(?:需|待)(?:补充|提供|交付)([^，。；;]{1,24}(?:文档|规范|清单|附件|说明))",
            line,
        ):
            add(line_no, match.group(0), "pending_artifact", match.group(1).strip())
        for match in re.finditer(
            r"(?:复用|沿用)[^，。；;]{1,50}(?:页面|功能|规则)", line
        ):
            portal = next(
                (
                    token
                    for token in re.split(r"[，。；;的\s]", match.group(0))
                    if token.endswith("端")
                ),
                None,
            )
            target = portal or "文档内同名功能"
            add(line_no, match.group(0), "internal_reference", target)
        for match in re.finditer(
            r"同([^，。；;]{1,12}(?:端|模块|页面|功能|规则))一致",
            line,
        ):
            add(line_no, match.group(0), "internal_reference", match.group(1))
        for match in re.finditer(r"(?:其他)?校验规则同(?:当前|现有)一致", line):
            add(line_no, match.group(0), "existing_baseline", "现行系统校验规则")
        for match in re.finditer(
            r"(?:请求地址、请求参数、响应参数、加密方式等)?均?与历史接口保持一致", line
        ):
            add(line_no, match.group(0), "existing_baseline", "历史接口契约")
        for match in re.finditer(r"其余均?保持不变", line):
            add(line_no, match.group(0), "existing_baseline", "现行功能其余行为")
        for match in re.finditer(r"【([^【】]+)】", line):
            segments = split_reference_path(match.group(1))
            if segments:
                add(line_no, match.group(0), "internal_reference", "/".join(segments))
        for match in re.finditer(r"[\"'“”]([^\"'“”]+)[\"'“”]", line):
            segments = split_reference_path(match.group(1))
            if segments:
                add(line_no, match.group(0), "internal_reference", "/".join(segments))

    occurrences: dict[str, int] = {}
    dependencies: list[dict[str, Any]] = []
    for item in sorted(hits, key=lambda value: value["identity"]):
        ref_type, target, line_no = (
            item["reference_type"],
            item["target_name"],
            item["line"],
        )
        base_key = f"{ref_type}:{normalize(target)}"
        target_locator = None
        unresolved_segment = None
        if ref_type == "internal_reference":
            segments = split_reference_path(target)
            if segments:
                wanted = [
                    normalize("/".join(segments[: index + 1]))
                    for index in range(len(segments))
                ]
                best: dict[str, Any] | None = None
                # 模块路径是全局命名，允许前向引用（后文定义、前文使用）。
                for heading in headings:
                    keys = heading_prefix_keys(heading)
                    depth = max(
                        (
                            index
                            for index in range(len(segments))
                            if wanted[index] in keys
                        ),
                        default=-1,
                    )
                    if depth >= 0 and (best is None or depth >= best["depth"]):
                        best = {"heading": heading, "depth": depth}
                if best and best["depth"] == len(segments) - 1:
                    match = best["heading"]
                else:
                    match = None
                    unresolved_segment = segments[(best["depth"] + 1) if best else 0]
            else:
                owner = owner_before(headings, line_no)
                if len(target) > 1 and target.endswith("端"):
                    direct = [
                        heading
                        for heading in headings
                        if heading["line"] < line_no
                        and heading["name"] == target
                        and owner
                        and owner["name"] in heading["path"]
                    ]
                    same_name = [
                        heading
                        for heading in headings
                        if heading["line"] < (owner["line"] if owner else line_no)
                        and owner
                        and heading["name"] == owner["name"]
                    ]
                    match = (direct or same_name)[-1] if (direct or same_name) else None
                elif target == "文档内同名功能":
                    matches = [
                        heading
                        for heading in headings
                        if owner
                        and heading["line"] < owner["line"]
                        and heading["name"] == owner["name"]
                    ]
                    match = matches[-1] if matches else None
                else:
                    matches = [
                        heading
                        for heading in headings
                        if heading["line"] < line_no
                        and normalize(heading["name"]) == normalize(target)
                    ]
                    match = matches[-1] if matches else None
            if match:
                target_locator = f"L{match['line']}"
                base_key = f"internal_reference:{normalize(' / '.join(match['path']))}"
        material_available = any(
            normalize(target) in name or name in normalize(target)
            for name in provided_names
            if len(name) > 3
        )
        if ref_type == "internal_reference":
            status = "available" if target_locator else "review_required"
        else:
            status = "available" if material_available else "missing"
        occurrences[base_key] = occurrences.get(base_key, 0) + 1
        dependency = {
            "dependency_id": stable_id("DEP", base_key, occurrences[base_key]),
            "reference_type": ref_type,
            "reference_key": base_key,
            "target_name": target,
            "quote": item["quote"],
            "locator": f"L{line_no}",
            "status": status,
            "reason": None
            if status == "available"
            else (
                (
                    f"路径段「{unresolved_segment}」无法在文档标题中定位"
                    if unresolved_segment
                    else "文档内部目标无法唯一定位"
                )
                if status == "review_required"
                else "未在本次评审提供的资料中定位到该依赖"
            ),
        }
        if target_locator:
            dependency["target_locator"] = target_locator
        if item.get("location_hint"):
            dependency["location_hint"] = item["location_hint"]
        dependencies.append(dependency)

    missing_groups: dict[str, list[dict[str, Any]]] = {}
    for dependency in dependencies:
        if dependency["status"] != "available":
            missing_groups.setdefault(dependency["reference_key"], []).append(
                dependency
            )
    findings = []
    for key, group in missing_groups.items():
        first = group[0]
        code = (
            "UNRESOLVED_INTERNAL_REFERENCE"
            if first["status"] == "review_required"
            else {
                "external_artifact": "MISSING_REFERENCED_ARTIFACT",
                "existing_baseline": "MISSING_EXISTING_BASELINE",
                "pending_artifact": "PENDING_REQUIRED_ARTIFACT",
            }[first["reference_type"]]
        )
        finding_id = stable_id("RQF", code, key)
        findings.append(
            {
                "finding_id": finding_id,
                "code": code,
                "severity": "REVIEW"
                if first["status"] == "review_required"
                else "REJECT",
                "certainty": "confirmed",
                "evidence_type": "ABSENCE",
                "lifecycle_status": "OPEN",
                "dependency_ids": [item["dependency_id"] for item in group],
                "affected_test_dimensions": dimensions(
                    first["reference_type"], first["target_name"]
                ),
                "source_refs": [f"SRC-001:{item['locator']}" for item in group],
                "evidence": f"需求引用了「{first['target_name']}」，但在本次评审来源中未完成定位。",
                "inspected_scope": [
                    str(args.source),
                    *[item["file"] for item in provided],
                ],
                "expected_element": first["target_name"],
                "question": f"请提供或明确「{first['target_name']}」的权威来源。",
                "recommendation": "补充来源后重新执行资料依赖评审，再将结果交给功能图谱。",
            }
        )
    output = {
        "meta": {
            "schema_version": "1.0",
            "artifact_kind": "requirement_source_dependency_review",
            "generated_at": datetime.now(timezone.utc)
            .astimezone()
            .isoformat(timespec="seconds"),
        },
        "source": {
            "source_id": "SRC-001",
            "file": str(args.source),
            "sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        },
        "provided_sources": provided,
        "dependencies": dependencies,
        "findings": findings,
        "summary": {
            "occurrence_count": len(dependencies),
            "distinct_target_count": len(
                {item["reference_key"] for item in dependencies}
            ),
            "by_type": {
                kind: sum(item["reference_type"] == kind for item in dependencies)
                for kind in sorted(REFERENCE_TYPES)
            },
            "by_status": {
                status: sum(item["status"] == status for item in dependencies)
                for status in ("available", "review_required", "missing")
            },
            "finding_count": len(findings),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
