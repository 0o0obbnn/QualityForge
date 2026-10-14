from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_full_draft_extractor import FIXTURE


ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "scripts" / "extract_markdown_full_draft.py"
FINALIZER = ROOT / "scripts" / "finalize_mapping.py"
VALIDATOR = ROOT / "scripts" / "validate_mapping.py"
EXPORTER = ROOT / "scripts" / "build_test_design_input.py"
INPUT_VALIDATOR = ROOT / "scripts" / "validate_test_design_input.py"
REVIEW_APPLIER = ROOT / "scripts" / "apply_review_to_mapping.py"


class Schema12HandoffTests(unittest.TestCase):
    def build(self, text: str, base: Path, suffix: str) -> dict:
        source = base / f"source-{suffix}.md"
        draft = base / f"draft-{suffix}.json"
        final = base / f"final-{suffix}.json"
        source.write_text(text, encoding="utf-8")
        subprocess.run(["python3", str(EXTRACTOR), "--source", str(source), "--out", str(draft)], check=True)
        subprocess.run(["python3", str(FINALIZER), "--mapping", str(draft), "--source", str(source), "--out", str(final)], check=True)
        validation = subprocess.run(["python3", str(VALIDATOR), "--mapping", str(final), "--source", str(source)], check=False, capture_output=True, text=True)
        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
        return json.loads(final.read_text(encoding="utf-8"))

    def test_core_ids_do_not_depend_on_line_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first = self.build(FIXTURE, base, "a")
            second = self.build("\n\n" + FIXTURE, base, "b")
            self.assertEqual(first["meta"]["artifact_kind"], "normalized_requirement_mapping")
            self.assertEqual(first["meta"]["schema_version"], "1.2")
            for key, id_key in (("functions", "function_id"), ("atomic_functions", "atomic_id"), ("business_fields", "field_id")):
                self.assertEqual({item[id_key] for item in first[key]}, {item[id_key] for item in second[key]})
            self.assertEqual({item["module_id"] for item in first["modules"]}, {item["module_id"] for item in second["modules"]})
            contains = {(item["source_id"], item["target_id"]) for item in first["relations"] if item["type"] == "contains"}
            self.assertTrue(all((item["module_id"], item["function_id"]) in contains for item in first["functions"]))

    def test_draft_handoff_is_structurally_valid_but_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            mapping = self.build(FIXTURE, base, "draft")
            mapping_path = base / "mapping.json"
            output = base / "test-design-input.json"
            mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(EXPORTER), "--mapping", str(mapping_path), "--out", str(output)], check=True)
            result = subprocess.run(["python3", str(INPUT_VALIDATOR), "--input", str(output)], check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            packet = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(packet["acceptance"]["downstream_eligible"])
            self.assertGreater(packet["coverage"]["dimension_status_counts"]["BLOCKED"], 0)

    def test_finalizer_is_idempotent_for_core_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first = self.build(FIXTURE, base, "first")
            source = base / "source-second.md"
            first_path, second_path = base / "first.json", base / "second.json"
            source.write_text(FIXTURE, encoding="utf-8")
            first_path.write_text(json.dumps(first, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(FINALIZER), "--mapping", str(first_path), "--source", str(source), "--out", str(second_path)], check=True)
            second = json.loads(second_path.read_text(encoding="utf-8"))
            for key, id_key in (("functions", "function_id"), ("atomic_functions", "atomic_id"), ("business_fields", "field_id")):
                self.assertEqual({item[id_key] for item in first[key]}, {item[id_key] for item in second[key]})

    def test_review_projection_releases_only_clear_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            mapping = self.build(FIXTURE, base, "reviewed")
            atomic = mapping["atomic_functions"][0]
            atomic.update({
                "actor": "已授权用户",
                "trigger": "用户点击查询",
                "action": "按条件查询记录",
                "outputs": ["展示符合条件的记录"],
                "processing_rules": ["权限规则：仅可由已授权用户执行查询"],
                "branches": [],
                "status": "confirmed",
            })
            requirement_id = "REQ-TEST-001"
            review = {
                "review_id": "RQR-TEST-001",
                "requirements": [{"requirement_id": requirement_id, "atomic_refs": [atomic["atomic_id"]]}],
                "requirement_assessments": [
                    {"requirement_id": requirement_id, "dimension": dimension, "status": "CLEAR", "finding_ids": []}
                    for dimension in ("ambiguity", "consistency", "testability", "completeness", "nfr_measurability", "role_permission")
                ],
                "findings": [],
            }
            mapping_path, review_path = base / "mapping.json", base / "review.json"
            projected_path, output_path = base / "projected.json", base / "input.json"
            mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(REVIEW_APPLIER), "--mapping", str(mapping_path), "--review", str(review_path), "--out", str(projected_path)], check=True)
            subprocess.run(["python3", str(EXPORTER), "--mapping", str(projected_path), "--out", str(output_path)], check=True)
            validation = subprocess.run(["python3", str(INPUT_VALIDATOR), "--input", str(output_path)], capture_output=True, text=True)
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
            packet = json.loads(output_path.read_text(encoding="utf-8"))
            selected = next(item for item in packet["items"] if item["atomic_id"] == atomic["atomic_id"])
            self.assertIn("functional", selected["eligible_dimensions"])
            self.assertIn("permission", selected["eligible_dimensions"])
            self.assertTrue(packet["acceptance"]["downstream_eligible"])
            self.assertEqual(packet["acceptance"]["verdict"], "PARTIAL_PASS")
            self.assertFalse(packet["source_artifacts"]["review_downstream_eligible"])
            self.assertEqual(packet["acceptance"]["scope"], "READY_DIMENSIONS_ONLY")
            self.assertFalse(packet["fact_policy"]["assumptions_allowed"])
            slice_path = base / "slice.json"
            subprocess.run(["python3", str(EXPORTER), "--mapping", str(projected_path), "--atomic-id", atomic["atomic_id"], "--ready-only", "--out", str(slice_path)], check=True)
            sliced = json.loads(slice_path.read_text(encoding="utf-8"))
            self.assertEqual(sliced["coverage"]["item_count"], 1)
            self.assertEqual(sliced["coverage"]["selected_item_count"], 1)
            self.assertLessEqual(len(sliced["rule_registry"]), len(packet["rule_registry"]))

    def test_open_reject_finding_blocks_only_mapped_dimension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            mapping = self.build(FIXTURE, base, "finding")
            atomic = mapping["atomic_functions"][0]
            atomic.update({"actor": "已授权用户", "trigger": "点击查询", "action": "查询记录", "outputs": ["展示记录"], "branches": [], "status": "confirmed"})
            req_id, finding_id = "REQ-TEST-002", "RQF-TEST-002"
            review = {
                "review_id": "RQR-TEST-002",
                "requirements": [{"requirement_id": req_id, "atomic_refs": [atomic["atomic_id"]]}],
                "requirement_assessments": [
                    {"requirement_id": req_id, "dimension": dimension,
                     "status": "FINDING" if dimension == "role_permission" else "CLEAR",
                     "finding_ids": [finding_id] if dimension == "role_permission" else []}
                    for dimension in ("ambiguity", "consistency", "testability", "completeness", "nfr_measurability", "role_permission")
                ],
                "findings": [{"finding_id": finding_id, "severity": "REJECT", "lifecycle_status": "OPEN",
                              "requirement_ids": [req_id], "atomic_ids": [atomic["atomic_id"]],
                              "affected_test_dimensions": ["permission"]}],
            }
            mapping_path, review_path, projected_path = base / "mapping.json", base / "review.json", base / "projected.json"
            mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(REVIEW_APPLIER), "--mapping", str(mapping_path), "--review", str(review_path), "--out", str(projected_path)], check=True)
            projected = json.loads(projected_path.read_text(encoding="utf-8"))
            self.assertEqual(projected["meta"]["artifact_kind"], "review_projected_mapping")
            gates = next(item for item in projected["atomic_functions"] if item["atomic_id"] == atomic["atomic_id"])["quality_review"]["dimension_eligibility"]
            self.assertEqual(gates["permission"]["status"], "BLOCKED")
            self.assertEqual(gates["functional"]["status"], "READY")

    def test_clear_nfr_is_exported_without_fabricated_function_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            mapping = self.build(FIXTURE, base, "nfr")
            atomic = mapping["atomic_functions"][0]
            functional_id, nfr_id = "REQ-FUNCTION", "REQ-NFR"
            dimensions = ("ambiguity", "consistency", "testability", "completeness", "nfr_measurability", "role_permission")
            review = {
                "review_id": "RQR-NFR",
                "requirements": [
                    {"requirement_id": functional_id, "atomic_refs": [atomic["atomic_id"]]},
                    {"requirement_id": nfr_id, "requirement_type": "non_functional", "quality_attribute": "性能", "title": "峰值吞吐", "summary": "峰值吞吐不低于1000笔/秒", "atomic_refs": [], "source_refs": [{"source_id": mapping["sources"][0]["source_id"], "locator": "L1", "quote": "性能"}]},
                ],
                "requirement_assessments": [
                    {"requirement_id": requirement_id, "dimension": dimension,
                     "status": "NOT_APPLICABLE" if requirement_id == nfr_id and dimension == "role_permission" else "CLEAR", "finding_ids": []}
                    for requirement_id in (functional_id, nfr_id) for dimension in dimensions
                ],
                "findings": [],
            }
            mapping_path, review_path, projected_path, output_path = (base / name for name in ("mapping.json", "review.json", "projected.json", "input.json"))
            mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(REVIEW_APPLIER), "--mapping", str(mapping_path), "--review", str(review_path), "--out", str(projected_path)], check=True)
            subprocess.run(["python3", str(EXPORTER), "--mapping", str(projected_path), "--ready-only", "--out", str(output_path)], check=True)
            packet = json.loads(output_path.read_text(encoding="utf-8"))
        nfr_item = next(item for item in packet["items"] if item.get("item_kind") == "non_functional")
        self.assertEqual(nfr_item["nfr_id"], nfr_id)
        self.assertNotIn("function_id", nfr_item)
        self.assertNotIn("atomic_id", nfr_item)
        self.assertEqual(nfr_item["eligible_dimensions"], ["nfr"])

    def test_explicit_finding_scope_does_not_fan_out(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            mapping = self.build(FIXTURE, base, "scoped-finding")
            atomic = next(item for item in mapping["atomic_functions"] if item["name"] == "查询")
            atomic.update({"actor": "已授权用户", "trigger": "点击查询", "action": "查询记录", "outputs": ["展示记录"], "branches": [], "status": "confirmed"})
            req_id, finding_id = "REQ-SCOPED", "RQF-SCOPED"
            review = {
                "review_id": "RQR-SCOPED",
                "requirements": [{"requirement_id": req_id, "atomic_refs": [atomic["atomic_id"]]}],
                "requirement_assessments": [
                    {"requirement_id": req_id, "dimension": dimension,
                     "status": "FINDING" if dimension == "ambiguity" else "CLEAR",
                     "finding_ids": [finding_id] if dimension == "ambiguity" else []}
                    for dimension in ("ambiguity", "consistency", "testability", "completeness", "nfr_measurability", "role_permission")
                ],
                "findings": [{
                    "finding_id": finding_id, "severity": "REJECT", "lifecycle_status": "OPEN",
                    "requirement_ids": [req_id], "atomic_ids": [atomic["atomic_id"]],
                    "affected_test_dimensions": ["field_validation"],
                }],
            }
            mapping_path, review_path, projected_path = base / "mapping.json", base / "review.json", base / "projected.json"
            mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(REVIEW_APPLIER), "--mapping", str(mapping_path), "--review", str(review_path), "--out", str(projected_path)], check=True)
            projected = json.loads(projected_path.read_text(encoding="utf-8"))
            gates = next(item for item in projected["atomic_functions"] if item["atomic_id"] == atomic["atomic_id"])["quality_review"]["dimension_eligibility"]
            self.assertEqual(gates["field_validation"]["status"], "BLOCKED")
            self.assertEqual(gates["functional"]["status"], "READY")

    def test_input_validator_rejects_invented_rule_and_assumptions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            mapping = self.build(FIXTURE, base, "invalid-input")
            mapping_path, output_path = base / "mapping.json", base / "input.json"
            mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(EXPORTER), "--mapping", str(mapping_path), "--out", str(output_path)], check=True)
            packet = json.loads(output_path.read_text(encoding="utf-8"))
            packet["fact_policy"]["assumptions_allowed"] = True
            packet["items"][0]["operation_rule_ids"] = ["RULE-INVENTED"]
            output_path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
            validation = subprocess.run(["python3", str(INPUT_VALIDATOR), "--input", str(output_path)], capture_output=True, text=True)
            self.assertEqual(validation.returncode, 2)
            self.assertIn("forbid assumptions", validation.stdout)
            self.assertIn("unknown operation rule", validation.stdout)


if __name__ == "__main__":
    unittest.main()
