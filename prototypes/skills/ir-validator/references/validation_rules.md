# IR 校验规则

## 族 1 — Schema 完整性

v1.0 IR 冻结六个模型类：`requirements`、`entities`、
`business_rules`、`state_machines`、`interface_contracts`、
`constraints`。每类都有必填字段。检查：

- 每条 `requirement` 有 `req_id`、`title`、`description`、`validation_status`。
- 每条 `business_rule` 有 `rule_id`、`condition`、`action`、`source`。
- 每个实体 `entity` 有 `entity_id`、`name`、非空 `fields`。
- 每个 `state_machine` 有 `sm_id`、绑定的 `entity_id`、非空 `states`、`transitions`。
- 每个 `interface_contract` 有 `contract_id`、`endpoint`、`method`。
- `ir_version` 必须精确为 `1.0` 或 `1.0.<数字 patch>`。形如 `1.0evil` 的
  前缀式取值与未知/`v1.1` 版本一律硬 REJECT——v1.0 已冻结，且
  "在 v1.0 冻结期内任何 Skill 不得向 IR 写入未定义字段"。
- 六个冻结模型类必须全部以数组形式出现；缺失或类型错误的集合
  属结构性 REJECT finding。
- `requirements` 非空。六个类都在却全空是一个空契约，不是可发布
  的 IR。
- 模型类层面不允许任何未定义的额外字段（前向兼容守卫：新字段
  出现必须升版本，不许走私）。

族 1 finding 是结构性的——上游 IR 编译步骤漏掉了 IR 规范要求的
东西。连同缺失字段清单一起路由回上游 IR 编译步骤。

## 族 2 — 溯源绑定

每个产出物必须携带 `trace_id`、`source_id`、`parent_id` 并挂到
Traceability Graph。对 IR 而言，每条规则、需求、实体和约束都必须
携带 `source_trace`（人类可读的溯源：来自哪份输入文档、哪一节、
哪一轮抽取）。检查：

- 每条规则、需求、约束的 `source_trace` 存在且非空。
- 没有 `source_trace` 的规则直接 REJECT——它是一条被烤进语义
  契约的不可验证断言。（这是上游 IR 编译步骤最常见的失败：模型
  凭空发明规则、忘了给出依据。）

## 族 3 — 置信分层

每个 AI 推断的元素都携带 [0.0, 1.0] 的 `confidence` 和一个
`source`。校验器不做人工评审路由（那是人工评审的职责）；它检查
*分布*是否健康：

- 每条规则和需求都有有限、非布尔的数值 `confidence`。
- `confidence` 在 [0.0, 1.0] 内。
- 报告 confidence 的分布（多少 ≥0.9、多少在 [0.7,0.9)、多少
  <0.7）。健康的 IR 分布应合理；全部 0.9+ 的 IR 可疑（模型
  无差别打了高分，这是幻觉的信号），全部 <0.7 的 IR 说明上游
  IR 编译步骤没能可靠抽取任何东西，大概率要重审输入。

校验器不单凭分布拒绝——它标记。但完全没有 confidence 字段的
元素是 REJECT（缺失 ≠ 高分）。

## 族 4 — 冲突解决（显式禁令）

设计规则："禁止放行含未解决 conflict 标记的 IR"。上游 IR 编译
步骤检测到多源冲突时，必须保留全部源版本，标记 `conflict: true`
并附 `conflict_refs` 清单。校验器检查：

- 任何元素不得带着未解决的 `conflict: true` 放行。若 `conflict`
  为 true，`resolution_status` 必须是 `RESOLVED`（并记录选定的
  解决方案）；否则整份 IR 硬 REJECT。
- 被静默丢弃的冲突标记（原始输入中源之间有分歧、IR 里却是干净
  的单一取值且无 conflict 标记）在这里检测不到——那是上游 IR
  编译步骤的诚实性问题。校验器只抓*已声明*却悬而未决的冲突。

## 族 5 — 状态机可达性

设计规则："每个状态机无不可达状态"。对每个 `state_machine`：

- `initial_state` 必填，必须在 `states` 中，且永不推断。
- `states` 中每个状态都必须能从 `initial_state` 经某条迁移链
  到达（图可达性）。
- 每个状态必须至少有一条出边迁移，或被标记 `terminal: true`。
  非终态的死胡同是规格 bug。
- 每条 `transition.from` 与 `transition.to` 必须是 `states` 的
  成员。引用未声明状态的迁移是 REJECT。
- 状态机构建步骤（state-machine builder）："必须检查死锁状态与不可达状态并在输出中标注"——上游状态机步骤本应标注这些，
  但校验器独立复查，因为上游状态机步骤的标注本身也是可能出错的
  AI 产出。

## 族 6 — 实体字段健全性（领域模型抽取步骤的显式要求）

领域模型抽取步骤（domain-model extractor）："字段级敏感级别必须给出初判，不得默认为 PUBLIC"。对每个实体字段：

- `sensitivity_level` 取值 `PUBLIC | INTERNAL | SENSITIVE` 之一。
- 不允许任何字段的 `sensitivity_level` 缺失、为空，或无依据地
  字面默认为 PUBLIC。这条规则的全部意义就是强迫做出有意识的
  敏感级判断——静默读作 PUBLIC 的字段正是该规则要抓的失败模式。

注意：校验器判断不了*正确*的敏感级是不是 SENSITIVE——那需要
领域知识。它只抓程序性失败（没有做出判断）。
