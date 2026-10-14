# 回归选取规则

## Finding Codes

| Code | Severity | 含义 |
|---|---|---|
| `FULL_REGRESSION_DEFAULT` | REJECT | 选取结果就是整个测试套件（>10）。 |
| `BREAKING_DRIFT_EXCLUDED` | REJECT | 受 breaking drift 影响的资产未被选入。 |
| `EXCLUSION_WITHOUT_REASON` | REJECT | 排除的用例没有理由。 |
| `HIGH_RISK_EXCLUDED` | REJECT | 高风险资产既未选入也未记录排除。 |

## 为什么全量回归被拒绝

默认全量回归意味着没有人分析爆炸半径——这种"选取"等于"全测"，等于没有选取。它浪费算力、拖慢反馈，还掩盖了哪些失败与本次变更相关。

## 排除审计

每个被排除的用例 MUST 给出理由。排除清单就是审计线索，回答复盘时的"为什么没测 X"。像"风险低、不依赖变更模块"这样的理由是有效的；没有理由则无效。

## Breaking drift 没有商量余地

Breaking drift 意味着契约发生了不兼容变更。任何受 breaking drift 影响的测试 MUST 进入回归集，不论优先级或预估成本。跳过一个 breaking-drift 测试就是把回归发布上线。
