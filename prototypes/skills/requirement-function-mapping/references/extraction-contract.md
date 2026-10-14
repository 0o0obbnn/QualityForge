# 功能—最小功能—业务字段提取契约

## 标识与顶层结构

- 功能点：`FUN-001`；最小功能：`AF-001`；业务字段：`FLD-001`；关系：`REL-001`；来源：`SRC-001`。
- 标识在单次产物中唯一且稳定，内容顺序调整不应改变已有实体标识。

```json
{
  "meta": {},
  "sources": [],
  "modules": [],
  "source_units": [],
  "functions": [],
  "atomic_functions": [],
  "business_fields": [],
  "field_contexts": [],
  "field_bindings": [],
  "field_relations": [],
  "relations": [],
  "gaps": {},
  "coverage": {},
  "audit": {}
}
```

模块使用基于规范化业务名称的稳定 `module_id`。功能同时保留人读 `module` 与机器引用 `module_id`；子功能用 `parent_function_id` 递归引用直接父功能。`relations` 中建立 `module --contains--> function` 和 `function --contains--> child_function`；不得只靠数组嵌套表达层级。

## 证据对象

所有 `confirmed` 结论至少包含一条证据：

```json
{"source_id":"SRC-001","locator":"3.2.1 / 表4 / 第2行","quote":"申请金额为必填项"}
```

`quote` 使用原文连续片段，不混入分析结论。只有同时提供额外输入文档时，证据才能引用该文档。

## 功能点

```json
{
  "function_id": "FUN-001",
  "name": "创建申请",
  "module": "申请管理",
  "actors": ["经办人"],
  "business_goal": "提交一笔待审批申请",
  "preconditions": ["用户已登录"],
  "outcomes": ["申请进入待审批状态"],
  "status": "confirmed",
  "evidence": []
}
```

`status` 只能为 `confirmed / inferred / unresolved`。

## 最小功能

最小功能是可独立触发、执行并观察结果的最小行为，不等同于按钮或页面控件。
只有叶子功能必须直接拥有最小功能。纯聚合父功能通过 `parent_function_id` 和 `contains` 关系覆盖其子功能，不得为了满足数量校验而制造“处理某功能”之类的占位最小功能。

```json
{
  "atomic_id": "AF-001",
  "function_id": "FUN-001",
  "name": "校验申请金额",
  "action": "提交时校验金额范围",
  "actor": "经办人",
  "trigger": "点击提交",
  "preconditions": ["已填写申请表"],
  "inputs": ["FLD-001"],
  "processing_rules": ["金额必须大于0"],
  "outputs": ["FLD-002"],
  "state_changes": [],
  "branches": ["不合法时拒绝提交并提示"],
  "status": "confirmed",
  "evidence": []
}
```

只改变展示布局、无业务意义且无法独立验证的细粒度 UI 动作不单列为最小功能。

## 业务字段

```json
{
  "field_id": "FLD-001",
  "business_name": "申请金额",
  "technical_name": "amount",
  "business_object": "申请单",
  "description": "本次申请的金额",
  "data_type": "decimal",
  "format": null,
  "length": null,
  "precision": "18,2",
  "required": true,
  "default_value": null,
  "enum_values": [],
  "rules": ["必须大于0"],
  "source": "用户输入",
  "sensitivity": "internal",
  "aliases": [],
  "unresolved_attributes": ["最大值"],
  "status": "confirmed",
  "evidence": []
}
```

未给出的属性使用 `null`、空数组或列入 `unresolved_attributes`，不得根据常见数据库设计猜测。

## 字段绑定

```json
{
  "atomic_id": "AF-001",
  "field_id": "FLD-001",
  "usages": ["input", "validation"],
  "direction": "read",
  "required_here": true,
  "condition": "提交申请时",
  "rules": ["金额必须大于0"],
  "evidence": []
}
```

`inputs` 和 `outputs` 只填写业务字段 ID；自然语言结果分别写入 `state_changes` 或 `branches`。

`usages` 只允许：`input / query / display / output / derived / validation / control / audit`。`direction` 只允许：`read / write / read_write`。每条绑定至少有一条证据；如果绑定仅为推断，应在证据之外增加 `status: inferred`，并列入待确认内容。

## 字段上下文与血缘

每个业务字段至少有一个上下文：

```json
{"field_id":"FLD-001","function_id":"FUN-001","surface":"query_condition","location":"查询页面 / 筛选条件","role":"input"}
```

同一概念在输入、结果、列表、详情或接口请求/响应中出现时，默认分别建字段。有关联时显式建立血缘：

```json
{"source_field_id":"FLD-001","target_field_id":"FLD-002","type":"masked_from","evidence":[]}
```

关系类型只允许 `echo_of / masked_from / derived_from / transformed_from / copied_from / same_concept_as`。`source_field_id` 是来源，`target_field_id` 是产生的新字段。

## 缺口、覆盖与去重

`gaps` 必须包含：

- `unbound_fields`：未绑定任何最小功能的字段 ID。
- `fieldless_atomic_functions`：未使用业务字段的最小功能及合理性说明。
- `unresolved_references`：从资料依赖评审导入的非可用依赖，或已判定为文档内部引用但图谱无法定位目标的依赖；每项保留 `unit_id / reference_type / target_name / locator / blocking_scope / reason`。本 Skill 不通过重新扫描原文自行生成“资料未提供”结论。
- `conflicts`：跨来源或同一来源中的冲突摘要及双方证据。

`coverage` 至少记录总数、已绑定字段数、孤立实体数和证据覆盖率。百分比由实际计数计算，不由模型估计。

- 同一业务对象、同一上下文、相同语义且规则一致的字段才允许合并，其他名称放入 `aliases`。
- 名称相同但业务对象不同的字段不合并。
- 输入与展示、请求与响应、原值与掩码值、基础值与派生值不合并；使用字段血缘关联。
- 字段全局定义与具体最小功能中的用途分开表达。
- 一个最小功能只能直属一个功能点；跨功能复用通过关系表示，不复制实体。

## 提取完整性与属性来源

Schema 1.1 及以上必须包含未经合并的 `field_occurrences`。每个业务字段至少对应一个出现项；每个出现项只能归入一个业务字段。

Schema 1.2 及以上的功能、最小功能、字段和来源标识必须按归一化业务语义生成，不能依赖行号或数组序号。每个最小功能必须包含：

```json
{"generation_readiness":{"status":"review_required","reasons":["触发条件仍需确认"]}}
```

状态只允许 `ready / review_required / blocked`。`ready` 只表示该最小功能的信息足以设计测试，不代表整份图谱已通过阶段验收。

Schema 1.1 及以上还必须包含 `source_units`，其计数与 `coverage.source_coverage` 一致；不能只填写汇总数字而不列出可核验单元。

引用依赖从 `requirement_source_dependency_review@1.0` 导入，使用 `kind: reference_dependency`，`reference_type` 只允许 `internal_reference / external_artifact / existing_baseline / pending_artifact`。每项必须保留评审的 `dependency_id / reference_key / target_name / quote / finding_ids`，并增加图谱侧的 `resolution_status / blocking_scope`。文档内部目标定位成功时记录 `resolved_reference.target_locator`，可对应图谱实体时再记录 `target_id`。

`coverage.reference_summary` 必须由来源单元计算，分开报告 `occurrence_count` 和按 `reference_key` 去重的 `distinct_target_count`，并提供 `by_type` 与 `by_status`。不得把引用出现次数表述为缺失资料数。

每个来源单元还必须包含不依赖行号的 `semantic_key` 和对规范化单元内容计算的 `content_sha256`。`unit_id` 可以用于当前快照内引用；跨版本变化识别使用 `semantic_key`，内容是否修改使用 `content_sha256`。仅定位行号变化不得产生来源内容变化。

Schema 1.2 将相关来源单元的 `status` 区分为 `processed / review_required / skipped / unavailable`。默认正文权威模式下，图片登记为 `relevant=false / skipped`，不进入相关来源覆盖门禁；明确启用多模态视觉核验后，只有完成语义对账的视觉观察才可作为补充证据。

每个业务字段的 `attribute_provenance` 至少覆盖 `business_object / data_type / required / sensitivity`，取值仅允许 `explicit / derived / inferred / unresolved`。

`coverage.source_coverage` 至少包含：

```json
{
  "claim":"representative",
  "relevant_units":10,
  "processed_units":10,
  "review_required_units":0,
  "skipped_units":0,
  "unavailable_units":0,
  "uncovered_ranges":[]
}
```

`claim` 为 `full` 时，相关单元必须全部处理，且不得存在跳过、不可用或未覆盖范围。`claim` 为 `representative` 时，`audit.verdict` 不得为 `PASS`。

Schema 1.1 及以上必须提供布尔值 `audit.downstream_eligible`。它只有在 `claim=full`、`audit.verdict=PASS`、语义复核完成、且没有跳过、不可用或未覆盖来源单元时才能为 `true`；否则必须为 `false`。
