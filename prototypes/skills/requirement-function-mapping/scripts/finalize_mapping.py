#!/usr/bin/env python3
"""Normalize a discovery mapping into schema 1.2 without inventing acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def stable_id(prefix: str, *parts: Any) -> str:
    value = "|".join(" ".join(str(part or "").split()).casefold() for part in parts)
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:12].upper()}"


def replace_refs(value: Any, maps: dict[str, str]) -> Any:
    if isinstance(value, str):
        return maps.get(value, value)
    if isinstance(value, list):
        return [replace_refs(item, maps) for item in value]
    if isinstance(value, dict):
        return {key: replace_refs(item, maps) for key, item in value.items()}
    return value


def atomic_readiness(atomic: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    placeholder = any(
        token in str(atomic.get(key, ""))
        for key in ("actor", "trigger", "action")
        for token in ("待确认", "对应功能", "相关行为", "满足原文触发条件")
    )
    result_text = " ".join(str(value) for key in ("outputs", "state_changes", "branches") for value in (atomic.get(key) or []))
    if not result_text or "待语义复核" in result_text:
        reasons.append("缺少可直接判定的预期结果")
    if placeholder:
        reasons.append("执行角色、触发或动作仍是占位描述")
    if atomic.get("status") != "confirmed":
        reasons.append(f"最小功能状态为 {atomic.get('status', 'unresolved')}")
    if not atomic.get("evidence"):
        reasons.append("缺少来源证据")
    if any("预期结果" in reason for reason in reasons):
        status = "blocked"
    elif reasons:
        status = "review_required"
    else:
        status = "ready"
    return {"status": status, "reasons": reasons}


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize a mapping draft as schema 1.2")
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--source-version", default="unknown")
    options = parser.parse_args()

    data = json.loads(options.mapping.read_text(encoding="utf-8"))
    already_finalized = data.get("meta", {}).get("id_strategy") == "semantic-sha256-12"
    source_bytes = options.source.read_bytes()
    source_sha = hashlib.sha256(source_bytes).hexdigest()

    source_map: dict[str, str] = {}
    for index, source in enumerate(data.get("sources", [])):
        old = source.get("source_id")
        digest = source_sha if index == 0 else source.get("sha256", "")
        new = old if already_finalized and old else stable_id("SRC", Path(str(source.get("file", "source"))).name, source.get("version", options.source_version), digest)
        source_map[old] = new
        source["source_id"] = new
        source["file"] = Path(str(source.get("file", options.source.name))).name
        source["version"] = options.source_version if options.source_version != "unknown" else (source.get("version") or "unknown")
        if index == 0:
            source["sha256"] = source_sha

    module_map = {
        module.get("module_id"): stable_id("MOD", module.get("name"))
        for module in data.get("modules", []) if isinstance(module, dict)
    }

    function_map: dict[str, str] = {}
    for function in data.get("functions", []):
        if already_finalized:
            function_map[function["function_id"]] = function["function_id"]
        elif function.get("parent_function_id"):
            function_map[function["function_id"]] = stable_id("FUN", function.get("module"), function.get("function_path"), function.get("business_goal"))
        else:
            # Preserve established top-level IDs; hierarchy only adds semantic
            # path material where identical child names otherwise collide.
            function_map[function["function_id"]] = stable_id("FUN", function.get("module"), function.get("name"), function.get("business_goal"))
    atomic_map: dict[str, str] = {}
    for atomic in data.get("atomic_functions", []):
        atomic_map[atomic["atomic_id"]] = atomic["atomic_id"] if already_finalized else stable_id("AF", function_map.get(atomic.get("function_id")), atomic.get("name"), atomic.get("action"), atomic.get("category"))

    direction_by_field: dict[str, set[str]] = {}
    function_by_field: dict[str, set[str]] = {}
    for occurrence in data.get("field_occurrences", []):
        direction_by_field.setdefault(occurrence.get("field_id"), set()).add(occurrence.get("role", ""))
        function_by_field.setdefault(occurrence.get("field_id"), set()).add(function_map.get(occurrence.get("function_id"), occurrence.get("function_id")))
    field_map: dict[str, str] = {}
    for field in data.get("business_fields", []):
        old = field["field_id"]
        field_map[old] = old if already_finalized else stable_id("FLD", ",".join(sorted(function_by_field.get(old, set()))), field.get("business_object"), field.get("business_name"), ",".join(sorted(direction_by_field.get(old, set()))))
    unit_map = {unit.get("unit_id"): (unit.get("unit_id") if already_finalized else stable_id("UNIT", source_map.get(unit.get("source_id")), unit.get("kind"), unit.get("locator"), unit.get("unit_id"))) for unit in data.get("source_units", [])}
    occurrence_map = {item.get("occurrence_id"): (item.get("occurrence_id") if already_finalized else stable_id("OCC", field_map.get(item.get("field_id")), function_map.get(item.get("function_id")), item.get("surface"), item.get("role"), item.get("name_as_written"), item.get("evidence"))) for item in data.get("field_occurrences", [])}
    relation_map = {item.get("relation_id"): (item.get("relation_id") if already_finalized else stable_id("REL", item.get("type"), function_map.get(item.get("source_id"), atomic_map.get(item.get("source_id"), field_map.get(item.get("source_id")))), function_map.get(item.get("target_id"), atomic_map.get(item.get("target_id"), field_map.get(item.get("target_id")))), item.get("note"), item.get("evidence"))) for item in data.get("relations", [])}
    all_maps = {**source_map, **module_map, **function_map, **atomic_map, **field_map, **unit_map, **occurrence_map, **relation_map}
    data = replace_refs(data, all_maps)

    modules_by_name = {module.get("name"): module.get("module_id") for module in data.get("modules", [])}
    existing_relations = {(item.get("source_id"), item.get("target_id"), item.get("type")) for item in data.get("relations", [])}
    for function in data.get("functions", []):
        module_id = modules_by_name.get(function.get("module"))
        if not module_id:
            continue
        function["module_id"] = module_id
        parent_function_id = function.get("parent_function_id")
        source_id = parent_function_id or module_id
        key = (source_id, function.get("function_id"), "contains")
        if key not in existing_relations:
            data.setdefault("relations", []).append({
                "relation_id": stable_id("REL", *key), "source_id": source_id,
                "target_id": function.get("function_id"), "type": "contains",
                "note": "子功能属于该功能" if parent_function_id else "功能属于该模块", "evidence": function.get("evidence", []),
            })
            existing_relations.add(key)

    readiness_counts = {"ready": 0, "review_required": 0, "blocked": 0}
    for atomic in data.get("atomic_functions", []):
        atomic["generation_readiness"] = atomic_readiness(atomic)
        readiness_counts[atomic["generation_readiness"]["status"]] += 1

    data.setdefault("meta", {})["schema_version"] = "1.2"
    data["meta"]["artifact_kind"] = "normalized_requirement_mapping"
    data["meta"]["generated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    data["meta"]["content_hash"] = source_sha
    data["meta"]["id_strategy"] = "semantic-sha256-12"
    data.setdefault("coverage", {})["generation_readiness"] = readiness_counts
    data.setdefault("audit", {})["downstream_eligible"] = False if data["audit"].get("verdict") != "PASS" else data["audit"].get("downstream_eligible", False)
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
