---
name: business-rule-extractor
description: 在 Testing IR 融合前校验候选业务规则。在一轮抽取产出候选规则之后、对该候选 packet 使用。检查 condition/action 结构、来源引用、置信度元数据有效性，以及每条推断或不可结构化规则强制路由到 NEED_HUMAN_REVIEW。置信度绝不能授权一条推断规则。不得使用本 skill 从来源文档抽取规则——它只校验已抽取的候选。
---

# Business Rule Extractor

规则是 IR 中可测试的原子。本 skill 确保每条规则在融合前确实是一条
规则（结构化、有来源、置信度诚实）。

## 四项规则检查

| 检查项                       | Code                                  | 拦截什么                                          |
| ---------------------------- | ------------------------------------- | ------------------------------------------------- |
| condition→action 结构        | `UNSTRUCTURED_RULE`                   | 规则没有 condition 或没有 action。                |
| 推断规则路由给人             | `INFERRED_RULE_MISSING_REVIEW_ROUTE`  | 推断规则未标记 NEED_HUMAN_REVIEW。                |
| 推断置信度有效               | `INVALID_INFERRED_CONFIDENCE`         | 置信度缺失、布尔、非数值、非有限或超出范围。      |
| 不可结构化 → NEED_HUMAN_REVIEW | `RULE_FORCED_INTO_SHAPE`            | 规则被标记为不可结构化但未 NEED_HUMAN_REVIEW。    |
| 来源引用                     | `RULE_NO_SOURCE`                      | 规则没有 source 字段。                            |

本原型校验抽取出的草稿；它本身不执行来源解析或抽取。模型推断而非
直接从权威来源读到的规则永远带有认识论风险。无论置信度多高，都
必须标记 `NEED_HUMAN_REVIEW`；分数只是元数据。

## 集成

- **输入**：抽取出的规则草稿 + 来源文档。
- **输出**：已校验的规则列表，或 REJECT 并标出具体规则。



## 运行确定性检查器

```bash
python scripts/rule_check.py --packet path/to/rules.json [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input.

## 本 skill 禁止事项

- **反模式**：绝不把业务规则改述成更弱的约束。绝不把多条独立规则合并成一条。

## 使用示例

**正确用法：**
把一条没有 `NEED_HUMAN_REVIEW` 的推断业务规则标记为 `INFERRED_RULE_MISSING_REVIEW_ROUTE`。

**错误用法：**
填一个通用或假定的来源名，让没有来源引用的规则通过。

condition/action 语法与「推断」判定规则见 `references/rule_extraction_rules.md`。
