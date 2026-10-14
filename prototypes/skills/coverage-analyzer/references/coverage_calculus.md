# 覆盖率计算参考

四个维度的详细公式与图语义。`scripts/coverage.py` 是可执行编码；
本文档是意图说明。

## 图边（traceability 路径）

Traceability graph 沿固定路径连接资产。覆盖率只能沿这些边游走
计算——绝不许跨层抄近路。

```
Requirement ─REALIZED_BY─▶ Rule ─DERIVES─▶ Scenario ─COVERED_BY─▶ Case ─VERIFIED_BY─▶ Assertion
 │ │ │ │ │ │
 └─CONSTRAINS───┴────────────┴──────────────┴─────────────┴──────────────┘
```

| 边 | 含义 | 使用维度 |
|---|---|---|
| `REALIZED_BY` | 一条需求被一条或多条规则实现 | （Dim 1 的上下文） |
| `DERIVES` | 一条规则派生一个或多个场景 | Dim 2 |
| `COVERED_BY` | 一个场景被一个或多个用例覆盖 | Dim 2 |
| `VERIFIED_BY` | 一个用例被一条或多条断言验证 | Dim 4 |
| `CONSTRAINS` | 一条规则/状态约束一个用例（经 rule_id 绑定） | Dim 1、Dim 3 |

### 为什么禁止跨层查询（设计禁令）

设计规则："禁止跨层直连查询"。具体地说：不要直接查询
`Case → Requirement` 来计算需求覆盖。路径是
`Requirement → Rule → Case`。一个引用了需求却跳过规则绑定的用例
是孤儿——它声称测了需求，却没测编码该需求的规则。沿边游走强制
每条覆盖声明都经过规则绑定，这正是覆盖率可审计的原因。

## 维度公式

### Dim 1 — 规则覆盖

```
rule_coverage = |{ r ∈ IR.rules : ∃ c ∈ cases, c.rule_id == r.rule_id }|
 ÷ |IR.rules|
```

- 分子：至少有一个用例经 `rule_id` 绑定的 IR 规则。
- 分母：全部 IR 业务规则。
- 缺失清单：`IR.rules - bound_rules`，按 `rule_id` 列出。

一条未覆盖的规则等于一条被静默丢弃的需求。这是默认最严的维度
（阈值 1.0）：IR 中每条规则都应至少有一个用例。如果某条规则确实
不在范围内，应在 IR 里正式移出范围（IR 编译步骤的返工），而不是
留着不覆盖。

### Dim 2 — 场景覆盖

```
scenario_coverage = |{ s ∈ scenarios : ∃ c ∈ cases, c.scenario_id == s.scenario_id }|
 ÷ |scenarios|
```

- 分子：至少有一个落地用例的场景（场景生成步骤的产出）。
- 分母：全部生成的场景。
- 缺失清单：未落地的场景 ID。

生成了场景却没有用例，意味着场景生成步骤产出了一个测试意图
（异常路径、边界、权限边角），用例生成步骤却从未把它转成可执行
测试。该场景只存在于纸面上，贡献为零的可执行验证。

### Dim 3 — 状态覆盖

```
state_coverage = |{ t ∈ ⋃ SM.transitions : t ∈ exercised_transitions }|
 ÷ |⋃ SM.transitions|
```

- 每条迁移以 `sm_id:from->to` 为键（经两条路径可达的状态算两条
  迁移）。
- 分子：至少被一个用例执行过的迁移。
- 分母：IR 全部状态机的全部迁移。
- 缺失清单：未执行的迁移键。

这是按迁移计，不是按状态计。一个每个状态都可达、但
PENDING→PAID 迁移从未被执行的状态机，即使所有状态都出现在某
用例里，仍有状态覆盖空洞。状态覆盖抓的是「测了状态、没测状态
变化」。

### Dim 4 — 断言覆盖（有效口径）

```
assertion_coverage = |{ a : skill11_verdict(a) == PASS }|
 ÷ (|PASS| + |REPAIR| + |REJECT| + |UNVERIFIED|)

# Any REJECT independently forces the assertion dimension to FAIL.
```

| 断言验证步骤的 verdict | 分子 | 分母 | 理由 |
|---|---|---|---|
| `PASS` | ✓ | ✓ | 已验证——计入真实覆盖。 |
| `REPAIR` | ✗ | ✓ | 存在但未验证；拉低分数，而不是谎称已覆盖。 |
| `REJECT` | ✗ | ✓ | 已确认的验证失败；保留为质量债并阻断断言门禁。 |
| missing/unknown | ✗ | ✓ | 验证没有产出可用证据。 |

分母保持规则是承重墙。两个备选方案及其错误之处：

- *把 REPAIR 计入分子*：撒谎。该断言未经验证。
- *剔除失败或不完整的 verdict*：隐藏已知质量债。50 PASS +
  50 REPAIR 的套件如果剔除 REPAIR 会报 100%，这比撒谎更糟——
  它让半成品套件看起来完整。REPAIR 只计入分母会报 50%，
  如实反映「我们还有大量待验证」。

`snapshot.assertions` 存在时，断言清单是权威依据。Verdict 按
`assertion_id` 一对一连接；重复的 verdict IDs、重复的必需 IDs、
畸形记录、以及清单之外断言的 verdict 都属证据错误，强制该维度
FAIL，绝不增加分子。没有断言清单的遗留 snapshot，以去重后的
verdict IDs 定义责任集。

断言生成步骤修复一条 REPAIR/REJECT 断言、且断言验证步骤复验为
PASS 后，该断言从「仅分母」移入「分子+分母」，分数上升。这个
移动就是闭环在起作用的信号。

## 0/0 规则

`_pct(0, 0) == 0.0`，不是 1.0。分母为零的维度（无 IR 规则、无
场景、无迁移）是数据问题——通常意味着 IR 为空或 snapshot 物化
错误——而不是完美覆盖。报 1.0 会让一条无可测试内容的流水线
静默通过门禁。

因此空维度无论数值阈值如何一律 FAIL。只有当已评审的 Strategy
在 `not_applicable_dimensions` 中显式列出该维度时才可跳过；
其 verdict 记为 `NOT_APPLICABLE`。覆盖率与阈值比较使用未舍入的
分数。三位小数值仅供展示，所以 `2124/2500` 不可能变成通过的
`0.85`。

如果你看到分母为 0、覆盖率为 0.0，按 IR 编译 / snapshot 提取
的 bug 处理，不要当作覆盖率结果。

## 缺失覆盖分诊（漏测分级）

某维度未过门禁时，缺失清单按以下方式分诊供人工评审：

| Severity | 条件 | 处置 |
|---|---|---|
| `BLOCKING` | 关键路径需求（认证/支付/权限）中的规则未覆盖。 | Phase 不得关闭。补写测试，或经 Strategy 修订正式移出范围。 |
| `HIGH` | 高业务影响的规则（非关键路径，但涉及资金/客户）。 | 强压力要求 Phase 关闭前覆盖；转人工评审。 |
| `MEDIUM` | 普通影响的规则。 | 记为测试债；凭书面豁免可以关闭 Phase。 |
| `LOW` | Strategy 中显式标注范围外的场景或迁移。 | 仅供参考；无需动作。 |

分诊 severity 是建议性的——它喂给人工评审做路由。门禁 verdict
（PASS/FAIL）纯粹基于阈值；分诊回答的是对失败*做什么*，而不是
*是否*失败。

## 本 skill 不计算什么

- **行/分支覆盖。** 设计上明确排除在范围外。覆盖工具的行覆盖率
  在这里不作为任何计算的输入。如果有人要了解，去看覆盖工具自己
  的报告；本 skill 不转述。
- **Strategy 阈值。** 那些来自 strategy 步骤，本 skill 只消费。
  为过门禁而改阈值属于 Strategy Contract 修订，必须经人工评审，
  不是 coverage-analyzer 的动作。
- **测试质量。** 那是断言验证步骤的职责（mutation 分数）。本
  skill 消费断言验证步骤的 verdicts，不重新评判断言质量。
