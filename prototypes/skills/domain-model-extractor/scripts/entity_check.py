#!/usr/bin/env python3
"""确定性领域模型实体抽取检查器。"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from collections import Counter


ENTITY_ID_RE = re.compile(r"^ENT-[A-Z]+-\d{3,}$")


def finding(code, target, msg):
    return {"code": code, "severity": "REJECT", "target": target, "msg": msg}


def check_entities(packet):
    findings = []
    if not isinstance(packet, dict):
        packet = {}
        findings.append(
            finding("INVALID_ENTITY_PACKET", "root", "packet 根节点必须是对象")
        )

    raw_entities = packet.get("entities", []) or []
    if not isinstance(raw_entities, list):
        findings.append(
            finding(
                "INVALID_ENTITY_COLLECTION", "entities", "entities 必须是数组"
            )
        )
        raw_entities = []

    entities = []
    for index, entity in enumerate(raw_entities):
        if not isinstance(entity, dict):
            findings.append(
                finding(
                    "INVALID_ENTITY", f"entities[{index}]", "entity 必须是对象"
                )
            )
        else:
            entities.append(entity)

    if not raw_entities:
        findings.append(
            finding("EMPTY_ENTITY_SET", "entities", "至少需要一个 entity")
        )

    ids = [entity.get("entity_id") for entity in entities]
    id_counts = Counter(item for item in ids if isinstance(item, str) and item)
    entity_id_set = set(id_counts)
    for entity_id in sorted(item for item, count in id_counts.items() if count > 1):
        findings.append(
            finding(
                "DUPLICATE_ENTITY_ID", entity_id, "entity_id 出现了多次"
            )
        )

    for index, entity in enumerate(entities):
        entity_id = entity.get("entity_id")
        target = (
            entity_id
            if isinstance(entity_id, str) and entity_id
            else f"entities[{index}]"
        )
        if not isinstance(entity_id, str) or not entity_id:
            findings.append(
                finding(
                    "MISSING_ENTITY_ID", target, "entity_id 必须是非空字符串"
                )
            )
        elif not ENTITY_ID_RE.fullmatch(entity_id):
            findings.append(
                finding(
                    "MALFORMED_ENTITY_ID", entity_id, "entity_id 必须形如 ENT-XXX-NNN"
                )
            )

        name = entity.get("name")
        if not isinstance(name, str) or not name.strip():
            findings.append(
                finding(
                    "MISSING_ENTITY_NAME",
                    target,
                    "entity 名称必须是非空字符串",
                )
            )

        raw_fields = entity.get("fields", []) or []
        if not isinstance(raw_fields, list):
            findings.append(
                finding("INVALID_FIELD_COLLECTION", target, "fields 必须是数组")
            )
            continue
        if not raw_fields:
            findings.append(
                finding(
                    "EMPTY_ENTITY_FIELDS",
                    target,
                    "entity 必须声明至少一个 field",
                )
            )
            continue

        fields = []
        for field_index, field in enumerate(raw_fields):
            if not isinstance(field, dict):
                findings.append(
                    finding(
                        "INVALID_ENTITY_FIELD",
                        f"{target}.fields[{field_index}]",
                        "field 必须是对象",
                    )
                )
            else:
                fields.append((field_index, field))

        field_names = [field.get("name") for _, field in fields]
        field_counts = Counter(
            item for item in field_names if isinstance(item, str) and item.strip()
        )
        for field_name in sorted(
            item for item, count in field_counts.items() if count > 1
        ):
            findings.append(
                finding(
                    "DUPLICATE_FIELD_NAME",
                    f"{target}.{field_name}",
                    "field 名称出现了多次",
                )
            )

        for field_index, field in fields:
            field_name = field.get("name")
            field_target = (
                f"{target}.{field_name}"
                if isinstance(field_name, str) and field_name.strip()
                else f"{target}.fields[{field_index}]"
            )
            if not isinstance(field_name, str) or not field_name.strip():
                findings.append(
                    finding(
                        "MISSING_FIELD_NAME",
                        field_target,
                        "field 名称必须是非空字符串",
                    )
                )
            field_type = field.get("type")
            if (
                not isinstance(field_type, str)
                or not field_type.strip()
                or field_type.strip().lower() == "unknown"
            ):
                findings.append(
                    finding(
                        "UNTYPED_FIELD",
                        field_target,
                        "field 类型必须是非空的已知字符串",
                    )
                )

            reference_keys = [
                key for key in ("references", "fk_reference") if key in field
            ]
            if len(reference_keys) > 1:
                findings.append(
                    finding(
                        "AMBIGUOUS_ENTITY_REF",
                        field_target,
                        "references 与 fk_reference 只能用其一，不得同时使用",
                    )
                )
            for reference_key in reference_keys:
                reference = field.get(reference_key)
                if not isinstance(reference, str) or not reference.strip():
                    findings.append(
                        finding(
                            "INVALID_ENTITY_REF",
                            field_target,
                            f"{reference_key} 必须是非空字符串",
                        )
                    )
                elif reference not in entity_id_set:
                    findings.append(
                        finding(
                            "DANGLING_ENTITY_REF",
                            field_target,
                            f"{reference_key} {reference!r} 未声明",
                        )
                    )

    verdict = "REJECT" if findings else "PASS"
    return {
        "skill": "03",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "total_entities": len(entities),
        "total_findings": len(findings),
        "findings": findings,
        "verdict": verdict,
        "routing": "PASS -> 实体可进入融合；REJECT -> 重新抽取被标记的实体",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    try:
        with open(args.packet, encoding="utf-8") as handle:
            packet = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": f"输入错误：{exc}"}), file=sys.stderr)
        return 3
    result = check_entities(packet)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    try:
        if args.out:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(output)
        else:
            print(output)
    except OSError as exc:
        print(json.dumps({"error": f"输出错误：{exc}"}), file=sys.stderr)
        return 3
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
