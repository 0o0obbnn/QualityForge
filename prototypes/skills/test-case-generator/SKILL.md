---
name: test-case-generator
description: 从 requirement-function-mapping 产出的、已通过门禁的 test_design_input 生成可供人工评审和下游 AI 消费的测试用例。输出权威 Test Case IR JSON 与等价 CSV 人工视图；仅处理 READY 维度，保留需求、规则、字段、证据和图谱快照追踪。缺少 Oracle、来源证据或放行维度时阻断，不从原始需求文档直接生成，也不生成测试数据值、定位器、自动化代码、实际结果或 Allure 报告。
---

# Test Case Generator

把已确认的测试设计事实转换成测试意图，不重新解释原始需求。

## 输入与输出

输入必须是 `requirement-function-mapping` 输出的 `test_design_input 2.0`，且
`acceptance.downstream_eligible=true`。处理全量包时逐个 `items[]` 生成，但只允许
覆盖 `dimension_eligibility.*.status=READY` 的维度。

每次生成两个同步产物：

- `test_cases.json`：权威 Test Case IR，供测试数据、自动化和结果链路消费；
- `test_cases.csv`：从同一 JSON 确定性投影的人工评审/导入视图。

完整字段与边界见 `references/test-case-ir-contract.md`。模板见
`assets/test_case_ir_template.json`。

## 生成流程

1. 校验输入的图谱快照、来源哈希、验收状态和 READY 维度。
2. 逐个最小功能建立测试覆盖矩阵，至少覆盖每个 READY 维度和已放行规则。
3. 仅使用 `rule_registry`、`evidence_registry`、字段使用、关系和已确认流程生成用例。
4. 测试技术可以推导边界、等价类、判定表和状态转换，但标记为
   `TEST_DERIVATION`，不得把推导写成需求事实。
5. 每个步骤同时写动作和可判定预期结果。预期结果必须绑定
   `oracle_rule_ids` 或 `oracle_evidence_ids`。
6. 只声明固有执行语义和候选执行渠道；不判断当前自动化是否 READY。
7. 先执行确定性校验，再投影 CSV。REJECT 时不得发布任何正式用例。

运行：

```bash
python3 scripts/validate_case_ir.py \
  --cases test_cases.json \
  --input test_design_input.json \
  --out test_case_validation.json

python3 scripts/render_case_csv.py \
  --cases test_cases.json \
  --validation test_case_validation.json \
  --out test_cases.csv
```

旧版 `Testing IR + scenarios + cases` 仅由 `scripts/case_check.py` 兼容校验，
不得用于新产物。

## 职责边界

本 Skill 负责：测试目标、前置条件、原子步骤、逐步 Oracle、测试数据需求、
测试技术、优先级、固有执行语义和端到端 trace。

本 Skill 不负责：

- 具体测试数据值、账号、密码或环境准备；
- endpoint、定位器、自动化框架绑定或测试代码；
- API/UI 自动化可行性和当前就绪状态；
- 实际结果、截图、日志、Allure 调用、缺陷或测试报告；
- 为 `REVIEW_REQUIRED`、`BLOCKED`、`NOT_APPLICABLE` 维度生成正式用例。

## 验收标准

- JSON 通过 `validate_case_ir.py`，结论为 `PASS`；
- 每个用例只有一个最小功能来源，所有 trace ID 均存在于同一图谱快照；
- 每个 READY 维度至少被一个用例覆盖，未放行维度零覆盖；
- 每个步骤非空并有至少一个可判定 Oracle；
- 每个 Oracle 都有规则或证据来源，不含 `ASSUMPTION`；
- 测试数据只有需求描述和约束引用，不含伪造的具体值；
- CSV 由已通过校验的 JSON 生成，case 数量和 ID 完全一致；
- 输出明确记录未生成范围和原因，不把局部放行描述成全量完成。
