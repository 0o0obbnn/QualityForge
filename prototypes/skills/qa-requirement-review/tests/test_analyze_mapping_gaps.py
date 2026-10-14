from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "analyze_mapping_gaps.py"


class AnalyzeMappingGapsTests(unittest.TestCase):
    def test_missing_actor_is_review_scoped_to_permission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            review_path, mapping_path, out = base / "review.json", base / "mapping.json", base / "out.json"
            review = {
                "meta": {"lifecycle_status": "BLOCKED"},
                "requirements": [{"requirement_id": "REQ-1", "function_refs": ["FUN-1"], "atomic_refs": ["AF-1"], "field_refs": []}],
                "requirement_assessments": [{"requirement_id": "REQ-1", "dimension": "role_permission", "status": "NOT_REVIEWED", "finding_ids": []}],
                "assessments": [{"dimension": "role_permission", "status": "NOT_REVIEWED", "finding_ids": []}],
            }
            mapping = {
                "atomic_functions": [{"atomic_id": "AF-1", "actor": "待确认", "status": "confirmed", "trigger": "提交", "generation_readiness": {"status": "ready"}, "evidence": [{"source_id": "SRC-1", "locator": "L1"}]}],
                "gaps": {"conflicts": []},
            }
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(SCRIPT), "--review", str(review_path), "--mapping", str(mapping_path), "--out", str(out)], check=True)
            result = json.loads(out.read_text(encoding="utf-8"))
            finding = next(item for item in result["findings"] if item["code"] == "MISSING_REQUIRED_ACTOR")
            self.assertEqual(finding["severity"], "REVIEW")
            self.assertEqual(finding["affected_test_dimensions"], ["permission"])

    def test_field_conflict_is_linked_to_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            review_path, mapping_path, out = base / "review.json", base / "mapping.json", base / "out.json"
            review = {
                "meta": {"lifecycle_status": "BLOCKED"},
                "requirements": [{"requirement_id": "REQ-1", "function_refs": ["FUN-1"], "atomic_refs": ["AF-1"], "field_refs": ["FLD-1"]}],
                "requirement_assessments": [{"requirement_id": "REQ-1", "dimension": "consistency", "status": "NOT_REVIEWED", "finding_ids": []}],
                "assessments": [{"dimension": "consistency", "status": "NOT_REVIEWED", "finding_ids": []}],
            }
            mapping = {
                "atomic_functions": [{"atomic_id": "AF-1", "actor": "用户", "status": "confirmed", "trigger": "提交", "generation_readiness": {"status": "ready"}, "evidence": []}],
                "gaps": {"conflicts": [{"entity_ids": ["FLD-1"], "summary": "长度冲突", "status": "unresolved", "evidence": [{"source_id": "SRC-1", "locator": "L1"}, {"source_id": "SRC-1", "locator": "L2"}]}]},
            }
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(SCRIPT), "--review", str(review_path), "--mapping", str(mapping_path), "--out", str(out)], check=True)
            result = json.loads(out.read_text(encoding="utf-8"))
            conflicts = [item for item in result["findings"] if item["code"] == "CROSS_SOURCE_CONFLICT"]
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0]["requirement_ids"], ["REQ-1"])
            self.assertEqual(result["requirement_assessments"][0]["status"], "FINDING")

    def test_question_carries_atomic_name_and_locator_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            review_path, mapping_path, out = base / "review.json", base / "mapping.json", base / "out.json"
            review = {
                "meta": {"lifecycle_status": "BLOCKED"},
                "requirements": [{"requirement_id": "REQ-1", "function_refs": ["FUN-1"], "atomic_refs": ["AF-1"], "field_refs": []}],
                "requirement_assessments": [{"requirement_id": "REQ-1", "dimension": "role_permission", "status": "NOT_REVIEWED", "finding_ids": []}],
                "assessments": [{"dimension": "role_permission", "status": "NOT_REVIEWED", "finding_ids": []}],
            }
            mapping = {
                "atomic_functions": [{"atomic_id": "AF-1", "name": "下载原包", "actor": "待确认", "status": "confirmed", "trigger": "点击", "generation_readiness": {"status": "ready"}, "evidence": [{"source_id": "SRC-1", "locator": "L658"}]}],
                "gaps": {"conflicts": []},
            }
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(SCRIPT), "--review", str(review_path), "--mapping", str(mapping_path), "--out", str(out)], check=True)
            result = json.loads(out.read_text(encoding="utf-8"))
            finding = next(item for item in result["findings"] if item["code"] == "MISSING_REQUIRED_ACTOR")
            self.assertIn("下载原包", finding["question"])
            self.assertIn("L658", finding["question"])


if __name__ == "__main__":
    unittest.main()
