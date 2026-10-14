---
name: quality-governance
description: 面向干系人的质量治理仪表盘的诚实性门禁。每当治理报告成稿、在干系人看到之前使用。要求有效覆盖而非行覆盖、按 skill 拆解成本并对超限告警、规范化的指标定义，以及仅咨询性的行为。不得放行未经验证或未声明的指标。不得用本 skill 修改 Strategy Contract。不得用它计算覆盖（改用 coverage-analyzer）。
---

# Quality Governance

治理仪表盘是干系人看到的东西。本 skill 确保他们看到的是诚实的。

## 本 skill 为何存在

治理仪表盘以四种可复现的方式误导人：把原始行覆盖冒充覆盖、隐藏成本超限、临时重定义指标，以及仪表盘悄悄修改它本应如实汇报的策略。

## 四项治理检查

每项检查陈述一条*要求*；违反即产出所示 code。

| # | 要求 | 违反时的 code |
|---|---|---|
| 1 | 每个覆盖指标都必须是 `type: effective`——绝不是 line/branch/statement。 | `RAW_LINE_COVERAGE_REPORTED`, `NO_METRICS_REPORTED` |
| 2 | 成本必须按 skill 拆解、声明预算，任何超限必须触发告警。 | `COST_NOT_DECOMPOSED`, `BUDGET_NOT_DECLARED`, `BUDGET_OVERRUN_SILENT` |
| 3 | 报告仅具咨询性；不得修改策略阈值。 | `STRATEGY_AMENDED_BY_DASHBOARD` |
| 4 | 指标定义必须来自规范化来源。 | `METRIC_DEFINITIONS_UNDECLARED`, `METRIC_REDEFINED_ADHOC` |

输出：`PASS`（发布仪表盘）或 `REJECT`（修正指标/成本/策略）。

空荡或声明不足的仪表盘是 REJECT，不是干净通过。一份没有指标、没有声明预算、没有说明指标定义来源的报告，等于把对应检查关掉了——而被关掉的检查绝不能被报告为已满足。

## 运行确定性检查器

```bash
python scripts/governance_check.py --report path/to/dashboard.json [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input.

## 本 skill 禁止事项

- **绝不发布覆盖数字实为行覆盖的仪表盘。** 有效覆盖是唯一的门禁信号。
- **绝不静默吞掉成本超限。** 无告警的超限就是 REJECT。
- **绝不修改 Strategy Contract。** 治理负责汇报，不负责立法。阈值变更是经 review 的人类决策。
- **绝不把未声明的指标来源当作规范来源。** 无法验证的出处本身就是一个 finding。
- **绝不越过安全或阻断级质量门禁。** 那些不是咨询性的。

## 使用示例

**正确：**
- 评估一份覆盖报告，确认它使用「有效覆盖」并与规范定义一致。
- 拒绝一份静默吞掉 3 倍 token 成本超限的仪表盘草稿。

**错误：**
- 批准一份用行覆盖而非有效覆盖计算的治理报告。
- 在仪表盘展示层直接修改策略阈值（如测试通过率）。

## 集成

- **输入**：治理报告草稿、策略契约、规范化指标定义。
- **输出**：校验通过的仪表盘，或带具体 findings 的 REJECT。

有效覆盖规则、成本拆解与咨询性边界，见 `references/governance_rules.md`。
