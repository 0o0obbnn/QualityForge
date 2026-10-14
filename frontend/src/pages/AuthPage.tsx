import { useState } from "react";
import { IconCheck, IconMark } from "../app/Icons";
import { ApiError, api } from "../api";
import type { Profile } from "../types";

/**
 * 登录/初始化页（对齐 01-login.html 视觉基线）：
 * 左品牌栏（暖炭 + 琥珀 + 信任锚）+ 右表单区（精密对齐）。
 * 交互逻辑沿用既有 auth 流程（setup 初始化本地管理员 / login 本地账号）。
 */

function readableError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.traceId ? `${error.message}。追踪号 ${error.traceId}` : error.message;
  }
  return "操作失败，请重试。";
}

const TRUST_ANCHORS = [
  { n: "8", label: "模块覆盖" },
  { n: "8", label: "AI 治理能力" },
  { n: "7", label: "角色模板" },
];

interface AuthPageProps {
  mode: "setup" | "login";
  onAuthenticated: (profile: Profile) => void;
}

export function AuthPage({ mode, onAuthenticated }: AuthPageProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantName, setTenantName] = useState("本地质量团队");
  const [workspaceName, setWorkspaceName] = useState("测试项目");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      const payload =
        mode === "setup"
          ? { email, password, tenantName, workspaceName }
          : { email, password };
      const result = await api<Profile>(`/api/v1/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      onAuthenticated(result.data);
    } catch (caught) {
      setError(readableError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell">
      <section className="auth-intro">
        <p className="product-name" style={{ display: "flex", alignItems: "center", gap: 8, margin: "0 0 auto" }}>
          <span className="mark" style={{ width: 26, height: 26, borderRadius: 8, background: "var(--qf-primary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <IconMark />
          </span>
          QualityForge
        </p>
        <h1>把判断权留给测试人员</h1>
        <p>Agent 准备测试策略、计划和用例。你逐版本检查内容、摘要和执行轨迹，再作决定。</p>
        <div className="flex mt-6" style={{ gap: 32, color: "var(--qf-neutral-400)", fontSize: 12.5 }}>
          {TRUST_ANCHORS.map((anchor) => (
            <span key={anchor.label}>
              <b style={{ color: "var(--qf-neutral-50)", fontSize: 18, display: "block" }}>{anchor.n}</b>
              {anchor.label}
            </span>
          ))}
        </div>
      </section>
      <form className="auth-form" onSubmit={submit}>
        <div>
          <h2>{mode === "setup" ? "初始化本地工作台" : "登录审核工作台"}</h2>
          <p>{mode === "setup" ? "数据只保存在当前电脑的 SQLite 文件中。" : "使用本地账号继续审核。"}</p>
        </div>
        {error && (
          <div className="toast err" role="alert" style={{ position: "static", boxShadow: "none" }}>
            <span className="t-dot" />
            {error}
          </div>
        )}
        <div className="field">
          <label>邮箱 <span className="req">*</span></label>
          <input className="input" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" />
        </div>
        <div className="field">
          <label>密码 <span className="req">*</span></label>
          <input className="input" type="password" required minLength={12} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "setup" ? "new-password" : "current-password"} />
        </div>
        {mode === "setup" && (
          <>
            <div className="field">
              <label>团队名称 <span className="req">*</span></label>
              <input className="input" required value={tenantName} onChange={(event) => setTenantName(event.target.value)} />
            </div>
            <div className="field">
              <label>项目名称 <span className="req">*</span></label>
              <input className="input" required value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} />
            </div>
          </>
        )}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? <span className="loading-text">正在处理</span> : mode === "setup" ? "创建并进入" : "登录"}
          {busy ? "" : <IconCheck />}
        </button>
      </form>
    </div>
  );
}
