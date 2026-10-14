import { useState } from "react";
import { assetLocators, assetMocks } from "../../mock/mockData";

/**
 * 配套资产页（对齐 42-assets.html + Sprint 2 T7）：
 * 四 Tab（Locator / Mock 配置 / 测试数据 / 视觉基线），各 Tab 资产列表。
 * mock 演示数据；真实模式接 listAutomationAssets（后端待接入）。
 */

const TABS = [
  { key: "locator", label: "Locator" },
  { key: "mock", label: "Mock 配置" },
  { key: "data", label: "测试数据" },
  { key: "visual", label: "视觉基线" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export function AssetsPage() {
  const [tab, setTab] = useState<TabKey>("locator");
  return (
    <>
      <div className="page-head">
        <div>
          <h1>配套资产</h1>
          <div className="sub">Locator / Mock / 数据 Profile / 视觉基线 · 版本化与人工审核 · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-primary" onClick={() => setTab("locator")}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M8 3v10M3 8h10" /></svg>
          新建资产
        </button>
      </div>

      <div className="tabs" role="tablist">
        {TABS.map((item) => (
          <button key={item.key} role="tab" aria-selected={tab === item.key} className={tab === item.key ? "on" : ""} onClick={() => setTab(item.key)}>
            {item.label}
          </button>
        ))}
      </div>

      {tab === "locator" && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="phead"><h2>资产列表</h2></div>
          <div className="table-scroll">
            <table>
              <thead><tr><th>Locator</th><th>主选择器</th><th>状态</th><th>来源</th><th>操作</th></tr></thead>
              <tbody>
                {assetLocators.map((row) => (
                  <tr key={row.title}>
                    <td>
                      <div className="t-title">{row.title}</div>
                      <div className="t-sub">{row.sub}</div>
                    </td>
                    <td className="mono">{row.selector}</td>
                    <td><span className={`status ${row.statusClass}`}><span className="d" />{row.status}</span></td>
                    <td>{row.source === "AI 发现" ? <span className="ai-tag">AI</span> : row.source}</td>
                    <td>
                      <button className="btn btn-sm btn-ghost">
                        {row.status === "DECAYING" ? "查看候选" : "自愈候选"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="empty-note" hidden={assetLocators.length > 0}>
              <div className="en-title">暂无资产</div>新建或由 AI 发现
            </div>
          </div>
        </div>
      )}

      {tab === "mock" && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="table-scroll">
            <table>
              <thead><tr><th>Mock</th><th>绑定契约</th><th>匹配规则</th><th>状态</th></tr></thead>
              <tbody>
                {assetMocks.map((row) => (
                  <tr key={row.title}>
                    <td>
                      <div className="t-title">{row.title}</div>
                      <div className="t-sub">{row.sub}</div>
                    </td>
                    <td className="mono">{row.contract}</td>
                    <td className="mono">{row.rule}</td>
                    <td><span className={`status ${row.statusClass}`}><span className="d" />{row.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "data" && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="pbody">
            <div className="empty-note" style={{ border: "none" }}>
              <div className="en-title">暂无测试数据资产</div>
              数据 Profile 由平台管理创建，此处为绑定视图（后续里程碑）。
            </div>
          </div>
        </div>
      )}

      {tab === "visual" && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="pbody">
            <div className="empty-note" style={{ border: "none" }}>
              <div className="en-title">暂无视觉基线资产</div>
              视觉基线在首次执行时由 Runner 采集（后续里程碑）。
            </div>
          </div>
        </div>
      )}
    </>
  );
}