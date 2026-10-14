# 断言批次规则

`scripts/batch_check.py` 是可执行编码；本文档是意图说明。

## 弱断言模式

断言命中任一模式即被检查器判定为弱断言：

| 模式 | Code | 示例 |
|---|---|---|
| 只查状态码 | `status_code_only` | `status_code == 200` |
| 只查存在性 | `presence_only` | `response is not None` |
| 只查类型 | `type_only` | `isinstance(total, int)` |
| 恒真 | `constant_true` | `True == True` |
| 无字段引用 | `no_field_reference` | 断言没有 `target` 也没有 `field` |

分类之前，每条断言必须是对象，且 `assertion_id`、`expression`、
`expected` 非空，并具备 `target` 或 `field` 之一。缺少可执行的
比较结构即 `INVALID_ASSERTION_STRUCTURE`，整个批次被拒绝；绝不会
仅因为带了 target 就当作强断言。其余断言默认分类为**强**。

## 为什么是语法层，不是语义层

本检查是快速的语法过滤，不是运行时验证。它读取断言的
expression 文本并做模式匹配，无法判断一条「强」断言在上下文里
是否其实很弱（例如 `total == 100`，而 100 恒为答案）。那是
mutation 门禁的职责。

取舍是：语法分类快（不执行）、保守（能抓住明显的弱模式）。
它是保护验证预算的早期过滤器，不是质量的最终裁决者。

## 阈值

默认 0.3：一个批次中至多 30% 为弱断言。这是宽松上限——设计良好
的批次里大多数断言应校验具体取值，只保留少量 status/presence
检查作为 sanity。

调参：
- 调低（0.2）：用于关键路径模块，每条断言都应是取值级校验。
- 调高（0.5）：用于冒烟批次，presence 检查本来就是主要意图。

阈值优先取自 strategy contract；未设置时使用默认值。

## 本检查器不做的事

- **逐条断言的正确性。** 某条断言引用的 IR 字段是否有效，是逐条
  断言验证的职责。
- **Mutation 测试。** 断言能否真正抓住 bug，是 mutation 门禁的
  职责。
- **语义强度。** 一条「强」断言在上下文中是否真强，需要运行时
  分析。
- **强化弱断言。** 那是生成器的职责；本 skill 只报告、只拒绝。
