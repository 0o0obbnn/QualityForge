# 数据需求规则参考

`scripts/requirement_check.py` 是可执行编码；本文档是意图说明。

## Finding codes（完整清单）

| Code | Severity | 含义 |
|---|---|---|
| `CATEGORY_MISMATCH` | REJECT | requirement 的 fixture_category 与用例声明不一致 |
| `ORPHAN_REQUIREMENT` | REJECT | case_id 在用例批次中不存在 |
| `INVALID_PRECONDITION_STATE` | REJECT | 前置状态不是已声明的合法状态，或实体没有 SM |
| `UNREACHABLE_TARGET_STATE` | REJECT | 状态已声明但经迁移不可达 |
| `MISSING_SENSITIVE_FIELD` | REJECT | 所需实体上 IR-SENSITIVE 的字段未列入 sensitive_fields |
| `STATIC_NOT_IN_BASELINE` | REJECT | Static 需求引用的实例不在任何 baseline 中 |
| `DYNAMIC_NO_STEPS` | REJECT | Dynamic/Hybrid 需求没有 construction_steps |

## 敏感字段链（合规挂钩）

最重要的一项检查。三个 skill 连成一条无断点的链：

```
the IR-validation step (IR Validator) → field marked SENSITIVE in IR
the data-requirement step (this) → requirement lists it in sensitive_fields
the data-generation step (Compliance) → generated data packet masks it
```

所需实体上存在 IR 标记为 SENSITIVE 的字段、而 requirement 遗漏了
它时，触发 `MISSING_SENSITIVE_FIELD`。这样的 requirement 是不完整
的，会让下游数据生成步骤的合规门禁失效——数据生成步骤只能对
被告知敏感的字段做脱敏，而告知来源就是这里。

交叉引用是单向的：IR → requirement。requirement 可以向
`sensitive_fields` 追加字段（ADD，偏执一点没关系），但绝不可
OMIT 任何 IR 声明为 SENSITIVE 的字段。

## 状态可达性（与 IR 校验步骤/场景生成步骤共享算法）

初始状态推断：一个状态只作为迁移的 `from` 出现、从未作为 `to`
出现，即为「初始」。若每个状态都是迁移目标（成环），取第一个
声明的状态为初始。这与 IR 校验步骤的可达性检查使用同一启发式；
保持一致意味着通过 IR 校验步骤的 IR，产出的前置条件也能通过
数据需求步骤。

前置状态或 target_state 是已声明但不可达的状态时，判
`UNREACHABLE_TARGET_STATE` 而不是 `INVALID_PRECONDITION_STATE`。
区分有意义：INVALID 表示「根本不是状态」（拼写错误、幻觉）；
UNREACHABLE 表示「真实状态、无路径可达」（规格缺口）。两者都是
REJECT，但修复指引不同。

## Fixture 类别语义

| 类别 | requirement 义务 | 检查规则 |
|---|---|---|
| `Static` | 使用预构建 baseline 实例。`instance_id` 必须引用已声明的 baseline。 | 实例不在 baselines 中判 `STATIC_NOT_IN_BASELINE`。 |
| `Dynamic` | 现场构建。`construction_steps` 必须非空。 | 为空判 `DYNAMIC_NO_STEPS`。 |
| `Hybrid` | baseline + 增补。`construction_steps` 必须非空（即增补部分）。 | 为空判 `DYNAMIC_NO_STEPS`。 |

`fixture_category` 必须与源用例的声明一致（`CATEGORY_MISMATCH`）。
类别的权威是用例——requirement 只是回显它，不能覆盖它。

## 本检查器不验证什么

- **取值质量。** 所需数据是不是好的边界数据，是数据生成步骤的
  采样职责。本检查器只验证物料清单的一致性。
- **数量正确性。** 「100 个实例」对一次负载测试是否正确，是下游
  性能测试生成关心的事。本检查器对数量直接放行。
- **构建步骤的可执行性。** 下游 fixture 规划能否把步骤建出来，
  是下游 fixture 规划的 DAG 规划问题。本检查器只验证
  Dynamic/Hybrid 有步骤存在。
