from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_full_draft_extractor import FIXTURE


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "scripts" / "run_pipeline.py"
REFRESH = ROOT / "scripts" / "incremental_refresh.py"
SOURCE_REVIEWER = ROOT.parent / "qa-requirement-review" / "scripts" / "review_source_dependencies.py"

RULE_TABLE = """
<table><tr><th>字段</th><th>是否必填</th><th>描述</th></tr>
<tr><td>备注长度</td><td>否</td><td>最多50个字符</td></tr></table>
"""


class IncrementalRefreshTests(unittest.TestCase):
    def test_refresh_removes_stale_field_and_invalidates_verifying_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "requirement.md"
            initial_source = FIXTURE.replace("##### 字段说明", RULE_TABLE + "\n##### 字段说明")
            source.write_text(initial_source, encoding="utf-8")
            initial_out = base / "initial"
            first = subprocess.run(
                ["python3", str(PIPELINE), "--source", str(source), "--out-dir", str(initial_out), "--through-stage", "enrich"],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            graph_path = initial_out / "requirement_typed_graph.json"
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            field = next(item for item in graph["business_fields"] if item["business_name"] == "备注长度")
            graph["test_cases"] = [{"case_id": "TC-1", "title": "验证备注长度", "status": "ACTIVE"}]
            graph["relations"].append({
                "relation_id": "REL-TEST-1", "source_id": "TC-1", "target_id": field["field_id"], "type": "verifies",
                "note": "测试用例验证该字段", "evidence": field["evidence"],
            })
            graph["coverage"]["graph_nodes"]["test_cases"] = 1
            graph["coverage"]["graph_edges"] = len(graph["relations"])
            before = base / "before.json"
            before.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")

            source.write_text(FIXTURE, encoding="utf-8")
            refresh_out = base / "refresh"
            source_review = base / "source-review.json"
            subprocess.run(["python3", str(SOURCE_REVIEWER), "--source", str(source), "--out", str(source_review)], check=True)
            result = subprocess.run(
                ["python3", str(REFRESH), "--before-graph", str(before), "--source", str(source),
                 "--source-review", str(source_review), "--out-dir", str(refresh_out)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            invalidation = json.loads((refresh_out / "requirement_semantic_invalidation.json").read_text(encoding="utf-8"))
            refreshed = json.loads((refresh_out / "requirement_refreshed_typed_graph.json").read_text(encoding="utf-8"))
            current_field_ids = {item["field_id"] for item in refreshed["business_fields"]}
            self.assertNotIn(field["field_id"], current_field_ids)
            self.assertIn(field["field_id"], invalidation["stale_entities_removed"])
            self.assertEqual(invalidation["source_unit_invalidation"]["mode"], "BOUNDED")
            self.assertGreater(invalidation["source_unit_invalidation"]["changed_count"], 0)
            self.assertTrue(any(item["change_type"] == "DELETED" for item in invalidation["source_unit_invalidation"]["changes"]))
            self.assertEqual(invalidation["test_invalidation"]["case_ids"], ["TC-1"])
            self.assertEqual(invalidation["acceptance"]["stale_cleanup"], "PASS")
            self.assertFalse(invalidation["acceptance"]["affected_scope_downstream_eligible"])
            self.assertEqual(invalidation["release_policy"], "READY_DIMENSIONS_ONLY; preserve unaffected cases and regenerate changed or newly READY slices")

    def test_visual_evidence_fact_requires_revalidation_instead_of_silent_loss(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, before = base / "requirement.md", base / "before.json"
            source.write_text("# 系统功能设计\n", encoding="utf-8")
            before.write_text(json.dumps({
                "meta": {"schema_version": "1.4", "artifact_kind": "typed_requirement_graph"},
                "atomic_functions": [{"atomic_id": "AF-VISUAL", "origin": "visual_evidence"}],
            }), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(REFRESH), "--before-graph", str(before), "--source", str(source), "--out-dir", str(base / "out")],
                check=False, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("revalidate visual evidence", result.stderr)


if __name__ == "__main__":
    unittest.main()
