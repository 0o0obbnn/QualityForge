from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_review.py"
SPEC = importlib.util.spec_from_file_location("validate_review", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
GATE_SCRIPT = Path(__file__).parents[2] / "requirement-quality-gate" / "scripts" / "gate_check.py"
GATE_SPEC = importlib.util.spec_from_file_location("requirement_gate", GATE_SCRIPT)
GATE = importlib.util.module_from_spec(GATE_SPEC)
assert GATE_SPEC and GATE_SPEC.loader
GATE_SPEC.loader.exec_module(GATE)
RESOLUTION_SCRIPT = Path(__file__).parents[1] / "scripts" / "apply_review_resolutions.py"
RESOLUTION_QUEUE_SCRIPT = Path(__file__).parents[1] / "scripts" / "build_review_resolution_queue.py"


def accepted_review() -> dict:
    dimensions = sorted(MODULE.DIMENSIONS)
    return {
        "meta": {
            "schema_version": "1.0",
            "artifact_kind": "requirement_quality_review",
            "review_mode": "full",
            "lifecycle_status": "ACCEPTED",
            "generated_at": "2026-09-06T00:00:00+08:00",
        },
        "review_id": "RQR-EXAMPLE",
        "source_ids": ["SRC-001"],
        "sources": [{"source_id": "SRC-001", "file": "requirement.md", "type": "requirement", "version": "1.0", "authority": 1}],
        "source_units": [{"unit_id": "UNIT-001", "source_id": "SRC-001", "kind": "paragraph", "locator": "L1", "relevant": True, "status": "processed"}],
        "source_unit_dispositions": [{"unit_id": "UNIT-001", "disposition": "requirement", "requirement_ids": ["REQ-001"], "finding_ids": [], "reason": "已映射到需求"}],
        "requirements": [{
            "requirement_id": "REQ-001",
            "title": "提交申请",
            "summary": "用户提交完整申请后，系统返回申请编号。",
            "function_refs": ["FUN-001"],
            "atomic_refs": ["AT-001"],
            "field_refs": ["FLD-001"],
            "rule_refs": [],
            "source_refs": [{"source_id": "SRC-001", "locator": "L1", "quote": "系统返回申请编号"}],
        }],
        "assessments": [{"dimension": d, "status": "CLEAR", "rationale": "已按原文完成评审", "finding_ids": []} for d in dimensions],
        "requirement_assessments": [{"assessment_id": f"ASM-{i:02d}", "requirement_id": "REQ-001", "dimension": d, "status": "CLEAR", "rationale": "已按原文完成评审", "finding_ids": [], "source_refs": ["SRC-001:L1"]} for i, d in enumerate(dimensions, 1)],
        "findings": [],
        "test_points": [{
            "test_point_id": "TP-001",
            "requirement_id": "REQ-001",
            "category": "normal",
            "objective": "验证成功提交",
            "preconditions": ["申请资料完整"],
            "action": "提交申请",
            "expected_result": "系统返回申请编号",
            "source_refs": ["SRC-001:L1"],
            "readiness": "ready",
            "blocking_finding_ids": [],
        }],
        "coverage": {
            "requirement_count": 1,
            "requirement_assessment_count": 6,
            "expected_requirement_assessment_count": 6,
            "source_unit_disposition_count": 1,
            "unresolved_source_unit_count": 0,
            "source_coverage": {"claim": "full", "relevant_units": 1, "processed_units": 1, "review_required_units": 0, "skipped_units": 0, "unavailable_units": 0, "uncovered_ranges": []},
        },
        "audit": {"verdict": "PASS", "downstream_eligible": True, "errors": [], "warnings": []},
    }


def two_requirement_review() -> dict:
    review = accepted_review()
    second = json.loads(json.dumps(review["requirements"][0]))
    second.update({"requirement_id": "REQ-002", "title": "查看申请", "summary": "用户查看申请结果。"})
    review["requirements"].append(second)
    for index, dimension in enumerate(sorted(MODULE.DIMENSIONS), 1):
        review["requirement_assessments"].append({
            "assessment_id": f"ASM-B{index:02d}",
            "requirement_id": "REQ-002",
            "dimension": dimension,
            "status": "CLEAR",
            "rationale": "已按原文完成评审",
            "finding_ids": [],
            "source_refs": ["SRC-001:L1"],
        })
    review["coverage"].update({"requirement_count": 2, "requirement_assessment_count": 12, "expected_requirement_assessment_count": 12})
    return review


class ReviewValidatorTests(unittest.TestCase):
    def test_accepted_review_is_downstream_eligible(self) -> None:
        errors, warnings = MODULE.validate(accepted_review(), "系统返回申请编号")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_accepted_review_is_compatible_with_existing_quality_gate(self) -> None:
        result = GATE.check_review(accepted_review())
        self.assertEqual(result["verdict"], "PASS")

    def test_draft_may_be_structurally_valid_but_not_eligible(self) -> None:
        review = accepted_review()
        review["meta"]["lifecycle_status"] = "BLOCKED"
        review["assessments"][0]["status"] = "NOT_REVIEWED"
        review["audit"] = {"verdict": "NOT_RUN", "downstream_eligible": False, "errors": [], "warnings": []}
        errors, _ = MODULE.validate(review)
        self.assertEqual(errors, [])

    def test_ready_test_point_requires_explicit_preconditions(self) -> None:
        review = accepted_review()
        review["test_points"][0]["preconditions"] = []
        errors, _ = MODULE.validate(review)
        self.assertIn(
            "test_point[0] ready state requires explicit preconditions and no blockers",
            errors,
        )

    def test_unavailable_source_bound_to_finding_remains_unresolved(self) -> None:
        review = accepted_review()
        finding = {
            "finding_id": "FND-SOURCE", "code": "MISSING_REFERENCED_ARTIFACT", "severity": "REJECT",
            "certainty": "confirmed", "evidence_type": "ABSENCE", "evidence": "附件未提供",
            "source_refs": ["SRC-001:L1"], "requirement_ids": ["REQ-001"],
            "affected_test_dimensions": ["integration"],
            "inspected_scope": ["SRC-001:L1"], "expected_element": "被引用附件",
        }
        review["findings"] = [finding]
        review["source_units"][0].update(status="unavailable", reason="引用附件未提供")
        review["source_unit_dispositions"][0].update(
            disposition="finding", requirement_ids=["REQ-001"], finding_ids=["FND-SOURCE"]
        )
        review["coverage"]["source_coverage"].update(processed_units=0, unavailable_units=1)
        review["coverage"]["unresolved_source_unit_count"] = 0
        review["audit"].update(verdict="REJECT", downstream_eligible=False)
        review["meta"]["lifecycle_status"] = "BLOCKED"
        errors, _ = MODULE.validate(review)
        self.assertIn(
            "coverage.unresolved_source_unit_count does not match source status and dispositions",
            errors,
        )

    def test_quick_review_cannot_claim_downstream_eligibility(self) -> None:
        review = accepted_review()
        review["meta"]["review_mode"] = "quick"
        errors, _ = MODULE.validate(review)
        self.assertIn("audit.downstream_eligible cannot be true before full acceptance", errors)
        self.assertIn("quick review cannot be downstream eligible", errors)

    def test_open_review_finding_cannot_claim_pass(self) -> None:
        review = accepted_review()
        review["findings"] = [{
            "finding_id": "FND-REVIEW", "code": "AMBIGUOUS_LANGUAGE", "severity": "REVIEW",
            "certainty": "risk", "evidence_type": "QUOTE", "evidence": "系统及时处理",
            "source_refs": ["SRC-001:L1"], "requirement_ids": ["REQ-001"],
            "affected_test_dimensions": ["functional"],
        }]
        errors, _ = MODULE.validate(review)
        self.assertIn("audit.downstream_eligible cannot be true before full acceptance", errors)
        self.assertIn("PASS review cannot contain unreviewed assessments or unresolved findings", errors)

    def test_absence_finding_requires_inspected_scope(self) -> None:
        review = accepted_review()
        finding = {
            "finding_id": "FND-001", "code": "MISSING_EXCEPTION_BEHAVIOR", "severity": "REVIEW",
            "certainty": "risk", "evidence_type": "ABSENCE", "evidence": "未定义异常路径",
            "source_refs": ["SRC-001:L1"], "requirement_ids": ["REQ-001"], "expected_element": "异常处理规则",
        }
        review["findings"] = [finding]
        review["assessments"][0] = {"dimension": review["assessments"][0]["dimension"], "status": "FINDING", "rationale": "存在缺失", "finding_ids": ["FND-001"]}
        review["audit"] = {"verdict": "PASS_WITH_REVIEW", "downstream_eligible": False, "errors": [], "warnings": []}
        review["meta"]["lifecycle_status"] = "REVIEW_REQUIRED"
        errors, _ = MODULE.validate(review)
        self.assertIn("finding FND-001 absence evidence lacks inspected_scope or expected_element", errors)

    def test_empty_sources_returns_errors_instead_of_crashing(self) -> None:
        review = accepted_review()
        review["sources"] = []
        review["source_ids"] = []
        errors, _ = MODULE.validate(review, "系统返回申请编号")
        self.assertTrue(errors)

    def test_evidenced_resolution_closes_finding_and_recomputes_acceptance(self) -> None:
        review = accepted_review()
        finding = {
            "finding_id": "FND-001", "code": "MISSING_EXCEPTION_BEHAVIOR", "severity": "REJECT",
            "certainty": "confirmed", "evidence_type": "ABSENCE", "evidence": "未定义异常路径",
            "source_refs": ["SRC-001:L1"], "requirement_ids": ["REQ-001"],
            "inspected_scope": ["SRC-001:L1"], "expected_element": "异常处理规则",
        }
        review["findings"] = [finding]
        review["assessments"][0].update({"status": "FINDING", "finding_ids": ["FND-001"]})
        review["requirement_assessments"][0].update({"status": "FINDING", "finding_ids": ["FND-001"]})
        review["meta"]["lifecycle_status"] = "BLOCKED"
        review["audit"].update({"verdict": "REJECT", "downstream_eligible": False})
        resolutions = {"resolutions": [{
            "finding_id": "FND-001", "decision": "RESOLVE", "resolution": "补充了失败结果",
            "source_refs": ["SRC-001:L1"],
            "assessment_updates": [{"requirement_id": "REQ-001", "dimension": review["requirement_assessments"][0]["dimension"], "status": "CLEAR", "rationale": "新证据已明确异常结果"}],
        }]}
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            review_path, resolution_path, out_path = base / "review.json", base / "resolutions.json", base / "out.json"
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            resolution_path.write_text(json.dumps(resolutions, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(RESOLUTION_SCRIPT), "--review", str(review_path), "--resolutions", str(resolution_path), "--out", str(out_path)], check=True)
            resolved = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(resolved["findings"][0]["lifecycle_status"], "RESOLVED")
            self.assertEqual(resolved["audit"]["verdict"], "PASS")
            self.assertTrue(resolved["audit"]["downstream_eligible"])
            errors, _ = MODULE.validate(resolved, "系统返回申请编号")
            self.assertEqual(errors, [])

    def test_closing_finding_without_assessment_update_does_not_auto_clear(self) -> None:
        review = accepted_review()
        finding = {
            "finding_id": "FND-001", "code": "MISSING_EXCEPTION_BEHAVIOR", "severity": "REVIEW",
            "certainty": "confirmed", "evidence_type": "ABSENCE", "evidence": "未定义异常路径",
            "source_refs": ["SRC-001:L1"], "requirement_ids": ["REQ-001"],
            "affected_test_dimensions": ["functional"],
            "inspected_scope": ["SRC-001:L1"], "expected_element": "异常处理规则",
        }
        review["findings"] = [finding]
        review["requirement_assessments"][0].update(status="FINDING", finding_ids=["FND-001"])
        review["audit"].update(verdict="PASS_WITH_REVIEW", downstream_eligible=False)
        review["meta"]["lifecycle_status"] = "REVIEW_REQUIRED"
        resolutions = {"resolutions": [{
            "finding_id": "FND-001", "decision": "RESOLVE", "resolution": "已补充异常结果",
            "source_refs": ["SRC-001:L1"], "assessment_updates": [],
        }]}
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            review_path, resolution_path, out_path = base / "review.json", base / "resolutions.json", base / "out.json"
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            resolution_path.write_text(json.dumps(resolutions, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(RESOLUTION_SCRIPT), "--review", str(review_path), "--resolutions", str(resolution_path), "--out", str(out_path)], check=True)
            resolved = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(resolved["requirement_assessments"][0]["status"], "NOT_REVIEWED")
        self.assertEqual(resolved["audit"]["verdict"], "PASS_WITH_REVIEW")
        self.assertFalse(resolved["audit"]["downstream_eligible"])

    def test_resolution_queue_covers_open_findings_and_unreviewed_assessments(self) -> None:
        review = accepted_review()
        review["requirement_assessments"][0]["status"] = "NOT_REVIEWED"
        review["requirement_assessments"][0]["rationale"] = "待评审"
        review["findings"] = [{
            "finding_id": "FND-001", "code": "MISSING_EXCEPTION_BEHAVIOR", "severity": "REVIEW",
            "question": "失败时如何处理？", "recommendation": "补充失败结果", "evidence": "未定义",
            "source_refs": ["SRC-001:L1"],
        }]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            review_path, out_path = base / "review.json", base / "queue.json"
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(RESOLUTION_QUEUE_SCRIPT), "--review", str(review_path), "--out", str(out_path)], check=True)
            queue = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(queue["coverage"]["open_finding_count"], 1)
            self.assertEqual(queue["coverage"]["not_reviewed_assessment_count"], 1)

    def test_semantic_review_can_add_and_bind_a_new_conflict_finding(self) -> None:
        review = accepted_review()
        target = review["requirement_assessments"][0]
        target.update({"status": "NOT_REVIEWED", "rationale": "待评审", "finding_ids": []})
        package = {
            "new_findings": [{
                "finding_id": "FND-NEW", "code": "CROSS_SOURCE_CONFLICT", "severity": "REJECT",
                "certainty": "confirmed", "evidence_type": "CONFLICT", "evidence": "同一操作在两处定义相反",
                "source_refs": ["SRC-001:L1", "SRC-001:L2"], "requirement_ids": ["REQ-001"],
                "affected_test_dimensions": ["functional"],
                "question": "以哪一处为准？", "recommendation": "明确唯一规则",
            }],
            "assessment_reviews": [{
                "requirement_id": "REQ-001", "dimension": target["dimension"], "status": "FINDING",
                "rationale": "原文存在相反规则", "finding_ids": ["FND-NEW"],
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            review_path, package_path, out_path = base / "review.json", base / "package.json", base / "out.json"
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            package_path.write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(RESOLUTION_SCRIPT), "--review", str(review_path), "--resolutions", str(package_path), "--out", str(out_path)], check=True)
            merged = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(merged["findings"][0]["finding_id"], "FND-NEW")
            self.assertEqual(merged["audit"]["verdict"], "REJECT")
            self.assertEqual(merged["requirement_assessments"][0]["finding_ids"], ["FND-NEW"])

    def test_validator_rejects_cross_requirement_finding_binding(self) -> None:
        review = two_requirement_review()
        finding = {
            "finding_id": "FND-OTHER", "code": "AMBIGUOUS_LANGUAGE", "severity": "REVIEW",
            "certainty": "risk", "evidence_type": "QUOTE", "evidence": "系统返回申请编号",
            "source_refs": ["SRC-001:L1"], "requirement_ids": ["REQ-002"],
            "affected_test_dimensions": ["functional"],
        }
        review["findings"] = [finding]
        review["requirement_assessments"][0].update(status="FINDING", finding_ids=["FND-OTHER"])
        review["assessments"][0].update(status="FINDING", finding_ids=["FND-OTHER"])
        review["audit"].update(verdict="PASS_WITH_REVIEW", downstream_eligible=False)
        review["meta"]["lifecycle_status"] = "REVIEW_REQUIRED"
        errors, _ = MODULE.validate(review, "系统返回申请编号")
        self.assertIn(
            "requirement_assessment[0] references a finding outside its requirement scope",
            errors,
        )

    def test_confirm_candidate_records_semantic_review_and_adds_verified_scope(self) -> None:
        review = two_requirement_review()
        review["findings"] = [{
            "finding_id": "FND-CANDIDATE", "code": "AMBIGUOUS_LANGUAGE", "severity": "REVIEW",
            "certainty": "risk", "origin": "deterministic_candidate", "evidence_type": "QUOTE",
            "evidence": "系统返回申请编号", "source_refs": ["SRC-001:L1"],
            "requirement_ids": ["REQ-002"], "affected_test_dimensions": ["functional"],
        }]
        target = review["requirement_assessments"][0]
        target.update(status="NOT_REVIEWED", rationale="待语义评审", finding_ids=[])
        review["audit"].update(verdict="PASS_WITH_REVIEW", downstream_eligible=False)
        review["meta"]["lifecycle_status"] = "REVIEW_REQUIRED"
        package = {
            "resolutions": [{
                "finding_id": "FND-CANDIDATE", "decision": "CONFIRM",
                "resolution": "AI 回读原文后确认该问题也影响提交申请。",
                "source_refs": ["SRC-001:L1"], "add_requirement_ids": ["REQ-001"],
            }],
            "assessment_reviews": [{
                "requirement_id": "REQ-001", "dimension": target["dimension"], "status": "FINDING",
                "rationale": "原文复核确认问题适用", "finding_ids": ["FND-CANDIDATE"],
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            review_path, package_path, out_path = base / "review.json", base / "package.json", base / "out.json"
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            package_path.write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(RESOLUTION_SCRIPT), "--review", str(review_path), "--resolutions", str(package_path), "--out", str(out_path)], check=True)
            merged = json.loads(out_path.read_text(encoding="utf-8"))
        candidate = merged["findings"][0]
        self.assertEqual(candidate["certainty"], "confirmed")
        self.assertEqual(candidate["origin"], "semantic_review")
        self.assertIn("REQ-001", candidate["requirement_ids"])
        self.assertEqual(candidate["semantic_review"]["decision"], "CONFIRM")
        errors, _ = MODULE.validate(merged, "系统返回申请编号")
        self.assertEqual(errors, [])

    def test_source_unit_and_audit_statistics_are_recomputed(self) -> None:
        review = accepted_review()
        review["source_units"][0]["status"] = "review_required"
        review["source_unit_dispositions"][0].update({"disposition": "review_required", "requirement_ids": [], "reason": "待语义处置"})
        review["coverage"]["source_coverage"].update({"processed_units": 0, "review_required_units": 1})
        review["coverage"]["unresolved_source_unit_count"] = 1
        review["requirement_assessments"][0].update({"status": "NOT_REVIEWED", "rationale": "待评审"})
        review["audit"] = {"verdict": "PASS_WITH_REVIEW", "downstream_eligible": False, "errors": ["陈旧错误"], "warnings": ["陈旧统计"]}
        review["meta"]["lifecycle_status"] = "REVIEW_REQUIRED"
        package = {
            "source_unit_reviews": [{
                "unit_id": "UNIT-001", "disposition": "requirement", "requirement_ids": ["REQ-001"],
                "finding_ids": [], "reason": "已确认映射到提交申请需求",
            }],
            "assessment_reviews": [{
                "requirement_id": "REQ-001", "dimension": review["requirement_assessments"][0]["dimension"],
                "status": "CLEAR", "rationale": "原文已给出明确行为", "finding_ids": [],
                "source_refs": ["SRC-001:L1"],
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            review_path, package_path, out_path = base / "review.json", base / "package.json", base / "out.json"
            review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            package_path.write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(RESOLUTION_SCRIPT), "--review", str(review_path), "--resolutions", str(package_path), "--out", str(out_path)], check=True)
            merged = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(merged["coverage"]["unresolved_source_unit_count"], 0)
        self.assertEqual(merged["coverage"]["source_coverage"]["processed_units"], 1)
        self.assertEqual(merged["audit"]["warnings"], [])
        self.assertEqual(merged["audit"]["errors"], [])
        self.assertEqual(merged["audit"]["verdict"], "PASS")
