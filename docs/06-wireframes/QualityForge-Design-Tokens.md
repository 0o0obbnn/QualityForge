# QualityForge Design Tokens

Design Tokens 定义文件：`qualityforge-ui/colors_and_type.css`

## 1. 色彩体系

### 1.1 品牌主色阶（Brand Primary Scale）
单一品牌色调，用于主按钮、链接、当前模块高亮。

| Token | 值 |
|---|---|
| `--qf-primary-50` | `#e6f4ff` |
| `--qf-primary-100` | `#b3e0ff` |
| `--qf-primary-200` | `#80ccff` |
| `--qf-primary-300` | `#4db8ff` |
| `--qf-primary-400` | `#1aa3ff` |
| `--qf-primary-500` | `#008cff` |
| `--qf-primary-600` | `#0070cc` |
| `--qf-primary-700` | `#005499` |
| `--qf-primary-800` | `#003866` |
| `--qf-primary-900` | `#001c33` |

### 1.2 中性色阶（Neutral Scale）
用于背景、表面、文字、边框。

| Token | 值 |
|---|---|
| `--qf-neutral-0` | `#ffffff` |
| `--qf-neutral-50` | `#f8fafc` |
| `--qf-neutral-100` | `#f1f5f9` |
| `--qf-neutral-200` | `#e2e8f0` |
| `--qf-neutral-300` | `#cbd5e1` |
| `--qf-neutral-400` | `#94a3b8` |
| `--qf-neutral-500` | `#64748b` |
| `--qf-neutral-600` | `#475569` |
| `--qf-neutral-700` | `#334155` |
| `--qf-neutral-800` | `#1e293b` |
| `--qf-neutral-900` | `#0f172a` |
| `--qf-neutral-950` | `#020617` |

### 1.3 语义状态色（Semantic State Colors）
与 `docs/01-product/03-术语表Glossary.md` 状态枚举对应。

| Token | 值 | 用途 |
|---|---|---|
| `--qf-state-success` | `#4caf50` | Passed、Online、Verified |
| `--qf-state-success-dark` | `#2e7d32` | 亮色模式下的成功色 |
| `--qf-state-warning` | `#ff9800` | Warned、Decaying、Pass_With_Review |
| `--qf-state-warning-dark` | `#ed6c02` | 亮色模式下的警告色 |
| `--qf-state-error` | `#f44336` | Failed、Blocked、Critical |
| `--qf-state-error-dark` | `#d32f2f` | 亮色模式下的错误色 |
| `--qf-state-info` | `#008cff` | Draft、Running、Parsing |
| `--qf-state-info-dark` | `#0066cc` | 亮色模式下的信息色 |

### 1.4 AI 强调色
| Token | 值 | 用途 |
|---|---|---|
| `--qf-ai` | `#673ab7` | AI 生成/优化按钮、AI 标签、置信度条 |
| `--qf-ai-dark` | `#512da8` | 亮色模式下的 AI 强调色 |

### 1.5 主题色（Theme-aware Aliases）
暗色为默认主题，亮色通过 `.light` 类或媒体查询覆盖。

| Token | 暗色值 | 亮色值 |
|---|---|---|
| `--qf-background` | `var(--qf-neutral-900)` | `var(--qf-neutral-100)` |
| `--qf-foreground` | `var(--qf-neutral-50)` | `var(--qf-neutral-950)` |
| `--qf-card` | `var(--qf-neutral-800)` | `var(--qf-neutral-0)` |
| `--qf-card-foreground` | `var(--qf-neutral-50)` | `var(--qf-neutral-950)` |
| `--qf-popover` | `var(--qf-neutral-800)` | `var(--qf-neutral-0)` |
| `--qf-popover-foreground` | `var(--qf-neutral-50)` | `var(--qf-neutral-950)` |
| `--qf-primary` | `var(--qf-primary-500)` | `var(--qf-primary-600)` |
| `--qf-primary-foreground` | `var(--qf-neutral-0)` | `var(--qf-neutral-0)` |
| `--qf-secondary` | `var(--qf-neutral-700)` | `var(--qf-neutral-200)` |
| `--qf-secondary-foreground` | `var(--qf-neutral-50)` | `var(--qf-neutral-900)` |
| `--qf-muted` | `var(--qf-neutral-800)` | `var(--qf-neutral-200)` |
| `--qf-muted-foreground` | `var(--qf-neutral-400)` | `var(--qf-neutral-600)` |
| `--qf-border` | `var(--qf-neutral-700)` | `var(--qf-neutral-300)` |
| `--qf-input` | `var(--qf-neutral-700)` | `var(--qf-neutral-300)` |
| `--qf-ring` | `var(--qf-primary-500)` | `var(--qf-primary-600)` |

### 1.6 兼容别名（Legacy Aliases）
用于 `apply-html-head-contract.mjs` 等工具读取：

| Token | 映射 |
|---|---|
| `--color-background` | `var(--qf-background)` |
| `--color-foreground` | `var(--qf-foreground)` |
| `--color-card` | `var(--qf-card)` |
| `--color-card-foreground` | `var(--qf-card-foreground)` |
| `--color-popover` | `var(--qf-popover)` |
| `--color-popover-foreground` | `var(--qf-popover-foreground)` |
| `--color-primary` | `var(--qf-primary)` |
| `--color-primary-foreground` | `var(--qf-primary-foreground)` |
| `--color-secondary` | `var(--qf-secondary)` |
| `--color-secondary-foreground` | `var(--qf-secondary-foreground)` |
| `--color-muted` | `var(--qf-muted)` |
| `--color-muted-foreground` | `var(--qf-muted-foreground)` |
| `--color-border` | `var(--qf-border)` |
| `--color-input` | `var(--qf-input)` |
| `--color-ring` | `var(--qf-ring)` |
| `--radius-small` | `var(--qf-radius-sm)` |
| `--radius-medium` | `var(--qf-radius-md)` |
| `--radius-large` | `var(--qf-radius-lg)` |

## 2. 圆角系统

| Token | 值 | 用途 |
|---|---|---|
| `--qf-radius-sm` | `4px` | 小标签、输入框 |
| `--qf-radius-md` | `8px` | 按钮、卡片、徽章 |
| `--qf-radius-lg` | `12px` | 大卡片、弹窗 |
| `--qf-radius-xl` | `16px` | 页面级容器、Hero 卡片 |
| `--qf-radius-full` | `9999px` | 胶囊、头像 |

## 3. 间距系统

| Token | 值 |
|---|---|
| `--qf-space-1` | `4px` |
| `--qf-space-2` | `8px` |
| `--qf-space-3` | `12px` |
| `--qf-space-4` | `16px` |
| `--qf-space-5` | `20px` |
| `--qf-space-6` | `24px` |
| `--qf-space-8` | `32px` |
| `--qf-space-10` | `40px` |
| `--qf-space-12` | `48px` |

## 4. 字体与排版

### 4.1 字体族
| Token | 值 |
|---|---|
| `--qf-font-ui` | `"Inter", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, sans-serif` |
| `--qf-font-mono` | `"JetBrains Mono", "SF Mono", "Fira Code", Menlo, Consolas, monospace` |

### 4.2 字号
| Token | 值 | 用途 |
|---|---|---|
| `--qf-text-xs` | `12px` | 辅助文字、表头、标签 |
| `--qf-text-sm` | `13px` | 正文、日志、表格内容 |
| `--qf-text-base` | `14px` | 默认正文 |
| `--qf-text-md` | `16px` | 小标题、按钮 |
| `--qf-text-lg` | `20px` | 页面标题 |
| `--qf-text-xl` | `24px` | 数据大屏大数字 |

### 4.3 字重
| Token | 值 |
|---|---|
| `--qf-weight-regular` | `400` |
| `--qf-weight-medium` | `500` |
| `--qf-weight-semibold` | `600` |
| `--qf-weight-bold` | `700` |

### 4.4 行高
| Token | 值 | 用途 |
|---|---|---|
| `--qf-leading-none` | `1` | 大数字 |
| `--qf-leading-tight` | `1.25` | 标题 |
| `--qf-leading-snug` | `1.4` | 中等长度文本 |
| `--qf-leading-normal` | `1.6` | 正文、日志 |

### 4.5 排版工具类
| 类名 | 说明 |
|---|---|
| `.qf-text-xs` ~ `.qf-text-xl` | 字号 + 默认行高 |
| `.qf-font-ui` | UI 字体 |
| `.qf-font-mono` | 等宽字体 |
| `.qf-regular` ~ `.qf-bold` | 字重 |

## 5. 阴影系统

| Token | 值 | 用途 |
|---|---|---|
| `--qf-shadow-sm` | `0 1px 2px rgba(0, 0, 0, 0.05)` | 卡片默认 |
| `--qf-shadow-md` | `0 4px 6px rgba(0, 0, 0, 0.05)` | 卡片悬浮 |
| `--qf-shadow-lg` | `0 10px 15px rgba(0, 0, 0, 0.05)` | 下拉菜单 |
| `--qf-shadow-float` | `0 20px 25px rgba(0, 0, 0, 0.15)` | 弹窗、浮层 |

## 6. 动画与过渡

| Token | 值 | 用途 |
|---|---|---|
| `--qf-transition-fast` | `120ms ease` | 按钮、徽章状态变化 |
| `--qf-transition-base` | `200ms ease` | 卡片悬浮、面板展开 |

## 7. 状态颜色工具类

| 类名 | 说明 |
|---|---|
| `.qf-status-pass` | 成功文字色 |
| `.qf-status-warn` | 警告文字色 |
| `.qf-status-fail` | 错误文字色 |
| `.qf-status-info` | 信息文字色 |
| `.qf-status-ai` | AI 文字色 |
| `.qf-bg-pass` | 成功背景色（12% 透明度） |
| `.qf-bg-warn` | 警告背景色（12% 透明度） |
| `.qf-bg-fail` | 错误背景色（12% 透明度） |
| `.qf-bg-ai` | AI 背景色（12% 透明度） |

## 8. 主题切换

默认暗色，通过以下方式切换到亮色：
- 在 `html` 或任意父元素上添加 `.light`
- 设置 `data-theme="light"`
- 系统 `prefers-color-scheme: light` 且未显式设置暗色

所有组件必须优先使用 `--qf-background`、`--qf-foreground` 等主题别名，而非直接使用 `--qf-neutral-*` 或 `--qf-primary-*` 固定色阶。
