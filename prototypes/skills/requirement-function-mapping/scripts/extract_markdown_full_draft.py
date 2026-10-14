#!/usr/bin/env python3
"""Build an exhaustive, evidence-linked draft inventory from Markdown.

This is a discovery pass, not a semantic acceptance engine. It deliberately
keeps field occurrences separate and leaves unresolved authoritative external
units visible so a full claim cannot pass prematurely.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

GENERIC = {
    "系统功能设计",
    "功能模块概述",
    "模块功能描述",
    "功能描述",
    "列表页",
    "网页端",
    "接口端",
    "说明",
    "非功能需求",
}
NON_FUNCTIONAL = {"性能需求", "安全需求", "兼容性"}
SKIP_FIELD_TYPES = {"标签页", "页面标题", "Tab切换", "提示语", "按钮", "操作", "分页"}
UI_ONLY_FIELDS = {"序号", "操作", "按钮", "分页"}
ACTION_PREFIXES = (
    "查看",
    "新增",
    "编辑",
    "审批",
    "删除",
    "下载",
    "上传",
    "导出",
    "查询",
    "重置",
    "提交",
    "关闭",
    "启用",
    "停用",
)
ACTION_HEADING_PREFIXES = ACTION_PREFIXES + ("提交", "生成", "取消", "确定", "重新")
CAPABILITY_SUFFIXES = (
    "管理",
    "列表",
    "详情",
    "记录",
    "统计",
    "产品",
    "接口",
    "服务",
    "系数",
)
EXPLANATORY_SUFFIXES = ("说明", "概述", "描述")
NON_CAPABILITY_HEADING = re.compile(r"^(?:暂无|无)(?:数据|内容|记录)$|^空状态$")
SURFACE_BY_TYPE = {
    "筛选条件": "query_condition",
    "筛选": "query_condition",
    "列表": "list_column",
    "字段": "detail_field",
}
ACTION_SPLIT = re.compile(r"[、,，/]")
REFERENCE_TYPES = {
    "internal_reference",
    "external_artifact",
    "existing_baseline",
    "pending_artifact",
}


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[dict[str, Any]] = []
        self.tables: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.stack.append(
                {"line": self.getpos()[0], "rows": [], "row": None, "cell": None}
            )
        elif self.stack and tag == "tr":
            self.stack[-1]["row"] = []
        elif self.stack and tag in {"td", "th"} and self.stack[-1]["row"] is not None:
            self.stack[-1]["cell"] = []
        elif self.stack and tag == "br" and self.stack[-1]["cell"] is not None:
            self.stack[-1]["cell"].append(" / ")

    def handle_data(self, data: str) -> None:
        if self.stack and self.stack[-1]["cell"] is not None:
            self.stack[-1]["cell"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return
        table = self.stack[-1]
        if tag in {"td", "th"} and table["cell"] is not None:
            value = re.sub(r"\s+", " ", "".join(table["cell"])).strip()
            table["row"].append(value)
            table["cell"] = None
        elif tag == "tr" and table["row"] is not None:
            table["rows"].append(table["row"])
            table["row"] = None
        elif tag == "table":
            self.tables.append(self.stack.pop())


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a full-scope Markdown extraction draft"
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument(
        "--source-review",
        type=Path,
        help="qa-requirement-review source dependency review",
    )
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def heading_at(headings: list[dict[str, Any]], line: int) -> dict[str, Any] | None:
    found = [
        item
        for item in headings
        if item["line"] <= line and item["name"] not in GENERIC
    ]
    return found[-1] if found else None


def is_ancestor(parent: dict[str, Any], child: dict[str, Any]) -> bool:
    """Return whether parent is a strict Markdown-heading ancestor of child."""
    return (
        parent["line"] < child["line"]
        and parent["level"] < child["level"]
        and child["path"][: len(parent["path"])] == parent["path"]
    )


def owner_before(items: list[dict[str, Any]], line: int) -> dict[str, Any] | None:
    """Find the nearest preceding classified item by source position."""
    found = [item for item in items if item["line"] <= line]
    return found[-1] if found else None


def content_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_action_name(value: str) -> str:
    value = re.sub(r"[（(].*$", "", value).strip()
    value = re.sub(r"^(?:按钮|操作)[:：]?", "", value).strip()
    return value


def normalize_reference_target(value: str) -> str:
    return re.sub(r"[\s《》\"'“”]", "", value).lower()


def is_action_heading(name: str) -> bool:
    """Classify verb-like leaf headings without promoting capability nouns."""
    normalized = normalize_action_name(name)
    return normalized.startswith(ACTION_HEADING_PREFIXES) and not normalized.endswith(
        CAPABILITY_SUFFIXES
    )


def actor_from_path(path: list[str]) -> str:
    """Project only actor scope explicitly carried by headings."""
    joined = " / ".join(path)
    if "暂无权限" in joined:
        return "没有权限（角色）的用户"
    portal = next((segment for segment in reversed(path) if segment.endswith("端")), None)
    if portal is not None:
        return f"{portal}用户"
    return "待确认"


def split_field_enumeration(value: str) -> list[str]:
    """Split a prose field list without breaking commas inside parentheses."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in value:
        if char in "（(【[":
            depth += 1
        elif char in "）)】]" and depth:
            depth -= 1
        if depth == 0 and char in "、，,":
            if "".join(current).strip():
                parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if "".join(current).strip():
        parts.append("".join(current).strip())
    expanded: list[str] = []
    for part in parts:
        expanded.extend(item.strip() for item in re.split(r"和", part) if item.strip())
    return expanded


def field_rows(table: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand the common field-table shape while tolerating one rowspan cell."""
    rows = table["rows"]
    if not rows or "字段" not in rows[0]:
        return []
    header = rows[0]
    indexes = {name: header.index(name) for name in header}
    type_index = indexes.get("类型")
    required_index = indexes.get("是否必填")
    description_index = next(
        (indexes[name] for name in ("字段描述", "描述") if name in indexes), None
    )
    validation_index = next(
        (indexes[name] for name in ("校验规则", "校验") if name in indexes), None
    )
    current_type = "字段"
    result: list[dict[str, Any]] = []

    for values in rows[1:]:
        missing_type = type_index is not None and len(values) == len(header) - 1

        def value_at(index: int | None) -> str | None:
            if index is None:
                return None
            actual = index - 1 if missing_type and index > type_index else index
            return values[actual] if 0 <= actual < len(values) else None

        row_type = value_at(type_index)
        if not missing_type and row_type:
            current_type = row_type
        field_name = value_at(indexes["字段"])
        if field_name is None:
            continue
        # Many exported PRD tables encode a filter/detail group as an empty
        # rowspan cell immediately after the page-title row.  Carrying the
        # previous "页面标题" type silently drops every grouped business field.
        # Infer the group from explicit widget language in the first row; the
        # following rowspan-omitted rows then inherit that inferred type.
        description = value_at(description_index) or ""
        if (
            type_index is not None
            and not missing_type
            and not row_type
            and current_type in {"标签页", "页面标题"}
        ):
            current_type = (
                "筛选条件"
                if re.search(r"输入框|下拉框|选择器|请输入|请选择", description)
                else "字段"
            )
        result.append(
            {
                "type": current_type,
                "field_name": field_name.strip(),
                "required": value_at(required_index),
                "description": value_at(description_index),
                "validation": value_at(validation_index),
            }
        )
    return result


def derive_field_attributes(
    field_name: str, description: str, validation: str
) -> dict[str, Any]:
    """Derive conservative, provenance-labelled field attributes from source text."""
    combined = " ".join(
        value for value in (description, validation) if value and value != "-"
    )
    data_type = None
    if re.search(r"正整数|整数", combined):
        data_type = "integer"
    elif re.search(r"日期选择器|时间选择器|yyyy|YYYY", combined):
        data_type = "datetime" if re.search(r"时|hh|HH|ss", combined) else "date"
    elif re.search(r"输入框|下拉框|文本", combined):
        data_type = "string"

    format_match = re.search(r"(?:yyyy|YYYY)[A-Za-z年月日时分秒\-:～~ ]+", combined)
    field_format = format_match.group(0).strip() if format_match else None
    enum_values: list[str] = []
    enum_match = re.search(
        r"选项(?:为|包括)?\s*[：:]?\s*(.+?)(?:默认|[。；;]|$)", description
    )
    if enum_match:
        enum_values = [
            value.strip(" “\"”'")
            for value in re.split(r"[、，,/]", enum_match.group(1))
            if value.strip()
        ]
    default_match = re.search(r"默认(?:为|选择)?\s*([^，。；;/\s]+)", combined)
    default_value = default_match.group(1) if default_match else None
    length_match = re.search(
        r"(?:最多|不超过|最大(?:不能)?超过)\s*(\d+)\s*(?:位|个字符|字符)", combined
    )
    max_length = int(length_match.group(1)) if length_match else None

    normative = re.compile(
        r"必须|不能|不可|默认|仅|大于|小于|超过|格式|长度|范围|自动|实时|选项|掩码|校验|计算|反显|隐藏|显示"
    )
    rules = []
    for value in (validation, description):
        value = value.strip() if value else ""
        if value and value != "-" and normative.search(value) and value not in rules:
            rules.append(value)

    sensitivity = (
        "sensitive"
        if re.search(
            r"姓名|证件|手机号|电话|地址|银行卡|账号|密钥|初始向量", field_name
        )
        else "unclassified"
    )
    unresolved = ["技术名称"]
    if data_type is None:
        unresolved.append("数据类型")
    if sensitivity == "unclassified":
        unresolved.append("敏感性")
    unresolved.append("完整规则")
    return {
        "data_type": data_type,
        "format": field_format,
        "length": max_length,
        "default_value": default_value,
        "enum_values": enum_values,
        "rules": rules,
        "sensitivity": sensitivity,
        "unresolved_attributes": unresolved,
        "attribute_provenance": {
            "business_object": "inferred",
            "data_type": "derived" if data_type else "unresolved",
            "required": "unresolved",
            "sensitivity": "derived" if sensitivity != "unclassified" else "unresolved",
        },
    }


def main() -> int:
    options = args()
    text = options.source.read_text(encoding="utf-8")
    lines = text.splitlines()
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

    parser = TableParser()
    parser.feed(text)
    tables = sorted(parser.tables, key=lambda item: item["line"])
    images = [
        (index, match.start(), match.group(1))
        for index, match in enumerate(
            re.finditer(r'<img\b[^>]*?src="([^"]+)"', text), 1
        )
    ]
    source_units: list[dict[str, Any]] = []
    semantic_occurrences: dict[str, int] = {}

    def unit_key(kind: str, identity: str) -> str:
        base = f"{kind}:{' '.join(identity.split())}"
        semantic_occurrences[base] = semantic_occurrences.get(base, 0) + 1
        return f"{base}#{semantic_occurrences[base]}"

    for index, heading in enumerate(headings, 1):
        in_nonfunctional = "非功能需求" in heading["path"]
        end_line = next(
            (
                item["line"] - 1
                for item in headings[index:]
                if item["level"] <= heading["level"]
            ),
            len(lines),
        )
        section_text = "\n".join(lines[heading["line"] - 1 : end_line])
        source_units.append(
            {
                "unit_id": f"SEC-{index:03d}",
                "semantic_key": unit_key("section", " / ".join(heading["path"])),
                "content_sha256": content_sha256(section_text),
                "source_id": "SRC-001",
                "kind": "section",
                "locator": f"L{heading['line']}",
                "line_start": heading["line"],
                "line_end": end_line,
                "relevant": not in_nonfunctional,
                "status": "processed",
                "reason": "超出功能点图谱范围：非功能需求"
                if in_nonfunctional
                else None,
            }
        )
    table_occurrences: dict[str, int] = {}
    for index, table in enumerate(tables, 1):
        owner = heading_at(headings, table["line"])
        owner_path = " / ".join(owner["path"]) if owner else "document-root"
        table_occurrences[owner_path] = table_occurrences.get(owner_path, 0) + 1
        identity = f"{owner_path} / table-{table_occurrences[owner_path]}"
        source_units.append(
            {
                "unit_id": f"TBL-{index:03d}",
                "semantic_key": unit_key("table", identity),
                "content_sha256": content_sha256(
                    json.dumps(table["rows"], ensure_ascii=False, separators=(",", ":"))
                ),
                "source_id": "SRC-001",
                "kind": "table",
                "locator": f"L{table['line']}",
                "line_start": table["line"],
                "line_end": table["line"],
                "relevant": True,
                "status": "processed",
                "reason": None,
            }
        )
    for index, offset, image_path in images:
        line = text.count("\n", 0, offset) + 1
        exists = (options.source.parent / image_path).is_file()
        source_units.append(
            {
                "unit_id": f"IMG-{index:03d}",
                "semantic_key": unit_key("image", image_path),
                "content_sha256": content_sha256(image_path),
                "source_id": "SRC-001",
                "kind": "image",
                "locator": f"L{line}:{image_path}",
                "line_start": line,
                "line_end": line,
                "relevant": False,
                "status": "skipped",
                "reason": "正文为默认权威输入；图片仅在具备多模态能力且明确需要视觉核验时作为补充证据",
                "visual_availability": "available" if exists else "file_missing",
            }
        )

    source_review = None
    source_review_findings: dict[str, list[str]] = {}
    if options.source_review:
        source_review = json.loads(options.source_review.read_text(encoding="utf-8"))
        if (
            source_review.get("meta", {}).get("artifact_kind")
            != "requirement_source_dependency_review"
        ):
            raise SystemExit(
                "--source-review must be a requirement_source_dependency_review artifact"
            )
        if (
            source_review.get("source", {}).get("sha256")
            != hashlib.sha256(options.source.read_bytes()).hexdigest()
        ):
            raise SystemExit(
                "--source-review was produced from a different primary source snapshot"
            )
        for finding in source_review.get("findings", []):
            for dependency_id in finding.get("dependency_ids", []):
                source_review_findings.setdefault(dependency_id, []).append(
                    finding.get("finding_id")
                )

    for index, item in enumerate(
        source_review.get("dependencies", []) if source_review else [], 1
    ):
        reference_type = item["reference_type"]
        quote = item["quote"]
        target_name = item["target_name"]
        line_no = int(str(item["locator"])[1:])
        reviewed_status = item.get("status")
        source_units.append(
            {
                "unit_id": f"REF-{index:03d}",
                "semantic_key": unit_key(
                    "reference_dependency", f"{reference_type}:{target_name}"
                ),
                "content_sha256": content_sha256(quote),
                "source_id": "SRC-001",
                "kind": "reference_dependency",
                "reference_type": reference_type,
                "reference_key": item["reference_key"],
                "target_name": target_name,
                "quote": quote,
                "locator": f"L{line_no}",
                "line_start": line_no,
                "line_end": line_no,
                "relevant": True,
                "status": {
                    "available": "processed",
                    "review_required": "review_required",
                    "missing": "unavailable",
                }[reviewed_status],
                "resolution_status": (
                    "target_located"
                    if reviewed_status == "available" and item.get("target_locator")
                    else "baseline_available"
                    if reviewed_status == "available"
                    and reference_type == "existing_baseline"
                    else "artifact_available"
                    if reviewed_status == "available"
                    else "unresolved"
                ),
                "blocking_scope": {"source_id": "SRC-001", "locator": f"L{line_no}"},
                "reason": item.get("reason"),
                "dependency_id": item["dependency_id"],
                "finding_ids": sorted(
                    value
                    for value in source_review_findings.get(item["dependency_id"], [])
                    if value
                ),
                **(
                    {"review_target_locator": item["target_locator"]}
                    if item.get("target_locator")
                    else {}
                ),
                **(
                    {"location_hint": item["location_hint"]}
                    if item.get("location_hint")
                    else {}
                ),
            }
        )

    functional_headings = [
        item
        for item in headings
        if item["level"] >= 2 and "非功能需求" not in item["path"]
    ]
    module_candidates = [
        item
        for item in functional_headings
        if item["level"] == 2 and not NON_CAPABILITY_HEADING.match(item["name"])
    ]
    candidates: list[dict[str, Any]] = []
    atomic_candidates: list[dict[str, Any]] = []
    excluded_headings: list[dict[str, Any]] = []

    # Heading depth is not globally meaningful. Classify relative to each H2
    # module, transparently skipping document-structure wrapper headings.
    for module in module_candidates:
        descendants = [
            item for item in functional_headings if is_ancestor(module, item)
        ]
        business_descendants = [
            item
            for item in descendants
            if item["name"] not in GENERIC
            and not item["name"].endswith(EXPLANATORY_SUFFIXES)
        ]
        for item in descendants:
            if item not in business_descendants:
                excluded_headings.append(
                    {"heading": item, "reason": "文档结构、展示载体或解释性标题"}
                )

        if not business_descendants:
            # A leaf H2 can itself describe a standalone function.
            candidates.append(module)
            continue

        for item in business_descendants:
            business_ancestors = [
                other for other in business_descendants if is_ancestor(other, item)
            ]
            if not business_ancestors or not is_action_heading(item["name"]):
                candidates.append(item)
            else:
                atomic_candidates.append(item)

    candidates.sort(key=lambda item: item["line"])
    atomic_candidates.sort(key=lambda item: item["line"])
    functions: list[dict[str, Any]] = []
    atomics: list[dict[str, Any]] = []
    heading_to_function: dict[int, str] = {}
    for index, item in enumerate(candidates, 1):
        function_id = f"FUN-{index:03d}"
        heading_to_function[item["line"]] = function_id
        module = item["path"][1] if len(item["path"]) > 1 else item["name"]
        parent_candidates = [
            candidate for candidate in candidates if is_ancestor(candidate, item)
        ]
        parent = parent_candidates[-1] if parent_candidates else None
        function_path = [
            name
            for name in item["path"][1:]
            if name not in GENERIC and not name.endswith(EXPLANATORY_SUFFIXES)
        ]
        actor = actor_from_path(item["path"])
        functions.append(
            {
                "function_id": function_id,
                "name": item["name"],
                "module": module,
                "parent_function_id": heading_to_function.get(parent["line"])
                if parent
                else None,
                "function_path": function_path,
                "actors": [] if actor == "待确认" else [actor],
                "business_goal": f"处理{item['name']}相关业务",
                "preconditions": [],
                "outcomes": [f"完成{item['name']}相关处理"],
                "status": "inferred",
                "evidence": [
                    {
                        "source_id": "SRC-001",
                        "locator": f"L{item['line']}",
                        "quote": item["name"],
                    }
                ],
            }
        )
    for item in atomic_candidates:
        owners = [candidate for candidate in candidates if is_ancestor(candidate, item)]
        owner = owners[-1] if owners else owner_before(candidates, item["line"])
        if owner is None:
            continue
        function_id = heading_to_function[owner["line"]]
        atomic_id = f"AF-{len(atomics) + 1:03d}"
        category = (
            "interaction"
            if item["name"].startswith(ACTION_PREFIXES)
            else "business_action"
        )
        atomics.append(
            {
                "atomic_id": atomic_id,
                "function_id": function_id,
                "name": item["name"],
                "category": category,
                "action": item["name"],
                "actor": actor_from_path(item["path"]),
                "trigger": f"触发{item['name']}相关行为",
                "preconditions": [],
                "inputs": [],
                "processing_rules": [],
                "outputs": [],
                "state_changes": [],
                "branches": ["具体结果待语义复核"],
                "status": "inferred",
                "evidence": [
                    {
                        "source_id": "SRC-001",
                        "locator": f"L{item['line']}",
                        "quote": item["name"],
                    }
                ],
            }
        )

    table_atomic_decisions: list[dict[str, Any]] = []
    prose_atomic_decisions: list[dict[str, Any]] = []
    interface_atomic_decisions: list[dict[str, Any]] = []

    def add_discovered_atomic(
        function_id: str,
        name: str,
        line: int,
        detail: str | None = None,
        *,
        origin: str = "table_action",
    ) -> None:
        name = normalize_action_name(name)
        if not name or name == "-":
            return
        proof = {"source_id": "SRC-001", "locator": f"L{line}", "quote": name}
        existing = next(
            (
                item
                for item in atomics
                if item["function_id"] == function_id and item["name"] == name
            ),
            None,
        )
        if existing is not None:
            if proof not in existing["evidence"]:
                existing["evidence"].append(proof)
            return
        atomic_id = f"AF-{len(atomics) + 1:03d}"
        owning_function = next(
            item for item in functions if item["function_id"] == function_id
        )
        inherited_actor = next(iter(owning_function.get("actors", [])), "待确认")
        atomics.append(
            {
                "atomic_id": atomic_id,
                "function_id": function_id,
                "name": name,
                "category": "interaction",
                "action": name,
                "actor": inherited_actor,
                "trigger": f"触发{name}操作",
                "preconditions": [],
                "inputs": [],
                "processing_rules": [detail] if detail else [],
                "outputs": [],
                "state_changes": [],
                "branches": [detail or f"{name}操作产生可观察结果，具体结果待语义复核"],
                "status": "confirmed",
                "origin": origin,
                "evidence": [proof],
            }
        )
        target = (
            table_atomic_decisions
            if origin == "table_action"
            else interface_atomic_decisions
            if origin == "interface_table"
            else prose_atomic_decisions
        )
        reason = (
            "表格中的按钮或操作定义"
            if origin == "table_action"
            else "接口或能力清单中的显式条目"
            if origin == "interface_table"
            else "正文中的显式能力陈述"
        )
        target.append(
            {
                "locator": f"L{line}",
                "heading": name,
                "decision": "atomic_function",
                "reason": reason,
            }
        )

    # Tables often carry the actual interaction inventory even when headings do
    # not. Extract those operations before binding their fields.
    for table in tables:
        owner = owner_before(candidates, table["line"])
        if owner is None:
            continue
        function_id = heading_to_function[owner["line"]]
        rows = table["rows"]
        if rows and "操作" in rows[0]:
            operation_index = rows[0].index("操作")
            for row in rows[1:]:
                if operation_index >= len(row):
                    continue
                raw = row[operation_index]
                detail = " / ".join(
                    value
                    for index, value in enumerate(row)
                    if index != operation_index and value
                )
                action_list = re.sub(r"[（(].*?[）)]", "", raw)
                for operation in ACTION_SPLIT.split(action_list):
                    add_discovered_atomic(
                        function_id, operation.strip(), table["line"], detail or None
                    )
        for row in field_rows(table):
            field_name = row["field_name"]
            description = (row["description"] or "").strip()
            is_button = row["type"] in {"按钮", "操作"}
            is_action_shaped_field = (
                "类型" not in rows[0]
                and row["required"] in {"-", None}
                and bool(re.match(r"^点击(?:[^，。；;]{0,16})后", description))
            )
            if is_button or is_action_shaped_field:
                add_discovered_atomic(
                    function_id, field_name, table["line"], description or None
                )

        # Capability catalogs such as interface/function/service name tables are
        # not field tables. Each row is an explicit child capability.
        if rows:
            capability_index = next(
                (
                    index
                    for index, value in enumerate(rows[0])
                    if re.fullmatch(r"(?:新|目标)?(?:接口|功能|操作|服务)名称", value)
                ),
                None,
            )
            if capability_index is not None:
                for row in rows[1:]:
                    if capability_index >= len(row):
                        continue
                    name = row[capability_index].strip()
                    detail = " / ".join(
                        value
                        for index, value in enumerate(row)
                        if index != capability_index and value
                    )
                    add_discovered_atomic(
                        function_id,
                        name,
                        table["line"],
                        detail or None,
                        origin="interface_table",
                    )

    prose_action_patterns = [
        re.compile(
            r"(?:支持|仅能|可以|(?<!不)可)(?:进行)?(查询|查看|新增|编辑|删除|导出|下载|上传|审批|启用|停用|提交|重置)"
        ),
        re.compile(
            r"(?:^|\s|\d+[、.)）])\s*(新增|编辑|删除|停用|启用|提交|审批|导出|下载|上传|查看|查询)[^，。；;]{0,24}(?:时|后|前|[：:])"
        ),
    ]
    for line_no, line in enumerate(lines, 1):
        current_heading = owner_before(headings, line_no)
        if current_heading is not None and "非功能需求" in current_heading["path"]:
            continue
        owner = owner_before(candidates, line_no)
        if owner is None:
            continue
        function_id = heading_to_function[owner["line"]]
        plain_line = re.sub(r"<[^>]+>|[*_`]", "", line).strip()
        if re.search(r"</?(?:td|th|tr)\b", line, re.IGNORECASE):
            continue
        for prose_action_pattern in prose_action_patterns:
            for match in prose_action_pattern.finditer(plain_line):
                add_discovered_atomic(
                    function_id,
                    match.group(1),
                    line_no,
                    plain_line,
                    origin="prose_action",
                )
        for match in re.finditer(
            r"点击[“\"]?([^，。；;]{1,24}?)[”\"]?(?:按钮)?后", plain_line
        ):
            named_action = (
                normalize_action_name(match.group(1)).removesuffix("按钮").strip()
            )
            known_action_names = {
                item.get("name")
                for item in atomics
                if item.get("function_id") == function_id
            }
            explicit_control = bool(
                re.fullmatch(
                    r"确认|确定|取消|关闭|取消或X|关闭或X", named_action, re.IGNORECASE
                )
            )
            if (
                named_action
                and len(named_action) <= 20
                and (named_action in known_action_names or explicit_control)
            ):
                add_discovered_atomic(
                    function_id,
                    named_action,
                    line_no,
                    plain_line,
                    origin="prose_action",
                )
        # Action enumerations such as “停用/启用” describe multiple distinct
        # behaviours. A single regex capture must not silently drop the later
        # actions in the same source sentence.
        for enumeration in re.finditer(r"(?:停用[/、]启用|启用[/、]停用)", plain_line):
            for action in re.split(r"[/、]", enumeration.group(0)):
                add_discovered_atomic(
                    function_id, action, line_no, plain_line, origin="prose_action"
                )

    # System-job candidates via set difference: a prose sentence that produces
    # an observable result through CRUD/state verbs, is not triggered by any
    # user interaction pattern, and carries a system subject or a time-grammar
    # trigger. Judgement stays structural; status stays inferred for semantic
    # review to confirm or downgrade.
    system_subjects = (
        "系统",
        "平台",
        "后台",
        "服务端",
        "定时任务",
        "调度",
        "批处理",
        "程序",
    )
    time_grammar = re.compile(r"每[天日周月年号]|\bT[+-]\d|次日")
    result_verb = re.compile(
        r"生成|创建|新增|删除|更新|统计|汇总|计算|发送|触发|同步|停用|启用|重置|归档|清理|执行|校验"
    )
    interaction_trigger = re.compile(r"点击|选择|输入|按钮|登录后|勾选")
    consumed_system_lines: set[int] = set()
    for line_no, line in enumerate(lines, 1):
        current_heading = owner_before(headings, line_no)
        if current_heading is not None and "非功能需求" in current_heading["path"]:
            continue
        owner = owner_before(candidates, line_no)
        if owner is None:
            continue
        plain_line = re.sub(r"<[^>]+>|[*_`]", "", line).strip()
        if not plain_line or re.search(r"</?(?:td|th|tr)\b", line, re.IGNORECASE):
            continue
        verb_match = result_verb.search(plain_line)
        if not verb_match:
            continue
        subject_hit = next(
            (token for token in system_subjects if token in plain_line), None
        )
        time_match = time_grammar.search(plain_line)
        if subject_hit is None and time_match is None:
            continue
        if interaction_trigger.search(plain_line):
            continue
        function_id = heading_to_function[owner["line"]]
        if any(
            item.get("function_id") == function_id
            and verb_match.group(0) in str(item.get("name", ""))
            for item in atomics
        ):
            continue
        tail = re.split(
            r"[，。；;、]", plain_line[verb_match.end() : verb_match.end() + 16]
        )[0]
        name = f"{verb_match.group(0)}{tail}" if tail else f"{verb_match.group(0)}行为"
        atomics.append(
            {
                "atomic_id": f"AF-{len(atomics) + 1:03d}",
                "function_id": function_id,
                "name": name,
                "category": "system_job",
                "action": name,
                "actor": subject_hit or "系统（待确认）",
                "trigger": time_match.group(0)
                if time_match
                else f"{subject_hit}行为（触发待语义复核确认）",
                "preconditions": [],
                "inputs": [],
                "processing_rules": [plain_line],
                "outputs": [],
                "state_changes": [],
                "branches": ["系统行为候选，具体结果待语义复核"],
                "status": "inferred",
                "origin": "prose_system_job",
                "evidence": [
                    {
                        "source_id": "SRC-001",
                        "locator": f"L{line_no}",
                        "quote": plain_line,
                    }
                ],
            }
        )
        consumed_system_lines.add(line_no)
        prose_atomic_decisions.append(
            {
                "locator": f"L{line_no}",
                "heading": name,
                "decision": "atomic_function",
                "reason": "正文中的系统行为陈述（非交互触发）",
            }
        )

    # A no-permission default page is a testable access-control outcome, not an
    # empty-state heading. Preserve the complete trigger and observable result.
    permission_outcome = re.compile(
        r"(?:(?:没有|无|未).{0,8}权限|暂无权限).{0,24}(?:显示|展示|看到|进入|跳转).{0,24}(?:暂无权限|无权限|缺省页|默认页|提示页)"
    )
    for function in functions:
        if not re.search(r"(?:暂无|无).{0,4}权限", function["name"]):
            continue
        proof_line = int(function["evidence"][0]["locator"][1:])
        match_line = next(
            (
                line_no
                for line_no in range(proof_line, min(proof_line + 12, len(lines)) + 1)
                if permission_outcome.search(
                    re.sub(r"<[^>]+>|[*_`]", "", lines[line_no - 1])
                )
            ),
            None,
        )
        if match_line is None:
            continue
        quote = lines[match_line - 1].strip()
        atomics.append(
            {
                "atomic_id": f"AF-{len(atomics) + 1:03d}",
                "function_id": function["function_id"],
                "name": "展示暂无权限缺省页",
                "category": "business_action",
                "action": "展示暂无权限缺省页",
                "actor": "没有权限（角色）的用户",
                "trigger": "用户登录后",
                "preconditions": ["用户没有分配权限（角色）"],
                "inputs": [],
                "processing_rules": [quote],
                "outputs": [],
                "state_changes": [],
                "branches": ["显示暂无权限的缺省页"],
                "status": "confirmed",
                "origin": "prose_rule",
                "evidence": [
                    {
                        "source_id": "SRC-001",
                        "locator": f"L{match_line}",
                        "quote": quote,
                    }
                ],
            }
        )

    # A function needs at least one behavior for coverage, but a heading is not
    # itself a behavior. Create an explicit unresolved fallback only when no
    # action heading, table operation, interface entry, or prose action exists.
    for function in functions:
        if any(item["function_id"] == function["function_id"] for item in atomics):
            continue
        if any(
            item.get("parent_function_id") == function["function_id"]
            for item in functions
        ):
            continue
        proof = function["evidence"][0]
        atomics.append(
            {
                "atomic_id": f"AF-{len(atomics) + 1:03d}",
                "function_id": function["function_id"],
                "name": f"待拆解：{function['name']}",
                "category": "unresolved_behavior",
                "action": "待从原文确认最小可验证行为",
                "actor": "待确认",
                "trigger": "待确认",
                "preconditions": [],
                "inputs": [],
                "processing_rules": [],
                "outputs": [],
                "state_changes": [],
                "branches": ["原文仅确认功能边界，未确认最小行为"],
                "status": "unresolved",
                "origin": "function_fallback",
                "evidence": [proof],
            }
        )

    relations: list[dict[str, Any]] = []
    for unit in source_units:
        if unit.get("kind") != "reference_dependency":
            continue
        line_no = int(str(unit["locator"])[1:])
        quote = str(unit.get("quote") or "")
        source_function = owner_before(candidates, line_no)
        if source_function is not None:
            scoped_function_id = heading_to_function[source_function["line"]]
            unit["blocking_scope"]["function_id"] = scoped_function_id
            matched_atomics = [
                item["atomic_id"]
                for item in atomics
                if item.get("function_id") == scoped_function_id
                and item.get("name")
                and normalize_action_name(str(item["name"])) in quote
            ]
            if matched_atomics:
                unit["blocking_scope"]["atomic_ids"] = sorted(set(matched_atomics))
        if (
            unit.get("reference_type") != "internal_reference"
            or source_function is None
        ):
            continue

        target_name = str(unit.get("target_name") or "")
        reviewed_target = unit.get("review_target_locator")
        target_heading = next(
            (item for item in headings if f"L{item['line']}" == reviewed_target), None
        )
        if target_heading is None and target_name == "文档内同名功能":
            matches = [
                item
                for item in candidates
                if item["name"] == source_function["name"]
                and item["line"] < source_function["line"]
            ]
            target_heading = matches[-1] if matches else None
        elif target_heading is None and len(target_name) > 1 and target_name.endswith("端"):
            same_scope_headings = [
                item
                for item in headings
                if item["line"] < line_no
                and item["name"] == target_name
                and source_function["name"] in item["path"]
            ]
            if same_scope_headings:
                target_heading = same_scope_headings[-1]
            else:
                same_function_targets = [
                    item
                    for item in candidates
                    if item["name"] == source_function["name"]
                    and item["line"] < source_function["line"]
                ]
                preferred_targets = [
                    item
                    for item in same_function_targets
                    if target_name in " / ".join(item["path"])
                ]
                target_heading = (
                    (preferred_targets or same_function_targets)[-1]
                    if same_function_targets
                    else None
                )
        elif target_heading is None:
            target_matches = [
                item
                for item in headings
                if item["line"] < line_no
                and normalize_reference_target(item["name"])
                == normalize_reference_target(target_name)
            ]
            target_heading = target_matches[-1] if target_matches else None

        if target_heading is not None:
            resolved_source = heading_to_function[source_function["line"]]
            target_owner = (
                target_heading
                if target_heading["line"] in heading_to_function
                else owner_before(candidates, target_heading["line"])
            )
            resolved_target = (
                heading_to_function.get(target_owner["line"])
                if target_owner is not None
                else None
            )
            proof = {"source_id": "SRC-001", "locator": unit["locator"], "quote": quote}
            unit["status"] = "processed"
            unit["resolution_status"] = "target_located"
            unit["reference_key"] = (
                f"internal_reference:{normalize_reference_target(' / '.join(target_heading['path']))}"
            )
            unit["resolved_reference"] = {
                "source_id": resolved_source,
                "target_locator": f"L{target_heading['line']}",
            }
            if resolved_target:
                unit["resolved_reference"]["target_id"] = resolved_target
            unit["reason"] = None
            if resolved_target and resolved_source != resolved_target:
                relations.append(
                    {
                        "relation_id": f"REL-{len(relations) + 1:03d}",
                        "source_id": resolved_source,
                        "target_id": resolved_target,
                        "type": "references",
                        "note": "文档内部复用或一致性引用；继承范围由原文限定",
                        "evidence": [proof],
                    }
                )
                if "复用" in quote and "页面" in quote:
                    source_actor = next(
                        iter(
                            next(
                                item
                                for item in functions
                                if item["function_id"] == resolved_source
                            ).get("actors", [])
                        ),
                        "待确认",
                    )
                    source_end = next(
                        (
                            item["line"] - 1
                            for item in headings
                            if item["line"] > source_function["line"]
                            and item["level"] <= source_function["level"]
                        ),
                        len(lines),
                    )
                    source_section = "\n".join(
                        lines[source_function["line"] - 1 : source_end]
                    )
                    prohibited_actions = {
                        match.group(1)
                        for match in re.finditer(
                            r"不能(?:进行)?(下载原包|下载|导出|删除|上传|编辑|查看)",
                            source_section,
                        )
                    }
                    target_atomics = [
                        item
                        for item in list(atomics)
                        if item.get("function_id") == resolved_target
                        and item.get("origin") != "function_fallback"
                    ]
                    for target_atomic in target_atomics:
                        if target_atomic.get("name") in prohibited_actions:
                            continue
                        if any(
                            item.get("function_id") == resolved_source
                            and item.get("name") == target_atomic.get("name")
                            and item.get("origin") != "function_fallback"
                            for item in atomics
                        ):
                            continue
                        inherited = dict(target_atomic)
                        inherited.update(
                            {
                                "atomic_id": f"AF-{len(atomics) + 1:03d}",
                                "function_id": resolved_source,
                                "actor": source_actor,
                                "origin": "internal_reference",
                                "status": "confirmed",
                                "inherited_from_atomic_id": target_atomic.get(
                                    "atomic_id"
                                ),
                                "evidence": [*target_atomic.get("evidence", []), proof],
                            }
                        )
                        atomics.append(inherited)

    # Whole-page reuse may have replaced an unresolved leaf fallback with
    # inherited concrete behaviours. Parent functions with child functions do
    # not need a synthetic atomic node of their own.
    concrete_function_ids = {
        item["function_id"]
        for item in atomics
        if item.get("origin") != "function_fallback"
    }
    parent_function_ids = {
        item.get("parent_function_id")
        for item in functions
        if item.get("parent_function_id")
    }
    atomics = [
        item
        for item in atomics
        if not (
            item.get("origin") == "function_fallback"
            and (
                item.get("function_id") in concrete_function_ids
                or item.get("function_id") in parent_function_ids
            )
        )
    ]

    def default_atomic_id(
        function_id: str, before_line: int | None = None
    ) -> str | None:
        """Return a concrete local behavior for binding, never invent one for a parent."""
        owned = [item for item in atomics if item.get("function_id") == function_id]
        if before_line is not None:
            preceding = [
                item
                for item in owned
                if item.get("evidence")
                and str(item["evidence"][0].get("locator", "")).startswith("L")
                and int(item["evidence"][0]["locator"][1:]) <= before_line
            ]
            if preceding:
                nearest = max(
                    preceding,
                    key=lambda item: int(item["evidence"][0]["locator"][1:]),
                )
                return nearest["atomic_id"]
        return owned[0]["atomic_id"] if owned else None

    fields: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    contexts: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    excluded_occurrences: list[dict[str, Any]] = []
    validation_records: list[dict[str, Any]] = []
    for table in tables:
        parsed_rows = field_rows(table)
        if not parsed_rows:
            continue
        owner = owner_before(candidates, table["line"])
        if owner is None:
            continue
        function_id = heading_to_function[owner["line"]]
        atomic_id = default_atomic_id(function_id, table["line"])
        if atomic_id is None:
            # Tables under an aggregate heading belong to a child capability or
            # need semantic review; binding them to an invented parent action
            # would fabricate executable behavior.
            continue
        for row in parsed_rows:
            field_name = row["field_name"]
            current_type = row["type"]
            required_value = row["required"]
            description = (row["description"] or "").strip()
            validation = (row["validation"] or "").strip()
            is_action_shaped_field = (
                "类型" not in table["rows"][0]
                and required_value in {"-", None}
                and bool(re.match(r"^点击(?:[^，。；;]{0,16})后", description))
            )
            if (
                not field_name
                or field_name == "-"
                or current_type in SKIP_FIELD_TYPES
                or is_action_shaped_field
            ):
                continue
            if field_name in UI_ONLY_FIELDS:
                excluded_occurrences.append(
                    {
                        "name_as_written": field_name,
                        "function_id": function_id,
                        "locator": f"L{table['line']}",
                        "reason": "界面结构或操作列，不承载业务数据",
                    }
                )
                continue
            field_id = f"FLD-{len(fields) + 1:04d}"
            occurrence_id = f"OCC-{len(occurrences) + 1:04d}"
            required = (
                True
                if required_value == "是"
                else False
                if required_value == "否"
                else None
            )
            surface = SURFACE_BY_TYPE.get(current_type, "detail_field")
            if current_type == "字段" and (
                required is True
                or re.search(r"请输入|请选择|可修改|支持编辑|手工编辑", description)
            ):
                surface = "form_input"
            role = "input" if surface in {"query_condition", "form_input"} else "output"
            proof = {
                "source_id": "SRC-001",
                "locator": f"L{table['line']}",
                "quote": field_name,
            }
            attributes = derive_field_attributes(field_name, description, validation)
            attributes["attribute_provenance"]["required"] = (
                "explicit" if required_value in {"是", "否"} else "unresolved"
            )
            fields.append(
                {
                    "field_id": field_id,
                    "business_name": field_name,
                    "technical_name": None,
                    "business_object": owner["name"],
                    "description": description or "由需求表格提取，详细语义待复核",
                    "data_type": attributes["data_type"],
                    "format": attributes["format"],
                    "length": attributes["length"],
                    "precision": None,
                    "required": required,
                    "default_value": attributes["default_value"],
                    "enum_values": attributes["enum_values"],
                    "rules": attributes["rules"],
                    "source": "需求文档",
                    "sensitivity": attributes["sensitivity"],
                    "aliases": [],
                    "unresolved_attributes": attributes["unresolved_attributes"],
                    "attribute_provenance": attributes["attribute_provenance"],
                    "status": "inferred",
                    "evidence": [proof],
                }
            )
            occurrences.append(
                {
                    "occurrence_id": occurrence_id,
                    "field_id": field_id,
                    "name_as_written": field_name,
                    "function_id": function_id,
                    "surface": surface,
                    "role": role,
                    "evidence": [proof],
                }
            )
            contexts.append(
                {
                    "field_id": field_id,
                    "function_id": function_id,
                    "surface": surface,
                    "location": f"{owner['name']} / L{table['line']}",
                    "role": role,
                }
            )
            usages = ["query", "input"] if role == "input" else ["display", "output"]
            bindings.append(
                {
                    "atomic_id": atomic_id,
                    "field_id": field_id,
                    "usages": usages,
                    "direction": "read" if role == "input" else "write",
                    "required_here": required,
                    "condition": "对应功能执行时",
                    "rules": attributes["rules"],
                    "evidence": [proof],
                }
            )
            same_table_actions = [
                item
                for item in atomics
                if item["function_id"] == function_id
                and any(
                    evidence.get("locator") == f"L{table['line']}"
                    for evidence in item.get("evidence", [])
                )
            ]
            for action_atomic in same_table_actions:
                action_name = action_atomic["name"]
                if "查询" in action_name:
                    action_usages = (
                        ["query", "input"] if role == "input" else ["display", "output"]
                    )
                elif "重置" in action_name and role == "input":
                    action_usages = ["control", "input"]
                elif any(token in action_name for token in ("导出", "下载")):
                    action_usages = (
                        ["query", "input"] if role == "input" else ["output"]
                    )
                else:
                    continue
                bindings.append(
                    {
                        "atomic_id": action_atomic["atomic_id"],
                        "field_id": field_id,
                        "usages": action_usages,
                        "direction": "read",
                        "required_here": required if role == "input" else False,
                        "condition": f"执行{action_name}时",
                        "rules": attributes["rules"],
                        "evidence": [proof],
                    }
                )

    # Nested validation tables define concrete negative or boundary oracles.
    # Record them independently, then attach them after field normalization.
    for table in tables:
        rows = table["rows"]
        if not rows or not {"触发条件", "提示语"}.issubset(rows[0]):
            continue
        owner = owner_before(candidates, table["line"])
        if owner is None:
            continue
        function_id = heading_to_function[owner["line"]]
        trigger_index = rows[0].index("触发条件")
        prompt_index = rows[0].index("提示语")
        current_target = None
        for row in rows[1:]:
            if max(trigger_index, prompt_index) >= len(row):
                continue
            trigger, prompt = row[trigger_index].strip(), row[prompt_index].strip()
            target_match = re.search(r"(?:请输入|请选择)\s*([^，。；;]+)", prompt)
            if target_match:
                current_target = target_match.group(1).strip(" “\"”'")
            else:
                named_rule = re.match(r"^(.{2,30}?)(?:不能|格式错误)", prompt)
                if named_rule and not named_rule.group(1).startswith(("长度", "格式")):
                    current_target = named_rule.group(1).strip()
            validation_records.append(
                {
                    "function_id": function_id,
                    "field_name": current_target,
                    "trigger": trigger,
                    "expected_prompt": prompt,
                    "evidence": {
                        "source_id": "SRC-001",
                        "locator": f"L{table['line']}",
                        "quote": prompt,
                    },
                }
            )

    # Capture compact field enumerations that are expressed in prose rather
    # than field tables. Keep these as occurrences so normalization remains a
    # separate, auditable pass.
    prose_field_patterns = [
        (
            re.compile(r"(?:展示|显示)字段(?:为)?\s*[：:]\s*(.+?)(?:[。；;]|$)"),
            "list_column",
            "output",
            False,
        ),
        (
            re.compile(
                r"(?:[^，。；;：:]{0,24}(?:信息|记录))包括\s*[：:]\s*(.+?)(?:[。；;]|$)"
            ),
            "detail_field",
            "output",
            False,
        ),
        (
            re.compile(
                r"(?:(?:字段|参数)(?:名|取值)?(?:为)?|约定的)\s*[「“]([^」”]{1,30})[」”]"
            ),
            "detail_field",
            "output",
            False,
        ),
        (
            re.compile(r"筛选条件(?:只)?保留\s*(.+?)(?:[。；;]|$)"),
            "query_condition",
            "input",
            False,
        ),
        (
            re.compile(
                r"(?:增加|新增|补充)\s*([^：:。；;]{1,80}?)字段(?:[：:]|，|,|。)"
            ),
            "form_input",
            "input",
            False,
        ),
        # Form fields are often introduced as circled-number labels and have
        # their widget/required semantics on the following lines.  Inspect a
        # short local window, but require an explicit form clue so structural
        # labels such as "基本信息" or "处理流程" are not promoted.
        (
            re.compile(
                r"(?:^|\\)\s*[①②③④⑤⑥⑦⑧⑨⑩]\s*([^：:\\]{1,20})[：:].{0,160}?(?:单选|多选|输入|必填|默认|校验)"
            ),
            "form_input",
            "input",
            True,
        ),
    ]
    for line_no, line in enumerate(lines, 1):
        current_heading = owner_before(headings, line_no)
        if current_heading is not None and "非功能需求" in current_heading["path"]:
            continue
        owner = owner_before(candidates, line_no)
        if owner is None:
            continue
        function_id = heading_to_function[owner["line"]]
        atomic_id = default_atomic_id(function_id, line_no)
        if atomic_id is None:
            continue
        for pattern, surface, role, use_window in prose_field_patterns:
            if use_window and not re.search(
                r"(?:^|\\)\s*[①②③④⑤⑥⑦⑧⑨⑩]\s*[^：:\\]{1,20}[：:]", line
            ):
                continue
            search_text = (
                " ".join(lines[line_no - 1 : line_no + 2]) if use_window else line
            )
            match = pattern.search(search_text)
            if not match:
                continue
            captured = match.group(1)
            if surface == "form_input":
                captured = re.split(r"[，,](?:增加|新增|补充)", captured)[-1]
            captured = re.split(r"[，,](?=按照|按|支持|默认|并且|且)", captured)[0]
            for raw_name in split_field_enumeration(captured):
                raw_name = re.sub(r"[*_`]", "", raw_name).strip()
                raw_name = re.sub(r"^(?:增加|新增|补充)", "", raw_name).strip()
                field_name = re.sub(r"[（(].*$", "", raw_name).strip()
                is_prose_group = bool(
                    field_name.endswith("信息")
                    and re.search(
                        rf"{re.escape(field_name[:-2])}.{{0,2}}信息(?:还)?包括\s*[：:]",
                        text,
                    )
                )
                if not field_name or field_name in UI_ONLY_FIELDS or is_prose_group:
                    if field_name:
                        excluded_occurrences.append(
                            {
                                "name_as_written": field_name,
                                "function_id": function_id,
                                "locator": f"L{line_no}",
                                "reason": "正文枚举中的界面结构或字段分组，不承载最小业务数据",
                            }
                        )
                    continue
                if any(
                    item["function_id"] == function_id
                    and item["name_as_written"] == field_name
                    and item["surface"] == surface
                    and item["evidence"][0]["locator"] == f"L{line_no}"
                    for item in occurrences
                ):
                    continue
                same_line_actions = [
                    item
                    for item in atomics
                    if item["function_id"] == function_id
                    and item.get("origin") in {"prose_action", "table_action"}
                    and any(
                        evidence.get("locator") == f"L{line_no}"
                        for evidence in item.get("evidence", [])
                    )
                ]
                field_atomic_id = (
                    same_line_actions[-1]["atomic_id"]
                    if same_line_actions
                    else atomic_id
                )
                field_id = f"FLD-{len(fields) + 1:04d}"
                occurrence_id = f"OCC-{len(occurrences) + 1:04d}"
                proof = {
                    "source_id": "SRC-001",
                    "locator": f"L{line_no}",
                    "quote": field_name,
                }
                prose_description = (
                    search_text
                    if use_window
                    else raw_name
                    if raw_name != field_name
                    else "由需求正文枚举提取，详细语义待复核"
                )
                attributes = derive_field_attributes(field_name, prose_description, "")
                fields.append(
                    {
                        "field_id": field_id,
                        "business_name": field_name,
                        "technical_name": None,
                        "business_object": owner["name"],
                        "description": prose_description,
                        "data_type": attributes["data_type"],
                        "format": attributes["format"],
                        "length": attributes["length"],
                        "precision": None,
                        "required": None,
                        "default_value": attributes["default_value"],
                        "enum_values": attributes["enum_values"],
                        "rules": attributes["rules"],
                        "source": "需求文档",
                        "sensitivity": attributes["sensitivity"],
                        "aliases": [],
                        "unresolved_attributes": [
                            *attributes["unresolved_attributes"],
                            "必填性",
                        ],
                        "attribute_provenance": attributes["attribute_provenance"],
                        "status": "inferred",
                        "evidence": [proof],
                    }
                )
                occurrences.append(
                    {
                        "occurrence_id": occurrence_id,
                        "field_id": field_id,
                        "name_as_written": field_name,
                        "function_id": function_id,
                        "surface": surface,
                        "role": role,
                        "evidence": [proof],
                    }
                )
                contexts.append(
                    {
                        "field_id": field_id,
                        "function_id": function_id,
                        "surface": surface,
                        "location": f"{owner['name']} / L{line_no}",
                        "role": role,
                    }
                )
                usages = (
                    ["query", "input"] if role == "input" else ["display", "output"]
                )
                bindings.append(
                    {
                        "atomic_id": field_atomic_id,
                        "field_id": field_id,
                        "usages": usages,
                        "direction": "read" if role == "input" else "write",
                        "required_here": None,
                        "condition": "对应功能执行时",
                        "rules": [],
                        "evidence": [proof],
                    }
                )

    # A validation prompt can be the only place where a composite field's
    # independently validated subfields are named. Promote such explicit names
    # into input occurrences rather than hiding them as unresolved prose.
    function_by_id = {item["function_id"]: item for item in functions}
    for record in validation_records:
        field_name = record["field_name"]
        if not field_name or any(
            item["function_id"] == record["function_id"]
            and item["name_as_written"] == field_name
            and item["role"] == "input"
            for item in occurrences
        ):
            continue
        function = function_by_id[record["function_id"]]
        line_no = int(record["evidence"]["locator"][1:])
        atomic_id = default_atomic_id(function["function_id"], line_no)
        if atomic_id is None:
            continue
        field_id = f"FLD-{len(fields) + 1:04d}"
        occurrence_id = f"OCC-{len(occurrences) + 1:04d}"
        proof = {
            "source_id": "SRC-001",
            "locator": record["evidence"]["locator"],
            "quote": field_name,
        }
        attributes = derive_field_attributes(field_name, record["expected_prompt"], "")
        fields.append(
            {
                "field_id": field_id,
                "business_name": field_name,
                "technical_name": None,
                "business_object": function["name"],
                "description": "由验证提示中明确命名的独立输入项",
                "data_type": attributes["data_type"],
                "format": attributes["format"],
                "length": attributes["length"],
                "precision": None,
                "required": True if "空" in record["trigger"] else None,
                "default_value": attributes["default_value"],
                "enum_values": attributes["enum_values"],
                "rules": [],
                "source": "需求文档",
                "sensitivity": attributes["sensitivity"],
                "aliases": [],
                "unresolved_attributes": attributes["unresolved_attributes"],
                "attribute_provenance": {
                    **attributes["attribute_provenance"],
                    "required": "derived"
                    if "空" in record["trigger"]
                    else "unresolved",
                },
                "status": "inferred",
                "evidence": [proof],
            }
        )
        occurrences.append(
            {
                "occurrence_id": occurrence_id,
                "field_id": field_id,
                "name_as_written": field_name,
                "function_id": function["function_id"],
                "surface": "form_input",
                "role": "input",
                "evidence": [proof],
            }
        )
        contexts.append(
            {
                "field_id": field_id,
                "function_id": function["function_id"],
                "surface": "form_input",
                "location": f"{function['name']} / {record['evidence']['locator']}",
                "role": "input",
            }
        )
        bindings.append(
            {
                "atomic_id": atomic_id,
                "field_id": field_id,
                "usages": ["input", "validation"],
                "direction": "read",
                "required_here": True if "空" in record["trigger"] else None,
                "condition": "执行字段校验时",
                "rules": [],
                "evidence": [proof],
            }
        )

    # Normalize only within the same function and direction context. This
    # safely collapses repeated table/prose occurrences while preventing the
    # classic error of merging an input field with a masked/display field.
    raw_field_count = len(fields)
    raw_fields = {item["field_id"]: item for item in fields}
    normalization_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for occurrence in occurrences:
        direction_group = "input" if occurrence["role"] == "input" else "output"
        key = (
            occurrence["function_id"],
            occurrence["name_as_written"],
            direction_group,
        )
        normalization_groups.setdefault(key, []).append(occurrence)

    normalized_fields: list[dict[str, Any]] = []
    old_to_new: dict[str, str] = {}
    normalization_decisions: list[dict[str, Any]] = []
    normalization_conflicts: list[dict[str, Any]] = []
    for index, (key, group) in enumerate(normalization_groups.items(), 1):
        new_id = f"FLD-{index:04d}"
        source_fields = [raw_fields[item["field_id"]] for item in group]
        canonical = dict(source_fields[0])
        canonical["field_id"] = new_id
        canonical["evidence"] = []
        canonical["rules"] = []
        for source_field in source_fields:
            old_to_new[source_field["field_id"]] = new_id
            for evidence in source_field.get("evidence", []):
                if evidence not in canonical["evidence"]:
                    canonical["evidence"].append(evidence)
            for rule in source_field.get("rules", []):
                if rule not in canonical["rules"]:
                    canonical["rules"].append(rule)
        required_values = {
            item.get("required")
            for item in source_fields
            if item.get("required") is not None
        }
        if len(required_values) == 1:
            canonical["required"] = next(iter(required_values))
        elif len(required_values) > 1:
            canonical["required"] = None
            canonical["attribute_provenance"] = dict(canonical["attribute_provenance"])
            canonical["attribute_provenance"]["required"] = "unresolved"
            normalization_conflicts.append(
                {
                    "field_id": new_id,
                    "attribute": "required",
                    "values": sorted(required_values),
                    "reason": "同一功能和方向上下文中的必填定义冲突",
                }
            )
        normalized_fields.append(canonical)
        normalization_decisions.append(
            {
                "field_id": new_id,
                "function_id": key[0],
                "business_name": key[1],
                "direction_group": key[2],
                "occurrence_ids": [item["occurrence_id"] for item in group],
                "decision": "merge" if len(group) > 1 else "keep",
                "basis": "同一功能、同名且同输入/输出方向",
            }
        )

    for occurrence in occurrences:
        occurrence["field_id"] = old_to_new[occurrence["field_id"]]
    fields = normalized_fields

    normalized_contexts: list[dict[str, Any]] = []
    seen_contexts: set[tuple[Any, ...]] = set()
    for context in contexts:
        context["field_id"] = old_to_new[context["field_id"]]
        key = (
            context["field_id"],
            context["function_id"],
            context["surface"],
            context["location"],
            context["role"],
        )
        if key not in seen_contexts:
            seen_contexts.add(key)
            normalized_contexts.append(context)
    contexts = normalized_contexts

    normalized_bindings: list[dict[str, Any]] = []
    binding_index: dict[tuple[str, str], dict[str, Any]] = {}
    for binding in bindings:
        binding["field_id"] = old_to_new[binding["field_id"]]
        key = (binding["atomic_id"], binding["field_id"])
        existing = binding_index.get(key)
        if existing is None:
            binding_index[key] = binding
            normalized_bindings.append(binding)
            continue
        existing["usages"] = list(
            dict.fromkeys([*existing["usages"], *binding["usages"]])
        )
        existing["rules"] = list(
            dict.fromkeys([*existing.get("rules", []), *binding.get("rules", [])])
        )
        for evidence in binding.get("evidence", []):
            if evidence not in existing["evidence"]:
                existing["evidence"].append(evidence)
        if existing["direction"] != binding["direction"]:
            existing["direction"] = "read_write"
        if existing.get("required_here") != binding.get("required_here"):
            existing["required_here"] = None
    bindings = normalized_bindings

    unresolved_validations: list[dict[str, Any]] = []
    normalized_field_by_id = {item["field_id"]: item for item in fields}
    for record in validation_records:
        targets = [
            item
            for item in normalization_decisions
            if item["function_id"] == record["function_id"]
            and item["business_name"] == record["field_name"]
            and item["direction_group"] == "input"
        ]
        if not targets:
            unresolved_validations.append(record)
            continue
        rule = f"{record['trigger']} => {record['expected_prompt']}"
        for target in targets:
            field = normalized_field_by_id[target["field_id"]]
            if rule not in field["rules"]:
                field["rules"].append(rule)
            if record["evidence"] not in field["evidence"]:
                field["evidence"].append(record["evidence"])
            if "空" in record["trigger"]:
                field["required"] = True
                field["attribute_provenance"]["required"] = "derived"
            for binding in bindings:
                if binding["field_id"] != field["field_id"]:
                    continue
                if rule not in binding["rules"]:
                    binding["rules"].append(rule)
                if record["evidence"] not in binding["evidence"]:
                    binding["evidence"].append(record["evidence"])

    cross_context_candidates: list[dict[str, Any]] = []
    fields_by_business_key: dict[tuple[str, str], dict[str, list[str]]] = {}
    for decision in normalization_decisions:
        key = (decision["function_id"], decision["business_name"])
        fields_by_business_key.setdefault(key, {}).setdefault(
            decision["direction_group"], []
        ).append(decision["field_id"])
    for (function_id, business_name), directions in fields_by_business_key.items():
        if directions.get("input") and directions.get("output"):
            cross_context_candidates.append(
                {
                    "function_id": function_id,
                    "business_name": business_name,
                    "input_field_ids": directions["input"],
                    "output_field_ids": directions["output"],
                    "decision_required": "确认回显、脱敏、派生或互不相关后再建立字段血缘",
                }
            )

    bound_atomics = {item["atomic_id"] for item in bindings}
    fieldless = [
        {
            "atomic_id": item["atomic_id"],
            "reason": "本轮全文发现阶段未从同章节表格绑定字段，需语义复核",
        }
        for item in atomics
        if item["atomic_id"] not in bound_atomics
    ]
    relevant = [unit for unit in source_units if unit["relevant"]]
    unavailable = sum(unit["status"] == "unavailable" for unit in relevant)
    review_required = sum(unit["status"] == "review_required" for unit in relevant)
    reference_units = [
        unit for unit in source_units if unit.get("kind") == "reference_dependency"
    ]
    reference_summary = {
        "occurrence_count": len(reference_units),
        "distinct_target_count": len(
            {unit["reference_key"] for unit in reference_units}
        ),
        "by_type": {
            kind: sum(unit.get("reference_type") == kind for unit in reference_units)
            for kind in sorted(REFERENCE_TYPES)
        },
        "by_status": {
            status: sum(unit.get("status") == status for unit in reference_units)
            for status in ("processed", "review_required", "unavailable")
        },
    }
    audit_errors = ["候选实体语义复核未完成"]
    if source_review is None:
        audit_errors.insert(
            0, "未提供 qa-requirement-review 资料依赖评审，不能判定项目资料完整性"
        )
    elif unavailable or review_required:
        audit_errors.insert(0, "资料依赖评审存在未解决 Finding")
    data = {
        "meta": {
            "document": options.source.name,
            "generated_at": "2026-09-06T00:00:00+08:00",
            "schema_version": "1.1",
            "scope": "full",
            "artifact_kind": "full_discovery_draft",
        },
        "sources": [
            {
                "source_id": "SRC-001",
                "file": str(options.source),
                "type": "requirement",
                "version": "V1.1",
                "priority": 1,
            }
        ],
        "source_dependency_review": (
            {
                "artifact_kind": source_review.get("meta", {}).get("artifact_kind"),
                "sha256": content_sha256(
                    options.source_review.read_text(encoding="utf-8")
                ),
                "summary": source_review.get("summary", {}),
                "findings": source_review.get("findings", []),
            }
            if source_review is not None
            else None
        ),
        "source_units": source_units,
        "modules": [
            {
                "module_id": f"MOD-{index:03d}",
                "name": item["name"],
                "locator": f"L{item['line']}",
            }
            for index, item in enumerate(module_candidates, 1)
        ],
        "candidate_inventory": {
            "module_headings": len(module_candidates),
            "function_headings": len(candidates),
            "atomic_headings": len(atomic_candidates),
            "table_atomic_actions": len(table_atomic_decisions),
            "prose_atomic_actions": len(prose_atomic_decisions),
            "interface_atomic_actions": len(interface_atomic_decisions),
            "excluded_structural_headings": len(excluded_headings),
            "nonfunctional_headings": len(NON_FUNCTIONAL),
        },
        "classification_decisions": [
            *[
                {
                    "locator": f"L{item['line']}",
                    "heading": item["name"],
                    "decision": "module",
                    "reason": "功能范围内的二级标题",
                }
                for item in module_candidates
            ],
            *[
                {
                    "locator": f"L{item['line']}",
                    "heading": item["name"],
                    "decision": "function",
                    "reason": "模块下首层业务标题或独立二级功能",
                }
                for item in candidates
            ],
            *[
                {
                    "locator": f"L{item['line']}",
                    "heading": item["name"],
                    "decision": "atomic_function",
                    "reason": "功能点下更细粒度的业务行为或业务子项",
                }
                for item in atomic_candidates
            ],
            *table_atomic_decisions,
            *prose_atomic_decisions,
            *interface_atomic_decisions,
            *[
                {
                    "locator": f"L{entry['heading']['line']}",
                    "heading": entry["heading"]["name"],
                    "decision": "exclude",
                    "reason": entry["reason"],
                }
                for entry in excluded_headings
            ],
        ],
        "functions": functions,
        "atomic_functions": atomics,
        "business_fields": fields,
        "field_occurrences": occurrences,
        "normalization_decisions": normalization_decisions,
        "validation_rules": validation_records,
        "field_contexts": contexts,
        "field_bindings": bindings,
        "field_relations": [],
        "excluded_field_occurrences": excluded_occurrences,
        "relations": relations,
        "gaps": {
            "unbound_fields": [],
            "fieldless_atomic_functions": fieldless,
            "unresolved_references": [
                {
                    "unit_id": unit["unit_id"],
                    "reference_type": unit.get("reference_type"),
                    "target_name": unit.get("target_name"),
                    "locator": unit["locator"],
                    "blocking_scope": unit.get("blocking_scope"),
                    "reason": unit["reason"],
                }
                for unit in relevant
                if unit.get("kind") == "reference_dependency"
                and unit["status"] in {"review_required", "unavailable"}
            ],
            "unresolved_validation_rules": unresolved_validations,
            "conflicts": normalization_conflicts,
        },
        "coverage": {
            "function_count": len(functions),
            "atomic_function_count": len(atomics),
            "business_field_count": len(fields),
            "field_occurrence_count": len(occurrences),
            "raw_field_candidate_count": raw_field_count,
            "bound_field_count": len({item["field_id"] for item in bindings}),
            "orphan_count": len(fieldless),
            "evidence_coverage_percent": 100,
            "reference_summary": reference_summary,
            "source_coverage": {
                "claim": "full",
                "relevant_units": len(relevant),
                "processed_units": len(relevant) - unavailable - review_required,
                "review_required_units": review_required,
                "skipped_units": 0,
                "unavailable_units": unavailable,
                "uncovered_ranges": [],
            },
        },
        "audit": {
            "verdict": "FAIL",
            "downstream_eligible": False,
            "semantic_review": {
                "status": "REVIEW_REQUIRED",
                "cross_context_candidates": cross_context_candidates,
            },
            "errors": audit_errors,
            "warnings": [
                "标题、表格和正文候选已做保守归一化；跨上下文字段仍待语义复核"
            ],
        },
    }
    options.out.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
