import { useNavigate, useParams } from "react-router-dom";
import { traceAuth, traceMeta, traceSteps } from "../../mock/mockData";

/**
 * Agent Trace 页（原型 72-trace.html）
 * 节点决策摘要 · 输入输出摘要 · 不保存隐藏思维链 · 原型演示数据
 */
export function AgentTracePage() {
  const navigate = useNavigate();
  const { runId = "a9f2c1" } = useParams<{ runId: string }>();

  return (
    <>
      <div className="page-head">
        <div>
          <div className="flex">
            <span className="ai-tag">AI</span>
            <h1 style={{ fontSize: "20px" }}>Agent Trace · run {runId}</h1>
          </div>
          <div className="sub">节点决策摘要 · 输入输出摘要 · 不保存隐藏思维链 · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => navigate("/agent/operations")}>
          ← 返回运行列表
        </button>
        <span className="status st-run">
          <span className="d" />
          运行中 · 128s
        </span>
      </div>

      <div className="two-col">
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {traceSteps.map((step) => (
            <div className="panel" key={step.title} style={step.highlight ? { borderColor: "var(--qf-primary)" } : undefined}>
              <div className="pbody">
                <div className="flex" style={{ marginBottom: "10px" }}>
                  {step.done ? (
                    <span className={`badge ${step.badgeClass}`}>{step.badge}</span>
                  ) : (
                    <span className="pulse" />
                  )}
                  <b>{step.title}</b>
                  <span className="small muted" style={{ marginLeft: "auto" }}>
                    {step.time}
                  </span>
                </div>
                <div className="flex" style={{ paddingLeft: "26px" }}>
                  {step.arrow && <span className="badge b-gray">→</span>}
                  <span className="small muted">{step.note}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="aside-stack">
          <div className="mini-card">
            <h2>运行元数据</h2>
            {traceMeta.map((row) => (
              <div className="row" key={row.k}>
                <span className="k">{row.k}</span>
                <span className={row.mono ? "mono" : "v"}>{row.v}</span>
              </div>
            ))}
          </div>
          <div className="mini-card">
            <h3>授权快照</h3>
            {traceAuth.map((row) => (
              <div className="row" key={row.k}>
                <span className="k">{row.k}</span>
                <span
                  className="v"
                  style={
                    row.danger
                      ? { color: "var(--qf-error-500)" }
                      : row.ok
                        ? { color: "var(--qf-success-600)" }
                        : undefined
                  }
                >
                  {row.v}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
