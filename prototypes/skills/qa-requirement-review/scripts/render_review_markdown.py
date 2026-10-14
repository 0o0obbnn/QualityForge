#!/usr/bin/env python3
"""Render a human-readable report from the canonical QA review JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def esc(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render requirement quality review Markdown")
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.review.read_text(encoding="utf-8"))
    meta, audit = data.get("meta", {}), data.get("audit", {})
    findings = data.get("findings", [])
    requirements = data.get("requirements", [])
    points = data.get("test_points", [])
    coverage = data.get("coverage", {}).get("source_coverage", {})
    lines = [
        f"# {esc(data.get('review_id'))} · 需求质量评审报告",
        "",
        f"> 生命周期状态：{esc(meta.get('lifecycle_status'))} · 验收结论：{esc(audit.get('verdict'))} · 下游可用：{str(bool(audit.get('downstream_eligible'))).lower()}",
        "",
    ]
    if not audit.get("downstream_eligible"):
        lines += ["> **非正式下游基线。** 该产物仍需评审、澄清或补齐来源。", ""]
    lines += [
        "## 摘要", "",
        f"- 需求条目：{len(requirements)}",
        f"- Findings：{len(findings)}",
        f"- 测试点：{len(points)}",
        f"- 来源覆盖：{coverage.get('processed_units', 0)}/{coverage.get('relevant_units', 0)}，待语义评审 {coverage.get('review_required_units', 0)}，跳过 {coverage.get('skipped_units', 0)}，不可用 {coverage.get('unavailable_units', 0)}",
        f"- 来源单元处置：{data.get('coverage', {}).get('source_unit_disposition_count', 0)}，未完成或不可用 {data.get('coverage', {}).get('unresolved_source_unit_count', 0)}",
        "", "## 六维总体评估", "",
        "| 维度 | 状态 | 理由 |", "|---|---|---|",
    ]
    for item in data.get("assessments", []):
        lines.append(f"| {esc(item.get('dimension'))} | {esc(item.get('status'))} | {esc(item.get('rationale'))} |")
    per_requirement: dict[str, list[dict]] = {}
    for assessment in data.get("requirement_assessments", []):
        per_requirement.setdefault(assessment.get("requirement_id"), []).append(assessment)
    lines += ["", "## 逐需求评审工作队列", "", "| 需求 ID | 标题 | 六维完成度 | 图谱追踪 | 来源 |", "|---|---|---:|---|---|"]
    for requirement in requirements:
        assessments = per_requirement.get(requirement.get("requirement_id"), [])
        completed = sum(item.get("status") != "NOT_REVIEWED" for item in assessments)
        graph_refs = [*requirement.get("function_refs", []), *requirement.get("atomic_refs", [])]
        source_refs = [f"{item.get('source_id')}:{item.get('locator')}" for item in requirement.get("source_refs", []) if isinstance(item, dict)]
        lines.append(f"| {esc(requirement.get('requirement_id'))} | {esc(requirement.get('title'))} | {completed}/6 | {esc(', '.join(graph_refs))} | {esc(', '.join(source_refs))} |")
    lines += ["", "## 问题与待澄清项", ""]
    if findings:
        for item in findings:
            lines += [
                f"### {esc(item.get('finding_id'))} · {esc(item.get('code'))}", "",
                f"- 严重度：{esc(item.get('severity'))}",
                f"- 证据类型：{esc(item.get('evidence_type'))}",
                f"- 需求：{', '.join(map(esc, item.get('requirement_ids', [])))}",
                f"- 证据：{esc(item.get('evidence'))}",
                f"- 问题：{esc(item.get('question'))}",
                f"- 建议：{esc(item.get('recommendation'))}", "",
            ]
    else:
        lines += ["当前没有已登记 finding。若评审状态仍为 NOT_RUN，这不代表需求没有问题。", ""]
    lines += ["## 测试分析入口", "", "| ID | 需求 | 类别 | 目标 | 就绪度 |", "|---|---|---|---|---|"]
    for item in points:
        lines.append(f"| {esc(item.get('test_point_id'))} | {esc(item.get('requirement_id'))} | {esc(item.get('category'))} | {esc(item.get('objective'))} | {esc(item.get('readiness'))} |")
    if not points:
        lines.append("| - | - | - | 尚未生成测试点 | blocked |")
    lines += ["", "## 验收错误", ""]
    lines += [f"- {esc(value)}" for value in audit.get("errors", [])] or ["- 无"]
    lines += ["", "## 验收警告", ""]
    lines += [f"- {esc(value)}" for value in audit.get("warnings", [])] or ["- 无"]
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
