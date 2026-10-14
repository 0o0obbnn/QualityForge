# Test Case IR 1.0 契约

Test Case IR 是测试意图的权威工件。CSV、测试数据、自动化代码和 Allure 元数据
都是它的下游投影或绑定，不得反向成为事实来源。

## 来源与范围

- 唯一正式输入是 `test_design_input 2.0`。
- `source_artifacts.graph_snapshot_id` 必须与输入一致。
- `generation_scope.mode=FULL_READY_SCOPE` 时，所选条目必须恰好等于输入中全部含 READY 维度的条目；`SELECTED_SLICE` 只证明所选切片。
- 每个用例绑定一个 `test_design_item_id` 和一个 `atomic_id`。
- `covered_dimensions` 只能包含该条目状态为 `READY` 的维度。
- `generation_scope.excluded_dimensions` 必须保留未生成维度及上游原因。

## 测试用例

用例必须表达单一测试意图。`steps[]` 按 `step_no` 从 1 连续编号；每一步包含：

- 可观察的业务动作 `action`；
- 业务目标 `target`，不得填 CSS/XPath、URL 或框架定位器；
- 所使用的数据需求引用；
- 一个或多个与该动作对应的预期结果。

预期结果不是操作说明。每个预期结果必须：

- 描述可观察状态、字段、响应、展示或业务结果；
- 至少绑定一个 `oracle_rule_ids` 或 `oracle_evidence_ids`；
- 明确 `machine_checkable`，但不据此声称自动化已经就绪。

## 测试数据边界

`data_requirements[]` 通过 `test_design_item_id` 绑定唯一最小功能，只描述业务数据需求、取值类别、用途和约束来源。例如
“机构名称使用一个合法代表值”。具体值、创建方式、账号、清理动作和敏感数据由
`test-data-generator` 产生的 Data Packet 管理。

允许的 `value_class`：

- `VALID`、`INVALID`、`BOUNDARY`：来自明确字段规则或测试技术；
- `STATE_SETUP`：为状态前置准备数据；
- `REPRESENTATIVE`：不声称业务边界的普通代表值。

测试技术推导必须标记 `TEST_DERIVATION`，且不得创造新的业务规则。

## 执行语义

`execution.semantics` 只描述 Oracle 的固有性质：

- `DETERMINISTIC`：所有关键 Oracle 都能按明确规则判定；
- `HUMAN_JUDGMENT`：关键 Oracle 依赖人工视觉、体验或主观判断；
- `MIXED`：两者同时存在。

`candidate_channels` 只表示可能渠道：`MANUAL`、`API_AUTOMATION`、
`UI_AUTOMATION`。API/UI Skill 结合接口、定位器、环境和数据绑定后，另行判断
`ELIGIBLE / BLOCKED / READY / NOT_APPLICABLE`。

## CSV 投影

CSV 是一行一个用例的人工视图，包含：

`case_id,module,function_name,minimum_function,title,objective,priority,test_level,`
`test_techniques,covered_dimensions,execution_semantics,candidate_channels,`
`fixture_category,preconditions,test_steps,expected_results,data_requirements,`
`traceability,case_status`

多值使用换行分隔；步骤和预期结果保留稳定编号。CSV 不作为下游自动化的权威输入。

## 禁止字段

正式 Test Case IR 不得包含运行时事实或实现绑定，包括：

`actual_result`、`execution_result`、`pass_fail`、`allure`、`screenshot`、
`log_path`、`base_url`、`endpoint`、`locator`、`xpath`、`css_selector`、
`username`、`password`、`token`、`secret`。

## 发布门禁

只有满足以下条件时 `acceptance.publishable=true`：

1. 所有 trace 引用存在且属于同一快照；
2. 所有正式用例仅覆盖 READY 维度；
3. 每个 READY 维度至少有一个用例；
4. 每一步都有来源充分的 Oracle；
5. READY 范围内的每条功能、字段和排序规则都至少被一个 Oracle 覆盖；
6. 数据需求引用完整且没有具体敏感值；
7. 没有 `ASSUMPTION`；
8. 结构校验结论为 PASS。
