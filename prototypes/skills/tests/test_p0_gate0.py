"""P0 regression tests for the Gate 0 requirement-to-coverage chain."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[1]


def load_script(skill: str, script: str):
    path = SKILLS_ROOT / skill / "scripts" / script
    spec = importlib.util.spec_from_file_location(f"p0_{skill.replace('-', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coverage = load_script("coverage-analyzer", "coverage.py")
compiler = load_script("requirement-compiler", "compile_check.py")
ir_validator = load_script("ir-validator", "validate.py")
state_machine = load_script("state-machine-builder", "sm_check.py")
business_rule = load_script("business-rule-extractor", "rule_check.py")
assertion_generator = load_script("assertion-generator", "batch_check.py")


class CoverageAnalyzerTests(unittest.TestCase):
    def test_rejected_assertions_remain_in_denominator_and_block_gate(self):
        snapshot = {
            "assertion_verdicts": [
                {"assertion_id": "A-1", "skill11_verdict": "PASS"},
                {"assertion_id": "A-2", "skill11_verdict": "REJECT"},
                {"assertion_id": "A-3", "skill11_verdict": "REJECT"},
                {"assertion_id": "A-4", "skill11_verdict": "REJECT"},
            ]
        }
        result = coverage.analyze(
            snapshot,
            {
                "gate_thresholds": {
                    "rule": 0,
                    "scenario": 0,
                    "state": 0,
                    "assertion": 0.2,
                }
            },
        )

        assertion = result["dimensions"]["assertion"]
        self.assertEqual(4, assertion["denominator"])
        self.assertEqual(3, assertion["reject"])
        self.assertEqual(0.25, assertion["coverage"])
        self.assertEqual("FAIL", assertion["verdict"])
        self.assertEqual("GATE_FAILURE", result["overall_verdict"])

    def test_unbound_pass_verdicts_cannot_inflate_required_assertion_coverage(self):
        snapshot = {
            "assertions": [{"assertion_id": "REQUIRED"}],
            "assertion_verdicts": [
                {"assertion_id": f"EXTRA-{index}", "skill11_verdict": "PASS"}
                for index in range(100)
            ],
        }
        strategy = {
            "gate_thresholds": {"assertion": 0.85},
            "not_applicable_dimensions": ["rule", "scenario", "state"],
        }

        result = coverage.analyze(snapshot, strategy)

        assertion = result["dimensions"]["assertion"]
        self.assertEqual(0, assertion["numerator"])
        self.assertEqual(1, assertion["denominator"])
        self.assertEqual(100, len(assertion["unexpected_verdict_ids"]))
        self.assertEqual("FAIL", assertion["verdict"])

    def test_gate_compares_unrounded_coverage(self):
        assertions = [{"assertion_id": f"A-{index}"} for index in range(2500)]
        verdicts = [
            {
                "assertion_id": f"A-{index}",
                "skill11_verdict": "PASS" if index < 2124 else "REPAIR",
            }
            for index in range(2500)
        ]
        result = coverage.analyze(
            {"assertions": assertions, "assertion_verdicts": verdicts},
            {
                "gate_thresholds": {"assertion": 0.85},
                "not_applicable_dimensions": ["rule", "scenario", "state"],
            },
        )

        self.assertEqual(0.85, result["dimensions"]["assertion"]["coverage"])
        self.assertEqual("FAIL", result["dimensions"]["assertion"]["verdict"])

    def test_empty_dimensions_fail_without_explicit_not_applicable_declaration(self):
        result = coverage.analyze(
            {}, {"gate_thresholds": {name: 0 for name in coverage.DEFAULT_THRESHOLDS}}
        )

        self.assertEqual("GATE_FAILURE", result["overall_verdict"])
        self.assertTrue(
            all(item["verdict"] == "FAIL" for item in result["dimensions"].values())
        )

    def test_duplicate_verdict_id_is_blocking_evidence_error(self):
        result = coverage.analyze(
            {
                "assertions": [{"assertion_id": "A-1"}],
                "assertion_verdicts": [
                    {"assertion_id": "A-1", "skill11_verdict": "PASS"},
                    {"assertion_id": "A-1", "skill11_verdict": "PASS"},
                ],
            },
            {
                "not_applicable_dimensions": ["rule", "scenario", "state"],
                "gate_thresholds": {"assertion": 0.1},
            },
        )

        assertion = result["dimensions"]["assertion"]
        self.assertEqual(["A-1"], assertion["duplicate_verdict_ids"])
        self.assertEqual(0, assertion["numerator"])
        self.assertEqual("FAIL", assertion["verdict"])

    def test_invalid_threshold_configuration_fails_gate(self):
        result = coverage.analyze(
            {},
            {
                "not_applicable_dimensions": [
                    "rule",
                    "scenario",
                    "state",
                    "assertion",
                ],
                "gate_thresholds": {"assertion": float("nan")},
            },
        )

        self.assertEqual("GATE_FAILURE", result["overall_verdict"])
        self.assertIn(
            "INVALID_GATE_THRESHOLDS",
            {item.get("code") for item in result["gate_failures"]},
        )

    def test_not_applicable_cannot_hide_malformed_snapshot(self):
        result = coverage.analyze(
            {"assertions": "bad"},
            {"not_applicable_dimensions": list(coverage.DEFAULT_THRESHOLDS)},
        )

        self.assertEqual("GATE_FAILURE", result["overall_verdict"])
        self.assertEqual("FAIL", result["dimensions"]["assertion"]["verdict"])

    def test_not_applicable_cannot_hide_non_object_snapshot_root(self):
        result = coverage.analyze(
            [],
            {"not_applicable_dimensions": list(coverage.DEFAULT_THRESHOLDS)},
        )

        self.assertEqual("GATE_FAILURE", result["overall_verdict"])
        self.assertIn(
            "INVALID_SNAPSHOT",
            {item.get("code") for item in result["gate_failures"]},
        )


class RequirementCompilerTests(unittest.TestCase):
    def test_empty_packet_rejects(self):
        result = compiler.check_compilation({})

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "EMPTY_SOURCE_MANIFEST", {item["code"] for item in result["findings"]}
        )
        self.assertIn("EMPTY_IR_DRAFT", {item["code"] for item in result["findings"]})

    def test_expected_missing_source_degrades_prd_only_packet(self):
        packet = {
            "declared_sources": [
                {"source_id": "prd.md", "availability": "AVAILABLE"},
                {"source_id": "api.yaml", "availability": "EXPECTED_MISSING"},
            ],
            "ir_draft": {
                "requirements": [
                    {
                        "req_id": "REQ-001",
                        "source_trace": "prd.md§1",
                        "confidence": 0.73,
                    }
                ]
            },
        }

        result = compiler.check_compilation(packet)

        self.assertEqual("PASS_WITH_REVIEW", result["verdict"])
        finding = next(
            item for item in result["findings"] if item["code"] == "SOURCE_UNAVAILABLE"
        )
        self.assertEqual("REVIEW", finding["severity"])

    def test_non_object_root_rejects_without_crashing(self):
        result = compiler.check_compilation([])

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_COMPILATION_PACKET", {item["code"] for item in result["findings"]}
        )

    def test_invalid_source_availability_shape_rejects_without_crashing(self):
        result = compiler.check_compilation(
            {
                "declared_sources": [{"source_id": "prd", "availability": []}],
                "ir_draft": {"requirements": []},
            }
        )

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_SOURCE_AVAILABILITY",
            {item["code"] for item in result["findings"]},
        )

    def test_dropped_source_findings_are_sorted(self):
        result = compiler.check_compilation(
            {
                "declared_sources": ["c", "a", "b"],
                "ir_draft": {
                    "requirements": [
                        {"req_id": "R", "source_trace": "a§1", "confidence": 0.8}
                    ]
                },
            }
        )

        dropped = [
            item["target"]
            for item in result["findings"]
            if item["code"] == "SOURCE_SILENTLY_DROPPED"
        ]
        self.assertEqual(["b", "c"], dropped)


class StateMachineTests(unittest.TestCase):
    def test_non_object_state_machine_root_rejects_without_crashing(self):
        result = state_machine.check_state_machines([])

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_STATE_MACHINE_PACKET",
            {item["code"] for item in result["findings"]},
        )

    def test_empty_declared_states_cannot_hide_invented_transition_states(self):
        packet = {
            "known_entity_ids": ["ENT-ORD-001"],
            "state_machines": [
                {
                    "sm_id": "SM-ORD-001",
                    "entity_id": "ENT-ORD-001",
                    "initial_state": "INVENTED_A",
                    "states": [],
                    "transitions": [
                        {"from": "INVENTED_A", "to": "INVENTED_B", "guard": None}
                    ],
                }
            ],
        }

        result = state_machine.check_state_machines(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn("EMPTY_STATE_SET", {item["code"] for item in result["findings"]})

    def test_missing_initial_state_rejects_in_ir_validator(self):
        ir = {
            "ir_version": "1.0.0",
            "state_machines": [
                {
                    "sm_id": "SM-ORD-001",
                    "entity_id": "ENT-ORD-001",
                    "states": ["A", "B"],
                    "transitions": [{"from": "A", "to": "B", "guard": None}],
                    "terminal_states": ["B"],
                }
            ],
        }

        result = ir_validator.validate(ir)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "MISSING_INITIAL_STATE", {item["code"] for item in result["findings"]}
        )

    def test_transition_missing_endpoint_rejects_without_crashing(self):
        ir = {
            "ir_version": "1.0.0",
            "requirements": [],
            "business_rules": [],
            "entities": [],
            "interface_contracts": [],
            "constraints": [],
            "state_machines": [
                {
                    "sm_id": "SM-001",
                    "entity_id": "ENT-001",
                    "initial_state": "A",
                    "states": ["A"],
                    "transitions": [{"from": "A"}],
                    "terminal_states": ["A"],
                }
            ],
        }

        result = ir_validator.validate(ir)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "MISSING_TRANSITION_ENDPOINT", {item["code"] for item in result["findings"]}
        )

    def test_empty_ir_model_and_malformed_version_reject(self):
        empty_result = ir_validator.validate({"ir_version": "1.0.0"})
        version_result = ir_validator.validate(
            {
                "ir_version": "1.0evil",
                **{name: [] for name in ir_validator.FROZEN_V1_MODELS},
            }
        )

        self.assertEqual("REJECT", empty_result["verdict"])
        self.assertIn(
            "MISSING_REQUIRED_MODEL_CLASS",
            {item["code"] for item in empty_result["findings"]},
        )
        self.assertEqual("REJECT", version_result["verdict"])
        self.assertIn(
            "UNKNOWN_IR_VERSION", {item["code"] for item in version_result["findings"]}
        )

    def test_six_present_but_empty_ir_models_reject(self):
        result = ir_validator.validate(
            {
                "ir_version": "1.0.0",
                **{name: [] for name in ir_validator.FROZEN_V1_MODELS},
            }
        )

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "EMPTY_REQUIREMENTS", {item["code"] for item in result["findings"]}
        )

    def test_boolean_confidence_is_not_numeric_evidence(self):
        ir = {
            "ir_version": "1.0.0",
            "requirements": [
                {
                    "req_id": "R",
                    "title": "t",
                    "description": "d",
                    "validation_status": "VALIDATED",
                    "source_trace": "prd",
                    "confidence": True,
                }
            ],
            "business_rules": [],
            "entities": [],
            "interface_contracts": [],
            "constraints": [],
            "state_machines": [],
        }

        result = ir_validator.validate(ir)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_CONFIDENCE_TYPE", {item["code"] for item in result["findings"]}
        )

    def test_non_scalar_state_values_reject_without_crashing(self):
        state_result = state_machine.check_state_machines(
            {"known_entity_ids": [{}], "state_machines": []}
        )
        builder_initial_result = state_machine.check_state_machines(
            {
                "known_entity_ids": ["E"],
                "state_machines": [
                    {
                        "sm_id": "SM",
                        "entity_id": "E",
                        "initial_state": [],
                        "states": ["A"],
                        "transitions": [],
                    }
                ],
            }
        )
        ir_result = ir_validator.validate(
            {
                "ir_version": "1.0.0",
                "requirements": [
                    {
                        "req_id": "R",
                        "title": "t",
                        "description": "d",
                        "validation_status": "VALIDATED",
                        "source_trace": "prd",
                        "confidence": 0.8,
                    }
                ],
                "business_rules": [],
                "entities": [],
                "interface_contracts": [],
                "constraints": [],
                "state_machines": [
                    {
                        "sm_id": "SM",
                        "entity_id": "E",
                        "initial_state": [],
                        "states": ["A"],
                        "transitions": [{"from": "A", "to": []}],
                    }
                ],
            }
        )

        self.assertEqual("REJECT", state_result["verdict"])
        self.assertEqual("REJECT", builder_initial_result["verdict"])
        self.assertEqual("REJECT", ir_result["verdict"])


class BusinessRuleTests(unittest.TestCase):
    def test_non_object_rule_item_rejects_without_crashing(self):
        result = business_rule.check_rules({"rules": ["bad"]})

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn("INVALID_RULE", {item["code"] for item in result["findings"]})

    def test_inferred_rule_without_human_route_rejects(self):
        packet = {
            "rules": [
                {
                    "rule_id": "BR-001",
                    "condition": "order.total > 0",
                    "action": "accept order",
                    "source": "prd.md§2",
                    "inferred": True,
                    "confidence": 0.8,
                }
            ]
        }

        result = business_rule.check_rules(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INFERRED_RULE_MISSING_REVIEW_ROUTE",
            {item["code"] for item in result["findings"]},
        )

    def test_inferred_rule_non_numeric_confidence_rejects(self):
        packet = {
            "rules": [
                {
                    "rule_id": "BR-002",
                    "condition": "order.total > 0",
                    "action": "accept order",
                    "source": "inferred",
                    "confidence": "0.99",
                }
            ]
        }

        result = business_rule.check_rules(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_INFERRED_CONFIDENCE", {item["code"] for item in result["findings"]}
        )


class AssertionGeneratorTests(unittest.TestCase):
    def test_e2e_list_format_is_a_valid_assertion_batch(self):
        assertions = [
            {
                "assertion_id": "A-001",
                "target": "response.status",
                "expression": "eq",
                "expected": "PARSED",
            }
        ]

        result = assertion_generator.check_batch(assertions)

        self.assertEqual(1, result["total_assertions"])
        self.assertEqual("PASS", result["verdict"])

    def test_missing_expression_and_expected_rejects(self):
        result = assertion_generator.check_batch(
            [{"assertion_id": "A-002", "target": "response.value"}]
        )

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_ASSERTION_STRUCTURE", {item["code"] for item in result["findings"]}
        )


class RequirementQualityGateTests(unittest.TestCase):
    @staticmethod
    def _gate():
        return load_script("requirement-quality-gate", "gate_check.py")

    @staticmethod
    def _complete_review():
        dimensions = [
            "ambiguity",
            "consistency",
            "testability",
            "completeness",
            "nfr_measurability",
            "role_permission",
        ]
        return {
            "review_id": "RQR-001",
            "source_ids": ["prd.md"],
            "assessments": [
                {
                    "dimension": dimension,
                    "status": "CLEAR",
                    "rationale": "Reviewed against prd.md§1; no issue found.",
                    "finding_ids": [],
                }
                for dimension in dimensions
            ],
            "findings": [],
        }

    def test_missing_required_quality_dimension_rejects(self):
        gate = self._gate()
        packet = self._complete_review()
        packet["assessments"] = packet["assessments"][:-1]

        result = gate.check_review(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "MISSING_QUALITY_DIMENSION", {item["code"] for item in result["findings"]}
        )

    def test_cross_source_conflict_cannot_be_downgraded_to_review(self):
        gate = self._gate()
        packet = self._complete_review()
        conflict = {
            "finding_id": "RQF-001",
            "code": "CROSS_SOURCE_CONFLICT",
            "severity": "REVIEW",
            "source_refs": ["prd.md§2", "prd.md§8"],
            "evidence": "refund actor is user in §2 and admin-only in §8",
            "question": "Which actor is authoritative?",
        }
        packet["findings"] = [conflict]
        assessment = next(
            item for item in packet["assessments"] if item["dimension"] == "consistency"
        )
        assessment.update({"status": "FINDING", "finding_ids": ["RQF-001"]})

        result = gate.check_review(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_SEVERITY_FOR_CODE", {item["code"] for item in result["findings"]}
        )

    def test_evidence_bound_ambiguity_routes_to_review(self):
        gate = self._gate()
        packet = self._complete_review()
        ambiguity = {
            "finding_id": "RQF-002",
            "code": "AMBIGUOUS_LANGUAGE",
            "severity": "REVIEW",
            "source_refs": ["prd.md§4"],
            "evidence": "system should respond promptly",
            "question": "What measurable response-time objective applies?",
        }
        packet["findings"] = [ambiguity]
        assessment = next(
            item for item in packet["assessments"] if item["dimension"] == "ambiguity"
        )
        assessment.update({"status": "FINDING", "finding_ids": ["RQF-002"]})

        result = gate.check_review(packet)

        self.assertEqual("PASS_WITH_REVIEW", result["verdict"])
        self.assertEqual(1, result["review_findings"])

    def test_source_ids_must_be_an_array(self):
        gate = self._gate()
        packet = self._complete_review()
        packet["source_ids"] = "prd.md"

        result = gate.check_review(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_SOURCE_SET", {item["code"] for item in result["findings"]}
        )

    def test_finding_ids_must_be_strings(self):
        gate = self._gate()
        packet = self._complete_review()
        packet["assessments"][0]["status"] = "FINDING"
        packet["assessments"][0]["finding_ids"] = [[]]

        result = gate.check_review(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_FINDING_REFS", {item["code"] for item in result["findings"]}
        )


if __name__ == "__main__":
    unittest.main()
