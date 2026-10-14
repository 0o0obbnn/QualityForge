# 测试设计输入契约 2.0

`test_design_input` 是版本化需求图谱面向测试用例设计的受约束编译结果。图谱仍是完整事实层；输入切片只暴露当前最小功能或独立非功能要求及已放行测试维度需要的事实。

## 防幻觉不变量

- 正式测试用例只能消费状态为 `READY` 的维度。
- 业务事实只能来自 `rule_registry` 和 `evidence_registry`；缺少规则、Oracle 或证据时阻断并形成待确认问题。
- `REQUIREMENT_FACT` 与 `TEST_DERIVATION` 必须分开。边界值、等价类和判定表属于推导方法，不得创造新的业务行为。
- `ASSUMPTION` 不允许进入正式用例。
- 下游用例必须保留 `graph_snapshot_id / requirement_ids`；功能项保留 `atomic_id / field_usage_id / rule_id / evidence_id`，非功能项保留 `nfr_id / quality_attribute / evidence_id`。

## 顶层结构

```text
meta
source_artifacts
graph_snapshot_id
fact_policy
evidence_registry[]
rule_registry[]
items[]
coverage
acceptance
```

`source_artifacts` 必须记录图谱与评审摘要哈希。`graph_snapshot_id` 标识本次编译使用的不可混用快照。
同时必须暴露评审生命周期、结论、未评审数量和 `acceptance.source_review_scope`。
`PARTIAL_REVIEW_PROJECTION` 只表示当前评审快照中的局部 READY，禁止描述为需求全文已确认范围；
只有评审 `PASS`、下游可用且未评审数为 0 时才是 `FULLY_REVIEWED_SOURCE`。

## 维度门禁

每个 `items[].dimension_eligibility` 分别包含 `functional / field_validation / sorting / state_transition / permission / integration / nfr`。

`item_kind=functional` 时必须包含 `function_id / atomic_id`；`item_kind=non_functional` 时必须包含 `nfr_id / quality_attribute`，不得为非功能要求伪造功能或最小功能 ID。

- `READY`：事实、证据和该维度所需 Oracle 完整，没有未解决 finding。
- `REVIEW_REQUIRED`：内容可供分析，但正式用例生成必须跳过。
- `BLOCKED`：存在 REJECT finding、占位信息或关键事实缺失。
- `NOT_APPLICABLE`：该最小功能不适用该维度。

包内存在至少一个 `READY` 维度时，可以 `PARTIAL_PASS` 并设置 `downstream_eligible=true`，但 `acceptance.scope` 必须是 `READY_DIMENSIONS_ONLY`。只有全部适用维度为 `READY` 才是 `PASS`。

## 规则、字段使用和证据

规则必须具有稳定 `rule_id`、类别、所属节点、规则文本、`evidence_ids` 和 `provenance_type`。字段必须以具体使用关系输出，而不是只引用全局字段：

```json
{
  "field_usage_id": "FUSE-...",
  "field_id": "FLD-...",
  "usages": ["input", "validation"],
  "direction": "read",
  "rule_ids": ["RULE-..."],
  "evidence_ids": ["EVD-..."]
}
```

下游生成的每个预期结果必须声明 `oracle_rule_ids` 或 `oracle_evidence_ids`。无法建立 Oracle 时输出澄清项，不得输出正式预期结果。

`relation_context` 只传递当前功能关联的依赖、引用、状态流、数据流和冲突；`flow_context` 只传递包含当前最小功能的已确认业务流。候选关系不得伪装成已确认流程。

## 验收

运行 `validate_test_design_input.py`。校验器必须拒绝悬空规则/证据、跨快照条目、带 blocker 的 READY 维度、错误覆盖计数、允许假设的策略，以及没有 READY 维度却声称可下游使用的产物。

全量包用于盘点，不应整包放入生成模型上下文。正式流水线必须默认使用 `--ready-only`，只把至少有一个 `READY` 维度的条目交给测试用例生成 Skill。需要更小上下文时再使用 `--atomic-id` 选择一个最小功能或小批次；编译器同时裁剪未被切片引用的规则和证据。不带 `--ready-only` 的输出只用于人工/机器盘点门禁分布，不是正式用例生成输入。
