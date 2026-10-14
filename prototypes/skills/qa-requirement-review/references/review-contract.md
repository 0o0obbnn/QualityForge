# 需求质量评审契约 1.0

## 顶层结构

```text
meta
review_id
source_ids[]
sources[]
source_units[]
source_unit_dispositions[]
requirements[]
assessments[]
requirement_assessments[]
findings[]
test_points[]
coverage
audit
```

`review_id / source_ids / assessments / findings` 与 `requirement-quality-gate` 的输入保持兼容；其余字段补足全量评审、逐需求追踪和下游测试设计需要的信息。

## 元数据与状态

```json
{
  "meta": {
    "schema_version": "1.0",
    "artifact_kind": "requirement_quality_review",
    "review_mode": "full",
    "lifecycle_status": "DRAFT",
    "generated_at": "2026-09-06T12:00:00+08:00"
  },
  "review_id": "RQR-<稳定摘要>",
  "source_ids": ["SRC-<稳定摘要>"]
}
```

`lifecycle_status` 只允许 `DRAFT / REVIEW_REQUIRED / BLOCKED / ACCEPTED`。快速扫描不能是 `ACCEPTED`。

## 来源与来源单元

```json
{"source_id":"SRC-<稳定摘要>","file":"需求.md","type":"requirement","version":"unknown","sha256":"<64位摘要>","authority":1}
```

```json
{"unit_id":"UNIT-<稳定摘要>","source_id":"SRC-<稳定摘要>","kind":"section","locator":"3.2.1 / L120-L148","relevant":true,"status":"processed","reason":null}
```

`status` 只允许 `processed / review_required / skipped / unavailable`。`review_required` 表示内容已摄取但尚未完成语义评审，`unavailable` 表示内容本身不可获得；两者都阻止完整通过，但不能混为一类。

每个 relevant 来源单元还必须在 `source_unit_dispositions[]` 中恰好出现一次：

```json
{"unit_id":"UNIT-...","disposition":"requirement","requirement_ids":["REQ-..."],"finding_ids":[],"reason":"已映射到需求"}
```

`disposition` 只允许 `requirement / finding / no_output / unavailable / review_required`。完整验收不允许保留 `unavailable` 或 `review_required`；`no_output` 也必须给出已经人工复核的理由。

## 需求条目

```json
{
  "requirement_id":"REQ-<稳定摘要>",
  "title":"提交申请",
  "summary":"用户提交满足校验规则的申请",
  "function_refs":["FUN-..."],
  "atomic_refs":["AF-..."],
  "field_refs":["FLD-..."],
  "rule_refs":[],
  "source_refs":[{"source_id":"SRC-...","locator":"3.2.1","quote":"点击提交后保存申请"}]
}
```

核心实体 ID 基于规范化语义和来源路径生成；行号变化不得单独导致 ID 改变。

## 总体与逐需求评估

总体 `assessments` 必须恰好覆盖 `ambiguity / consistency / testability / completeness / nfr_measurability / role_permission`，并保持现有质量门兼容：

```json
{"dimension":"testability","status":"FINDING","rationale":"存在未定义的预期结果","finding_ids":["RQF-..."]}
```

`requirement_assessments` 增加 `assessment_id` 和 `requirement_id`，对每个需求分别覆盖六个维度。状态只允许 `CLEAR / FINDING / NOT_APPLICABLE / NOT_REVIEWED`。`CLEAR / NOT_APPLICABLE` 必须带非空 `source_refs`，证明执行模型或人工实际检查过对应来源；`FINDING` 通过绑定 finding 的证据追踪来源。`NOT_REVIEWED` 不得由脚本依据零命中自动转成其他状态。

## Finding 与证据类型

```json
{
  "finding_id":"RQF-<稳定摘要>",
  "lifecycle_status":"OPEN",
  "code":"UNTESTABLE_ACCEPTANCE_CRITERIA",
  "severity":"REJECT",
  "certainty":"confirmed",
  "evidence_type":"ABSENCE",
  "requirement_ids":["REQ-..."],
  "function_ids":["FUN-..."],
  "atomic_ids":["AF-..."],
  "affected_test_dimensions":["functional"],
  "source_refs":["SRC-...#3.2.1"],
  "evidence":"在已检查范围内没有找到失败后的可观察结果",
  "inspected_scope":["3.2.1","表4"],
  "expected_element":"失败结果或错误提示",
  "question":"校验失败时系统应返回什么结果？",
  "recommendation":"补充错误码、提示语和数据是否保留。"
}
```

`lifecycle_status` 允许 `OPEN / RESOLVED / WITHDRAWN / ACCEPTED_RISK`，缺省按 `OPEN` 处理。只有 `RESOLVED / WITHDRAWN` 不参与下游阻断；`ACCEPTED_RISK` 仍不是已确认需求事实。解决 finding 时必须记录解决依据和新的 `source_refs`，并同步更新对应逐需求评估，不能只改状态。

`severity` 只允许 `REJECT / REVIEW`。证据类型：`QUOTE / ABSENCE / CONFLICT`。ABSENCE 必须有 `inspected_scope` 和 `expected_element`；CONFLICT 必须至少有两个不同的 `source_refs`。
资料依赖问题使用 `MISSING_REFERENCED_ARTIFACT / MISSING_EXISTING_BASELINE / PENDING_REQUIRED_ARTIFACT / UNRESOLVED_INTERNAL_REFERENCE`，以 [资料依赖评审契约](source-dependency-review-contract.md) 为单一事实源。
新 finding 必须用 `affected_test_dimensions` 精确声明它会阻塞哪些测试维度；缺少角色通常为
`REVIEW` 且只影响 `permission`。只有角色本身决定业务结果或安全边界且存在明确冲突时，才使用
`ROLE_PERMISSION_CONFLICT / REJECT`。

## 测试点

```json
{
  "test_point_id":"TP-<稳定摘要>",
  "requirement_id":"REQ-...",
  "function_id":"FUN-...",
  "atomic_id":"AF-...",
  "category":"negative",
  "objective":"验证必填字段为空时拒绝提交",
  "preconditions":["用户具有提交权限"],
  "action":"将必填字段置空后提交",
  "expected_result":"系统拒绝提交并显示需求定义的提示",
  "field_ids":["FLD-..."],
  "rule_ids":[],
  "source_refs":["SRC-...#表4"],
  "readiness":"ready",
  "blocking_finding_ids":[]
}
```

`category` 允许 `normal / negative / boundary / permission / state / data / integration / nfr / exploratory`。

`ready` 测试点必须满足：`preconditions` 是非空数组、`action` 与 `expected_result` 非空、`source_refs` 非空且 `blocking_finding_ids` 为空。没有特殊前置条件时写明“无特殊前置条件”。只有动作名、字段清单或“按需求定义处理”之类占位 Oracle 的测试点保持 `review_required`。

## 覆盖与验收

`coverage.source_coverage` 包含 `claim / relevant_units / processed_units / review_required_units / skipped_units / unavailable_units / uncovered_ranges`。`unresolved_source_unit_count` 是来源状态为 `review_required / unavailable / skipped`、缺少 disposition，或 disposition 本身为 `review_required / unavailable` 的相关来源单元去重并集；绑定 finding 不会让 unavailable 来源自动变成已完成。`audit.verdict` 允许 `NOT_RUN / PASS / PASS_WITH_REVIEW / REJECT`。整体未通过不等于所有测试维度都不可用；评审结果投影到图谱后，只允许逐最小功能、逐维度消费状态为 `READY` 的切片。整体 `PASS` 仍要求 full、无遗漏、六维完成、无未解决 finding 和生命周期 ACCEPTED。
