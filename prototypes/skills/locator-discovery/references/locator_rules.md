# Locator 库规则

`scripts/locator_check.py` 是可执行编码；本文件描述其意图。

## Finding Codes

| Code | Severity | 含义 |
|---|---|---|
| `SINGLE_STRATEGY_LOCATOR` | REJECT | locator 的策略数 <2。 |
| `INDEX_XPATH_PRIMARY` | REJECT | 主策略是索引型 XPath。 |
| `MISSING_STABILITY_SCORE` | REJECT | 缺少 stability_score。 |
| `INVALID_STABILITY_SCORE` | REJECT | 分值不在 [0,1] 内。 |
| `LOW_STABILITY` | REVIEW | 分值低于 0.6 阈值。 |

## 策略排序（从最稳到最脆）

1. `data-testid` — 专为测试而生，稳定。
2. `id` — 唯一时稳定。
3. `css` — 较为稳定。
4. `aria-label` / 可访问性属性。
5. `xpath`（语义型）— 基于路径而非索引时稳定。
6. `xpath`（索引型）— **最脆弱；禁止作为主策略**。

索引型 XPath（`//*[3]`、`tbody[2]`）在任何兄弟节点新增或重排时都会失效。它是 UI 测试脆弱性的头号来源。

## 稳定性阈值

0.6 是默认 REVIEW 阈值。低于该分值的 locator 会被标记并交由 self-healing 步骤密切监控——它们在 DOM 变化时最可能需要修复。
