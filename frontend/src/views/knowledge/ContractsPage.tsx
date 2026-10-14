import { apiContracts, contractOperations } from "../../mock/mockData";

/**
 * API 契约页（对齐 21-api-contracts.html）：
 * 契约列表 + Operation 列表 + Release 基线侧栏 + 漂移检测侧栏。
 * mock 演示数据；真实模式接 listContractBaselines（后端契约域待接入）。
 */

export function ContractsPage() {
  return (
    <>
      <div className="page-head">
        <div>
          <h1>API 契约</h1>
          <div className="sub">APIContract 稳定根 + 不可变版本 · DECLARED / OBSERVED 分层 · mock 演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost">管理基线</button>
        <button className="btn btn-primary">导入契约</button>
      </div>

      <div className="two-col">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="panel">
            <div className="phead">
              <h2>契约列表</h2>
              <span className="hint">2 个契约 · 22 + 14 个 operation</span>
            </div>
            <div className="table-scroll">
              <table>
                <thead><tr><th>契约</th><th>当前版本</th><th>状态</th><th>Operation</th><th>基线</th></tr></thead>
                <tbody>
                  {apiContracts.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <div className="t-title">{row.id}</div>
                        <div className="t-sub">{row.title}</div>
                      </td>
                      <td className="mono">{row.version}</td>
                      <td><span className={`status ${row.statusClass}`}><span className="d" />{row.status}</span></td>
                      <td className="mono">{row.ops}</td>
                      <td className="small" style={{ color: row.baselineClass === "locked" ? "var(--qf-success-600)" : "var(--qf-muted-foreground)" }}>
                        {row.baseline}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="empty-note" hidden={apiContracts.length > 0}>
                <div className="en-title">暂无契约</div>导入 OpenAPI 或流量后显示
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="phead">
              <h2>Operation · settlement-api V7</h2>
              <span className="hint">点击行查看详情</span>
            </div>
            <div className="table-scroll">
              <table>
                <thead><tr><th>方法</th><th>路径</th><th>来源</th><th>稳定性</th></tr></thead>
                <tbody>
                  {contractOperations.map((op) => (
                    <tr key={op.path}>
                      <td><span className={`badge ${op.methodClass}`}>{op.method}</span></td>
                      <td className="mono">{op.path}</td>
                      <td><span className={`badge ${op.sourceClass}`}>{op.source}</span></td>
                      <td><span className={`status ${op.stabilityClass}`}><span className="d" />{op.stability}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="pagination">
                <span className="pg-info">共 22 个 Operation · 第 1/8 页</span>
                <button disabled>‹</button><button className="on">1</button><button>2</button><button>3</button><button>›</button>
              </div>
            </div>
          </div>
        </div>

        <div className="aside-stack">
          <div className="mini-card">
            <h3>Release 契约基线</h3>
            <div className="row"><span className="k">用途</span><span className="v">TEST_DESIGN</span></div>
            <div className="row"><span className="k">settlement-api</span><span className="mono">V7 · 摘要 3f9a…</span></div>
            <div className="row"><span className="k">reconciliation-api</span><span className="mono">V4 · 摘要 7b21…</span></div>
            <div className="row"><span className="k">批准人</span><span className="v">李测试</span></div>
          </div>
          <div className="mini-card">
            <h3>漂移检测</h3>
            <div className="row"><span className="k">最近扫描</span><span className="v">08-11 23:00</span></div>
            <div className="row"><span className="k">差异</span><span className="v" style={{ color: "var(--qf-warning-500)" }}>1 处 breaking</span></div>
            <div className="row"><span className="k">建议</span><span className="v muted">发起影响分析</span></div>
          </div>
        </div>
      </div>
    </>
  );
}
