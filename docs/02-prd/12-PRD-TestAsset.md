# 12-PRD-测试策划与设计

> 现行模块：测试策划与设计。文件名为兼容历史链接保留。自动化代码、Locator、Mock和数据资产迁至13号自动化测试开发。

## 1. 目标与边界

让AI基于已固化来源和API契约生成可追溯的测试策略、测试计划、场景、用例和断言草稿，由测试人员集中审核和纠偏。解决手工产出慢、覆盖遗漏、策略/计划/执行计划语义混乱和草稿直接入库风险。

## 2. 正式产出物

| 产出物 | 必需内容 | 人工责任 |
|---|---|---|
| TestStrategy | 目标、范围、风险、测试类型、方法、准入/退出、环境/数据/自动化/Defect策略 | 认可风险与方法 |
| TestPlan | 策略版本、Release、目标、类型、范围、里程碑、资源、依赖、时间和验收准则 | 认可可执行计划 |
| TestCase | 前置、步骤、数据引用、预期、断言、优先级、类型和SourceTrace | 认可业务正确性与覆盖 |

TestingIR、BusinessRule、Assertion、CoverageReport、TestScenario和DesignTestCase是设计链实体/中间产物，不与三类正式产出物混为同一生命周期。

## 3. 功能需求

| 能力 | AI作用 | 人工控制 |
|---|---|---|
| 范围输入 | 读取RequirementVersion、APIContractBaseline、Release和已审核知识 | 确认关键路径、排除项和冲突来源 |
| TestingIR | 编译规则、领域、状态机、断言和SourceTrace | 裁决关键规则冲突；IR验证不等于业务批准 |
| 策略草稿 | 生成风险驱动策略并运行结构检查 | 审核范围、风险和门槛引用 |
| 计划草稿 | 生成阶段DAG、里程碑、资源和验收准则 | 审核资源、时间、依赖和责任 |
| 场景/用例 | 生成正向、反向、边界、权限、状态、兼容和异常场景 | 批改业务步骤、数据和预期 |
| 覆盖分析 | 计算Requirement/API/Rule/Scenario/TestCase映射和缺口 | 决定接受缺口或生成补充草稿 |
| 版本/Diff | 生成变更摘要和受影响链 | 审核精确版本，不沿用陈旧批准 |

## 4. 关键规则

- TestStrategy替代旧TestDesignPlan；TestPlan表达项目执行安排；ExecutionPlan表达机器执行配置，三者不得合并。
- DesignTestCase是AI设计草稿；只有通过检查和人工审核后才能迁移为TestCaseVersion。
- Coverage必须声明分子、分母、排除项和映射证据；不得用“生成数量”代替覆盖。
- 正式版本状态遵循`DRAFT/GENERATING/PENDING_REVIEW/CHANGES_REQUESTED/APPROVED/PUBLISHED/REJECTED/STALE/ARCHIVED`。
- 任一来源/契约版本变化都应影响分析并把相关草稿或已批准版本标为待重评，而非静默改写。

## 5. 主流程

```text
选择Release和来源基线 → 编译/验证TestingIR
→ 生成TestStrategy草稿 → 人工审核
→ 生成TestPlan草稿 → 人工审核
→ 生成场景/DesignTestCase/Assertion → 独立验证和Coverage
→ ReviewTask → 人工批改/批准 → 发布TestCaseVersion
```

## 6. 降级

- 来源质量差/规则冲突：停止关键路径生成，创建`BLOCK_HUMAN`（55-SOP 定义：Workflow 节点裁决=创建 ReviewTask 并暂停，非 WorkItem 状态，裁决 2026-08-14 批次二）。
- AI不可用：允许人工创建版本并继续使用相同检查/审核流程。
- 覆盖映射不足：标记`INCONCLUSIVE`或缺口，不自动补齐后静默发布。
- 策略未批准：计划可生成草稿但不能批准/启动执行。

## 7. 验收标准

### AC-01 策略、计划、执行计划分离

- **Given** Release已存在TestStrategy；
- **When** 用户安排里程碑和资源；
- **Then** 创建TestPlanVersion，不修改策略，也不创建Runner执行配置。

### AC-02 AI用例不能直接入库

- **Given** AI生成高置信度DesignTestCase；
- **When** 所有机器检查PASS；
- **Then** 仍创建ReviewTask，人工批准后才生成/发布TestCaseVersion。

### AC-03 覆盖分析分母透明

- **Given** 设计覆盖分析声称90%；
- **When** 用户查看详情；
- **Then** 可见分子、分母、排除项、未覆盖项和每条SourceTrace。
- 注：设计覆盖分析（需求→用例映射）归本模块中间产物；执行覆盖率报告 CoverageReport 由 15 号质量分析与缺陷唯一写入（裁决 B2-1，2026-08-14）。

### AC-04 陈旧版本重评

- **Given** 已批准用例引用APIContractVersion V1；
- **When** Release基线切换V2且存在breaking change；
- **Then** 用例进入受影响队列，旧批准不自动覆盖V2。

## 8. 版本范围

V1跑通策略、计划、用例和人工审核；V2增强变化影响、团队复核和复杂覆盖；V3增强受控L3跨工作项设计，但正式批准仍由人完成。

## 9. 指标承接(裁决 2026-08-14,口径见22号附录C五类覆盖率权威口径)

| 指标 | 本模块角色 | 基线 | 测量方法 | 验收 |
|---|---|---|---|---|
| 设计覆盖(DESIGN 口径) | 生产 | 试点后批准(22 §6) | 已映射需求条目/需求条目总数,SourceTraceEdge 事件,整 Release 窗口 | AC:设计覆盖报告分母/分子可复算 |
| 覆盖分析人工修改率 | 生产 | 试点后批准 | REQUEST_CHANGES 次数/AI 提交版本数,版本级主口径 | AC:版本级口径可复现 |
| 覆盖分析遗漏率(设计层) | 生产 | 试点后批准 | CoverageReport 未覆盖项/分母,整 Release | AC:未覆盖项可溯源到需求条目 |
