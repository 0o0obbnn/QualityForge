import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { reportDetail } from "../../mock/mockData";
import { fetchReport } from "../../services/dataService";
import type { Profile } from "../../types";

/**
 * 报告与门禁页（对齐 62-reports.html + M4 前端轨）：
 * KPI 3 卡 + 范围快照/风险摘要/结论 + 质量门禁建议。
 * mock 演示数据；真实模式接 listTestReports（后端 quality 域已实现，前端待接）。
 */

const GATE_ICON: Record<string, React.ReactNode> = {
  pass: (
    <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="m3 8.5 3 3 7-7" /></svg>
  ),
  review: (
    <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8 2.5 13.5 13.5h-11L8 2.5Z" /><path d="M8 7v3M8 12.2v.3" /></svg>
  ),
};

export function ReportsPage() {
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [detail, setDetail] = useState(reportDetail);

  useEffect(() => {
    let active = true;
    void fetchReport(profile).then((data) => {
      if (active) setDetail(data);
    });
    return () => {
      active = false;
    };
  }, [profile]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>报告与门禁</h1>
          <div className="sub">TestReport 签署 · 分母透明 · 质量门禁 · mock 演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => { /* 质量门禁弹窗 */ }}>质量门禁</button>
        <button className="btn btn-primary" onClick={() => { /* 签署弹窗 */ }}>签署报告</button>
      </div>

      <div className="panel">
        <div className="phead">
          <h2>{detail.title}</h2>
          <span className="hint">{detail.ref}</span>
        </div>
        <div className="pbody">
          <div className="grid g3">
            {detail.kpis.map((kpi) => (
              <div className="kpi" key={kpi.label}>
                <div className="label">{kpi.label}</div>
                <div className={`value ${kpi.tone}`}>
                  <b>{kpi.value}</b>
                  {kpi.sub && <span style={{ fontSize: 14 }}>{kpi.sub}</span>}
                </div>
                <div className="note">{kpi.note}</div>
              </div>
            ))}
          </div>
          {detail.summary.map((row) => (
            <div className="cov-row" key={row.k} style={{ marginTop: 14 }}>
              <div className="top">
                <span className="name">{row.k}</span>
                <span className="val">{row.v}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h2 style={{ fontSize: 14, marginBottom: 10 }}>质量门禁建议</h2>
        <div className="checks">
          {detail.gates.map((gate) => (
            <div key={gate.label} className={`check ${gate.state}`}>
              <span className="ic">{GATE_ICON[gate.state] ?? "·"}</span>
              {gate.label}
              <span className="verdict">{gate.verdict}</span>
            </div>
          ))}
        </div>
        <p className="small muted" style={{ marginTop: 12 }}>
          AI 建议不能自动放行/阻断发布；豁免需人工授权并进入报告。
        </p>
      </div>
    </>
  );
}
