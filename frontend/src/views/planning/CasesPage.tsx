import { useEffect, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { caseCoverage, caseRows, caseStages } from "../../mock/mockData";
import { fetchCases } from "../../services/dataService";
import type { Profile } from "../../types";

/**
 * 场景与用例页（对齐 32-cases.html + Sprint 1 T3）：
 * 流程阶段条 + DesignTestCase 草稿列表 + 覆盖分析。
 * mock 演示数据；真实模式接 listTestCases/listTestCaseVersions（T4）。
 */

const STAGE_STATE_CLASS: Record<string, string> = {
  done: "done",
  active: "active-now",
  wait: "wait",
};

export function CasesPage() {
  const navigate = useNavigate();
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [rows, setRows] = useState(caseRows);

  useEffect(() => {
    let active = true;
    void fetchCases(profile).then((list) => {
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
          <h1>场景与用例</h1>
          <div className="sub">TestingIR → 场景树 → DesignTestCase 草稿 → 人工审核迁移为 TestCaseVersion · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => navigate("/knowledge/sources")}>TestingIR</button>
        <button className="btn btn-primary" onClick={() => navigate("/reviews")}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M8 3v10M3 8h10" /></svg>
          生成用例草稿
        </button>
      </div>

      <div className="stage" style={{ marginBottom: 18 }}>
        {caseStages.map((stage, index) => (
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

      <div className="two-col">
        <div className="panel">
          <div className="phead"><h2>DesignTestCase 草稿</h2><span className="hint">批准后迁移为正式 TestCaseVersion</span></div>
          <div className="table-scroll">
            <table>
              <thead><tr><th>用例</th><th>优先级</th><th>状态</th><th>覆盖</th></tr></thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} style={{ cursor: "pointer" }} onClick={() => navigate("/reviews")}>
                    <td>
                      <div className="tid">{row.id}</div>
                      <div className="t-title"><span className="ai-tag">AI</span>{row.title}</div>
                      <div className="t-sub">{row.sub}</div>
                    </td>
                    <td><span className={`pri p${row.pri.slice(1)}`}>{row.pri}</span></td>
                    <td><span className={`status ${row.statusClass}`}><span className="d" />{row.status}</span></td>
                    <td><span className={`badge ${row.coverClass}`}>{row.cover}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="pagination">
              <span className="pg-info">共 66 条 · 第 1/11 页</span>
              <button disabled>‹</button><button className="on">1</button><button>2</button><button>3</button><button>›</button>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="phead"><h2>覆盖分析</h2><span className="hint">分子 / 分母透明</span></div>
          <div className="pbody">
            {caseCoverage.map((row) => (
              <div className="cov-row" key={row.k} style={{ marginBottom: 12 }}>
                <div className="top">
                  <span className="name">{row.k}</span>
                  <span className="val">{row.v}</span>
                </div>
                <div className={`bar${row.ok ? " ok" : ""}`}>
                  <i style={{ width: `${row.pct}%` }} />
                </div>
              </div>
            ))}
            <p className="small muted">
              STALE 标记：契约升级后待重评的用例不计入覆盖分子；缺口项提示场景待补充。
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
