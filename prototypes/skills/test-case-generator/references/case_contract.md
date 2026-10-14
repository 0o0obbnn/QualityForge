# 旧版测试用例校验契约

本文件只描述 `Testing IR + Scenario Graph` 兼容入口。新生成链路的权威契约见
`test-case-ir-contract.md`。

`scripts/case_check.py` 是可执行行为的权威。

## Trace 契约

`req_id`、`rule_id` 和 `scenario_id` 必填。需求和规则必须存在于 IR；scenario 必须存在于所供图。用例的需求/规则对必须与绑定的 scenario 匹配，否则 `CASE_SCENARIO_BINDING_MISMATCH` REJECT。

## 执行与 oracle 契约

| Finding | Severity | 含义 |
|---|---|---|
| `EMPTY_CASE_STEPS` | REJECT | 不存在可执行步骤。 |
| `INVALID_CASE_STEP` | REJECT | 步骤不是对象或缺少 action。 |
| `STEP_ENDPOINT_NOT_IN_IR` | REJECT | 步骤调用了未声明的端点。 |
| `EMPTY_EXPECTED_RESULTS` | REJECT | 不存在 oracle。 |
| `INVALID_EXPECTED_RESULT` | REJECT | oracle 条目不是非空对象。 |
| `EXPECTED_STATE_INVALID` | REJECT | 状态形状非法，或不在已解析的状态机中。 |
| `STATE_MACHINE_NOT_IN_IR` | REJECT | 显式机器绑定未知。 |
| `STATE_CHECK_INDETERMINATE` | REVIEW | 状态存在但无法解析出状态机。 |
| `EXPECTED_ENDPOINT_NOT_IN_IR` | REJECT | 期望交互不在 IR 中。 |

Fixture 类别为 `Static`、`Dynamic` 和 `Hybrid`。缺失或未知类别是 REJECT。空批次是 `EMPTY_CASE_SET` REJECT，批次内重复 ID 同样拒绝。

## 覆盖族（2026-08-27）

结构检查抓格式错误的用例；覆盖族抓另一种静默失败——格式完好、测试面却小于其所生成自的契约面的套件。

| Finding | Severity | 含义 |
|---|---|---|
| `CONTRACT_UNCOVERED` | REJECT | 某 IR 接口契约没有任何用例步骤触达。不带 `method` 的步骤视为覆盖其端点的所有已声明方法。 |
| `WEAK_ASSERTION` | REVIEW | `assertion` 措辞含糊（错误码式字眼、"类/大约/roughly"）或纯否定（`code != 200` 且无所断言）。 |
| `BOUNDARY_CONSTRAINT_UNCOVERED` | REVIEW | 边界性质的 IR 约束未被任何用例的 `constraint_refs` 引用。 |

`constraint_refs` 是可选的用例级 IR 约束 ID 数组；用例靠它声明自己触达了某个边界约束。

检查器证明的是结构可追溯、执行/oracle 存在、契约面覆盖。它不证明合法的期望状态就是语义上正确的状态；oracle 真伪仍由断言验证负责。
