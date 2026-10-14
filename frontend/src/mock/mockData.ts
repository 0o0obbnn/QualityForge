import type { AiRun, BoardRow, QueueItem, WorkItemDetailData } from "../types/domain";

/**
 * Mock 数据（对齐 27 页原型演示数据）：
 * - 审核队列 6 项（11-reviews.html）
 * - 工作项看板 6 行（10-board.html）
 * - 工作项详情 WI-0246（12-workitem.html）
 * - AI 运行面板 3 条 + Release 进度卡（10-board.html）
 * VITE_MOCK=1 时经 mock 层使用；联调窗口开启后切换真实接口（契约见 32-API规范.yaml）。
 * 领域类型统一在 src/types/domain.ts，本文件只承载演示数据。
 */

export const queueItems: QueueItem[] = [
  {
    id: "q1",
    workItemId: "WI-0241",
    reviewTaskId: "RT-4832",
    type: "策略",
    typeClass: "strategy",
    title: "TestStrategy V2",
    version: "V2",
    due: "今日 18:00 到期",
    dueClass: "err",
    detail: {
      reviewTask: "RT-4832 · SINGLE_REVIEW",
      policy: "SINGLE_REVIEW",
      artifactVersion: "TS-2026-0811-0042 · V2",
      changeSummary: "V2: 补充支付网关故障注入范围,调整退出标准",
      aiRun: "策略 Agent · run a9f2c1 · 128s · ¥0.042",
      sourceBaseline: "Req-2026-08-11 V3 · APIContract V7 · KnowledgeEntry K-104",
      digest: "sha256:3f9a…c21e",
      tabs: {
        diff: [
          { kind: "del", old: "范围: 支付流程、对账、风控", next: "范围: 支付流程、对账、风控、网关故障注入" },
          { kind: "add", old: "退出标准: 核心用例通过率 ≥ 基线", next: "退出标准: 核心用例通过率 ≥ 基线, 且网关故障场景全部执行" },
        ],
        trace: [
          { label: "Req-2026-08-11 V3", state: "confirmed" },
          { label: "APIContract V7", state: "confirmed" },
          { label: "BusinessRule BR-12", state: "inferred" },
          { label: "TestStrategy V2", state: "confirmed" },
        ],
        checks: [
          { state: "pass", label: "结构检查 · 范围/风险/方法齐全", verdict: "PASS" },
          { state: "pass", label: "来源引用完整 · 每条风险有 SourceTrace", verdict: "PASS" },
          { state: "review", label: "独立验证 · 网关风险建议人工复核", verdict: "PASS_WITH_REVIEW" },
        ],
        evidence: [
          { label: "策略正文 V2", href: "/planning" },
          { label: "来源需求 V3", href: "/knowledge" },
          { label: "API 契约 V7", href: "/knowledge" },
          { label: "Agent Trace a9f2c1", href: "/agent" },
        ],
      },
      approveDisabledReason: null,
      policyBar: "审核策略: SINGLE_REVIEW · 需要能力 test-strategy.approve · 你的角色 TestLead 已具备",
    },
  },
  {
    id: "q2",
    workItemId: "WI-0243",
    reviewTaskId: "RT-4835",
    type: "用例",
    typeClass: "case",
    title: "支付流程用例包 V3",
    version: "V3",
    due: "明日 12:00",
    dueClass: "warn",
    detail: {
      reviewTask: "RT-4835 · FOUR_EYES",
      policy: "FOUR_EYES",
      artifactVersion: "TC-2026-0812-0031 · V3",
      changeSummary: "V3: 按退回意见补充边界值,重写金额计算用例",
      aiRun: "测试设计 Agent · run b7d4e2 · 96s · ¥0.031",
      sourceBaseline: "Req-2026-08-11 V3 · TestStrategy V2 · APIContract V7",
      digest: "sha256:8c21…f4a7",
      tabs: {
        diff: [
          { kind: "add", old: "用例数: 22", next: "用例数: 24, 新增退款金额边界 2 条" },
          { kind: "del", old: "金额校验: 单一上限", next: "金额校验: 上限+下限双向" },
        ],
        trace: [
          { label: "Req-2026-08-11 V3", state: "confirmed" },
          { label: "TestStrategy V2", state: "confirmed" },
          { label: "TestCase V2 退回意见", state: "inferred" },
          { label: "支付流程用例包 V3", state: "confirmed" },
        ],
        checks: [
          { state: "pass", label: "结构检查 · 场景/步骤/断言齐全", verdict: "PASS" },
          { state: "pass", label: "与策略覆盖要求对齐", verdict: "PASS" },
        ],
        evidence: [
          { label: "用例正文 V3", href: "/planning" },
          { label: "DesignTestCase V3", href: "/planning" },
          { label: "Agent Trace b7d4e2", href: "/agent" },
        ],
      },
      approveDisabledReason: "STALE_VERSION",
      policyBar: "审核策略: FOUR_EYES · 需要两名审核人独立通过 · 你是第二审核人",
    },
  },
  {
    id: "q3",
    workItemId: "WI-0244",
    reviewTaskId: "RT-4838",
    type: "计划",
    typeClass: "plan",
    title: "TestPlan V1",
    version: "V1",
    due: "明日 18:00",
    dueClass: "muted",
    detail: {
      reviewTask: "RT-4838 · SINGLE_REVIEW",
      policy: "SINGLE_REVIEW",
      artifactVersion: "TP-2026-0812-0008 · V1",
      changeSummary: "V1: 初版,基于已批准 TestStrategy V2 编排里程碑",
      aiRun: "策略 Agent · run a9f2c1 · 128s · ¥0.042",
      sourceBaseline: "TestStrategy V2 · Release R-2026.08",
      digest: "sha256:d91e…07b2",
      tabs: {
        diff: [
          { kind: "plain", old: "（首版无对照）", next: "（首版无对照）" },
        ],
        trace: [
          { label: "TestStrategy V2", state: "confirmed" },
          { label: "Release R-2026.08", state: "confirmed" },
          { label: "TestPlan V1", state: "confirmed" },
        ],
        checks: [
          { state: "pass", label: "结构检查 · 里程碑/资源/验收准则齐全", verdict: "PASS" },
        ],
        evidence: [
          { label: "计划正文 V1", href: "/planning" },
          { label: "Agent Trace a9f2c1", href: "/agent" },
        ],
      },
      approveDisabledReason: null,
      policyBar: "审核策略: SINGLE_REVIEW · 需要能力 test-plan.approve · 你的角色 TestLead 已具备",
    },
  },
  {
    id: "q4",
    workItemId: "WI-0245",
    reviewTaskId: "RT-4841",
    type: "代码",
    typeClass: "code",
    title: "API 脚本 · 对账 V2",
    version: "V2",
    due: "周四",
    dueClass: "muted",
    detail: {
      reviewTask: "RT-4841 · SINGLE_REVIEW",
      policy: "SINGLE_REVIEW",
      artifactVersion: "AS-2026-0812-0015 · V2",
      changeSummary: "V2: 补充幂等键与超时重试",
      aiRun: "自动化 Agent · run c3e8f5 · 64s · ¥0.028",
      sourceBaseline: "APIContract V7 · TestCase V3",
      digest: "sha256:4b8c…19d6",
      tabs: {
        diff: [
          { kind: "add", old: "重试: 无", next: "重试: 指数退避 3 次" },
          { kind: "add", old: "幂等: 无", next: "幂等: Idempotency-Key 校验" },
        ],
        trace: [
          { label: "APIContract V7", state: "confirmed" },
          { label: "TestCase V3", state: "confirmed" },
          { label: "API 脚本 V2", state: "confirmed" },
        ],
        checks: [
          { state: "pass", label: "语法与契约校验通过", verdict: "PASS" },
        ],
        evidence: [
          { label: "脚本代码 V2", href: "/automation" },
          { label: "Agent Trace c3e8f5", href: "/agent" },
        ],
      },
      approveDisabledReason: null,
      policyBar: "审核策略: SINGLE_REVIEW · 需要能力 automation-script.approve · 你的角色 TestLead 已具备",
    },
  },
  {
    id: "q5",
    workItemId: "WI-0239",
    reviewTaskId: "RT-4844",
    type: "报告",
    typeClass: "report",
    title: "TestReport 草稿",
    version: "V1",
    due: "需签署",
    dueClass: "muted",
    detail: {
      reviewTask: "RT-4844 · SIGN_OFF",
      policy: "SIGN_OFF",
      artifactVersion: "TR-2026-0812-0003 · V1",
      changeSummary: "V1: 覆盖率 62% · 5 项缺陷待裁决",
      aiRun: "分析 Agent · run e1f9a4 · 210s · ¥0.087",
      sourceBaseline: "ExecutionRun E-084 · Defect D-12..16",
      digest: "sha256:f7a2…53c0",
      tabs: {
        diff: [],
        trace: [
          { label: "ExecutionRun E-084", state: "confirmed" },
          { label: "Defect D-12..16", state: "inferred" },
          { label: "TestReport V1", state: "confirmed" },
        ],
        checks: [
          { state: "review", label: "覆盖率口径 · 需人工复核 effective 口径", verdict: "PASS_WITH_REVIEW" },
        ],
        evidence: [
          { label: "报告草稿 V1", href: "/quality" },
          { label: "执行证据 E-084", href: "/execution" },
        ],
      },
      approveDisabledReason: "TASK_CLOSED",
      policyBar: "审核策略: SIGN_OFF · 报告签署绑定证据摘要 · 你的角色 TestLead 已具备",
    },
  },
  {
    id: "q6",
    workItemId: "WI-0250",
    reviewTaskId: "RT-4847",
    type: "知识",
    typeClass: "knowledge",
    title: "知识条目 · 幂等模式",
    version: "V1",
    due: "本周五",
    dueClass: "muted",
    detail: {
      reviewTask: "RT-4847 · SINGLE_REVIEW",
      policy: "SINGLE_REVIEW",
      artifactVersion: "KE-2026-0812-0104 · V1",
      changeSummary: "V1: 支付幂等模式候选条目,待合并 2 条重复候选",
      aiRun: "知识 Agent · run f2b7c9 · 42s · ¥0.019",
      sourceBaseline: "Defect D-12 · API 脚本 V2",
      digest: "sha256:6c1d…88e3",
      tabs: {
        diff: [],
        trace: [
          { label: "Defect D-12", state: "confirmed" },
          { label: "API 脚本 V2", state: "confirmed" },
          { label: "知识条目 K-104", state: "inferred" },
        ],
        checks: [
          { state: "pass", label: "适用/失效条件齐全", verdict: "PASS" },
        ],
        evidence: [
          { label: "条目正文 V1", href: "/knowledge" },
        ],
      },
      approveDisabledReason: null,
      policyBar: "审核策略: SINGLE_REVIEW · 需要能力 knowledge-entry.approve · 你的角色 TestLead 已具备",
    },
  },
  {
    // WP-05 发布链示例（批次六十七）：已批准待发布的策略版本，审核台提供发布入口
    id: "q7",
    workItemId: "WI-0266",
    reviewTaskId: "RT-4901",
    type: "策略",
    typeClass: "strategy",
    title: "TestStrategy V1",
    version: "V1",
    due: "已批准待发布",
    dueClass: "muted",
    detail: {
      reviewTask: "RT-4901 · SINGLE_REVIEW",
      policy: "SINGLE_REVIEW",
      artifactVersion: "8c3f2a61-4b7d-4e29-9c55-1f6e0a2b7d10",
      changeSummary: "已批准待发布：策略首版，发布后正式执行只消费 PUBLISHED 版本",
      aiRun: "策略 Agent · run b7c4d2 · 96s · ¥0.031",
      sourceBaseline: "Req-2026-08-12 V2 · APIContract V7",
      digest: "sha256:7c41…9b02",
      taskStatus: "APPROVED",
      artifactTypeCode: "TEST_STRATEGY",
      artifactId: "5d2e8f47-9a1b-4c63-b8e4-7f0d3a9c2e55",
      minApprovers: 1,
      approvals: [{ actorId: "user-001", decidedAt: "2026-09-05T09:30:00+00:00" }],
      tabs: {
        diff: [],
        trace: [
          { label: "Req-2026-08-12 V2", state: "confirmed" },
          { label: "APIContract V7", state: "confirmed" },
          { label: "TestStrategy V1", state: "confirmed" },
        ],
        checks: [{ state: "pass", label: "审核已通过（APPROVED）", verdict: "PASS" }],
        evidence: [{ label: "产出物正文", href: "/planning" }],
      },
      approveDisabledReason: null,
      policyBar: "审核策略: SINGLE_REVIEW · 已批准 · 发布是审核通过后的 Owner 命令",
    },
  },
];

export const boardRows: BoardRow[] = [
  {
    id: "WI-0241",
    title: "审核 TestStrategy 草稿 · Release R-2026.08",
    sub: "范围 32 项需求 · 3 个风险点待确认",
    type: "策略",
    typeClass: "strategy",
    status: "review",
    statusLabel: "待审核",
    actor: "李测试",
    ai: true,
    priority: "P1",
    risk: "中",
    due: "今日 18:00",
    dueOver: true,
    filter: "review",
    href: "/reviews",
  },
  {
    id: "WI-0243",
    title: "用例包审核 · 支付流程 24 条",
    sub: "DesignTestCase V3 · 来源 Req-2026-08-11",
    type: "用例",
    typeClass: "case",
    status: "review",
    statusLabel: "待审核",
    actor: "王审核",
    ai: true,
    priority: "P1",
    risk: "低",
    due: "明日 12:00",
    dueOver: false,
    filter: "review",
    href: "/reviews",
  },
  {
    id: "WI-0246",
    title: "生成测试计划草稿",
    sub: "依赖策略 V2 已批准 · 里程碑编排中",
    type: "计划",
    typeClass: "plan",
    status: "run",
    statusLabel: "AI 运行中",
    actor: "策略 Agent",
    ai: true,
    priority: "P2",
    risk: "中",
    due: "—",
    dueOver: false,
    filter: "running",
    href: "/work-items/WI-0246",
  },
  {
    id: "WI-0238",
    title: "执行计划 · 环境 prod-staging",
    sub: "BLOCKED: SECRET_ACCESS_DENIED · 缺少 Vault 授权",
    type: "执行",
    typeClass: "",
    status: "blocked",
    statusLabel: "阻塞",
    actor: "Runner 调度",
    ai: true,
    priority: "P1",
    risk: "高",
    due: "已逾期 2h",
    dueOver: true,
    filter: "blocked",
    href: "/work-items/WI-0238",
  },
  {
    id: "WI-0235",
    title: "Defect 草稿 · 对账失败率异常",
    sub: "已批准 V1 · 外部同步待确认",
    type: "Defect",
    typeClass: "defect",
    status: "done",
    statusLabel: "已批准",
    actor: "李测试",
    ai: false,
    priority: "P0",
    risk: "高",
    due: "昨日",
    dueOver: false,
    filter: "done",
    href: "/quality",
  },
  {
    id: "WI-0250",
    title: "知识条目 · 支付幂等模式",
    sub: "候选中 · 待合并 2 条重复候选",
    type: "知识",
    typeClass: "",
    status: "backlog",
    statusLabel: "待办",
    actor: "知识 Agent",
    ai: true,
    priority: "P2",
    risk: "低",
    due: "本周五",
    dueOver: false,
    filter: "backlog",
    href: "/knowledge",
  },
];

export const aiRuns: AiRun[] = [
  { name: "TestStrategy 草稿生成", agent: "策略 Agent · 步骤 4/6 · 128s", step: "4/6", progress: 66 },
  { name: "用例编译 · 支付流程", agent: "测试设计 Agent · 步骤 2/5", step: "2/5", progress: 40 },
  { name: "覆盖率分析", agent: "独立验证 Agent · 等待检查器", step: "等待", progress: 20 },
];

export const releaseProgress = [
  { k: "用例已批准", v: "184 / 236" },
  { k: "策略/计划", v: "策略 ✓ · 计划草稿" },
  { k: "自动化覆盖", v: "62% (示意)" },
  { k: "阻塞项", v: "2", danger: true },
];

export const workItemDetail: WorkItemDetailData = {
  id: "WI-0246",
  type: "计划",
  typeClass: "plan",
  title: "生成测试计划草稿",
  createdAt: "2026-08-11 14:32",
  actor: "策略 Agent",
  ai: true,
  status: "run",
  statusLabel: "AI 运行中",
  basicInfo: [
    { k: "描述", v: "基于已批准 TestStrategy V2,生成 Release R-2026.08 的测试计划草稿,含里程碑、资源与验收准则。" },
    { k: "优先级", v: "P2" },
    { k: "风险等级", v: "中" },
    { k: "关联 Release", v: "R-2026.08" },
    { k: "父工作项", v: "WI-0241 (TestStrategy)" },
    { k: "负责人", v: "李测试 (TestLead)" },
  ],
  run: {
    step: "4/6",
    elapsed: "128s",
    progress: 66,
    checks: [
      { state: "pass" as const, label: "锁定策略版本 TS V2 · 摘要匹配", verdict: "完成" },
      { state: "pass" as const, label: "读取 Release 范围与约束", verdict: "完成" },
      { state: "pass" as const, label: "编排里程碑 DAG", verdict: "完成" },
      { state: "review" as const, label: "生成资源与依赖清单", verdict: "进行中" },
      { state: "pending" as const, label: "起草验收准则", verdict: "排队" },
    ],
  },
  timeline: [
    { at: "14:32", text: "AI 开始运行 · 锁定策略 V2 (run a9f2c1)" },
    { at: "14:33", text: "里程碑 DAG 编排完成" },
    { at: "14:35", text: "结构预检通过 · 进入资源编排" },
    { at: "now", text: "生成资源与依赖清单(进行中)", current: true },
  ],
  assets: [
    { k: "策略", v: "TestStrategy V2", href: "/planning" },
    { k: "需求", v: "Req-2026-08-11 V3", href: "/knowledge" },
    { k: "执行计划", v: "待计划批准", href: undefined },
  ],
  metrics: [
    { k: "Token 用量", v: "24,812" },
    { k: "成本", v: "¥0.042" },
    { k: "尝试次数", v: "attempt 1" },
  ],
};

/* ===== M2 剩余 5 类视图演示数据（§5.5.9 定义驱动，原型参考 50/51/60/62） ===== */

/** 视图 2 AI 工作中（§5.5.9：Agent、当前步骤、耗时、预算、重试和中断入口） */
export const aiRunTasks = [
  { id: "AR-01", name: "TestStrategy 草稿生成", workItemId: "WI-0241", agent: "策略 Agent", step: "4/6", elapsed: "128s", budget: "预算 300s", progress: 66, attempt: "attempt 1" },
  { id: "AR-02", name: "用例编译 · 支付流程", workItemId: "WI-0243", agent: "测试设计 Agent", step: "2/5", elapsed: "43s", budget: "预算 240s", progress: 40, attempt: "attempt 2" },
  { id: "AR-03", name: "覆盖率分析", workItemId: "WI-0246", agent: "独立验证 Agent", step: "等待检查器", elapsed: "—", budget: "预算 180s", progress: 20, attempt: "attempt 1" },
];

/** 视图 3 审核退回/重做（§5.5.9：审核意见、差异、当前修改人） */
export const reworkRows = [
  { id: "RW-01", workItemId: "WI-0244", title: "TestPlan V1 · 里程碑编排", reworkRound: "第 1 轮", reviewComment: "退出标准未覆盖网关故障场景,补充后重新提交", diff: "范围 32→34 项 · 退出标准 +2 条", editor: "AI", editorName: "策略 Agent", status: "REWORK", due: "今日 18:00", over: true },
  { id: "RW-02", workItemId: "WI-0243", title: "支付流程用例包 V3", reworkRound: "第 2 轮", reviewComment: "金额边界用例缺少下限校验分支", diff: "用例 22→24 · 边界 +2", editor: "人工", editorName: "王测试", status: "REWORK", due: "明日 12:00", over: false },
];

/** 视图 4 待执行/执行中（§5.5.9：环境、Release、脚本版本、ExecutionTask） */
export const executionRows = [
  { id: "EX-01", plan: "R-2026.08 回归执行", planId: "EP-2026-0811-007", environment: "staging", release: "R-2026.08", scriptVersion: "settlement_api_flow V2", executionTask: "ET-0812-004", status: "run", statusLabel: "执行中", progress: 62 },
  { id: "EX-02", plan: "对账专项回归", planId: "EP-2026-0728-002", environment: "staging", release: "R-2026.07", scriptVersion: "recon_flow V4", executionTask: "ET-0812-003", status: "queue", statusLabel: "待执行", progress: 0 },
  { id: "EX-03", plan: "支付网关故障注入", planId: "EP-2026-0811-009", environment: "prod-staging", release: "R-2026.08", scriptVersion: "gw-timeout-mock V2", executionTask: "ET-0812-006", status: "blocked", statusLabel: "阻塞", progress: 0 },
];

/** 视图 5 阻塞与风险（§5.5.9：按阻塞原因、责任方、持续时间和恢复条件分组） */
export const blockedGroups = [
  {
    reason: "SECRET_ACCESS_DENIED",
    label: "Secret 未授权",
    count: 2,
    rows: [
      { workItemId: "WI-0238", title: "执行计划 · 环境 prod-staging", owner: "Runner 调度", duration: "2h 15m", recover: "补 Vault 授权后由 Runner 重试" },
      { workItemId: "WI-0247", title: "执行计划 · 环境 staging", owner: "平台管理员", duration: "1h 02m", recover: "环境 Secret 引用绑定" },
    ],
  },
  {
    reason: "RUNNER_OFFLINE",
    label: "Runner 离线",
    count: 1,
    rows: [
      { workItemId: "WI-0248", title: "对账脚本冒烟", owner: "运维 · 张运维", duration: "38m", recover: "Runner 心跳恢复后自动重试(预算 3 次)" },
    ],
  },
];

/** 视图 7 管理视图（§5.5.11 指标：周期/吞吐/在制品/审核积压/返工/AI 采用率；口径=基于事件流） */
export const metricsDashboard = {
  kpis: [
    { label: "Lead Time 中位", value: "3.2d", note: "BACKLOG→DONE · 近 14 天", tone: "num-acc" },
    { label: "Cycle Time 中位", value: "18.4h", note: "首次执行→DONE", tone: "num-ok" },
    { label: "在制品 WIP", value: "9", note: "5 类型合计", tone: "num-warn" },
    { label: "审核积压", value: "6", note: "2 项今日到期", tone: "num-warn" },
    { label: "平均返工", value: "0.8", note: "次/工作项", tone: "num-acc" },
    { label: "AI 采用率", value: "82%", note: "Agent 产出直接采用", tone: "num-ok" },
    { label: "AI 成功率", value: "94%", note: "attempt 1 完成率", tone: "num-ok" },
    { label: "生成→批准", value: "9.6h", note: "产出物中位时长", tone: "num-acc" },
  ],
  distribution: [
    { name: "Lead Time 分布", rows: [["p50", "3.2d"], ["p90", "6.8d"], ["p99", "9.1d"]] },
    { name: "Cycle Time 分布", rows: [["p50", "18.4h"], ["p90", "41h"], ["p99", "63h"]] },
  ],
  note: "指标基于 WorkItemEvent 事件流计算,禁止人工编辑汇总字段(§5.5.11)。本页为演示数据,联调后接统计接口。",
};

/* ===== M3 执行与证据演示数据（原型 51-execution-monitor / 52-evidence） ===== */

/**
 * 执行任务级（契约 ExecutionTask：id/executionPlanVersionId/runnerId/status/startedAt/completedAt）。
 * mock 存储按契约字段；页面展示所需 taskNo/scriptVersion/attemptNo/result/durationMs
 * 由 dataService.mapExecutionTask 聚合（result 经 listExecutionResults join，attempt 经 retry 链）。
 */
export const executionTasks: Array<{
  id: string;
  executionPlanVersionId: string;
  runnerId: string;
  status: string;
  startedAt: string;
  completedAt?: string;
  // mock 扩展（真实模式由 dataService join 结果列表与 testCase/script 元数据）
  taskNo: string;
  scriptVersion: string;
  attemptNo: number;
  result: string | null;
  durationMs: number | null;
}> = [
  { id: "EX-T-3181", executionPlanVersionId: "EP-2026-0811-007-V1", runnerId: "runner-02", status: "COMPLETED", startedAt: "2026-08-18T10:31:57Z", completedAt: "2026-08-18T10:32:00Z", taskNo: "TC-0221 支付成功回调", scriptVersion: "settlement_api_flow V2", attemptNo: 1, result: "PASSED", durationMs: 3200 },
  { id: "EX-T-3182", executionPlanVersionId: "EP-2026-0811-007-V1", runnerId: "runner-02", status: "RUNNING", startedAt: "2026-08-18T10:32:02Z", taskNo: "TC-0222 余额不足", scriptVersion: "settlement_api_flow V2", attemptNo: 1, result: null, durationMs: null },
  { id: "EX-T-3185", executionPlanVersionId: "EP-2026-0811-007-V1", runnerId: "runner-01", status: "FAILED", startedAt: "2026-08-18T10:32:05Z", completedAt: "2026-08-18T10:32:11Z", taskNo: "TC-0225 重复回调幂等", scriptVersion: "settlement_api_flow V2", attemptNo: 2, result: "FAILED", durationMs: 6100 },
  { id: "EX-T-3190", executionPlanVersionId: "EP-2026-0811-007-V1", runnerId: "runner-01", status: "FAILED", startedAt: "2026-08-18T10:32:11Z", completedAt: "2026-08-18T10:32:41Z", taskNo: "TC-0231 网关超时注入", scriptVersion: "gw-timeout-mock", attemptNo: 1, result: "ERROR", durationMs: 30000 },
];

/** 证据页（52-evidence）：断言明细 + 结果元数据 + attempt 历史 */
export const evidenceDetail = {
  title: "TC-0225 重复回调幂等 · attempt #2",
  status: "FAILED",
  checks: [
    { state: "pass", label: "第一次调用返回 200 且 order_no 非空", verdict: "PASS" },
    { state: "pass", label: "幂等键格式校验通过", verdict: "PASS" },
    { state: "pass", label: "响应延迟 ≤ 2s", verdict: "PASS" },
    { state: "review", label: "重复回调返回首次结果 (order_no 一致)", verdict: "FAILED" },
  ],
  evidenceLinks: [
    { label: "请求/响应 JSON", href: "/evidence" },
    { label: "运行日志 (12KB)", href: "/evidence" },
    { label: "Trace 快照", href: "/agent" },
  ],
  metadata: [
    { k: "任务", v: "EX-T-3185 #2" },
    { k: "用例版本", v: "TC-0225 V3" },
    { k: "脚本版本", v: "settlement_api_flow V2" },
    { k: "耗时", v: "6.1s" },
    { k: "结果摘要", v: "sha256:44b2…f01d" },
  ],
  attempts: [
    { no: "#1", text: "FAILED · Runner 超时" },
    { no: "#2", text: "FAILED · 断言 #4" },
  ],
};

/** 事件流（docs/36 §4 ExecutionTask Stream，mock 轮询源） */
export const mockEventFeed: Array<{
  eventId: string;
  type: string;
  sequence: number;
  resourceType: string;
  resourceId: string;
  occurredAt: string;
  data: Record<string, unknown>;
}> = [
  { eventId: "ev-01", type: "ExecutionTaskStatusChanged", sequence: 1, resourceType: "EXECUTION_TASK", resourceId: "EX-T-3181", occurredAt: "2026-08-18T10:32:04Z", data: { fromStatus: "RUNNING", toStatus: "COMPLETED", reasonCode: "DONE" } },
  { eventId: "ev-02", type: "ExecutionTaskStatusChanged", sequence: 1, resourceType: "EXECUTION_TASK", resourceId: "EX-T-3182", occurredAt: "2026-08-18T10:32:06Z", data: { fromStatus: "QUEUED", toStatus: "RUNNING", reasonCode: "STARTED" } },
  { eventId: "ev-03", type: "ExecutionResultRecorded", sequence: 2, resourceType: "EXECUTION_TASK", resourceId: "EX-T-3181", occurredAt: "2026-08-18T10:32:08Z", data: { status: "PASSED", durationMs: 3200 } },
  { eventId: "ev-04", type: "ExecutionResultRecorded", sequence: 2, resourceType: "EXECUTION_TASK", resourceId: "EX-T-3185", occurredAt: "2026-08-18T10:32:11Z", data: { status: "FAILED", durationMs: 6100 } },
];

/* ===== M4 质量域演示数据（原型 60-analyses / 61-defects / 62-reports） ===== */

export const analysisRows = [
  { id: "RA-033", title: "重复回调 order_no 不一致", ref: "引用 3 个 ExecutionResult", confidence: 0.72, status: "review", statusLabel: "待审核" },
  { id: "RA-031", title: "网关超时注入能力缺失", ref: "ERROR 归类", confidence: 0.91, status: "done", statusLabel: "已批准" },
];

export const failureClusters = [
  { id: "FC-08", members: "3 个 FailureAnalysis", fingerprint: "idem-key-mismatch", algorithm: "cluster-v1" },
];

export interface DefectRow {
  id: string;
  title: string;
  sub: string;
  severity: "严重" | "一般";
  lifecycle: string;
  lifecycleClass: string;
  version: string;
  sync: string;
  syncClass: string;
}

export const defectRows: DefectRow[] = [
  { id: "D-0142", title: "重复回调返回不同 order_no", sub: "支付 · 复现步骤 4 条", severity: "严重", lifecycle: "NEW", lifecycleClass: "st-review", version: "V1", sync: "待批准", syncClass: "b-warn" },
  { id: "D-0138", title: "对账失败率异常", sub: "对账 · 已批准 V1", severity: "严重", lifecycle: "IN_PROGRESS", lifecycleClass: "st-run", version: "V1", sync: "已同步 JIRA", syncClass: "b-ok" },
  { id: "D-0135", title: "网关限流提示文案缺失", sub: "网关 · 已关闭", severity: "一般", lifecycle: "CLOSED", lifecycleClass: "st-done", version: "V2", sync: "未同步", syncClass: "b-gray" },
];

export const reportDetail = {
  title: "TestReport · R-2026.08",
  ref: "TR-2026-0812-001 · 草稿 V1",
  kpis: [
    { label: "用例执行", value: "228", sub: "/236", note: "8 SKIPPED · 分母含全部", tone: "" },
    { label: "通过率", value: "96.1%", sub: "", note: "219 PASSED · 7 FAILED", tone: "num-ok" },
    { label: "阻断项", value: "1", sub: "", note: "ERROR 不计入 PASS(已披露)", tone: "num-err" },
  ],
  summary: [
    { k: "范围快照", v: "R-2026.08 · 236 用例版本 · 22 契约操作" },
    { k: "风险摘要", v: "网关限流场景未覆盖(环境限制)" },
    { k: "结论", v: "建议有条件放行,网关故障注入待补测" },
  ],
  gates: [
    { state: "pass", label: "门禁: 核心通过率 ≥ 95%", verdict: "PASS" },
    { state: "pass", label: "门禁: 无未批准 P0 Defect", verdict: "PASS" },
    { state: "review", label: "门禁: 网关故障场景覆盖率 ≥ 90%", verdict: "未达标" },
  ],
};

/* ===== 知识域演示数据（原型 20-sources / 21-api-contracts / 22-knowledge） ===== */

export const sourceSnapshots = [
  { id: "SS-2026-08-11-003", title: "结算中心需求规格 v2.1.docx", type: "文档", version: "fetch #3", status: "已固化", statusClass: "st-done", sensitivity: "内部", sensitivityClass: "b-warn", fetchedAt: "08-11 10:02", digest: "sha256:8c1e…" },
  { id: "SS-2026-08-10-021", title: "OpenAPI · settlement-api.yaml", type: "OpenAPI", version: "fetch #7", status: "已固化", statusClass: "st-done", sensitivity: "公开", sensitivityClass: "b-acc", fetchedAt: "08-10 16:44", digest: "22 个 operation" },
  { id: "SS-2026-08-09-014", title: "网关故障流量观察 08-08", type: "流量", version: "fetch #1", status: "解析中", statusClass: "st-review", sensitivity: "敏感", sensitivityClass: "b-err", fetchedAt: "08-09 22:18", digest: "1,204 条请求" },
];

export const requirementDocs = [
  { id: "REQ-2026-08-11", title: "结算中心需求规格", items: "32 项需求", version: "V3", parseStatus: "已解析", reviewStatus: "已发布", reviewClass: "st-done", rules: "12 条规则" },
  { id: "REQ-2026-07-28", title: "对账服务需求", items: "18 项需求", version: "V2", parseStatus: "已解析", reviewStatus: "待审核", reviewClass: "st-review", rules: "7 条规则" },
];

export const sourceConflicts = [
  { title: "DECLARED vs OBSERVED 冲突", detail: "OpenAPI 声明 POST /settlements 响应必填 fee，但流量观察中 3 条缺失。两套证据并存，禁止自动合并。" },
  { title: "业务规则歧义 · BR-12", detail: "「批量退款上限」在两份需求文档中数值不一致(500 vs 1000 笔)。需人工裁决。" },
];

export const apiContracts = [
  { id: "settlement-api", title: "结算服务 · owningTeam: 支付组", version: "V7", status: "已发布", statusClass: "st-done", ops: 22, baseline: "已锁定", baselineClass: "locked" },
  { id: "reconciliation-api", title: "对账服务 · owningTeam: 数据组", version: "V4", status: "待审核", statusClass: "st-review", ops: 14, baseline: "未锁定", baselineClass: "unlocked" },
];

export const contractOperations = [
  { method: "POST", methodClass: "b-sec", path: "/settlements", source: "DECLARED", sourceClass: "b-acc", stability: "稳定", stabilityClass: "st-done" },
  { method: "GET", methodClass: "b-acc", path: "/settlements/{id}", source: "DECLARED", sourceClass: "b-acc", stability: "稳定", stabilityClass: "st-done" },
  { method: "POST", methodClass: "b-ok", path: "/settlements/{id}/refund", source: "MERGED", sourceClass: "b-warn", stability: "漂移检测", stabilityClass: "st-review" },
];

export const knowledgeEntries = [
  { id: "pay-idempotency", title: "支付幂等模式", sub: "来源: Defect D-0142 + 复盘", category: "模式", version: "V2", status: "已发布", statusClass: "st-done", expiry: "网关升级后失效" },
  { id: "recon-troubleshoot", title: "对账差异排查路径", sub: "knowledgeKey: recon-troubleshoot", category: "经验", version: "V1", status: "已发布", statusClass: "st-done", expiry: "—" },
  { id: "gw-throttle-limits", title: "网关限流阈值速查", sub: "knowledgeKey: gw-throttle-limits", category: "参考", version: "V3", status: "待重评", statusClass: "st-review", expiry: "版本变更" },
  { id: "refund-idempotency-key", title: "退款幂等键规范", sub: "knowledgeKey: refund-idempotency-key", category: "规范", version: "V1", status: "已发布", statusClass: "st-done", expiry: "—" },
];

/* ===== 规划域演示数据（原型 30-strategies / 31-plans / 32-cases） ===== */

export const strategyRows = [
  { id: "TS-2026-0811-0042", title: "结算中心主测试策略", version: "V2", scope: "支付/对账/风控/网关", risks: 4, status: "待审核", statusClass: "st-review", action: "审核" },
  { id: "TS-2026-0728-0017", title: "对账服务专项策略", version: "V1", scope: "对账差异/超时", risks: 2, status: "已批准", statusClass: "st-done", action: "已发布" },
];

export const strategyPreview = [
  { k: "范围", v: "支付流程、对账、风控、网关故障注入" },
  { k: "风险点", v: "4 项 (含新增: 第三方网关限流)" },
  { k: "测试方法", v: "功能 + API 契约 + 故障注入" },
  { k: "准入/退出", v: "核心用例通过率 ≥ 基线 且 网关故障场景全部执行" },
  { k: "环境/数据/自动化/Defect", v: "staging · 合成数据 · API 优先 · 外部同步逐次批准" },
];

export const planRows = [
  { id: "TP-2026-0811-009", title: "结算中心测试计划", version: "V1", lifecycle: "ACTIVE", lifecycleClass: "st-run", milestones: "4 个里程碑", status: "草稿生成中", statusClass: "st-review", depends: "依赖策略 TS V2" },
  { id: "TP-2026-0728-003", title: "对账专项计划", version: "V2", lifecycle: "COMPLETED", lifecycleClass: "st-done", milestones: "3 个里程碑", status: "已批准", statusClass: "st-done", depends: "—" },
];

export const planStages = [
  { no: "M1", name: "用例批准", state: "done", note: "184/236" },
  { no: "M2", name: "自动化代码", state: "done", note: "62%" },
  { no: "M3", name: "回归执行", state: "active", note: "进行中" },
  { no: "M4", name: "质量报告", state: "wait", note: "待签署" },
];

export const caseStages = [
  { no: "01", name: "TestingIR", state: "done", note: "已验证 V4" },
  { no: "02", name: "策略", state: "done", note: "已批准 V2" },
  { no: "03", name: "计划", state: "done", note: "已批准 V1" },
  { no: "04", name: "场景与用例", state: "active", note: "24 条待审核" },
  { no: "05", name: "覆盖分析", state: "wait", note: "等待批准" },
];

export const caseRows = [
  { id: "DC-1021", title: "支付成功·正常扣款回调", sub: "正向 · 步骤 6 · 断言 4", pri: "P1", status: "待审核", statusClass: "st-review", cover: "Req-8.1", coverClass: "b-ok" },
  { id: "DC-1022", title: "余额不足·拒绝并返回错误码", sub: "反向 · 步骤 4 · 断言 3", pri: "P1", status: "待审核", statusClass: "st-review", cover: "BR-12", coverClass: "b-ok" },
  { id: "DC-1023", title: "并发扣款·幂等校验", sub: "边界 · 步骤 5 · 断言 5", pri: "P2", status: "待审核", statusClass: "st-review", cover: "BR-14", coverClass: "b-ok" },
  { id: "DC-1024", title: "网关超时·故障注入", sub: "异常 · 步骤 7 · 断言 6", pri: "P1", status: "待审核", statusClass: "st-review", cover: "缺口", coverClass: "b-err" },
  { id: "DC-1025", title: "重复回调·去重后仅一次入账", sub: "状态机 · 步骤 5 · 断言 4", pri: "P2", status: "已批准", statusClass: "st-done", cover: "SM-3", coverClass: "b-ok" },
  { id: "DC-1026", title: "引用契约 V6 的旧用例", sub: "已批准 · 契约升级 V7 后待重评", pri: "P2", status: "待重评", statusClass: "st-blocked", cover: "STALE", coverClass: "b-err" },
];

export const caseCoverage = [
  { k: "需求覆盖", v: "29 / 32 (90.6%)", pct: 90.6, ok: true },
  { k: "规则覆盖", v: "10 / 12 (83.3%)", pct: 83.3, ok: false },
];

/* ===== 自动化域演示数据（原型 40-scripts / 41-code-review / 42-assets） ===== */

export const scriptRows = [
  { id: "AS-2026-0811-0022", title: "settlement_api_flow.py", sub: "pytest · Python 3.12 · 依赖锁 2f81…", type: "API", version: "V2", boundCases: "8 个 TestCaseVersion", check: "全部通过", checkClass: "b-ok", status: "待代码审核", statusClass: "st-review" },
  { id: "AS-2026-0812-0015", title: "refund_flow_test.py", sub: "pytest · Python 3.12 · 依赖锁 7c19…", type: "API", version: "V1", boundCases: "5 个 TestCaseVersion", check: "2 项警告", checkClass: "b-warn", status: "草稿", statusClass: "st-backlog" },
  { id: "AS-2026-0812-0018", title: "checkout_page_ui.py", sub: "Selenium · Python 3.12", type: "Web", version: "V3", boundCases: "12 个 TestCaseVersion", check: "全部通过", checkClass: "b-ok", status: "已批准", statusClass: "st-done" },
];

export const codeReviewDetail = {
  title: "settlement_api_flow.py · V2",
  type: "API",
  status: "RT-4841 · CODE_REVIEW",
  diffLines: [
    { color: "var(--qf-success-500)", text: "+ def test_refund_idempotency(api):" },
    { color: "var(--qf-success-500)", text: '+     """重复回调只入账一次 (TC-0225)"""' },
    { color: "var(--qf-success-500)", text: "+     resp1 = api.post(\"/settlements/refund\", json=payload, idempotency_key=KEY)" },
    { color: "var(--qf-neutral-500)", text: "      assert resp1.status_code == 200" },
    { color: "var(--qf-success-500)", text: "+     resp2 = api.post(\"/settlements/refund\", json=payload, idempotency_key=KEY)" },
    { color: "var(--qf-error-500)", text: "-     assert resp2.status_code == 409" },
    { color: "var(--qf-success-500)", text: '+     assert resp2.json()["order_no"] == resp1.json()["order_no"]  # 返回首次结果' },
  ],
  checks: [
    { state: "pass" as const, label: "格式 / 类型 / 依赖锁", verdict: "PASS" },
    { state: "pass" as const, label: "契约绑定 · 22 个 operation 引用一致", verdict: "PASS" },
    { state: "review" as const, label: "受控试跑 · 删除类操作未在 staging 授权", verdict: "REVIEW" },
  ],
  reviewInfo: [
    { k: "任务", v: "RT-4841" },
    { k: "策略", v: "CODE_REVIEW" },
    { k: "作者", v: "AI · 自动化 Agent" },
    { k: "摘要", v: "sha256:4b8c…19d6" },
  ],
};

export const assetLocators = [
  { title: "checkout-submit-btn", sub: "结算页 · 提交按钮", selector: "#checkout-submit", status: "VERIFIED", statusClass: "st-done", source: "人工录入" },
  { title: "order-table-row", sub: "订单列表 · 行元素", selector: '[data-testid="order-row"]', status: "DECAYING", statusClass: "st-review", source: "AI 发现" },
];

export const assetMocks = [
  { title: "gw-timeout-mock", sub: "网关超时场景", contract: "settlement-api V7 · op-refund-batch", rule: "header[x-mock]=timeout", status: "已发布", statusClass: "st-done" },
  { title: "insufficient-balance-mock", sub: "余额不足场景", contract: "settlement-api V7 · op-pay", rule: "body[amount]>balance", status: "待审核", statusClass: "st-review" },
];

/* ===== 执行计划域演示数据（原型 50-execution-plans） ===== */

export const executionPlanRows = [
  { id: "EP-2026-0811-007", title: "R-2026.08 回归执行", version: "V1", environment: "staging", trigger: "手工", triggerClass: "b-acc", concurrency: "4", status: "执行中", statusClass: "st-run", frozen: "236 用例版本" },
  { id: "EP-2026-0728-002", title: "对账专项回归", version: "V2", environment: "staging", trigger: "计划", triggerClass: "b-sec", concurrency: "2", status: "已完成", statusClass: "st-done", frozen: "18 用例版本" },
];

export const frozenManifest = [
  { k: "用例版本", v: "236 个 TestCaseVersion · 摘要 8f2a…" },
  { k: "脚本版本", v: "settlement_api_flow V2 · checkout_page_ui V3" },
  { k: "契约基线", v: "settlement V7 · recon V4" },
  { k: "数据/Mock", v: "pay-users v3 · gw-timeout-mock V2" },
  { k: "环境", v: "staging · endpoint 快照 09:30" },
];

/* ---------- Agent 中心（原型 70/71/72 · Sprint 2 T11 · P3 确认入范围） ---------- */

export const skillRows = [
  { id: "requirement-compiler", name: "requirement-compiler", sub: "编译 TestingIR · 输入 outputSchema 版本化", version: "V3", permission: "只读来源", permissionClass: "b-acc", eval: "PASS", evalClass: "b-ok", status: "ACTIVE", statusClass: "st-done" },
  { id: "coverage-analyzer", name: "coverage-analyzer", sub: "覆盖分子/分母分析", version: "V2", permission: "只读", permissionClass: "b-acc", eval: "PASS", evalClass: "b-ok", status: "ACTIVE", statusClass: "st-done" },
  { id: "self-healing-orchestrator", name: "self-healing-orchestrator", sub: "Locator 自愈候选", version: "V1", permission: "候选写入", permissionClass: "b-warn", eval: "待补", evalClass: "b-gray", status: "INACTIVE", statusClass: "st-backlog" },
];

export const agentRows = [
  { id: "qf-supervisor", name: "qf-supervisor", sub: "Gate 0 工作流监督者", duty: "分类/派发/停止/汇总", allowlist: "—", delegates: "3 subagent", status: "ACTIVE", statusClass: "st-done" },
  { id: "qf-requirement-ir", name: "qf-requirement-ir", sub: "需求与 IR Subagent", duty: "需求质量/规则/IR 草稿", allowlist: "5 个 Skill", delegates: "0", status: "ACTIVE", statusClass: "st-done" },
  { id: "qf-test-design", name: "qf-test-design", sub: "测试设计 Subagent", duty: "策略/计划/用例草稿", allowlist: "5 个 Skill", delegates: "0", status: "ACTIVE", statusClass: "st-done" },
  { id: "qf-independent-verifier", name: "qf-independent-verifier", sub: "独立验证 Subagent", duty: "IR/断言/覆盖验证", allowlist: "4 个 Skill", delegates: "0", status: "ACTIVE", statusClass: "st-done" },
];

export const promptRows = [
  { id: "requirement-ir-v3", name: "requirement-ir-v3", sub: "系统提示词 v3 · 参数化", version: "v3", target: "qf-requirement-ir", evalStatus: "Eval PASS", evalClass: "b-ok", publish: "已发布", publishClass: "st-done" },
  { id: "verifier-v2", name: "verifier-v2", sub: "独立验证提示词", version: "v2", target: "qf-independent-verifier", evalStatus: "待重评", evalClass: "b-warn", publish: "草稿", publishClass: "st-review" },
];

export const workflowRows = [
  { id: "gate0-requirement-to-coverage", name: "gate0-requirement-to-coverage", sub: "14 节点 DAG · 1 人工检查点 · 结构验证 PASS · 权限交集 fail-closed" },
];

export const agentKpis = [
  { label: "今日 Session", value: "27", cls: "", note: "Gate 0 链 9 次" },
  { label: "成功率", value: "92.4%", cls: "num-ok", note: "Eval Golden Set v2" },
  { label: "越权拦截", value: "0", cls: "num-err", note: "fail-closed 生效" },
  { label: "今日成本", value: "¥3.42", cls: "num-acc", note: "24,812 token 均值" },
];

export const sessionRows = [
  { id: "a9f2c1", title: "run a9f2c1 · 策略生成", sub: "WI-0246 · qf-test-design · prompt v3", workflow: "gate0-…", status: "运行中", statusClass: "st-run", cost: "¥0.042" },
  { id: "8d31e2", title: "run 8d31e2 · IR 编译", sub: "WI-0241 · qf-requirement-ir", workflow: "gate0-…", status: "完成", statusClass: "st-done", cost: "¥0.118" },
];

export const evalRows = [
  { id: "EV-2026-08-11-01", title: "EV-2026-08-11-01", sub: "Prompt v3 准入评测", target: "requirement-ir v3", dataset: "golden-v2 (120 例)", rate: "92.4%", verdict: "准入通过", verdictClass: "st-done" },
];

export const traceSteps = [
  { done: true, badge: "✓", badgeClass: "b-ok", arrow: true, title: "锁定策略版本 TS V2", time: "0.8s", note: "读取策略正文与摘要,校验 digest 匹配" },
  { done: true, badge: "✓", badgeClass: "b-ok", arrow: false, title: "读取 Release 范围与约束", time: "1.2s", note: "来源: R-2026.08 · 32 需求 · 3 排除项" },
  { done: true, badge: "✓", badgeClass: "b-ok", arrow: false, title: "编排里程碑 DAG", time: "9.4s", note: "产出: 4 里程碑 · 依赖 6 条 · 无环校验通过" },
  { done: false, badge: "", badgeClass: "", arrow: false, title: "生成资源与依赖清单", time: "进行中…", note: "调用 skill: plan-orchestrator v2 · 授权快照 a-9f2", highlight: true },
];

export const traceMeta = [
  { k: "Session", v: "ses_a9f2c1", mono: true },
  { k: "Agent", v: "qf-test-design", mono: false },
  { k: "Prompt", v: "v3", mono: true },
  { k: "Workflow", v: "gate0-…", mono: true },
  { k: "Token", v: "24,812", mono: true },
  { k: "成本", v: "¥0.042", mono: true },
];

export const traceAuth = [
  { k: "技能", v: "allowlist 5", ok: false },
  { k: "网络", v: "deny", ok: true },
  { k: "Secret", v: "无", ok: true },
  { k: "审批权", v: "无", ok: false, danger: true },
];

/* ===== 平台管理域（原型 80/81/82，P3 T12） ===== */

export const workspaceRows = [
  { title: "结算中心", sub: "Workspace · owner: 李测试", key: "settlement", status: "ACTIVE", statusClass: "st-done", release: "R-2026.08" },
  { title: "对账服务", sub: "Workspace · owner: 王审核", key: "recon", status: "ACTIVE", statusClass: "st-done", release: "R-2026.07" },
];

export const releaseRows = [
  { name: "状态", val: "TESTING", statusClass: "st-run", status: true },
  { name: "范围", val: "32 需求 · 236 用例", status: false },
  { name: "计划/实际", val: "08-11 → 08-20", status: false },
];

export const memberRows = [
  { name: "李测试", role: "TestLead" },
  { name: "王审核", role: "TestEngineer" },
  { name: "赵运维", role: "WorkspaceAdmin" },
  { name: "钱观察", role: "ViewerAuditor" },
];

export const envRows = [
  { title: "staging", sub: "测试环境 · 数据策略: 合成", type: "测试", endpoint: "https://staging.settle.internal", secret: "secret:stg-db · V2", status: "可用", statusClass: "st-done" },
  { title: "dev", sub: "开发环境", type: "开发", endpoint: "https://dev.settle.internal", secret: "secret:dev-db · V1", status: "可用", statusClass: "st-done" },
  { title: "prod-staging", sub: "生产预发 · 高风险", type: "预发", endpoint: "https://pre.settle.internal", secret: "secret:pre-db · V3", status: "Secret 过期", statusClass: "st-blocked" },
];

export const runnerRows = [
  { name: "runner-01", status: "ONLINE_IDLE", statusClass: "st-done" },
  { name: "runner-02", status: "ONLINE_BUSY", statusClass: "st-run" },
  { name: "runner-03", status: "HEARTBEAT_LOST", statusClass: "st-blocked" },
];

export const secretRows = [
  { name: "stg-db", note: "V2 · 30 天后过期", expired: false },
  { name: "pre-db", note: "已过期", expired: true },
];

export const quotaRows = [
  { name: "并发 Runner", val: "2 / 8", width: "25%" },
  { name: "月度成本", val: "¥342 / ¥2000", width: "17%" },
];

export const integrationRows = [
  { title: "JIRA · 结算中心", sub: "Defect 同步 · 出站 allowlist", type: "Defect", scope: "workspace:settlement", cred: "cred:jira · V4", status: "已连接", statusClass: "st-done" },
  { title: "GitLab · 测试代码库", sub: "Git 模式脚本", type: "Git", scope: "workspace:settlement", cred: "cred:gitlab · V2", status: "已连接", statusClass: "st-done" },
  { title: "Jenkins · CI 流水线", sub: "Pipeline 触发", type: "CI", scope: "tenant:default", cred: "cred:jenkins · V1", status: "凭据失效", statusClass: "st-blocked" },
];

export const roleRows = [
  { title: "TestLead", scope: "WORKSPACE", duties: "策略/计划审核 · 报告签署", excluded: "租户管理 · Secret 明文" },
  { title: "TestEngineer", scope: "WORKSPACE", duties: "草稿/执行/普通审核", excluded: "高风险单人批准" },
  { title: "WorkspaceAdmin", scope: "WORKSPACE", duties: "成员/环境/集成引用", excluded: "报告签署 · 门禁豁免" },
];

export const policyRows = [
  { title: "SINGLE_REVIEW", risk: "策略/计划/用例 · 低中风险", stage: "1 人审核", separation: "—", version: "V3" },
  { title: "FOUR_EYES", risk: "报告/外部写入 · 高风险", stage: "2 人", separation: "Reviewer ≠ Approver", version: "V2" },
  { title: "CODE_REVIEW", risk: "自动化代码", stage: "代码审核", separation: "非作者审核", version: "V1" },
];

export const auditRows = [
  { time: "10:31:02", action: "review.approve", resource: "TS-…0042 V2", decision: "ALLOW", decisionClass: "b-ok" },
  { time: "10:30:44", action: "external.write", resource: "D-0142 → JIRA", decision: "DENY (未授权)", decisionClass: "b-err" },
  { time: "10:28:17", action: "agent.skill.invoke", resource: "coverage-analyzer v2", decision: "ALLOW", decisionClass: "b-ok" },
];

/* ---------- WP-03 协作对话 mock 台账（批次六十；模块级可变，演示会话内持久） ---------- */

export const conversationRows: Array<{
  id: string
  title: string
  status: string
  releaseId: string | null
  workItemId: string | null
  lastActivityAt: string
}> = [
  { id: "c-refund", title: "退款策略协作", status: "ACTIVE", releaseId: "00000000-0000-4000-8000-000000000001", workItemId: null, lastActivityAt: "2026-08-30T09:30:00+00:00" },
  { id: "c-release", title: "R-2026.09 发布口径对齐", status: "ACTIVE", releaseId: "00000000-0000-4000-8000-000000000001", workItemId: null, lastActivityAt: "2026-08-29T15:00:00+00:00" },
];

export const conversationMessageRows: Array<{
  id: string
  conversationId: string
  actorType: "USER" | "AGENT" | "SYSTEM"
  actorId: string
  messageType: string
  contentRef: string
  contentDigest: string
  dataClass: "PUBLIC" | "INTERNAL" | "CONFIDENTIAL" | "RESTRICTED"
  createdAt: string
}> = [
  { id: "m-1", conversationId: "c-refund", actorType: "USER", actorId: "user-mock", messageType: "TEXT", contentRef: "帮我把退款需求整理成测试策略初稿", contentDigest: "0".repeat(64), dataClass: "INTERNAL", createdAt: "2026-08-30T09:00:00+00:00" },
  { id: "m-2", conversationId: "c-refund", actorType: "AGENT", actorId: "agent-coordinator", messageType: "TEXT", contentRef: "已归纳 3 条业务规则，需要先澄清风控阈值口径（见澄清卡）", contentDigest: "0".repeat(64), dataClass: "INTERNAL", createdAt: "2026-08-30T09:05:00+00:00" },
  { id: "m-3", conversationId: "c-release", actorType: "USER", actorId: "user-mock", messageType: "TEXT", contentRef: "本 Release 的验收判据以哪份基线为准？", contentDigest: "0".repeat(64), dataClass: "CONFIDENTIAL", createdAt: "2026-08-29T15:00:00+00:00" },
];

/* ---------- WP-03 任务卡/计划 + WP-04 命令 mock 台账（批次六十一） ---------- */

export const taskCardRows: Array<{
  id: string
  workItemId: string
  objective: string
  scope: string
  status: "SUBMITTED" | "ACTIVE" | "SUPERSEDED" | "DRAFT"
  contentDigest: string
  createdAt: string
}> = [
  { id: "tc-1", workItemId: "WI-0246", objective: "生成结算中心回归资产", scope: "正向与异常路径", status: "ACTIVE", contentDigest: "a1".repeat(32), createdAt: "2026-08-28T10:00:00+00:00" },
];

export const agentPlanRows: Array<{
  id: string
  workItemId: string
  taskCardId: string
  planVersion: number
  steps: Array<{ stepKey: string; agentRole: string; description: string }>
  status: "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "SUPERSEDED" | "DRAFT"
  contentDigest: string
  createdAt: string
}> = [
  {
    id: "ap-1",
    workItemId: "WI-0246",
    taskCardId: "tc-1",
    planVersion: 1,
    steps: [
      { stepKey: "summarize", agentRole: "coordinator", description: "需求归纳" },
      { stepKey: "cases", agentRole: "case-designer", description: "用例编制" },
    ],
    status: "PENDING_APPROVAL",
    contentDigest: "b2".repeat(32),
    createdAt: "2026-08-28T10:05:00+00:00",
  },
];
