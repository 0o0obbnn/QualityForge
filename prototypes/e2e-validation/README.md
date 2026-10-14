# Gate 0 Negative E2E (intentionally incomplete)

This chain is the negative companion to `prototypes/e2e-validation-golden/`.
**Its incompleteness is deliberate.** It exists to prove the coverage gate
actually fails when coverage is genuinely missing, and it must always end in
`GATE_FAILURE`.

Do not "fix" the coverage gaps here. Raising the numbers, lowering the
thresholds in `05-coverage/strategy.json`, or deleting the REJECTed assertion
from `05-coverage/snapshot.json` would destroy the only negative baseline the
project has.

## Automated assertion

`prototypes/skills/tests/test_e2e_chains.py::NegativeChainTests` re-runs the
checkers against these inputs and asserts:

- terminal verdict stays `GATE_FAILURE`
- all four dimensions stay `FAIL`
- the missing rules/scenarios/transitions stay enumerated, not summarised
- **the REJECTed assertion stays in the denominator** — coverage is `2/3 = 0.667`,
  not `2/2 = 1.0` (design invariant 3, verified end to end)

Run with `make test-skills`.

## Why each dimension fails

| Dimension | Coverage | Threshold | Cause |
|---|---|---|---|
| rule | 0.75 (3/4) | 1.00 | `R-TD-004` has no bound case |
| scenario | 0.333 (3/9) | 0.70 | 6 scenarios have no case |
| state | 0.25 (1/4) | 0.90 | 3 `SM-DTC` transitions unexercised |
| assertion | 0.667 (2/3) | 0.85 | 1 assertion REJECTed; it stays in the denominator and forces FAIL |

## Reproducing

Same command sequence as the golden chain (see
`../e2e-validation-golden/README.md`), with `e2e-validation-golden` replaced by
`e2e-validation`. Every command exits 0 except the final coverage call, which
exits **2** — that non-zero exit is the expected result.

## Extra artifacts

`03-cases/blind_spot_report.json` and `03-cases/blind_spot_repro.json` are a
separate REJECT sample retained alongside this chain; they are not produced by
the six-command sequence above.
