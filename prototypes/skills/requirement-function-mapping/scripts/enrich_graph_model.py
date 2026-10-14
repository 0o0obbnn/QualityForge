#!/usr/bin/env python3
"""Materialize typed graph nodes and edges from normalized mapping facts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def stable_id(prefix: str, *parts: Any) -> str:
    normalized = "|".join(" ".join(str(part or "").split()).casefold() for part in parts)
    return f"{prefix}-{hashlib.sha256(normalized.encode()).hexdigest()[:12].upper()}"


def classify_rule(statement: str) -> str:
    text = statement.casefold()
    classifiers = (
        ("sorting", ("排序", "升序", "降序", "正序", "倒序", "sort", "order by")),
        ("calculation", ("计算", "公式", "系数", "相加", "相乘", "乘以", "除以")),
        ("state", ("状态", "流转", "变更为")),
        ("required", ("必填", "不能为空", "为空")),
        ("uniqueness", ("唯一", "重复")),
        ("format", ("格式", "正则", "日期格式", "文件类型", "后缀")),
        ("range", ("最大", "最小", "不超过", "不少于", "范围", "长度", "字符", "字节")),
        ("enumeration", ("枚举", "取值", "下拉", "包括")),
        ("permission", ("权限", "角色", "仅可", "禁止")),
    )
    return next((kind for kind, tokens in classifiers if any(token in text for token in tokens)), "operation")


def add_relation(relations: list[dict[str, Any]], source_id: str, target_id: str, relation_type: str,
                 note: str, evidence: list[dict[str, Any]]) -> None:
    key = (source_id, target_id, relation_type)
    if not source_id or not target_id or any((item.get("source_id"), item.get("target_id"), item.get("type")) == key for item in relations):
        return
    relations.append({
        "relation_id": stable_id("REL", *key), "source_id": source_id, "target_id": target_id,
        "type": relation_type, "note": note, "evidence": evidence,
    })


def enrich(data: dict[str, Any], source_text: str | None = None) -> dict[str, Any]:
    relations = data.setdefault("relations", [])
    functions = {item.get("function_id"): item for item in data.get("functions", []) if isinstance(item, dict)}
    fields = {item.get("field_id"): item for item in data.get("business_fields", []) if isinstance(item, dict)}

    objects: dict[str, dict[str, Any]] = {}
    states: dict[str, dict[str, Any]] = {}
    for field in fields.values():
        name = field.get("business_object") or "未归属业务对象"
        object_id = stable_id("OBJ", name)
        objects.setdefault(object_id, {"object_id": object_id, "name": name, "status": field.get("attribute_provenance", {}).get("business_object", "unresolved"), "evidence": []})
        for proof in field.get("evidence", []):
            if proof not in objects[object_id]["evidence"]:
                objects[object_id]["evidence"].append(proof)
        field["object_id"] = object_id
        add_relation(relations, object_id, field.get("field_id"), "contains", "业务对象包含字段定义", field.get("evidence", []))
        if re.search(r"状态|情况", str(field.get("business_name", ""))):
            state_ids: list[str] = []
            for value in field.get("enum_values", []):
                state_id = stable_id("STATE", field.get("field_id"), value)
                states[state_id] = {
                    "state_id": state_id, "field_id": field.get("field_id"), "value": value,
                    "status": "derived", "evidence": field.get("evidence", []),
                }
                state_ids.append(state_id)
                add_relation(relations, field.get("field_id"), state_id, "has_state", "状态字段包含明确枚举状态", field.get("evidence", []))
            if state_ids:
                field["state_ids"] = sorted(state_ids)

    rules: dict[str, dict[str, Any]] = {}
    usages: list[dict[str, Any]] = []
    flow_candidates: dict[str, dict[str, Any]] = {
        item.get("candidate_id"): item for item in data.get("business_flow_candidates", [])
        if isinstance(item, dict) and item.get("candidate_id")
    }
    for binding in data.get("field_bindings", []):
        atomic_id, field_id = binding.get("atomic_id"), binding.get("field_id")
        usage_id = stable_id("FUSE", atomic_id, field_id, binding.get("direction"), binding.get("usages"))
        rule_ids: list[str] = []
        for statement in binding.get("rules", []):
            rule_id = stable_id("RULE", "field_usage", usage_id, statement)
            rules[rule_id] = {
                "rule_id": rule_id, "category": classify_rule(str(statement)), "scope": "field_usage",
                "statement": str(statement), "applies_to_ids": [usage_id], "status": "confirmed" if binding.get("evidence") else "unresolved",
                "evidence": binding.get("evidence", []),
            }
            rule_ids.append(rule_id)
            add_relation(relations, usage_id, rule_id, "constrained_by", "字段使用受该规则约束", binding.get("evidence", []))
        usage = {
            "field_usage_id": usage_id, "atomic_id": atomic_id, "field_id": field_id,
            "usages": binding.get("usages", []), "direction": binding.get("direction"),
            "required_here": binding.get("required_here"), "condition": binding.get("condition"),
            "rule_ids": sorted(rule_ids), "evidence": binding.get("evidence", []),
        }
        usages.append(usage)
        add_relation(relations, atomic_id, usage_id, "uses_field", "最小功能使用该上下文字段", binding.get("evidence", []))
        add_relation(relations, usage_id, field_id, "field_of", "字段使用引用字段定义", binding.get("evidence", []))

    # Composite list ordering is often prose or a one-cell table, not a field row.
    # Attach it to the nearest query/list behavior while preserving exact evidence.
    if source_text:
        source_id = data.get("sources", [{}])[0].get("source_id")
        function_lines = []
        for function in functions.values():
            locator = str((function.get("evidence") or [{}])[0].get("locator", ""))
            match = re.match(r"L(\d+)", locator)
            if match:
                function_lines.append((int(match.group(1)), function))
        function_lines.sort(key=lambda item: item[0])
        for line_no, raw_line in enumerate(source_text.splitlines(), 1):
            statement = re.sub(r"<[^>]+>|[*_`]", "", raw_line).strip()
            owners = [item for item in function_lines if item[0] <= line_no]
            action_verbs = set(re.findall(r"查询|展示|显示|导出|下载|上传|提交|审批|启用|停用|删除|生成|更新|变更|进入|返回", statement))
            explicit_sequence = bool(re.search(r"先.+(?:再|然后|最后)", statement))
            evidenced_sequence = len(action_verbs) >= 2 and bool(re.search(r"后|然后|再|最后", statement))
            if 10 <= len(statement) <= 500 and (explicit_sequence or evidenced_sequence):
                if owners:
                    function = owners[-1][1]
                    candidate_id = stable_id("FLOWC", function.get("function_id"), statement)
                    flow_candidates[candidate_id] = {
                        "candidate_id": candidate_id, "function_id": function.get("function_id"),
                        "statement": statement, "status": "review_required",
                        "review_question": "确认参与步骤、顺序、异常分支及跨模块起止节点",
                        "evidence": [{"source_id": source_id, "locator": f"L{line_no}", "quote": statement}],
                    }

            # Materialize only explicit cross-capability references. Bracketed
            # labels that resolve to known functions provide a safe, generic
            # alternative to guessing relationships from domain vocabulary.
            referenced_functions: list[str] = []
            for raw_ref in re.findall(r"【([^】]+)】", statement):
                leaf = raw_ref.split("/")[-1].strip()
                matches = [item for item in functions.values() if item.get("name") in {raw_ref.strip(), leaf}]
                if len(matches) == 1 and matches[0].get("function_id") not in referenced_functions:
                    referenced_functions.append(matches[0]["function_id"])
            if referenced_functions and any(token in statement for token in ("同步", "自动", "绑定", "依赖", "联动", "下线", "停用", "启用")):
                relation_type = (
                    "state_flow" if any(token in statement for token in ("同步停用", "下线", "状态为", "一键停用", "启用"))
                    else "depends_on" if any(token in statement for token in ("绑定", "依赖", "只能"))
                    else "data_flow"
                )
                proof = [{"source_id": source_id, "locator": f"L{line_no}", "quote": statement}]
                for source_function_id, target_function_id in zip(referenced_functions, referenced_functions[1:]):
                    add_relation(relations, source_function_id, target_function_id, relation_type, "原文明示的跨功能业务关联", proof)
                if len(referenced_functions) == 1 and owners:
                    owner_id = owners[-1][1].get("function_id")
                    if owner_id and owner_id != referenced_functions[0]:
                        add_relation(relations, referenced_functions[0], owner_id, relation_type, "原文明示的跨功能业务关联", proof)
            if not statement or not (
                any(token in statement for token in ("排序规则", "列表排序", "列表默认按照", "顺序排列"))
                or ("排序" in statement and any(token in statement for token in ("倒序", "正序", "升序", "降序")))
            ):
                continue
            if not owners:
                continue
            function = owners[-1][1]
            candidates = [item for item in data.get("atomic_functions", []) if item.get("function_id") == function.get("function_id")]
            if not candidates:
                continue
            def score(item: dict[str, Any]) -> tuple[int, int]:
                name = str(item.get("name", ""))
                locator = str((item.get("evidence") or [{}])[0].get("locator", ""))
                match = re.match(r"L(\d+)", locator)
                distance = abs(line_no - int(match.group(1))) if match else 10**9
                preference = 0 if any(token in name for token in ("查询", "列表", "处理")) else 1
                return preference, distance
            atomic = min(candidates, key=score)
            if statement not in atomic.setdefault("processing_rules", []):
                atomic["processing_rules"].append(statement)
            atomic.setdefault("processing_rule_evidence", {})[statement] = [{"source_id": source_id, "locator": f"L{line_no}", "quote": statement}]

    for atomic in data.get("atomic_functions", []):
        atomic_id = atomic.get("atomic_id")
        add_relation(relations, atomic.get("function_id"), atomic_id, "contains", "功能包含最小功能", atomic.get("evidence", []))
        operation_rule_ids: list[str] = []
        for statement in atomic.get("processing_rules", []):
            rule_evidence = atomic.get("processing_rule_evidence", {}).get(statement, atomic.get("evidence", []))
            rule_id = stable_id("RULE", "atomic", atomic_id, statement)
            rules[rule_id] = {
                "rule_id": rule_id, "category": classify_rule(str(statement)), "scope": "atomic_function",
                "statement": str(statement), "applies_to_ids": [atomic_id], "status": atomic.get("status", "unresolved"),
                "evidence": rule_evidence,
            }
            operation_rule_ids.append(rule_id)
            add_relation(relations, atomic_id, rule_id, "constrained_by", "最小功能受该业务规则约束", rule_evidence)
        atomic["rule_ids"] = sorted(operation_rule_ids)

    # Preserve intrinsic field constraints separately from contextual usage rules.
    for field in fields.values():
        intrinsic_rule_ids: list[str] = []
        for statement in field.get("rules", []):
            rule_id = stable_id("RULE", "field", field.get("field_id"), statement)
            rules[rule_id] = {
                "rule_id": rule_id, "category": classify_rule(str(statement)), "scope": "field_definition",
                "statement": str(statement), "applies_to_ids": [field.get("field_id")], "status": field.get("status", "unresolved"),
                "evidence": field.get("evidence", []),
            }
            intrinsic_rule_ids.append(rule_id)
            add_relation(relations, field.get("field_id"), rule_id, "constrained_by", "字段定义受该规则约束", field.get("evidence", []))
        field["rule_ids"] = sorted(intrinsic_rule_ids)

    data["business_objects"] = sorted(objects.values(), key=lambda item: item["object_id"])
    data["field_usages"] = sorted(usages, key=lambda item: item["field_usage_id"])
    data["business_rules"] = sorted(rules.values(), key=lambda item: item["rule_id"])
    data.setdefault("business_flows", [])
    data["business_flow_candidates"] = sorted(flow_candidates.values(), key=lambda item: item["candidate_id"])
    data["states"] = sorted(states.values(), key=lambda item: item["state_id"])
    data.setdefault("meta", {})["graph_model_version"] = "1.0"
    data["meta"]["schema_version"] = "1.4"
    data["meta"]["artifact_kind"] = "typed_requirement_graph"
    data.setdefault("coverage", {})["graph_nodes"] = {
        "modules": len(data.get("modules", [])), "functions": len(functions),
        "atomic_functions": len(data.get("atomic_functions", [])), "business_objects": len(objects),
        "business_fields": len(fields), "field_usages": len(usages), "business_rules": len(rules),
        "business_flows": len(data.get("business_flows", [])), "states": len(states),
    }
    data["coverage"]["business_flow_candidate_count"] = len(flow_candidates)
    data["coverage"]["graph_edges"] = len(relations)
    if flow_candidates:
        data.setdefault("gaps", {})["unresolved_business_flows"] = sorted(flow_candidates)
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize typed requirement graph nodes and edges")
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--source", type=Path, help="Optional source Markdown for prose-level composite rules")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    source_text = args.source.read_text(encoding="utf-8") if args.source else None
    data = enrich(json.loads(args.mapping.read_text(encoding="utf-8")), source_text)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
