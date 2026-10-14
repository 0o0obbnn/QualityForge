---
name: performance-test-generator
description: 已草拟性能或负载测试脚本的契约门禁。在脚本草拟完成之后、运行之前使用，且每当性能阈值需要对照 Strategy Contract 做溯源核验时使用。拒绝针对 mock 依赖的断言、与功能测试共享命名空间的负载数据，以及凭空发明的阈值。不得用本 skill 编写脚本——它只审计已有脚本。功能 API 测试不得使用（改用 api-test-generator）。
---

# Performance Test Generator (Contract Gate)

草拟好的负载测试脚本在运行前要通过的门禁。它审计脚本；不合成脚本。

## 本 skill 为何存在

性能测试与功能测试有本质差异。生成一个脚本很容易，但生成一个*有效的*
负载测试需要严格的边界：
1. **mock 依赖对性能测试毫无意义**。被 mock 的依赖会即时响应（它是个桩）。对着 mock 断言 "payment gateway responds < 200ms" 测的是 mock 的响应时间，不是真实网关。结果就是虚假信心——真实网关在负载下可能要花 2 秒。
2. **数据隔离**。负载测试数据必须使用独立命名空间（如 `loadtest_*` 表前缀、独立 fixture 命名空间）。与功能测试共享意味着负载数据量拖垮功能测试速度，而功能测试的数据变更会污染负载测试基线。

## Finding Codes 与路由

| Code | Severity | 含义 |
|---|---|---|
| `MOCK_DEP_PERF_ASSERT` | REJECT | 对被 mock 的依赖做性能断言。 |
| `SHARED_DATA_NAMESPACE` | REJECT | 负载数据与功能命名空间共享。 |
| `THRESHOLD_NOT_FROM_STRATEGY` | REJECT | 阈值不来自 strategy contract。 |

处置：
- **REJECT**：强制重新生成或人工审查。不得运行脚本。

缺失本身就是 finding，不是通过。未声明 `namespace` 的脚本、或断言了性能
却没有 `thresholds[]` 的脚本，一律 REJECT——未声明的命名空间无法确认已
隔离，未说明的阈值就是一条无法溯源的 SLO。

## 阈值溯源

`thresholds[]` 中的每个条目都必须携带 `strategy_ref`，指向 Strategy
Contract 中的某个 gate。检查器把每个 ref 解析到契约的 `Quality_Gates[].gate_name` /
`.metric` 与 `performance_thresholds`。解析不到任何东西的 ref，或未提供
契约却声称有 ref，都是 `THRESHOLD_NOT_FROM_STRATEGY`——无法验证的声明
按未满足处理。

## 运行确定性检查器

```bash
python scripts/perf_check.py --script path/to/perf_script.json --strategy path/to/strategy.json [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input. 省略 `--strategy` 不会放宽门禁：此时阈值溯源无法核验，所有阈值一律拒绝。

## 本 skill 禁止事项

- **绝不对被 mock 的依赖做性能断言。**
- **绝不与功能测试共享数据命名空间。**
- **绝不发明性能阈值。** 所有阈值必须来自 strategy contract。

## 使用示例

**示例 1 —— 正确触发**
```
给 /checkout API 生成一个负载测试脚本。下游 payment gateway 用真实的
staging 实例。数据使用 loadtest_ 前缀。
```
→ 脚本生成成功。

**示例 2 —— 错误触发（反模式）**
```
给用户登录流程生成一个性能测试。DB 用内存 SQLite 数据库 mock。
```
→ REJECT。（MOCK_DEP_PERF_ASSERT）无法在 mock 的 DB 上验证性能。
