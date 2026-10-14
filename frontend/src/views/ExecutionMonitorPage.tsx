import { useEffect, useRef, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { fetchExecutionEvents, fetchExecutionTasks, issueExecutionCommand } from "../services/dataService";
import type { ExecutionTaskRow } from "../types/domain";
import { isTerminal, mergeEvents, type EventEnvelope } from "../services/eventEnvelope";
import { useToast } from "../app/Toast";
import type { Profile } from "../types";

/**
 * 执行监控页（对齐 51-execution-monitor.html + docs/36 §4）：
 * - ExecutionTask 列表（8 状态 + 结果五值 + runner/耗时）
 * - 事件流轮询渲染：2-3s 追加事件，终态即停（docs/36 §3 事件信封抽象）
 * - mock 模式用 mockEventFeed 模拟推送；真实模式 listEvents REST 轮询补读（WS/SSE 未实现为已知降级）
 */

const STATUS_CLASS: Record<string, string> = {
  RUNNING: "st-run",
  COMPLETED: "st-done",
  FAILED: "st-blocked",
  PENDING: "st-backlog",
  QUEUED: "st-backlog",
  CANCELLED: "st-done",
  TIMED_OUT: "st-blocked",
  BLOCKED: "st-blocked",
};

const RESULT_BADGE: Record<string, string> = {
  PASSED: "b-ok",
  FAILED: "b-err",
  SKIPPED: "b-gray",
  ERROR: "b-err",
  INCONCLUSIVE: "b-warn",
};

const KPIS = [
  { label: "总任务", value: "236", note: "批次 B-0711", tone: "" },
  { label: "通过", value: "198", note: "PASSED", tone: "num-ok" },
  { label: "失败", value: "7", note: "FAILED · 与 ERROR 分离", tone: "num-err" },
  { label: "进行中", value: "23", note: "8 SKIPPED · 0 ERROR", tone: "num-acc" },
];

export function ExecutionMonitorPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [tasks, setTasks] = useState<ExecutionTaskRow[]>([]);
  const [events, setEvents] = useState<EventEnvelope[]>([]);
  const [gaps, setGaps] = useState<Array<{ resourceId: string; missing: number[] }>>([]);
  const [streamDone, setStreamDone] = useState(false);
  const feedIndex = useRef(0);

  const reloadTasks = () => {
    void fetchExecutionTasks(profile.workspaceId).then(setTasks).catch(() => undefined);
  };

  /** WP-04 运行命令（批次六十一）：回执是生效唯一事实，toast 呈现 effectiveStatus */
  const runCommand = async (executionTaskId: string, commandType: "PAUSE" | "RESUME" | "CANCEL", reason: string) => {
    try {
      const result = await issueExecutionCommand(executionTaskId, commandType, reason);
      const label = commandType === "PAUSE" ? "已暂停" : commandType === "RESUME" ? "已恢复" : "已取消";
      toast(`${label}（回执 ${result.receipt.effectiveStatus}）`, "ok");
      reloadTasks();
    } catch {
      toast("命令失败，请重试", "err");
    }
  };

  useEffect(() => {
    let active = true;
    void fetchExecutionTasks(profile.workspaceId).then((rows) => {
      if (active) setTasks(rows);
    });
    return () => {
      active = false;
    };
  }, [profile.workspaceId]);

  useEffect(() => {
    if (streamDone) return;
    let active = true;
    // mock 轮询：每 2s 推送一批事件，终态事件到达后停止
    const timer = setInterval(() => {
      void fetchExecutionEvents(profile.workspaceId).then((feed) => {
        if (!active) return;
        const next = feed.slice(feedIndex.current, feedIndex.current + 2);
        if (next.length === 0) {
          setStreamDone(true);
          clearInterval(timer);
          return;
        }
        feedIndex.current += next.length;
        setEvents((prev) => {
          const { merged, gaps: newGaps } = mergeEvents(prev, next);
          setGaps(newGaps);
          return merged;
        });
        const hasTerminal = next.some(
          (event) => event.type === "ExecutionResultRecorded" && isTerminal(String((event.data as { status?: string }).status ?? "")),
        );
        if (hasTerminal && feedIndex.current >= feed.length) {
          setStreamDone(true);
          clearInterval(timer);
        }
      });
    }, 2000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [streamDone, profile.workspaceId]);

  const formatTime = (iso: string) => new Date(iso).toISOString().slice(11, 19);
  const describe = (event: EventEnvelope): string => {
    if (event.type === "ExecutionTaskStatusChanged") {
      const data = event.data as { toStatus?: string; reasonCode?: string };
      return `${event.resourceId} ${data.toStatus} · ${data.reasonCode ?? ""}`;
    }
    if (event.type === "ExecutionResultRecorded") {
      const data = event.data as { status?: string };
      return `${event.resourceId} result=${data.status ?? "?"}`;
    }
    return `${event.resourceId} ${event.type}`;
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>执行监控</h1>
          <div className="sub">ExecutionTask 实时状态 · 事件信封轮询 · mock 演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => navigate("/execution")}>返回执行计划</button>
        <button className="btn btn-ghost" disabled title="重试失败的 attempt（待后端 retry endpoint）">重试失败的 attempt</button>
        <button className="btn btn-primary" onClick={() => navigate("/execution")}>取消批次</button>
      </div>

      <div className="grid g4" style={{ marginBottom: 18 }}>
        {KPIS.map((kpi) => (
          <div className="kpi" key={kpi.label}>
            <div className="label">{kpi.label}</div>
            <div className={`value ${kpi.tone}`}><b>{kpi.value}</b></div>
            <div className="note">{kpi.note}</div>
          </div>
        ))}
      </div>

      <div className="panel">
        <div className="phead">
          <h2>任务列表</h2>
          <span className="hint">attempt 只追加 · 重试不覆盖</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr><th>任务</th><th>attempt</th><th>状态</th><th>用例结果</th><th>Runner</th><th>耗时</th><th>操作</th></tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.id} style={{ cursor: "pointer" }} onClick={() => navigate(`/evidence/${task.id}`)}>
                  <td>
                    <div className="t-title">{task.taskNo}</div>
                    <div className="t-sub mono">{task.id} · {task.scriptVersion}</div>
                  </td>
                  <td className="mono">#{task.attemptNo}</td>
                  <td>
                    <span className={`status ${STATUS_CLASS[task.status] ?? "st-backlog"}`}>
                      <span className="d" />
                      {task.status}
                    </span>
                  </td>
                  <td>
                    {task.result ? <span className={`badge ${RESULT_BADGE[task.result] ?? "b-gray"}`}>{task.result}</span> : <span className="badge b-gray">—</span>}
                  </td>
                  <td className="mono">{task.runnerId}</td>
                  <td className="mono">{task.durationMs ? `${(task.durationMs / 1000).toFixed(1)}s` : "—"}</td>
                  <td>
                    <span style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      {task.status === "RUNNING" && (
                        <button
                          className="btn btn-sm"
                          onClick={(event) => { event.stopPropagation(); void runCommand(task.id, "PAUSE", "人工暂停到安全点"); }}
                        >
                          暂停
                        </button>
                      )}
                      {task.status === "PAUSED" && (
                        <>
                          <button
                            className="btn btn-sm"
                            onClick={(event) => { event.stopPropagation(); void runCommand(task.id, "RESUME", "恢复执行"); }}
                          >
                            恢复
                          </button>
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={(event) => { event.stopPropagation(); void runCommand(task.id, "CANCEL", "人工取消，证据保留"); }}
                          >
                            取消
                          </button>
                        </>
                      )}
                      {task.status === "RUNNING" && (
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={(event) => { event.stopPropagation(); void runCommand(task.id, "CANCEL", "人工取消，证据保留"); }}
                        >
                          取消
                        </button>
                      )}
                      <button
                        className="btn btn-sm btn-ghost"
                        onClick={(event) => { event.stopPropagation(); navigate(`/evidence/${task.id}`); }}
                      >
                        {task.result === "FAILED" || task.result === "ERROR" ? "分析" : task.status === "RUNNING" ? "实时日志" : "证据"}
                      </button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pagination">
            <span className="pg-info">共 236 个任务 · 第 1/59 页</span>
            <button disabled>‹</button><button className="on">1</button><button>2</button><button>3</button><button>›</button>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h2 style={{ fontSize: 14, marginBottom: 8 }}>
          实时事件流 <span className="pulse" />
          <span className="small muted" style={{ fontWeight: 400 }}>（mock：每 2s 追加事件，终态即停）</span>
        </h2>
        <div className="small mono" data-testid="event-stream" style={{ color: "var(--qf-muted-foreground)", minHeight: 60 }}>
          {events.length === 0 ? (
            <div className="small muted">等待事件…</div>
          ) : (
            events.map((event) => (
              <div key={event.eventId}>{formatTime(event.occurredAt)} · {describe(event)}</div>
            ))
          )}
          {streamDone && <div className="small muted" style={{ marginTop: 8 }}>事件流已结束（终态）</div>}
        </div>
        {gaps.length > 0 && (
          <div className="small" style={{ color: "var(--qf-warning-600)", marginTop: 8 }}>
            检测到事件缺口：{gaps.map((gap) => `${gap.resourceId} 缺 sequence [${gap.missing.join(",")}]`).join("；")}——按 docs/36 应 REST 补读
          </div>
        )}
      </div>
    </>
  );
}
