import { useNavigate } from "react-router-dom";
import { codeReviewDetail } from "../../mock/mockData";

/**
 * 代码审核页（对齐 41-code-review.html + Sprint 2 T7）：
 * 代码 Diff（V1→V2）+ 检查结果（阻断项不可人工放行）+ 审核信息侧栏。
 */

const CHECK_ICON: Record<string, React.ReactNode> = {
  pass: (
    <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="m3 8.5 3 3 7-7" /></svg>
  ),
  review: (
    <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8 2.5 13.5 13.5h-11L8 2.5Z" /><path d="M8 7v3M8 12.2v.3" /></svg>
  ),
};

export function CodeReviewPage() {
  const navigate = useNavigate();
  return (
    <>
      <div className="page-head">
        <div>
          <div className="flex" style={{ gap: 10 }}>
            <span className="type-tag">{codeReviewDetail.type}</span>
            <h1 style={{ fontSize: 20 }}>{codeReviewDetail.title}</h1>
          </div>
          <div className="sub">{codeReviewDetail.status} · AI 生成 + 人工代码审核 · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <span className="status st-review"><span className="d" />待代码审核</span>
        <button className="btn btn-ghost" onClick={() => navigate("/automation/scripts")}>← 返回工作台</button>
      </div>

      <div className="two-col">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="panel">
            <div className="phead"><h2>代码 Diff</h2><span className="hint">V1 → V2 · AI 生成</span></div>
            <div className="pbody" style={{ padding: 0 }}>
              <div className="code-pane" style={{ borderRadius: 0 }}>
                {codeReviewDetail.diffLines.map((line, index) => (
                  <div key={index} style={{ color: line.color }}>{line.text}</div>
                ))}
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="phead"><h2>检查结果</h2><span className="hint">阻断项不可人工放行</span></div>
            <div className="pbody">
              <div className="checks">
                {codeReviewDetail.checks.map((check) => (
                  <div key={check.label} className={`check ${check.state}`}>
                    <span className="ic">{CHECK_ICON[check.state] ?? "·"}</span>
                    {check.label}
                    <span className="verdict">{check.verdict}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="aside-stack">
          <div className="mini-card">
            <h3>审核信息</h3>
            {codeReviewDetail.reviewInfo.map((row) => (
              <div key={row.k} className="row">
                <span className="k">{row.k}</span>
                <span className="mono">{row.v}</span>
              </div>
            ))}
          </div>
          <div className="mini-card">
            <h3>决定</h3>
            <div className="flex" style={{ gap: 8, flexWrap: "wrap" }}>
              <button className="btn btn-primary btn-sm" onClick={() => navigate("/reviews")}>批准 V2</button>
              <button className="btn btn-ghost btn-sm" onClick={() => navigate("/reviews")}>退回修改</button>
            </div>
            <p className="small muted" style={{ marginTop: 10 }}>检查 PASS 不替代代码批准；受控试跑 REVIEW 项需在 staging 授权后复跑。</p>
          </div>
        </div>
      </div>
    </>
  );
}