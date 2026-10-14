import { useEffect, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { strategyPreview, strategyRows } from "../../mock/mockData";
import { fetchStrategies } from "../../services/dataService";
import type { Profile } from "../../types";

/**
 * 测试策略页（对齐 30-strategies.html + Sprint 1 T1）：
 * 策略列表 + 策略结构预览。mock 演示数据；真实模式接 listTestStrategies（T4）。
 */

export function StrategiesPage() {
  const navigate = useNavigate();
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [rows, setRows] = useState(strategyRows);

  useEffect(() => {
    let active = true;
    void fetchStrategies(profile).then((list) => {
      if (active) setRows(list);
    });
    return () => {
      active = false;
    };
  }, [profile]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>测试策略</h1>
          <div className="sub">TestStrategy · 范围/风险/方法/准入退出 · AI 草稿 + 人工审核 · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => navigate("/planning/plans")}>测试计划</button>
        <button className="btn btn-ghost" onClick={() => navigate("/planning/cases")}>场景与用例</button>
        <button className="btn btn-primary" onClick={() => navigate("/reviews")}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M8 3v10M3 8h10" /></svg>
          生成策略草稿
        </button>
      </div>

      <div className="panel">
        <div className="phead"><h2>策略列表</h2><span className="hint">Release R-2026.08</span></div>
        <div className="table-scroll">
          <table>
            <thead><tr><th>策略</th><th>版本</th><th>范围</th><th>风险点</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} style={{ cursor: "pointer" }} onClick={() => navigate("/reviews")}>
                  <td>
                    <div className="t-title">{row.title}</div>
                    <div className="t-sub mono">{row.id}</div>
                  </td>
                  <td className="mono">{row.version}</td>
                  <td>{row.scope}</td>
                  <td className="t-num">{row.risks}</td>
                  <td><span className={`status ${row.statusClass}`}><span className="d" />{row.status}</span></td>
                  <td>
                    {row.action === "审核" ? (
                      <button className="btn btn-sm btn-ghost" onClick={(event) => { event.stopPropagation(); navigate("/reviews"); }}>审核</button>
                    ) : (
                      <span className="badge b-ok">{row.action}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="empty-note" hidden={rows.length > 0}>
            <div className="en-title">暂无策略</div>点击「生成策略草稿」让 AI 基于来源基线起草
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>策略结构预览 · 结算中心主测试策略 V2</h2>
        {strategyPreview.map((row) => (
          <div className="cov-row" key={row.k} style={{ marginBottom: 10 }}>
            <div className="top">
              <span className="name">{row.k}</span>
              <span className="val">{row.v}</span>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
