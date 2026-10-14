import { useEffect, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { analysisRows, failureClusters } from "../../mock/mockData";
import { fetchAnalyses } from "../../services/dataService";
import type { Profile } from "../../types";

/**
 * 结果分析页（对齐 60-analyses.html + M4 前端轨）：
 * 分析列表（AI 标签/置信度/状态）+ 失败聚类侧栏 + 关键规则侧栏。
 * mock 演示数据；真实模式接 listResultAnalyses（后端 quality 域已实现，前端待接）。
 */

const CONFIDENCE_COLOR = (confidence: number) =>
  confidence >= 0.8 ? "var(--qf-success-600)" : "var(--qf-warning-600)";

export function AnalysesPage() {
  const navigate = useNavigate();
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [rows, setRows] = useState(analysisRows);

  useEffect(() => {
    let active = true;
    void fetchAnalyses(profile).then((list) => {
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
          <h1>结果分析</h1>
          <div className="sub">ResultAnalysis · 聚类/RCA · AI 推断与执行事实分离 · mock 演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => navigate("/quality/defects")}>失败聚类 (2)</button>
        <button className="btn btn-primary" onClick={() => navigate("/execution-monitor")}>生成分析草稿</button>
      </div>

      <div className="two-col">
        <div className="panel">
          <div className="phead"><h2>分析列表</h2></div>
          <div className="table-scroll">
            <table>
              <thead><tr><th>分析</th><th>版本</th><th>置信</th><th>状态</th></tr></thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} style={{ cursor: "pointer" }} onClick={() => navigate("/quality/defects")}>
                    <td>
                      <div className="t-title"><span className="ai-tag">AI</span>{row.title}</div>
                      <div className="t-sub">{row.id} · {row.ref}</div>
                    </td>
                    <td className="mono">V1</td>
                    <td>
                      <span className="t-num" style={{ color: CONFIDENCE_COLOR(row.confidence), fontWeight: 600 }}>
                        {row.confidence.toFixed(2)}
                      </span>
                    </td>
                    <td>
                      <span className={`status ${row.status === "done" ? "st-done" : "st-review"}`}>
                        <span className="d" />
                        {row.statusLabel}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="empty-note" hidden={rows.length > 0}>
              <div className="en-title">暂无分析</div>执行结果产生后 AI 将生成分析草稿
            </div>
          </div>
        </div>
        <div className="aside-stack">
          {failureClusters.map((cluster) => (
            <div className="mini-card" key={cluster.id}>
              <h3>失败聚类 {cluster.id}</h3>
              <div className="row"><span className="k">成员</span><span className="v">{cluster.members}</span></div>
              <div className="row"><span className="k">指纹</span><span className="mono">{cluster.fingerprint}</span></div>
              <div className="row"><span className="k">算法</span><span className="v muted">{cluster.algorithm}</span></div>
            </div>
          ))}
          <div className="mini-card">
            <h3>关键规则</h3>
            <div className="row"><span className="k">聚类≠Defect</span><span className="v">需人工决定</span></div>
            <div className="row"><span className="k">分析可被纠正</span><span className="v">新版本保留</span></div>
            <div className="row"><span className="k">结果不可反写</span><span className="v">ExecutionResult</span></div>
          </div>
        </div>
      </div>
    </>
  );
}
