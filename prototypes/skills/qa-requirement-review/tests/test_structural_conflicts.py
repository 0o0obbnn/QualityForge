from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "analyze_structural_conflicts.py"

SOURCE = """# 需求

## 校验规则

①文件名第1～9位必须为上报机构的组织机构代码。

## 错误提示

①文件名第1～9位必须为上报机构的组织机构代码或者法人标识代码。

## 性能

- 故障恢复时间（RTO）：≤15分钟
- 容灾恢复：RTO ≤30分钟，RPO ≤10分钟
- 平均响应时间：≤500ms

## 字段

处理状态选项为：等待处理、正在处理。
"""


def run(source_text: str, mapping: dict, review_override: dict | None = None) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        source, review_path, mapping_path, out = (
            base / "doc.md",
            base / "review.json",
            base / "mapping.json",
            base / "result.json",
        )
        source.write_text(source_text, encoding="utf-8")
        review = review_override or {
                    "meta": {"lifecycle_status": "REVIEW_REQUIRED"},
                    "source_ids": ["SRC-001"],
                    "requirements": [{
                        "requirement_id": "REQ-1",
                        "title": "需求",
                        "source_refs": [{"source_id": "SRC-001", "locator": "L1", "quote": "需求"}],
                    }],
                    "requirement_assessments": [{
                        "assessment_id": "ASM-1",
                        "requirement_id": "REQ-1",
                        "dimension": "consistency",
                        "status": "NOT_REVIEWED",
                        "finding_ids": [],
                    }],
                    "assessments": [
                        {
                            "dimension": "consistency",
                            "status": "NOT_REVIEWED",
                            "finding_ids": [],
                        }
                    ],
                    "findings": [],
                }
        review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
        mapping_path.write_text(
            json.dumps(mapping, ensure_ascii=False), encoding="utf-8"
        )
        subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--review",
                str(review_path),
                "--mapping",
                str(mapping_path),
                "--source",
                str(source),
                "--out",
                str(out),
            ],
            check=True,
        )
        return json.loads(out.read_text(encoding="utf-8"))


class StructuralConflictTests(unittest.TestCase):
    def test_anchor_definition_conflict_is_detected_with_both_quotes(self) -> None:
        result = run(SOURCE, {"business_fields": []})
        conflict = next(
            item
            for item in result["findings"]
            if item["code"] == "INTRA_DOCUMENT_CONFLICT"
            and item["conflict_kind"] == "anchor_definition"
        )
        self.assertEqual(conflict["severity"], "REJECT")
        self.assertEqual(conflict["certainty"], "risk")
        self.assertEqual(conflict["origin"], "deterministic_candidate")
        self.assertEqual(conflict["evidence_type"], "CONFLICT")
        self.assertIn("组织机构代码", conflict["evidence"])
        self.assertIn("法人标识代码", conflict["evidence"])

    def test_metric_conflict_detects_rto_value_mismatch(self) -> None:
        result = run(SOURCE, {"business_fields": []})
        keys = [
            item["question"]
            for item in result["findings"]
            if item["conflict_kind"] == "metric_value"
        ]
        self.assertTrue(any("RTO" in question for question in keys), keys)

    def test_field_enum_conflict_across_entities(self) -> None:
        mapping = {
            "business_fields": [
                {
                    "field_id": "FLD-1",
                    "business_name": "处理状态",
                    "enum_values": ["等待处理", "正在处理"],
                    "evidence": [{"locator": "L15", "quote": "处理状态"}],
                },
                {
                    "field_id": "FLD-2",
                    "business_name": "处理状态",
                    "enum_values": ["等待处理", "正在处理", "处理完毕"],
                    "evidence": [{"locator": "L18", "quote": "处理状态"}],
                },
            ]
        }
        result = run("# 空文档\n", mapping)
        conflict = next(
            item for item in result["findings"] if item["conflict_kind"] == "field_enum"
        )
        self.assertIn("处理状态", conflict["question"])
        self.assertEqual(conflict["affected_test_dimensions"], ["field_validation"])

    def test_consistent_document_produces_no_conflict(self) -> None:
        source = "# 需求\n\n文件名第1～2位必须为机构代码。\n\n另一处说明：文件名第1～2位必须为机构代码。\n"
        result = run(source, {"business_fields": []})
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["assessments"][0]["status"], "NOT_REVIEWED")

    def test_conflict_marks_consistency_dimension_as_finding(self) -> None:
        result = run(SOURCE, {"business_fields": []})
        self.assertEqual(result["assessments"][0]["status"], "FINDING")
        self.assertEqual(result["audit"]["verdict"], "REJECT")

    def test_conflict_is_bound_only_to_related_requirement(self) -> None:
        review = {
            "meta": {"lifecycle_status": "REVIEW_REQUIRED"},
            "source_ids": ["SRC-001"],
            "requirements": [
                {"requirement_id": "REQ-1", "title": "规则", "source_refs": [{"source_id": "SRC-001", "locator": "L1", "quote": "需求"}]},
                {"requirement_id": "REQ-2", "title": "其他", "source_refs": [{"source_id": "SRC-001", "locator": "L20", "quote": "其他"}]},
            ],
            "requirement_assessments": [
                {"assessment_id": "ASM-1", "requirement_id": "REQ-1", "dimension": "consistency", "status": "NOT_REVIEWED", "finding_ids": []},
                {"assessment_id": "ASM-2", "requirement_id": "REQ-2", "dimension": "consistency", "status": "NOT_REVIEWED", "finding_ids": []},
            ],
            "assessments": [{"dimension": "consistency", "status": "NOT_REVIEWED", "finding_ids": []}],
            "findings": [],
        }
        result = run(SOURCE, {"business_fields": []}, review)
        by_requirement = {item["requirement_id"]: item for item in result["requirement_assessments"]}
        self.assertEqual(by_requirement["REQ-1"]["status"], "FINDING")
        self.assertEqual(by_requirement["REQ-2"]["status"], "NOT_REVIEWED")


if __name__ == "__main__":
    unittest.main()
