import { metricsDashboard } from "../../mock/mockData";

/**
 * 视图 7 · 管理视图（§5.5.11 指标：周期、吞吐、在制品、审核积压、返工和 AI 采用率）。
 * 对齐原型 62-reports.html 的 KPI 卡 + 口径提示；指标必须基于事件流计算（§5.5.11），
 * 本页为演示数据，联调后接统计接口。
 */

export function MetricsView() {
  return (
    <>
      <div className="grid g4">
        {metricsDashboard.kpis.map((kpi) => (
          <div className="kpi" key={kpi.label}>
            <div className="label">{kpi.label}</div>
            <div className={`value ${kpi.tone}`}>
              <b>{kpi.value}</b>
            </div>
            <div className="note">{kpi.note}</div>
          </div>
        ))}
      </div>

      <div className="grid g2" style={{ marginTop: 16 }}>
        {metricsDashboard.distribution.map((dist) => (
          <div className="panel" key={dist.name}>
            <div className="phead">
              <h2>{dist.name}</h2>
            </div>
            <div className="pbody">
              {dist.rows.map(([quantile, value]) => (
                <div className="cov-row" key={quantile} style={{ marginBottom: 10 }}>
                  <div className="top">
                    <span className="name">{quantile}</span>
                    <span className="val">{value}</span>
                  </div>
                  <div className="bar" style={{ height: 6 }}>
                    <i
                      style={{
                        width: quantile === "p50" ? "35%" : quantile === "p90" ? "72%" : "96%",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div
        className="flex mt-4"
        style={{ fontSize: 12.5, color: "var(--qf-muted-foreground)", background: "var(--qf-secondary-surface)", borderRadius: 8, padding: "8px 12px" }}
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" style={{ color: "var(--qf-warning-500)", flex: "none" }}>
          <path d="M8 2.5 13.5 13.5h-11L8 2.5Z" />
          <path d="M8 7v3M8 12.2v.3" />
        </svg>
        {metricsDashboard.note}
      </div>
    </>
  );
}
