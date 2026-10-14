# P1 Gate 0 Golden Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or execute inline with an explicit RED-GREEN-REFACTOR checkpoint per task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the four remaining unevaluated Gate 0 validators and add a complete positive Golden E2E sample without weakening the existing negative coverage sample.

**Architecture:** Keep generation guidance separate from deterministic judgement. Each checker fails closed on malformed JSON and validates only evidence that belongs to its layer. The existing E2E sample remains a negative gate fixture; a new Golden sample proves that the complete IR→Scenario→Case→Assertion→Coverage chain can reach `GATE_PASS` honestly.

**Tech Stack:** Markdown Skill contracts, Python standard library, `unittest`, JSON fixtures, OpenAPI YAML documentation.

## Global Constraints

- The workspace is non-Git; do not run Git commands or write commit steps.
- Preserve `prototypes/e2e-validation/` as the negative/incomplete sample; add a separate positive sample.
- Do not add `nfr-extractor` or `business-scenario-modeler` during P1. First close the current Gate 0 chain and measure remaining semantic defects on the Golden Set.
- Do not hard-code payment/auth/permission as universal business critical paths. Strategy input must declare project-specific critical paths explicitly.
- All public checker functions must return a deterministic verdict for malformed but parseable JSON; CLIs use exit 3 only for unreadable/invalid JSON or output I/O failure.
- Every behavior change starts with a failing test and ends with fresh full-suite verification.

---

### Task 1: Establish the P1 RED regression baseline

**Files:**
- Create: `prototypes/skills/tests/test_p1_gate0.py`
- Modify: `prototypes/skills/tests/README.md`

**Interfaces:**
- Consumes: `check_entities`, `check_strategy`, `check_graph`, and `check_cases`.
- Produces: adversarial regression evidence executed by the existing unittest discovery command.

- [ ] Add failing tests for malformed roots/collections/items in all four checkers.
- [ ] Add failing tests for empty entity fields, duplicate field names, and non-string references.
- [ ] Add failing tests proving a non-payment project is rejected by the hard-coded strategy vocabulary and that declared critical paths need explicit disposition/binding.
- [ ] Add failing tests for boolean/NaN thresholds, malformed pyramid values, missing gates, and duplicate gate names.
- [ ] Add failing tests for scenario `req_id` absent from IR, duplicate IDs, malformed transition endpoints, and non-object IR records.
- [ ] Add failing tests for cases whose `req_id` disagrees with the bound scenario, missing executable steps/expected results, unknown step endpoints, and malformed nested values.
- [ ] Run the P1 suite and record the expected RED failures before editing production checkers.

### Task 2: Harden `domain-model-extractor`

**Files:**
- Modify: `prototypes/skills/domain-model-extractor/scripts/entity_check.py`
- Modify: `prototypes/skills/domain-model-extractor/SKILL.md`
- Modify: `prototypes/skills/domain-model-extractor/references/entity_extraction_rules.md`
- Modify: `prototypes/skills/domain-model-extractor/assets/entity_template.json`
- Create: `prototypes/skills/domain-model-extractor/evals/evals.json`

**Interfaces:**
- Consumes: `{entities: [{entity_id, name, fields[]}]}`.
- Produces: `PASS|REJECT` with stable finding order and no exception for parseable JSON.

- [ ] Reject invalid packet/collection/item shapes.
- [ ] Require non-empty entity name and fields.
- [ ] Require every field to be an object with a unique non-empty name and non-empty non-`unknown` string type.
- [ ] Require references to be string entity IDs present in the same packet.
- [ ] Add normal, duplicate-field, dangling-reference, and malformed-shape evals.

### Task 3: Harden `strategy-planner`

**Files:**
- Modify: `prototypes/skills/strategy-planner/scripts/strategy_check.py`
- Modify: `prototypes/skills/strategy-planner/SKILL.md`
- Modify: `prototypes/skills/strategy-planner/references/strategy_rules.md`
- Modify: `prototypes/skills/strategy-planner/assets/strategy_template.json`
- Create: `prototypes/skills/strategy-planner/evals/evals.json`

**Interfaces:**
- Consumes: a Strategy Contract with `Critical_Paths[]`, `In_Scope[]`, `Out_Of_Scope[]`, `Quality_Gates[]`, `Pyramid_Distribution`, and `Mock_Policy`.
- Produces: `PASS|PASS_WITH_REVIEW|REJECT`; no project-specific critical path is invented by the checker.

- [ ] Replace universal keyword enumeration with explicit `Critical_Paths[]` entries containing `path_id`, `disposition`, and either bound `feature_ids` or an `exclusion_reason`.
- [ ] Validate non-empty scope and gate collections, unique IDs/names, finite non-boolean thresholds in `[0,1]`, valid risk levels, and referenced feature IDs.
- [ ] Validate pyramid numeric types/ranges and a sum of `1.0 ± 0.001` before shape judgement.
- [ ] Validate mock-policy collection shapes while preserving the existing advisory/reject semantics.
- [ ] Add evals for a QualityForge-specific critical path, unbound critical path, malformed threshold, inverted pyramid, and review-tier trophy.

### Task 4: Harden `scenario-generator`

**Files:**
- Modify: `prototypes/skills/scenario-generator/scripts/scenario_check.py`
- Modify: `prototypes/skills/scenario-generator/SKILL.md`
- Modify: `prototypes/skills/scenario-generator/references/scenario_contract.md`
- Modify: `prototypes/skills/scenario-generator/assets/scenario_template.json`
- Create: `prototypes/skills/scenario-generator/evals/evals.json`

**Interfaces:**
- Consumes: scenario array and validated Testing IR.
- Produces: deterministic graph verdict with requirement, rule, facet, and transition coverage findings.

- [ ] Fail closed on malformed scenario/IR shapes.
- [ ] Bind both `req_id` and `rule_id` to existing IR IDs.
- [ ] Validate unique scenario IDs and scalar facet/transition fields without exceptions.
- [ ] Preserve `TRANSITION_UNCOVERED` as hard REJECT and deterministic facet reporting.
- [ ] Add evals for complete graph, unknown requirement, uncovered transition, missing facet, and malformed nested values.

### Task 5: Harden `test-case-generator`

**Files:**
- Modify: `prototypes/skills/test-case-generator/scripts/case_check.py`
- Modify: `prototypes/skills/test-case-generator/SKILL.md`
- Modify: `prototypes/skills/test-case-generator/references/case_contract.md`
- Modify: `prototypes/skills/test-case-generator/assets/test_case_template.json`
- Create: `prototypes/skills/test-case-generator/evals/evals.json`

**Interfaces:**
- Consumes: case array, validated IR, and validated Scenario Graph.
- Produces: `PASS|PASS_WITH_REVIEW|REJECT` with one-to-one trace bindings and executable-structure findings.

- [ ] Fail closed on malformed roots, collections, cases, steps, and expected results.
- [ ] Require case `req_id`/`rule_id` to exist in IR and equal the bound scenario's IDs.
- [ ] Require non-empty steps and expected results; validate every step endpoint and expected endpoint against IR contracts.
- [ ] Preserve state-machine validation and reject unresolved explicit `state_machine_id` instead of silently falling back.
- [ ] Add evals for clean cases, cross-bound scenario IDs, missing executable structure, invalid state/endpoint, and malformed JSON shapes.

### Task 6: Add a positive Golden E2E chain

**Files:**
- Create: `prototypes/e2e-validation-golden/01-ir/testing_ir.json`
- Create: `prototypes/e2e-validation-golden/02-scenarios/scenarios.json`
- Create: `prototypes/e2e-validation-golden/03-cases/cases.json`
- Create: `prototypes/e2e-validation-golden/04-assertions/assertions.json`
- Create: `prototypes/e2e-validation-golden/05-coverage/snapshot.json`
- Create: `prototypes/e2e-validation-golden/05-coverage/strategy.json`
- Create generated reports under each matching stage.
- Create: `prototypes/e2e-validation-golden/README.md`

**Interfaces:**
- Produces a minimal but complete Golden chain whose four coverage dimensions meet thresholds using real bindings, not reduced denominators or hidden rejects.

- [ ] Build a corrected minimal TestDesign IR with explicit requirements, rules, entities, transitions, and contracts.
- [ ] Cover every rule, required facet, and state transition with scenarios and cases.
- [ ] Bind one verifier-PASS assertion to each required case responsibility.
- [ ] Run every checker; require all stages and final Coverage to return PASS/GATE_PASS.
- [ ] Re-run the original negative E2E and require it to remain `GATE_FAILURE`.

### Task 7: Integrate P1 documentation

**Files:**
- Modify: `docs/00-navigation/54-项目需求资料总索引.md`
- Modify: `docs/04-architecture/35-变更记录CHANGELOG.md`
- Modify formal authority files only if a persisted field or domain concept changes.

- [ ] Distinguish negative E2E evidence from the new positive Golden chain.
- [ ] Update standard eval coverage from 9 to 13 core Gate 0 Skills.
- [ ] Record CH-31 with each corrected false-pass/false-reject rule.
- [ ] State that NFR/business-scenario Skill creation remains evidence-gated after the Golden pilot.

### Task 8: Final verification and review

**Files:**
- Create: `prototypes/skills/tests/p1-verification-report.json`

- [ ] Parse every Skill Python file, JSON asset/eval, and OpenAPI YAML.
- [ ] Run every Skill CLI `--help`.
- [ ] Run P0+P1 tests with `PYTHONHASHSEED=0,1,42`.
- [ ] Run Ruff check/format on changed Python.
- [ ] Request independent Python review of changed checker code.
- [ ] Scan current documentation for stale eval counts, old strategy assumptions, and broken local links.
- [ ] Record hashes, runtime version, test/eval counts, both E2E verdicts, and reviewer outcome.
