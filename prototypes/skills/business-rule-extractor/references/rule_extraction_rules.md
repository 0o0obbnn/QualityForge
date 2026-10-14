# 规则抽取规则

## Finding codes

| Code | Severity | 含义 |
|---|---|---|
| `UNSTRUCTURED_RULE` | REJECT | 规则缺少 condition 或 action。 |
| `INFERRED_RULE_MISSING_REVIEW_ROUTE` | REJECT | 推断规则未标记 NEED_HUMAN_REVIEW。 |
| `INVALID_INFERRED_CONFIDENCE` | REJECT | 推断 confidence 缺失、为布尔、非数值、非有限数，或不在 [0,1] 内。 |
| `RULE_FORCED_INTO_SHAPE` | REJECT | 无法结构化的规则未路由到评审。 |
| `RULE_NO_SOURCE` | REJECT | 规则没有来源引用。 |

## Condition → Action 语法

一条规则必须同时具备：
- `condition`：触发条件（如 "total > 0"、"user.role == 'admin'"）。
- `action`：后果动作（如 "validate order"、"grant access"）。

不具备该结构的自由文本描述无法被确定性测试——没有清晰的
通过/失败边界。

## 推断规则的评审路由

若 `inferred=true` 或来源为 "inferred"/"guess"/"deduced"，则
confidence（提供时）必须是 [0,1] 内的有限非布尔数值。更重要的
是：无论分数多高，`validation_status` 必须为 `NEED_HUMAN_REVIEW`。
模型填补了来源空缺，不存在任何通用数值截断能解决它。
