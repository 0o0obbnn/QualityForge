from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_full_draft_extractor import FIXTURE


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "scripts" / "run_pipeline.py"
SOURCE_REVIEWER = ROOT.parent / "qa-requirement-review" / "scripts" / "review_source_dependencies.py"


class PipelineTests(unittest.TestCase):
    def run_pipeline(self, source: Path, output: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(PIPELINE), "--source", str(source), "--out-dir", str(output), *extra],
            check=False, capture_output=True, text=True,
        )

    def test_resume_reuses_verified_stages_and_source_change_invalidates_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, output = base / "requirement.md", base / "artifacts"
            source.write_text(FIXTURE, encoding="utf-8")
            first = self.run_pipeline(source, output)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(first.stdout.count("RUN "), 5)

            resumed = self.run_pipeline(source, output, "--resume")
            self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
            self.assertEqual(resumed.stdout.count("SKIP "), 5)

            source.write_text(FIXTURE + "\n补充说明。\n", encoding="utf-8")
            changed = self.run_pipeline(source, output, "--resume")
            self.assertEqual(changed.returncode, 0, changed.stdout + changed.stderr)
            self.assertIn("RUN extract", changed.stdout)
            state = json.loads((output / "pipeline-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["extract"]["last_action"], "EXECUTED")

    def test_review_chain_can_continue_from_existing_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, output = base / "requirement.md", base / "artifacts"
            source.write_text(FIXTURE, encoding="utf-8")
            first = self.run_pipeline(source, output)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            graph_path = output / "requirement_typed_graph.json"
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            atomic = graph["atomic_functions"][0]
            atomic.update({
                "actor": "已授权用户",
                "trigger": "用户点击查询",
                "action": "按条件查询记录",
                "outputs": [],
                "branches": ["查询完成后展示符合条件的记录"],
                "status": "confirmed",
            })
            graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            requirement_id = "REQ-PIPELINE-1"
            dimensions = ("ambiguity", "consistency", "testability", "completeness", "nfr_measurability", "role_permission")
            review = {
                "review_id": "RQR-PIPELINE-1",
                "meta": {"lifecycle_status": "REVIEW_REQUIRED"},
                "audit": {"verdict": "PASS_WITH_REVIEW", "downstream_eligible": False},
                "requirements": [{"requirement_id": requirement_id, "atomic_refs": [atomic["atomic_id"]]}],
                "requirement_assessments": [
                    {"requirement_id": requirement_id, "dimension": dimension, "status": "CLEAR", "finding_ids": []}
                    for dimension in dimensions
                ],
                "findings": [],
            }
            review_path = base / "review.json"
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            continued = self.run_pipeline(source, output, "--review", str(review_path), "--from-stage", "project_review")
            self.assertEqual(continued.returncode, 0, continued.stdout + continued.stderr)
            self.assertTrue((output / "requirement_reviewed_graph.json").exists())
            self.assertTrue((output / "requirement_test_design_input.json").exists())
            test_input = json.loads((output / "requirement_test_design_input.json").read_text(encoding="utf-8"))
            self.assertFalse(test_input["source_artifacts"]["review_downstream_eligible"])
            self.assertTrue(test_input["acceptance"]["downstream_eligible"])
            self.assertEqual(test_input["acceptance"]["scope"], "READY_DIMENSIONS_ONLY")
            self.assertTrue(test_input["items"])
            self.assertTrue(all(item["eligible_dimensions"] for item in test_input["items"]))
            self.assertNotEqual(test_input["coverage"]["source_item_count"], test_input["coverage"]["item_count"])
            state = json.loads((output / "pipeline-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["validate_test_input"]["status"], "COMPLETED")

    def test_formal_mapping_consumes_source_dependency_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, source_review, output = base / "requirement.md", base / "source-review.json", base / "artifacts"
            source.write_text("# 需求\n\n## 导出\n\n模板见《导出模板.xlsx》。\n", encoding="utf-8")
            subprocess.run(["python3", str(SOURCE_REVIEWER), "--source", str(source), "--out", str(source_review)], check=True)
            result = self.run_pipeline(source, output, "--source-review", str(source_review), "--through-stage", "extract")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            draft = json.loads((output / "requirement_full_discovery_draft.json").read_text(encoding="utf-8"))
            dependency = next(item for item in draft["source_units"] if item["kind"] == "reference_dependency")
            self.assertEqual(dependency["status"], "unavailable")
            self.assertTrue(dependency["finding_ids"])
            self.assertEqual(draft["source_dependency_review"]["artifact_kind"], "requirement_source_dependency_review")


if __name__ == "__main__":
    unittest.main()
