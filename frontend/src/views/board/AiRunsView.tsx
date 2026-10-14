import { useNavigate } from "react-router-dom";
import { aiRunTasks } from "../../mock/mockData";

/**
 * 视图 2 · AI 工作中（§5.5.9：显示 Agent、当前步骤、耗时、预算、重试和中断入口）。
 * 对齐原型 ai-panel 条目 + 12-workitem AI 运行详情形态，扩展到整页表格。
 */

const STEP_CLASS = "st-run";

export function AiRunsView() {
  const navigate = useNavigate();
  return (
    <div className="panel">
      <div className="phead">
        <h2>AI 工作中</h2>
        <span className="hint">{aiRunTasks.length} 个运行</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>任务</th>
              <th>Agent</th>
              <th>当前步骤</th>
              <th>进度</th>
              <th>预算</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {aiRunTasks.map((task) => (
              <tr key={task.id} style={{ cursor: "pointer" }} onClick={() => navigate(`/work-items/${task.workItemId}`)}>
                <td>
                  <div className="t-title">
                    <span className="ai-tag">AI</span> {task.name}
                  </div>
                  <div className="t-sub mono">{task.workItemId} · {task.attempt}</div>
                </td>
                <td>{task.agent}</td>
                <td>
                  <span className={`status ${STEP_CLASS}`}>
                    <span className="d" />
                    {task.step}
                  </span>
                  <span className="small muted" style={{ marginLeft: 6 }}>{task.elapsed}</span>
                </td>
                <td style={{ minWidth: 140 }}>
                  <div className="bar">
                    <i style={{ width: `${task.progress}%` }} />
                  </div>
                </td>
                <td className="t-num">{task.budget}</td>
                <td>
                  <span style={{ display: "flex", gap: 8 }}>
                    <button
                      className="btn btn-sm btn-ghost"
                      onClick={(event) => {
                        event.stopPropagation();
                        navigate(`/work-items/${task.workItemId}`);
                      }}
                    >
                      查看
                    </button>
                    <button className="btn btn-sm btn-ghost" disabled title="中断入口待后端 interrupt 接口(M2 契约缺口)">
                      中断
                    </button>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="empty-note" hidden={aiRunTasks.length > 0}>
          <div className="en-title">暂无 AI 运行</div>
          工作项启动后，运行状态与步骤进度在此展示。
        </div>
      </div>
    </div>
  );
}
