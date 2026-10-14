import { useNavigate } from "react-router-dom";
import { scriptRows } from "../../mock/mockData";

/**
 * 自动化工作台页（对齐 40-scripts.html + Sprint 2 T7）：
 * 脚本列表 + 三张卡片（用例绑定/代码检查/Secret 隔离）。
 * mock 演示数据；真实模式接 listAutomationScripts（后端待接入）。
 */

export function ScriptsPage() {
  const navigate = useNavigate();
  return (
    <>
      <div className="page-head">
        <div>
          <h1>自动化工作台</h1>
          <div className="sub">AutomationScript 版本化 + 用例绑定 + 代码检查 · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => navigate("/automation/code-review")}>配套资产</button>
        <button className="btn btn-primary" onClick={() => navigate("/reviews")}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M8 3v10M3 8h10" /></svg>
          生成脚本
        </button>
      </div>

      <div className="panel">
        <div className="phead"><h2>脚本列表</h2><span className="hint">Web / API · 版本化正式产出物</span></div>
        <div className="table-scroll">
          <table>
            <thead><tr><th>脚本</th><th>类型</th><th>版本</th><th>绑定用例</th><th>检查</th><th>状态</th></tr></thead>
            <tbody>
              {scriptRows.map((row) => (
                <tr key={row.id} style={{ cursor: "pointer" }} onClick={() => navigate("/automation/code-review")}>
                  <td>
                    <div className="t-title">{row.title}</div>
                    <div className="t-sub mono">{row.sub}</div>
                  </td>
                  <td><span className="type-tag">{row.type}</span></td>
                  <td className="mono">{row.version}</td>
                  <td>{row.boundCases}</td>
                  <td><span className={`badge ${row.checkClass}`}>{row.check}</span></td>
                  <td><span className={`status ${row.statusClass}`}><span className="d" />{row.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="empty-note" hidden={scriptRows.length > 0}>
            <div className="en-title">暂无脚本</div>点击「生成脚本」创建第一个自动化脚本
          </div>
        </div>
      </div>

      <div className="grid g3" style={{ marginTop: 20 }}>
        <div className="card">
          <h2 style={{ fontSize: 14, marginBottom: 8 }}>用例绑定</h2>
          <p className="small muted">1 个脚本版本可覆盖多个 TestCaseVersion；1 个用例可有多种自动化实现。绑定带 coverageType 标注。</p>
          <button className="btn btn-sm btn-ghost mt-3" onClick={() => navigate("/planning/cases")}>管理绑定</button>
        </div>
        <div className="card">
          <h2 style={{ fontSize: 14, marginBottom: 8 }}>代码检查</h2>
          <p className="small muted">格式 / 类型 / 静态安全 / 依赖 / 契约绑定 / 受控试跑。检查 PASS 不替代代码批准。</p>
          <button className="btn btn-sm btn-ghost mt-3" onClick={() => navigate("/automation/code-review")}>查看检查项</button>
        </div>
        <div className="card">
          <h2 style={{ fontSize: 14, marginBottom: 8 }}>Secret 隔离</h2>
          <p className="small muted">脚本只引用 secretRef；日志与 Trace 不出现明文。未授权 Secret 时生成模板但不试跑。</p>
          <button className="btn btn-sm btn-ghost mt-3" onClick={() => navigate("/platform")}>查看规范</button>
        </div>
      </div>
    </>
  );
}