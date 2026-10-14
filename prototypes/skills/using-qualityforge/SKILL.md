---
name: using-qualityforge
description: 启动任何 QualityForge 测试任务时使用，或当请求涉及从需求分析、测试设计、自动化、执行、缺陷到报告闭环的工作时使用。把意图路由到正确的产出 Skill 和内置验收门禁，保留跨阶段追踪与下游准入状态。
---

# Using QualityForge

QualityForge 是一条**产出与验收一体化的测试生命周期流水线**，不是互不相干的工具箱。本页告诉你当前处于哪个阶段、应生成什么产物，以及用什么证据验收后才能进入下游。

<EXTREMELY-IMPORTANT>
阶段 Skill 默认同时承担两项职责：按明确契约生成可直接使用的产物，并运行自身的确定性验收。只具备 checker 的历史 Skill 在完成迁移前视为“仅验收能力”，不得把校验器存在误报为该阶段已经具备生产能力。
</EXTREMELY-IMPORTANT>

## 三条不变量

这些不是风格偏好。每一条都由 checker 的 exit code 强制执行，每一条的存在都是因为它是最短的假通过路径。

1. **缺失的证据绝不会变成干净的 PASS。** 来源不可用时，verdict 降级为 `PASS_WITH_REVIEW`。绝不为填坑而捏造需求或 `source_trace`。
2. **冲突保留每一个版本。** 把冲突坍缩成一个版本，是一次披着分析外衣的静默裁决。按 `CONFLICT_SINGLE_VERSION` REJECT。
3. **被 REJECT 的断言留在覆盖分母中。** 一次 `REJECT` 是*已确认*的验证失败。它对分子贡献为零，并迫使所在维度 FAIL。删掉它来抬分，是伪造门禁通过的最省事手段。

分母为零的维度是一次物化失败，**不是** 100% 覆盖。

## verdict 一览

| Verdict | Exit | 含义 |
|---|---|---|
| `PASS` | 0 | 产物可以继续。 |
| `PASS_WITH_REVIEW` | 0 | 可以继续，但必须有人 review。不得静默当作 PASS。 |
| `REJECT` / `GATE_FAILURE` | 2 | 阻断。在上游修正产物；绝不靠改门禁或改数据来通过。 |
| invalid input | 3 | 数据包畸形。修正输入的形状。 |

`REPAIR`（仅 assertion-verifier）**不是** PASS。

## 按意图路由

找到与用户诉求匹配的那一行，运行该阶段的门禁。

### 需求 → IR

| 用户想要 | 阶段 skill | 审判对象 |
|---|---|---|
| 对需求做全量质量/可测试性评审 | `qa-requirement-review` | 生成结构化评审 JSON、逐需求工作队列、测试点和 Markdown 报告 |
| 提取功能点、最小功能与业务字段 | `requirement-function-mapping` | 生成图谱 JSON/HTML 和测试设计输入适配包 |
| 对评审报告执行发布门禁 | `requirement-quality-gate` | **评审报告**，而不是需求本身 |
| 把需求融合成 IR 草稿 | `requirement-compiler` | 已经跑过的那次**融合** |
| 从 PRD 中抽取实体 | `domain-model-extractor` | 实体**草稿包** |
| 实体生命周期 / 状态机 | `state-machine-builder` | 抽取出的**状态机** |
| 从来源提取业务规则 | `business-rule-extractor` | **候选规则** |
| 为下游发布 IR | `ir-validator` | 发布前的 IR **草稿** |

### IR → 测试

| 用户想要 | 阶段 skill | 审判对象 |
|---|---|---|
| 测试策略 | `strategy-planner` | 起草的 **Strategy Contract** |
| 测试场景 / 用户旅程 | `scenario-generator` | 起草的 **Scenario Graph** |
| 具体测试用例 | `test-case-generator` | 从已放行的 `test_design_input 2.0` 生成 Test Case IR JSON 与 CSV 视图 |
| 断言批量检查 | `assertion-generator` | 该批次的弱点**分布** |
| 每条断言的正确性检查 | `assertion-verifier` | 逐断言，经变异门禁 |

### 测试 → 可执行

| 用户想要 | 阶段 skill | 前置条件 |
|---|---|---|
| API 自动化脚本 | `api-test-generator` | 断言已通过 `assertion-verifier` |
| UI 自动化脚本 | `ui-automation-generator` | locator 库已存在 |
| UI locator | `locator-discovery` | locator 已被提出 |
| 负载/性能脚本 | `performance-test-generator` | 阈值可追溯到 Strategy |
| 安全测试 | `security-test-generator` | Strategy 含显式 `In_Scope` |

### 测试数据（三个有序阶段）

`data-requirement-analyzer` → `fixture-dag-planner` → `data-cleanup-manager`

另有 `test-data-generator` 作为针对字段值本身的合规门禁。

### 运行时与治理

| 用户想要 | 阶段 skill |
|---|---|
| 覆盖数字 / 阶段出口决策 | `coverage-analyzer` |
| 干系人仪表盘的诚实性检查 | `quality-governance` |
| 失败测试分诊 | `failure-analyzer`（先**归类**） |
| 自动修复一个不稳定的测试 | `self-healing-orchestrator`（归类之后） |
| 变更的波及面 | `change-impact-analyzer` |
| 重跑哪些测试 | `regression-planner`（消费影响清单） |
| 线上系统 vs IR 契约 | `contract-drift-detector` |
| 计划阶段顺序校验 | `plan-orchestrator` |
| 是否需要人工签核 | `hitl-gatekeeper` |
| 记忆条目入库前审核 | `knowledge-memory` |

## 易混淆的配对

把这两者搞反，是最常见的路由错误。

| 不是这个 | 而是这个 | 区别 |
|---|---|---|
| `requirement-quality-gate` | `requirement-compiler` | 前者审判*评审报告*；后者审判*融合*。 |
| `coverage-analyzer` | `quality-governance` | 前者**计算**数字；后者检查汇报该数字的**仪表盘**。 |
| `change-impact-analyzer` | `regression-planner` | 前者**产出**受影响清单；后者**审计**从清单做出的选择。 |
| `failure-analyzer` | `self-healing-orchestrator` | 先归类，再决定是否允许修复。绝不反过来。 |
| `assertion-generator` | `assertion-verifier` | 批次分布 vs 逐断言正确性。两者都要跑，按此顺序。 |
| `domain-model-extractor` | `state-machine-builder` | 实体 vs 实体的生命周期。 |

## 运行门禁

每个 checker 都是 `<skill>/scripts/` 下的独立 CLI，仅用标准库。**flag 名称并不统一**——本表是权威版本；不要靠猜。

```
requirement-quality-gate    gate_check.py        --review
requirement-compiler        compile_check.py     --packet
domain-model-extractor      entity_check.py      --packet
state-machine-builder       sm_check.py          --packet
business-rule-extractor     rule_check.py        --packet
ir-validator                validate.py          --ir
strategy-planner            strategy_check.py    --strategy
scenario-generator          scenario_check.py    --scenarios --ir
test-case-generator         validate_case_ir.py  --cases --input
assertion-generator         batch_check.py       --batch
assertion-verifier          verify.py static-check  --assertions --ir
api-test-generator          api_check.py         --script
ui-automation-generator     ui_check.py          --script
performance-test-generator  perf_check.py        --script --strategy
security-test-generator     security_check.py    --packet
locator-discovery           locator_check.py     --locator
data-requirement-analyzer   requirement_check.py --requirements --ir --cases --baselines
fixture-dag-planner         dag_check.py         --dag
data-cleanup-manager        cleanup_check.py     --cleanup
test-data-generator         compliance_check.py  --packet --ir
coverage-analyzer           coverage.py          --snapshot --strategy
quality-governance          governance_check.py  --report
change-impact-analyzer      impact_check.py      --report
regression-planner          regression_check.py  --selection
failure-analyzer            classify.py          --signal
contract-drift-detector     drift_detect.py      --contract --observed
plan-orchestrator           plan_check.py        --plan
knowledge-memory            memory_check.py      --entry --known-hashes
```

以上全部支持 `--out <report.json>`。有两个不遵循该模式——它们接收标量 flag、没有 `--out`：

```
hitl-gatekeeper           gate.py           --confidence --event-type --asset-type --source-trace
                                            --proposed-action --ir-element-id --artifact-id
                                            --artifact-version-id --content-digest --policy-type
self-healing-orchestrator  healing_gate.py  --asset-id --path-category --heal-type
                                            --touches-expected --confidence
```

在仓库根目录运行：

```bash
python3 prototypes/skills/<skill>/scripts/<checker>.py --<flag> <input.json> --out <report.json>
```

## 参考链

`prototypes/e2e-validation-golden/` 是一条最小而完整的 IR → 场景 → 用例 → 断言 → 覆盖链，必须以 `GATE_PASS` 结尾。它的孪生负例 `prototypes/e2e-validation/` 必须保持 `GATE_FAILURE`——它证明门禁在该失败的时候仍会*失败*，而这一点仅靠一条通过的链是显示不出来的。

两者都由 `prototypes/skills/tests/test_e2e_chains.py` 断言。回归：

```bash
python3 -m unittest discover -s prototypes/skills/tests -p 'test_*.py'
```

`e2e-validation-golden/README.md` 带有精确的命令序列——照抄它，不要重新推导路径。

## 红旗

冒出以下任何一个念头，都意味着立刻停下。

| 念头 | 现实 |
|---|---|
| 「门禁把它拒了，我来调低阈值」 | 阈值住在 Strategy Contract 里。降范围是经 review 的人类决策。 |
| 「我把被 REJECT 的断言删掉，覆盖就能过了」 | 这就是不变量 3 的原文。它留在分母里。 |
| 「这条规则没有来源，我来推断一条」 | 推断出的规则路由到 `NEED_HUMAN_REVIEW`。置信度永远不能授权推断。 |
| 「两个来源冲突，我选较新的那个」 | 两个都保留。单版本冲突会被 REJECT。 |
| 「这个维度是空的，所以是 100%」 | 空分母是一次物化失败。 |
| 「行覆盖 95%，门禁通过」 | 行覆盖绝不是门禁信号。四个可追溯维度才是。 |
| 「REPAIR 基本上就是 PASS」 | 不是。 |
| 「这个 skill 叫 X-generator，所以它生成 X」 | 大多数是门禁。读它的 description。 |
