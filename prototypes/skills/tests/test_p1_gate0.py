"""P1 regressions for the remaining Gate 0 design validators."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[1]


def load_script(skill: str, script: str):
    path = SKILLS_ROOT / skill / "scripts" / script
    spec = importlib.util.spec_from_file_location(f"p1_{skill.replace('-', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


domain = load_script("domain-model-extractor", "entity_check.py")
strategy = load_script("strategy-planner", "strategy_check.py")
scenario = load_script("scenario-generator", "scenario_check.py")
case_generator = load_script("test-case-generator", "case_check.py")


def clean_strategy():
    return {
        "Critical_Paths": [
            {
                "path_id": "test-design-publish",
                "disposition": "IN_SCOPE",
                "feature_ids": ["F-TD-001"],
            }
        ],
        "In_Scope": [
            {
                "feature_id": "F-TD-001",
                "feature": "publish reviewed test design",
                "risk_level": "high",
            }
        ],
        "Out_Of_Scope": [],
        "Quality_Gates": [
            {"gate_name": "effective_coverage", "metric": "coverage", "threshold": 0.85}
        ],
        "Pyramid_Distribution": {"unit": 0.6, "integration": 0.3, "e2e": 0.1},
        "Mock_Policy": {
            "mock_targets": ["email_provider"],
            "no_mock_targets": ["database"],
        },
    }


def clean_ir():
    return {
        "requirements": [{"req_id": "REQ-001"}, {"req_id": "REQ-002"}],
        "business_rules": [{"rule_id": "RULE-001"}],
        "interface_contracts": [
            {"contract_id": "IFC-001", "endpoint": "/designs", "method": "POST"}
        ],
        "state_machines": [
            {
                "sm_id": "SM-001",
                "entity_id": "ENT-TD-001",
                "states": ["DRAFT", "APPROVED"],
                "transitions": [{"from": "DRAFT", "to": "APPROVED"}],
            }
        ],
    }


def clean_scenario():
    return {
        "scenario_id": "S-td-001",
        "req_id": "REQ-001",
        "rule_id": "RULE-001",
        "facet": "normal",
        "title": "publish a reviewed design",
    }


def clean_case():
    return {
        "case_id": "TC-td-001",
        "req_id": "REQ-001",
        "rule_id": "RULE-001",
        "scenario_id": "S-td-001",
        "fixture_category": "Static",
        "entity_id": "ENT-TD-001",
        "steps": [{"action": "publish", "endpoint": "/designs", "input": {}}],
        "expected_results": [{"state": "APPROVED", "endpoint": "/designs"}],
    }


class DomainModelExtractorTests(unittest.TestCase):
    def test_explicit_null_reference_rejects(self):
        packet = {
            "entities": [
                {
                    "entity_id": "ENT-AAA-001",
                    "name": "A",
                    "fields": [{"name": "id", "type": "string", "references": None}],
                }
            ]
        }

        result = domain.check_entities(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_ENTITY_REF", {item["code"] for item in result["findings"]}
        )

    def test_whitespace_wrapped_unknown_type_rejects(self):
        packet = {
            "entities": [
                {
                    "entity_id": "ENT-AAA-001",
                    "name": "A",
                    "fields": [{"name": "id", "type": " unknown "}],
                }
            ]
        }

        result = domain.check_entities(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn("UNTYPED_FIELD", {item["code"] for item in result["findings"]})

    def test_blank_field_name_rejects(self):
        packet = {
            "entities": [
                {
                    "entity_id": "ENT-AAA-001",
                    "name": "A",
                    "fields": [{"name": "   ", "type": "string"}],
                }
            ]
        }

        result = domain.check_entities(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "MISSING_FIELD_NAME", {item["code"] for item in result["findings"]}
        )

    def test_dual_reference_aliases_reject(self):
        packet = {
            "entities": [
                {
                    "entity_id": "ENT-AAA-001",
                    "name": "A",
                    "fields": [
                        {
                            "name": "id",
                            "type": "string",
                            "references": "ENT-AAA-001",
                            "fk_reference": [],
                        }
                    ],
                }
            ]
        }

        result = domain.check_entities(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "AMBIGUOUS_ENTITY_REF", {item["code"] for item in result["findings"]}
        )

    def test_non_object_root_rejects_without_crashing(self):
        result = domain.check_entities([])

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_ENTITY_PACKET", {item["code"] for item in result["findings"]}
        )

    def test_empty_fields_and_duplicate_field_names_reject(self):
        result = domain.check_entities(
            {
                "entities": [
                    {"entity_id": "ENT-AAA-001", "name": "Empty", "fields": []},
                    {
                        "entity_id": "ENT-BBB-001",
                        "name": "Duplicate",
                        "fields": [
                            {"name": "id", "type": "string"},
                            {"name": "id", "type": "integer"},
                        ],
                    },
                ]
            }
        )

        codes = {item["code"] for item in result["findings"]}
        self.assertEqual("REJECT", result["verdict"])
        self.assertIn("EMPTY_ENTITY_FIELDS", codes)
        self.assertIn("DUPLICATE_FIELD_NAME", codes)

    def test_non_string_reference_rejects_without_crashing(self):
        result = domain.check_entities(
            {
                "entities": [
                    {
                        "entity_id": "ENT-AAA-001",
                        "name": "A",
                        "fields": [
                            {"name": "b_id", "type": "string", "references": []}
                        ],
                    }
                ]
            }
        )

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_ENTITY_REF", {item["code"] for item in result["findings"]}
        )


class StrategyPlannerTests(unittest.TestCase):
    def test_false_optional_scope_collection_rejects(self):
        packet = clean_strategy()
        packet["Out_Of_Scope"] = False

        result = strategy.check_strategy(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_STRATEGY_COLLECTION",
            {item["code"] for item in result["findings"]},
        )

    def test_non_scalar_disposition_rejects_without_crashing(self):
        packet = clean_strategy()
        packet["Critical_Paths"][0]["disposition"] = []

        result = strategy.check_strategy(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_CRITICAL_PATH_DISPOSITION",
            {item["code"] for item in result["findings"]},
        )

    def test_blank_strategy_identifiers_reject(self):
        packet = clean_strategy()
        packet["In_Scope"][0]["feature_id"] = "   "
        packet["Critical_Paths"][0]["path_id"] = "   "
        packet["Critical_Paths"][0]["feature_ids"] = ["   "]
        packet["Quality_Gates"][0]["gate_name"] = "   "

        result = strategy.check_strategy(packet)

        codes = {item["code"] for item in result["findings"]}
        self.assertEqual("REJECT", result["verdict"])
        self.assertIn("MISSING_FEATURE_ID", codes)
        self.assertIn("MISSING_CRITICAL_PATH_ID", codes)
        self.assertIn("MISSING_GATE_NAME", codes)

    def test_false_mock_target_collection_rejects(self):
        packet = clean_strategy()
        packet["Mock_Policy"]["mock_targets"] = False

        result = strategy.check_strategy(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_MOCK_TARGETS", {item["code"] for item in result["findings"]}
        )

    def test_project_declared_critical_path_passes_without_payment_assumption(self):
        result = strategy.check_strategy(clean_strategy())

        self.assertEqual("PASS", result["verdict"])

    def test_critical_path_must_bind_to_in_scope_feature(self):
        packet = clean_strategy()
        packet["Critical_Paths"][0]["feature_ids"] = ["F-MISSING"]

        result = strategy.check_strategy(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "CRITICAL_PATH_FEATURE_NOT_IN_SCOPE",
            {item["code"] for item in result["findings"]},
        )

    def test_boolean_threshold_rejects(self):
        packet = clean_strategy()
        packet["Quality_Gates"][0]["threshold"] = True

        result = strategy.check_strategy(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "GATE_THRESHOLD_NON_NUMERIC", {item["code"] for item in result["findings"]}
        )

    def test_invalid_pyramid_shape_rejects_without_crashing(self):
        packet = clean_strategy()
        packet["Pyramid_Distribution"]["e2e"] = "many"

        result = strategy.check_strategy(packet)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_PYRAMID_VALUE", {item["code"] for item in result["findings"]}
        )


class ScenarioGeneratorTests(unittest.TestCase):
    def test_non_scalar_facet_rejects_without_crashing(self):
        scen = clean_scenario()
        scen["facet"] = []

        result = scenario.check_graph([scen], clean_ir())

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn("MISSING_FACET", {item["code"] for item in result["findings"]})

    def test_empty_scenario_graph_rejects(self):
        ir = clean_ir()
        ir["state_machines"] = []

        result = scenario.check_graph([], ir)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "EMPTY_SCENARIO_SET", {item["code"] for item in result["findings"]}
        )

    def test_unknown_requirement_rejects(self):
        scen = clean_scenario()
        scen["req_id"] = "REQ-MISSING"

        result = scenario.check_graph([scen], clean_ir())

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "REQUIREMENT_NOT_IN_IR", {item["code"] for item in result["findings"]}
        )

    def test_non_object_scenario_rejects_without_crashing(self):
        result = scenario.check_graph(["bad"], clean_ir())

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn("INVALID_SCENARIO", {item["code"] for item in result["findings"]})

    def test_non_scalar_transition_endpoint_rejects_without_crashing(self):
        ir = clean_ir()
        ir["state_machines"][0]["transitions"] = [{"from": "DRAFT", "to": []}]

        result = scenario.check_graph([clean_scenario()], ir)

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_IR_TRANSITION", {item["code"] for item in result["findings"]}
        )


class TestCaseGeneratorTests(unittest.TestCase):
    def test_scenario_without_trace_bindings_rejects(self):
        result = case_generator.check_cases(
            [clean_case()], clean_ir(), [{"scenario_id": "S-td-001"}]
        )

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn("INVALID_SCENARIO", {item["code"] for item in result["findings"]})

    def test_empty_case_batch_rejects(self):
        result = case_generator.check_cases([], clean_ir(), [clean_scenario()])

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn("EMPTY_CASE_SET", {item["code"] for item in result["findings"]})

    def test_case_binding_must_match_bound_scenario(self):
        test_case = clean_case()
        test_case["req_id"] = "REQ-002"

        result = case_generator.check_cases([test_case], clean_ir(), [clean_scenario()])

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "CASE_SCENARIO_BINDING_MISMATCH",
            {item["code"] for item in result["findings"]},
        )

    def test_missing_steps_and_expected_results_reject(self):
        test_case = clean_case()
        test_case["steps"] = []
        test_case["expected_results"] = []

        result = case_generator.check_cases([test_case], clean_ir(), [clean_scenario()])

        codes = {item["code"] for item in result["findings"]}
        self.assertEqual("REJECT", result["verdict"])
        self.assertIn("EMPTY_CASE_STEPS", codes)
        self.assertIn("EMPTY_EXPECTED_RESULTS", codes)

    def test_unknown_step_endpoint_rejects(self):
        test_case = clean_case()
        test_case["steps"][0]["endpoint"] = "/invented"

        result = case_generator.check_cases([test_case], clean_ir(), [clean_scenario()])

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "STEP_ENDPOINT_NOT_IN_IR", {item["code"] for item in result["findings"]}
        )

    def test_malformed_expected_result_rejects_without_crashing(self):
        test_case = clean_case()
        test_case["expected_results"] = ["bad"]

        result = case_generator.check_cases([test_case], clean_ir(), [clean_scenario()])

        self.assertEqual("REJECT", result["verdict"])
        self.assertIn(
            "INVALID_EXPECTED_RESULT", {item["code"] for item in result["findings"]}
        )


if __name__ == "__main__":
    unittest.main()
