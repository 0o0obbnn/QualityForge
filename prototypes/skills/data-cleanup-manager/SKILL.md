---
name: data-cleanup-manager
description: 在 teardown 运行前后校验测试数据清理计划——数据链的第 3 阶段（需求、fixture DAG、清理）。草拟计划在运行前用一次，残余报告在运行后再用一次。检查清理顺序是否符合 LIFO（与构建顺序相反）、不删 Static 基线、失败被上报、残余被显式列出。不得执行 teardown。不得自动删除残余。不得用本 skill 编写清理计划。
---

# Data Cleanup Manager

构建搭起测试世界；清理把它拆掉。本 skill 校验 teardown 纪律，防止依赖
违例、Static 基线被破坏与脏状态。

## 核心检查（概览）

1. **REVERSE ORDER**：清理顺序必须是构建顺序的精确倒序（LIFO）。
2. **NO STATIC BASELINE**：Static 基线在测试间共享。它们绝不能出现在清理清单里。
3. **FAILURES REPORTED**：每个清理步骤必须有 status。失败/跳过必须带原因。
4. **RESIDUALS LISTED**：清理后的残余必须被显式枚举（即使为空）并附原因。

> **注**：详细算法（LIFO、Static 识别）与确切 JSON 格式，读 `references/cleanup_rules.md`。

## 集成

- **输入**：清理计划 JSON，含 `construction_order`、`cleanup_plan`、`static_baselines`、`results` 与 `residuals`。
- **输出**：一份通过校验的清理报告（`PASS` 或 `REJECT`）。
- **校验**：使用 `scripts/cleanup_check.py --cleanup <file.json>`。

## 本 skill 禁止事项

- **不得执行 teardown。** 本 skill 校验计划与结果。
- **不得自动删除残余。** 上报它们。由人类或快照恢复来决定。
- **不得跳过 Static 检查。** Static 规则是绝对的。
- **不得在存在未记录残余时报告完成。**

## 使用示例

**✅ 正确用法：**
```json
{
  "construction_order": ["USER_1", "ORDER_1"],
  "cleanup_plan": ["ORDER_1", "USER_1"],
  "static_baselines": ["VIP_TIER"],
  "results": [
    {"node_id": "ORDER_1", "status": "success"},
    {"node_id": "USER_1", "status": "success"}
  ],
  "residuals": []
}
```

**❌ 错误用法（依赖违例与被静默的失败）：**
```json
{
  "construction_order": ["USER_1", "ORDER_1"],
  "cleanup_plan": ["USER_1", "ORDER_1"],
  "static_baselines": ["VIP_TIER"],
  "results": [
    {"node_id": "USER_1", "status": "failed"}
  ]
}
```
