import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { agentKpis, evalRows, sessionRows } from "../../mock/mockData";
import { Modal } from "../../app/Modal";
import { useToast } from "../../app/Toast";

/**
 * 运行与评测页（原型 71-operations.html）
 * Session / Trace / Eval / 成本 · 运行事实只追加 · 原型演示数据
 */
export function AgentOperationsPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [sessionOpen, setSessionOpen] = useState(false);
  const [evalOpen, setEvalOpen] = useState(false);
  const [evalDetailOpen, setEvalDetailOpen] = useState(false);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>运行与评测</h1>
          <div className="sub">Session / Trace / Eval / 成本 · 运行事实只追加 · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => navigate("/agent")}>
          能力注册
        </button>
        <button className="btn btn-ghost" onClick={() => setEvalOpen(true)}>
          运行 Eval
        </button>
        <button className="btn btn-primary" onClick={() => setSessionOpen(true)}>
          发起 Session
        </button>
      </div>

      <div className="grid g4" style={{ marginBottom: "18px" }}>
        {agentKpis.map((kpi) => (
          <div className="kpi" key={kpi.label}>
            <div className="label">{kpi.label}</div>
            <div className={`value ${kpi.cls}`}>
              <b>{kpi.value}</b>
            </div>
            <div className="note">{kpi.note}</div>
          </div>
        ))}
      </div>

      <div className="panel">
        <div className="phead">
          <h2>Session 列表</h2>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Session</th>
                <th>Workflow</th>
                <th>状态</th>
                <th>成本</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {sessionRows.map((row) => (
                <tr key={row.id} onClick={() => navigate(`/agent/trace/${row.id}`)}>
                  <td>
                    <div className="t-title">{row.title}</div>
                    <div className="t-sub">{row.sub}</div>
                  </td>
                  <td className="mono">{row.workflow}</td>
                  <td>
                    <span className={`status ${row.statusClass}`}>
                      <span className="d" />
                      {row.status}
                    </span>
                  </td>
                  <td className="mono">{row.cost}</td>
                  <td>
                    <button
                      className="btn btn-sm btn-ghost"
                      onClick={(event) => {
                        event.stopPropagation();
                        navigate(`/agent/trace/${row.id}`);
                      }}
                    >
                      Trace
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="empty-note" hidden={sessionRows.length > 0}>
            <div className="en-title">暂无 Session</div>发起 Session 后运行记录将出现在这里
          </div>
          <div className="pagination">
            <span className="pg-info">共 27 个 Session · 第 1/14 页</span>
            <button disabled>‹</button>
            <button className="on">1</button>
            <button>2</button>
            <button>3</button>
            <button>›</button>
          </div>
        </div>
      </div>

      <div className="panel mt-6">
        <div className="phead">
          <h2>Eval 记录</h2>
          <span className="hint">版本可复现</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Eval Run</th>
                <th>目标</th>
                <th>数据集</th>
                <th>通过率</th>
                <th>裁决</th>
              </tr>
            </thead>
            <tbody>
              {evalRows.map((row) => (
                <tr key={row.id} onClick={() => setEvalDetailOpen(true)}>
                  <td>
                    <div className="t-title">{row.title}</div>
                    <div className="t-sub">{row.sub}</div>
                  </td>
                  <td className="mono">{row.target}</td>
                  <td className="mono">{row.dataset}</td>
                  <td>
                    <span className="t-num" style={{ color: "var(--qf-success-600)", fontWeight: 600 }}>
                      {row.rate}
                    </span>
                  </td>
                  <td>
                    <span className={`status ${row.verdictClass}`}>
                      <span className="d" />
                      {row.verdict}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        id="m-session"
        open={sessionOpen}
        title="发起 Session"
        triggerNote="触发入口: 「发起 Session」按钮"
        onClose={() => setSessionOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setSessionOpen(false)}>
              取消
            </button>
            <button
              className="btn btn-primary"
              onClick={() => {
                setSessionOpen(false);
                toast("Session 已启动,权限预检通过(演示)", "ok");
              }}
            >
              启动
            </button>
          </>
        }
      >
        <div className="field">
          <label>Workflow</label>
          <select className="input">
            <option>gate0-requirement-to-coverage</option>
            <option>其他(草稿)</option>
          </select>
        </div>
        <div className="field">
          <label>来源版本</label>
          <select className="input">
            <option>Req V3 · APIContract V7</option>
          </select>
        </div>
        <label className="check">
          <input type="checkbox" defaultChecked /> 权限预检(默认)
        </label>
      </Modal>

      <Modal
        id="m-eval"
        open={evalOpen}
        title="运行 Eval"
        triggerNote="触发入口: 「运行 Eval」按钮"
        onClose={() => setEvalOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setEvalOpen(false)}>
              取消
            </button>
            <button
              className="btn btn-primary"
              onClick={() => {
                setEvalOpen(false);
                toast("Eval 已启动(演示)", "ok");
              }}
            >
              运行
            </button>
          </>
        }
      >
        <div className="field">
          <label>目标</label>
          <select className="input">
            <option>Agent: qf-requirement-ir (prompt v3)</option>
          </select>
        </div>
        <div className="field">
          <label>数据集</label>
          <select className="input">
            <option>golden-v2 (120 例)</option>
          </select>
        </div>
      </Modal>

      <Modal
        id="m-eval-detail"
        open={evalDetailOpen}
        title="Eval 详情"
        triggerNote="触发入口: 点击 Eval 行"
        onClose={() => setEvalDetailOpen(false)}
        footer={
          <button className="btn btn-primary" onClick={() => setEvalDetailOpen(false)}>
            关闭
          </button>
        }
      >
        <div className="kv">
          <span className="muted">指标</span>
          <span>准确率 92.4% · 路由正确率 97% · 越权率 0%</span>
          <span className="muted">环境</span>
          <span className="mono">eval-env-1 · 2026-08-11</span>
          <span className="muted">版本绑定</span>
          <span className="mono">prompt v3 · golden-v2</span>
        </div>
        <p className="small muted mt-4">文档静态 PASS 不等于运行时有效;校准只基于版本化 Eval 证据。</p>
      </Modal>
    </>
  );
}
