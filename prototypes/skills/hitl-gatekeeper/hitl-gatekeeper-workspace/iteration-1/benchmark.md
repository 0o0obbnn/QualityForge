# Skill Benchmark: hitl-gatekeeper

**Date**: 2026-07-24T08:00:00Z
**Evals**: 6 (with_skill vs without_skill, paired)

## Summary

| Metric | with_skill | without_skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 1.0 ± 0.0% | 0.75 ± 0.294% | +25.0% |
| Time (s) | 124.9 ± 32.118 | 93.5 ± 36.31 | +31.4s |
| Tokens | 465133.667 ± 121660.207 | 175267.167 ± 36154.804 | +289866 |

## Per-eval pass rate

| Eval | with_skill | without_skill |
|------|------------|---------------|
| eval-1-critical-path-high-confidence-still-blocks | 4/4 (100%) | 2/4 (50%) |
| eval-2-mid-confidence-sampling-deterministic | 3/3 (100%) | 3/3 (100%) |
| eval-3-ambiguity-flag-overrides-confidence | 3/3 (100%) | 2/3 (67%) |
| eval-4-contract-mutation-requires-ir-target | 4/4 (100%) | 4/4 (100%) |
| eval-5-low-confidence-block-and-sla | 3/3 (100%) | 1/3 (33%) |
| eval-6-missing-confidence-is-not-high-confidence | 3/3 (100%) | 3/3 (100%) |