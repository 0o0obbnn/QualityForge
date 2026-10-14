# Skill Benchmark: assertion-verifier

**Date**: 2026-07-24T08:30:00Z
**Evals**: 6 (with vs without skill, paired)

## Summary

| Metric | with_skill | without_skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 100% ± 0% | 67% ± 30% | +33% |
| Time (s) | 109.2 ± 18.1 | 91.5 ± 30.2 | +17.7s |
| Tokens | 413125 ± 113286 | 174840 ± 1331 | +238285 |

## Per-eval pass rate

| Eval | with_skill | without_skill |
|------|------------|---------------|
| eval-1-static-check-rejects-hal | 4/4 (100%) | 2/4 (50%) |
| eval-2-static-check-rejects-orp | 4/4 (100%) | 3/4 (75%) |
| eval-3-mutation-score-high-risk | 4/4 (100%) | 1/4 (25%) |
| eval-4-degrade-rule-stage2-skip | 4/4 (100%) | 4/4 (100%) |
| eval-5-no-mutants-is-hard-rejec | 4/4 (100%) | 4/4 (100%) |
| eval-6-effective-coverage-not-l | 4/4 (100%) | 2/4 (50%) |