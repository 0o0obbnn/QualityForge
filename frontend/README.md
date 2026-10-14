# QualityForge 前端启动与验收指南

## 从零启动

```bash
cd frontend
npm install
VITE_MOCK=1 npm run dev
# 打开 http://127.0.0.1:5173/
```

无需后端，无需数据库——mock 模式独立运行全部 27 页原型。

## 模式切换

| 命令 | 模式 | 说明 |
|---|---|---|
| `VITE_MOCK=1 npm run dev` | mock 模式 | 静态演示数据 + localStorage 持久化台账 |
| `npm run dev:integration` | 真实模式 | 端口 4174，/api 代理到 `127.0.0.1:8000` |

真实模式下后端接口不可用时：列表页显示空态（不虚构数据），Provider 状态 chip 显示「未知」灰色。

## 门禁命令

```bash
npm run typecheck   # tsc --noEmit
npm run lint        # eslint src --max-warnings 0
npm run test        # vitest（43 组件 + 4 持久化 = 47 用例）
npm run build       # vite build（生产构建）
npx playwright test e2e/  # mock 模式端到端测试（93 条）
```

## Mock 数据层

### 静态数据（`src/mock/mockData.ts`）
- 看板 6 行、审核队列 6 项、执行计划 2 条、各域列表数据
- 所有 `fetch*` 函数 mock 分支从此读取

### 持久化台账（localStorage `qf_mock_store`）
- `createWorkItem` → 写入 `workItems` 集合 → 看板列表合并显示
- `createExecutionPlan` → 写入 `executionPlans` 集合 → 执行计划列表合并显示
- `submitReviewDecision` → 写入 `reviewDecisions` 集合
- 刷新不丢，清空用 `resetMockStore()` 或在浏览器控制台执行 `localStorage.removeItem("qf_mock_store")`

### 切换真实接口
所有数据请求函数统一在 `dataService.ts` 中，mock 分支由 `MOCK_MODE` 常量控制。切换真实接口只需：
1. 确认后端接口路径与返回字段与 `dataService.ts` 真实分支一致
2. 移除 `VITE_MOCK=1`（或改为 `VITE_MOCK=0`）
3. 页面组件无需任何改动

## 页面路由清单

| 路由 | 页面 | 原型 | 状态 |
|---|---|---|---|
| `/artifacts` | 测试产出物总览（默认首页） | 新增 | ✅ |
| `/board` | 工作看板（7 视图） | 10 | ✅ |
| `/reviews` | 待我审核 | 11 | ✅ |
| `/work-items/:id` | 工作项详情 | 12 | ✅ |
| `/knowledge/sources` | 来源需求 | 20 | ✅ |
| `/knowledge/contracts` | API 契约 | 21 | ✅ |
| `/knowledge/entries` | 知识条目 | 22 | ✅ |
| `/planning/strategies` | 测试策略 | 30 | ✅ |
| `/planning/plans` | 测试计划 | 31 | ✅ |
| `/planning/cases` | 场景用例 | 32 | ✅ |
| `/automation/scripts` | 自动化脚本 | 40 | ✅ |
| `/automation/assets` | 测试资产 | 41 | ✅ |
| `/automation/code-review` | 代码审核 | 42 | ✅ |
| `/execution` | 执行计划 | 50 | ✅ |
| `/execution-monitor` | 执行监控 | 51 | ✅ |
| `/evidence/:id` | 证据审核 | 52 | ✅ |
| `/quality/analyses` | 结果分析 | 60 | ✅ |
| `/quality/defects` | 缺陷管理 | 61 | ✅ |
| `/quality/reports` | 测试报告 | 62 | ✅ |
| `/agent/capabilities` | Agent 能力 | 70 | ✅ |
| `/agent/operations` | Agent 运行 | 71 | ✅ |
| `/agent/trace` | Agent 追踪 | 72 | ✅ |
| `/platform/workspaces` | 项目与 Release | 80 | ✅ |
| `/platform/environments` | 环境与资源 | 81 | ✅ |
| `/platform/governance` | 集成与权限 | 82 | ✅ |
| `/help` | 帮助与术语 | — | ✅ |

## 手动测试清单

### 关键用户路径
1. 看板：新建工作项 → 列表出现 → 刷新 → 仍在列表
2. 审核：队列列表 → 点击审核项 → 4 Tab 切换 → 审核决定
3. 规划：策略/计划/用例三页列表浏览与路由跳转
4. 执行：执行计划列表 → 监控页事件流 → 证据页
5. 平台管理：项目/环境/治理三页 + 弹窗交互
6. 移动端：390px 宽度下 6 个关键页面无水平溢出、汉堡抽屉可开关

### 交互状态
- 列表加载态：各列表页进入时数据即渲染（mock 模式同步返回）
- 空态：真实模式后端无数据时显示「暂无数据」空态文案
- 表单提交：看板新建弹窗提交后 toast 提示，列表立即更新
- 错误态：mock 模式不触发网络错误；真实模式 404/异常回落空态

## 已知限制

| 限制 | 说明 | 后续 |
|---|---|---|
| 执行计划创建入口 | 前端按钮跳转 /execution-monitor，createExecutionPlan 调用未绑定表单 | 补充创建弹窗后启用持久化 e2e 第二条 |
| 新建项目（平台管理） | toast 演示，原型 80/02 为真实表单 | 抽 workspace-create 组件 |
| 分派工作项 | 组件内存态 + toast 演示，真实分派待后端 assign endpoint | 后端就绪后切换 |
| 搜索框 | 演示 toast 行为，无实际搜索 | 后续里程碑实现 |
| 通知 | 演示 toast 行为 | 后续里程碑实现 |
| Provider 降级 | mock 模式固定显示 NOMINAL 绿 | 后端 GET /ai/provider/status 就绪后自动切换三态 |
| 后端阻塞接口 | listExecutionPlans、listSourceSnapshots、listKnowledgeEntries、契约域 0 接口 | 后端轨补齐后切换真实 |
| 执行事件流 | 前端 mock 轮询，非真实 WebSocket/SSE | 后端 B2 就绪后切换 |
| 移动端表格 | 宽表格通过 `.table-scroll` 横向滚动，不溢出页面 | 已验收 |

### 已闭环（deep_delivery 修复）

- 新建工作项/新建环境/审核决定/执行计划：mock 提交写入 localStorage 台账，刷新不丢（环境另有页面级 e2e 双验证）
- 加载态：看板/测试计划/环境列表首载渲染骨架（qf-skeleton shimmer）
- 响应式：移动 390px 六页无水平溢出（14 条走查全绿）

## 截图归档

`visual-align/` 下 01-32 共 32 张截图（关键页面原型对齐后采集），每次全量测试自动重采。

## 架构要点

- 数据层：`dataService.ts` 统一出口，页面组件不感知 mock/真实
- 视觉体系：qf-tokens.css（琥珀铜 #D96C1F + 暖石墨）+ qf-components.css（布局/导航/按钮/表单/表格/弹窗）
- 组件库：AppShell（侧栏+顶栏）、Modal、Toast、Icons、ProviderStatusChip（M5 降级状态）
- 响应式：900px 断点侧栏隐藏+topbar 换行，640px 断点 page-head 精简
