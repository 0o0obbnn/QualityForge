---
name: ir-validator
description: Testing IR 的发布门禁。在 IR 草稿已通过 requirement-compiler 之后、任何下游 skill 消费它之前使用。运行六组确定性检查族，输出 PASS、PASS_WITH_REVIEW 或 REJECT。不得使用本 skill 生成或修改 IR。不得用它审计融合过程（改用 requirement-compiler）或需求评审报告（改用 requirement-quality-gate）。
---

# IR Validator

Testing IR 的发布门禁。上游 IR 编译步骤负责编译；本 skill 决定这次
编译是否可以发布。

## 六组检查族

对每份 IR 草稿运行全部六组（细节见 `references/validation_rules.md`）：
1. **SCHEMA COMPLETENESS** —— 必填字段齐全
2. **PROVENANCE BINDING** —— 每个条目都有 `source_trace`
3. **CONFIDENCE TIERING** —— 分数存在且在 [0,1] 内
4. **CONFLICT RESOLUTION** —— 无未解决冲突，**且每个冲突保留全部分歧版本**
5. **STATE-MACHINE REACHAB.** —— 无死状态/不可达状态
6. **ENTITY FIELD SANITY** —— ≥1 个字段，无裸 PUBLIC

## 本门禁强制的设计不变量

两条只有发布门禁才能守住的规则，因为它是下游 skill 把 IR 当作真相
之前的最后一道关卡：

- **缺失的证据绝不变成干净的 PASS。** 缺失的 `source_trace`、缺失的
  置信度分数或不可用的来源降级为 `PASS_WITH_REVIEW` 或 `REJECT`——
  绝不静默 `PASS`，绝不捏造值。
- **冲突保留所有版本。** 一个 `conflict: true` 的元素只带一个版本
  不是已解决的冲突；那是穿着分析外衣的静默裁决。编译器将其标记为
  `CONFLICT_SINGLE_VERSION`，而本门禁绝不能发布一个靠丢弃分歧版本
  来「解决」冲突的 IR。只有人可以裁决哪个版本胜出。

## 判定逻辑

| 判定              | 条件                                        | 后果                                  |
| ----------------- | ------------------------------------------- | ------------------------------------- |
| `PASS`            | 全部检查族零 finding。                      | IR 发布到 Traceability Graph。        |
| `PASS_WITH_REVIEW`| 仅软性 finding（如低置信度条目、降级来源）。| IR 发布，但附带人工评审清单。         |
| `REJECT`          | 任何结构性 finding（如字段缺失、冲突）。    | IR 被扣住。路由回编译步骤返工。       |

## 运行确定性检查器

```bash
python scripts/validate.py --ir path/to/testing_ir.json [--out report.json]
```

Exit codes: `0` PASS | `1` PASS_WITH_REVIEW | `2` REJECT | `3` invalid input.

## 本 skill 禁止事项

- **绝不修改 IR。** 校验器只做裁决。
- **绝不让未解决的冲突通过。** 悬空的 `conflict: true` 一律 REJECT。
- **绝不接受只保留一个版本的冲突。** 丢弃分歧版本是静默裁决，不是修复。
- **绝不把缺失的 source_trace 或置信度分数当作可接受。** 缺失的证据是
  finding，不是默认值。
- **绝不代人执行人工评审的路由。** 低置信度元素怎么处理由人工评审决定。
- **绝不接受未知 IR 版本。** v1.0 已冻结。

## 使用示例

**正确用法**
```text
User: IR 编译完成了，这是草稿。
Agent: 我将对这份 IR 运行 `ir-validator` 检查。schema 字段齐全、没有冲突、置信度有效。结果：PASS。可以安全发布。
```

**错误用法**
```text
User: 我们缺一些 source_trace 字段，帮我补上。
Agent: 我来运行 `ir-validator` 修复缺失字段。（错误：ir-validator 绝不能修改 IR，只能 REJECT 并退回上游编译）
```
