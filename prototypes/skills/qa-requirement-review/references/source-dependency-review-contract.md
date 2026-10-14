# 资料依赖评审契约

资料依赖评审是正式需求评审的入口阶段，在功能图谱建模前执行。它判断需求引用的项目资料是否已提供；功能图谱只消费评审结论并绑定受影响范围。

## 产物

`requirement_source_dependency_review@1.0` 包含：

```text
meta
source
provided_sources[]
dependencies[]
findings[]
summary
```

`dependencies[]` 每次引用出现一项：

```json
{
  "dependency_id":"DEP-...",
  "reference_type":"external_artifact",
  "reference_key":"external_artifact:导出模板.xlsx",
  "target_name":"导出模板.xlsx",
  "quote":"导出模板见《导出模板.xlsx》",
  "locator":"L120",
  "status":"missing",
  "reason":"未在本次评审提供的资料中定位到该依赖"
}
```

- `reference_type`：`internal_reference / external_artifact / existing_baseline / pending_artifact`。
- `status`：`available / review_required / missing`。
- 同一资料的多次引用共享 `reference_key`，但保留各自 `dependency_id / locator / quote`。
- “详见云盘”是位置提示，与同句中的具名资料合并，不单独计为一份资料。
- `summary` 分开报告引用出现次数与去重目标数。

## Finding

每个未解决的 `reference_key` 形成一个去重 Finding，可引用多个 `dependency_id`：

- `MISSING_REFERENCED_ARTIFACT`：已引用的外部附件或标准未提供。
- `MISSING_EXISTING_BASELINE`：“同当前”或“同历史”依赖的基线未提供。
- `PENDING_REQUIRED_ARTIFACT`：需求声明尚需提供的文档。
- `UNRESOLVED_INTERNAL_REFERENCE`：文档内部引用不能唯一定位。

资料缺失使用 `ABSENCE` 证据，`inspected_scope` 必须列出本次实际提供和检查的资料。缺失判断只对该范围有效，不等于断言资料在项目中永久不存在。

## 执行

```bash
python3 scripts/review_source_dependencies.py \
  --source <需求.md> \
  [--provided-source <附件或基线资料>]... \
  --out <资料依赖评审.json>
python3 scripts/validate_source_dependency_review.py --review <资料依赖评审.json> --source <需求.md>
```

产物必须在后续功能图谱流程中作为 `--source-review` 输入。
