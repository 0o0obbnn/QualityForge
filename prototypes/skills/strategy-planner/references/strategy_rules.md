# 策略校验规则

`scripts/strategy_check.py` 是可执行行为的权威。

## 关键路径靠声明，不靠猜测

检查器从不预设固定的领域词表。上游分析列出当前项目的关键路径，然后校验器要求显式决定纳入或排除：

| 处置 | 必需证据 |
|---|---|
| `IN_SCOPE` | 一个或多个存在于 `In_Scope` 中的 feature ID。 |
| `OUT_OF_SCOPE` | 非空的排除理由。 |

这样既检测沉默，又不把支付/认证概念强加给测试设计平台、数据管道、嵌入式系统或其他无关领域。

## 主要 findings

| Code | Severity | 含义 |
|---|---|---|
| `CRITICAL_PATH_FEATURE_NOT_IN_SCOPE` | REJECT | 声明纳入的关键路径绑定了未声明的 feature。 |
| `MISSING_CRITICAL_PATH_EXCLUSION_REASON` | REJECT | 被排除的关键路径没有给出理由。 |
| `DUPLICATE_CRITICAL_PATH_ID` | REJECT | 关键路径 ID 重复。 |
| `INVALID_RISK_LEVEL` | REJECT | feature 风险缺失或非法。 |
| `GATE_NOT_QUANTIFIED` | REJECT | gate 没有阈值。 |
| `GATE_THRESHOLD_NON_NUMERIC` | REJECT | 阈值是布尔、非数值、NaN 或无穷。 |
| `GATE_THRESHOLD_OUT_OF_RANGE` | REJECT | 阈值不在 `[0,1]` 内。 |
| `PYRAMID_SUM_INVALID` | REJECT | 份额之和不是 `1.0 ± 0.001`。 |
| `PYRAMID_INVERTED` | REJECT | E2E 份额超过 unit 份额。 |
| `PYRAMID_TROPHY` | REVIEW | 集成份额超过 unit 份额。 |
| `CORE_LAYER_MOCKED` | REJECT | DB/repository/内部数据路径被 mock。 |

质量门阈值是归一化比率。带单位的门（如延迟上限）需要未来引入单位感知的契约，而不是过载本 schema。
