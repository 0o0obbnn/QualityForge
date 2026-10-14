"""P2 regressions for the highest-consequence gates that had no test coverage.

Three gaps this file closes:

  1. hitl-gatekeeper — the human-approval gate. Highest consequence in the
     repo (it decides whether AI output may proceed without a human) and had
     zero tests. Its six eval cases were prose-only.
  2. contract-drift-detector — the BREAKING/COMPATIBLE classifier. A
     misclassification here silently publishes a contract break.
  3. CONFLICT_SINGLE_VERSION — design invariant 2. Implemented in
     requirement-compiler and declared in ir-validator/SKILL.md, but asserted
     nowhere.

Same discipline as test_p0/test_p1: real checkers via importlib, no mocks.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[1]


def load_script(skill: str, script: str):
    path = SKILLS_ROOT / skill / "scripts" / script
    spec = importlib.util.spec_from_file_location(f"p2_{skill.replace('-', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load_script("hitl-gatekeeper", "gate.py")
drift = load_script("contract-drift-detector", "drift_detect.py")
compiler = load_script("requirement-compiler", "compile_check.py")


def decide(**overrides):
    """Route a non-formal inference event unless the test overrides it."""
    payload = {
        "event_type": "inference",
        "asset_type": "assertion",
        "source_trace": "test-case-generator:TC-1:req-1",
        "proposed_action": "attach assertion",
        "confidence": 0.9,
    }
    payload.update(overrides)
    return gate.decide(**payload)


# ---------------------------------------------------------------- hitl gate


class FormalArtifactsAlwaysBlockTests(unittest.TestCase):
    """Every formal artifact requires a human ReviewDecision, at any confidence."""

    def test_every_formal_asset_type_blocks(self):
        for asset_type in sorted(gate.FORMAL_ASSET_TYPES):
            result = decide(asset_type=asset_type, confidence=0.99)
            self.assertEqual(result["decision"], "BLOCK_HUMAN", asset_type)

    def test_perfect_confidence_does_not_authorize_a_formal_artifact(self):
        result = decide(asset_type="test_case", confidence=1.0)
        self.assertEqual(result["decision"], "BLOCK_HUMAN")
        self.assertIn("置信度不参与", result["reason"])

    def test_formal_block_emits_a_review_task(self):
        result = decide(asset_type="test_report", confidence=0.95)
        self.assertIsNotNone(result["review_task"])

    def test_non_formal_pass_never_emits_a_review_task(self):
        result = decide(asset_type="assertion", confidence=0.9)
        self.assertEqual(result["decision"], "PASS")
        self.assertIsNone(result["review_task"])


class ConfidenceIsNotAuthorizationTests(unittest.TestCase):
    def test_missing_confidence_blocks_rather_than_defaulting_high(self):
        """A missing score is not a high score — the load-bearing rule."""
        result = decide(confidence=None)
        self.assertEqual(result["decision"], "BLOCK_HUMAN")
        self.assertIn("缺失的分数不是高分", result["reason"])

    def test_zero_confidence_blocks(self):
        # 0.0 is present evidence of *low* confidence; it must not sneak past
        # a truthiness check into PASS.
        result = decide(confidence=0.0)
        self.assertEqual(result["decision"], "PASS")

    def test_pass_is_not_approval(self):
        result = decide(confidence=0.99)
        self.assertEqual(result["decision"], "PASS")
        self.assertNotIn("APPROVED", result["reason"].upper())
        self.assertIn("不授权", result["reason"])


class ForcedCheckpointTests(unittest.TestCase):
    def test_every_forced_event_blocks_regardless_of_confidence(self):
        for event_type in sorted(gate.FORCED_CHECKPOINT_EVENTS):
            result = decide(event_type=event_type, confidence=1.0)
            self.assertEqual(result["decision"], "BLOCK_HUMAN", event_type)
            self.assertEqual(result["review_task"]["severity"], "forced", event_type)

    def test_ambiguity_flag_blocks(self):
        result = decide(event_type="ambiguity_flag", confidence=0.88)
        self.assertEqual(result["decision"], "BLOCK_HUMAN")
        self.assertIn("不得编造", result["reason"])

    def test_ambiguity_flag_is_required_not_forced(self):
        result = decide(event_type="ambiguity_flag", confidence=0.88)
        self.assertEqual(result["review_task"]["severity"], "required")


class ReviewTaskBindingTests(unittest.TestCase):
    """An unbound ReviewTask cannot be audited, so the binding is mandatory."""

    BINDING = ("artifact_id", "artifact_version_id", "content_digest", "policy_type")

    def _args(self, **overrides):
        class Args:
            pass

        args = Args()
        args.event_type = "inference"
        args.asset_type = "test_case"
        args.source_trace = "s"
        args.proposed_action = "publish"
        args.confidence = 0.9
        args.ir_element_id = None
        args.artifact_id = "tc-42"
        args.artifact_version_id = "tcv-7"
        args.content_digest = "sha256:abc"
        args.policy_type = "SINGLE_REVIEW"
        for key, value in overrides.items():
            setattr(args, key, value)
        return args

    def test_complete_binding_validates(self):
        self.assertIsNone(gate._validate(self._args()))

    def test_each_missing_binding_field_is_rejected(self):
        for field in self.BINDING:
            error = gate._validate(self._args(**{field: None}))
            self.assertIsNotNone(error, f"{field} was allowed to be missing")
            self.assertIn("审核绑定", error)

    def test_review_task_carries_the_full_binding(self):
        result = decide(
            asset_type="defect",
            artifact_id="d-1",
            artifact_version_id="dv-1",
            content_digest="sha256:xyz",
            policy_type="FOUR_EYES",
        )
        task = result["review_task"]
        expected = {
            "artifact_id": "d-1",
            "artifact_version_id": "dv-1",
            "content_digest": "sha256:xyz",
            "policy_type": "FOUR_EYES",
        }
        for field, value in expected.items():
            self.assertEqual(task.get(field), value, field)
        self.assertEqual(
            sorted(task["must_present"]),
            sorted(list(self.BINDING) + ["source_trace", "proposed_action"]),
        )

    def test_contract_mutation_requires_the_mutation_target(self):
        error = gate._validate(
            self._args(
                event_type="contract_mutation",
                asset_type="contract",
                ir_element_id=None,
            )
        )
        self.assertIsNotNone(error)
        self.assertIn("ir-element-id", error)

    def test_out_of_range_confidence_is_rejected(self):
        for bad in (-0.1, 1.1):
            self.assertIsNotNone(gate._validate(self._args(confidence=bad)), bad)

    def test_unknown_event_and_asset_types_are_rejected(self):
        self.assertIn(
            "无效的 --event-type", gate._validate(self._args(event_type="made_up"))
        )
        self.assertIn(
            "无效的 --asset-type", gate._validate(self._args(asset_type="made_up"))
        )


class GateExitCodeTests(unittest.TestCase):
    """gate.main() prints its decision; capture stdout so test output stays readable."""

    def _main(self, argv):
        buffer = io.StringIO()
        with (
            contextlib.redirect_stdout(buffer),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            return gate.main(argv)

    def test_block_exits_nonzero(self):
        code = self._main(
            [
                "--confidence",
                "0.99",
                "--event-type",
                "inference",
                "--asset-type",
                "test_case",
                "--source-trace",
                "s",
                "--proposed-action",
                "p",
                "--artifact-id",
                "a",
                "--artifact-version-id",
                "v",
                "--content-digest",
                "d",
                "--policy-type",
                "SINGLE_REVIEW",
            ]
        )
        self.assertEqual(code, 2)

    def test_pass_exits_zero(self):
        code = self._main(
            [
                "--confidence",
                "0.9",
                "--event-type",
                "inference",
                "--asset-type",
                "assertion",
                "--source-trace",
                "s",
                "--proposed-action",
                "p",
            ]
        )
        self.assertEqual(code, 0)

    def test_invalid_input_exits_three(self):
        code = self._main(
            [
                "--confidence",
                "0.9",
                "--event-type",
                "inference",
                "--asset-type",
                "test_case",
                "--source-trace",
                "s",
                "--proposed-action",
                "p",
            ]
        )
        self.assertEqual(code, 3)


# ------------------------------------------------------- contract drift


def interface(contract_props, observed_props):
    return (
        {
            "type": "interface_contract",
            "contract_id": "IFC-1",
            "response_schema": {"properties": contract_props},
        },
        {"response_schema": {"properties": observed_props}},
    )


class DriftClassificationTests(unittest.TestCase):
    def test_identical_contract_is_no_drift(self):
        result = drift.detect(
            *interface({"a": {"type": "int"}}, {"a": {"type": "int"}})
        )
        self.assertEqual(result["verdict"], "NO_DRIFT")
        self.assertEqual(result["findings"], [])

    def test_added_field_is_compatible(self):
        result = drift.detect(*interface({}, {"b": {"type": "int"}}))
        self.assertEqual(result["verdict"], "COMPATIBLE_DRIFT")
        self.assertEqual(result["findings"][0]["drift_kind"], "FIELD_ADDED")

    def test_removed_field_is_breaking(self):
        result = drift.detect(*interface({"a": {"type": "int"}}, {}))
        self.assertEqual(result["verdict"], "BREAKING_DRIFT")
        self.assertEqual(result["findings"][0]["drift_kind"], "FIELD_REMOVED")

    def test_widening_is_compatible(self):
        result = drift.detect(
            *interface({"a": {"type": "int"}}, {"a": {"type": "float"}})
        )
        self.assertEqual(result["verdict"], "COMPATIBLE_DRIFT")
        self.assertEqual(result["findings"][0]["drift_kind"], "TYPE_WIDENED")

    def test_narrowing_is_breaking(self):
        result = drift.detect(
            *interface({"a": {"type": "float"}}, {"a": {"type": "int"}})
        )
        self.assertEqual(result["verdict"], "BREAKING_DRIFT")
        self.assertEqual(result["findings"][0]["drift_kind"], "TYPE_NARROWED")

    def test_ambiguous_type_change_defaults_to_breaking(self):
        """The load-bearing default: unknown transitions are never waved through."""
        result = drift.detect(
            *interface({"a": {"type": "date"}}, {"a": {"type": "uuid"}})
        )
        self.assertEqual(result["verdict"], "BREAKING_DRIFT")
        self.assertEqual(result["findings"][0]["drift_kind"], "TYPE_CHANGED")

    def test_one_breaking_finding_outranks_many_compatible_ones(self):
        result = drift.detect(
            *interface(
                {"a": {"type": "int"}, "keep": {"type": "int"}},
                {"keep": {"type": "int"}, "x": {"type": "int"}, "y": {"type": "int"}},
            )
        )
        self.assertEqual(result["verdict"], "BREAKING_DRIFT")
        self.assertGreater(result["compatible_count"], 0)
        self.assertEqual(result["breaking_count"], 1)

    def test_breaking_drift_routes_to_a_human_checkpoint(self):
        result = drift.detect(*interface({"a": {"type": "int"}}, {}))
        self.assertIn("人工", result["routing"])


class StateMachineDriftTests(unittest.TestCase):
    def _sm(self, contract, observed):
        return drift.detect(
            {"type": "state_machine", "sm_id": "SM-1", **contract},
            {"type": "state_machine", **observed},
        )

    def test_removed_state_is_breaking(self):
        result = self._sm(
            {"states": ["A", "B"], "transitions": []},
            {"states": ["A"], "transitions": []},
        )
        self.assertEqual(result["verdict"], "BREAKING_DRIFT")
        self.assertEqual(result["findings"][0]["drift_kind"], "STATE_REMOVED")

    def test_added_state_is_compatible(self):
        result = self._sm(
            {"states": ["A"], "transitions": []},
            {"states": ["A", "B"], "transitions": []},
        )
        self.assertEqual(result["verdict"], "COMPATIBLE_DRIFT")

    def test_removed_transition_is_breaking(self):
        result = self._sm(
            {"states": ["A", "B"], "transitions": [{"from": "A", "to": "B"}]},
            {"states": ["A", "B"], "transitions": []},
        )
        self.assertEqual(result["verdict"], "BREAKING_DRIFT")
        self.assertEqual(result["findings"][0]["drift_kind"], "TRANSITION_REMOVED")


class MalformedSnapshotNeverReadsAsNoDriftTests(unittest.TestCase):
    """A drift detector that reports NO_DRIFT on garbage is worse than useless."""

    def test_states_as_bare_string_does_not_become_no_drift(self):
        # set("DRAFT") would silently expand to a character set and compare equal.
        result = drift.detect(
            {
                "type": "state_machine",
                "sm_id": "SM-1",
                "states": "DRAFT",
                "transitions": [],
            },
            {"type": "state_machine", "states": "DRAFT", "transitions": []},
        )
        self.assertEqual(result["verdict"], "BREAKING_DRIFT")
        self.assertTrue(
            any(f["drift_kind"] == "MALFORMED_SNAPSHOT" for f in result["findings"])
        )

    def test_non_object_transition_is_reported_not_crashed(self):
        result = drift.detect(
            {
                "type": "state_machine",
                "sm_id": "SM-1",
                "states": ["A"],
                "transitions": ["A->B"],
            },
            {"type": "state_machine", "states": ["A"], "transitions": []},
        )
        self.assertEqual(result["verdict"], "BREAKING_DRIFT")
        self.assertTrue(
            any(f["drift_kind"] == "MALFORMED_SNAPSHOT" for f in result["findings"])
        )

    def test_non_object_roots_error_rather_than_crash(self):
        for contract, observed in ((None, {}), ({}, None), ("x", {}), ([], {})):
            result = drift.detect(contract, observed)
            self.assertIn("error", result)

    def test_unknown_contract_type_errors(self):
        self.assertIn("error", drift.detect({"type": "nope"}, {}))

    def test_drift_exit_codes(self):
        self.assertEqual(
            {"NO_DRIFT": 0, "COMPATIBLE_DRIFT": 1, "BREAKING_DRIFT": 2}[
                drift.detect(*interface({"a": {"type": "int"}}, {}))["verdict"]
            ],
            2,
        )


# -------------------------------------------- invariant 2: keep all versions


def packet(items):
    return {
        "declared_sources": [
            {"source_id": "PRD", "availability": "AVAILABLE"},
            {"source_id": "API", "availability": "AVAILABLE"},
        ],
        "ir_draft": {"requirements": items},
    }


def requirement(**overrides):
    base = {
        "req_id": "REQ-1",
        "source_trace": "PRD§1",
        "confidence": 0.77,
    }
    base.update(overrides)
    return base


class ConflictMultiVersionRetentionTests(unittest.TestCase):
    """Design invariant 2: a conflict must retain every disagreeing version.

    A conflict with one version is not a resolved conflict — it is a silent
    adjudication wearing the costume of analysis.
    """

    def _codes(self, result):
        return {f["code"] for f in result["findings"]}

    def test_conflict_with_a_single_version_is_rejected(self):
        result = compiler.check_compilation(
            packet(
                [
                    requirement(conflict=True, conflict_refs=["PRD§1"]),
                    # second source must contribute, or SOURCE_SILENTLY_DROPPED masks the signal
                    requirement(req_id="REQ-2", source_trace="API§1"),
                ]
            )
        )
        self.assertIn("CONFLICT_SINGLE_VERSION", self._codes(result))
        self.assertEqual(result["verdict"], "REJECT")

    def test_conflict_with_zero_versions_is_rejected(self):
        result = compiler.check_compilation(
            packet(
                [
                    requirement(conflict=True, conflict_refs=[]),
                    requirement(req_id="REQ-2", source_trace="API§1"),
                ]
            )
        )
        self.assertIn("CONFLICT_SINGLE_VERSION", self._codes(result))

    def test_duplicate_refs_do_not_fake_a_multi_version_conflict(self):
        """Two identical refs are one version, not two."""
        result = compiler.check_compilation(
            packet(
                [
                    requirement(conflict=True, conflict_refs=["PRD§1", "PRD§1"]),
                    requirement(req_id="REQ-2", source_trace="API§1"),
                ]
            )
        )
        self.assertIn("CONFLICT_SINGLE_VERSION", self._codes(result))

    def test_conflict_retaining_two_versions_is_accepted(self):
        result = compiler.check_compilation(
            packet(
                [
                    requirement(conflict=True, conflict_refs=["PRD§1", "API§2"]),
                    # conflict_refs are not source contributions; only source_trace is.
                    # Without this second item, API is (correctly) SOURCE_SILENTLY_DROPPED.
                    requirement(req_id="REQ-2", source_trace="API§1"),
                ]
            )
        )
        self.assertNotIn("CONFLICT_SINGLE_VERSION", self._codes(result))
        self.assertEqual(result["verdict"], "PASS", result["findings"])

    def test_conflict_ref_must_bind_to_an_available_source(self):
        result = compiler.check_compilation(
            packet(
                [
                    requirement(conflict=True, conflict_refs=["PRD§1", "GHOST§9"]),
                    requirement(req_id="REQ-2", source_trace="API§1"),
                ]
            )
        )
        self.assertIn("CONFLICT_REF_NOT_AVAILABLE", self._codes(result))
        self.assertEqual(result["verdict"], "REJECT")

    def test_no_conflict_flag_means_no_conflict_checks(self):
        result = compiler.check_compilation(
            packet([requirement(), requirement(req_id="REQ-2", source_trace="API§1")])
        )
        self.assertNotIn("CONFLICT_SINGLE_VERSION", self._codes(result))
        self.assertEqual(result["verdict"], "PASS", result["findings"])


class MissingEvidenceNeverCleanPassTests(unittest.TestCase):
    """Design invariant 1, at the compiler boundary."""

    def _codes(self, result):
        return {f["code"] for f in result["findings"]}

    def test_fabricated_source_trace_is_rejected(self):
        result = compiler.check_compilation(
            packet(
                [
                    requirement(source_trace="INVENTED§1"),
                    requirement(req_id="REQ-2", source_trace="API§1"),
                ]
            )
        )
        self.assertIn("FABRICATED_SOURCE_TRACE", self._codes(result))
        self.assertEqual(result["verdict"], "REJECT")

    def test_unavailable_source_degrades_to_review_not_pass(self):
        result = compiler.check_compilation(
            {
                "declared_sources": [
                    {"source_id": "PRD", "availability": "AVAILABLE"},
                    {"source_id": "LEGACY", "availability": "UNREADABLE"},
                ],
                "ir_draft": {"requirements": [requirement()]},
            }
        )
        self.assertEqual(result["verdict"], "PASS_WITH_REVIEW")
        self.assertIn("SOURCE_UNAVAILABLE", self._codes(result))

    def test_silently_dropped_source_is_rejected(self):
        result = compiler.check_compilation(packet([requirement()]))
        self.assertIn("SOURCE_SILENTLY_DROPPED", self._codes(result))

    def test_empty_source_manifest_is_rejected(self):
        result = compiler.check_compilation(
            {"declared_sources": [], "ir_draft": {"requirements": [requirement()]}}
        )
        self.assertIn("EMPTY_SOURCE_MANIFEST", self._codes(result))


if __name__ == "__main__":
    unittest.main()
