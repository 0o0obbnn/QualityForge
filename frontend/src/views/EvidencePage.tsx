import { useNavigate, useParams } from "react-router-dom";
import { evidenceDetail } from "../mock/mockData";

/**
 * 证据审核页（对齐 52-evidence.html + M3 前端轨验收）：
 * ExecutionResult 只追加 + digest 展示 + 人工批准。
 * 断言明细/证据链接/结果元数据/attempt 历史；mock 演示数据，联调后接 listExecutionResults。
 */

const CHECK_ICON: Record<string, React.ReactNode> = {
  pass: (
    <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="m3 8.5 3 3 7-7" /></svg>
  ),
  review: (
    <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8 2.5 13.5 13.5h-11L8 2.5Z" /><path d="M8 7v3M8 12.2v.3" /></svg>
  ),
};

export function EvidencePage() {
  const navigate = useNavigate();
  const { executionTaskId } = useParams<{ executionTaskId: string }>();
  const detail = evidenceDetail;

  return (
    <>
      <div className="page-head">
        <div>
          <div className="flex" style={{ gap: 10 }}>
            <span className={`badge ${detail.status === "FAILED" ? "b-err" : "b-ok"}`}>{detail.status}</span>
            <h1 style={{ fontSize: 20 }}>{executionTaskId ? detail.title : detail.title}</h1>
          </div>
          <div className="sub">ExecutionResult 只追加 · 断言明细与证据 · mock 演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => navigate("/execution")}>← 返回执行监控</button>
        <button className="btn btn-ghost" onClick={() => navigate("/quality")}>创建失败分析</button>
      </div>

      <div className="two-col">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="panel">
            <div className="phead">
              <h2>断言明细</h2>
              <span className="hint">{detail.checks.filter((check) => check.state === "pass").length}/{detail.checks.length} 通过 · {detail.checks.filter((check) => check.state === "review").length} 失败</span>
            </div>
            <div className="pbody">
              <div className="checks">
                {detail.checks.map((check) => (
                  <div key={check.label} className={`check ${check.state}`}>
                    <span className="ic">{CHECK_ICON[check.state] ?? "·"}</span>
                    {check.label}
                    <span className="verdict">{check.verdict}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="phead">
              <h2>证据</h2>
              <span className="hint">只追加 · 脱敏</span>
            </div>
            <div className="pbody">
              <div className="evidence-links">
                {detail.evidenceLinks.map((link) => (
                  <a
                    key={link.label}
                    className="ev-link"
                    href={link.href}
                    onClick={(event) => {
                      event.preventDefault();
                      if (link.href === "/evidence") {
                        // 演示：证据预览弹窗省略，直接提示
                        alert(`证据预览（演示）：${link.label}`);
                      } else {
                        navigate(link.href);
                      }
                    }}
                  >
                    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M4 12.5V3.5h8v9H4Z" /></svg>
                    {link.label}
                  </a>
                ))}
              </div>
              <p className="small muted" style={{ marginTop: 12 }}>
                敏感证据访问受限；人工注释不能修改原始事实（ExecutionResult 只追加）。
              </p>
            </div>
          </div>
        </div>

        <div className="aside-stack">
          <div className="mini-card">
            <h3>结果元数据</h3>
            {detail.metadata.map((row) => (
              <div key={row.k} className="row">
                <span className="k">{row.k}</span>
                <span className="mono">{row.v}</span>
              </div>
            ))}
          </div>
          <div className="mini-card">
            <h3>attempt 历史</h3>
            {detail.attempts.map((attempt) => (
              <div key={attempt.no} className="row">
                <span className="k">{attempt.no}</span>
                <span className="v" style={{ color: "var(--qf-error-500)" }}>{attempt.text}</span>
              </div>
            ))}
            <div className="row">
              <span className="k">规则</span>
              <span className="v muted">重试预算内</span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
