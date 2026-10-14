import { useEffect, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { planStages } from "../../mock/mockData";
import { fetchPlans } from "../../services/dataService";
import type { PlanRow } from "../../services/dataService";
import { useToast } from "../../app/Toast";
import type { Profile } from "../../types";

/**
 * 测试计划页（对齐 31-plans.html + Sprint 1 T2）：
 * 计划列表 + 里程碑 DAG 预览。mock 演示数据；真实模式接 listTestPlans（T4）。
 */

const STAGE_STATE_CLASS: Record<string, string> = {
  done: "done",
  active: "active-now",
  wait: "wait",
};

export function PlansPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [rows, setRows] = useState<PlanRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void fetchPlans(profile)
      .then((list) => {
        if (active) setRows(list);
      })
      .catch(() => {
        if (active) toast("计划列表加载失败", "err");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [profile, toast]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>测试计划</h1>
          <div className="sub">TestPlan · 里程碑/资源/依赖/验收准则 · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => navigate("/planning/strategies")}>测试策略</button>
        <button className="btn btn-ghost" onClick={() => navigate("/planning/cases")}>场景与用例</button>
        <button className="btn btn-primary" onClick={() => navigate("/board")}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M8 3v10M3 8h10" /></svg>
          新建计划
        </button>
      </div>

      <div className="panel">
        <div className="phead"><h2>计划列表</h2><span className="hint">R-2026.08</span></div>
        <div className="table-scroll">
          <table>
            <thead><tr><th>计划</th><th>版本</th><th>生命周期</th><th>里程碑</th><th>状态</th></tr></thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={5}>
                    <div className="table-loading">
                      <div className="row"><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /></div>
                      <div className="row"><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /></div>
                    </div>
                  </td>
                </tr>
              )}
              {!loading &&
                rows.map((row) => (
                  <tr key={row.id} style={{ cursor: "pointer" }} onClick={() => navigate("/board")}>
                    <td>
                      <div className="t-title">{row.title}</div>
                      <div className="t-sub mono">{row.id} · {row.depends}</div>
                    </td>
                    <td className="mono">{row.version}</td>
                    <td><span className={`status ${row.lifecycleClass}`}><span className="d" />{row.lifecycle}</span></td>
                    <td>{row.milestones}</td>
                    <td><span className={`status ${row.statusClass}`}><span className="d" />{row.status}</span></td>
                  </tr>
                ))}
            </tbody>
          </table>
          <div className="empty-note" hidden={loading || rows.length > 0}>
            <div className="en-title">暂无测试计划</div>点击「新建计划」创建
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>里程碑编排 (DAG 预览)</h2>
        <div className="stage">
          {planStages.map((stage, index) => (
            <span key={stage.no} style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
              {index > 0 && <span className="stage-arrow">→</span>}
              <div className={`stage-item ${STAGE_STATE_CLASS[stage.state] ?? "wait"}`}>
                <div className="no">{stage.no}</div>
                <div className="nm">{stage.name}</div>
                <div className="st"><span className="d" />{stage.note}</div>
              </div>
            </span>
          ))}
        </div>
      </div>
    </>
  );
}
