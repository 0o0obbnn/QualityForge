import { useEffect, useMemo, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { IconCheck, IconExecution, IconPlanning, IconQuality, IconWarn } from "../app/Icons";
import { scriptRows } from "../mock/mockData";
import {
  fetchCases,
  fetchDefects,
  fetchExecutionPlans,
  fetchPlans,
  fetchReport,
  fetchStrategies,
} from "../services/dataService";
import type { Profile } from "../types";

type LoadState = "loading" | "ready" | "partial";

interface ArtifactSnapshot {
  strategies: Awaited<ReturnType<typeof fetchStrategies>>;
  plans: Awaited<ReturnType<typeof fetchPlans>>;
  cases: Awaited<ReturnType<typeof fetchCases>>;
  executions: Awaited<ReturnType<typeof fetchExecutionPlans>>;
  defects: Awaited<ReturnType<typeof fetchDefects>>;
  report: Awaited<ReturnType<typeof fetchReport>> | null;
}

const EMPTY_SNAPSHOT: ArtifactSnapshot = {
  strategies: [],
  plans: [],
  cases: [],
  executions: [],
  defects: [],
  report: null,
};

function toneFromStatus(status: string): "done" | "review" | "active" | "blocked" | "idle" {
  if (/已批准|已发布|COMPLETED|完成|CLOSED/.test(status)) return "done";
  if (/阻塞|失败|STALE/.test(status)) return "blocked";
  if (/进行|ACTIVE|激活/.test(status)) return "active";
  if (/审核|草稿|待批准|待签署/.test(status)) return "review";
  return "idle";
}

export function ArtifactHubPage() {
  const navigate = useNavigate();
  const { profile } = useOutletContext<{ profile: Profile }>();
  const [snapshot, setSnapshot] = useState<ArtifactSnapshot>(EMPTY_SNAPSHOT);
  const [loadState, setLoadState] = useState<LoadState>("loading");

  useEffect(() => {
    let active = true;
    const loaders = [
      fetchStrategies(profile),
      fetchPlans(profile),
      fetchCases(profile),
      fetchExecutionPlans(profile),
      fetchDefects(profile),
      fetchReport(profile),
    ] as const;

    void Promise.allSettled(loaders).then((results) => {
      if (!active) return;
      const [strategies, plans, cases, executions, defects, report] = results;
      setSnapshot({
        strategies: strategies.status === "fulfilled" ? strategies.value : [],
        plans: plans.status === "fulfilled" ? plans.value : [],
        cases: cases.status === "fulfilled" ? cases.value : [],
        executions: executions.status === "fulfilled" ? executions.value : [],
        defects: defects.status === "fulfilled" ? defects.value : [],
        report: report.status === "fulfilled" ? report.value : null,
      });
      setLoadState(results.every((result) => result.status === "fulfilled") ? "ready" : "partial");
    });

    return () => {
      active = false;
    };
  }, [profile]);

  const artifacts = useMemo(() => {
    const strategy = snapshot.strategies[0];
    const plan = snapshot.plans[0];
    const execution = snapshot.executions[0];
    const openDefects = snapshot.defects.filter((item) => item.lifecycle !== "CLOSED");
    return [
      {
        key: "strategy",
        kind: "策略",
        title: strategy?.title ?? "测试策略待创建",
        metric: snapshot.strategies.length ? `${snapshot.strategies.length} 份` : "未产出",
        status: strategy?.status ?? "缺失",
        tone: toneFromStatus(strategy?.status ?? ""),
        dependency: "定义范围、风险、方法与质量标准",
        to: "/planning/strategies",
      },
      {
        key: "plan",
        kind: "计划",
        title: plan?.title ?? "测试计划待创建",
        metric: snapshot.plans.length ? `${snapshot.plans.length} 份` : "未产出",
        status: plan?.status ?? "缺失",
        tone: toneFromStatus(plan?.status ?? ""),
        dependency: "承接策略，编排人员、时间与里程碑",
        to: "/planning/plans",
      },
      {
        key: "cases",
        kind: "用例",
        title: "场景与测试用例",
        metric: snapshot.cases.length ? `${snapshot.cases.length} 条可见` : "未产出",
        status: snapshot.cases.some((item) => item.status.includes("待审核")) ? "待审核" : "已同步",
        tone: snapshot.cases.some((item) => item.status.includes("待审核")) ? "review" as const : "done" as const,
        dependency: "经人工审核后形成正式 TestCaseVersion",
        to: "/planning/cases",
      },
      {
        key: "automation",
        kind: "自动化",
        title: "自动化脚本与测试资产",
        metric: `${scriptRows.length} 个脚本`,
        status: scriptRows.some((item) => item.status.includes("待")) ? "待审核" : "已就绪",
        tone: scriptRows.some((item) => item.status.includes("待")) ? "review" as const : "done" as const,
        dependency: "绑定已批准用例版本，支持可重复执行",
        to: "/automation/scripts",
      },
      {
        key: "execution",
        kind: "执行",
        title: execution?.title ?? "执行计划待创建",
        metric: snapshot.executions.length ? `${snapshot.executions.length} 个批次` : "未产出",
        status: execution?.status ?? "未启动",
        tone: toneFromStatus(execution?.status ?? ""),
        dependency: "冻结计划、环境、脚本与用例版本",
        to: "/execution-monitor",
      },
      {
        key: "defects",
        kind: "缺陷",
        title: "缺陷与处置记录",
        metric: `${openDefects.length} 个未关闭`,
        status: openDefects.some((item) => item.severity === "严重") ? "存在严重缺陷" : "可控",
        tone: openDefects.some((item) => item.severity === "严重") ? "blocked" as const : "done" as const,
        dependency: "由执行证据与结果分析产生并持续回读",
        to: "/quality/defects",
      },
      {
        key: "report",
        kind: "报告",
        title: snapshot.report?.title ?? "测试报告待生成",
        metric: snapshot.report ? "1 份当前报告" : "未产出",
        status: snapshot.report?.ref.includes("草稿") ? "待签署" : "已生成",
        tone: snapshot.report?.ref.includes("草稿") ? "review" as const : "done" as const,
        dependency: "汇总范围、执行、缺陷、风险与放行结论",
        to: "/quality/reports",
      },
    ];
  }, [snapshot]);

  const openCriticalDefects = snapshot.defects.filter(
    (item) => item.severity === "严重" && item.lifecycle !== "CLOSED",
  ).length;
  const pendingCases = snapshot.cases.filter((item) => item.status.includes("待审核")).length;

  return (
    <div className="artifact-hub">
      <div className="page-head artifact-page-head">
        <div>
          <h1>测试产出物</h1>
          <div className="sub">围绕当前 Release 查看策略、计划、用例、执行证据、缺陷和报告</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => navigate("/board")}>查看任务流</button>
        <button className="btn btn-primary" onClick={() => navigate("/quality/reports")}>查看当前报告</button>
      </div>

      <section className="release-overview" aria-label="当前发布测试概览">
        <div className="release-identity">
          <span className="release-label">当前 Release</span>
          <strong>R-2026.08</strong>
          <span className="status st-run"><span className="d" />测试中</span>
        </div>
        <dl className="release-facts">
          <div><dt>测试范围</dt><dd>结算中心</dd></div>
          <div><dt>当前阶段</dt><dd>回归执行</dd></div>
          <div><dt>质量结论</dt><dd className="release-warning">有条件放行</dd></div>
          <div><dt>报告状态</dt><dd>{snapshot.report?.ref.includes("草稿") ? "草稿待签署" : "已生成"}</dd></div>
        </dl>
      </section>

      {loadState === "partial" && (
        <div className="artifact-inline-alert" role="status">
          <IconWarn /> 部分数据暂时不可用，已保留可读取的产出物。
        </div>
      )}

      <div className="artifact-dashboard">
        <section className="artifact-map" aria-labelledby="artifact-map-title">
          <div className="artifact-section-head">
            <div>
              <h2 id="artifact-map-title">产出物链</h2>
              <p>每个节点都是可查看、可审核、可追溯的正式产出物，不只是流程状态。</p>
            </div>
            <span className="artifact-load-state">{loadState === "loading" ? "正在同步" : "已同步"}</span>
          </div>

          <div className="artifact-flow">
            {artifacts.map((artifact, index) => (
              <button
                key={artifact.key}
                className={`artifact-node artifact-node-${artifact.key}`}
                onClick={() => navigate(artifact.to)}
                aria-label={`查看${artifact.kind}: ${artifact.title}`}
              >
                <span className="artifact-node-topline">
                  <span className="artifact-kind">{artifact.kind}</span>
                  <span className={`artifact-state ${artifact.tone}`}>{artifact.status}</span>
                </span>
                <strong>{artifact.title}</strong>
                <span className="artifact-metric">{loadState === "loading" ? "同步中" : artifact.metric}</span>
                <span className="artifact-dependency">{artifact.dependency}</span>
                <span className="artifact-open">打开产出物 <span aria-hidden>→</span></span>
                {index < artifacts.length - 1 && <span className="artifact-connector" aria-hidden />}
              </button>
            ))}
          </div>
        </section>

        <aside className="artifact-focus" aria-labelledby="artifact-focus-title">
          <div className="artifact-focus-head">
            <IconQuality size={18} />
            <h2 id="artifact-focus-title">当前关注</h2>
          </div>

          <div className="focus-verdict">
            <span>Release 建议</span>
            <strong>有条件放行</strong>
            <p>报告已形成草稿，但严重缺陷和故障场景覆盖仍需闭环。</p>
          </div>

          <div className="focus-list">
            <button onClick={() => navigate("/reviews")}>
              <span className="focus-icon review"><IconPlanning size={15} /></span>
              <span><strong>{pendingCases} 条用例待审核</strong><small>审核后才能形成正式版本</small></span>
              <span aria-hidden>→</span>
            </button>
            <button onClick={() => navigate("/quality/defects")}>
              <span className="focus-icon blocked"><IconWarn size={15} /></span>
              <span><strong>{openCriticalDefects} 个严重缺陷未关闭</strong><small>影响当前放行结论</small></span>
              <span aria-hidden>→</span>
            </button>
            <button onClick={() => navigate("/execution-monitor")}>
              <span className="focus-icon active"><IconExecution size={15} /></span>
              <span><strong>网关故障场景待补测</strong><small>环境能力限制已写入报告</small></span>
              <span aria-hidden>→</span>
            </button>
          </div>
        </aside>
      </div>

      <section className="artifact-recents" aria-labelledby="artifact-recents-title">
        <div className="artifact-section-head">
          <div>
            <h2 id="artifact-recents-title">最近产出</h2>
            <p>从版本结果进入详情，任务过程仍保留在任务看板中。</p>
          </div>
        </div>
        <div className="artifact-recent-list">
          {artifacts.slice(0, 4).map((artifact) => (
            <button key={artifact.key} onClick={() => navigate(artifact.to)}>
              <span className={`artifact-result-icon ${artifact.tone}`}>
                {artifact.tone === "done" ? <IconCheck /> : artifact.tone === "blocked" ? <IconWarn /> : <IconPlanning />}
              </span>
              <span className="artifact-result-copy">
                <strong>{artifact.title}</strong>
                <small>{artifact.kind}产出物</small>
              </span>
              <span className="artifact-result-metric">{artifact.metric}</span>
              <span className={`artifact-state ${artifact.tone}`}>{artifact.status}</span>
              <span className="artifact-result-open" aria-hidden>→</span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
