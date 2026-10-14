# QualityForge UI 原型 · 运行说明

> 版本: V1 · 2026-08-12 · 全部页面与弹窗的可点击高保真原型
> 设计体系: 锻炉琥珀铜 × 暖石墨(禁蓝紫) · Build 呼吸感 × 瑞士网格克制风

## 一、如何运行

**无需安装依赖**:所有页面为自包含 HTML + 共享静态资源,双击打开或用任意静态服务器均可。

```bash
# 方式 1: 直接双击 01-login.html 打开(推荐入口)
# 方式 2: 静态服务器
cd deliverables/2026-08-12/prototype
python3 -m http.server 8080
# 浏览器访问 http://localhost:8080/01-login.html
```

**入口建议**:`01-login.html`(登录)→ `02-workspace-create.html`(创建项目)→ `10-board.html`(工作看板,平台首页)。

## 二、文件结构

```
prototype/
├── assets/
│   ├── qf-tokens.css        # 设计 token(颜色/字体/间距/圆角/阴影,禁蓝紫)
│   ├── qf-components.css    # 组件库(按钮/表单/表格/徽标/弹窗/toast/状态)
│   └── qf-shell.js          # 交互脚本(弹窗/Toast/localStorage/表单校验)
├── 01-login.html            # 登录(表单校验 + 注册/协议弹窗 + 加载反馈)
├── 02-workspace-create.html # 创建项目(表单 → localStorage 持久化)
├── 10-board.html            # 任务看板(平台首页: 筛选/视图/新建工作项弹窗)
├── 11-reviews.html          # 待我审核(审核包: Diff/来源/检查/证据 + 批准/退回/拒绝)
├── 12-workitem.html         # 工作项详情(AI 运行面板/事件时间线)
├── 20-sources.html          # 来源与需求(导入/快照/冲突裁决)
├── 21-api-contracts.html    # API 契约(版本/Operation/基线/漂移)
├── 22-knowledge.html        # 知识库(检索/候选治理/条目发布)
├── 30-strategies.html       # 测试策略
├── 31-plans.html            # 测试计划(里程碑 DAG)
├── 32-cases.html            # 场景与用例(草稿/覆盖分析/图表)
├── 40-scripts.html          # 自动化工作台(脚本/绑定/检查)
├── 41-code-review.html      # 代码审核(代码 Diff/检查/批准)
├── 42-assets.html           # 配套资产(Locator/Mock/数据/视觉基线)
├── 50-execution-plans.html  # 执行计划(版本冻结)
├── 51-execution-monitor.html# 执行监控(任务/实时流/错误分类)
├── 52-evidence.html         # 结果与证据(断言明细/证据预览)
├── 60-analyses.html         # 结果分析(聚类/RCA)
├── 61-defects.html          # Defect(外部同步确认)
├── 62-reports.html          # 报告与门禁(签署/分母透明)
├── 70-capabilities.html     # 能力注册(Skill/Agent/Prompt/Workflow)
├── 71-operations.html       # 运行与评测(Session/Eval/成本)
├── 72-trace.html            # Agent Trace 回放
├── 80-workspaces.html       # 项目与 Release
├── 81-environments.html     # 环境与资源(Secret 引用/Runner)
├── 82-governance.html       # 集成与权限(RBAC/审核策略/审计)
└── 99-modals.html           # 弹窗体系规范(10 类弹窗全部实例)
```

## 三、主流程(可点击路径)

1. **登录 → 工作台**: `01-login.html` → 提交 → `10-board.html`
2. **创建项目**: `02-workspace-create.html` → 提交 → `10-board.html`(项目出现在 `80-workspaces.html` 与顶栏切换列表,localStorage 持久化)
3. **审核链**: `10-board.html` 待审核行 → `11-reviews.html`(批准/退回/拒绝弹窗)→ 详情链接回策略/契约/知识页
4. **设计链**: `30-strategies.html` → `31-plans.html` → `32-cases.html` → 审核 → `50-execution-plans.html`
5. **执行链**: `50-execution-plans.html` → `51-execution-monitor.html` → `52-evidence.html` → `60-analyses.html`
6. **缺陷链**: `60-analyses.html` → `61-defects.html` → 外部同步确认弹窗
7. **报告链**: `62-reports.html` → 签署弹窗
8. **AI 治理链**: `70-capabilities.html` → `71-operations.html` → `72-trace.html`

## 四、交互与持久化说明

| 交互 | 实现 | 验证方式 |
|---|---|---|
| 弹窗开关 | qf-shell.js(ESC / 遮罩 / × 三态关闭) | 任意「实例」按钮 |
| 表单校验 | 必填/邮箱/模式,blur 后提示,错误可恢复 | 空提交表单看错误提示 |
| 新建工作项 | localStorage 持久化(`qf.items`) | 10-board 新建 → 刷新 → 顶部出现「我创建的」 |
| 创建项目 | localStorage 持久化(`qf.workspaces`) | 02 提交 → 刷新 → 80-workspaces 出现本地项目 |
| 登录会话 | localStorage 持久化(`qf.session`) | 01 登录 → 10-board 头像显示用户名 |
| Toast 反馈 | 成功/失败/信息三态 | 各操作按钮 |

原型层用 localStorage 模拟持久化;真实后端联调属开发阶段(项目后端骨架已就绪: `backend/` FastAPI)。

## 五、修改指南

| 想改什么 | 改哪里 |
|---|---|
| 品牌色/字体/间距/圆角 | `assets/qf-tokens.css`(全站一处生效) |
| 按钮/表单/表格/弹窗组件样式 | `assets/qf-components.css` |
| 弹窗交互/存储逻辑 | `assets/qf-shell.js` |
| 页面文案/表格数据 | 各页面 HTML 的 `<tbody>` 与正文(标注「原型演示数据」处) |
| 侧栏导航 | 每个页面 `<aside class="sidebar">`(保持 8 模块一致) |
| 新增页面 | 复制任一页面骨架,改 `<body data-page>` 与 `<main>` 内容 |

## 六、设计约束

- 禁蓝紫: 全体系色相避开 hue 190-320°,含中性色(暖石墨)
- 复验: `python3 tools/verify_palette.py deliverables/2026-08-12/prototype`
- 响应式: 桌面(>900px 侧栏+主区) / 平板 / 移动(<900px 隐藏侧栏,表格横向滚动)
- 无障碍: 语义标签、:focus-visible 焦点环、弹窗 role=dialog + aria-modal、错误 role 语义、对比度 ≥4.5:1
