# 覆盖率规则与机制

## 四个覆盖维度

覆盖率不是一个数字——是四个，各自度量不同的失败面。一个套件
可能在一个维度上很强、在另一个维度上是空壳。

```
Requirement ─REALIZED_BY─▶ Rule ─DERIVES─▶ Scenario ─COVERED_BY─▶ Case ─VERIFIED_BY─▶ Assertion
 │                                                                          │
 └────────────────────〈 Traceability Graph edges 〉──────────────────────────┘

Dimension 1: RULE coverage — of all IR rules, how many have ≥1 bound case?
Dimension 2: SCENARIO coverage — of all generated scenarios, how many have ≥1 case?
Dimension 3: STATE coverage — of all state-machine transitions, how many are exercised?
Dimension 4: ASSERTION coverage — of all assertions, what fraction PASSED the assertion-verification step?
```

### 维度 1 — 规则覆盖（需求 traceability 维度）
Testing IR 里的每条 `business_rule`，是否至少有一个 Test Case 的
`rule_id` 绑定指向它？这是与「我们是否测了 PRD 要求的东西」最
直接相关的维度。一条未覆盖的规则等于一条被静默丢弃的需求。该
维度抓的是「200 个用例、40 条规则没测」的失败：规则覆盖会报
60%，40 条未覆盖规则会按 ID 列进漏测清单（missing-coverage
list）。

### 维度 2 — 场景覆盖
Scenario Graph（上游场景生成步骤的产出）里的每个 Scenario，
是否至少有一个 Test Case 落地？场景编码五个覆盖面
（正常 / 异常 / 边界 / 状态迁移 / 权限）。生成了场景却没有用例，
意味着面分析产出了测试意图，却从未转成可执行测试。

### 维度 3 — 状态覆盖
每个 IR `state_machine` 里的每条 `transition`，是否至少有一个
用例执行过它？它与规则覆盖不同：一个状态机可以规则全部绑定，
却从未执行 PENDING→PAID 迁移，支付状态变化因此未测。状态覆盖
按迁移计，不按状态计（经两条路径可达的状态，若一条路径未测，
只算覆盖了一半）。

### 维度 4 — 断言覆盖（有效覆盖口径）
所有必需断言中，有多大比例 PASSED 断言验证
（Assertion Verifier）的验证？PASS 计入分子和分母。REPAIR、
REJECT、缺失 verdict、无法识别的 verdict 只计入分母。即使数值
阈值本来能过，一条 REJECT 也会独立强制断言维度 FAIL。存在显式
断言清单时，verdict 按 `assertion_id` 一对一绑定；重复、多余或
畸形的证据强制 FAIL，绝不能虚增覆盖。阈值比较使用未舍入的分数。

## 有效覆盖规则（承重墙）

**原始行覆盖率不可接受。** 断言验证步骤之所以存在，正是因为
AI 生成测试的行覆盖率被假覆盖问题主导（Meta ACH，arXiv 2025）。
本 skill 报告的有效覆盖是唯一反映真实 bug 检出能力的数字。

| 来自断言验证步骤的输入 | 在下游覆盖统计中的处理 |
|---|---|
| 断言 `verdict=PASS` | 计入维度 4 的分子 + 分母。 |
| 断言 `verdict=REPAIR` | 只计入分母（存在但尚未验证）。拉低分数。 |
| 断言 `verdict=REJECT` | 只计入分母，并强制断言维度 FAIL。 |
| missing/unknown verdict | 按未验证只计入分母。 |

REPAIR 只计分母是其中最微妙的一条：REPAIR 表示断言可挽救但当前
未验证。只计入分母，既如实反映「我们知道这还要做」，又不谎称
已覆盖。断言生成步骤修复它、断言验证步骤复验 PASS 后，它移入
分子。

## 门禁

上游 strategy 步骤（Strategy Planner）定义带量化阈值的质量门禁。
上游 planning 步骤（Plan）在每个 Phase 出口调用本 skill。任何
维度的有效覆盖低于阈值，emit `GATE_FAILURE`。

分母为零的维度是物化失败，不是 100% 覆盖。只有已评审 Strategy
在 `not_applicable_dimensions` 中的声明才能把空维度标为
`NOT_APPLICABLE`。

```
for each dimension in [rule, scenario, state, assertion]:
 effective_coverage = compute(dimension, skill11_results)
 threshold = strategy_contract.gate_thresholds[dimension]
 if effective_coverage < threshold:
 emit GATE_FAILURE(dimension, effective_coverage, threshold, missing_list)
```

`GATE_FAILURE` 阻断 Phase（上游 planning 步骤扣住 Plan）并触发
人工评审（缺失覆盖是评审项：由人决定是补写缺失测试，还是修订
Strategy Contract 正式移出范围）。门禁绝不静默降低标准——阈值
不达标时，诚实的路径只有两条：「补测试」或「经已评审的
Strategy Contract 修订改阈值」。

## 本 skill 禁止事项

- **绝不把原始行覆盖率当覆盖率数字报告。** 规则明确。行覆盖率
  至多是信息性侧指标，绝不作为门禁信号。
- **绝不把 REJECTED 断言计为已验证覆盖。** 它对分子贡献为零，
  仍是分母责任，并阻断断言门禁。剔除它等于隐藏已确认的验证
  失败。
- **绝不跨层直连查询。** 设计规则："审计基于图查询（沿 DERIVES → CONSTRAINS → REALIZED_BY 传导路径，禁止跨层直连查询)"。
  直接 Case→Requirement 查询绕过了 Rule 绑定，会把引用了需求、
  却跳过真正编码需求的规则的用例也计入。永远沿图边游走。
- **绝不为让门禁通过而静默自动修订 Strategy Contract。** 移出
  范围是 routed 到人工评审的人工决策。

## 集成

- **输入**：Traceability Graph（全部资产 + 边）、Strategy
  Contract（阈值）、断言验证结果（逐断言 verdicts）。
- **输出**：
 - 上游 planning 步骤：GATE_PASS / GATE_FAILURE（决定 Phase 能否
   关闭）。
 - 人工评审：缺失覆盖清单作为评审项（GATE_FAILURE 时）。
 - 下游治理报表：覆盖矩阵喂给治理看板。
- **横切**：本 skill 在每个 Phase 出口门禁被调用。它不是流水线
  末端的一次性报告；流水线中段的 Phase 有自己的阈值，中段的
  GATE_FAILURE 正是系统在「早期规则覆盖偷工」滚雪球之前抓住它
  的手段。

## 存疑时

无法确定某资产是否计入覆盖时，先查它的断言验证步骤 verdict。
没有 verdict（断言验证步骤尚未跑过它）就意味着只计分母——绝不
计入分子。未验证的资产不是覆盖，至多是意图。这个不对称性就是
全部要点：给未验证资产记功的流水线在表演覆盖剧场，而它报出的
数字会被用来做发布/不发布决策。

各维度公式、图边语义与漏测分级（missing-coverage triage）见
`references/coverage_calculus.md`。
