# P0 Gate 0 Skill Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or execute inline with an explicit RED-GREEN-REFACTOR checkpoint per task.

**Goal:** Remove false-pass paths from the Gate 0 requirement-to-coverage chain, add a requirement-quality analysis gate, and give every changed checker executable regression evidence.

**Architecture:** Keep probabilistic analysis separate from deterministic verdicts. Existing Skill documents provide generation/analysis guidance; Python standard-library checkers validate structured artifacts and fail closed on missing mandatory evidence. New requirement-quality analysis and gate prototypes remain separate capabilities and publish JSON artifacts with traceable finding codes.

**Tech Stack:** Markdown Skill contracts, Python 3.12 standard library, `unittest`, JSON fixtures, OpenAPI YAML, PostgreSQL DDL documentation.

**Execution status (2026-08-03): COMPLETE.** Tasks 1-7 were executed with
RED/GREEN regressions, three hash seeds, full CLI/artifact parsing, the existing
E2E sample, and an independent Python review. The separate quality analyzer was
intentionally omitted after two pressure baselines showed no incremental value;
the deterministic `requirement-quality-gate` was retained. Fresh machine-readable
evidence is in `prototypes/skills/tests/p0-verification-report.json`. The original
checkboxes below are preserved as the pre-execution specification.

## Global Constraints

- The workspace is non-Git; do not run Git commands. Record fresh hashes and a file inventory instead of commits.
- Use only Python standard library; the workspace has no dependency manifest or build system.
- Do not modify `docs/05-audits/historical/40-52`.
- Any formal entity or status change must remain aligned across glossary, domain model, API, and DB authority files.
- AI autonomy and review routing must reuse `docs/03-governance/21-AI介入点降级矩阵.md`; do not introduce a new confidence threshold.
- Every checker change starts with a failing `unittest` and ends with a fresh passing run.

---

### Task 1: Establish the P0 regression harness

**Files:**
- Create: `prototypes/skills/tests/test_p0_gate0.py`
- Create: `prototypes/skills/tests/README.md`

**Interfaces:**
- Consumes: checker functions loaded from each Skill's `scripts/*.py` file.
- Produces: `python3 -m unittest discover -s prototypes/skills/tests -p 'test_*.py' -v` as the single P0 regression command.

- [ ] Write failing tests proving: rejected assertions cannot yield full coverage; empty compilation rejects; PRD-only compilation degrades rather than rejects; state transitions cannot bypass an empty state set; inferred confidence `0.8` cannot pass; IR reachability is deterministic.
- [ ] Run the suite and record the expected failures against current code.
- [ ] Add fixture helpers only; do not change production checkers in this task.

### Task 2: Repair `coverage-analyzer`

**Files:**
- Modify: `prototypes/skills/coverage-analyzer/scripts/coverage.py`
- Modify: `prototypes/skills/coverage-analyzer/SKILL.md`
- Modify: `prototypes/skills/coverage-analyzer/references/coverage_calculus.md`
- Modify: `prototypes/skills/coverage-analyzer/assets/coverage_report_template.json`
- Create: `prototypes/skills/coverage-analyzer/evals/evals.json`
- Modify: `docs/01-product/03-术语表Glossary.md`
- Modify: `docs/01-product/04-核心领域模型.md`
- Modify: `docs/04-architecture/32-API规范.yaml`
- Modify: `docs/04-architecture/33-数据库Schema设计.md`

**Interfaces:**
- Consumes: `assertion_verdicts[].skill11_verdict` in `PASS|REPAIR|REJECT`.
- Produces: assertion dimension with `verified_pass`, `repair`, `reject`, `unverified`, coverage denominator including every required assertion, plus an independent rejection gate.

- [ ] Run the focused RED test showing `1 PASS + 3 REJECT` currently reports `1.0`.
- [ ] Change the minimal calculation so REJECT remains denominator responsibility and any rejection prevents `GATE_PASS`.
- [ ] Fail closed when no required assertions exist unless the strategy explicitly declares the dimension not applicable.
- [ ] Align templates, Skill rules, and four formal authority contracts with the corrected semantics.
- [ ] Run focused and full P0 tests.

### Task 3: Repair `requirement-compiler`

**Files:**
- Modify: `prototypes/skills/requirement-compiler/scripts/compile_check.py`
- Modify: `prototypes/skills/requirement-compiler/SKILL.md`
- Modify: `prototypes/skills/requirement-compiler/references/compiler_rules.md`
- Modify: `prototypes/skills/requirement-compiler/assets/compile_template.json`
- Create: `prototypes/skills/requirement-compiler/evals/evals.json`

**Interfaces:**
- Consumes: `declared_sources[]` objects with `source_id` and `availability`, plus `ir_draft`.
- Produces: `PASS`, `PASS_WITH_REVIEW`, or `REJECT`; findings distinguish empty input, unavailable expected sources, silently dropped available sources, fabricated traces, conflicts, and unreasoned confidence.

- [ ] Run RED tests proving empty packets pass and missing undeclared sources have no explicit degradation state.
- [ ] Require a non-empty source manifest and non-empty IR requirement content.
- [ ] Add source availability values `AVAILABLE`, `NOT_PROVIDED`, `NOT_APPLICABLE`, `UNREADABLE`, `EXPECTED_MISSING` while accepting legacy source strings as `AVAILABLE`.
- [ ] Reject dropped `AVAILABLE` sources; route `NOT_PROVIDED`/`UNREADABLE`/`EXPECTED_MISSING` to review; ignore `NOT_APPLICABLE` for contribution.
- [ ] Require each conflict reference to be distinct and bound to a declared source.
- [ ] Update documentation, template, evals, and run full tests.

### Task 4: Repair IR, state-machine, and business-rule gates

**Files:**
- Modify: `prototypes/skills/ir-validator/scripts/validate.py`
- Modify: `prototypes/skills/ir-validator/SKILL.md`
- Modify: `prototypes/skills/ir-validator/references/validation_rules.md`
- Modify: `prototypes/skills/state-machine-builder/scripts/sm_check.py`
- Modify: `prototypes/skills/state-machine-builder/SKILL.md`
- Modify: `prototypes/skills/state-machine-builder/references/state_machine_rules.md`
- Create: `prototypes/skills/state-machine-builder/evals/evals.json`
- Modify: `prototypes/skills/business-rule-extractor/scripts/rule_check.py`
- Modify: `prototypes/skills/business-rule-extractor/SKILL.md`
- Modify: `prototypes/skills/business-rule-extractor/references/rule_extraction_rules.md`
- Create: `prototypes/skills/business-rule-extractor/evals/evals.json`

**Interfaces:**
- Consumes: explicit `initial_state`, non-empty `states`, transitions, known entity ids, structured business rules.
- Produces: deterministic findings independent of set/hash iteration order.

- [ ] Run RED tests for empty-state bypass, hash-dependent initial-state inference, and inferred confidence `0.8` passing.
- [ ] Require explicit state-machine initial state and validate reachability, endpoints, duplicates, and binding.
- [ ] Remove `next(iter(states))` fallback from IR validation and reject missing explicit initial state.
- [ ] Align inferred-rule confidence behavior with the documented `0.7` cap without inventing a new platform autonomy threshold.
- [ ] Update rules and evals, then run the suite under multiple `PYTHONHASHSEED` values.

### Task 5: Create the requirement-quality gate prototype

**Files:**
- Create: `prototypes/skills/requirement-quality-gate/SKILL.md`
- Create: `prototypes/skills/requirement-quality-gate/assets/gate_report_template.json`
- Create: `prototypes/skills/requirement-quality-gate/references/gate_rules.md`
- Create: `prototypes/skills/requirement-quality-gate/scripts/gate_check.py`
- Create: `prototypes/skills/requirement-quality-gate/evals/evals.json`
- Modify: `prototypes/skills/tests/test_p0_gate0.py`

**Interfaces:**
- Test Design Agent produces source-indexed quality assessments; the Gate consumes that report and emits `PASS`, `PASS_WITH_REVIEW`, or `REJECT` without inventing business truth or thresholds.

- [x] Capture two baseline pressure scenarios. Both unguided runs retained the seeded conflict and identified ambiguous/NFR defects, so a separate analyzer Skill has no demonstrated incremental value and is not created.
- [ ] Write RED checker tests for missing evidence, unknown finding codes, silent conflict resolution, and unmeasurable NFR handling.
- [ ] Implement concise Gate guidance and a deterministic checker that requires explicit assessment across all mandatory quality dimensions.
- [ ] Add standard eval manifests and run the full suite.

### Task 6: Integrate P0 prototypes into current navigation and Test Design flow

**Files:**
- Modify: `docs/00-navigation/54-项目需求资料总索引.md`
- Modify: `docs/02-prd/11-PRD-TestDesign.md`
- Modify: `docs/03-governance/21-AI介入点降级矩阵.md` only if routing text needs clarification, without changing thresholds.
- Modify: `docs/04-architecture/35-变更记录CHANGELOG.md`

**Interfaces:**
- Consumes: hardened P0 Skill names and verdict contracts.
- Produces: one authoritative Gate 0 order and a traceable change record.

- [ ] Replace the current core-11 list with the validated Gate 0 chain and mark full test-data synthesis as deferred.
- [ ] Insert requirement-quality analysis before IR compilation in the Test Design flow.
- [ ] Document analyzer findings as prototype artifacts unless and until a formal persistence entity is added across all four authorities.
- [ ] Record every corrected false-pass rule and compatibility note in the current architecture changelog.

### Task 7: Review and final verification

**Files:**
- Review every file changed by Tasks 1-6.
- Create: `prototypes/skills/tests/p0-verification-report.json`

**Interfaces:**
- Produces: fresh verification evidence with command, timestamp, Python version, test counts, eval counts, and SHA-256 hashes of changed executable contracts.

- [ ] Run AST parsing for all Skill Python scripts and JSON parsing for all assets/evals.
- [ ] Run every Skill CLI with `--help`.
- [ ] Run P0 tests under at least three `PYTHONHASHSEED` values.
- [ ] Re-run the existing E2E validation chain and inspect verdict changes.
- [ ] Request an independent Python review of every changed Python file.
- [ ] Scan current docs for stale coverage formulas, old Skill counts, and broken links.
- [ ] Write the verification report from fresh command output.
