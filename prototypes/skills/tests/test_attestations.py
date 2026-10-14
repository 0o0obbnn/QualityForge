"""Make the verification attestations checked rather than decorative.

`p0-verification-report.json` and `p1-verification-report.json` pin sha256
digests of the checkers they attest to. Nothing re-verified them, so drift was
undetectable — a pin nobody checks is a claim of integrity, not integrity.

This file closes that. The policy it enforces is deliberately *not* "the digests
must always match": these are dated point-in-time records, and silently
regenerating their hashes would backdate today's content into a 2026-08-02
attestation. Instead:

  * every pinned path must still resolve to a real file (a pin pointing at
    nothing is meaningless),
  * drift is allowed only where the report itself declares it in
    `_known_drift_since_attestation`,
  * undeclared drift fails, forcing a conscious choice: declare it, or restore
    the file.

That way the attestation stays honest about its own age.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_DIR = Path(__file__).resolve().parent
REPORTS = ("p0-verification-report.json", "p1-verification-report.json")


def load_report(name: str) -> dict:
    with (TESTS_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def pinned_digests(report: dict) -> dict[str, str]:
    """Pins, minus the underscore-prefixed metadata keys."""
    return {
        path: digest
        for path, digest in report.get("sha256", {}).items()
        if not path.startswith("_")
    }


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AttestationsAreHonestAboutTheirAgeTests(unittest.TestCase):
    def test_reports_declare_themselves_historical(self):
        """A dated snapshot must not read as a live gate."""
        for name in REPORTS:
            report = load_report(name)
            self.assertEqual(
                report.get("record_type"), "historical point-in-time attestation", name
            )
            self.assertIn("superseded_by", report, name)

    def test_reports_warn_their_counts_are_stale(self):
        for name in REPORTS:
            self.assertIn("NOT updated", load_report(name).get("note", ""), name)


class PinnedPathsResolveTests(unittest.TestCase):
    def test_every_pinned_path_exists(self):
        """A pin pointing at a missing file attests to nothing."""
        for name in REPORTS:
            for path in pinned_digests(load_report(name)):
                self.assertTrue((REPO_ROOT / path).is_file(), f"{name}: {path}")

    def test_pins_are_repo_relative_paths_not_bare_basenames(self):
        """p1 originally keyed by basename, which cannot be resolved unambiguously."""
        for name in REPORTS:
            for path in pinned_digests(load_report(name)):
                self.assertIn(
                    "/", path, f"{name}: {path!r} must be a repo-relative path"
                )

    def test_pins_are_well_formed_sha256(self):
        for name in REPORTS:
            for path, digest in pinned_digests(load_report(name)).items():
                self.assertEqual(len(digest), 64, f"{name}: {path}")
                self.assertTrue(
                    all(c in "0123456789abcdef" for c in digest), f"{name}: {path}"
                )


class DriftMustBeDeclaredTests(unittest.TestCase):
    """Undeclared drift fails; declared drift is documented history."""

    def _drift(self, name: str) -> tuple[set[str], set[str]]:
        report = load_report(name)
        declared = set(
            report.get("sha256", {}).get("_known_drift_since_attestation", [])
        )
        actual = {
            path
            for path, digest in pinned_digests(report).items()
            if (REPO_ROOT / path).is_file() and sha256_of(REPO_ROOT / path) != digest
        }
        return declared, actual

    def test_no_undeclared_drift(self):
        for name in REPORTS:
            declared, actual = self._drift(name)
            undeclared = actual - declared
            self.assertEqual(
                undeclared,
                set(),
                f"{name}: these files changed since the attestation but are not listed in "
                f"_known_drift_since_attestation: {sorted(undeclared)}. Either add them there "
                f"(if the change is intended) or restore the file.",
            )

    def test_declared_drift_is_real(self):
        """A stale drift declaration is its own kind of lie."""
        for name in REPORTS:
            declared, actual = self._drift(name)
            phantom = declared - actual
            self.assertEqual(
                phantom,
                set(),
                f"{name}: declared as drifted but the digest now matches: {sorted(phantom)}. "
                f"Remove the stale declaration.",
            )

    def test_p1_pins_all_still_match(self):
        """P1 originally promised zero drift for its four hardened checkers.

        That promise had no lawful exit for authorized evolution, so on
        2026-08-27 (coverage-family checks added to case_check.py and
        scenario_check.py, declared in the report's _known_drift) this test
        was aligned with the p0 policy: drift is allowed only where the
        report declares it, and every declaration must be real.
        """
        declared, actual = self._drift("p1-verification-report.json")
        self.assertEqual(
            actual - declared,
            set(),
            "p1: changed since attestation but not declared in "
            "_known_drift_since_attestation",
        )
        self.assertEqual(
            declared - actual,
            set(),
            "p1: declared as drifted but the digest now matches",
        )


if __name__ == "__main__":
    unittest.main()
