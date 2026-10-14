import { useNavigate } from "react-router-dom";
import { executionRows } from "../../mock/mockData";

/**
 * 视图 4 · 待执行/执行中（§5.5.9：关联环境、Release、脚本版本和 ExecutionTask）。
 * 对齐原型 50-execution-plans.html 表格结构 + 51-execution-monitor 状态语义。
 */

const STATUS_CLASS: Record<string, string> = {
  run: "st-run",
  queue: "st-backlog",
  blocked: "st-blocked",
};

export function ExecutionView() {
  const navigate = useNavigate();
  return (
    <div className="panel">
      <div className="phead">
        <h2>待执行 / 执行中</h2>
        <span className="hint">{executionRows.length} 个执行计划</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>计划</th>
              <th>环境</th>
              <th>Release</th>
              <th>脚本版本</th>
              <th>ExecutionTask</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {executionRows.map((row) => (
              <tr key={row.id} style={{ cursor: "pointer" }} onClick={() => navigate("/execution")}>
                <td>
                  <div className="t-title">{row.plan}</div>
                  <div className="t-sub mono">{row.planId}</div>
                </td>
                <td>{row.environment}</td>
                <td>{row.release}</td>
                <td className="mono small">{row.scriptVersion}</td>
                <td className="mono small">{row.executionTask}</td>
                <td>
                  <span className={`status ${STATUS_CLASS[row.status]}`}>
                    <span className="d" />
                    {row.statusLabel}
                  </span>
                  {row.status === "run" && (
                    <div className="pr-line" style={{ marginTop: 6, width: 120 }}>
                      <i style={{ width: `${row.progress}%` }} />
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="empty-note" hidden={executionRows.length > 0}>
          <div className="en-title">暂无执行计划</div>
          创建并冻结版本后开始执行（执行模块归 M3，本视图为看板投影）。
        </div>
      </div>
      <p className="small muted" style={{ padding: "0 18px 14px" }}>
        执行版本冻结语义：冻结后用例/脚本发布新版本不影响本次执行；新版本需新建计划版本。
      </p>
    </div>
  );
}
