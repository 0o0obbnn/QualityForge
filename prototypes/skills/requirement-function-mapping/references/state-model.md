# 状态模型与组合门禁

四类状态描述不同层级，不得互相替代。

| 层级 | 字段 | 合法值 | 含义 |
|---|---|---|---|
| 图谱验收 | `audit.verdict` | `NOT_RUN / PARTIAL_PASS / PASS / FAIL` | 整份映射产物的业务验收结果 |
| 语义复核 | `audit.semantic_review.status` | `REVIEW_REQUIRED / COMPLETED` | 同名字段、跨上下文、候选与冲突是否完成语义复核 |
| 最小功能事实就绪度 | `atomic_functions[].generation_readiness.status` | `ready / review_required / blocked` | 最小功能事实是否足以进入评审或测试设计 |
| 测试维度门禁 | `quality_review.dimension_eligibility.*.status` | `READY / REVIEW_REQUIRED / BLOCKED / NOT_APPLICABLE` | 单个最小功能的某个测试维度是否可消费 |
| 校验器运行结果 | CLI `verdict` | `STRUCTURAL_PASS / PARTIAL_PASS / PASS / FAIL` | 本次校验命令的结果；`STRUCTURAL_PASS` 不写回图谱验收字段 |

## 不变量

1. `STRUCTURAL_PASS` 只表示结构合法，不代表语义完成或下游可用。
2. `audit.downstream_eligible=true` 要求：全量来源完成、`audit.verdict=PASS`、语义复核完成、无跳过/不可用/未覆盖来源。
3. 测试设计输入可在包级 `PARTIAL_PASS` 时消费局部 `READY` 维度，但必须声明 `READY_DIMENSIONS_ONLY`；这不提升原图谱的整体验收状态。
4. `BLOCKED` 表示已有证据证明当前不能生成；`REVIEW_REQUIRED` 表示信息尚待确认；`NOT_APPLICABLE` 表示该维度不适用。三者不得互换。
5. 发现草稿、候选、可选视觉观察和代表性提取均不得设置为正式下游可用。

## 流程语义

这些状态是交付范围和证据边界，不是整条流水线的停止开关。图谱或评审的包级 `downstream_eligible=false` 只表示不能宣称“整份需求已确认”，不得压制其中已经评审为 `READY` 的最小功能/测试维度。

正式流水线同时交付两类范围：

- **已确认范围**：编译为只含 `READY` 维度的 `test_design_input`，可立即生成正式测试用例。
- **待确认范围**：留在评审 Finding、解决队列和完整图谱中，不进入本次正式测试输入。

补充需求、项目资料或争议结论后，重新生成评审快照并投影图谱；新达到 `READY` 的切片追加生成用例，发生变化的已有切片按稳定 ID 失效并重新生成，未受影响切片保留。

## 关键合法组合

| 场景 | 图谱 verdict | 语义复核 | downstream | 维度门禁 |
|---|---|---|---|---|
| 发现草稿 | `FAIL` 或 `NOT_RUN` | `REVIEW_REQUIRED` | `false` | 尚未投影 |
| 结构通过、语义未完成 | 非 `PASS` | `REVIEW_REQUIRED` | `false` | 可有局部 READY，但不能声称全文已确认 |
| 全量图谱验收完成 | `PASS` | `COMPLETED` | `true` | 各适用维度仍按需求评审结果判断 |
| 测试设计局部切片 | `PARTIAL_PASS` | 继承来源投影 | `true` | 仅包含至少一个 READY 的条目 |
