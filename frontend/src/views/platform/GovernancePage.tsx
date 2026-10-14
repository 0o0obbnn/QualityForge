import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { auditRows, integrationRows, policyRows, roleRows } from "../../mock/mockData";
import { IconPlus } from "../../app/Icons";
import { Modal } from "../../app/Modal";
import { useToast } from "../../app/Toast";

/**
 * 集成与权限页（原型 82-governance.html）
 * Integration / RBAC / ReviewPolicy / 审计 · 四级作用域 fail-closed · 原型演示数据
 */
export function GovernancePage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [tab, setTab] = useState("integration");
  const [auditOpen, setAuditOpen] = useState(false);
  const [newRoleOpen, setNewRoleOpen] = useState(false);
  const [integrationOpen, setIntegrationOpen] = useState(false);
  const [roleOpen, setRoleOpen] = useState(false);
  const [policyOpen, setPolicyOpen] = useState(false);
  const [roleName, setRoleName] = useState("");
  const [roleNameError, setRoleNameError] = useState("");

  const submitNewRole = () => {
    if (!roleName.trim()) {
      setRoleNameError("请输入名称");
      return;
    }
    setNewRoleOpen(false);
    setRoleName("");
    setRoleNameError("");
    toast("角色已创建,等待人工授权(演示)", "ok");
  };

  const tabs = [
    { key: "integration", label: "集成" },
    { key: "rbac", label: "RBAC" },
    { key: "policy", label: "审核策略" },
  ];

  return (
    <>
      <div className="page-head">
        <div>
          <h1>集成与权限</h1>
          <div className="sub">Integration / RBAC / ReviewPolicy / 审计 · 四级作用域 fail-closed · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-sm btn-ghost" onClick={() => navigate("/platform")}>
          项目
        </button>
        <button className="btn btn-sm btn-ghost" onClick={() => navigate("/platform/environments")}>
          环境与资源
        </button>
        <button className="btn btn-ghost" onClick={() => setAuditOpen(true)}>
          审计日志
        </button>
        <button className="btn btn-primary" onClick={() => setNewRoleOpen(true)}>
          <IconPlus />
          新建角色
        </button>
      </div>

      <div className="tabs">
        {tabs.map((item) => (
          <button key={item.key} className={tab === item.key ? "on" : ""} onClick={() => setTab(item.key)}>
            {item.label}
          </button>
        ))}
      </div>

      {tab === "integration" && (
        <div className="tabpane on">
          <div className="panel">
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>集成</th>
                    <th>类型</th>
                    <th>作用域</th>
                    <th>凭据</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {integrationRows.map((row) => (
                    <tr key={row.title} onClick={() => setIntegrationOpen(true)}>
                      <td>
                        <div className="t-title">{row.title}</div>
                        <div className="t-sub">{row.sub}</div>
                      </td>
                      <td>
                        <span className="type-tag">{row.type}</span>
                      </td>
                      <td>{row.scope}</td>
                      <td className="mono">{row.cred}</td>
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

      {tab === "rbac" && (
        <div className="tabpane on">
          <div className="panel">
            <div className="phead">
              <h2>角色模板</h2>
              <span className="hint">内置角色不可被租户原地修改</span>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>角色</th>
                    <th>作用域</th>
                    <th>默认责任</th>
                    <th>不默认拥有</th>
                  </tr>
                </thead>
                <tbody>
                  {roleRows.map((row) => (
                    <tr key={row.title} onClick={() => setRoleOpen(true)}>
                      <td>
                        <div className="t-title">{row.title}</div>
                      </td>
                      <td>{row.scope}</td>
                      <td>{row.duties}</td>
                      <td>{row.excluded}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === "policy" && (
        <div className="tabpane on">
          <div className="panel">
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>策略</th>
                    <th>产出物/风险</th>
                    <th>阶段</th>
                    <th>职责分离</th>
                    <th>版本</th>
                  </tr>
                </thead>
                <tbody>
                  {policyRows.map((row) => (
                    <tr key={row.title} onClick={() => setPolicyOpen(true)}>
                      <td>
                        <div className="t-title">{row.title}</div>
                      </td>
                      <td>{row.risk}</td>
                      <td>{row.stage}</td>
                      <td>{row.separation}</td>
                      <td className="mono">{row.version}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pbody small muted">平台最低要求只能调严,不能取消至少一名人类审核。</div>
          </div>
        </div>
      )}

      <Modal
        id="m-audit"
        open={auditOpen}
        title="审计日志"
        width="wide"
        triggerNote="触发入口: 「审计日志」按钮 · 只追加 · 应用角色禁止 UPDATE/DELETE"
        onClose={() => setAuditOpen(false)}
        footer={
          <button className="btn btn-primary" onClick={() => setAuditOpen(false)}>
            关闭
          </button>
        }
      >
        <div className="table-scroll">
          <table data-readonly>
            <thead>
              <tr>
                <th>时间</th>
                <th>动作</th>
                <th>资源</th>
                <th>决定</th>
              </tr>
            </thead>
            <tbody>
              {auditRows.map((row) => (
                <tr key={`${row.time}-${row.action}`}>
                  <td className="mono small">{row.time}</td>
                  <td>{row.action}</td>
                  <td className="mono">{row.resource}</td>
                  <td>
                    <span className={`badge ${row.decisionClass}`}>{row.decision}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Modal>

      <Modal
        id="m-new-role"
        open={newRoleOpen}
        title="新建角色"
        triggerNote="触发入口: 「新建角色」按钮 · 角色管理需人工授权"
        onClose={() => setNewRoleOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setNewRoleOpen(false)}>
              取消
            </button>
            <button className="btn btn-primary" onClick={submitNewRole}>
              创建
            </button>
          </>
        }
      >
        <div className={`field${roleNameError ? " has-err" : ""}`}>
          <label>
            角色名称 <span className="req">*</span>
          </label>
          <input
            className="input"
            placeholder="例如: 风险审核员"
            value={roleName}
            onChange={(event) => {
              setRoleName(event.target.value);
              if (roleNameError) setRoleNameError("");
            }}
          />
          <div className="err">请输入名称</div>
        </div>
        <div className="field">
          <label>作用域</label>
          <select className="input">
            <option>WORKSPACE</option>
            <option>TENANT</option>
            <option>PLATFORM</option>
          </select>
        </div>
        <div className="field">
          <label>权限</label>
          <select className="input">
            <option>从已有角色复制</option>
            <option>自定义</option>
          </select>
        </div>
      </Modal>

      <Modal
        id="m-integration"
        open={integrationOpen}
        title="集成详情"
        triggerNote="触发入口: 点击集成行"
        onClose={() => setIntegrationOpen(false)}
        footer={
          <button className="btn btn-primary" onClick={() => setIntegrationOpen(false)}>
            关闭
          </button>
        }
      >
        <div className="kv">
          <span className="muted">出站目标</span>
          <span className="mono">*.atlassian.net (allowlist)</span>
          <span className="muted">操作</span>
          <span>CREATE / UPDATE / COMMENT</span>
          <span className="muted">凭据</span>
          <span className="mono">cred:jira V4 (引用)</span>
          <span className="muted">写入</span>
          <span>逐次批准 · 幂等</span>
        </div>
      </Modal>

      <Modal
        id="m-role"
        open={roleOpen}
        title="角色详情"
        triggerNote="触发入口: 点击角色行"
        onClose={() => setRoleOpen(false)}
        footer={
          <button className="btn btn-primary" onClick={() => setRoleOpen(false)}>
            关闭
          </button>
        }
      >
        <p className="body-text small muted">最终动作 = 用户 RBAC ∩ 资源作用域 ∩ ReviewPolicy ∩ 机器权限 ∩ 环境条件 − Deny − humanOnly。任一拒绝即 fail-closed。</p>
      </Modal>

      <Modal
        id="m-policy"
        open={policyOpen}
        title="审核策略"
        triggerNote="触发入口: 点击策略行"
        onClose={() => setPolicyOpen(false)}
        footer={
          <button className="btn btn-primary" onClick={() => setPolicyOpen(false)}>
            关闭
          </button>
        }
      >
        <div className="kv">
          <span className="muted">类型</span>
          <span>FOUR_EYES · V2</span>
          <span className="muted">阶段</span>
          <span>Reviewer → Approver</span>
          <span className="muted">分离</span>
          <span>Approver ≠ 最后修改人</span>
          <span className="muted">阻断检查</span>
          <span>digest 匹配 · 权限有效</span>
        </div>
      </Modal>
    </>
  );
}
