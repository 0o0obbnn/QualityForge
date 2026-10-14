# Gate 0 regression tests

Run the deterministic checker regression suite from the workspace root:

```bash
make test-skills
```

or directly:

```bash
python3 -m unittest discover -s prototypes/skills/tests -p 'test_*.py' -v
```

The suite imports the real checker scripts directly. It does not mock validation
behavior and requires only the Python standard library.

- `test_p0_gate0.py` covers the P0 requirement/IR/assertion/coverage hardening.
- `test_p1_gate0.py` covers P1 entity, strategy, scenario, and case contracts.
- `test_p2_gate0.py` covers the HITL gate, contract-drift classification, and the
  conflict-retention invariant.
- `test_e2e_chains.py` asserts both end-to-end chains hold their terminal verdict.
- `test_attestations.py` re-verifies the sha256 pins in the two verification
  reports, so those pins are checked rather than decorative.

## What each layer actually asserts

Four separate mechanisms exist; they are not interchangeable, and the strong
claim belongs only to the first.

| Layer | Command | What it asserts |
|---|---|---|
| Contract tests (this dir) | `make test-skills` | Real behavioural assertions on verdicts *and* finding codes, via `importlib` against the production checkers. 127 tests across 13 of 30 skills, plus both E2E chains and the attestation pins. |
| Deterministic runners | `run_all_evals.py` | Per-skill runners compare expected vs actual verdict/findings against `assets/evals/evals.json`, for the 14 skills that have one. |
| Eval manifests | `run_all_evals.py` | **Schema lint only.** `evals/evals.json` `expected_output` is prose and is never compared to any output. The "103 eval cases" figure measures manifest well-formedness, not behaviour. |
| LLM evals | `promptfooconfig.yaml` | 32 model-facing cases over the SKILL.md files. Needs API keys; run in CI only. |

Do not cite the manifest count as evidence of behavioural coverage.

## The two eval files are not duplicates

Each skill may carry two files with confusingly similar paths. They serve
different consumers and are both correct to exist:

| Path | Consumer | Shape |
|---|---|---|
| `evals/evals.json` | `run_all_evals.py` schema lint, and `promptfooconfig.yaml` | prose manifest: `id`, `name`, `prompt`, `expected_output`, `files` |
| `assets/evals/evals.json` | the skill's own `scripts/test_evals.py` / `run_evals.py` | machine-readable fixtures: `input` packet + `expected_verdict` / `expected_findings` |

Nothing cross-checks that the two cover the same scenarios, so they can and do
diverge in case count. Treat `assets/evals/evals.json` as authoritative for
behaviour and `evals/evals.json` as the documented intent.

## Design invariants — all three now asserted

| Invariant | Where asserted |
|---|---|
| Missing evidence never becomes a clean PASS | `test_p0_gate0.py` (coverage/IR), `test_p2_gate0.MissingEvidenceNeverCleanPassTests` (compiler boundary) |
| Conflicts retain all disagreeing versions | `test_p2_gate0.ConflictMultiVersionRetentionTests` (`CONFLICT_SINGLE_VERSION`, incl. duplicate refs not faking two versions) |
| Rejected assertions stay in the coverage denominator | `test_p0_gate0.py` (unit), `test_e2e_chains.py` (end to end) |

## End-to-end chains

`test_e2e_chains.py` re-runs every checker against the committed inputs and
asserts the verdicts live:

- `prototypes/e2e-validation-golden/` must end in `GATE_PASS`, with every
  dimension passing on a non-empty denominator.
- `prototypes/e2e-validation/` must stay `GATE_FAILURE`, with all four
  dimensions failing.

The tests read the chain directories but never write to them, so a failure means
checker behaviour changed — not that a fixture drifted. `test_committed_reports_match_live_run`
additionally proves the committed JSON reports are regenerated evidence rather
than hand-authored verdicts.

`NegativeChainTests.test_rejected_assertion_stays_in_denominator` pins design
invariant 3 end to end: the negative chain has 1 REJECT among 3 assertions, so
coverage must be `2/3 = 0.667`. Deleting the rejected assertion would report
`2/2 = 1.0` and flip the chain to `GATE_PASS` — verified to be caught by 5 of
these tests.

## Coverage gaps

17 of 30 skills have no test in this directory. 24 of 30 are outside the e2e
chain. The remaining untested set is the peripheral generator/planner layer
(`api-test-generator`, `ui-automation-generator`, `fixture-dag-planner`,
`data-cleanup-manager`, `failure-analyzer`, `test-data-generator`, and the four
newly-implemented validators), all of which do have a deterministic runner over
`assets/evals/evals.json`.
