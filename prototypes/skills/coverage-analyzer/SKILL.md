---
name: coverage-analyzer
description: 基于 Gate 0 产物计算四个可追溯覆盖维度（rule、scenario、state-transition、verified-assertion），并产出阶段门禁 verdict。当阶段出口或质量决策需要覆盖数字时使用。只用有效覆盖（effective coverage），绝不用原始行覆盖。不得把原始行覆盖当作门禁信号上报。不得把被 REJECT 的断言计入分子——它留在分母中，并迫使该维度 FAIL。不得用本 skill 搭建面向干系人的仪表盘（改用 quality-governance）。
---

# Coverage Analyzer

把「我们写了测试」变成「我们清楚什么真的被验证、什么没有」的审计层。其他每个 skill 都在生产资产；本 skill 度量这些资产是否真的叠加成对 IR 的覆盖。

## 本 skill 为何存在

本 skill 要消灭两种失败模式：

1. **靠计数制造覆盖通胀。** 「我们有 200 个测试用例」不是覆盖。200 个用例全在测同一条 happy path、留下 40 条规则无人测试，是披着大数字外衣的近似零覆盖。
2. **抹除失败的验证。** Assertion Verifier 会 REJECT 未通过变异门禁的断言。被 REJECT 的断言**对分子贡献为零、但留在分母中**，并迫使断言维度 FAIL。

分析器的职责是产出流水线信任的那一个数字，并在数字低于 Strategy Contract 阈值时让门禁 FAIL。

## 设计不变量：被 REJECT 的断言留在分母

这是本 skill 的承重规则。被 REJECT 的断言是一次*已确认*的验证失败——把它从分母中移除，等于靠删除已知问题的证据来抬高覆盖分数。这是伪造门禁通过的最省事手段。

| 断言 verdict | 分子 | 分母 |
|---|---|---|
| `PASS` | ✅ 计入 | ✅ 计入 |
| `REPAIR` | ✗ | ✅ 计入（存在，尚未验证） |
| `REJECT` | ✗ | ✅ 计入**并迫使维度 FAIL** |
| 缺失 / 未知 | ✗ | ✅ 计为未验证 |

分母为零的维度是一次物化失败，不是 100% 覆盖。只有经过 review 的 Strategy 声明写入 `not_applicable_dimensions`，才能把空维度标记为 `NOT_APPLICABLE`。完整演算见 `references/coverage_rules.md`。

## 四个覆盖维度

覆盖不是一个数字——是四个，各自度量一个不同的失败面：

- **维度 1：RULE 覆盖** —— 全部 IR 规则中，有多少拥有 ≥1 个绑定的用例？
- **维度 2：SCENARIO 覆盖** —— 全部生成的场景中，有多少拥有 ≥1 个用例？
- **维度 3：STATE 覆盖** —— 全部状态机迁移中，有多少被行使到？
- **维度 4：ASSERTION 覆盖** —— 全部断言中，有多大比例通过了 assertion-verification 步骤？

> **注意**：各维度的详细规则、计算与机制，见 `references/coverage_rules.md`。

## 本 skill 禁止事项

- **绝不把原始行覆盖当作门禁信号上报。** 行覆盖至多是一个信息性辅助指标。
- **绝不把被 REJECT 的断言移出分母。** 它对分子贡献为零并阻断断言门禁；丢弃它就是隐藏一次已确认的验证失败。
- **绝不把分母为零的维度当作 100% 覆盖。** 空维度是一次物化失败，除非 Strategy Contract 声明其为 `not_applicable`。
- **绝不为让 FAIL 的门禁变绿而悄悄修改 Strategy Contract。** 降范围（descoping）是经 review 路由的人类决策。

## 运行确定性检查器

覆盖演算由脚本强制执行，绝不在散文中重新推导：

```bash
python scripts/coverage.py --snapshot path/to/snapshot.json --strategy path/to/strategy.json [--out report.json]
```

Exit codes: `0` GATE_PASS | `2` GATE_FAILURE | `3` invalid input.

## 使用示例

### ✅ 正确用法
```
User: 请计算用户认证模块当前的覆盖率。
Assistant:
1. 已查阅 `references/coverage_rules.md`。
2. 分析 4 个维度：Rule（85%）、Scenario（90%）、State（100%）、Assertion（80%）。
3. 所有阈值均为 85%。断言覆盖 80%（未达标）。
4. 因断言覆盖过低，发出 GATE_FAILURE。
```

### ❌ 错误用法
```
User: 请计算用户认证模块当前的覆盖率。
Assistant:
1. 运行了行覆盖工具（如 Istanbul 或 Coverage.py）。
2. 行覆盖为 95%。
3. 因 95% > 85%，发出 GATE_PASS。
（错误：用了原始行覆盖，而不是 4 个维度上的有效可追溯覆盖。不得把行覆盖用于阶段门禁。）
```
