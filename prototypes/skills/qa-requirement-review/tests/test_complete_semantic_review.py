from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPLETER = ROOT / "scripts" / "complete_semantic_review.py"
VALIDATOR = ROOT / "scripts" / "validate_review.py"


class CompleteSemanticReviewTests(unittest.TestCase):
    def test_compatibility_finalizer_preserves_semantic_work_for_ai_or_human(self) -> None:
        dimensions = ("ambiguity", "consistency", "testability", "completeness", "nfr_measurability", "role_permission")
        proof = {"source_id": "SRC-1", "locator": "L1", "quote": "查询后展示订单编号"}
        finding = {
            "finding_id": "RQF-ACTOR", "code": "MISSING_REQUIRED_ACTOR", "severity": "REVIEW", "certainty": "confirmed",
            "evidence_type": "ABSENCE", "requirement_ids": ["REQ-1"], "function_ids": ["FUN-1"], "atomic_ids": ["AF-1"],
            "affected_test_dimensions": ["permission"], "source_refs": ["SRC-1:L1"], "evidence": "未找到执行角色",
            "inspected_scope": ["SRC-1:L1"], "expected_element": "执行角色", "question": "谁可查询？", "recommendation": "补充角色。",
        }
        review = {
            "meta": {"schema_version": "1.0", "artifact_kind": "requirement_quality_review", "review_mode": "full", "lifecycle_status": "BLOCKED", "generated_at": "2026-09-07T00:00:00+08:00"},
            "review_id": "RQR-1", "source_ids": ["SRC-1"], "sources": [{"source_id": "SRC-1", "file": "r.md", "type": "requirement", "version": "1", "authority": 1}],
            "source_units": [{"unit_id": "U-1", "source_id": "SRC-1", "kind": "paragraph", "locator": "L1", "relevant": True, "status": "processed"}],
            "source_unit_dispositions": [{"unit_id": "U-1", "disposition": "requirement", "requirement_ids": ["REQ-1"], "finding_ids": [], "reason": "已映射"}],
            "requirements": [{"requirement_id": "REQ-1", "title": "查询", "summary": "查询", "function_refs": ["FUN-1"], "atomic_refs": ["AF-1"], "field_refs": ["FLD-1"], "rule_refs": [], "source_refs": [proof]}],
            "assessments": [{"dimension": d, "status": "NOT_REVIEWED", "rationale": "待评审", "finding_ids": []} for d in dimensions],
            "requirement_assessments": [{"assessment_id": f"A-{i}", "requirement_id": "REQ-1", "dimension": d, "status": "FINDING" if d == "role_permission" else "NOT_REVIEWED", "rationale": "角色缺失" if d == "role_permission" else "待评审", "finding_ids": ["RQF-ACTOR"] if d == "role_permission" else []} for i, d in enumerate(dimensions)],
            "findings": [finding], "test_points": [],
            "coverage": {"requirement_count": 1, "requirement_assessment_count": 6, "expected_requirement_assessment_count": 6, "source_unit_disposition_count": 1, "unresolved_source_unit_count": 0, "source_coverage": {"claim": "full", "relevant_units": 1, "processed_units": 1, "review_required_units": 0, "skipped_units": 0, "unavailable_units": 0, "uncovered_ranges": []}},
            "audit": {"verdict": "NOT_RUN", "downstream_eligible": False, "errors": [], "warnings": []},
        }
        mapping = {
            "atomic_functions": [{"atomic_id": "AF-1", "function_id": "FUN-1", "name": "查询", "action": "查询", "actor": "待确认", "status": "confirmed", "origin": "table_action", "preconditions": [], "outputs": [], "state_changes": [], "branches": ["具体结果待语义复核"], "processing_rules": [], "evidence": [proof], "rule_ids": []}],
            "business_fields": [{"field_id": "FLD-1", "business_name": "订单编号"}],
            "field_bindings": [{"atomic_id": "AF-1", "field_id": "FLD-1", "usages": ["display", "output"], "rules": []}],
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, review_path, mapping_path, output = base / "r.md", base / "review.json", base / "mapping.json", base / "out.json"
            source.write_text("查询后展示订单编号", encoding="utf-8")
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(COMPLETER), "--review", str(review_path), "--mapping", str(mapping_path), "--source", str(source), "--out", str(output)], check=True)
            completed = json.loads(output.read_text(encoding="utf-8"))
            validation = subprocess.run(["python3", str(VALIDATOR), "--review", str(output), "--source", str(source)], text=True, capture_output=True)
        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
        self.assertEqual(completed["test_points"], [])
        self.assertEqual(completed["audit"]["verdict"], "PASS_WITH_REVIEW")
        self.assertFalse(completed["audit"]["downstream_eligible"])
        self.assertEqual(
            sum(item["status"] == "NOT_REVIEWED" for item in completed["requirement_assessments"]),
            5,
        )
        consistency = next(item for item in completed["requirement_assessments"] if item["dimension"] == "consistency")
        self.assertEqual(consistency["status"], "NOT_REVIEWED")
