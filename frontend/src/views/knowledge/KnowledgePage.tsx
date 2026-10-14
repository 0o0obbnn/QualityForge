import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { fetchKnowledgeEntries } from "../../services/dataService";
import type { KnowledgeEntryRow } from "../../services/dataService";
import type { Profile } from "../../types";

/**
 * 知识库页（对齐 22-knowledge.html）：
 * 检索 + 已发布条目列表 + 检索说明/候选治理侧栏。
 * 真实模式接 listKnowledgeEntries（批次四十六补路由）；无数据时空态不虚构。
 */

export function KnowledgePage() {
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<KnowledgeEntryRow[]>([]);

  useEffect(() => {
    let active = true;
    void fetchKnowledgeEntries(profile).then((list) => {
      if (active) setRows(list);
    });
    return () => {
      active = false;
    };
  }, [profile]);

  const filtered = query.trim()
    ? rows.filter(
        (entry) => entry.title.includes(query) || entry.id.includes(query) || entry.category.includes(query),
      )
    : rows;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>知识库</h1>
          <div className="sub">已审核经验 · 检索必须带来源与版本 · 命中不等于可信 · mock 演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost">知识候选 (3)</button>
        <button className="btn btn-primary">+ 新建条目</button>
      </div>

      <div className="search" style={{ width: "100%", marginBottom: 18 }}>
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
          <circle cx="7" cy="7" r="4.5" /><path d="m10.5 10.5 3 3" />
        </svg>
        <input
          type="search"
          aria-label="知识库检索"
          placeholder="关键词 / 向量 / 图谱混合检索…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      <div className="two-col">
        <div className="panel">
          <div className="phead">
            <h2>已发布条目</h2>
            <span className="hint">{filtered.length} 条 · 点击查看详情</span>
          </div>
          <div className="table-scroll">
            <table>
              <thead><tr><th>条目</th><th>分类</th><th>版本</th><th>状态</th><th>失效条件</th></tr></thead>
              <tbody>
                {filtered.map((entry) => (
                  <tr key={entry.id}>
                    <td>
                      <div className="t-title">{entry.title}</div>
                      <div className="t-sub mono">{entry.sub}</div>
                    </td>
                    <td><span className="type-tag">{entry.category}</span></td>
                    <td className="mono">{entry.version}</td>
                    <td><span className={`status ${entry.statusClass}`}><span className="d" />{entry.status}</span></td>
                    <td className="small muted">{entry.expiry}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="empty-note" hidden={filtered.length > 0}>
              <div className="en-title">没有匹配的条目</div>尝试更换关键词，或提交新知识候选
            </div>
          </div>
        </div>
        <div className="aside-stack">
          <div className="mini-card">
            <h3>检索说明</h3>
            <div className="row"><span className="k">结果带来源</span><span className="v">✅ 是</span></div>
            <div className="row"><span className="k">版本+摘要</span><span className="v">✅ 是</span></div>
            <div className="row"><span className="k">高相似≠事实</span><span className="v" style={{ color: "var(--qf-warning-500)" }}>AI 须遵守</span></div>
          </div>
          <div className="mini-card">
            <h3>候选治理</h3>
            <div className="row"><span className="k">待处理</span><span className="v" style={{ color: "var(--qf-warning-500)" }}>3</span></div>
            <div className="row"><span className="k">其中重复</span><span className="v">2</span></div>
            <div className="row"><span className="k">最近生成</span><span className="v muted">08-11 22:10</span></div>
          </div>
        </div>
      </div>
    </>
  );
}
