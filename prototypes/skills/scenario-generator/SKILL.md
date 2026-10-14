---
name: scenario-generator
description: 对照已发布的 Testing IR 与 Strategy Contract，校验已草拟的 Scenario Graph。在场景已草拟之后、用例生成之前使用。拒绝畸形场景、孤儿绑定、无效 facet、捏造迁移与未覆盖的 IR 迁移。不得使用本 skill 编写或修复场景——生成是本门禁所裁决的上游步骤。不得从原始 PRD 重新推导场景。
---

# Scenario Generator

生成是软性步骤；`scripts/scenario_check.py` 是只做裁决的契约门禁。
只从已发布的 IR 与 strategy 生成，绝不重新解读原始 PRD。

## 生成契约

每个场景有唯一的 `S-{module}-{NNN}` ID，并绑定到一个 IR
`req_id` 和 `rule_id`。它声明一个 facet：

- `normal`
- `abnormal`
- `boundary`
- `state_transition`
- `permission`

对每个 IR 迁移，至少生成一个 `state_transition` 场景，其
`transition_ref` 为 `sm_id:from->to`。

## 门禁语义

- 未知需求或规则：REJECT。
- 绑定、ID 或 facet 缺失/无效：REJECT。
- IR/场景容器或条目畸形：REJECT，不崩溃。
- IR 迁移无效或未覆盖：REJECT。
- 某个非 state facet 为空：REVIEW，因为它可能不适用。
- `'normal'` 占有效 facet 场景的比例超过 60%：REVIEW
  （`FACET_IMBALANCE`），happy-path 漂移需要解释。

运行：

```bash
python scripts/scenario_check.py --scenarios scenarios.json --ir testing_ir.json
```

## 禁止

- 不得捏造需求、规则或迁移。
- 不得靠给重复 happy path 改标签来凑 facet 数量。
- 不得自动修复被拒绝的图节点。

确切结构规则见 `references/scenario_contract.md`。



## 本 skill 禁止事项

- **反模式**：绝不同时生成测试多个正交特性的过于复杂场景。绝不忽略负向路径。

## 使用示例

**正确**：直接映射已发布 IR 中的 `req_id` 和 `rule_id` 生成场景。
**错误**：基于直接从 PRD 推断的未文档化行为生成场景。
