import { useEffect, useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { IconCheck, IconChevronDown, IconTrace, IconWarn } from "../app/Icons";
import { Modal } from "../app/Modal";
import { useToast } from "../app/Toast";
import {
  fetchArtifactTabContent,
  fetchReviewQueue,
  publishCaseVersion,
  publishPlanVersion,
  publishStrategyVersion,
  submitReviewDecision,
} from "../services/dataService";
import { queueItems } from "../mock/mockData";
import type { QueueItem } from "../types/domain";
import type { Profile } from "../types";

/**
 * 待我审核（对齐 11-reviews.html）：
 * 队列面板（.qitem 选中态）+ 详情面板（kv + contentDigest + 4 Tab：版本Diff/来源追溯/检查结果/证据）
 * + 批准/退回/拒绝三弹窗 + 审核策略提示条 + 筛选弹窗。
 */

const TYPE_BADGE: Record<QueueItem["typeClass"], string> = {
  strategy: "b-acc",
  case: "b-sec",
  plan: "b-warn",
  code: "b-gray",
  report: "b-ok",
  knowledge: "b-sec",
};

const TAB_LIST = [
  { key: "diff", label: "版本 Diff" },
  { key: "trace", label: "来源追溯" },
  { key: "checks", label: "检查结果" },
  { key: "evidence", label: "证据" },
] as const;

type TabKey = (typeof TAB_LIST)[number]["key"];

export function ReviewsPage() {
  const toast = useToast();
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [items, setItems] = useState<QueueItem[]>(queueItems);
  const [selectedId, setSelectedId] = useState(queueItems[0].id);
  const [tab, setTab] = useState<TabKey>("diff");
  const [filterOpen, setFilterOpen] = useState(false);
  const [approveOpen, setApproveOpen] = useState(false);
  const [reworkOpen, setReworkOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [reworkReason, setReworkReason] = useState("");
  const [reworkDetail, setReworkDetail] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [decided, setDecided] = useState<Record<string, string>>({});
  const [artifactTabs, setArtifactTabs] = useState<Partial<QueueItem["detail"]["tabs"]> | null>(null);
  // WP-05 发布链（批次六十七）：已批准任务的就地发布入口
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishBusy, setPublishBusy] = useState(false);
  const [publishedIds, setPublishedIds] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let active = true;
    void fetchReviewQueue(profile)
      .then((queue) => {
        if (!active) return;
        setItems(queue);
        setSelectedId((current) => (queue.some((item) => item.id === current) ? current : queue[0]?.id ?? ""));
      })
      .catch(() => {
        if (active) setItems(queueItems);
      });
    return () => {
      active = false;
    };
  }, [profile]);

  // T6：选中任务变化时从 getReviewArtifact 拉取 4 Tab 真实内容（真实模式），mock 模式返回 {} 回退演示数据
  useEffect(() => {
    let active = true;
    void fetchArtifactTabContent(profile, selectedId).then((tabs) => {
      if (active) setArtifactTabs(tabs);
    });
    return () => {
      active = false;
    };
  }, [profile, selectedId]);

  const selected = useMemo(() => items.find((item) => item.id === selectedId) ?? items[0], [items, selectedId]);
  const selectedIndex = useMemo(() => Math.max(0, items.findIndex((item) => item.id === selected?.id)), [items, selected]);

  // T6：artifact 拉取到的 Tab 内容优先，未拉到（mock/空）回退 selected.detail.tabs 演示数据
  const tabs = useMemo(() => {
    const fallback = selected?.detail.tabs ?? { diff: [], trace: [], checks: [], evidence: [] };
    if (!artifactTabs) return fallback;
    const merge = <T,>(value: T[] | undefined, base: T[]): T[] => (value && value.length > 0 ? value : base);
    return {
      diff: merge(artifactTabs.diff as typeof fallback.diff | undefined, fallback.diff),
      trace: merge(artifactTabs.trace as typeof fallback.trace | undefined, fallback.trace),
      checks: merge(artifactTabs.checks as typeof fallback.checks | undefined, fallback.checks),
      evidence: merge(artifactTabs.evidence as typeof fallback.evidence | undefined, fallback.evidence),
    };
  }, [selected, artifactTabs]);

  if (!selected) {
    return (
      <>
        <div className="page-head">
          <div>
            <h1>待我审核</h1>
            <div className="sub">ReviewTask 队列 · 审核决定仅限人工</div>
          </div>
        </div>
        <div className="review-layout">
          <div className="panel">
            <div className="phead"><h2>审核队列</h2><span className="hint">0 项待审</span></div>
            <div className="empty-note" style={{ border: "none" }}>
              <div className="en-title">暂无待审核任务</div>
              在任务看板创建并运行工作项后，AI 产出物会进入审核队列。
            </div>
          </div>
        </div>
      </>
    );
  }

  const disabledReason = selected.detail.approveDisabledReason;
  const decidedStatus = decided[selected.id];
  const taskClosed = selected.detail.taskStatus === "APPROVED";
  const publishable =
    taskClosed &&
    ["TEST_STRATEGY", "TEST_PLAN", "TEST_CASE"].includes(selected.detail.artifactTypeCode ?? "") &&
    !publishedIds[selected.id];

  function advanceAfterDecision(currentIndex: number) {
    // H8 连续处理导航：决定后自动聚焦下一项未决定任务
    const next = items.find((item, index) => index > currentIndex && !decided[item.id]);
    if (next) setSelectedId(next.id);
  }

  async function decide(kind: "approve" | "rework" | "reject") {
    const currentIndex = selectedIndex;
    if (kind === "approve") {
      setApproveOpen(false);
      try {
        await submitReviewDecision(selected.id, "APPROVE", selected.detail.digestFull ?? selected.detail.digest, "");
        setDecided((prev) => ({ ...prev, [selected.id]: "已批准" }));
        toast(`已批准 ${selected.title} ${selected.version} · ReviewDecision 已记录`, "ok");
        advanceAfterDecision(currentIndex);
      } catch (caught) {
        toast(`批准失败：${caught instanceof Error ? caught.message : "请重试"}`, "err");
      }
    } else if (kind === "rework") {
      if (!reworkReason || !reworkDetail) {
        toast("请检查必填项", "err");
        return;
      }
      setReworkOpen(false);
      try {
        await submitReviewDecision(selected.id, "REQUEST_CHANGES", selected.detail.digestFull ?? selected.detail.digest, reworkDetail);
        setDecided((prev) => ({ ...prev, [selected.id]: "已退回" }));
        toast(`已退回 · 将创建新版本重新审核`, "ok");
        advanceAfterDecision(currentIndex);
      } catch (caught) {
        toast(`退回失败：${caught instanceof Error ? caught.message : "请重试"}`, "err");
      }
      setReworkReason("");
      setReworkDetail("");
    } else {
      if (!rejectReason) {
        toast("请填写拒绝原因", "err");
        return;
      }
      setRejectOpen(false);
      try {
        await submitReviewDecision(selected.id, "REJECT", selected.detail.digestFull ?? selected.detail.digest, rejectReason);
        setDecided((prev) => ({ ...prev, [selected.id]: "已拒绝" }));
        toast("已拒绝 · 版本进入 REJECTED", "err");
        advanceAfterDecision(currentIndex);
      } catch (caught) {
        toast(`拒绝失败：${caught instanceof Error ? caught.message : "请重试"}`, "err");
      }
      setRejectReason("");
    }
  }

  async function publishSelected() {
    const artifactType = selected.detail.artifactTypeCode;
    const artifactId = selected.detail.artifactId ?? "";
    const versionId = selected.detail.artifactVersion;
    if (!artifactType || !artifactId || !versionId) {
      toast("缺少发布所需版本信息", "err");
      return;
    }
    setPublishBusy(true);
    try {
      const publishMap = {
        TEST_STRATEGY: publishStrategyVersion,
        TEST_PLAN: publishPlanVersion,
        TEST_CASE: publishCaseVersion,
      } as const;
      const result = await publishMap[artifactType as keyof typeof publishMap](artifactId, versionId);
      setPublishedIds((prev) => ({ ...prev, [selected.id]: true }));
      setPublishOpen(false);
      toast(`已发布 ${selected.title} · reviewStatus ${result.reviewStatus}`, "ok");
    } catch (caught) {
      toast(`发布失败：${caught instanceof Error ? caught.message : "请重试"}`, "err");
    } finally {
      setPublishBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>待我审核</h1>
          <div className="sub">ReviewTask 队列 · 审核决定仅限人工 · 原型演示数据</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => setFilterOpen(true)}>
          筛选 <IconChevronDown size={11} />
        </button>
      </div>

      <div className="review-layout">
        <div className="panel">
          <div className="phead">
            <h2>审核队列</h2>
            <span className="hint">{items.length} 项待审</span>
            <span style={{ display: "flex", gap: 6 }}>
              <button
                className="btn btn-sm btn-ghost"
                disabled={selectedIndex <= 0}
                onClick={() => setSelectedId(items[selectedIndex - 1].id)}
              >
                上一项
              </button>
              <button
                className="btn btn-sm btn-ghost"
                disabled={selectedIndex >= items.length - 1}
                onClick={() => setSelectedId(items[selectedIndex + 1].id)}
              >
                下一项
              </button>
            </span>
          </div>
          {items.length === 0 ? (
            <div className="empty-note" style={{ border: "none" }}>
              <div className="en-title">暂无待审核任务</div>
              在任务看板创建并运行工作项后，AI 产出物会进入审核队列。
            </div>
          ) : (
          <div style={{ padding: 14, display: "grid", gap: 8 }}>
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`qitem${item.id === selected.id ? " selected" : ""}`}
                onClick={() => {
                  setSelectedId(item.id);
                  setTab("diff");
                }}
                style={{ border: "1px solid transparent" }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className={`badge ${TYPE_BADGE[item.typeClass]}`}>{item.type}</span>
                  <b style={{ fontSize: 13 }}>{item.title}</b>
                </span>
                <div className="t-sub mt-2 mono">{item.workItemId} · {item.reviewTaskId}</div>
                <div className={`small mt-2 ${item.dueClass === "err" ? "txt-err" : item.dueClass === "warn" ? "txt-warn" : "muted"}`}>
                  {decided[item.id] ?? item.due}
                </div>
              </button>
            ))}
          </div>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="panel">
            <div className="phead" style={{ flexWrap: "wrap" }}>
              <div className="flex">
                <span className={`badge ${TYPE_BADGE[selected.typeClass]}`}>{selected.type}</span>
                <b style={{ fontSize: 16 }}>
                  {selected.title} · Release R-2026.08{" "}
                  <span className="mono muted" style={{ fontWeight: 400, fontSize: 12 }}>{selected.version}</span>
                </b>
              </div>
              <a className="btn btn-sm btn-ghost" href="#queue" onClick={(event) => { event.preventDefault(); document.querySelector(".review-layout .panel")?.scrollIntoView(); }}>
                打开策略列表
              </a>
            </div>
            <div className="pbody">
              <div className="kv" style={{ "--kv-first": "130px" } as React.CSSProperties}>
                <span className="muted">审核任务</span><b>{selected.detail.reviewTask}</b>
                <span className="muted">产出版本</span><b>{selected.detail.artifactVersion}</b>
                <span className="muted">变更摘要</span><span>{selected.detail.changeSummary}</span>
                <span className="muted">AI 参与</span><span>{selected.detail.aiRun}</span>
                <span className="muted">来源基线</span><span>{selected.detail.sourceBaseline}</span>
                {Boolean(selected.detail.minApprovers && selected.detail.minApprovers > 1) && (
                  <>
                    <span className="muted">复核进度</span>
                    <b data-testid="four-eyes-progress">
                      {selected.detail.approvals?.length ?? 0}/{selected.detail.minApprovers} 名审批人已批准 · 双人复核
                    </b>
                  </>
                )}
              </div>
              <div className="mono mt-3" style={{ fontSize: 12, color: "var(--qf-muted-foreground)", background: "var(--qf-secondary-surface)", borderRadius: 8, padding: "8px 10px", display: "inline-block" }}>
                contentDigest: {selected.detail.digest}
              </div>

              <div className="tabs" role="tablist">
                {TAB_LIST.map((t) => (
                  <button key={t.key} role="tab" aria-selected={tab === t.key} className={tab === t.key ? "on" : ""} onClick={() => setTab(t.key)}>
                    {t.label}
                  </button>
                ))}
              </div>

              {tab === "diff" && (
                <div className="tabpane on">
                  <div className="diff-view">
                    <div className="dhead"><div>{selected.version === "V1" ? "V1 (首版)" : `V${Number(selected.version.slice(1)) - 1} (已批准)`}</div><div>{selected.version} (待审核)</div></div>
                    {tabs.diff.map((line, index) => (
                      <div key={index} className={`diff-line ${line.kind !== "plain" ? line.kind : ""}`}>
                        <div>{line.old}</div><div>{line.next}</div>
                      </div>
                    ))}
                    {tabs.diff.length === 0 && (
                      <div className="diff-line"><div>（无变更对照）</div><div>（首版）</div></div>
                    )}
                  </div>
                </div>
              )}

              {tab === "trace" && (
                <div className="tabpane on">
                  <div className="src-trace" style={{ marginTop: 10 }}>
                    {tabs.trace.map((node, index) => (
                      <span key={node.label} style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                        {index > 0 && <span className="arrow">→</span>}
                        <span className={`src-node ${node.state}`}>{node.label}</span>
                      </span>
                    ))}
                  </div>
                  <p className="small muted mt-3">实心 = CONFIRMED 来源 · 虚线 = INFERRED 规则(需人工确认)</p>
                </div>
              )}

              {tab === "checks" && (
                <div className="tabpane on">
                  <div className="checks" style={{ marginTop: 10 }}>
                    {tabs.checks.map((check) => (
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
                </div>
              )}

              {tab === "evidence" && (
                <div className="tabpane on">
                  <div className="evidence-links">
                    {tabs.evidence.map((link) => (
                      <a key={link.label} className="ev-link" href={link.href} onClick={(event) => { event.preventDefault(); toast(`${link.label} 页面见原型对应模块(演示)`, "info"); }}>
                        <IconTrace />{link.label}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex mt-4" style={{ paddingTop: 16, borderTop: "1px solid var(--qf-border)", flexWrap: "wrap" }}>
                <button
                  className={`btn btn-primary${disabledReason || decidedStatus || taskClosed ? " disabled" : ""}`}
                  disabled={Boolean(disabledReason) || Boolean(decidedStatus) || taskClosed}
                  onClick={() => !decidedStatus && !taskClosed && setApproveOpen(true)}
                  title={disabledReason ?? undefined}
                >
                  <IconCheck />批准 {selected.version}
                </button>
                <button className={`btn btn-ghost${decidedStatus || taskClosed ? " disabled" : ""}`} disabled={Boolean(decidedStatus) || taskClosed} onClick={() => setReworkOpen(true)}>
                  退回修改
                </button>
                <button className={`btn btn-danger${decidedStatus || taskClosed ? " disabled" : ""}`} disabled={Boolean(decidedStatus) || taskClosed} onClick={() => setRejectOpen(true)}>
                  拒绝
                </button>
                {publishable && (
                  <button className="btn btn-primary" onClick={() => setPublishOpen(true)}>
                    发布版本
                  </button>
                )}
                {publishedIds[selected.id] && (
                  <button className="btn btn-primary disabled" disabled>
                    已发布
                  </button>
                )}
                <span className="small muted" style={{ marginLeft: "auto" }}>决定将绑定 contentDigest 并只追加记录</span>
              </div>
              {disabledReason && !decidedStatus && (
                <div className="flex mt-3" style={{ fontSize: 12.5, color: "var(--qf-error-600)", background: "var(--qf-error-100)", borderRadius: 8, padding: "8px 12px" }} data-testid="approve-blocked-reasons">
                  <IconWarn />
                  {disabledReason === "STALE_VERSION" ? "此版本已陈旧，请先查看最新版本" : "任务已结，无法再批准"}
                </div>
              )}
              <div className="flex mt-3" style={{ fontSize: 12.5, color: "var(--qf-muted-foreground)", background: "var(--qf-secondary-surface)", borderRadius: 8, padding: "8px 12px" }}>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" style={{ color: "var(--qf-warning-500)", flex: "none" }}>
                  <path d="M8 2.5 13.5 13.5h-11L8 2.5Z" /><path d="M8 7v3M8 12.2v.3" />
                </svg>
                {selected.detail.policyBar}
              </div>
            </div>
          </div>
        </div>
      </div>

      <Modal
        id="m-approve"
        open={approveOpen}
        title="确认批准"
        width="narrow"
        triggerNote={`触发入口: 审核包「批准 ${selected.version}」按钮 · 确认提示类弹窗`}
        onClose={() => setApproveOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setApproveOpen(false)}>取消</button>
            <button className="btn btn-primary" onClick={() => decide("approve")}>确认批准</button>
          </>
        }
      >
        <p className="body-text">
          批准后将绑定当前版本摘要 <span className="mono">{selected.detail.digest}</span>,ReviewDecision 只追加不可撤销。批准不代表外部同步或发布完成。
        </p>
        <div className="field"><label>审核意见(可选)</label><textarea className="input" placeholder="记录你的判断依据" /></div>
      </Modal>

      <Modal
        id="m-rework"
        open={reworkOpen}
        title="退回修改"
        triggerNote="触发入口: 审核包「退回修改」按钮 · 表单类弹窗"
        onClose={() => setReworkOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setReworkOpen(false)}>取消</button>
            <button className="btn btn-primary" onClick={() => decide("rework")}>提交退回</button>
          </>
        }
      >
        <div className="field">
          <label>退回原因 <span className="req">*</span></label>
          <select className="input" value={reworkReason} onChange={(event) => setReworkReason(event.target.value)}>
            <option value="">请选择原因…</option>
            <option>范围需要调整</option>
            <option>风险判断不认可</option>
            <option>来源引用有误</option>
            <option>其他</option>
          </select>
        </div>
        <div className="field">
          <label>详细意见 <span className="req">*</span></label>
          <textarea className="input" value={reworkDetail} onChange={(event) => setReworkDetail(event.target.value)} placeholder="请说明需要修改的内容,AI 将按意见生成新版本" />
        </div>
        <p className="small muted">退回将保留 {selected.version} 与本次决定,创建新版本 V{Number(selected.version.slice(1)) + 1} 重新走检查与审核。</p>
      </Modal>

      <Modal
        id="m-reject"
        open={rejectOpen}
        title="拒绝"
        width="narrow"
        triggerNote="触发入口: 审核包「拒绝」按钮 · 危险操作确认"
        onClose={() => setRejectOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setRejectOpen(false)}>取消</button>
            <button className="btn btn-danger" onClick={() => decide("reject")}>确认拒绝</button>
          </>
        }
      >
        <p className="body-text">拒绝后该版本进入 <b>REJECTED</b> 状态,工作项可重新创建草稿。此操作同样只追加记录。</p>
        <div className="field">
          <label>拒绝原因 <span className="req">*</span></label>
          <textarea className="input" value={rejectReason} onChange={(event) => setRejectReason(event.target.value)} placeholder="将进入审计记录" />
        </div>
      </Modal>

      <Modal
        id="m-publish"
        open={publishOpen}
        title="确认发布"
        width="narrow"
        triggerNote="触发入口: 审核包「发布版本」按钮 · WP-05 资产发布链"
        onClose={() => setPublishOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setPublishOpen(false)}>取消</button>
            <button className="btn btn-primary" disabled={publishBusy} onClick={() => void publishSelected()}>
              确认发布
            </button>
          </>
        }
      >
        <p className="body-text">
          发布将把版本 <span className="mono">{selected.detail.artifactVersion}</span> 置为 <b>PUBLISHED</b> 并回填资产发布指针；
          发布是审核通过后的 Owner 命令（APPROVED → PUBLISHED），正式执行只消费 PUBLISHED 版本。
          若上游基线已变化，发布新版本会使引用旧版本的下游资产失效（STALE）。
        </p>
      </Modal>

      <Modal
        id="m-filter"
        open={filterOpen}
        title="筛选审核队列"
        width="narrow"
        triggerNote="触发入口: 待我审核页「筛选」按钮"
        onClose={() => setFilterOpen(false)}
        footer={
          <button className="btn btn-primary" onClick={() => { setFilterOpen(false); toast("筛选条件已应用(演示)", "ok"); }}>应用</button>
        }
      >
        <div className="field"><label>产出物类型</label><select className="input"><option>全部</option><option>策略 / 计划 / 用例</option><option>代码</option><option>报告 / 知识</option></select></div>
        <div className="field"><label>风险等级</label><select className="input"><option>全部</option><option>高</option><option>中</option><option>低</option></select></div>
        <div className="field"><label>到期时间</label><select className="input"><option>全部</option><option>今日到期</option><option>本周到期</option></select></div>
      </Modal>
    </>
  );
}
