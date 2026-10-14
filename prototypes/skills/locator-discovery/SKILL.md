---
name: locator-discovery
description: UI locator 的稳定性门禁。在为某个元素提出候选 locator 之后、在它们进入 locator 库或任何自动化脚本之前使用。拒绝单一策略 locator、以基于序号的 XPath 为主策略，以及缺失或超出范围的稳定性分数；把低稳定性 locator 标记进 self-healing 监控。不得用本 skill 从活体 DOM 编写或发现 locator——它只校验候选。
---

# Locator Discovery (Stability Gate)

候选 locator 进入 locator 库之前要通过的门禁。它校验 locator；不从活体
DOM 发现它们。

## 本 skill 为何存在

测试脆弱性是 UI 自动化的头号杀手。脆弱的 locator（如 `//*[3]` 或
`/html/body/div[2]/div/span`）会在任何兄弟元素被添加或重排时失效。不稳定
最常见的根源，是依赖 DOM 层级而非语义属性。本 skill 强制一套稳定性层级，
确保测试能扛住轻微的 UI 变更。

## 稳定性策略排序

locator 必须按从最稳定到最不稳定排序：
1. `data-testid` —— 专为测试而生，高度稳定。
2. `id` —— 唯一时稳定。
3. `css` —— 比较稳定。
4. `aria-label` / 无障碍属性。
5. `xpath`（语义型）—— 基于路径而非序号时稳定。
6. `xpath`（序号型）—— **最脆弱；禁止作主策略**。

## Finding Codes 与路由

| Code | Severity | 含义 |
|---|---|---|
| `SINGLE_STRATEGY_LOCATOR` | REJECT | locator 策略少于 2 个。 |
| `INDEX_XPATH_PRIMARY` | REJECT | 主策略是基于序号的 XPath。 |
| `MISSING_STABILITY_SCORE` | REJECT | 缺少 stability_score。 |
| `INVALID_STABILITY_SCORE` | REJECT | 分数不在 [0,1] 内。 |
| `LOW_STABILITY` | REVIEW | 分数低于 0.6 阈值。 |

处置：
- **REJECT**：未通过严格检查的 locator 不得用于自动化脚本。
- **REVIEW**：分数 < 0.6 的 locator 被标记，交由 self-healing 步骤密切监控。

基于序号的 XPath 有两种检测方式：显式的 `index_based: true` 标志，或值本身
携带位置谓词（`//button[1]`、`tbody[2]`）。调用方无法靠省略标志绕过检查。

## 运行确定性检查器

```bash
python scripts/locator_check.py --locator path/to/locator.json [--out report.json]
```

Exit codes: `0` PASS | `1` REVIEW | `2` REJECT | `3` invalid input.

输入形状——strategies 是有序数组，最稳定的排最前；`strategies[0]` 即主策略：

```json
{
  "locator_id": "submit-btn",
  "strategies": [
    {"type": "data-testid", "value": "submit-btn"},
    {"type": "css", "value": "button.btn-primary"}
  ],
  "stability_score": 0.95
}
```

## 本 skill 禁止事项

- **绝不用基于序号的 XPath 作主 locator。** 任何兄弟元素被添加都会让它失效。
- **绝不返回只有一个策略的 locator。** 永远提供后备（如主策略 data-testid、后备 css）。
- **绝不随意赋予稳定性分数。** 分数必须遵循上面的排序规则。
- **绝不把缺失的稳定性分数当作高分。** 缺失分数是 `MISSING_STABILITY_SCORE`，不是隐式通过。

## 使用示例

**示例 1 —— 正确触发**
```
把提交按钮的候选 locator 加入库之前先校验一遍。
```
→ PASS：两个策略，主策略是 `data-testid`，分数 0.95 在范围内且高于阈值。

**示例 2 —— 错误触发（反模式）**
```
用 XPath 找容器里的第二个 span。
```
→ REJECT。（INDEX_XPATH_PRIMARY）基于序号的 XPath 禁止作主 locator。
