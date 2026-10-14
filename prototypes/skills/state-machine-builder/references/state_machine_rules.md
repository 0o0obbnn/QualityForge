# 状态机抽取规则

## Finding Codes

| Code | Severity | 含义 |
|---|---|---|
| `MISSING_GUARD` | REJECT | 迁移缺少 'guard' 键。 |
| `UNBOUND_STATE_MACHINE` | REJECT | 状态机没有 entity_id 或其非法。 |
| `EMPTY_ENTITY_SET` | REJECT | 已知实体为空，绑定无法检查。 |
| `EMPTY_STATE_SET` | REJECT | states[] 为空。 |
| `MISSING_INITIAL_STATE` | REJECT | 缺少 initial_state。 |
| `INITIAL_STATE_NOT_DECLARED` | REJECT | initial_state 不在 states[] 中。 |
| `STATE_NOT_IN_DECLARED_SET` | REJECT | 迁移引用了未声明的状态。 |
| `MISSING_TRANSITION_ENDPOINT` | REJECT | 迁移缺少 from 或 to。 |
| `DUPLICATE_TRANSITION` | REJECT | 相同 from/to/guard 的边重复。 |
| `UNREACHABLE_STATE` | REJECT | 从 initial_state 出发不存在可达路径。 |

## guard 标注规则

`guard: null` 合法（无守卫条件）。但 `guard` 键 ABSENT 不合法——那意味着抽取器忘了考虑是否存在守卫。该检查强制显式标注：没有守卫，就明说。

## 实体绑定

每个状态机 MUST 绑定 entity_id。未绑定的状态机无法与它所治理生命周期的实体交叉引用。

## 初始状态与可达性

`initial_state` 必填，且必须出现在 `states[]` 中。可达性只从这个显式状态起算。绝不从集合迭代顺序推断，也不为循环状态机悄悄选定入口。
