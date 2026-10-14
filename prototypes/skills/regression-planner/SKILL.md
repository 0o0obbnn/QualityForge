---
name: regression-planner
description: 在回归运行开始前校验草拟的回归选择。在 change-impact-analyzer 产出受影响资产清单之后、回归运行开始之前使用。强制：选择必须是真子集而非默认全量回归；每个 breaking-drift 与高风险资产都被覆盖；每个排除都携带理由；没有任何受影响资产被静默丢弃。不得用本 skill 执行回归运行。不得用它计算受影响资产清单（改用 change-impact-analyzer）。
---

# Regression Planner

把"改了什么"翻译成"要重测什么，且只重测这些"。它是影响分析的互补
另一半——消费受影响资产清单，审计据此做出的选择。

## 这些保证

- **不默认全量回归**：选择必须是子集，不是"全部"。
- **breaking drift 必覆盖**：所有受 breaking-drift 影响的资产必须纳入，没得商量。
- **排除有据**：每个被排除的资产都携带理由。
- **高风险必覆盖**：所有高风险资产要么被选中，要么有记录在案的排除。
- **无静默丢弃**：`all_impacted_assets` 中的每个资产要么被选中，要么被显式排除。正是这条让选择成为*充分*而非仅仅*最小*。
- **选择可溯源**：选中的资产若不在受影响清单里，就无法溯源到影响分析。

## 判定与 Finding Codes

| Code | Severity | 含义 |
|---|---|---|
| `FULL_REGRESSION_DEFAULT` | REJECT | 选择等于整个套件；不构成选择。 |
| `BREAKING_DRIFT_EXCLUDED` | REJECT | breaking-drift 资产未被选中。 |
| `EXCLUSION_WITHOUT_REASON` | REJECT | 排除没有理由；无法问责的缺口。 |
| `HIGH_RISK_EXCLUDED` | REJECT | 高风险资产既未选中也无有记录的排除。 |
| `IMPACTED_ASSET_UNACCOUNTED` | REJECT | 受影响资产既未选中也无有记录的排除。 |
| `SELECTED_ASSET_NOT_IMPACTED` | REJECT | 选中资产不在 `all_impacted_assets` 中。 |
| `SUITE_SIZE_UNDECLARED` | REJECT | `total_suite_size` 缺失或 ≤ 0；全量回归检测被禁用。 |
| `EMPTY_SELECTION_PACKET` | REJECT | 既无选择也无排除；无从审计。 |

输出：`PASS`（执行回归）或 `REJECT`（修正选择）。

未声明 `total_suite_size` 判 REJECT 而非跳过检查：没有它，"不做全量回归"
的保证就无法评估，而被禁用的检查绝不能读作已满足。

## 运行确定性检查器

```bash
python scripts/regression_check.py --selection path/to/selection.json [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input.

## 本 skill 禁止事项

- **绝不盲目选择整个套件。** 没有影响分析的全量跑是弃责，不是安全网。
- **绝不无记录理由地排除资产。** 无文档的排除是看不见的覆盖缺口。
- **绝不丢掉 breaking-drift 资产。** 这种排除在任何风险等级下都不可用。
- **绝不执行回归运行。** 本 skill 审计计划；执行在下游。

## 使用示例

**正确用法：**
- 拿到影响报告后生成一个测试子集，确保所有 breaking-drift 资产都包含在内。
- 为从运行中排除某些测试用例记录具体理由。

**错误用法：**
- 为了保险起见运行整个测试套件。
- 不记录清晰理由就把某测试用例排除出回归套件。

## 集成

- **输入**：影响报告、风险等级、breaking-drift 清单。
- **输出**：按优先级排序的回归选择、排除审计清单。

选择算法与优先级排序，读 `references/regression_rules.md`。
