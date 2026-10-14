import { useNavigate } from "react-router-dom";
import { memberRows, releaseRows, workspaceRows } from "../../mock/mockData";
import { IconPlus } from "../../app/Icons";
import { useToast } from "../../app/Toast";

/**
 * 项目与 Release 页（原型 80-workspaces.html）
 * UI「项目」= Workspace 实体 · 生命周期与成员 · 原型演示数据
 */
export function WorkspacesPage() {
  const navigate = useNavigate();
  const toast = useToast();

  return (
    <>
      <div className="page-head">
        <div>
          <h1>项目与 Release</h1>
          <div className="sub">UI「项目」= Workspace 实体 · 生命周期与成员 · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-sm btn-ghost" onClick={() => navigate("/platform/environments")}>
          环境与资源
        </button>
        <button className="btn btn-sm btn-ghost" onClick={() => navigate("/platform/governance")}>
          集成与权限
        </button>
        <button className="btn btn-primary" onClick={() => toast("新建项目(演示)", "info")}>
          <IconPlus />
          新建项目
        </button>
      </div>

      <div className="grid g2">
        <div className="panel">
          <div className="phead">
            <h2>项目列表</h2>
            <span className="hint">{workspaceRows.length} 个项目(含本地创建)</span>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>项目</th>
                  <th>标识</th>
                  <th>状态</th>
                  <th>Release</th>
                </tr>
              </thead>
              <tbody>
                {workspaceRows.map((row) => (
                  <tr key={row.key} onClick={() => toast("切换到该项目(演示)", "info")}>
                    <td>
                      <div className="t-title">{row.title}</div>
                      <div className="t-sub">{row.sub}</div>
                    </td>
                    <td className="mono">{row.key}</td>
                    <td>
                      <span className={`status ${row.statusClass}`}>
                        <span className="d" />
                        {row.status}
                      </span>
                    </td>
                    <td className="mono">{row.release}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="empty-note" hidden={workspaceRows.length > 0}>
              <div className="en-title">暂无项目</div>点击「新建项目」开始第一个测试项目
            </div>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="panel">
            <div className="phead">
              <h2>Release · R-2026.08</h2>
            </div>
            <div className="pbody">
              {releaseRows.map((row, index) => (
                <div className="cov-row" key={row.name} style={index === releaseRows.length - 1 ? { marginBottom: 0 } : undefined}>
                  <div className="top">
                    <span className="name">{row.name}</span>
                    <span className="val">
                      {row.status ? (
                        <span className={`status ${row.statusClass}`}>
                          <span className="d" />
                          {row.val}
                        </span>
                      ) : (
                        row.val
                      )}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="mini-card">
            <h3>成员 (5)</h3>
            {memberRows.map((member) => (
              <div className="row" key={member.name}>
                <span className="k">{member.name}</span>
                <span className="v">{member.role}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
