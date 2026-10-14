# QualityForge 前端交接文档（原型对齐版）

> 生成：2026-08-18 ｜ 最近更新：2026-08-30（WP-01A 全局上下文）｜ 基线：deliverables/2026-08-12/prototype/（27 页原型）｜ 前端轨：autoclaw

## 一、启动命令

```bash
# 前端（mock 模式，无需后端，独立预览原型）
cd frontend && npm install && VITE_MOCK=1 npm run dev
# 打开 http://127.0.0.1:5173/

# 前端（真实模式，联调）
cd frontend && npm run dev:integration   # 端口 4174，/api 代理到 127.0.0.1:8000

# 后端
cd backend && uv run uvicorn qf.main:app --host 127.0.0.1 --port 8000
```

## 一·补二 WP-01A 全局 Workspace/Release 上下文（2026-08-30）

- App 持有 `workspaces`/`releases` 全局状态：登录后 `resolveProfileContext` 取服务端最近活跃 Release（`pickCurrentRelease`：服务端仅回 ACTIVE 且 updatedAt DESC，前端不重算）
- 顶栏项目/Release 双切换器接真实列表：切换项目走**服务端专用命令** `POST /api/v1/auth/switch-workspace`（重签 JWT + 新 cookie），成功后重置 Release 并整体换 profile 引用 → 全站查询自动刷新、不残留旧工作区数据
- `lastBusinessUpdatedAt` 口径由服务端给出（9 类业务事件 MAX，排除 provider 运行面事件；轮询/Trace 不刷新），切换器排序即服务端排序
- 联调前置：第二工作区用 `backend/scripts/qf_seed_workspace.py` 种子；e2e 见 `e2e-integration/workspace-switch.spec.ts`（未种子时 skip）
- mock 模式：切换为本地状态降级（无后端），`dataService.switchWorkspaceProfile` 仅真实分支调用
- 任务卡/AgentPlan 裁决 UI + 执行命令条（批次六十一）：工作项详情新增「任务卡（正式任务输入）」与「AgentPlan（人工裁决链）」两面板——固化任务卡（提交即固化、新卡取代旧卡）、生成计划（动态步骤行）、批准/拒绝（弹层展示内容摘要对账，批准后任务卡转 ACTIVE）；执行监控页运行中任务行内 暂停/恢复/取消 命令（回执 effectiveStatus 入 toast）。真实链 e2e 全通（建项→固化→计划→批准→刷新持久）
- 修复两处真实模式缺陷：看板乐观行使用后端真实 id（此前假 id 点击进详情 404）；createTaskCard body 携带多余 workspaceId 致 422（StrictRequest extra_forbidden）。契约补 listTaskCards 读面（141 op，39 号 §3.1 未列、前端纵向需要）
- 协作对话页（批次六十）：/conversations 双栏（会话列表最近活跃优先 + 只追加消息流）；真实模式接 4 op（listConversations/createConversation/listConversationMessages/createConversationMessage）；contentRef 策略——PUBLIC/INTERNAL 低敏正文内联、CONFIDENTIAL/RESTRICTED 自动转引用 chip（与服务端 dataClass 语义一致，本地运行时简化口径）；导航「工作」组新增入口；组件测试 3 条 + mock e2e 2 条 + 真实后端集成链 1 条
- 常用项目置顶（批次五十二）：切换器行内 置顶/取消置顶（`setWorkspacePin`，任意成员工作区可操作）；置顶组优先展示；登录默认工作区=最近置顶（服务端解析，前端无需切换跳）
- 驾驶舱投影 `getProjectContextProjection` 数据面就绪（工作区/Release/置顶/三类待办计数），UI 消费归 WP-03 首屏，不在本切片接管徽标（fetchReviewCount 已随 profile 刷新）

## 一·补 前端 README（新增）

从零启动 / 模式切换 / 门禁 / mock 数据层 / 页面路由 / 手动测试清单 / 已知限制，统一见 `frontend/README.md`。

### mock 本地持久化台账（deep_delivery，localStorage `qf_mock_store`）

- `createWorkItem` → `workItems` 集合 → 看板列表合并显示，刷新不丢
- `createExecutionPlan` → `executionPlans` 集合 → 执行计划列表合并显示
- `submitReviewDecision` → `reviewDecisions` 集合（`readMockDecisions()` 读取，供验收复核）
- `createEnvironment` → `environments` 集合 → 环境列表合并显示（页面级 e2e 双验证：提交可见 + 刷新不丢 + 校验错误不写库）
- 清空：`resetMockStore()` 或控制台 `localStorage.removeItem("qf_mock_store")`
- 验证：vitest 4 条（`dataServicePersist.test.ts`，vi.stubEnv 动态加载 mock 分支）+ e2e 页面级实测（`mock-persist.spec.ts` 2 条 + `env-create.spec.ts` 2 条）

### 加载骨架（deep_delivery）

- 看板（BoardPage）、测试计划（PlansPage）、环境（EnvironmentsPage）首载渲染 qf-skeleton shimmer 骨架，fetch 完成/失败后切换列表或空态；失败有 toast 反馈

### 前端闭环核验结论（.cluster/qf-p3-20260818/subagent_04-前端闭环核验.md）

- 27 页原型 100% 有实现，0 缺失路由；PlaceholderPage 仅作 /:module 未知路径兜底
- 0 处阻塞主流程的未完成痕迹；0 处真无响应交互（演示行为均有 toast 反馈）
- 3 项 P0（mock 无持久化/环境提交不写回/加载态缺失）本轮全部修复并复验

### 响应式修复（本轮）

- `.topbar` 900px 断点 flex-wrap 换行；`.search` 弹性收缩；640px 断点 provider-chip 换行
- `main` 加 `min-width:0` 修复 grid 1fr 列 min-content 撑宽（topbar 溢出根因）
- 内联 `gridTemplateColumns`（review-layout ×2、kv ×3）全部 class 化：`.review-layout`（300px 1fr，900px→1fr）、`.kv/.kv-grid` 支持 `--kv-first` 变量（900px→1fr）
- 验收：`e2e/responsive.spec.ts` 14 条全绿（桌面 6 页 + 移动 6 页 + 抽屉 + 表格滚动）

## 二、账号与种子数据

| 项 | 值 |
|---|---|
| 联调账号 | admin@test.com / Test1234567890（本地 SQLite，仅开发环境） |
| 数据库 | backend/data/qualityforge.sqlite3（相对 backend/ 工作目录，重启不丢） |
| 种子数据 | 联调创建 7 个工作项（含「联调测试策略」）；审核任务须由 Agent 会话生成后出现 |
| 前端 mock | VITE_MOCK=1 时使用 frontend/src/mock/mockData.ts（原型演示数据 6 队列项/6 看板行） |

## 三、接口清单（本轮联调涉及）

| 接口 | 用途 | 验证状态 |
|---|---|---|
| GET /api/v1/auth/status | 登录态探测 | ✅ |
| POST /api/v1/auth/setup | 初始化本地管理员 | ✅ |
| POST /api/v1/auth/login | 登录（qf_access/qf_csrf cookie） | ✅ |
| GET /api/v1/auth/me | 当前用户/工作区 | ✅ |
| POST /api/v1/work-items | 创建工作项（releaseId 必须 UUID、acceptanceCriteria 非空字符串、requiresReview/objective 必填、Idempotency-Key 头、CSRF） | ✅ |
| GET /api/v1/work-items?workspaceId= | 工作项列表 | ✅ |
| GET /api/v1/review-tasks?workspaceId= | 审核队列（真实模式无数据时前端显示空态，不虚构） | ✅ |
| POST /api/v1/review-tasks/{id}/decisions | 审核决定（绑定 contentDigest） | 契约已接，待 Agent 生成审核任务后实测 |

**契约注意**：`workItemType` 后端暂收 STRATEGY/PLAN/CASE/GENERAL；`acceptanceCriteria` 为字符串非数组。前端 dataService 已做映射。

## 四、页面结构（对齐原型 + M2 七类视图已全量完成）

| 路由 | 页面 | 原型源 |
|---|---|---|
| /board | 工作看板（视图切换 tabs 七入口：全部工作项/AI 工作中/退回重做/待执行/阻塞风险/管理视图 + 我的待审核跳转） | 10-board.html + §5.5.9 |
| /reviews | 待我审核（队列 + kv 详情 + 4 Tab + 三弹窗 + 策略条 + H8 连续导航） | 11-reviews.html |
| /work-items/:id | 工作项详情 | 12-workitem.html |
| /help | 帮助与术语（H10 最小方案：8 核心条目） | 新建 |
| /knowledge 等 6 模块 | 占位页（后续里程碑） | 20-82 原型 |
| 登录/初始化 | 左品牌栏 + 右表单 | 01-login.html |

**七类视图完成度（M2 计划 §四 验收条目 1）**：
- 视图 1 我的待审核 ✅（/reviews，含 H8 连续导航：上一项/下一项 + 决定后自动聚焦下一项）
- 视图 2 AI 工作中 ✅（Agent/步骤/耗时/预算/中断入口；中断按钮待后端 interrupt endpoint）
- 视图 3 审核退回/重做 ✅（轮次/意见/差异/修改人）
- 视图 4 待执行/执行中 ✅（环境/Release/脚本版本/ExecutionTask；数据待 M3 后端）
- 视图 5 阻塞与风险 ✅（按原因分组：责任方/持续时间/恢复条件）
- 视图 6 全部工作项 ✅（筛选/分页/新建/分派弹窗）
- 视图 7 管理视图 ✅（8 指标卡 + Lead/Cycle 分布 + 口径提示）

E6（零脚手架）✅ / H8（连续导航）✅ / H9（supersede 无撤销文案）✅ / H10（帮助入口+术语页）✅

## 三·补 M5 降级状态呈现（9b68d00）

- 顶栏 AI Provider 状态 chip 三态：NOMINAL 绿（AI Provider 正常）/ DEGRADED 金（已降级：本地确定性生成，b-warn）/ UNKNOWN 灰（状态未知）
- 数据源：fetchProviderStatus()，假设契约 GET /api/v1/ai/provider/status（后端暂无，404/异常回落 UNKNOWN；mock 模式 NOMINAL）
- 跨轨契约请求：墙 M-136，待后端轨 M5 开工时定死接口形状
- 语义纪律：降级≠故障，用 warning 金不用 error 红（deterministic-local 为计划内 failover 与评估锚点）

## 四·补 功能完成清单（计划项 → 实现映射）

| 计划项 | 实现文件 | 状态 |
|---|---|---|
| 8 模块导航骨架 | src/app/AppShell.tsx | ✅ |
| 视图 6 全部工作项 | src/views/BoardPage.tsx | ✅ |
| 视图 1 我的待审核 | src/views/ReviewsPage.tsx | ✅ |
| 视图 2 AI 工作中 | src/views/board/AiRunsView.tsx | ✅ |
| 视图 3 退回重做 | src/views/board/ReworkView.tsx | ✅ |
| 视图 4 待执行 | src/views/board/ExecutionView.tsx | ✅ |
| 视图 5 阻塞风险 | src/views/board/BlockedView.tsx | ✅ |
| 视图 7 管理视图 | src/views/board/MetricsView.tsx | ✅ |
| H10 帮助入口 | src/views/HelpPage.tsx + AppShell 侧栏 foot | ✅ |
| 分派弹窗（N4 优先） | BoardPage AssignDialog | ✅（演示形态，待后端 assign endpoint） |

视觉体系：qf-tokens.css（琥珀铜 #D96C1F + 暖石墨）+ qf-components.css 全套组件（按钮/徽标/chip/tabs/modal/toast/diff-view/src-trace/checks/ev-link），已移除 Fluent UI。

## 五、质量记录

- vitest：12 文件 / 47 用例 / 47 passed（含 mock 持久化 4 条）
- lint：eslint（Babel 解析器方案，typescript-eslint 尚不支持 TS7）+ 类型层由 tsc noUnusedLocals 承担
- typecheck：tsc --noEmit 无错误（noUnusedLocals/noUnusedParameters 已开启）
- build：vite build 成功，路由级代码分割（React.lazy + Suspense，ReviewsPage 等视图独立 chunk）
- Playwright mock 模式：63/63 常规（平台管理冒烟 5 条；automation 1 条偶发 flaky，单跑绿）（含执行计划 3 条：列表/冻结清单/双向互跳）（含自动化 4 条：脚本列表/代码 Diff/资产 Tab 切换/侧栏入口）（含规划域 5 条：策略/计划/用例三页+侧栏入口）（含知识库 4 条：三 Tab 切换/契约列表/检索过滤/侧栏入口）
- Playwright 联调模式（真实后端）：3/3
- 后端重启持久化：SQLite 落库验证通过
- 逐屏截图：frontend/visual-align/01-26

## 五·补 目录结构（最佳实践收尾后）

```
frontend/src/
├── main.tsx / App.tsx        # 入口 + 路由（React.lazy 分包 + Suspense）
├── app/                      # 壳层：AppShell/Modal/Toast/Icons
├── views/                    # 页面：BoardPage/ReviewsPage/WorkItemPage/PlaceholderPage/ExecutionMonitorPage/EvidencePage/HelpPage + board/ 五视图
├── pages/                    # AuthPage
├── services/                 # dataService（双模式）+ eventEnvelope（事件信封纯函数）
├── mock/mockData.ts          # 仅演示数据
├── types/domain.ts           # 领域类型（UI 数据形态契约 + 执行域类型）
├── types.ts / api.ts         # 契约类型 / fetch 封装
├── archive/                  # M1 遗留组件（review/ + statusBadge，git 可回溯）
└── styles/                   # qf-tokens / qf-components / app.css
```

## 五·补二 M3 执行与证据（2026-08-18）

- 执行监控页 `/execution-monitor`（侧栏「测试执行」入口）：ExecutionTask 列表（8 状态 + 结果五值）+ KPI 4 卡 + 事件流轮询渲染（终态即停）+ 分页
- 证据审核页 `/evidence/:executionTaskId`：断言明细 + 证据链接 + 结果元数据（digest）+ attempt 历史 + 只追加语义
- 事件信封抽象 `services/eventEnvelope.ts`：eventId 去重 + sequence 缺口检测 + 终态判定（docs/36 §3）
- dataService 执行域访问层（mock/真实双模式，真实模式后端 execution 域未实现时返回空态）
- 契约审计结论：后端执行域 8 个 operation 0 实现（待后端轨）；前端已补领域类型/访问层/信封字段，mock 对齐真实 schema

## 六、已知问题与后续建议

1. **审核决定实测**：后端 review-tasks 由 Agent 会话生成，本轮联调库中尚无审核任务；decide 接口契约已接好（绑定 contentDigest），待 M3 执行链路生成任务后实测。
2. **工作项详情数据**：后端 getWorkItem 未实现，/work-items/:id 页当前展示原型演示数据，接后端需补 GET /work-items/{id}。
3. **搜索框/通知/项目切换**：当前为原型演示行为（toast 提示），后端无对应接口，归后续里程碑。
4. **看板视图切换**：「看板」列布局为演示 toast，真实列视图归 M2.b。
5. **旧组件遗留**：M1 遗留组件已归档至 src/archive/（review/ 组件与 statusBadge），不参与新代码路径，git 可回溯，后续可删除。
6. **建议下一步**：后端补齐 B1（ExecutionResult 补 resultDigest/assertionResultsRef）、B2（执行事件流接口）后，证据页+执行事件流切真实；知识库已做（20/21/22），测试规划三页已完成（30/31/32，Sprint 1 T1-T3）；自动化工作台三页已完成（40/41/42，Sprint 2 T7）；执行计划页已完成（50，Sprint 2 T8）；质量域三视图已切真实接口（Sprint 2 T9）；知识域已切真实接口（Sprint 2 T10）；Agent 中心三页已完成（70/71/72，Sprint 2 T11，b8455fd）；平台管理三页已完成（80/81/82，Sprint 2 T12，eb87b42，全 mock：后端平台管理域无接口）。
