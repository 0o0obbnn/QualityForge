---
name: state-machine-builder
description: 在 Testing IR 融合前校验已抽取的实体生命周期状态机。在状态与迁移已抽取之后、对该 packet 使用。检查 guard 已标注、实体绑定、显式初始状态、无捏造状态、迁移完整、可达性。不得推断初始状态或猜测缺失的迁移 guard。不得使用本 skill 编写状态机。实体本身改用 domain-model-extractor。
---

# State Machine Builder

状态机编码实体的生命周期迁移。本 skill 检查抽取出的状态机在融合前
是完整且已绑定的。

## 状态机检查

| 检查项           | Code                                                        | 拦截什么                                |
| ---------------- | ----------------------------------------------------------- | --------------------------------------- |
| guard 显式标注   | `MISSING_GUARD`                                             | 迁移完全没有 guard 字段。               |
| 绑定到实体       | `UNBOUND_STATE_MACHINE`                                     | 状态机没有 entity_id。                  |
| 上下文非空       | `EMPTY_STATE_SET` / `EMPTY_ENTITY_SET`                      | 空状态或空实体会绕过校验。              |
| 显式初始状态     | `MISSING_INITIAL_STATE` / `INITIAL_STATE_NOT_DECLARED`      | 入口状态缺失或无效。                    |
| 无捏造状态       | `STATE_NOT_IN_DECLARED_SET`                                 | 迁移引用了不在 `states[]` 中的状态。    |
| 迁移完整且唯一   | `MISSING_TRANSITION_ENDPOINT` / `DUPLICATE_TRANSITION`      | 边不完整或重复。                        |
| 可达性           | `UNREACHABLE_STATE`                                         | 某状态从 `initial_state` 没有路径可达。 |

初始状态是承重的，必须声明；绝不从无序集合或迁移形状推断。guard
规则同样严格：`guard: null` 合法（表示「无 guard 条件」），但字段
缺失不合法——那说明抽取器忘了考虑是否适用 guard。该检查强制的是
显式标注，而非 guard 的值。

## 集成

- **输入**：抽取出的状态机草稿 + 实体列表（用于绑定检查）。
- **输出**：已校验的状态机，或 REJECT。



## 运行确定性检查器

```bash
python scripts/sm_check.py --packet path/to/state_machines.json [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input.

## 本 skill 禁止事项

- **反模式**：绝不创建孤立（无连接）状态。绝不允许未定义的迁移。

## 使用示例

**正确用法：**
拒绝一个在某条迁移上完全省略 `guard` 键的状态机。

**错误用法：**
因为无序 `states` 数组里名为 "Draft" 的状态排在第一，就推断它是 `initial_state`。

guard 标注规则与实体绑定要求见 `references/state_machine_rules.md`。
