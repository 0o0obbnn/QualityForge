# NPRJ Test Case Generator 验证报告

## 结论

`test-case-generator` 对当前 NPRJ `test_design_input 2.0` 的**全部 READY 范围**验证通过。
这不等于 NPRJ 需求全文测试用例已经完成：上游 117 个最小功能中只有 2 个最小功能、
4 个测试维度获准进入正式测试用例设计。

## 验证输入

- 输入：`requirement-function-mapping/tests/outputs/nprj_test_design_input_after_batch_001_v2.json`
- 输入哈希：`370e2a34c747cb09b2b116af9fbb9d95d953dac7c224f4f143d61f1cd2fae370`
- 图谱快照：`GRAPH-1BDF14613A91`
- 输入最小功能：117
- 含 READY 维度的最小功能：2
- 无 READY 维度的最小功能：115
- READY 维度：4
- REVIEW_REQUIRED：169
- BLOCKED：162
- NOT_APPLICABLE：484

## 正式生成范围

| 最小功能 | READY 维度 | 正式用例 |
|---|---|---|
| 检索次数管理（管理侧）/签约机构/重置 | functional、field_validation | `TC-AFBFB669ACE883-001` |
| 结算管理/数据调用量系数（Y）/查询 | field_validation | `TC-AF6AE6490F9A3C-001`、`TC-AF6AE6490F9A3C-002` |
| 结算管理/数据调用量系数（Y）/查询 | sorting | `TC-AF6AE6490F9A3C-003` |

未放行维度没有生成正式用例。查询功能本身为 `REVIEW_REQUIRED`，权限维度为
`BLOCKED`，均只保留在排除清单中。

## 产物核对

- Test Case IR：4 条用例
- CSV：4 行，19 列
- JSON/CSV 用例 ID：完全一致
- 测试数据需求：14 条，只描述需求和约束，不包含具体值
- 逐步 Oracle：11 条
- READY 范围应覆盖规则：13 条
- 被 Oracle 覆盖规则：13 条
- 缺失规则：0
- 校验结论：`PASS`
- 校验 finding：0

语义复核覆盖：重置清空与默认未选、月份选择器、会员职务选项、机构名称省略与悬浮、
18 位法人标识代码、月份格式、创建/更新时间格式及初始空值、会员职务展示集合、
系数初始空值与每日汇总后的对应关系、月份/创建时间/更新时间复合倒序。

## 负向与回归验证

标准库单元测试 10/10 通过，覆盖：

1. 真实 NPRJ 切片通过；
2. 全部 READY 范围完整通过；
3. 遗漏任一 READY 条目时拒绝；
4. 覆盖 BLOCKED 权限维度时拒绝；
5. READY 规则没有 Oracle 时拒绝；
6. 跨最小功能数据需求时拒绝；
7. 混入 locator 等运行时绑定时拒绝；
8. 上游输入哈希漂移时拒绝；
9. JSON/CSV 身份一致；
10. JSON 校验后被修改时拒绝生成 CSV。

旧版 `case_check.py` 兼容回归为 `PASS`；Skill 结构校验为 `Skill is valid!`；
全部 Python 脚本通过编译检查。

## 验收边界

本次可以确认：Skill 能从当前全部已放行事实生成可审计 Test Case IR 和 CSV，且门禁能
阻止越过上游状态、丢失规则 Oracle、来源漂移及运行时污染。

本次不能确认：115 个无 READY 维度的最小功能尚不能生成正式用例；具体测试数据值、
API/UI 自动化绑定和实际执行结果属于后续 Skill，当前用例中的候选执行渠道不代表自动化
已经 READY。

