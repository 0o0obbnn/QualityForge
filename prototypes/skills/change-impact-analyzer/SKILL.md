---
name: change-impact-analyzer
description: 分析一次代码或契约变更的波及面，产出受影响资产清单。当 diff 或契约变更落地、需要知道它牵动哪些测试、用例与规则时使用。沿可追溯图至少走 2 跳，并归类每一处影响。做纯静态分析而不标记置信度降级时不得使用。不得用本 skill 挑选要重跑哪些测试——该选择由 regression-planner 审计，它消费本清单。
---

# Change Impact Analyzer

沿可追溯图行走，回答「这次变更会弄坏什么」。

## 本 skill 为何存在

1. **纯静态分析。** 只读代码分析 diff，没有图上下文，漏掉间接影响。
2. **静默降级。** 图缺失时，分析器悄悄回退到纯静态。

本分析器把图传播设为默认，并让降级显式化。

## 传播模型

```
changed nodes
       │
       ▼  walk graph edges, 2-hop minimum
   ┌───────────────────────────────────────┐
   │  hop 1: DIRECT dependents             │
   │  hop 2+: INDIRECT transitive deps     │
   └───────────────────────────────────────┘
       │
       ▼
   Impact Report
```

## verdict 与 finding code

| Code | 严重级别 | 含义 |
|---|---|---|
| `SHALLOW_PROPAGATION` | REJECT | `max_depth_reached` < 2；间接影响未被捕获。 |
| `UNCLASSIFIED_IMPACT` | REJECT | 某个受影响资产没有 `direct`/`indirect` 归类。 |
| `SILENT_STATIC_FALLBACK` | REJECT | 用了静态回退，或图不可用，且未设置 `degraded_confidence_flagged`。 |
| `GRAPH_AVAILABILITY_UNDECLARED` | REJECT | `graph_available` 缺失；遍历完整性无法确认。 |

输出：`PASS`（交给回归选择）或 `REJECT`（重跑分析）。

`graph_available` 必须显式声明。它**没有宽松默认值**：否则一份从未碰过图的报告会被读作一次健康的全图遍历，而这正是本 skill 要抓的静默降级。缺少图访问的证据，按没有图访问处理。

## 运行确定性检查器

```bash
python scripts/impact_check.py --report path/to/impact_report.json [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input.

## 本 skill 禁止事项

- **绝不假设未分析的组件是安全的。** 没有分析不等于没有影响。
- **绝不止步于一跳。** 传递依赖才是重点；2 跳是下限，不是目标。
- **绝不静默降级。** 图缺失而使用静态回退时，必须设置 `degraded_confidence_flagged`——一次未标记的降级运行就是 REJECT。

## 使用示例

**正确：**
```json
{
  "max_depth_reached": 2,
  "graph_available": true,
  "used_static_fallback": false,
  "impacted_assets": [{"asset_id": "api-1", "impact_class": "direct"}]
}
```

**错误（浅层传播）：**
```json
{
  "max_depth_reached": 1,
  "impacted_assets": [{"asset_id": "api-1", "impact_class": "direct"}]
}
```

完整规则与 finding code 见 `references/impact_rules.md`。
