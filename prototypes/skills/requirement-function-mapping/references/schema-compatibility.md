# 产物与 Schema 兼容矩阵

Schema 版本属于具体产物类型，不表示整条流水线的统一成熟度。消费者必须同时检查 `meta.artifact_kind` 和 `meta.schema_version`，不得只比较版本号。

| artifact_kind | 当前 Schema | 生产脚本 | 可接受输入 | 下游用途 |
|---|---:|---|---|---|
| `full_discovery_draft` | 1.1 | `extract_markdown_full_draft.py` | Markdown | 未合并事实和候选台账，不可直接生成正式测试 |
| `normalized_requirement_mapping` | 1.2 | `finalize_mapping.py` | 1.1 发现草稿或兼容映射 | 稳定语义 ID、字段上下文和生成就绪度 |
| `review_projected_mapping` | 1.3 | `apply_review_to_mapping.py` | 1.2 映射 + 需求评审 | 按测试维度投影评审门禁 |
| `typed_requirement_graph` | 1.4 | `enrich_graph_model.py` | 1.2+ 映射 | 类型化节点、规则、状态和关系 |
| `review_projected_typed_graph` | 1.4 | `apply_review_to_mapping.py` | 1.4 图谱 + 需求评审 | 测试设计的权威事实层 |
| `test_design_input` | 2.0 | `build_test_design_input.py` | 已投影图谱 | 下游按最小功能和 READY 维度消费 |

`full_discovery_draft@1.1` 中的引用统一表示为 `reference_dependency`，其分类和完整字段以 [提取契约](extraction-contract.md) 为准。

## 兼容规则

- `assets/mapping_template.json` 只用于 `full_discovery_draft@1.1`，不是最新正式图谱模板。
- 1.1 → 1.2 必须运行 `finalize_mapping.py`；1.2/1.3 → 1.4 必须运行 `enrich_graph_model.py`，不得只修改版本号。
- 评审投影不删除来源事实。对 1.4 输入投影后仍为 1.4；对 1.2 输入投影后为 1.3。
- 比较版本时，先把两端规范化到相同 `artifact_kind` 和兼容 Schema。不同类型的产物不得直接做业务差异比较。
- 未列入矩阵的版本视为不兼容；停止下游生成并报告版本缺口。

历史产物结构已经属于1.1–1.4、但缺少 `artifact_kind` 时，使用以下命令生成新文件；迁移器拒绝原地覆盖，也不会升级 Schema 或修改业务事实：

```bash
python3 scripts/migrate_legacy_artifact.py --mapping <旧产物.json> --out <迁移后产物.json>
```

新增或修改 Schema 时，必须同时更新本矩阵、对应校验器、模板或生产脚本、迁移回归测试和 `CHANGELOG.md`。
