import { useEffect, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { IconPlus } from "../app/Icons";
import { Modal } from "../app/Modal";
import { useToast } from "../app/Toast";
import { createWorkItem, fetchBoardRows } from "../services/dataService";
import { aiRuns, releaseProgress } from "../mock/mockData";
import { AiRunsView } from "./board/AiRunsView";
import { BlockedView } from "./board/BlockedView";
import { ExecutionView } from "./board/ExecutionView";
import { MetricsView } from "./board/MetricsView";
import { ReworkView } from "./board/ReworkView";
import type { BoardRow } from "../types/domain";
import type { Profile } from "../types";

/**
 * 工作看板（对齐 10-board.html + §5.5.9 七类视图）：
 * 视图切换（全部工作项 / AI 工作中 / 退回重做 / 待执行 / 阻塞风险 / 管理视图），
 * 「我的待审核」为独立路由 /reviews（对齐 11-reviews.html）。
 * 全部工作项视图保留 KPI 4 卡 + 筛选 + 表格 + AI 侧栏 + 新建弹窗 + 分派弹窗。
 */

const STATUS_CLASS: Record<BoardRow["status"], string> = {
  review: "st-review",
  run: "st-run",
  blocked: "st-blocked",
  done: "st-done",
  backlog: "st-backlog",
};

const TYPE_CLASS: Record<string, string> = {
  策略: "strategy",
  用例: "case",
  计划: "plan",
  Defect: "defect",
};

const FILTERS = [
  { key: "all", label: "全部" },
  { key: "review", label: "待审核" },
  { key: "running", label: "AI 运行中" },
  { key: "blocked", label: "阻塞" },
  { key: "done", label: "已完成" },
  { key: "mine", label: "我创建的" },
];

const VIEW_TABS = [
  { key: "all", label: "全部工作项" },
  { key: "ai", label: "AI 工作中" },
  { key: "rework", label: "退回重做" },
  { key: "execution", label: "待执行" },
  { key: "blocked", label: "阻塞风险" },
  { key: "metrics", label: "管理视图" },
] as const;

type ViewKey = (typeof VIEW_TABS)[number]["key"];

export function BoardPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [filter, setFilter] = useState("all");
  const [view, setView] = useState<ViewKey>("all");
  const [newItemOpen, setNewItemOpen] = useState(false);
  const [assignRow, setAssignRow] = useState<BoardRow | null>(null);
  const [myItems, setMyItems] = useState<BoardRow[]>([]);
  const [remoteRows, setRemoteRows] = useState<BoardRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let active = true;
    void fetchBoardRows(profile)
      .then((rows) => {
        if (active) setRemoteRows(rows);
      })
      .catch(() => {
        if (active) toast("看板数据加载失败", "err");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [profile, toast]);

  const allRows = [...myItems, ...remoteRows];
  const filtered = filter === "all" ? allRows : filter === "mine" ? myItems : allRows.filter((r) => r.filter === filter);

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const title = (form.elements.namedItem("title") as HTMLInputElement).value;
    const desc = (form.elements.namedItem("desc") as HTMLTextAreaElement).value;
    const type = (form.elements.namedItem("type") as HTMLSelectElement).value;
    const pri = (form.elements.namedItem("pri") as HTMLSelectElement).value as "P0" | "P1" | "P2";
    if (!title.trim()) {
      toast("请输入标题", "err");
      return;
    }
    if (creating) return;
    setCreating(true);
    try {
      const createdId = await createWorkItem(profile, { title, description: desc, workItemType: type, priority: pri });
      // 真实模式返回后端 id（乐观行可直接点击穿透到详情）；mock 模式退回本地编号
      const id = createdId ?? `WI-${9000 + myItems.length + 1}`;
      setMyItems((prev) => [
        {
          id,
          title,
          sub: desc || "由我创建",
          type,
          typeClass: TYPE_CLASS[type] ?? "",
          status: "backlog",
          statusLabel: "待办",
          actor: "我",
          ai: false,
          priority: pri,
          risk: "低",
          due: "—",
          dueOver: false,
          filter: "mine",
          href: `/work-items/${id}`,
        },
        ...prev,
      ]);
      setNewItemOpen(false);
      toast(`工作项 ${id} 已创建并持久化`, "ok");
      form.reset();
    } catch (caught) {
      toast(`创建失败：${caught instanceof Error ? caught.message : "请重试"}`, "err");
    } finally {
      setCreating(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>工作看板</h1>
          <div className="sub">统一查看工作项、AI 运行与待审核事项 · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => toast("视图设置(演示)", "info")}>视图设置</button>
        <button className="btn btn-primary" onClick={() => setNewItemOpen(true)}>
          <IconPlus />新建工作项
        </button>
      </div>

      <div className="tabs" style={{ marginTop: 0, marginBottom: 16 }} role="tablist" aria-label="看板视图">
        {VIEW_TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={view === t.key} className={view === t.key ? "on" : ""} onClick={() => setView(t.key)}>
            {t.label}
          </button>
        ))}
        <button role="tab" aria-selected={false} onClick={() => navigate("/reviews")}>
          我的待审核 <span className="nav-badge">6</span>
        </button>
      </div>

      {view === "ai" && <AiRunsView />}
      {view === "rework" && <ReworkView />}
      {view === "execution" && <ExecutionView />}
      {view === "blocked" && <BlockedView />}
      {view === "metrics" && <MetricsView />}

      {view === "all" && (
        <>
      <div className="grid g4">
        <div className="kpi"><div className="label">待我审核</div><div className="value num-warn"><b>6</b></div><div className="note">其中 2 项今日到期</div></div>
        <div className="kpi"><div className="label">AI 运行中</div><div className="value num-acc"><b>3</b></div><div className="note">策略 · 用例 · 覆盖率</div></div>
        <div className="kpi"><div className="label">今日完成</div><div className="value num-ok"><b>12</b></div><div className="note">4 项经人工批准</div></div>
        <div className="kpi"><div className="label">阻塞</div><div className="value num-err"><b>2</b></div><div className="note">Secret 未授权 · Runner 离线</div></div>
      </div>

      <div className="filters">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className={`chip${filter === f.key ? " on" : ""}`}
            onClick={() => setFilter(f.key)}
            style={f.key === "mine" && myItems.length === 0 ? { display: "none" } : undefined}
          >
            {f.label}
          </button>
        ))}
        <button className="chip" disabled title="归档工作项(演示禁用态)">已归档</button>
        <span className="spacer" />
        <div className="viewswitch">
          <button className="on" onClick={() => toast("已切换为列表视图", "info")}>列表</button>
          <button onClick={() => toast("看板视图(演示): 列视图详见弹窗与组件规范", "info")}>看板</button>
        </div>
      </div>

      <div className="main-grid">
        <div className="panel">
          <div className="table-scroll">
            <table className="board-table">
              <thead>
                <tr><th>工作项</th><th>类型</th><th>状态</th><th>当前执行者</th><th>优先级</th><th>风险</th><th>截止</th><th style={{ width: 80 }}>操作</th></tr>
              </thead>
              <tbody>
                {loading && (
                  <tr>
                    <td colSpan={7}>
                      <div className="table-loading">
                        <div className="row"><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /></div>
                        <div className="row"><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /></div>
                        <div className="row"><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /><span className="qf-skeleton" /></div>
                      </div>
                    </td>
                  </tr>
                )}
                {!loading &&
                  filtered.map((row) => (
                  <tr key={row.id} onClick={() => navigate(row.href)} style={{ cursor: "pointer" }}>
                    <td data-label="工作项">
                      <div className="tid">{row.id}</div>
                      <div className="t-title">{row.title}</div>
                      <div className="t-sub">{row.sub}</div>
                    </td>
                    <td data-label="类型"><span className={`type-tag ${row.typeClass}`}>{row.type}</span></td>
                    <td data-label="状态"><span className={`status ${STATUS_CLASS[row.status]}`}><span className="d" />{row.statusLabel}</span></td>
                    <td data-label="执行者"><div className="actor">{row.ai && <span className="ai-tag">AI</span>}{row.actor}</div></td>
                    <td data-label="优先级"><span className={`pri p${row.priority.slice(1)}`}>{row.priority}</span></td>
                    <td data-label="风险"><span className={`risk ${row.risk === "高" ? "high" : row.risk === "中" ? "mid" : "low"}`}>{row.risk}</span></td>
                    <td data-label="截止" className={`due${row.dueOver ? " over" : ""}`}>{row.due}</td>
                    <td data-label="操作">
                      <button
                        className="btn btn-sm btn-ghost"
                        onClick={(event) => {
                          event.stopPropagation();
                          setAssignRow(row);
                        }}
                      >
                        分派
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!loading && filtered.length === 0 && (
            <div className="empty-note">
              <div className="en-title">没有符合条件的工作项</div>
              试试调整筛选条件,或新建一个工作项
            </div>
          )}
        </div>

        <div className="aside-stack">
          <div className="ai-panel">
            <h2><span className="pulse" />AI 运行中</h2>
            {aiRuns.map((run) => (
              <div key={run.name} className="ai-run">
                <div className="ic">
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
                    <path d="M3 4h10M3 8h10M3 12h6" /><circle cx="13" cy="12" r="1.6" />
                  </svg>
                </div>
                <div>
                  <div className="nm">{run.name}</div>
                  <div className="st">{run.agent}</div>
                  <div className="pr-line"><i style={{ width: `${run.progress}%` }} /></div>
                </div>
              </div>
            ))}
          </div>
          <div className="mini-card">
            <h2>Release 进度 · R-2026.08</h2>
            {releaseProgress.map((r) => (
              <div key={r.k} className="row">
                <span className="k">{r.k}</span>
                <span className={`v${"danger" in r && r.danger ? " txt-err" : ""}`}>{r.v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
        </>
      )}

      <Modal
        id="m-new-item"
        open={newItemOpen}
        title="新建工作项"
        triggerNote="触发入口: 看板页「新建工作项」主按钮 · 提交后在列表顶部展示"
        onClose={() => setNewItemOpen(false)}
        footer={
          <>
            <button type="button" className="btn btn-ghost" onClick={() => setNewItemOpen(false)}>取消</button>
            <button type="submit" form="newItemForm" className="btn btn-primary">创建</button>
          </>
        }
      >
        <form id="newItemForm" onSubmit={handleCreate} noValidate>
          <div className="field">
            <label>标题 <span className="req">*</span></label>
            <input className="input" name="title" required placeholder="例如: 补充退款场景用例" />
            <div className="err">请输入标题</div>
          </div>
          <div className="field">
            <label>描述</label>
            <textarea className="input" name="desc" placeholder="补充说明(可选)" />
          </div>
          <div className="form-row">
            <div className="field">
              <label>类型</label>
              <select className="input" name="type">
                <option>用例</option><option>策略</option><option>计划</option>
                <option>执行</option><option>Defect</option><option>知识</option><option>其他</option>
              </select>
            </div>
            <div className="field">
              <label>优先级</label>
              <select className="input" name="pri"><option>P1</option><option>P0</option><option>P2</option></select>
            </div>
          </div>
        </form>
      </Modal>
      <Modal
        id="m-assign"
        open={assignRow !== null}
        title="分派工作项"
        width="narrow"
        triggerNote={`触发入口: 看板表格行「分派」· ${assignRow?.id ?? ""} ${assignRow?.title ?? ""}`}
        onClose={() => setAssignRow(null)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setAssignRow(null)}>取消</button>
            <button
              className="btn btn-primary"
              onClick={() => {
                if (!assignRow) return;
                setMyItems((prev) =>
                  prev.map((row) => (row.id === assignRow.id ? { ...row, actor: "王测试", ai: false } : row)),
                );
                setRemoteRows((prev) =>
                  prev.map((row) => (row.id === assignRow.id ? { ...row, actor: "王测试", ai: false } : row)),
                );
                toast(`已将 ${assignRow.id} 分派给 王测试（演示，真实分派待后端 assign endpoint）`, "ok");
                setAssignRow(null);
              }}
            >
              确认分派
            </button>
          </>
        }
      >
        <div className="field">
          <label>执行者</label>
          <select className="input" defaultValue="王测试">
            <option>王测试</option>
            <option>李测试</option>
            <option>策略 Agent（AI）</option>
          </select>
        </div>
        <p className="small muted">真实分派依赖后端 assign endpoint（§5.5.10 workitem:assign 能力，契约缺口 P1），本弹窗为演示形态。</p>
      </Modal>
    </>
  );
}
