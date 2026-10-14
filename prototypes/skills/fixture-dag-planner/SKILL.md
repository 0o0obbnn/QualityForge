---
name: fixture-dag-planner
description: 校验已草拟的测试 fixture 依赖图——数据链（需求、fixture DAG、清理）的第 2 阶段。在 DAG 已草拟之后、fixture 构建运行之前使用。用 Kahn 算法检查无环性、teardown 存在性、依赖可解析性与 scope/type 有效性；PASS 时返回拓扑构建顺序。不得生成字段值。不得执行 DAG。不得使用本 skill 编写该图。
---

# Fixture DAG Planner

把「这个测试需要哪些实体」变成「它们必须按什么顺序构建、各自如何
清理」。输出是一张有向无环图，由下游构建按拓扑顺序执行。

## 本 skill 检查什么

1. **无环**：拓扑排序成功；无反向边。
2. **可逆**：每个带 `creates` 的节点声明非空 `teardown`。
3. **依赖存在**：每个 `depends_on` 引用都解析到某个 `node_id`。
4. **Scope/Type 有效**：Scope 取值于 `{session, module, function}`，type 取值于 `{Static, Dynamic, Hybrid}`。

算法细节、teardown 语义与基线版本规则见 `references/dag_rules.md`。



## 运行确定性检查器

```bash
python scripts/dag_check.py --dag path/to/dag.json [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input. 无环性用 Kahn
算法计算；PASS 时报告携带 `topological_order`。

## 本 skill 禁止事项

- **反模式**：绝不允许 fixture DAG 中出现循环依赖。绝不对相互独立的 fixture 强制串行执行。

## 使用示例

**正确用法**：
- 从数据需求出发规划一张 DAG。
- 确保所有创建的资源都显式声明 teardown 属性。
- 在执行测试准备前确认输出已按拓扑排序。

**错误用法**：
- 不得使用本 skill 生成字段值（例如测试邮箱地址）。那是数据生成步骤的职责。
- 不得使用本 skill 执行 DAG 或搭建测试环境（本 skill 只做规划/校验）。
- 不得靠删边静默消除环。检测到环时应上报，由人来修设计。

## 数据结构示例

```json
{
  "dag_id": "example-001",
  "nodes": [
    {
      "node_id": "node_A",
      "creates": "db_connection",
      "depends_on": [],
      "teardown": "db_connection.close()",
      "scope": "session",
      "type": "Static"
    }
  ],
  "baseline_refs": []
}
```
