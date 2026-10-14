import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { sourceSnapshots, requirementDocs, sourceConflicts } from "../../mock/mockData";
import { fetchRequirementDocs, fetchSourceSnapshots } from "../../services/dataService";
import type { Profile } from "../../types";

/**
 * 来源与需求页（对齐 20-sources.html）：
 * 三 Tab：来源快照 / 需求文档 / 冲突。mock 演示数据；
 * 真实模式接 listRequirementDocuments（后端已实现）。
 */

const TABS = [
  { key: "sources", label: "来源快照" },
  { key: "reqs", label: "需求文档" },
  { key: "conflicts", label: "冲突 (2)" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export function SourcesPage() {
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [tab, setTab] = useState<TabKey>("sources");
  const [reqRows, setReqRows] = useState(requirementDocs);
  const [snapRows, setSnapRows] = useState(sourceSnapshots);

  useEffect(() => {
    let active = true;
    void fetchRequirementDocs(profile).then((list) => {
      if (active) setReqRows(list);
    });
    void fetchSourceSnapshots(profile).then((list) => {
      if (active) setSnapRows(list);
    });
    return () => {
      active = false;
    };
  }, [profile]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>来源与需求</h1>
          <div className="sub">导入来源 → 固化 SourceSnapshot → 需求版本化与冲突治理 · mock 演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost">导入来源</button>
        <button className="btn btn-primary">+ 新建需求</button>
      </div>

      <div className="tabs" role="tablist">
        {TABS.map((item) => (
          <button key={item.key} role="tab" aria-selected={tab === item.key} className={tab === item.key ? "on" : ""} onClick={() => setTab(item.key)}>
            {item.label}
          </button>
        ))}
      </div>

      {tab === "sources" && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="phead"><h2>来源快照</h2></div>
          <div className="table-scroll">
            <table>
              <thead><tr><th>来源</th><th>类型</th><th>版本</th><th>抓取状态</th><th>敏感级</th><th>抓取时间</th></tr></thead>
              <tbody>
                {snapRows.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <div className="t-title">{row.title}</div>
                      <div className="t-sub mono">{row.id} · {row.digest}</div>
                    </td>
                    <td><span className="type-tag">{row.type}</span></td>
                    <td className="mono">{row.version}</td>
                    <td><span className={`status ${row.statusClass}`}><span className="d" />{row.status}</span></td>
                    <td><span className={`badge ${row.sensitivityClass}`}>{row.sensitivity}</span></td>
                    <td className="due">{row.fetchedAt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="empty-note" hidden={snapRows.length > 0}>
              <div className="en-title">暂无来源</div>点击「导入来源」添加第一个测试依据（真实模式后端来源导入接口待补）
            </div>
          </div>
        </div>
      )}

      {tab === "reqs" && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="phead"><h2>需求文档</h2></div>
          <div className="table-scroll">
            <table>
              <thead><tr><th>需求</th><th>当前版本</th><th>解析状态</th><th>审核状态</th><th>业务规则</th></tr></thead>
              <tbody>
                {reqRows.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <div className="t-title">{row.title}</div>
                      <div className="t-sub mono">{row.id} · {row.items}</div>
                    </td>
                    <td className="mono">{row.version}</td>
                    <td><span className="status st-done"><span className="d" />{row.parseStatus}</span></td>
                    <td><span className={`status ${row.reviewClass}`}><span className="d" />{row.reviewStatus}</span></td>
                    <td>{row.rules}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="empty-note" hidden={reqRows.length > 0}>
              <div className="en-title">暂无需求文档</div>导入来源后自动解析生成
            </div>
          </div>
        </div>
      )}

      {tab === "conflicts" && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="pbody">
            {sourceConflicts.map((conflict) => (
              <div key={conflict.title} className="check review" style={{ marginBottom: 10 }}>
                <span className="ic">
                  <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8 2.5 13.5 13.5h-11L8 2.5Z" /><path d="M8 7v3M8 12.2v.3" /></svg>
                </span>
                <div>
                  <b>{conflict.title}</b>
                  <div className="small muted">{conflict.detail}</div>
                </div>
                <span className="verdict" style={{ marginLeft: "auto" }}>
                  <button className="btn btn-sm btn-ghost">处理冲突</button>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
