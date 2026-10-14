from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# 全部输入为本 Skill 内的合成 fixture，不依赖其他 Skill 的 tests/outputs 或 NPRJ 资料。
ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "evals/files/synthetic_reset_slice_test_design_input.json"
CASES = ROOT / "evals/files/synthetic_reset_slice_case_ir.json"
FULL_INPUT = ROOT / "evals/files/synthetic_full_ready_test_design_input.json"
FULL_CASES = ROOT / "evals/files/synthetic_full_ready_case_ir.json"


def _load_validator():
    path = ROOT / "scripts/validate_case_ir.py"
    spec = importlib.util.spec_from_file_location("validate_case_ir", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class TestCaseIRContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = _load_validator()
        cls.packet = json.loads(CASES.read_text(encoding="utf-8"))
        cls.source = json.loads(INPUT.read_text(encoding="utf-8"))
        cls.source_hash = hashlib.sha256(INPUT.read_bytes()).hexdigest()

    def validate(self, packet):
        return self.validator.validate(
            packet, self.source, "fixture-hash", self.source_hash
        )

    def test_synthetic_reset_slice_passes_contract(self):
        result = self.validate(self.packet)
        self.assertEqual(result["verdict"], "PASS", result["findings"])
        self.assertEqual(result["case_count"], 1)

    def test_non_ready_permission_case_is_rejected(self):
        broken = copy.deepcopy(self.packet)
        broken["cases"][0]["covered_dimensions"].append("permission")
        result = self.validate(broken)
        self.assertEqual(result["verdict"], "REJECT")
        self.assertIn(
            "NON_READY_DIMENSION_COVERED", {item["code"] for item in result["findings"]}
        )

    def test_runtime_binding_is_rejected(self):
        broken = copy.deepcopy(self.packet)
        broken["cases"][0]["steps"][0]["locator"] = "#reset"
        result = self.validate(broken)
        self.assertIn(
            "FORBIDDEN_RUNTIME_FIELD", {item["code"] for item in result["findings"]}
        )

    def test_source_hash_drift_is_rejected(self):
        broken = copy.deepcopy(self.packet)
        broken["source_artifacts"]["test_design_input_sha256"] = "0" * 64
        result = self.validate(broken)
        self.assertIn(
            "SOURCE_HASH_MISMATCH", {item["code"] for item in result["findings"]}
        )

    def test_cross_item_data_requirement_is_rejected(self):
        broken = copy.deepcopy(self.packet)
        broken["data_requirements"][0]["test_design_item_id"] = "TDI-NOPE"
        result = self.validate(broken)
        self.assertIn(
            "DATA_ITEM_NOT_IN_SCOPE", {item["code"] for item in result["findings"]}
        )

    def test_ready_rule_without_oracle_is_rejected(self):
        broken = copy.deepcopy(self.packet)
        broken["cases"][0]["steps"][0]["expected_results"][0]["oracle_rule_ids"].remove(
            "RULE-SYN-011"
        )
        result = self.validate(broken)
        self.assertIn(
            "READY_RULE_WITHOUT_ORACLE", {item["code"] for item in result["findings"]}
        )

    def test_full_ready_scope_is_complete(self):
        packet = json.loads(FULL_CASES.read_text(encoding="utf-8"))
        source = json.loads(FULL_INPUT.read_text(encoding="utf-8"))
        result = self.validator.validate(
            packet,
            source,
            "fixture-hash",
            hashlib.sha256(FULL_INPUT.read_bytes()).hexdigest(),
        )
        self.assertEqual(result["verdict"], "PASS", result["findings"])
        self.assertEqual(result["case_count"], 4)

    def test_full_ready_scope_cannot_omit_ready_item(self):
        packet = json.loads(FULL_CASES.read_text(encoding="utf-8"))
        source = json.loads(FULL_INPUT.read_text(encoding="utf-8"))
        packet["generation_scope"]["selected_test_design_item_ids"].pop()
        result = self.validator.validate(
            packet,
            source,
            "fixture-hash",
            hashlib.sha256(FULL_INPUT.read_bytes()).hexdigest(),
        )
        self.assertIn(
            "FULL_READY_SCOPE_INCOMPLETE", {item["code"] for item in result["findings"]}
        )

    def test_csv_projection_keeps_case_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            validation = Path(directory) / "validation.json"
            output = Path(directory) / "cases.csv"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/validate_case_ir.py"),
                    "--cases",
                    str(CASES),
                    "--input",
                    str(INPUT),
                    "--out",
                    str(validation),
                ],
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/render_case_csv.py"),
                    "--cases",
                    str(CASES),
                    "--validation",
                    str(validation),
                    "--out",
                    str(output),
                ],
                check=True,
            )
            with output.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual([row["case_id"] for row in rows], ["TC-SYN01-001"])
        self.assertIn("1. 填写合法设备编号", rows[0]["test_steps"])
        self.assertIn(
            "系统提示提交成功并展示生成的唯一工单编号", rows[0]["expected_results"]
        )

    def test_csv_projection_rejects_changed_json(self):
        with tempfile.TemporaryDirectory() as directory:
            validation = Path(directory) / "validation.json"
            changed_cases = Path(directory) / "changed.json"
            output = Path(directory) / "cases.csv"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/validate_case_ir.py"),
                    "--cases",
                    str(CASES),
                    "--input",
                    str(INPUT),
                    "--out",
                    str(validation),
                ],
                check=True,
            )
            changed = copy.deepcopy(self.packet)
            changed["cases"][0]["title"] = "校验后被修改"
            changed_cases.write_text(
                json.dumps(changed, ensure_ascii=False), encoding="utf-8"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/render_case_csv.py"),
                    "--cases",
                    str(changed_cases),
                    "--validation",
                    str(validation),
                    "--out",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("JSON 在校验后发生变化", result.stderr)


if __name__ == "__main__":
    unittest.main()
