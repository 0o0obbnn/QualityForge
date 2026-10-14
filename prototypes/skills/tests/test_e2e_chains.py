"""End-to-end chain regression: both Gate 0 sample chains must hold their verdict.

The two chains under prototypes/ are the project's regression baselines:

  * e2e-validation-golden/ — a minimal COMPLETE chain that must end in GATE_PASS.
  * e2e-validation/        — an intentionally INCOMPLETE chain that must stay
                             GATE_FAILURE.

Until now both were hand-run command sequences whose committed JSON reports were
the only evidence, and nothing referenced the negative chain at all. A regression
that flipped it to GATE_PASS would have been caught by nothing.

These tests re-run every checker against the committed inputs and assert the
verdicts live. They never write into the chain directories, so a failure here
means the checkers changed behaviour, not that a fixture drifted.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[1]
PROTOTYPES_ROOT = SKILLS_ROOT.parent
GOLDEN = PROTOTYPES_ROOT / "e2e-validation-golden"
NEGATIVE = PROTOTYPES_ROOT / "e2e-validation"


def load_script(skill: str, script: str):
    path = SKILLS_ROOT / skill / "scripts" / script
    spec = importlib.util.spec_from_file_location(f"e2e_{skill.replace('-', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ir_validator = load_script("ir-validator", "validate.py")
scenario_generator = load_script("scenario-generator", "scenario_check.py")
case_generator = load_script("test-case-generator", "case_check.py")
assertion_generator = load_script("assertion-generator", "batch_check.py")
coverage = load_script("coverage-analyzer", "coverage.py")


def read(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def run_coverage(chain: Path):
    """Re-run the terminal gate of a chain from its committed inputs."""
    return coverage.analyze(
        read(chain / "05-coverage" / "snapshot.json"),
        read(chain / "05-coverage" / "strategy.json"),
    )


class ChainFixturesPresentTests(unittest.TestCase):
    """Guard against the chains being deleted or renamed out from under the suite."""

    REQUIRED = (
        "01-ir/testing_ir.json",
        "02-scenarios/scenarios.json",
        "03-cases/cases.json",
        "04-assertions/assertions.json",
        "05-coverage/snapshot.json",
        "05-coverage/strategy.json",
    )

    def test_golden_chain_inputs_exist(self):
        for relative in self.REQUIRED:
            self.assertTrue((GOLDEN / relative).is_file(), f"missing {relative}")

    def test_negative_chain_inputs_exist(self):
        for relative in self.REQUIRED:
            self.assertTrue((NEGATIVE / relative).is_file(), f"missing {relative}")


class GoldenChainTests(unittest.TestCase):
    """The positive chain must clear every stage and end in GATE_PASS."""

    def test_ir_validates(self):
        result = ir_validator.validate(read(GOLDEN / "01-ir" / "testing_ir.json"))
        self.assertEqual(result["verdict"], "PASS", result.get("findings"))

    def test_scenarios_validate(self):
        result = scenario_generator.check_graph(
            read(GOLDEN / "02-scenarios" / "scenarios.json"),
            read(GOLDEN / "01-ir" / "testing_ir.json"),
        )
        self.assertEqual(result["verdict"], "PASS", result.get("findings"))

    def test_cases_validate(self):
        result = case_generator.check_cases(
            read(GOLDEN / "03-cases" / "cases.json"),
            read(GOLDEN / "01-ir" / "testing_ir.json"),
            read(GOLDEN / "02-scenarios" / "scenarios.json"),
        )
        self.assertEqual(result["verdict"], "PASS", result.get("findings"))

    def test_assertion_batch_validates(self):
        result = assertion_generator.check_batch(
            read(GOLDEN / "04-assertions" / "assertions.json")
        )
        self.assertEqual(result["verdict"], "PASS", result.get("findings"))

    def test_terminal_gate_passes(self):
        result = run_coverage(GOLDEN)
        self.assertEqual(result["overall_verdict"], "GATE_PASS", result["gate_failures"])
        self.assertEqual(result["gate_failures"], [])

    def test_every_dimension_passes(self):
        dims = run_coverage(GOLDEN)["dimensions"]
        for name, dim in dims.items():
            self.assertEqual(dim["verdict"], "PASS", f"{name}: {dim}")
            # A GATE_PASS earned on an empty denominator would be a fake pass.
            self.assertGreater(dim["denominator"], 0, f"{name} has an empty denominator")

    def test_committed_reports_match_live_run(self):
        """The committed reports are evidence, not hand-authored verdicts."""
        live = run_coverage(GOLDEN)
        committed = read(GOLDEN / "05-coverage" / "coverage_report.json")
        self.assertEqual(live["overall_verdict"], committed["overall_verdict"])
        self.assertEqual(live["dimensions"], committed["dimensions"])
        self.assertEqual(live["gate_failures"], committed["gate_failures"])


class NegativeChainTests(unittest.TestCase):
    """The incomplete chain must STAY failing. This is the regression that had no guard."""

    def test_terminal_gate_still_fails(self):
        result = run_coverage(NEGATIVE)
        self.assertEqual(
            result["overall_verdict"],
            "GATE_FAILURE",
            "the negative chain must never reach GATE_PASS; "
            "if coverage improved, the fixture was changed, not the bug fixed",
        )

    def test_all_four_dimensions_fail(self):
        dims = run_coverage(NEGATIVE)["dimensions"]
        for name in ("rule", "scenario", "state", "assertion"):
            self.assertEqual(dims[name]["verdict"], "FAIL", f"{name}: {dims[name]}")

    def test_rejected_assertion_stays_in_denominator(self):
        """Design invariant 3, demonstrated end to end rather than only in a unit test.

        One of three assertions is REJECTed. Coverage must be 2/3, not 2/2 —
        dropping the rejected one from the denominator would report 1.0 and hide
        a confirmed verification failure.
        """
        assertion = run_coverage(NEGATIVE)["dimensions"]["assertion"]
        self.assertEqual(assertion["denominator"], 3)
        self.assertEqual(assertion["numerator"], 2)
        self.assertEqual(assertion["reject"], 1)
        self.assertEqual(assertion["coverage"], 0.667)
        self.assertEqual(assertion["verdict"], "FAIL")

    def test_missing_coverage_is_enumerated_not_summarised(self):
        """A failing gate must name what is missing so it can be acted on."""
        dims = run_coverage(NEGATIVE)["dimensions"]
        self.assertIn("R-TD-004", dims["rule"]["missing"])
        self.assertGreater(len(dims["scenario"]["missing"]), 0)
        self.assertGreater(len(dims["state"]["missing"]), 0)

    def test_gate_failures_cover_every_failing_dimension(self):
        result = run_coverage(NEGATIVE)
        failed = {d["dimension"] for d in result["dimensions"].values() if d["verdict"] == "FAIL"}
        reported = {f["dimension"] for f in result["gate_failures"]}
        self.assertEqual(failed, reported & failed)

    def test_committed_reports_match_live_run(self):
        live = run_coverage(NEGATIVE)
        committed = read(NEGATIVE / "05-coverage" / "coverage_report.json")
        self.assertEqual(live["overall_verdict"], committed["overall_verdict"])
        self.assertEqual(live["dimensions"], committed["dimensions"])
        self.assertEqual(live["gate_failures"], committed["gate_failures"])


class ChainContrastTests(unittest.TestCase):
    """The two chains must stay genuinely different, or the pair proves nothing."""

    def test_chains_reach_opposite_verdicts(self):
        self.assertEqual(run_coverage(GOLDEN)["overall_verdict"], "GATE_PASS")
        self.assertEqual(run_coverage(NEGATIVE)["overall_verdict"], "GATE_FAILURE")

    def test_chains_use_distinct_inputs(self):
        self.assertNotEqual(
            read(GOLDEN / "05-coverage" / "snapshot.json"),
            read(NEGATIVE / "05-coverage" / "snapshot.json"),
            "the two chains share a snapshot; the contrast is not real",
        )


if __name__ == "__main__":
    unittest.main()
