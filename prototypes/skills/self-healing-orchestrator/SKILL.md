---
name: self-healing-orchestrator
description: 判定一个失败测试是否允许自动修复的运行时决策门禁。在 failure-analyzer 把失败归类为易变 locator、过期 fixture 或瞬时环境问题之后使用。三条硬性护栏——关键路径失败绝不自动修复、每资产 7 天/3 次修复上限、断言期望值绝不静默修改。不得自动修复关键路径失败。不得用本 skill 做失败归类（改用 failure-analyzer）。
---

# Self-Healing Orchestrator

站在「测试失败了」与「系统自动修好了」之间的决策层。修复强大而危险；本 skill 是让它变安全的护栏。

## 三条硬性护栏

1. **关键路径绝不自动修复**：认证、支付、权限类失败直接路由到人工 review。
2. **7 天 / 3 次修复上限**：7 天内修复超过 3 次需要人工重构。
3. **断言期望值神圣不可侵犯**：绝不静默修改断言的期望值。

## 运行确定性门禁

```bash
python scripts/healing_gate.py --asset-id <id> --heal-type <locator|fixture|assertion|other> \
  --heals-7d <int> [--path-category critical|normal] [--touches-expected] [--confidence <float>]
```

Exit codes: `0` ALLOW | `2` DENY | `3` invalid input.

`--path-category` 默认为 `critical`，因此未指明路径时按 fail-closed 处理。`--heals-7d` **必填且无默认值**：本门禁没有修复历史存储，计数由调用方提供。若默认为 0，调用方就能靠省略该 flag 绕过修复上限，所以必须显式给出——确实没有历史修复时传 `0`。提供真实计数是调用方的责任；门禁无法核实它。

## 本 skill 禁止事项

- **反模式**：绝不未经 review 就把修复变更直接写入仓库。绝不暴力穷举 locator。

## 使用示例

**正确：**
- 允许对非关键组件的易变 locator 做一次自动修复，并记录一条审计事件。
- 拒绝一个试图修改价格断言期望文本的修复请求。

**错误：**
- 自动修复登录按钮的 locator 失败。
- 放任一个测试本周第 5 次自动修复而不告警。

## 集成

- **输入**：修复请求（asset_id、path、是否触碰断言、历史）
- **输出**：ALLOW（附抽查路由）或 DENY（强制人工 review）。

路径分类法、窗口/上限策略与审计格式，见 `references/healing_policy.md`。
