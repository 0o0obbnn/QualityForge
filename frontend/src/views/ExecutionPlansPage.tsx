import { useEffect, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { frozenManifest } from "../mock/mockData";
import {
  createExecutionPlan,
  fetchExecutionPlans,
  fetchTestPlanOptions,
} from "../services/dataService";
import type { ExecutionPlanRow, TestPlanOption } from "../services/dataService";
import type { Profile } from "../types";
import { IconPlus } from "../app/Icons";
import { Modal } from "../app/Modal";
import { useToast } from "../app/Toast";

/**
 * 执行计划页（对齐 50-execution-plans.html + Sprint 2 T8）：
 * 计划列表（版本/环境/触发/并发/状态）+ 版本冻结清单。
 * 真实模式接 listExecutionPlans/createExecutionPlan（批次四十六补路由）；
 * 版本层字段（环境/触发/并发）为延期面，仅 UI 呈现不提交。
 */

function defaultPlanKey(): string {
  return `EP-${new Date().toISOString().slice(5, 10).replace("-", "")}-${Math.floor(Math.random() * 90 + 10)}`;
}

export function ExecutionPlansPage() {
  const navigate = useNavigate();
  const { profile } = useOutletContext<{ profile: Profile }>();
  const toast = useToast();
  const [rows, setRows] = useState<ExecutionPlanRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [testPlans, setTestPlans] = useState<TestPlanOption[]>([]);
  const [planName, setPlanName] = useState("");
  const [planNameError, setPlanNameError] = useState("");
  const [planKey, setPlanKey] = useState(defaultPlanKey());
  const [testPlanId, setTestPlanId] = useState("");
  const [environment, setEnvironment] = useState("测试");
  const [triggerType, setTriggerType] = useState("手工");
  const [concurrency, setConcurrency] = useState(1);
  const [submitting, setSubmitting] = useState(false);

  const loadRows = () => {
    void fetchExecutionPlans(profile)
      .then(setRows)
      .catch(() => toast("执行计划列表加载失败", "err"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRows();
    void fetchTestPlanOptions(profile).then(setTestPlans).catch(() => setTestPlans([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile]);

  const openCreate = () => {
    setPlanName("");
    setPlanNameError("");
    setPlanKey(defaultPlanKey());
    setTestPlanId(testPlans[0]?.id ?? "");
    setCreateOpen(true);
  };

  const submitCreate = async () => {
    if (!planName.trim()) {
      setPlanNameError("请输入计划名称");
      return;
    }
    if (!testPlanId) return;
    setSubmitting(true);
    try {
      await createExecutionPlan(profile, {
        planKey,
        name: planName.trim(),
        testPlanId,
        environment,
        triggerType,
        concurrency,
      });
      setCreateOpen(false);
      toast("执行计划已创建", "ok");
      setLoading(true);
      loadRows();
    } catch (error) {
      toast(`创建失败：${error instanceof Error ? error.message : "未知错误"}`, "err");
    } finally {
      setSubmitting(false);
    }
  };

  const noTestPlans = testPlans.length === 0;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>执行计划</h1>
          <div className="sub">ExecutionPlanVersion · 版本冻结 + 精确引用</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-primary" onClick={openCreate}>
          <IconPlus />
          新建执行计划
        </button>
      </div>

      <div className="panel">
        <div className="phead"><h2>执行计划列表</h2></div>
        <div className="table-scroll">
          <table>
            <thead><tr><th>计划</th><th>版本</th><th>环境</th><th>触发</th><th>并发</th><th>状态</th></tr></thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={6}>
                    <div className="table-loading">
                      <span />
                      <span />
                      <span />
                    </div>
                  </td>
                </tr>
              )}
              {!loading &&
                rows.map((row, index) => (
                  <tr key={`${row.id}-${index}`} style={{ cursor: "pointer" }} onClick={() => navigate("/execution-monitor")}>
                    <td>
                      <div className="t-title">{row.title}</div>
                      <div className="t-sub mono">{row.id} · 冻结 {row.frozen}</div>
                    </td>
                    <td className="mono">{row.version}</td>
                    <td>{row.environment}</td>
                    <td><span className={`badge ${row.triggerClass}`}>{row.trigger}</span></td>
                    <td className="mono">{row.concurrency}</td>
                    <td><span className={`status ${row.statusClass}`}><span className="d" />{row.status}</span></td>
                  </tr>
                ))}
            </tbody>
          </table>
          <div className="empty-note" hidden={loading || rows.length > 0}>
            <div className="en-title">暂无执行计划</div>点击「新建执行计划」创建并冻结首版基线
          </div>
        </div>
      </div>

      <div className="card mt-6">
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>版本冻结清单 · EP-2026-0811-007 V1</h2>
        <div className="kv" style={{ "--kv-first": "200px" } as React.CSSProperties}>
          {frozenManifest.map((row) => (
            <span key={row.k} style={{ display: "contents" }}>
              <span className="muted">{row.k}</span>
              <span className="mono">{row.v}</span>
            </span>
          ))}
        </div>
        <p className="small muted mt-4">冻结后用例/脚本发布新版本不影响本次执行；新版本需新建计划版本。</p>
      </div>

      <Modal
        id="m-new-exec-plan"
        open={createOpen}
        title="新建执行计划"
        triggerNote="触发入口: 「新建执行计划」按钮"
        onClose={() => setCreateOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setCreateOpen(false)}>
              取消
            </button>
            <button
              className="btn btn-primary"
              onClick={submitCreate}
              disabled={submitting || noTestPlans}
              title={noTestPlans ? "请先在规划域创建测试计划" : undefined}
            >
              {submitting ? "创建中…" : "创建"}
            </button>
          </>
        }
      >
        <div className={`field${planNameError ? " has-err" : ""}`}>
          <label>
            计划名称 <span className="req">*</span>
          </label>
          <input
            className="input"
            placeholder="例如: 结算回归批次"
            value={planName}
            onChange={(event) => {
              setPlanName(event.target.value);
              if (planNameError) setPlanNameError("");
            }}
          />
          <div className="err">请输入计划名称</div>
        </div>
        <div className="field">
          <label>
            计划键 planKey <span className="req">*</span>
          </label>
          <input className="input mono" value={planKey} onChange={(event) => setPlanKey(event.target.value)} />
        </div>
        <div className="field">
          <label>
            关联测试计划 <span className="req">*</span>
          </label>
          <select className="input" value={testPlanId} onChange={(event) => setTestPlanId(event.target.value)}>
            {noTestPlans ? (
              <option value="">（暂无测试计划）</option>
            ) : (
              testPlans.map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {plan.title}
                </option>
              ))
            )}
          </select>
          {noTestPlans && (
            <p className="small" style={{ color: "var(--qf-warning-600)", marginTop: 6 }}>
              当前 Workspace 尚无测试计划，请先到「规划 → 测试计划」创建后再建执行计划。
            </p>
          )}
        </div>
        <div className="field">
          <label>环境（版本层字段 · 延期不提交）</label>
          <select className="input" value={environment} onChange={(event) => setEnvironment(event.target.value)}>
            <option>测试</option>
            <option>预发</option>
            <option>生产</option>
          </select>
        </div>
        <div className="field">
          <label>触发方式（版本层字段 · 延期不提交）</label>
          <select className="input" value={triggerType} onChange={(event) => setTriggerType(event.target.value)}>
            <option>手工</option>
            <option>定时</option>
            <option>CI</option>
          </select>
        </div>
        <div className="field">
          <label>并发（版本层字段 · 延期不提交）</label>
          <input
            className="input mono"
            type="number"
            min={1}
            value={concurrency}
            onChange={(event) => setConcurrency(Math.max(1, Number(event.target.value) || 1))}
          />
        </div>
      </Modal>
    </>
  );
}
