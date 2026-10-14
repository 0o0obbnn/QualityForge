# 治理看板规则

## Finding Codes

| Code | Severity | 含义 |
|---|---|---|
| `RAW_LINE_COVERAGE_REPORTED` | REJECT | 覆盖率指标使用行/分支/语句口径。 |
| `COST_NOT_DECOMPOSED` | REJECT | 缺少按 skill 分解的成本。 |
| `BUDGET_OVERRUN_SILENT` | REJECT | 成本超预算且无告警。 |
| `STRATEGY_AMENDED_BY_DASHBOARD` | REJECT | 报告修改了策略阈值。 |
| `METRIC_REDEFINED_ADHOC` | REJECT | 使用非规范口径的指标定义。 |

## 只认有效覆盖率

任何名称含 "coverage" 的指标 MUST 标注 `type: "effective"`。行/分支/语句覆盖率往好里说是参考信息，往坏里说是误导（它们把弱断言也计入覆盖）。effective口径 会剔除 REJECTED 断言——这是唯一诚实的数字。

## 成本分解

成本必须按 skill 分解（token 成本、执行时间）。只有总量的成本看不出哪个 skill 在失控消耗。每个定义了预算且超支的 skill 都必须触发告警——静默超支就是云账单突袭的来源。

## 仅提供建议

治理对策略只做 REPORT，不做 AMEND。阈值变更必须走策略契约的修订路径（经审核），而不是在看板上直接改。一份改动了阈值的报告等于绕过了审核。
