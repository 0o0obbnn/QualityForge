# QualityForge 页面地图

> 页面信息架构以8模块产品边界为准。以下是目标线框范围，不代表前端已实现；资源API以32/37号为准。

## 1. 全局框架

- 顶栏：Tenant、项目（Workspace）切换、Release切换、全局搜索、通知、个人菜单。
- 左侧一级导航：任务看板、知识库、测试策划与设计、自动化测试开发、测试执行、质量分析与缺陷、AI Agent中心、平台管理。
- 全局抽屉：WorkItem详情、ReviewTask审核、Agent运行/Trace、Evidence预览。

## 2. 页面与路由

| 模块 | 页面 | 建议路由 | 核心内容 |
|---|---|---|---|
| 任务看板 | 工作看板 | `/projects/:workspaceId/board` | 工作项、AI进度、阻塞、Release筛选 |
| 任务看板 | 待我审核 | `/projects/:workspaceId/reviews` | 版本Diff、证据、检查、职责/期限、决定 |
| 任务看板 | 工作项详情 | `/projects/:workspaceId/work-items/:workItemId` | 运行、依赖、评论、Trace和产出物引用 |
| 知识库 | 来源与需求 | `/projects/:workspaceId/knowledge/sources` | 导入、快照、需求版本、冲突 |
| 知识库 | API契约 | `/projects/:workspaceId/knowledge/api-contracts` | 契约版本、Operation/Schema、Diff和Baseline |
| 知识库 | 知识条目 | `/projects/:workspaceId/knowledge/entries` | 检索、候选、审核、适用/失效条件 |
| 测试策划与设计 | 测试策略 | `/projects/:workspaceId/planning/strategies` | 范围、风险、方法、准入/退出和审核 |
| 测试策划与设计 | 测试计划 | `/projects/:workspaceId/planning/plans` | Release、里程碑、资源、DAG和验收准则 |
| 测试策划与设计 | 场景与用例 | `/projects/:workspaceId/design/cases` | TestingIR、场景树、草稿、正式版本和Coverage |
| 自动化测试开发 | 自动化代码 | `/projects/:workspaceId/automation/scripts` | Web/API等代码、版本、绑定、检查和Review |
| 自动化测试开发 | 配套资产 | `/projects/:workspaceId/automation/assets` | Locator、Mock、数据Profile、视觉基线 |
| 测试执行 | 执行计划 | `/projects/:workspaceId/execution/plans` | 版本冻结、环境、Runner策略和触发 |
| 测试执行 | 执行监控 | `/projects/:workspaceId/execution/tasks` | 队列、实时日志、结果、证据和重试 |
| 质量分析与缺陷 | 结果分析 | `/projects/:workspaceId/quality/analyses` | 聚类、RCA、证据和替代解释 |
| 质量分析与缺陷 | Defect | `/projects/:workspaceId/quality/defects` | 草稿/版本、状态、同步attempt和回执 |
| 质量分析与缺陷 | 报告与门禁 | `/projects/:workspaceId/quality/reports` | 报告签署、指标口径、门禁/流水线 |
| AI Agent中心 | 能力注册 | `/projects/:workspaceId/ai/capabilities` | Skill、Agent、Prompt、Workflow版本和权限 |
| AI Agent中心 | 运行与评测 | `/projects/:workspaceId/ai/operations` | Session、Trace、Eval、成本和降级 |
| 平台管理 | 项目与Release | `/platform/workspaces` | Workspace、Release、成员和归档 |
| 平台管理 | 环境与资源 | `/projects/:workspaceId/platform/runtime` | Environment、Secret引用、Runner和配额 |
| 平台管理 | 集成与权限 | `/projects/:workspaceId/platform/governance` | Integration、RoleBinding、ReviewPolicy、Audit |

路由使用`projects`作为UI语义，不创造Project领域实体；所有请求仍使用workspaceId。

## 3. 审核界面最低信息

审核页必须同时展示：产出物类型/稳定ID/版本ID/摘要、来源版本、变更Diff、AI/人工作者、确定性检查、独立验证、Evidence、风险、ReviewPolicy、职责分离、历史决定和陈旧状态。

批准按钮在权限不足、摘要不匹配、blocking check失败或职责分离冲突时禁用并说明服务端原因；前端禁用不是授权边界。

## 4. V1页面优先级

P0：工作看板、待审核、来源/API导入、策略、计划、用例、Web/API代码、执行监控、分析/Defect/报告、基础项目/环境/权限、Agent Trace。

P1：复杂知识图谱、可视化Workflow编辑器、高级门禁、跨项目运营、Skill市场和L3自治控制台。

## 5. 状态展示规则

- `FAILED`（业务未满足）与`ERROR`（无有效执行）分色且配文字/图标。
- AI建议、执行事实和人工决定使用不同视觉层级。
- `STALE`、`BLOCKED`、`INCONCLUSIVE`不能渲染为通过。
- 长任务显示阶段、版本、已用时间、取消、降级和恢复条件。
