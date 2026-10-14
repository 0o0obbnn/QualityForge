---
name: strategy-planner
description: 在场景与用例设计之前校验已草拟的 Strategy Contract。在关键路径、范围、风险、质量门禁、测试金字塔与 mock 策略均已草拟后使用一次。拒绝静默的关键路径缺口、未绑定的范围与未量化的门禁。不得使用本 skill 生成关键路径——上游规划器必须显式枚举本项目自己的路径，且不预设任何普适路径集。
---

# Strategy Planner

这个只做裁决的门禁校验项目专属策略。它不假设每个产品都包含认证、
支付、权限或任何其他普适业务路径。上游规划器必须在 `Critical_Paths`
中显式枚举当前项目的关键路径。

## 契约

`Critical_Paths[]` 是承重的范围声明：

- `path_id`：唯一、非空的标识符。
- `disposition`：`IN_SCOPE` 或 `OUT_OF_SCOPE`。
- `IN_SCOPE` 路径通过非空 `feature_ids` 绑定到已声明的
  `In_Scope[].feature_id` 值。
- `OUT_OF_SCOPE` 路径携带非空 `exclusion_reason`。

检查器还要求：

- 非空 `In_Scope`，feature ID 唯一，风险取值于
  `{low, medium, high, critical}`；
- 所有 `Out_Of_Scope` 条目都有显式理由；
- 质量门禁非空且命名唯一，阈值是 [0,1] 内的有限非布尔数值；
- `unit`、`integration`、`e2e` 份额在 [0,1] 内，合计为
  `1.0 ± 0.001`；
- mock 策略结构有效，且核心数据/内部层不出现在 `mock_targets` 中。

倒金字塔是 REJECT。集成偏重的奖杯型是 REVIEW，因为它可能是有意为之。

运行：

```bash
python scripts/strategy_check.py --strategy path/to/strategy.json
```

## 禁止

- 不得自动添加项目范围或关键路径。
- 不得规定或调低质量阈值。
- 不得从通用关键词清单推断关键路径。
- 不得改写被拒绝的策略。

finding code 与示例见 `references/strategy_rules.md`。



## 本 skill 禁止事项

- **反模式**：绝不在 strategy 内捏造或重复定义 AI 置信度阈值。存在已批准的 CalibrationProfile 时引用它，且始终定义必要的测试环境。

## 使用示例

**正确**：对一份包含显式 `Critical_Paths` 的完整草拟策略运行 strategy planner。
**错误**：要求 strategy planner 为新项目猜测并定义关键路径。
