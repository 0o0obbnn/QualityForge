---
name: "qa-requirement-review"
description: "从 QA 视角全量评审 PRD、接口说明和相关需求资料，生成带来源证据、覆盖台账和阶段验收状态的结构化评审 JSON 与可直接评审的 Markdown 报告。当用户要求需求评审、可测试性分析、歧义/冲突/遗漏检查或测试分析时使用；功能、最小功能和字段事实建模改用 requirement-function-mapping。"
---

# 需求质量评审

把需求资料转换为可追踪、可验收、可供需求建模和测试设计消费的质量评审产物。评审判断“需求写得是否足够明确、完整、一致且可测试”，不替代功能事实提取。

## 执行责任

执行模型是语义评审主体：必须阅读本次范围内的需求正文、表格和关联资料，逐条形成判断、证据和理由。脚本只负责哈希、来源定位、候选缺口扫描、队列生成、合并、统计、结构校验和渲染。

确定性扫描结果是评审线索，不是语义结论。模型必须回到原始来源验证线索，才能把维度更新为 `CLEAR / FINDING / NOT_APPLICABLE`。没有完成来源阅读或无法判断时保留 `NOT_REVIEWED`；“扫描器没有发现问题”不能作为 `CLEAR` 的依据。

`requirement-function-mapping` 是可选的事实建模输入，不是本 Skill 启动的前置条件。没有图谱时使用来源定位和稳定 `requirement_id` 完成评审；图谱生成后只回填 `function_id / atomic_id / field_id / rule_id` 和精确影响范围，不让图谱替代原文语义判断。

## 运行隔离

每次评审先判定运行类型：用户明确要求“继续、续评、增量评审”时，才允许加载指定的既有评审 JSON；其余情况均为新评审。新评审只以用户本次指定的原始来源和当前 Skill 为输入，在新的输出目录中从空白状态建立基线。目录中已有的评审 JSON、报告、队列、映射或历史结论仅是旁路文件，不得作为输入、证据、进度或判断依据。

来源范围服从用户本次选择。用户只指定 Markdown 时，AI 完整阅读该 Markdown；同名 DOCX、PDF 或历史转换产物不自动加入评审范围。文档中的附件、图片引用或“同当前”等依赖仍按资料依赖契约登记其可用性，但不能为补齐资料而擅自扩大输入范围。

## 输入与产物

输入可以是 Markdown、DOCX、PDF、HTML，以及用户提供的接口、原型、数据字典和现状资料。评审开始时必须明示登记本次实际提供的资料范围；“缺失”只表示在该范围内无法定位。DOCX/PDF 应先转换为能保留标题、表格、图片引用和来源位置的中间文本；无法可靠解析的内容进入 `unavailable`，不得静默忽略。

默认生成：

1. `<文档名>_需求质量评审.json`：权威机器产物，符合 [评审契约](references/review-contract.md)。
2. `<文档名>_需求质量评审.md`：由同一 JSON 渲染的人读报告。

除非用户指定输出位置，否则在当前工作区的输出目录生成，不擅自写回原始资料目录。

## 执行

### 1. 建立评审基线

先记录运行类型和用户指定的来源清单；新评审创建全新的输出目录与空白评审状态。登记每份来源的 `source_id`、版本、摘要哈希、权威级别和可用性。再按 [资料依赖评审契约](references/source-dependency-review-contract.md) 检查文档内部继承、外部附件、现有系统基线和待提供资料，并把章节、规则段落、表格、图片和接口拆成 `source_units`。

完成条件：运行类型和输入边界已记录；新评审未继承任何历史评审状态；全部输入均已登记；每个引用依赖都有分类、定位、状态和去重键；每个来源单元都有 `processed / review_required / skipped / unavailable` 状态；非 `processed` 单元有原因。

### 2. 建立需求条目

从全部相关来源单元识别可独立评审的需求陈述，生成不依赖图谱 ID 的稳定 `requirement_id`并保留来源证据。图谱建立后可在后续语义评审中回填 `function_id / atomic_id / field_id / rule_id`，但它们不是资料完整性评审的前置条件。资料 Finding 投影时优先消费图谱给出的 `blocking_scope.atomic_ids`；只有没有最小功能范围时才回退到所属功能的需求集。

完成条件：每个相关来源单元都映射到需求条目、评审 finding，或带理由的无产物决策。

### 3. 逐条评审

完整模式对每个需求条目评估六个标准维度：

- `ambiguity`：术语、主体、条件、范围、量化标准是否明确。
- `consistency`：跨段落、表格、接口和来源是否矛盾。
- `testability`：是否存在可观察结果、验收边界和可判定 oracle。
- `completeness`：正常、异常、边界、数据、状态、依赖和恢复路径是否完整。
- `nfr_measurability`：适用的非功能要求是否定义指标、负载模型和阈值。
- `role_permission`：角色、数据范围和允许/拒绝行为是否明确且一致。

每项状态为 `CLEAR / FINDING / NOT_APPLICABLE / NOT_REVIEWED`。完整模式只有在进入 `ACCEPTED` 时才不允许遗留 `NOT_REVIEWED`；评审过程和阻塞结果必须如实保留未决状态。快速扫描只评估 ambiguity、consistency、testability，产物不能进入正式下游。

这里的“完成”指模型或人工已经阅读相关来源并写入可复核理由，不是脚本把字段填成非空。逐条评审使用 [评审问题解决契约](references/review-resolution-contract.md) 的 `assessment_reviews / new_findings` 分批写回；每个 `CLEAR / NOT_APPLICABLE` 都要保留支撑判断的 `source_refs`，每个 `FINDING` 通过 finding 的证据追踪来源。

详细检查方法、finding code、证据类型和严重度见 [全量评审协议](references/review-protocol.md)。

### 4. 形成可回写的评审结论

对已明确且可测试的需求生成 `test_points`，至少包含测试目标、场景类别、前置条件、动作、预期结果和追踪关系。测试点是评审辅助信息，不直接作为最终测试用例输入；正式链路由 `requirement-function-mapping` 把评审结论投影回图谱后再编译测试设计切片。

测试点状态：

- `ready`：有明确触发、输入和预期结果，没有阻断 finding。
- `review_required`：可形成草稿，但含待确认假设。
- `blocked`：缺少关键规则或 oracle，不得生成正式用例。

测试点由执行模型依据已经评审的需求生成。脚本不得从动作名、字段绑定或图谱存在性自动生成 `ready`；`ready` 至少要有明确前置条件、具体动作或输入、来源引用和非占位预期结果。确实没有特殊前置条件时显式写“无特殊前置条件”，不能留空。

每个 finding 使用 `OPEN / RESOLVED / WITHDRAWN / ACCEPTED_RISK` 生命周期。解决 finding 时必须补充解决依据并同步更新对应 `requirement_assessments`；只修改 finding 状态不能视为评审闭环。
每个新 finding 还必须声明精确的 `affected_test_dimensions`。缺少执行角色默认只影响权限测试，
不得扩散阻塞已经具备动作、证据和 Oracle 的功能测试。

收到产品、研发或接口资料的确认结果时，读取 [评审问题解决契约](references/review-resolution-contract.md)，生成解决包并执行：

```bash
python3 scripts/build_review_resolution_queue.py --review <评审.json> --out <评审解决队列.json>
python3 scripts/apply_review_resolutions.py --review <评审.json> --resolutions <解决包.json> --out <更新后的评审.json>
python3 scripts/validate_review.py --review <更新后的评审.json> --source <主需求.md>
```

全量队列过大时使用 `--dimension`、重复的 `--requirement-id`，或 `--offset / --limit` 生成可独立复核的小批次；合并时仍以稳定 finding 和 assessment 标识对账。批次只允许作为进度快照，
不得因为其中出现少量 CLEAR 就宣称完成全文评审。最后一批合并后必须重新计算来源处置、
NOT_REVIEWED、finding、errors 和 warnings，再决定下游范围。

### 5. 验收与发布

在建立功能图谱前先执行资料依赖评审：

```bash
python3 scripts/review_source_dependencies.py --source <需求.md> [--provided-source <项目资料>]... --out <资料依赖评审.json>
python3 scripts/validate_source_dependency_review.py --review <资料依赖评审.json> --source <需求.md>
```

该产物作为 `requirement-function-mapping --source-review` 的输入。功能图谱建立后，再完成逐需求六维语义评审和评审投影。

运行：

```bash
python3 scripts/validate_review.py --review <评审.json> [--source <主需求.md>]
python3 scripts/render_review_markdown.py --review <评审.json> --out <评审.md>
```

有功能图谱时，可以用确定性工具建立不可冒充正式结论的评审草稿和候选问题：

```bash
python3 scripts/build_review_draft.py --source <需求.md> --mapping <功能点图谱.json> --out <评审草稿.json>
python3 scripts/analyze_mapping_gaps.py --review <评审草稿.json> --mapping <功能点图谱.json> --out <带确定性缺口的评审.json>
python3 scripts/analyze_markdown_nfr.py --review <带确定性缺口的评审.json> --source <需求.md> --out <含非功能评审的评审.json>
python3 scripts/analyze_structural_conflicts.py --review <含非功能评审的评审.json> --mapping <功能点图谱.json> --source <需求.md> --out <含文内冲突的评审.json>
python3 scripts/build_review_resolution_queue.py --review <含文内冲突的评审.json> --out <语义评审队列.json>
```

执行模型按可控批次读取队列对应的全部来源上下文，填写 `assessment_reviews / new_findings / source_unit_reviews`，再用 `apply_review_resolutions.py` 合并。重复生成队列和评审，直到所有相关来源单元与六维状态都有真实处置，或者剩余项因资料不足明确保持阻塞。

缺口、NFR 和结构冲突分析器只提供候选问题。模型必须验证其来源范围、排除抽取遗漏和误报，再决定确认、修订或撤回：确认使用解决包的 `CONFIRM` 并保留复核来源，修订使用“撤回旧 finding + 新建完整 finding”。逐需求评估不得引用未绑定当前 `requirement_id` 的问题。兼容入口 `complete_semantic_review.py` 只重新汇总 AI/人工已经写入的状态，不执行语义评审、不清除 `NOT_REVIEWED`、不生成测试点。

## 阶段验收标准

只有同时满足以下条件，才允许 `audit.verdict=PASS`、`meta.lifecycle_status=ACCEPTED` 和 `audit.downstream_eligible=true`：

- 完整模式覆盖全部相关来源单元，且无 skipped、unavailable 或 uncovered。
- 每个需求完成六维评审，不存在 `NOT_REVIEWED`。
- 每个 finding 的证据类型和来源范围可核验。
- 硬缺陷已解决或明确阻断，不能带着 `REJECT` finding 通过。
- 所有 `ready` 测试点具备可执行动作和可判定预期结果。
- 需求、finding、测试点与功能图谱标识不存在悬空引用。
- JSON 通过校验器；Markdown 与 JSON 来自同一版本。

`PASS_WITH_REVIEW`、`REJECT`、快速扫描和任何草稿的包级 `downstream_eligible` 必须为 `false`。这个布尔值只限定“能否声明全包已完成评审”，不是中止后续 Skill 的流程开关。

包级未通过时仍必须把评审投影回图谱，由下游逐项、逐维度放行已明确内容；这不改变本评审产物自身的验收结论。评审每完成一批都可以发布新的评审快照：已经 `CLEAR` 且无影响 Finding 的维度继续进入测试设计，其余项继续留在解决队列。

## 证据边界

- 原文明示用 `QUOTE` 证据；`quote` 必须是连续原文。
- 缺失问题用 `ABSENCE` 证据，记录已检查范围和预期要素，不引用无关原文充数。
- 冲突用 `CONFLICT` 证据，同时保留冲突双方。
- 领域常识只能形成待澄清问题，不能升级为已确认需求。
- 结构校验通过不等于语义评审完成。
