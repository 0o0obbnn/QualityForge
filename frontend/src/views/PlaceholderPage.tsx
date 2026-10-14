import { useParams } from "react-router-dom";

/**
 * 模块占位页（M2 验收「八模块导航骨架可路由，占位页允许」）。
 * 对应原型 20-82 页面的模块入口，具体页面后续里程碑实现。
 */

const MODULE_META: Record<string, { title: string; note: string }> = {
  knowledge: { title: "知识与契约", note: "来源与需求、API 契约、知识条目（原型 20/21/22）" },
  planning: { title: "测试规划与设计", note: "测试策略、测试计划、场景与用例（原型 30/31/32）" },
  automation: { title: "自动化工作台", note: "自动化代码、配套资产（原型 40/41/42）" },
  execution: { title: "测试执行", note: "执行计划、执行监控、证据（原型 50/51/52）" },
  quality: { title: "质量中心", note: "结果分析、Defect、报告与门禁（原型 60/61/62）" },
  agent: { title: "AI Agent 中心", note: "能力注册、运行与评测（原型 70/71/72）" },
  platform: { title: "平台管理", note: "项目与 Release、环境与资源、集成与权限（原型 80/81/82）" },
};

export function PlaceholderPage() {
  const { module } = useParams<{ module: string }>();
  const meta = MODULE_META[module ?? ""] ?? { title: "模块", note: "" };
  return (
    <>
      <div className="page-head">
        <div>
          <h1>{meta.title}</h1>
          <div className="sub">{meta.note}</div>
        </div>
      </div>
      <div className="panel">
        <div className="pbody">
          <div className="empty-note" style={{ border: "none" }}>
            <div className="en-title">模块建设中</div>
            本模块页面将在后续里程碑按原型实现，当前为导航占位页（M2 验收口径允许）。
          </div>
        </div>
      </div>
    </>
  );
}
