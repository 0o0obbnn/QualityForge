import { useNavigate } from "react-router-dom";
import { reworkRows } from "../../mock/mockData";

/**
 * 视图 3 · 审核退回/重做（§5.5.9：显示审核意见、差异和当前修改人）。
 * 无原型对应页，按 §5.5.9 定义 + qf 组件语言构建（原型 11-reviews diff 组件复用视觉）。
 */

export function ReworkView() {
  const navigate = useNavigate();
  return (
    <div className="panel">
      <div className="phead">
        <h2>审核退回 / 重做</h2>
        <span className="hint">{reworkRows.length} 项返工中</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>工作项</th>
              <th>返工轮次</th>
              <th>审核意见</th>
              <th>差异</th>
              <th>当前修改人</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {reworkRows.map((row) => (
              <tr key={row.id} style={{ cursor: "pointer" }} onClick={() => navigate(`/work-items/${row.workItemId}`)}>
                <td>
                  <div className="tid">{row.workItemId}</div>
                  <div className="t-title">{row.title}</div>
                </td>
                <td>
                  <span className="badge b-warn">{row.reworkRound}</span>
                </td>
                <td style={{ maxWidth: 320 }}>
                  <span className="small">{row.reviewComment}</span>
                </td>
                <td>
                  <span className="small muted mono">{row.diff}</span>
                </td>
                <td>
                  <div className="actor">
                    {row.editor === "AI" ? <span className="ai-tag">AI</span> : null}
                    {row.editorName}
                  </div>
                </td>
                <td>
                  <span className="status st-review">
                    <span className="d" />
                    需修改
                  </span>
                  <div className={`due small ${row.over ? "over" : ""}`}>{row.due}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="empty-note" hidden={reworkRows.length > 0}>
          <div className="en-title">暂无退回重做项</div>
          审核退回后，工作项在此展示意见、差异与修改人。
        </div>
      </div>
    </div>
  );
}
