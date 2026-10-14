# Scenario 契约参考

`scripts/scenario_check.py` 是可执行行为的权威。

## 绑定与标识符

- ID：`S-{alphanumeric_or_underscore_module}-{NNN}`。
- `req_id` 存在于 `IR.requirements`。
- `rule_id` 存在于 `IR.business_rules`。
- ID 在图内唯一。

缺失绑定是 `ORPHAN_SCENARIO`；未知绑定是 `REQUIREMENT_NOT_IN_IR` 或 `RULE_NOT_IN_IR`。全部 REJECT。空图是 `EMPTY_SCENARIO_SET` REJECT。

## Facet 与迁移覆盖

合法的 facet 为 `normal`、`abnormal`、`boundary`、`state_transition` 和 `permission`。状态迁移引用使用 `sm_id:from->to`，且必须存在于 IR。每个结构合法的 IR 迁移都必须被覆盖。

| Finding | Severity | 含义 |
|---|---|---|
| `INVALID_TRANSITION_REF` | REJECT | scenario 引用了不存在的迁移。 |
| `TRANSITION_UNCOVERED` | REJECT | IR 迁移没有对应 scenario。 |
| `EMPTY_FACET` | REVIEW | 非状态 facet 没有 scenario；是否适用需要判断。 |
| `FACET_IMBALANCE` | REVIEW | 'normal' 占合法 facet scenario 的比例超过 60%；面向缺陷的 facet 代表性不足。 |

IR 迁移端点格式错误时产生 `INVALID_IR_TRANSITION`，而不是被字符串拼接成假迁移键。格式错误的根、集合与条目同样变成显式 REJECT finding。

检查器校验的是结构覆盖，不校验标题、边界值或权限选择的语义质量。
