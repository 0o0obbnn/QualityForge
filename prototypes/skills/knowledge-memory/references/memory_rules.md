# Knowledge 记忆规则

## Finding codes

| Code | Severity | 含义 |
|---|---|---|
| `NO_PROVENANCE` | REJECT | 条目缺少来源或 confidence。 |
| `SENSITIVE_IN_ENTRY` | REJECT | 发现未脱敏的敏感模式。 |
| `UNVETTED_FEEDBACK` | REJECT | 符合反馈条件却没有评审签署。 |
| `NO_TIMESTAMP` | REJECT | 没有 created_at，无法做衰减调度。 |
| `DUPLICATE_ENTRY` | REJECT | 内容 hash 与既有条目一致。 |

## 敏感模式

检查器扫描条目文本中的：
- 形似手机号的模式（\d{3}-\d{3,4}-\d{3,4}）。
- `password=`、`api_key=`、`Bearer <token>` 字面量。

这些是最小集；真实部署应按自己的 PII 目录扩展正则。

## 反馈评审

标记 `feedback_eligible: true` 的条目必须携带 `review_signoff`
（评审人 id 或评审时间戳）。未评审的反馈会把猜测自动灌回流水线
——正是该检查要防的失败模式。

## 衰减

条目携带 `created_at`。衰减流程（本检查器之外）用该时间戳给
旧条目降权或过期。没有时间戳的条目无法衰减——它会以全权重
永久留存。

## 重复检测

`{pattern, summary, content}` 的内容 hash（SHA-1，前 12 位十六
进制）。hash 一致意味着同样的知识已存过；重复条目被拒绝，避免
反馈环节重复计数。
