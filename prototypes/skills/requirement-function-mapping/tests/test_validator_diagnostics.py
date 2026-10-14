from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_mapping.py"
TEMPLATE = ROOT / "assets" / "mapping_template.json"
MIGRATOR = ROOT / "scripts" / "migrate_legacy_artifact.py"


class ValidatorDiagnosticsTests(unittest.TestCase):
    def test_duplicate_id_has_machine_repair_metadata(self) -> None:
        data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        data["functions"] = [
            {"function_id": "FUN-X", "name": "A"},
            {"function_id": "FUN-X", "name": "B"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(VALIDATOR), "--mapping", str(path)],
                check=False, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        duplicate = next(item for item in report["diagnostics"] if item["code"] == "DUPLICATE_ENTITY_ID")
        self.assertEqual(duplicate["entity_ids"], ["FUN-X"])
        self.assertIn("rule_anchor", duplicate)

    def test_text_format_preserves_codes_and_rule_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{}", encoding="utf-8")
            result = subprocess.run(
                ["python3", str(VALIDATOR), "--mapping", str(path), "--format", "text"],
                check=False, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("MISSING_REQUIRED_PROPERTY", result.stdout)
        self.assertIn("extraction-contract#顶层结构", result.stdout)

    def test_reference_dependency_requires_declared_type(self) -> None:
        data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        data["source_units"] = [{
            "unit_id": "REF-001", "source_id": "SRC-001", "kind": "reference_dependency",
            "semantic_key": "reference_dependency:example#1", "content_sha256": "0" * 64,
            "locator": "L1", "relevant": True, "status": "processed", "reason": None,
            "dependency_id": "DEP-001", "finding_ids": [],
            "reference_type": "external", "reference_key": "external:example",
            "target_name": "example", "quote": "详见示例文档", "resolution_status": "target_located",
            "blocking_scope": {"source_id": "SRC-001", "locator": "L1"},
        }]
        data["source_dependency_review"] = {"artifact_kind": "requirement_source_dependency_review", "sha256": "0" * 64, "summary": {}, "findings": []}
        data["coverage"]["source_coverage"].update({"relevant_units": 1, "processed_units": 1})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid-reference.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(VALIDATOR), "--mapping", str(path), "--format", "text"],
                check=False, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid reference_type", result.stdout)

    def test_legacy_kind_migration_writes_new_file_and_preserves_facts(self) -> None:
        data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        data["meta"].pop("artifact_kind")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "legacy.json"
            output = Path(directory) / "migrated.json"
            source.write_text(json.dumps(data), encoding="utf-8")
            subprocess.run(["python3", str(MIGRATOR), "--mapping", str(source), "--out", str(output)], check=True)
            migrated = json.loads(output.read_text(encoding="utf-8"))
        self.assertNotIn("artifact_kind", data["meta"])
        self.assertEqual(migrated["meta"]["artifact_kind"], "full_discovery_draft")
        self.assertEqual(migrated["functions"], data["functions"])
        self.assertEqual(migrated["business_fields"], data["business_fields"])


if __name__ == "__main__":
    unittest.main()
