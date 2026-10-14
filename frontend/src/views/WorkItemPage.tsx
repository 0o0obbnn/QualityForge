import { useEffect, useState } from "react";
import { useNavigate, useOutletContext, useParams } from "react-router-dom";
import { Modal } from "../app/Modal";
import { useToast } from "../app/Toast";
import { workItemDetail } from "../mock/mockData";
import {
  createAgentPlan,
  createTaskCard,
  decideAgentPlan,
  fetchAgentPlans,
  fetchTaskCards,
  fetchWorkItemDetail,
} from "../services/dataService";
import type { AgentPlanRow, TaskCardRow } from "../types";
import { IconPlus } from "../app/Icons";
import type { Profile } from "../types";

/**
 * 工作项详情（对齐 12-workitem.html）：
 * 页头（类型 tag + 标题 + 编号 + 状态 + 取消/查看审核队列）+ 两栏（基本信息/AI 运行/事件时间线 | 关联资产/运行指标）
 */

export function WorkItemPage() {
  const { workItemId } = useParams<{ workItemId: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  const [detail, setDetail] = useState(workItemDetail);
  const [notFound, setNotFound] = useState(false);
  // WP-03 任务卡与 AgentPlan（批次六十一）
  const [cards, setCards] = useState<TaskCardRow[]>([]);
  const [plans, setPlans] = useState<AgentPlanRow[]>([]);
  const [cardOpen, setCardOpen] = useState(false);
  const [cardForm, setCardForm] = useState({ objective: "", scope: "", acceptanceCriteria: "", constraints: "无", permissions: "", budgetMinutes: 30 });
  const [planOpen, setPlanOpen] = useState(false);
  const [planCardId, setPlanCardId] = useState("");
  const [planSteps, setPlanSteps] = useState([{ stepKey: "", agentRole: "", description: "" }]);
  const [decideTarget, setDecideTarget] = useState<{ plan: AgentPlanRow; decision: "APPROVE" | "REJECT" } | null>(null);
  const [decideReason, setDecideReason] = useState("");
  const [busy, setBusy] = useState(false);

  const loadCardsAndPlans = () => {
    const id = workItemId ?? "";
    void fetchTaskCards(id).then(setCards).catch(() => setCards([]));
    void fetchAgentPlans(profile, id).then(setPlans).catch(() => setPlans([]));
  };

  useEffect(() => {
    let active = true;
    void fetchWorkItemDetail(profile, workItemId ?? "")
      .then((result) => {
        if (!active) return;
        if (result) {
          setDetail(result);
          setNotFound(false);
        } else {
          setNotFound(true);
        }
      })
      .catch(() => {
        if (active) setNotFound(true);
      });
    return () => {
      active = false;
    };
  }, [profile, workItemId]);

  useEffect(() => {
    loadCardsAndPlans();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile, workItemId]);

  if (notFound) {
    return (
      <>
        <div className="page-head">
          <div>
            <h1>工作项详情</h1>
            <div className="sub mono">{workItemId}</div>
          </div>
        </div>
        <div className="panel">
          <div className="pbody">
            <div className="empty-note" style={{ border: "none" }}>
              <div className="en-title">未找到该工作项</div>
              工作项不存在或已归档（真实模式不虚构数据）。
            </div>
          </div>
        </div>
      </>
    );
  }

  // 演示数据只预置 WI-0246 与 WI-0238；其余 id 显示通用结构（真实模式由 fetchWorkItemDetail 填充）
  const title = workItemId === "WI-0238" ? "执行计划 · 环境 prod-staging" : workItemId === "WI-0246" ? detail.title : `工作项 ${workItemId ?? ""}`;

  return (
    <>
      <div className="page-head">
        <div>
          <div className="flex" style={{ gap: 10 }}>
            <span className={`type-tag ${detail.typeClass}`}>{workItemId === "WI-0238" ? "执行" : detail.type}</span>
            <h1 style={{ fontSize: 20 }}>{title}</h1>
          </div>
          <div className="sub">
            <span className="mono">{workItemId}</span> · 创建于 {detail.createdAt} · 当前执行者{" "}
            <span className="ai-tag">AI</span>{detail.actor}
          </div>
        </div>
        <div className="spacer" />
        {cancelled ? (
          <span className="status st-blocked"><span className="d" />已取消</span>
        ) : (
          <span className="status st-run"><span className="d" />AI 运行中</span>
        )}
        <button className="btn btn-ghost" onClick={() => setCancelOpen(true)} disabled={cancelled}>取消任务</button>
        <button className="btn btn-primary" onClick={() => navigate("/reviews")}>查看审核队列</button>
      </div>

      <div className="two-col">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="panel">
            <div className="phead"><h2>基本信息</h2></div>
            <div className="pbody">
              <div className="kv" style={{ "--kv-first": "130px" } as React.CSSProperties}>
                {detail.basicInfo.map((row) => (
                  <span key={row.k} style={{ display: "contents" }}>
                    <span className="muted">{row.k}</span>
                    <span>
                      {row.k === "优先级" ? (
                        <span className={`pri p${row.v.slice(1)}`}>{row.v}</span>
                      ) : row.k === "风险等级" ? (
                        <span className={`risk ${row.v === "高" ? "high" : row.v === "中" ? "mid" : "low"}`}>{row.v}</span>
                      ) : (
                        row.v
                      )}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="phead"><h2>AI 运行详情</h2><span className="hint">步骤 {detail.run.step} · 已用 {detail.run.elapsed}</span></div>
            <div className="pbody">
              <div className="bar" style={{ marginBottom: 16 }}><i style={{ width: `${detail.run.progress}%` }} /></div>
              <div className="checks">
                {detail.run.checks.map((check) => (
                  <div key={check.label} className={`check ${check.state}`}>
                    <span className="ic">
                      {check.state === "pass" ? (
                        <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="m3 8.5 3 3 7-7" /></svg>
                      ) : check.state === "review" ? (
                        <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8 2.5 13.5 13.5h-11L8 2.5Z" /><path d="M8 7v3M8 12.2v.3" /></svg>
                      ) : (
                        "·"
                      )}
                    </span>
                    {check.label}
                    <span className="verdict">{check.verdict}</span>
                  </div>
                ))}
              </div>
              <a className="ev-link mt-4" href="#trace" onClick={(event) => { event.preventDefault(); toast("Trace 回放见 AI Agent 中心(演示)", "info"); }}>
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M8 2.8v2M8 11.2v2M2.8 8h2M11.2 8h2" /></svg>
                查看 Agent Trace 回放
              </a>
            </div>
          </div>

          <div className="panel">
            <div className="phead"><h2>事件时间线</h2><span className="hint">WorkItemEvent · 只追加</span></div>
            <div className="pbody" style={{ paddingTop: 8 }}>
              <div className="src-trace" style={{ flexDirection: "column", alignItems: "stretch", gap: 10 }}>
                {detail.timeline.map((event) => (
                  <div key={event.at + event.text}>
                    <b className="small">{event.at}</b>
                    <span className={event.current ? "small" : "muted small"} style={event.current ? { marginLeft: 10, color: "var(--qf-accent-600)" } : { marginLeft: 10 }}>
                      {event.text}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="aside-stack">
          <div className="mini-card">
            <h3>关联资产</h3>
            {detail.assets.map((row) => (
              <div key={row.k} className="row">
                <span className="k">{row.k}</span>
                {row.href ? (
                  <a href={row.href} onClick={(event) => { event.preventDefault(); toast(`${row.k} 页面见对应模块(演示)`, "info"); }}>{row.v}</a>
                ) : (
                  <span className="muted">{row.v}</span>
                )}
              </div>
            ))}
          </div>
          <div className="mini-card">
            <h3>运行指标</h3>
            {detail.metrics.map((row) => (
              <div key={row.k} className="row">
                <span className="k">{row.k}</span>
                <span className="mono">{row.v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ===== WP-03 任务卡与 AgentPlan（批次六十一）===== */}
      <div className="panel" style={{ marginTop: 18 }}>
        <div className="phead">
          <h2>任务卡（正式任务输入）</h2>
          <button className="btn btn-sm btn-primary" onClick={() => { setCardForm({ objective: "", scope: "", acceptanceCriteria: "", constraints: "无", permissions: "", budgetMinutes: 30 }); setCardOpen(true); }}>
            <IconPlus /> 固化任务卡
          </button>
        </div>
        <div className="table-scroll">
          <table>
            <thead><tr><th>目标</th><th>范围</th><th>状态</th><th>摘要</th><th>时间</th></tr></thead>
            <tbody>
              {cards.length === 0 && <tr><td colSpan={5} className="muted">暂无任务卡——对话意图须固化为任务卡并经计划批准后才能启动 Session</td></tr>}
              {cards.map((card) => (
                <tr key={card.id}>
                  <td>{card.objective}</td>
                  <td className="muted">{card.scope}</td>
                  <td><span className={`badge ${card.status === "ACTIVE" ? "b-ok" : card.status === "SUPERSEDED" ? "b-gray" : "b-warn"}`}>{card.status}</span></td>
                  <td className="mono small">{card.contentDigest.slice(0, 12)}…</td>
                  <td className="mono small">{card.createdAt.slice(5, 16).replace("T", " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 18 }}>
        <div className="phead">
          <h2>AgentPlan（人工裁决链）</h2>
          <button
            className="btn btn-sm btn-primary"
            disabled={!cards.some((card) => card.status === "SUBMITTED" || card.status === "ACTIVE")}
            onClick={() => {
              const usable = cards.find((card) => card.status === "SUBMITTED" || card.status === "ACTIVE");
              setPlanCardId(usable?.id ?? "");
              setPlanSteps([{ stepKey: "", agentRole: "", description: "" }]);
              setPlanOpen(true);
            }}
          >
            <IconPlus /> 生成计划
          </button>
        </div>
        <div className="table-scroll">
          <table>
            <thead><tr><th>版本</th><th>步骤</th><th>状态</th><th>摘要</th><th>裁决</th></tr></thead>
            <tbody>
              {plans.length === 0 && <tr><td colSpan={5} className="muted">暂无计划——基于已提交任务卡生成，落地即待人工裁决</td></tr>}
              {plans.map((plan) => (
                <tr key={plan.id}>
                  <td className="mono">v{plan.planVersion}</td>
                  <td className="muted small">{plan.steps.map((step) => step.stepKey).join(" → ") || "—"}</td>
                  <td>
                    <span className={`badge ${plan.status === "APPROVED" ? "b-ok" : plan.status === "PENDING_APPROVAL" ? "b-warn" : plan.status === "REJECTED" ? "b-err" : "b-gray"}`}>{plan.status}</span>
                  </td>
                  <td className="mono small" title={plan.contentDigest}>{plan.contentDigest.slice(0, 12)}…</td>
                  <td>
                    {plan.status === "PENDING_APPROVAL" ? (
                      <span style={{ display: "flex", gap: 6 }}>
                        <button className="btn btn-sm" onClick={() => { setDecideTarget({ plan, decision: "APPROVE" }); setDecideReason(""); }}>批准</button>
                        <button className="btn btn-sm btn-ghost" onClick={() => { setDecideTarget({ plan, decision: "REJECT" }); setDecideReason(""); }}>拒绝</button>
                      </span>
                    ) : (
                      <span className="muted small">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        id="m-task-card"
        open={cardOpen}
        title="固化任务卡"
        width="narrow"
        triggerNote="触发入口: 工作项详情「固化任务卡」"
        onClose={() => setCardOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setCardOpen(false)}>取消</button>
            <button
              className="btn btn-primary"
              disabled={busy || !cardForm.objective.trim() || !cardForm.scope.trim() || !cardForm.acceptanceCriteria.trim()}
              onClick={() => {
                setBusy(true);
                void createTaskCard(profile, workItemId ?? "", {
                  objective: cardForm.objective.trim(),
                  scope: cardForm.scope.trim(),
                  acceptanceCriteria: cardForm.acceptanceCriteria.trim(),
                  constraints: cardForm.constraints.trim() || "无",
                  requestedPermissions: cardForm.permissions.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean),
                  budgetMinutes: cardForm.budgetMinutes,
                })
                  .then(() => {
                    setCardOpen(false);
                    toast("任务卡已固化（旧卡被取代）", "ok");
                    loadCardsAndPlans();
                  })
                  .catch(() => toast("固化失败，请重试", "err"))
                  .finally(() => setBusy(false));
              }}
            >
              提交固化
            </button>
          </>
        }
      >
        <label className="small muted" htmlFor="tc-objective">目标</label>
        <input id="tc-objective" value={cardForm.objective} maxLength={2000} onChange={(e) => setCardForm({ ...cardForm, objective: e.target.value })} style={{ width: "100%" }} />
        <label className="small muted" style={{ display: "block", marginTop: 10 }} htmlFor="tc-scope">范围</label>
        <input id="tc-scope" value={cardForm.scope} maxLength={4000} onChange={(e) => setCardForm({ ...cardForm, scope: e.target.value })} style={{ width: "100%" }} />
        <label className="small muted" style={{ display: "block", marginTop: 10 }} htmlFor="tc-accept">验收判据</label>
        <textarea id="tc-accept" value={cardForm.acceptanceCriteria} maxLength={4000} rows={2} onChange={(e) => setCardForm({ ...cardForm, acceptanceCriteria: e.target.value })} style={{ width: "100%" }} />
        <label className="small muted" style={{ display: "block", marginTop: 10 }} htmlFor="tc-constraints">约束</label>
        <input id="tc-constraints" value={cardForm.constraints} maxLength={4000} onChange={(e) => setCardForm({ ...cardForm, constraints: e.target.value })} style={{ width: "100%" }} />
        <label className="small muted" style={{ display: "block", marginTop: 10 }}>申请权限（逗号分隔，可空）</label>
        <input value={cardForm.permissions} placeholder="requirement.write, work_item.create" onChange={(e) => setCardForm({ ...cardForm, permissions: e.target.value })} style={{ width: "100%" }} />
        <label className="small muted" style={{ display: "block", marginTop: 10 }}>预算上限（分钟）</label>
        <input type="number" min={1} value={cardForm.budgetMinutes} onChange={(e) => setCardForm({ ...cardForm, budgetMinutes: Number(e.target.value) || 1 })} style={{ width: 120 }} />
        <div className="small muted" style={{ marginTop: 10 }}>提交即固化：新卡将取代当前有效卡（不可静默扩展，变更走新版本）。</div>
      </Modal>

      <Modal
        id="m-agent-plan"
        open={planOpen}
        title="生成 AgentPlan"
        width="narrow"
        triggerNote="触发入口: 工作项详情「生成计划」"
        onClose={() => setPlanOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setPlanOpen(false)}>取消</button>
            <button
              className="btn btn-primary"
              disabled={busy || !planCardId || planSteps.some((step) => !step.stepKey.trim() || !step.agentRole.trim() || !step.description.trim())}
              onClick={() => {
                setBusy(true);
                void createAgentPlan(workItemId ?? "", planCardId, planSteps.map((step) => ({ stepKey: step.stepKey.trim(), agentRole: step.agentRole.trim(), description: step.description.trim() })))
                  .then(() => {
                    setPlanOpen(false);
                    toast("计划已生成，待人工裁决", "ok");
                    loadCardsAndPlans();
                  })
                  .catch(() => toast("生成失败，请重试", "err"))
                  .finally(() => setBusy(false));
              }}
            >
              生成并提交裁决
            </button>
          </>
        }
      >
        <label className="small muted">基于任务卡</label>
        <select value={planCardId} onChange={(e) => setPlanCardId(e.target.value)} style={{ width: "100%" }}>
          {cards.filter((card) => card.status === "SUBMITTED" || card.status === "ACTIVE").map((card) => (
            <option key={card.id} value={card.id}>{card.objective}（{card.status}）</option>
          ))}
        </select>
        <div style={{ marginTop: 12 }}>
          <label className="small muted">执行步骤（至少一步）</label>
          {planSteps.map((step, index) => (
            <div key={index} style={{ display: "flex", gap: 6, marginTop: 6 }}>
              <input placeholder="步骤键" value={step.stepKey} maxLength={64} onChange={(e) => setPlanSteps(planSteps.map((item, i) => (i === index ? { ...item, stepKey: e.target.value } : item)))} style={{ width: 90 }} />
              <input placeholder="角色" value={step.agentRole} maxLength={64} onChange={(e) => setPlanSteps(planSteps.map((item, i) => (i === index ? { ...item, agentRole: e.target.value } : item)))} style={{ width: 110 }} />
              <input placeholder="描述" value={step.description} maxLength={2000} onChange={(e) => setPlanSteps(planSteps.map((item, i) => (i === index ? { ...item, description: e.target.value } : item)))} style={{ flex: 1 }} />
            </div>
          ))}
          {planSteps.length < 5 && (
            <button className="btn btn-sm btn-ghost" style={{ marginTop: 6 }} onClick={() => setPlanSteps([...planSteps, { stepKey: "", agentRole: "", description: "" }])}>+ 添加步骤</button>
          )}
        </div>
      </Modal>

      <Modal
        id="m-plan-decision"
        open={decideTarget !== null}
        title={decideTarget?.decision === "APPROVE" ? "批准计划" : "拒绝计划"}
        width="narrow"
        triggerNote="触发入口: AgentPlan 行内 批准/拒绝"
        onClose={() => setDecideTarget(null)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setDecideTarget(null)}>取消</button>
            <button
              className={decideTarget?.decision === "APPROVE" ? "btn btn-primary" : "btn btn-danger"}
              disabled={busy || !decideReason.trim()}
              onClick={() => {
                if (!decideTarget) return;
                setBusy(true);
                void decideAgentPlan(decideTarget.plan.id, decideTarget.decision, decideTarget.plan.contentDigest, decideReason.trim())
                  .then((result) => {
                    setDecideTarget(null);
                    toast(`计划已${decideTarget.decision === "APPROVE" ? "批准" : "拒绝"}（${result.planStatus}）`, decideTarget.decision === "APPROVE" ? "ok" : "err");
                    loadCardsAndPlans();
                  })
                  .catch(() => toast("裁决失败，请重试", "err"))
                  .finally(() => setBusy(false));
              }}
            >
              {decideTarget?.decision === "APPROVE" ? "确认批准" : "确认拒绝"}
            </button>
          </>
        }
      >
        <div className="mini-card" style={{ border: "none", padding: 0 }}>
          <div className="row"><span className="k">计划版本</span><span className="v mono">v{decideTarget?.plan.planVersion}</span></div>
          <div className="row"><span className="k">内容摘要</span><span className="v mono">{decideTarget?.plan.contentDigest.slice(0, 24)}…</span></div>
        </div>
        <label className="small muted" style={{ display: "block", marginTop: 10 }} htmlFor="decision-reason">裁决理由（必填）</label>
        <textarea id="decision-reason" value={decideReason} rows={2} maxLength={2000} onChange={(e) => setDecideReason(e.target.value)} style={{ width: "100%" }} />
        <div className="small muted" style={{ marginTop: 8 }}>决定携带计划摘要对账（摘要漂移将 409 拒绝）；批准后任务卡转 ACTIVE，方可启动 Session。</div>
      </Modal>

      <Modal
        id="m-cancel"
        open={cancelOpen}
        title="取消任务"
        width="narrow"
        triggerNote="触发入口: 工作项详情「取消任务」按钮 · 危险操作确认"
        onClose={() => setCancelOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setCancelOpen(false)}>不取消</button>
            <button className="btn btn-danger" onClick={() => { setCancelOpen(false); setCancelled(true); toast("任务已取消,证据保留(演示)", "err"); }}>确认取消</button>
          </>
        }
      >
        <p className="body-text">取消将停止未开始节点,已保存的中间产物与 Trace 保留。运行中节点尽力终止并记录实际状态。</p>
      </Modal>
    </>
  );
}
