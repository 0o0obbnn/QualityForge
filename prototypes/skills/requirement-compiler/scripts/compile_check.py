#!/usr/bin/env python3
"""需求编译融合义务检查器。"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys

DEFAULT_CONFIDENCE_VALUES = {0.5, 0.9, 0.95, 1.0, 0.0}
SOURCE_AVAILABILITY = {
    "AVAILABLE",
    "NOT_PROVIDED",
    "NOT_APPLICABLE",
    "UNREADABLE",
    "EXPECTED_MISSING",
}


def finding(code, target, msg, severity="REJECT"):
    return {"code": code, "severity": severity, "target": target, "msg": msg}


def _source_root(value):
    return str(value).split("§")[0].split(":")[0].strip()


def _normalise_sources(raw_sources):
    sources = []
    findings = []
    if not isinstance(raw_sources, list):
        return [], [
            finding(
                "INVALID_SOURCE_MANIFEST",
                "declared_sources",
                "declared_sources 必须是数组",
            )
        ]
    for index, raw in enumerate(raw_sources):
        if isinstance(raw, str):
            source_id = raw.strip()
            availability = "AVAILABLE"
        elif isinstance(raw, dict):
            raw_source_id = raw.get("source_id", "")
            source_id = raw_source_id.strip() if isinstance(raw_source_id, str) else ""
            availability = raw.get("availability", "AVAILABLE")
        else:
            findings.append(
                finding(
                    "INVALID_SOURCE_ENTRY",
                    f"declared_sources[{index}]",
                    "source 条目必须是字符串或对象",
                )
            )
            continue
        if not source_id:
            findings.append(
                finding(
                    "MISSING_SOURCE_ID",
                    f"declared_sources[{index}]",
                    "source_id 为必填项",
                )
            )
            continue
        if not isinstance(availability, str) or availability not in SOURCE_AVAILABILITY:
            findings.append(
                finding(
                    "INVALID_SOURCE_AVAILABILITY",
                    source_id,
                    f"不支持 availability {availability!r}",
                )
            )
            continue
        sources.append({"source_id": source_id, "availability": availability})
    return sources, findings


def check_compilation(packet):
    findings = []
    if not isinstance(packet, dict):
        packet = {}
        findings.append(
            finding(
                "INVALID_COMPILATION_PACKET",
                "root",
                "编译 packet 根节点必须是对象",
            )
        )
    ir_draft = packet.get("ir_draft", {})
    if not isinstance(ir_draft, dict):
        findings.append(
            finding("INVALID_IR_DRAFT", "ir_draft", "ir_draft 必须是对象")
        )
        ir_draft = {}
    sources, source_findings = _normalise_sources(packet.get("declared_sources", []))
    findings.extend(source_findings)
    source_ids = [source["source_id"] for source in sources]
    duplicate_source_ids = sorted(
        {item for item in source_ids if source_ids.count(item) > 1}
    )
    for source_id in duplicate_source_ids:
        findings.append(
            finding(
                "DUPLICATE_SOURCE_ID",
                source_id,
                "source_id 在 declared_sources 中只能出现一次",
            )
        )
    declared_sources = {source["source_id"] for source in sources}
    available_sources = {
        source["source_id"]
        for source in sources
        if source["availability"] == "AVAILABLE"
    }
    contributing_sources = set()

    if not sources:
        findings.append(
            finding(
                "EMPTY_SOURCE_MANIFEST",
                "declared_sources",
                "至少需要声明一个 source",
            )
        )
    if not isinstance(ir_draft, dict) or not (ir_draft.get("requirements") or []):
        findings.append(
            finding(
                "EMPTY_IR_DRAFT",
                "ir_draft.requirements",
                "编译出的 IR 必须包含至少一条 requirement",
            )
        )

    for source in sources:
        if source["availability"] in {"NOT_PROVIDED", "UNREADABLE", "EXPECTED_MISSING"}:
            findings.append(
                finding(
                    "SOURCE_UNAVAILABLE",
                    source["source_id"],
                    f"source 可用性为 {source['availability']}；编译置信度受损",
                    severity="REVIEW",
                )
            )

    # 收集全部 source_trace 值 + 检查凭空捏造
    for cls in ("requirements", "business_rules", "constraints", "entities"):
        raw_items = ir_draft.get(cls, []) or []
        if not isinstance(raw_items, list):
            findings.append(
                finding(
                    "INVALID_IR_COLLECTION",
                    f"ir_draft.{cls}",
                    f"{cls} 必须是数组",
                )
            )
            continue
        for index, item in enumerate(raw_items):
            if not isinstance(item, dict):
                findings.append(
                    finding(
                        "INVALID_IR_ITEM",
                        f"ir_draft.{cls}[{index}]",
                        "编译出的条目必须是对象",
                    )
                )
                continue
            iid = (
                item.get(f"{cls[:-1]}_id")
                or item.get("entity_id")
                or item.get("rule_id")
                or "?"
            )
            st = item.get("source_trace", "")
            if st:
                root = _source_root(st)
                contributing_sources.add(root)
                # 检查凭空捏造：source_trace 根必须在 declared_sources 中
                if declared_sources and root not in declared_sources:
                    findings.append(
                        finding(
                            "FABRICATED_SOURCE_TRACE",
                            str(iid),
                            f"source_trace {st!r} 的根 {root!r} 不在声明的 sources 中",
                        )
                    )
                elif root not in available_sources:
                    findings.append(
                        finding(
                            "SOURCE_TRACE_UNAVAILABLE",
                            str(iid),
                            f"source_trace {st!r} 指向的 source 不是 AVAILABLE 状态",
                        )
                    )
            else:
                findings.append(
                    finding(
                        "MISSING_SOURCE_TRACE",
                        str(iid),
                        "编译出的元素缺少 source_trace",
                    )
                )
            # 检查默认置信度
            conf = item.get("confidence")
            if (
                conf is not None
                and conf in DEFAULT_CONFIDENCE_VALUES
                and not item.get("confidence_rationale")
            ):
                findings.append(
                    finding(
                        "DEFAULT_CONFIDENCE",
                        str(iid),
                        f"confidence {conf} 疑似默认值；需要补充 rationale",
                    )
                )

    # 检查所有 source 是否都有贡献
    for src in sorted(available_sources):
        if src not in contributing_sources:
            findings.append(
                finding(
                    "SOURCE_SILENTLY_DROPPED",
                    src,
                    f"声明的 source {src!r} 对 IR 没有任何贡献",
                )
            )

    # 检查冲突是否给出 >= 2 个版本
    for cls in ("requirements", "business_rules"):
        raw_items = ir_draft.get(cls, []) or []
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            iid = item.get("req_id") or item.get("rule_id") or "?"
            if item.get("conflict"):
                refs = item.get("conflict_refs", []) or []
                distinct_refs = {str(ref) for ref in refs}
                if len(distinct_refs) < 2:
                    findings.append(
                        finding(
                            "CONFLICT_SINGLE_VERSION",
                            str(iid),
                            f"conflict=true 但只有 {len(distinct_refs)} 个不同的 source 版本；需要 >=2",
                        )
                    )
                for ref in sorted(distinct_refs):
                    root = _source_root(ref)
                    if root not in available_sources:
                        findings.append(
                            finding(
                                "CONFLICT_REF_NOT_AVAILABLE",
                                str(iid),
                                f"冲突引用 {ref!r} 未绑定到 AVAILABLE 状态的声明 source",
                            )
                        )

    has_reject = any(f["severity"] == "REJECT" for f in findings)
    has_review = any(f["severity"] == "REVIEW" for f in findings)
    verdict = "REJECT" if has_reject else ("PASS_WITH_REVIEW" if has_review else "PASS")
    return {
        "skill": "01",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "total_findings": len(findings),
        "findings": findings,
        "verdict": verdict,
        "routing": {
            "PASS": "IR 草稿可进入校验",
            "PASS_WITH_REVIEW": "IR 草稿挂起，等待 source 完整性评审",
            "REJECT": "重新编译",
        }[verdict],
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--packet", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        with open(args.packet, encoding="utf-8") as handle:
            packet = json.load(handle)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"读取输入失败：{e}"}), file=sys.stderr)
        return 3
    result = check_compilation(packet)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    try:
        if args.out:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(out)
        else:
            print(out)
    except OSError as e:
        print(json.dumps({"error": f"写入输出失败：{e}"}), file=sys.stderr)
        return 3
    return {"PASS": 0, "PASS_WITH_REVIEW": 1, "REJECT": 2}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
