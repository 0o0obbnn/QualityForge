# 类型化需求图谱契约

图谱以扁平节点注册表和有类型的边作为权威存储；树、ER、流程和影响分析都是同一图谱的视图。

## 节点

- `modules[]`：功能模块，可用 `parent_module_id` 递归。
- `functions[]`：用户可感知能力或子功能，引用所属 `module_id`；子功能用 `parent_function_id` 递归引用直接父功能，顶层功能为 `null`。
- `atomic_functions[]`：可独立触发和观察结果的最小功能。
- `business_objects[]`：业务数据对象。
- `business_fields[]`：字段定义及内在约束。
- `field_usages[]`：字段在某最小功能中的输入、查询、展示、输出或校验上下文。
- `business_rules[]`：字段、字段使用或最小功能上的独立规则。
- `business_flows[] / states[]`：有明确证据时登记流程和状态；没有证据时保持为空并暴露缺口。
- `test_cases[]`：可选的下游测试用例索引，只保存稳定 `case_id`、标题和状态；完整步骤仍由测试用例产物维护。

正文出现明确时序词但尚不能可靠绑定全部步骤时，先进入 `business_flow_candidates[]`，状态固定为 `review_required`。候选必须保留原文、所属功能和待确认问题；确认步骤、顺序和异常分支后才能升级为 `business_flows[]` 和 `state_flow / data_flow` 边。

## 规则分类

`sorting / calculation / state / required / uniqueness / format / range / enumeration / permission / operation`

字段定义规则与上下文规则必须分开：长度、格式等可复用内在约束属于 `field_definition`；某页面必填、只读、默认值或排序属于 `field_usage`；跨字段和业务操作规则属于最小功能或流程。

## 边

```text
module --contains--> function
function --contains--> child_function
function --contains--> atomic_function
business_object --contains--> business_field
business_field --has_state--> state
atomic_function --uses_field--> field_usage
field_usage --field_of--> business_field
field_usage|field|atomic --constrained_by--> business_rule
```

`references / depends_on / state_flow / data_flow / conflict` 继续表达跨层业务关系。除结构性 `contains` 外，每条边都必须带原文证据。

测试用例接入影响图谱时使用 `test_case --verifies--> atomic_function|business_rule|field_usage`。需求变化沿反向关系定位用例并标记复核，不得把用例内容复制进需求事实节点。

执行 `enrich_graph_model.py` 后，重复运行必须保持节点 ID 稳定且不产生重复边。
