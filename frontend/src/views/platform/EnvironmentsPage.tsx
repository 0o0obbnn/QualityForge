import { useEffect, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { quotaRows, runnerRows, secretRows } from "../../mock/mockData";
import { createEnvironment, fetchEnvironments } from "../../services/dataService";
import type { EnvironmentRow } from "../../services/dataService";
import type { Profile } from "../../types";
import { IconPlus } from "../../app/Icons";
import { Modal } from "../../app/Modal";
import { useToast } from "../../app/Toast";

/**
 * 环境与资源页（原型 81-environments.html）
 * Environment / Secret 引用 / Runner / 配额 · Secret 永不显示明文 · 真实模式接 listEnvironments/createEnvironment
 */
export function EnvironmentsPage() {
  const navigate = useNavigate();
  const { profile } = useOutletContext<{ profile: Profile }>();
  const toast = useToast();
  const [rows, setRows] = useState<EnvironmentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [newEnvOpen, setNewEnvOpen] = useState(false);
  const [envDetailOpen, setEnvDetailOpen] = useState(false);
  const [secretOpen, setSecretOpen] = useState(false);
  const [envName, setEnvName] = useState("");
  const [envNameError, setEnvNameError] = useState("");
  const [envType, setEnvType] = useState("测试");
  const [envEndpoint, setEnvEndpoint] = useState("");
  const [envSecret, setEnvSecret] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    void fetchEnvironments(profile)
      .then((data) => {
        if (active) setRows(data);
      })
      .catch(() => {
        if (active) toast("环境列表加载失败", "err");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [toast, profile]);

  const submitNewEnv = async () => {
    if (!envName.trim()) {
      setEnvNameError("请输入名称");
      return;
    }
    setSubmitting(true);
    try {
      await createEnvironment(profile, {
        title: envName.trim(),
        type: envType,
        endpoint: envEndpoint.trim() || "—",
        secret: envSecret || "—",
      });
      setRows((prev) => [
        {
          title: envName.trim(),
          sub: "新建 · 刚刚",
          type: envType,
          endpoint: envEndpoint.trim() || "—",
          secret: envSecret || "—",
          status: "就绪",
          statusClass: "st-done",
        },
        ...prev,
      ]);
      setNewEnvOpen(false);
      setEnvName("");
      setEnvNameError("");
      setEnvType("测试");
      setEnvEndpoint("");
      setEnvSecret("");
      toast("环境已创建", "ok");
    } catch (error) {
      toast(`创建失败：${error instanceof Error ? error.message : "未知错误"}`, "err");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>环境与资源</h1>
          <div className="sub">Environment / Secret 引用 / Runner / 配额 · Secret 永不显示明文 · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-sm btn-ghost" onClick={() => navigate("/platform")}>
          项目
        </button>
        <button className="btn btn-sm btn-ghost" onClick={() => navigate("/platform/governance")}>
          集成与权限
        </button>
        <button className="btn btn-primary" onClick={() => setNewEnvOpen(true)}>
          <IconPlus />
          新建环境
        </button>
      </div>

      <div className="panel">
        <div className="phead">
          <h2>环境</h2>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>环境</th>
                <th>类型</th>
                <th>Endpoint</th>
                <th>Secret 引用</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={5}>
                    <div className="table-loading">
                      <span />
                      <span />
                      <span />
                    </div>
                  </td>
                </tr>
              )}
              {!loading &&
                rows.map((row) => (
                  <tr key={row.title} onClick={() => setEnvDetailOpen(true)}>
                    <td>
                      <div className="t-title">{row.title}</div>
                      <div className="t-sub">{row.sub}</div>
                    </td>
                    <td>
                      <span className="type-tag">{row.type}</span>
                    </td>
                    <td className="mono">{row.endpoint}</td>
                    <td className="mono">{row.secret}</td>
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
          <div className="empty-note" hidden={loading || rows.length > 0}>
            <div className="en-title">暂无环境</div>点击「新建环境」创建
          </div>
        </div>
      </div>

      <div className="grid g3 mt-6">
        <div className="panel">
          <div className="phead">
            <h2>Runner</h2>
          </div>
          <div className="pbody">
            {runnerRows.map((row) => (
              <div className="row" key={row.name} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderTop: "1px solid var(--qf-border)" }}>
                <span className="muted">{row.name}</span>
                <span className={`status ${row.statusClass}`}>
                  <span className="d" />
                  {row.status}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="panel">
          <div className="phead">
            <h2>Secret</h2>
            <span className="hint">只显示引用</span>
          </div>
          <div className="pbody">
            {secretRows.map((row) => (
              <div className="row" key={row.name} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderTop: "1px solid var(--qf-border)" }}>
                <span className="muted">{row.name}</span>
                <span className="mono small" style={row.expired ? { color: "var(--qf-error-500)" } : undefined}>
                  {row.note}
                </span>
              </div>
            ))}
            <button className="btn btn-sm btn-ghost mt-3" onClick={() => setSecretOpen(true)}>
              轮换 Secret
            </button>
          </div>
        </div>
        <div className="panel">
          <div className="phead">
            <h2>配额</h2>
          </div>
          <div className="pbody">
            {quotaRows.map((row, index) => (
              <div className="cov-row" key={row.name} style={index === quotaRows.length - 1 ? { marginBottom: 0 } : undefined}>
                <div className="top">
                  <span className="name">{row.name}</span>
                  <span className="val">{row.val}</span>
                </div>
                <div className="bar">
                  <i style={{ width: row.width }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Modal
        id="m-new-env"
        open={newEnvOpen}
        title="新建环境"
        triggerNote="触发入口: 「新建环境」按钮"
        onClose={() => setNewEnvOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setNewEnvOpen(false)}>
              取消
            </button>
            <button className="btn btn-primary" onClick={submitNewEnv} disabled={submitting}>
              {submitting ? "创建中…" : "创建"}
            </button>
          </>
        }
      >
        <div className={`field${envNameError ? " has-err" : ""}`}>
          <label>
            环境名称 <span className="req">*</span>
          </label>
          <input
            className="input"
            placeholder="例如: pre-prod"
            value={envName}
            onChange={(event) => {
              setEnvName(event.target.value);
              if (envNameError) setEnvNameError("");
            }}
          />
          <div className="err">请输入名称</div>
        </div>
        <div className="field">
          <label>类型</label>
          <select className="input" value={envType} onChange={(event) => setEnvType(event.target.value)}>
            <option>测试</option>
            <option>预发</option>
            <option>生产</option>
          </select>
        </div>
        <div className="field">
          <label>Endpoint</label>
          <input
            className="input"
            type="url"
            placeholder="https://api.example.com"
            value={envEndpoint}
            onChange={(event) => setEnvEndpoint(event.target.value)}
          />
        </div>
        <div className="field">
          <label>Secret 引用</label>
          <select className="input" value={envSecret} onChange={(event) => setEnvSecret(event.target.value)}>
            <option value="">选择 Secret…</option>
            <option>stg-db</option>
            <option>dev-db</option>
          </select>
        </div>
      </Modal>

      <Modal
        id="m-env"
        open={envDetailOpen}
        title="环境详情"
        triggerNote="触发入口: 点击环境行"
        onClose={() => setEnvDetailOpen(false)}
        footer={
          <button className="btn btn-primary" onClick={() => setEnvDetailOpen(false)}>
            关闭
          </button>
        }
      >
        <div className="kv">
          <span className="muted">能力</span>
          <span>Web/API · 故障注入</span>
          <span className="muted">数据策略</span>
          <span>合成数据 · 24h 清理</span>
          <span className="muted">连接</span>
          <span className="mono">secret:stg-db V2 (引用)</span>
        </div>
        <p className="small muted mt-4">环境不保存连接串明文;Secret 元数据与使用权限分离。</p>
      </Modal>

      <Modal
        id="m-secret"
        open={secretOpen}
        title="轮换 Secret"
        width="narrow"
        triggerNote="触发入口: 「轮换 Secret」按钮 · 危险操作确认"
        onClose={() => setSecretOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setSecretOpen(false)}>
              取消
            </button>
            <button
              className="btn btn-danger"
              onClick={() => {
                setSecretOpen(false);
                toast("Secret 轮换已发起(演示)", "err");
              }}
            >
              确认轮换
            </button>
          </>
        }
      >
        <p className="body-text">轮换后旧密钥保留至宽限期结束;业务接口永不返回明文。影响范围: 引用此 Secret 的执行计划将阻塞并提示。</p>
      </Modal>
    </>
  );
}
