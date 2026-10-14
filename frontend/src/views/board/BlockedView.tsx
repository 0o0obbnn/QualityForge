import { useNavigate } from "react-router-dom";
import { blockedGroups } from "../../mock/mockData";

/**
 * 视图 5 · 阻塞与风险（§5.5.9：按阻塞原因、责任方、持续时间和恢复条件分组）。
 * 分组列表形态：组头=原因码+计数，组内表格行。行点击 → 工作项详情。
 */

export function BlockedView() {
  const navigate = useNavigate();
  const total = blockedGroups.reduce((sum, group) => sum + group.count, 0);
  return (
    <div className="panel">
      <div className="phead">
        <h2>阻塞与风险</h2>
        <span className="hint">{total} 项阻塞 · {blockedGroups.length} 类原因</span>
      </div>
      {blockedGroups.map((group) => (
        <div key={group.reason} style={{ borderBottom: "1px solid var(--qf-border)" }}>
          <div className="flex" style={{ padding: "12px 18px", background: "var(--qf-secondary-surface)" }}>
            <span className="badge b-err">{group.reason}</span>
            <b style={{ fontSize: 13 }}>{group.label}</b>
            <span className="small muted">{group.count} 项</span>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>工作项</th>
                  <th>责任方</th>
                  <th>持续时间</th>
                  <th>恢复条件</th>
                </tr>
              </thead>
              <tbody>
                {group.rows.map((row) => (
                  <tr key={row.workItemId} style={{ cursor: "pointer" }} onClick={() => navigate(`/work-items/${row.workItemId}`)}>
                    <td>
                      <div className="tid">{row.workItemId}</div>
                      <div className="t-title">{row.title}</div>
                    </td>
                    <td>{row.owner}</td>
                    <td className="t-num" style={{ color: "var(--qf-error-600)", fontWeight: 600 }}>
                      {row.duration}
                    </td>
                    <td className="small">{row.recover}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
      <div className="empty-note" hidden={total > 0} style={{ borderTop: "1px solid var(--qf-border)" }}>
        <div className="en-title">暂无阻塞项</div>
        阻塞发生时按原因分组展示，含责任方与恢复条件（§5.5.4 规则 5 必录）。
      </div>
    </div>
  );
}
