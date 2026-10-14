# QualityForge 组件库规范

## 1. 设计系统基础

组件库基于项目根目录 `qualityforge-ui/colors_and_type.css` 中的 Design Token 构建，遵循以下原则：
- 暗色默认、亮色可选（`.light` 或 `prefers-color-scheme: light`）
- 不使用 Tailwind，使用 CSS 自定义属性 + CSS Modules
- 所有状态颜色与 `docs/01-product/03-术语表Glossary.md` 状态枚举对齐
- AI 可信度可视化作为一等公民嵌入每个相关组件

## 2. 全局布局组件

### 2.1 AppShell（应用外壳）
- **文件**：`partials/project-shell.html`
- **结构**：
  - 顶部固定应用栏（56px 高）
  - 左侧固定边栏（240px 宽）
  - 主内容区（自适应，含安全内边距 24px）
- **可插槽**：`pageTitle`、`activeNavItem`、`mainContent`
- **关键元素**：
  - Workspace 切换器
  - 全局搜索（Cmd/Ctrl + K）
  - Token 预算指示器
  - 用户头像 / 设置入口

### 2.2 SplitPane（分栏面板）
- **用途**：测试设计控制台、运行控制台、RCA 详情等需要左右分栏的页面
- **行为**：可拖拽调整宽度、支持折叠、最小宽度 280px
- **Token 依赖**：`--qf-border`、`--qf-card`、`--qf-radius-md`

### 2.3 PageHeader（页面标题区）
- **结构**：面包屑 + 页面标题 + 全局操作按钮
- **高度**：64px
- **样式**：标题使用 `var(--qf-text-lg)` 加粗，副标题使用 `var(--qf-text-sm)` + `var(--qf-muted-foreground)`

## 3. 通用 UI 组件

### 3.1 Button
| 变体 | 背景 | 文字 | 用途 |
|---|---|---|---|
| Primary | `var(--qf-primary)` | `var(--qf-primary-foreground)` | 主操作：创建、保存、执行 |
| Secondary | `var(--qf-secondary)` | `var(--qf-secondary-foreground)` | 次操作：取消、返回 |
| Ghost | transparent | `var(--qf-foreground)` | 工具栏图标按钮 |
| Danger | `var(--qf-state-error)` | white | 删除、强制停止 |
| AI | `var(--qf-ai)` | white | AI 生成/优化操作 |

- **尺寸**：默认 32px 高，紧凑 28px，大 40px
- **圆角**：`var(--qf-radius-md)`
- **禁用态**：opacity 0.5，cursor not-allowed

### 3.2 Badge（状态徽章）
| 类型 | 背景 | 文字 | 用途 |
|---|---|---|---|
| Pass | `rgba(76,175,80,0.12)` | `var(--qf-state-success)` | Passed、Online、Verified |
| Warn | `rgba(255,152,0,0.12)` | `var(--qf-state-warning)` | Warned、Pass_With_Review、Decaying |
| Fail | `rgba(244,67,54,0.12)` | `var(--qf-state-error)` | Failed、Blocked、Critical |
| Info | `rgba(0,140,255,0.12)` | `var(--qf-state-info)` | Draft、Running、Parsing |
| AI | `rgba(103,58,183,0.12)` | `var(--qf-ai)` | AI 生成、AI 优化 |

### 3.3 Card
- **背景**：`var(--qf-card)`
- **边框**：1px solid `var(--qf-border)`
- **圆角**：`var(--qf-radius-lg)`
- **内边距**：`var(--qf-space-4)`（默认），`var(--qf-space-3)`（紧凑）
- **阴影**：`var(--qf-shadow-sm)`，悬浮时 `var(--qf-shadow-md)`

### 3.4 Table
- **行高**：40px（紧凑模式 32px）
- **表头**：`var(--qf-muted)` 背景，`var(--qf-text-xs)` 大写加粗
- **分隔线**：1px solid `var(--qf-border)`
- **悬浮行**：背景色 `rgba(255,255,255,0.03)`（暗色）
- **选中行**：左边框 2px `var(--qf-primary)`

### 3.5 Form Elements
- **输入框**：高度 32px，背景 `var(--qf-input)`，边框 `var(--qf-border)`，聚焦 ring `var(--qf-ring)`
- **选择器**：同输入框，带下拉箭头
- **Switch**：高度 20px，宽度 36px，active 状态 `var(--qf-primary)`
- **Checkbox/Radio**：16px，选中 `var(--qf-primary)`

## 4. AI 专用组件

### 4.1 ConfidenceBadge（置信度徽章）
- **用途**：仅在存在经批准、版本化校准记录时，展示该策略定义的分档和原始分数；不得用模型自评分替代正确率或审核结论。
- **视觉**：颜色、标签和分界点由适用的AI策略/校准版本提供，组件库不定义通用数值阈值。
- **扩展**：hover显示校准集、策略版本、样本范围、更新时间和限制。
- **未校准态**：只显示“未校准，仅供参考”，使用中性灰色；不显示High/Medium/Low，不用绿色暗示可信，也不能影响自动入库、批准或门禁。

```html
<span class="qf-confidence-badge qf-confidence-uncalibrated">
  未校准，仅供参考
  <span class="qf-confidence-hint" title="没有已批准的校准记录，不得用于自动决策">?</span>
</span>
```

### 4.2 SourceTraceChip（溯源芯片）
- **用途**：展示 AI 生成物的来源，可点击跳转
- **视觉**：小圆角标签，内含来源图标 + 来源名称
- **来源类型**：
  - 需求文档章节
  - Skill 名称（如 `scenario-generator`）
  - Agent 调用链路
  - 历史执行记录
- **交互**：hover 显示摘要 tooltip；点击打开 Source Trace 抽屉或 Agent Trace 页面

### 4.3 AIActionToolbar（AI 操作条）
- **用途**：嵌入表格/表单顶部的 AI 操作入口
- **结构**：
  - 左侧：AI 图标 + 操作名称
  - 中间：可选配置（模型、温度、范围）
  - 右侧：执行按钮
- **示例操作**：生成场景、生成用例、生成断言、优化用例、检查覆盖率

### 4.4 RunProgressBar（执行进度条）
- **用途**：展示测试执行的整体进度
- **分段颜色**：
  - Passed：`var(--qf-state-success)`
  - Failed：`var(--qf-state-error)`
  - Skipped：`var(--qf-neutral-500)`
  - Running：`var(--qf-primary)`
- **信息**：左侧显示完成数/总数，右侧显示耗时与 ETA

### 4.5 LogStream（日志流）
- **用途**：实时展示测试执行日志、Agent Trace 输出
- **样式**：
  - 等宽字体 `var(--qf-font-mono)`
  - 字号 `var(--qf-text-sm)`
  - 行高 1.6
  - 自动滚动到底部
- **高亮**：
  - ERROR：`var(--qf-state-error)`
  - WARN：`var(--qf-state-warning)`
  - INFO：`var(--qf-state-info)`
  - AI 输出：`var(--qf-ai)`
- **交互**：支持暂停/继续、清空、复制、关键字过滤

### 4.6 EvidenceCard（证据卡片）
- **用途**：展示 Source Trace 的详细证据
- **结构**：
  - 标题：来源类型 + 名称
  - 内容：引用原文摘要 / 生成的中间产物
  - 底部：ConfidenceBadge + SourceTraceChip

## 5. 模块专属组件

### 5.1 WorkspaceCard（工作空间卡片）
- **元素**：名称、描述、健康状态、最近更新时间、用例数、执行通过率
- **操作**：进入、设置、删除

### 5.2 RequirementRow（需求文档行）
- **元素**：文档名、类型、解析状态、质量门禁结果、来源、更新时间
- **操作**：查看、重新解析、删除

### 5.3 TestCaseRow（用例行）
- **元素**：ID、名称、优先级、状态、置信度、Source Trace、操作
- **状态**：Draft / Ready / Published / Deprecated
- **操作**：编辑、查看 Source、发布、撤回

### 5.4 TopologyGraph（拓扑图）
- **用途**：测试设计控制台展示需求-场景-用例关系
- **视觉**：节点为卡片，边为贝塞尔曲线，支持缩放与拖拽
- **颜色**：需求节点 `var(--qf-primary)`，场景节点 `var(--qf-ai)`，用例节点 `var(--qf-secondary)`

### 5.5 FailureCluster（失败聚类）
- **用途**：RCA 详情页展示失败分组
- **元素**：聚类名称、失败数、共同特征、AI 根因、置信度
- **交互**：展开查看成员用例，跳转 Agent Trace

### 5.6 AgentTraceTree（Agent 链路树）
- **用途**：Agent Trace 链路回放页
- **结构**：嵌套列表/树，每个节点展示：
  - 工具调用名
  - 输入参数摘要
  - 输出结果摘要
  - 耗时
  - 状态（成功/失败/重试）
- **交互**：点击节点展开详情面板

## 6. 响应式策略

- **桌面优先**：所有 P0 页面针对 1440px 以上宽度设计
- **平板**：边栏可折叠为图标模式，分栏变为上下堆叠
- **移动端**：仅保留查看模式，复杂编辑操作提示“请在桌面端操作”

## 7. 无障碍要求

- 所有交互元素有清晰的 focus 状态
- 状态颜色必须配合图标或文本
- 按钮与链接有描述性 aria-label
- 表格支持键盘导航（Tab / 方向键）
- 支持 `prefers-reduced-motion` 减少动画
