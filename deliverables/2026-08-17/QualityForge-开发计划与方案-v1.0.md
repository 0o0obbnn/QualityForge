# QualityForge 开发计划与方案 v1.0

> 版本：v1.0 ｜ 日期：2026-08-17 ｜ 状态：生效（用户已批准）
> 依据：`docs/03-governance/22-MVP版本规划v2.0.md`、`wall/reviews/stage5-planning/VERDICT.md`、`deliverables/需求全量评审报告-2026-08-15.md`、`deliverables/2026-08-13/QualityForge-问题台账-QF-REQ-001-048.md`
> 范围：V0 Gate 0（已完成）→ V1 单 Workspace 试点（本轮主目标）的全程开发计划、开发方案、Skill 策略与分里程碑验收标准。

---

## 一、现状基线（计划起点）

| 维度 | 事实 | 对计划的影响 |
|---|---|---|
| 需求体系 | 全量评审结论 PASS_WITH_ACTIONS（0 Blocker / 6 Major / 3 高风险），可进入 V1 开发 | 6 项开放决策须在 M1 内关闭 |
| 里程碑 | Stage 5 VERDICT 已终裁：M1 需求与审核收口 → M2 看板工作化 → M3 执行与证据 → M4 分析与报告 → M5 真实模型准入 | 本计划以产物主链为排程骨架（共识 C6） |
| 代码 | 后端 22/108 operation 实现（FastAPI+SQLite）；前端 React 19 + Fluent UI 审核工作台；30 个 Skill 原型带 evals.json | 剩余 86 个 operation 按里程碑增量实现，不追全量 |
| 问题台账 | QF-REQ-001 已修复；003/004/005/006/007/011/025 仍 OPEN；049 起增量台账存在 | 台账偿还与里程碑前置债绑定（见第四节） |
| 硬约束 | C1 本轮不做 PostgreSQL/多用户；C2 真实模型须先有评估闸门；C7 执行=进程内串行+文件证据；C8 评估闸门=回放样本双层形态 | 任何方案不得违反，违反即 fail-closed |

**已生效的前置裁决（不再讨论）**：
1. 角色模型权威源＝05 §5.11（6 角色模板），用户已确认（2026-08-13）。
2. 前端栈基线＝React 19 + Fluent UI 9 + Vite，frontend-stack 话题 4/4 盲评追认，用户已确认（2026-08-13）。
3. QF-REQ-001 整改（WorkItem 6 关键字段补齐四源）置于 M1 之首，用户已确认（2026-08-13）。

---

## 二、版本规划

对齐 `docs/03-governance/22-MVP版本规划v2.0.md`：

| 版本 | 核心问题 | 完成定义 | 状态 |
|---|---|---|---|
| V0 设计/Gate 0 | 产品边界和 AI 治理是否可实现、可验证 | 权威契约一致；Gate 0 原型可静态验证；独立复审给出开发准入结论 | 已完成（Stage 4 审计通过 2026-08-12） |
| V1 单 Workspace 试点 | AI 生产+人工审核是否真实提升效率和质量 | 八模块最小入口贯通；用代表性试点跑通完整证据链并建立基线 | **本轮主目标**，拆解为 Stage 5 M1–M5 |
| V2 团队协同 | 平台能否稳定支持团队、集成和多 Runner | 权限/审核成熟；外部集成、知识反馈、门禁建议与恢复经过实测 | V1 验收后启动 |
| V3 企业规模 | 能否在更大规模提供受控 L3 代理能力 | 容量、安全、韧性、评测和运营 SLO 均有真实证据 | 远期 |

### Stage 5 里程碑排期（验收顺序 ≠ 开工顺序）

| 里程碑 | 主链环节 | 交付内容 | 前置债 |
|---|---|---|---|
| M1 需求与审核收口 | 策略→计划→用例 | 三类产出物「生成→审核→批改→新版本→二次复核」闭环；审核台 12 项最低信息；批准禁用态可见原因 | QF-REQ-001 复核闭环；6 项开放决策关闭 |
| M2 任务看板工作化 | 全环节编排视图 | 7 类看板视图真实数据可筛可分派；八模块导航骨架可路由 | 前端栈裁决已生效 |
| M3 执行与证据 | 执行→结果 | execution-workflow.json 先于业务代码合入；实现 createExecutionPlan / startExecutionPlan / listExecutionResults 三个 operation；不可变证据（文件+digest）+ 人工批准 | QF-REQ-004/015/016/043；存储增量改造（C3）须先完成 |
| M4 分析与报告 | 分析→Defect→报告→知识 | 4 类产出物各一纵向切片；报告反查源头 | QF-REQ-003/011/025 |
| M5 真实模型准入 | 上游生成引擎（分支 A） | 黄金集达标后切换 Provider；Provider 接口超时/重试/降级/成本四项先行；make eval baseline 归档 | QF-REQ-006/017 |

**并行线**：
- 分支 A（真实 Provider 工程 + 坏 provider 防御测试）自 M1 起并行开工，准入验收归 M5；不达标走 Plan B（强化 deterministic 生成链路与断言表达力）。
- 分支 B（质量中心/Defect）为 M4 之后收尾，不并设立项（共识 C4）。
- 存储增量改造（sqlite_store 全量 save() 改增量写/事件追加，共识 C3）为 M3 提供事件流，须在 M3 前完成。

### 本轮明确不做（Stage 5 VERDICT §三）

1. 多用户 / PostgreSQL / RLS（V2；安全前置项未外部化前是硬阻断）。
2. WebSocket / SSE 实时流（重启条件：任务 P95>30s 且需观察中间进度 / 多任务并行 / 多观察者）。
3. 调度框架 / 任务队列 / Redis / 独立聚合表（执行＝进程内串行命令）。
4. 独立重型评估框架与 LLM-judge（触发条件：结构判分漏判语义级质量问题的实测证据）。
5. 可视化 Workflow 设计器、用户上传任意 Skill。
6. 外部缺陷系统双向同步（V2）、企业 CI/CD 门禁。

---

## 三、开发方案

### 3.1 架构与技术栈（沿用既定基线，不引入新技术）

- **后端**：FastAPI + SQLite（uv 管理），分层 `api/v1 → services → db/sqlite_store → providers`（deterministic-local）。
- **前端**：React 19 + Vite + Fluent UI 9；事件渲染层按 `docs/04-architecture/36` §3 通用事件信封设计，传输层可替换而渲染层零改动，暂用 2–3s 轮询 + 终态即停。
- **契约**：`docs/04-architecture/32-API规范.yaml`（108 operations）为前后端共享 OpenAPI 契约，`make contract` 强制校验一致性。
- **治理**：`prototypes/agent-governance/` 声明式 workflow 契约；execution-workflow.json 与 gate0-workflow.json 同构，由 validate.py 统一校验。
- **数据库**：SQLite 本地权威；DDL 与迁移约定见 `docs/04-architecture/38-数据库迁移与种子数据约定.md`。

### 3.2 开发模式：主链驱动的纵向切片

1. 每个里程碑只做一条「从 API 到 UI 可演示」的纵向切片，拒绝按表/按接口横铺。
2. 每个 operation 的实现顺序：OpenAPI 契约核对 → schemas → service（含状态机迁移）→ sqlite_store 持久化 → api 路由 → 前端页面 → pytest + eval。
3. 正式产出物一律「稳定根 + 不可变版本 + 精确摘要绑定批准」；ExecutionResult / Evidence / ReviewDecision / AuthorizationDecision / AuditLog / Agent Trace 只追加。
4. AI 生成物一律过三层证据：确定性检查（Skill 结构判分）→ 独立验证 → 人工审核，三层分别报告，不混同。
5. 事实/推断/决定三层分离贯穿所有模块：执行结果是事实，AI 输出是草稿推断，ReviewTask 批准是决定。
6. 效率指标（Lead/Cycle Time、审核/阻塞时长、AI 成功率与成本、产出物生成到批准时间）采集自事件，不手工录入（裁决 2026-08-14）。

### 3.3 Skill 使用策略

**A. 开发流程 Skill（驱动开发过程）**

| 阶段 | Skill | 用途 |
|---|---|---|
| 开工前 | writing-plans | 每个里程碑拆成可执行实施计划 |
| 实现 | tdd / test-driven-development | 每个 operation 先写 pytest 红用例再实现 |
| 执行计划 | executing-plans / subagent-driven-development | 按检查点推进，独立任务并行分派 |
| 调试 | systematic-debugging | 失败先证据后修复 |
| 安全 | security-review | RBAC 四级边界、fail-closed、Secret 引用每个里程碑过一遍 |
| 完成前 | verification-before-completion | 声称完成前必须跑 `make lint && make contract && make test` 并附输出证据 |
| 评审 | code-review / deep-review / requesting-code-review | 里程碑合入前双轴评审（标准 + 规格） |
| 前端 | e2e-testing | 审核台关键旅程 Playwright 回归 |

**B. 产品流水线 Skill（仓库内 30 个原型，产品本身的能力组件）**

- 需求段：requirement-compiler / requirement-quality-gate / scenario-generator / ir-validator / business-rule-extractor / state-machine-builder
- 设计段：strategy-planner / plan-orchestrator / test-case-generator / test-data-generator / assertion-generator
- 自动化段：api-test-generator / ui-automation-generator / performance-test-generator / security-test-generator / fixture-dag-planner / locator-discovery
- 治理段：hitl-gatekeeper / quality-governance / regression-planner / self-healing-orchestrator / coverage-analyzer / contract-drift-detector / failure-analyzer / change-impact-analyzer / knowledge-memory
- 运行方式：`setup_skills.py` 统一生成 evals 契约，`run_all_evals.py` 批量执行，纳入 `make test`；M5 起作为真实 Provider 的评估锚点（回放样本即 v1 评估集，N=10 起步，结构判分零容忍，样本 ≥30 后启用 85% 统计阈值；样本增长源＝Stage 4 审核闭环的人审批准/退回决定）。

### 3.4 质量门禁

**PR 级（每 PR 必过）**：
- `make lint`（Ruff + Mypy）
- `make contract`（OpenAPI 契约一致性）
- `make test`（pytest + Skill evals + Agent 治理校验）

**评估闸门（共识 C8，双层互补）**：
- 确定性层：回放样本作 pytest fixture，验证 provider 接入不破坏既有闭环，归 `make test`。
- LLM 判分层：回放样本作 promptfoo vars.input，验证 skill 在真实模型下行为，归新增 `make eval`；baseline JSON 存 `prototypes/skills/evals/baseline/`；核心指标＝负例 false-accept 率；判分 v0＝promptfoo icontains + evals.json 结构化 assertions 字段，本轮零 LLM-judge。

**里程碑级**：对照第四节验收证据清单逐项出具证据。禁止「假关闭」——每项关闭必须附 commit 哈希 + CHANGELOG 条目双重落账（L1 复验纠正报告教训：8 项「假关闭」中仅 1 项真关闭）。

### 3.5 Git 操作规范（结合业界主流实践与项目审计要求，2026-08-17 联网调研后定稿）

**分支模型：主干开发 + 短命分支（Trunk-Based）**

- `main` 为唯一长期分支，必须随时保持 `make lint && make contract && make test` 全绿；禁止不建分支直接在 `main` 上开发。
- 每个工作包（WP）一条短命分支，生命周期建议 ≤2 天，验收后合并回 `main` 并删除分支。命名规则：`feat/m1-wp1-review-rework`、`fix/qf-req-003-coverage`、`docs/changelog-batch-xx`、`chore/ci-eval-gate`；分支 A 并行线用 `feat/provider-interface-hardening`。
- 合并回 `main` 的前置条件：PR 级三重门禁全绿 + GitHub Actions 三条 workflow（backend / frontend / skill-eval）全绿 + CHANGELOG 已落账。

**提交规范（Conventional Commits）**

- 格式：`<type>(<scope>): <描述>`。type 取 feat / fix / docs / refactor / test / chore / perf / style；scope 取模块名 backend / frontend / contract / skills / docs / governance。
- 原子提交：一个 commit 只做一件事；提交时代码必须可编译、测试可运行；拒绝「大杂烩」与半成品提交。
- 台账关联：契约类修复（32-API规范.yaml / 33-数据库Schema设计.md 等）与台账项关闭，commit 正文必须注明编号（如 QF-REQ-xxx 或 CHANGELOG 批次号）。
- 审计约束（项目特有）：**未提交的 git 工作区改动不得声称为「已修复/已关闭」**——只有 commit + CHANGELOG 双重落账才构成正式变更；巡检与验收时以 `git status --short` 与 `git log` 为证据。
- 自 M1 起新提交执行本规范；历史提交不回溯修改。

**安全红线（禁止操作）**

1. 禁止 `git push --force` 到 `main` 等共享分支；禁止 rebase 已推送的共享历史；回退一律用 `git revert` 生成新提交，保留可追溯性。
2. 禁止提交 `.env`、密钥、令牌与任何敏感配置；`.gitignore` 兜底 + 提交前自查双保险。
3. `reset --hard`、`clean`、删除分支等破坏性操作须先经用户明确批准。

**标签与发布**

- 里程碑验收通过后打标签：`v1.0-m1`、`v1.0-m2`、…、试点总验收为 `v1.0`；标签注解注明验收证据文档路径。
- CHANGELOG 唯一载体为 `docs/04-architecture/35-变更记录CHANGELOG.md`；commit 哈希与 CHANGELOG 条目互相引用，形成闭环。

**日常操作节奏**

- 开工前先同步 `main`（`git pull`）；合并前本地 rebase `main` 解决冲突，冲突解决后重跑三重门禁再合并。
- WP 完成即推送远端，不把工作区当唯一备份。
- 每 PR 变更规模建议 ≤400 行，超出则拆分工作包。

---

## 四、分里程碑验收标准

### M1 需求与审核收口

1. Given 三类产出物（策略/计划/用例）草稿已生成，When 审核员退回并批改，Then 产生新版本且旧版可查，二次复核通过（GWT-5.5.12-2）。
2. Given 审核台打开任一 ReviewTask，Then 呈现 Page-Map §3 的 12 项最低信息；批准按钮禁用时可见禁用原因。
3. Given QF-REQ-001 四源字段（requiresReview / lockVersion 等 6 字段），Then 代码/契约/DB/文档四源一致且有二次复核证据。
4. 台账：需求全量评审的 6 项开放决策关闭记录在案。

### M2 任务看板工作化

1. Given 真实数据，When 访问看板 7 类视图（05 §5.5.9），Then 可筛选、可分派、SLA 与版本 Diff 可见。
2. Given 八模块导航骨架，Then 每模块可路由访问（占位页允许）。
3. E6/H8/H9/H10 设计裁决先行动工（autoclaw 债清单）。

### M3 执行与证据

1. Given execution-workflow.json 已合入 validate.py 校验，When 任一执行 skill 进入生产调用路径，Then 当天必须已在 allowedSkills+DAG 内，否则 fail-closed。
2. Given 一次真实执行，Then 产出不可变证据（stdout/stderr/exit-code + contentDigest），人工批准生效，证据不被分析覆盖（05 §5.13.6）。
3. 三条隔离验证用例随首批执行代码同 PR 绿（agent 无法绕过 digest 直写证据状态）。
4. 前置：sqlite_store 增量写/事件追加改造（C3）完成并有并发回归与最薄性能基线。
5. humanOnlyActions 含正式产物批准；证据「已执行/已通过」状态不可由生成该证据的同一 agent 链自证。

### M4 分析与报告

1. Given 失败执行事实，When AI 生成分析/Defect/报告草稿，Then 4 类产出物（ResultAnalysis / Defect / TestReport / 知识回流）各一纵向切片，报告可反查源头（GWT-5.5.12-3）。
2. Defect 与 FailureCluster 分离；外部同步即使手工也必须落 DefectSyncAttempt + 批准记录 + 回执（裁决 B2-4）。
3. 覆盖率展示强制 effective 口径；五类覆盖率口径（附录 C）分母互不推导、互不替代，禁止混用。

### M5 真实模型准入

1. Provider 接口超时/重试/降级/成本四项先合入。
2. 黄金集达标 + 结构判分通过方可切换真实 Provider；不达标走 Plan B。
3. make eval baseline 归档；deterministic-local 保留为 failover 与评估锚点。

### V1 试点总验收（M5 之后）

1. 选定一个真实可控 Workspace + Release，跑通「来源→策略/计划/用例→Web/API 代码→执行→分析/Defect/报告→人工审核」全链。
2. 五类覆盖率分别报告（INSTANCE / DESIGN / EXECUTABLE / EFFECTIVE / HUMAN_ACCEPTANCE），各自声明分母口径，不混用分母（口径定义见 22 号文档附录 C）。
3. 版本门禁六类证据齐备（22 号文档 §7）：产品（范围/非目标/旅程/用户验收/已知限制）、质量（自动检查/独立验证/人工验收分层）、安全（越权/Secret/外联/供应链/审计测试）、AI（Golden Set/人工修改率/误放误阻/降级/越权率）、运行（容量/延迟/恢复/成本/可观测）、发布（版本摘要/迁移回滚/批准签署）。
4. 指标只建基线不承诺目标值；目标值须试点基线后经至少一个 Release 窗口批准（22 号文档 §6）。

---

## 五、风险与债务治理

| 风险/债务 | 治理方式 |
|---|---|
| 台账 OPEN 项（QF-REQ-003/004/005/006/007/011/025 等） | 偿还绑定里程碑前置债（第二节表格），不单独开「还债冲刺」 |
| 「假关闭」系统性风险 | 每项关闭必须 commit 哈希 + CHANGELOG 双重落账；协调人巡检复扫 |
| 安全前置未外部化（JWT 进程内密钥、进程内限流） | V2 硬阻断项，V1 内登记不解决，不对外暴露端口 |
| SQLite≠目标架构 | V1 全程以 SQLite 为准；迁移 PostgreSQL 属 V2，先补并发回归与最薄性能基线 |
| 契约深度不足（约 58 处 Generic 响应） | 随对应 operation 实现逐个收敛，不单独立项 |
| 真实模型评测缺失（高风险 R2） | 由分支 A + M5 评估闸门承接，裸接禁止 |

---

## 六、执行约定

1. 本文件为 V1 开发计划的权威载体；里程碑范围变更须经对话墙话题评审 + 用户确认后修订本文件并升版。
2. 每个里程碑开工前用 writing-plans 拆出详细实施计划（M1 实施计划见 `deliverables/2026-08-17/QualityForge-M1实施计划-v1.0.md`）。
3. 里程碑验收按证据验收而非日历验收；人力默认假设为单人 + AI 结对。
4. M1 开工已在对话墙登记（wall/threads/2026-08-17-m1-kickoff.md，消息 M-114）。
