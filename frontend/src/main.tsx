import React from "react"
import ReactDOM from "react-dom/client"

import { App } from "./App"
import "./styles/qf-tokens.css"
import "./styles/qf-components.css"
import "./styles/app.css"
import "./styles/artifact-hub.css"

/**
 * 入口（对齐原型视觉体系）：
 * - qf-tokens.css：锻炉琥珀铜 + 暖石墨设计令牌（27 页原型权威源）
 * - qf-components.css：qf 组件库（布局/按钮/表单/表格/徽标/弹窗/toast）
 * - app.css：应用特有补充样式（auth 布局等）
 * 已移除 Fluent UI：界面组件全部按原型自研 qf 体系。
 */

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
