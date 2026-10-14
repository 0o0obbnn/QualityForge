import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { agentRows, promptRows, skillRows, workflowRows } from "../../mock/mockData";
import { Modal } from "../../app/Modal";
import { useToast } from "../../app/Toast";

type TabKey = "skill" | "agent" | "prompt" | "wf";

/**
 * 能力注册页（原型 70-capabilities.html）
 * Skill / Agent / Prompt / Workflow 四 Tab · allowlist 权限 · 原型演示数据
 */
export function AgentCapabilitiesPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [tab, setTab] = useState<TabKey>("skill");
  const [skillModal, setSkillModal] = useState<string | null>(null);
  const [agentModal, setAgentModal] = useState<string | null>(null);
  const [promptModal, setPromptModal] = useState<string | null>(null);
  const [newSkillOpen, setNewSkillOpen] = useState(false);
  const [newAgentOpen, setNewAgentOpen] = useState(false);
  const [agentId, setAgentId] = useState("");
  const [agentIdError, setAgentIdError] = useState("");

  const submitNewAgent = () => {
    if (!agentId.trim()) {
      setAgentIdError("请输入标识");
      return;
    }
    setNewAgentOpen(false);
    setAgentId("");
    setAgentIdError("");
    toast("Agent 已创建,待治理审核激活(演示)", "ok");
  };

  const tabDefs: Array<{ key: TabKey; label: string }> = [
    { key: "skill", label: "Skill (14)" },
    { key: "agent", label: "Agent (4)" },
    { key: "prompt", label: "Prompt 版本" },
    { key: "wf", label: "Workflow" },
  ];

  return (
    <>
      <div className="page-head">
        <div>
          <h1>能力注册</h1>
          <div className="sub">Skill / Agent / Prompt / Workflow · allowlist 权限 · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => navigate("/agent/operations")}>
          运行与评测
        </button>
        <button className="btn btn-ghost" onClick={() => setNewSkillOpen(true)}>
          发布 Skill
        </button>
        <button className="btn btn-primary" onClick={() => setNewAgentOpen(true)}>
          + 新建 Agent
        </button>
      </div>

      <div className="tabs" role="tablist">
        {tabDefs.map((def) => (
          <button
            key={def.key}
            role="tab"
            aria-selected={tab === def.key}
            className={tab === def.key ? "on" : ""}
            onClick={() => setTab(def.key)}
          >
            {def.label}
          </button>
        ))}
      </div>

      {tab === "skill" && (
        <div className="tabpane on" id="tab-skill">
          <div className="panel mt-4">
            <div className="phead">
              <h2>Skill 列表</h2>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Skill</th>
                    <th>版本</th>
                    <th>权限要求</th>
                    <th>Eval</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {skillRows.map((row) => (
                    <tr key={row.id} onClick={() => setSkillModal(row.id)}>
                      <td>
                        <div className="t-title">{row.name}</div>
                        <div className="t-sub">{row.sub}</div>
                      </td>
                      <td className="mono">{row.version}</td>
                      <td>
                        <span className={`badge ${row.permissionClass}`}>{row.permission}</span>
                      </td>
                      <td>
                        <span className={`badge ${row.evalClass}`}>{row.eval}</span>
                      </td>
                      <td>
                        <span className={`status ${row.statusClass}`}>
                          <span className="d" />
                          {row.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="empty-note" hidden={skillRows.length > 0}>
                <div className="en-title">暂无 Skill</div>发布或导入 Skill 后显示
              </div>
              <div className="pagination">
                <span className="pg-info">共 14 个 Skill · 第 1/5 页</span>
                <button disabled>‹</button>
                <button className="on">1</button>
                <button>2</button>
                <button>3</button>
                <button>›</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === "agent" && (
        <div className="tabpane on" id="tab-agent">
          <div className="panel mt-4">
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>职责</th>
                    <th>allowlist 技能</th>
                    <th>委派</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {agentRows.map((row) => (
                    <tr key={row.id} onClick={() => setAgentModal(row.id)}>
                      <td>
                        <div className="t-title">{row.name}</div>
                        <div className="t-sub">{row.sub}</div>
                      </td>
                      <td>{row.duty}</td>
                      <td>{row.allowlist}</td>
                      <td className="mono">{row.delegates}</td>
                      <td>
                        <span className={`status ${row.statusClass}`}>
                          <span className="d" />
                          {row.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === "prompt" && (
        <div className="tabpane on" id="tab-prompt">
          <div className="panel mt-4">
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Prompt</th>
                    <th>版本</th>
                    <th>适用 Agent</th>
                    <th>Eval 状态</th>
                    <th>发布状态</th>
                  </tr>
                </thead>
                <tbody>
                  {promptRows.map((row) => (
                    <tr key={row.id} onClick={() => setPromptModal(row.id)}>
                      <td>
                        <div className="t-title">{row.name}</div>
                        <div className="t-sub">{row.sub}</div>
                      </td>
                      <td className="mono">{row.version}</td>
                      <td>{row.target}</td>
                      <td>
                        <span className={`badge ${row.evalClass}`}>{row.evalStatus}</span>
                      </td>
                      <td>
                        <span className={`status ${row.publishClass}`}>
                          <span className="d" />
                          {row.publish}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === "wf" && (
        <div className="tabpane on" id="tab-wf">
          <div className="panel mt-4">
            <div className="pbody">
              {workflowRows.map((row) => (
                <div className="check pass" key={row.id}>
                  <span className="ic">✓</span>
                  <div>
                    <b>{row.name}</b>
                    <div className="small muted">{row.sub}</div>
                  </div>
                  <span className="verdict">
                    <button className="btn btn-sm btn-ghost" onClick={() => navigate("/agent/trace/a9f2c1")}>
                      查看回放
                    </button>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <Modal
        id="m-new-skill"
        open={newSkillOpen}
        title="发布 Skill"
        triggerNote="触发入口: 「发布 Skill」按钮 · 供应链准入"
        onClose={() => setNewSkillOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setNewSkillOpen(false)}>
              取消
            </button>
            <button
              className="btn btn-primary"
              onClick={() => {
                setNewSkillOpen(false);
                toast("Skill 已进入发布审核(演示)", "ok");
              }}
            >
              提交发布
            </button>
          </>
        }
      >
        <div className="field">
          <label>Skill 包</label>
          <input className="input" placeholder="包名或上传 .zip" />
          <div className="hint">发布需代码与安全 Review;包摘要 sha256 记录。</div>
        </div>
        <div className="field">
          <label>权限要求</label>
          <select className="input">
            <option>只读</option>
            <option>候选写入</option>
            <option>执行</option>
          </select>
        </div>
      </Modal>

      <Modal
        id="m-new-agent"
        open={newAgentOpen}
        title="新建 Agent"
        triggerNote="触发入口: 「新建 Agent」按钮"
        onClose={() => setNewAgentOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setNewAgentOpen(false)}>
              取消
            </button>
            <button className="btn btn-primary" onClick={submitNewAgent}>
              创建(待激活)
            </button>
          </>
        }
      >
        <div className={`field${agentIdError ? " has-err" : ""}`}>
          <label>
            Agent 标识 <span className="req">*</span>
          </label>
          <input
            className="input"
            placeholder="例如: qf-regression"
            value={agentId}
            onChange={(event) => {
              setAgentId(event.target.value);
              if (agentIdError) setAgentIdError("");
            }}
          />
          {agentIdError && <div className="err">{agentIdError}</div>}
        </div>
        <div className="field">
          <label>职责描述</label>
          <textarea className="input" placeholder="目标、边界、委派深度" />
        </div>
        <div className="field">
          <label>allowlist 技能</label>
          <select className="input">
            <option>从已有 Skill 中选择…</option>
            <option>requirement-compiler</option>
            <option>coverage-analyzer</option>
          </select>
        </div>
        <label className="check">
          <input type="checkbox" /> 默认拒绝网络 / Secret / 外部写入
        </label>
      </Modal>

      <Modal
        id="m-skill"
        open={skillModal !== null}
        title="requirement-compiler · V3"
        triggerNote="触发入口: 点击 Skill 行"
        onClose={() => setSkillModal(null)}
        footer={
          <button className="btn btn-primary" onClick={() => setSkillModal(null)}>
            关闭
          </button>
        }
      >
        <div className="kv">
          <span className="muted">输入 Schema</span>
          <span className="mono">ir-input.v3</span>
          <span className="muted">输出 Schema</span>
          <span className="mono">testing-ir.v4</span>
          <span className="muted">权限</span>
          <span>只读来源 · 无网络</span>
          <span className="muted">包摘要</span>
          <span className="mono">sha256:7e2d…0b41</span>
        </div>
      </Modal>

      <Modal
        id="m-agent"
        open={agentModal !== null}
        title="Agent 详情"
        triggerNote="触发入口: 点击 Agent 行"
        onClose={() => setAgentModal(null)}
        footer={
          <button className="btn btn-primary" onClick={() => setAgentModal(null)}>
            关闭
          </button>
        }
      >
        <div className="kv">
          <span className="muted">禁止</span>
          <span>批准正式产出 / 修改权威源 / 外部写入 / 委派</span>
          <span className="muted">预算</span>
          <span className="mono">600s · 12 步 · ¥2/次上限</span>
          <span className="muted">委派深度</span>
          <span className="mono">1</span>
          <span className="muted">状态</span>
          <span className="status st-done">
            <span className="d" />
            ACTIVE(可调度)
          </span>
        </div>
        <p className="small muted mt-4">ACTIVE 只表示可被调度,不代表任何业务批准/网络/Secret 权限。</p>
      </Modal>

      <Modal
        id="m-prompt"
        open={promptModal !== null}
        title="Prompt 版本"
        triggerNote="触发入口: 点击 Prompt 行"
        onClose={() => setPromptModal(null)}
        footer={
          <button className="btn btn-primary" onClick={() => setPromptModal(null)}>
            关闭
          </button>
        }
      >
        <p className="body-text small muted">
          Prompt 不可变;发布前需 Eval 与人工批准。旧 Eval 只关联旧版本,新版本必须重新运行指定数据集版本。
        </p>
        <div className="kv">
          <span className="muted">版本</span>
          <span className="mono">v3 · sha256:4a91…cc2e</span>
          <span className="muted">Eval</span>
          <span>Golden Set v2 · 92.4% 通过</span>
        </div>
      </Modal>
    </>
  );
}
