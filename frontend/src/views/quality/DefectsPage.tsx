import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { defectRows } from "../../mock/mockData";
import { fetchDefects } from "../../services/dataService";
import type { Profile } from "../../types";

/**
 * Defect 页（对齐 61-defects.html + M4 前端轨）：
 * Defect 列表（严重度/生命周期/版本/外部同步）+ 严重度筛选。
 * mock 演示数据；真实模式接 listDefects/createDefect（后端 quality 域已实现，前端待接）。
 */

const FILTERS = [
  { key: "all", label: "全部" },
  { key: "严重", label: "严重" },
  { key: "一般", label: "一般" },
  { key: "synced", label: "已同步" },
];

export function DefectsPage() {
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [rows, setRows] = useState(defectRows);

  useEffect(() => {
    let active = true;
    void fetchDefects(profile).then((list) => {
      if (active) setRows(list);
    });
    return () => {
      active = false;
    };
  }, [profile]);

  const [filter, setFilter] = useState("all");
  const filtered =
    filter === "all"
      ? rows
      : filter === "synced"
        ? rows.filter((row) => row.sync.includes("已同步"))
        : rows.filter((row) => row.severity === filter);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Defect</h1>
          <div className="sub">稳定根 + 不可变版本 · 外部同步逐次批准 · mock 演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => { /* 外部同步弹窗 */ }}>外部同步</button>
      </div>

      <div className="filters">
        {FILTERS.map((item) => (
          <button key={item.key} className={`chip${filter === item.key ? " on" : ""}`} onClick={() => setFilter(item.key)}>
            {item.label}
          </button>
        ))}
        <span className="spacer" />
        <span className="small muted">按严重度筛选</span>
      </div>

      <div className="panel">
        <div className="phead"><h2>Defect 列表</h2></div>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Defect</th><th>严重度</th><th>生命周期</th><th>版本</th><th>外部同步</th></tr></thead>
            <tbody>
              {filtered.map((row) => (
                <tr key={row.id}>
                  <td>
                    <div className="t-title">{row.title}</div>
                    <div className="t-sub">{row.id} · {row.sub}</div>
                  </td>
                  <td><span className={`badge ${row.severity === "严重" ? "b-err" : "b-warn"}`}>{row.severity}</span></td>
                  <td><span className={`status ${row.lifecycleClass}`}><span className="d" />{row.lifecycle}</span></td>
                  <td className="mono">{row.version}</td>
                  <td><span className={`badge ${row.syncClass}`}>{row.sync}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="empty-note" hidden={filtered.length > 0}>
            <div className="en-title">暂无 Defect</div>
          </div>
        </div>
      </div>
    </>
  );
}
