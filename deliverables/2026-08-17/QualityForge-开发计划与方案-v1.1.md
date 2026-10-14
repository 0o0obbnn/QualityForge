# QualityForge 开发计划与方案 v1.1

> 版本：v1.1 ｜ 日期：2026-08-17 ｜ 状态：生效（用户裁决后升版）
> 取代：`deliverables/2026-08-17/QualityForge-开发计划与方案-v1.0.md`（v1.0 保留作历史版本）
> 依据：`docs/03-governance/22-MVP版本规划v2.0.md`、`wall/reviews/stage5-planning/VERDICT.md`、`deliverables/需求全量评审报告-2026-08-15.md`
> 升版动因：① 用户裁决开发分工——后端＝lingma、前端＝autoclaw（前端原型即 autoclaw 设计）；② 用户裁决 O1——接受「定性成功标准＋基线后量化」路径；③ 承接 2026-08-17 计划评估报告的 2 项 P0、3 项 P1、5 项 P2 整改。

## 修订记录

| 版本 | 修订内容 |
|---|---|
| v1.1 | 新增双轨协作模型（§3.0）；验收标准重构为后端/前端/集成三层（§四）；新增放行三条件关闭包与定性成功标准（§六）；P0-1 门禁整改已落地（Makefile test 聚合纳入前端测试；**2026-08-17 更新：批次二十八双落账完成——commits a981d41/15ef64a/5bb6438 + CHANGELOG 271f82f，P0-1 标 CLOSED**）；P2-3 双落账两段式操作序书面化（§3.5）；Git 分支命名按轨道划分；生效批注（autoclaw 评估 N2/N5）：§3.0.4 钉死 27 页原型路径、§3.0.5 明确升级触发权；M2 收缩预案优先保留分派视图（N4） |
| v1.0 | 初版：现状基线、版本规划、开发方案、Skill 策略、分里程碑验收、风险治理 |

---

## 一、现状基线（计划起点）

| 维度 | 事实 | 对计划的影响 |
|---|---|---|
| 需求体系 | 全量评审 PASS_WITH_ACTIONS（0 Blocker / 6 Major / 3 高风险）；放行三条件见 §六，M1 内完整挂账 | 三条件未全部关闭前不得宣称「需求已验收」 |
| 里程碑 | Stage 5 VERDICT 终裁 M1→M5；共识 C1–C8 全部落位 | 产物主链为排程骨架（C6） |
| 代码 | 后端 22/108 operation；前端 React 19 + Fluent UI 单页审核台（4 个业务文件）；30 个 Skill 原型带 evals | 后端按里程碑增量实现；前端 M2 起为规模化新建，须先做容量估算（§五 R6） |
| 测试基线 | 后端 15 个测试函数、planning 核心链路仅 6 个；前端 vitest 10 个；Playwright 尚未引入 | M1 先补 characterization 测试再改造（M1-B0）；Playwright 由前端轨道在 M1 引入 |
| 组织分工 | 后端＝lingma；前端＝autoclaw（用户裁决 2026-08-17） | 契约先行、双轨并行、按轨验收（§3.0） |
| 硬约束 | C1 不做 PostgreSQL/多用户；C2 真实模型先有评估闸门；C7 执行=进程内串行+文件证据；C8 评估闸门双层形态 | 违反即 fail-closed |

---

## 二、版本规划（对齐 22 号文档）

- **V0 Gate 0（已完成）**：权威契约一致、Gate 0 原型可静态验证、独立审计给出开发准入结论。
- **V1 单 Workspace 试点（本轮主目标）**：八模块最小入口贯通；跑通 Journey A/B/C 完整证据链并建立基线。拆解为 M1–M5。
- **V2 团队协同（V1 验收后启动）**；**V3 企业规模（远期）**。

### Stage 5 里程碑 × 轨道分工

| 里程碑 | 后端轨（lingma） | 前端轨（autoclaw） | 集成点 |
|---|---|---|---|
| M1 需求与审核收口 | 退回/新版本闭环、3 个新 operation、characterization 基线、放行三条件挂账 | 审核台 12 项信息、批准禁用原因、版本历史视图、引入 Playwright 基础设施 | 浏览器端走通「生成→审核→退回→批改→复核」全闭环 |
| M2 看板工作化 | 看板数据接口、7 类视图查询与分派 operation | 7 类看板视图（先做规模估算，超容量则收缩为最小纵向切片）、八模块导航骨架 | 真实数据可筛可分派 |
| M3 执行与证据 | execution-workflow.json、3 个执行 operation、不可变证据、存储增量改造（C3，含最薄恢复证据口径） | 执行状态 2–3s 轮询渲染（按 docs/36 §3 事件信封抽象）、证据审核页 | 一次真实执行产出证据并人工批准 |
| M4 分析与报告 | 分析/Defect/报告纵向切片、effective 口径覆盖率 | 分析/Defect/报告视图、报告反查源头导航 | 报告反查至需求源头（GWT-5.5.12-3） |
| M5 真实模型准入 | Provider 切换、make eval baseline 归档 | 降级状态呈现（量小） | 真实模型链路验证 |

**并行线（分支 A）**：真实 Provider 工程。**执行主体＝后端轨 AI 主导实现＋里程碑末人审合入**（低抢占模式，整改 P1-3）；每里程碑主链切片验收后再投入，**M4 起冻结分支 A 代码变更**，避免 M5 验收突击。
**分支 B（质量中心/Defect）**：M4 之后收尾，不并设立项（C4）。

### 本轮明确不做（Stage 5 VERDICT §三）

多用户/PostgreSQL/RLS、WebSocket/SSE、调度框架/Redis、独立重型评估框架与 LLM-judge、Workflow 设计器、外部双向同步、企业 CI/CD 门禁。各项重启条件不变。

---

## 三、开发方案

### 3.0 双轨协作模型（v1.1 新增，契约先行）

1. **契约是唯一接缝**：`docs/04-architecture/32-API规范.yaml` 为双轨共享权威契约。任一轨发现契约缺口/错误，在对话墙提出契约变更 → 对方轨确认 → 修订契约 → `make contract` 绿 → 双方各自实现。禁止任一侧私改契约或绕过契约传数据。
2. **并行节奏**：后端轨按「契约→schemas→service→store→路由→pytest」推进；前端轨在接口未就绪时可基于契约 mock 先行开发，接口就绪后切换真实联调。
3. **协调通道**：一切跨轨事项（派工、契约变更、联调阻塞、验收分歧）走对话墙 `m1-kickoff` 系列话题；点名必登记 INBOX。
4. **设计基线**：前端轨的视觉与交互基线＝`docs/06-wireframes/`（Page-Map、设计令牌）＋ `deliverables/2026-08-12/prototype/`（autoclaw 设计的 27 页 Fluent 原型，含 2 个 apple 变体与 README，实测在案）；前端验收对照自有设计基线执行。
5. **升级路径**：跨轨分歧两轮内不能收敛时，**任一方均可直接提请用户裁决，协调人不得单方面否决升级请求**（防协调人兼后端轨的结构性偏倚，autoclaw 评估 N5）。

### 3.1 架构与技术栈（沿用既定基线）

- 后端：FastAPI + SQLite（uv），分层 api/v1 → services → db/sqlite_store → providers（deterministic-local）。
- 前端：React 19 + Vite + Fluent UI 9；事件渲染层按 docs/36 §3 通用事件信封设计，暂用 2–3s 轮询＋终态即停。
- 契约：32-API规范.yaml（108 operations），`make contract` 强制校验。
- 治理：prototypes/agent-governance/ 声明式 workflow；execution-workflow.json 与 gate0-workflow.json 同构。

### 3.2 开发模式：主链驱动的纵向切片

1. 每个里程碑一条「从 API 到 UI 可演示」的纵向切片，拒绝横铺。
2. 后端 operation 实现顺序：契约核对 → schemas → service（状态机）→ store → 路由 → pytest。
3. 正式产出物「稳定根＋不可变版本＋摘要绑定批准」；ExecutionResult/Evidence/ReviewDecision/AuditLog 只追加。
4. AI 生成物三层证据：确定性检查 → 独立验证 → 人工审核，分别报告。
5. 事实/推断/决定三层分离贯穿全模块。
6. 效率指标采集自事件，不手工录入。

### 3.3 Skill 使用策略

**后端轨（lingma）开发流程 Skill**：writing-plans（里程碑拆解）、tdd（红先行）、executing-plans（检查点推进）、systematic-debugging（失败先证据）、security-review（RBAC/fail-closed 每里程碑一遍）、verification-before-completion（声称完成前跑门禁贴输出）、code-review / deep-review（合入前双轴评审）。

**前端轨（autoclaw）参照执行**：tdd（vitest 组件测试先行）、e2e-testing（Playwright 关键旅程）、design-qa / ui-alignment-review（对照自有原型基线验收）。

**产品流水线 Skill（30 个原型）**：需求段（requirement-compiler 等 6 个）、设计段（strategy-planner 等 5 个）、自动化段（api-test-generator 等 6 个）、治理段（hitl-gatekeeper 等 9 个）。运行方式：setup_skills.py 统一 evals 契约，run_all_evals.py 批量执行纳入 make test；M5 起作真实 Provider 评估锚点（N=10 起步、结构判分零容忍、样本 ≥30 启用 85% 阈值）。**样本积累跟踪（整改 P2-1）**：M3 起每个里程碑验收证据包含「回放样本数」计数，长期停滞时在墙上触发讨论。

### 3.4 质量门禁（v1.1 整改 P0-1 已落地）

**PR 级（每 PR 必过，双轨同一标准）**：
- `make lint`（Ruff + Mypy）
- `make contract`（OpenAPI 一致性）
- `make test`＝后端 pytest ＋ **前端 vitest（2026-08-17 已纳入聚合，实测 10 用例绿）** ＋ Skill evals ＋ Agent 治理校验
- GitHub Actions 三条 workflow（backend / frontend / skill-eval）全绿；前端 workflow 已含 typecheck＋vitest＋build
- **Playwright 冒烟**：由前端轨在 M1 引入基础设施并纳入 frontend workflow，作为 M1 起的集成验收门禁（引入前以 vitest＋手工演示过渡）

**评估闸门（C8 双层）**：确定性层归 make test；LLM 判分层归新增 make eval（baseline 存 prototypes/skills/evals/baseline/，核心指标＝负例 false-accept 率，本轮零 LLM-judge）。

**里程碑级**：对照 §四 三层验收出具证据；禁止假关闭（commit＋CHANGELOG 双落账）。

### 3.5 Git 操作规范（v1.1 按轨道修订）

**分支模型：主干开发＋短命分支（Trunk-Based）**
- `main` 唯一长期分支，随时保持三重门禁全绿；禁止不建分支直接在 main 开发。
- 每 WP 一条短命分支（≤2 天），命名按轨道：后端 `feat/m1-be-wp1-review-rework`、`fix/m1-be-qf-req-xxx`；前端 `feat/m1-fe-wp2-review-console`；文档 `docs/xxx`；分支 A 用 `feat/provider-interface-hardening`。
- 合并前置：三重门禁全绿＋CI 三 workflow 全绿＋CHANGELOG 已落账；跨轨契约变更 commit 必须注明对方轨确认的消息 id。

**提交规范（Conventional Commits）**
- `<type>(<scope>): <描述>`；type＝feat/fix/docs/refactor/test/chore/perf/style；scope＝backend/frontend/contract/skills/docs/governance。
- 原子提交；契约修复与台账关闭的 commit 必须注明编号（QF-REQ-xxx / 批次号）。
- 审计约束：未提交的工作区改动不得声称「已修复/已关闭」；验收以 `git status --short`＋`git log` 为证据。

**双落账操作序（整改 P2-3，固化既有惯例）**
1. 内容提交：过完整三重门禁后合入，取得 commit 哈希。
2. 回填提交：将哈希写入 CHANGELOG（35 号文档）批次条目，docs-only 提交，过 lint 免全量测试。
3. 两个提交都进入 main 后，该项方可标记 CLOSED。

**安全红线**：禁 force push 共享分支；禁 rebase 已推送共享历史；回退用 git revert；禁提交 .env/密钥；破坏性操作须用户批准。

**标签**：里程碑验收后打 `v1.0-m1`…`v1.0`，注解注明验收证据路径。

**节奏**：开工同步 main；合并前 rebase 后重跑门禁；PR ≤400 行；完成即推送。

---

## 四、分里程碑验收标准（v1.1 重构：后端/前端/集成三层）

> 每层验收证据包均附「验收口径速查」（整改 P2-2）：被引用的 GWT/章节关键句摘录进验收记录，引用与摘录并存。

### M1 需求与审核收口

**后端轨**
1. Given 三类产出物草稿已生成，When 审核退回并批改，Then 新版本产生且旧版只读可查、自动创建新 ReviewTask、二次复核通过（GWT-5.5.12-2）。
2. createTestStrategyVersion / createTestPlanVersion / transitionWorkItem 三个 operation 实现且契约绿；lockVersion 乐观锁陈旧提交返回 409。
3. characterization 基线：改造前固化既有 planning 链路行为（整改 P1-1），改造后基线测试全绿。
4. QF-REQ-001 四源一致，复核记录＋commit＋CHANGELOG 双落账。

**前端轨（autoclaw）**
1. 审核台呈现 Page-Map §3 的 12 项最低信息（对照自有原型逐项核对表）。
2. 批准按钮禁用时渲染可见原因（权限/陈旧版本/前置未完成/摘要不一致四类）。
3. 版本历史视图：新旧版本切换查看＋Diff 摘要（完整 Diff 归 M2）。
4. vitest 覆盖禁用原因与信息渲染；Playwright 基础设施引入并覆盖审核关键旅程冒烟。

**集成**
1. 浏览器端完整走通「生成→审核→退回→批改→新版本→复核」，三类产出物各一条演示记录。
2. 放行三条件关闭包（§六）记录在案。

### M2 任务看板工作化

**后端轨**：看板 7 类视图的查询/筛选/分派 operation；SLA 与版本 Diff 数据接口。
**前端轨**：7 类视图真实数据可筛可分派；八模块导航骨架可路由。**开工前置（整改 P1-2）**：writing-plans 输出 T-shirt 规模估算与容量声明；超容量则收缩为「1 类视图＋导航骨架」最小纵向切片，其余视图递延并登记。**收缩优先级（autoclaw 评估 N4）**：收缩时必须优先保留「任务分派」相关视图，保证 M3 集成链（真实数据可筛可分派）不因收缩断档；被递延视图登记入 R6 台账。
**集成**：真实数据全视图冒烟；E6/H8/H9/H10 设计裁决落地。

### M3 执行与证据

**后端轨**
1. execution-workflow.json 先于业务代码合入 validate.py；执行 skill 进生产路径当天必须在 allowedSkills+DAG 内，否则 fail-closed。
2. 一次真实执行产不可变证据（stdout/stderr/exit-code＋contentDigest），人工批准生效，证据不被分析覆盖（05 §5.13.6）。
3. 三条隔离验证用例同 PR 绿。**开工前置（整改 P2-4）**：M3 实施计划先列明三条用例各自的绕过向量（直写 store / 伪造 digest / 重放旧摘要）与预期 fail-closed 行为。
4. C3 存储增量改造完成：并发回归＋最薄性能基线＋**最薄恢复证据口径（整改 P2-5，如进程强杀后重启完整性校验用例）**。

**前端轨**：执行状态轮询渲染（终态即停）；证据审核页（digest 展示与批准）。
**集成**：端到端执行→证据→批准演示；humanOnlyActions 含正式产物批准的验证记录。

### M4 分析与报告

**后端轨**：ResultAnalysis/Defect/TestReport/知识回流各一纵向切片；Defect 与 FailureCluster 分离；手工外部同步也落 DefectSyncAttempt＋批准＋回执（B2-4）；覆盖率强制 effective 口径（五类口径分母互不推导）。
**前端轨**：分析/Defect/报告视图；报告反查源头导航。
**集成**：报告反查至需求源头（GWT-5.5.12-3）；回放样本数计数报告（P2-1）。

### M5 真实模型准入

**后端轨**：Provider 超时/重试/降级/成本四项先行；黄金集达标＋结构判分通过方可切换，不达标走 Plan B；make eval baseline 归档；deterministic-local 保留为 failover 与评估锚点。
**前端轨**：降级状态呈现。
**集成**：真实模型全链验证；回放样本数计数报告。

### V1 试点总验收（M5 后）

1. 选定真实可控 Workspace＋Release，跑通「来源→策略/计划/用例→Web/API 代码→执行→分析/Defect/报告→人工审核」全链。
2. 五类覆盖率分别报告（INSTANCE/DESIGN/EXECUTABLE/EFFECTIVE/HUMAN_ACCEPTANCE），各自声明分母口径，禁止混用（22 号附录 C）。
3. 版本门禁六类证据齐备（22 §7）：产品/质量/安全/AI/运行/发布。**运行类最薄口径**：单机 SQLite 形态下「恢复」证据＝进程强杀后重启完整性校验（承接 P2-5）。
4. **定性成功标准（O1 裁决 2026-08-17，用户确认接受「定性＋基线后量化」路径）**：
   - D1 试点用户仅凭平台 UI 完成 Journey A/B/C 全链，无需脚本手工补证据；
   - D2 事实/推断/决定三层可分离可追溯，正式产出物零绕过人工审核；
   - D3 事件采集管道正常产出效率指标数据（Lead/Cycle Time、审核时长、AI 成功率与成本、生成到批准时间），无手工录入；
   - D4 人工/影子基线对照数据归档，可支撑后续目标值批准；**采集安排（autoclaw 评估 N3）**：试点 Workspace 选定后明确基线采集人（默认用户本人或指定试点用户）、任务样本（与 Journey A/B/C 同任务）、归档格式（对照表或影子运行日志）；
   - D5 六类版本门禁证据齐备。
5. 量化目标值不在试点前承诺：按 22 §6 顺序——V1 建基线 → 同任务对照 → 至少经过一个 Release 窗口后批准目标值；模型/Prompt/Skill/数据分布变化后重新校准。

---

## 五、风险与债务治理

| # | 风险/债务 | 治理方式 |
|---|---|---|
| R1 | 台账 OPEN 项（QF-REQ-003/004/005/006/007/011/025 等） | 偿还绑定里程碑前置债，不单开还债冲刺 |
| R2 | 假关闭系统性风险 | 双落账操作序（§3.5）＋协调人巡检复扫 |
| R3 | 安全前置未外部化（JWT 进程内密钥、进程内限流） | V2 硬阻断，V1 登记不解决，不对外暴露端口 |
| R4 | SQLite≠目标架构 | V1 以 SQLite 为准；PG 迁移属 V2，先补并发回归与最薄性能基线 |
| R5 | 契约深度不足（约 58 处 Generic 响应） | 随对应 operation 实现逐个收敛 |
| R6 | M2 前端规模鸿沟（单页→7 视图＋8 导航，整改 P1-2） | 开工前规模估算＋容量声明；超容量收缩为最小纵向切片 |
| R7 | 双轨协作风险：契约漂移、联调时序、墙响应延迟 | 契约变更双人确认制（§3.0）；阻塞超 24h 协调人催办；联调窗口每里程碑末固定 |
| R8 | 分支 A 交付后置突击（整改 P1-3） | AI 主导低抢占＋M4 起冻结代码变更 |

---

## 六、放行三条件关闭包（整改 P0-2，M1 内完整挂账）

需求全量评审 §5.6 的 V1 准入 gate 三条件，逐条承接：

1. **关闭 6 项开放决策（O1–O6）**：
   - O1（V1 成功标准）：**已关闭**——用户 2026-08-17 裁决接受「定性＋基线后量化」路径，定性标准见 §四 D1–D5，量化目标值按 22 §6 延后批准。
   - O2–O6：M1 内逐条给出关闭证据或升级用户裁决（对应评审报告 T1–T7 行动项）。
2. **R1–R3 高风险对策落位清单**：
   - R1（V1 范围=全模块、最小入口量化不足）→ 对策＝本计划 §二 里程碑×轨道分工表＋§四 三层验收；M2 规模估算（R6）为量化补充。
   - R2（真实模型评测缺失）→ 对策＝分支 A＋M5 评估闸门（C8）＋make eval。
   - R3（SQLite≠PG RLS）→ 对策＝C1/C3：本轮不做多用户（硬阻断登记于 R3 行）、存储先增量后迁移。
3. **冻结 D1–D6 整改方案**（方案冻结于 M1，执行排入对应里程碑）：
   - D1 命名漂移：冻结方案＝机械重命名（一次性术语对齐批次，执行排 M2 文档批次）；
   - D2 TEST_DESIGN 同名不同义：冻结方案＝术语表加注＋引用消歧（执行排 M1 契约收敛）；
   - D3 手工测试范围模糊：冻结方案＝PRD 补显式声明（执行排 M1）；
   - D4 指标载体缺口：冻结方案＝指标落 metricKey 载体表（执行排 M1，配合 D3 定性标准采集）;
   - D5 覆盖率维度脱节：冻结方案＝五类口径附录 C 已冻结（2026-08-14 裁决），执行校验排 M4；
   - D6 裁决散落：冻结方案＝统一裁决台账（执行排 M1，由文档 Owner 后端轨兼任）。

---

## 七、执行约定

1. 本文件为 V1 开发计划权威载体；范围变更经对话墙评审＋用户确认后升版。
2. 里程碑开工前由对应轨道用 writing-plans 拆实施计划（M1 实施计划 v1.1 见 `deliverables/2026-08-17/QualityForge-M1实施计划-v1.1.md`）。
3. 验收按证据不按日历；人力假设＝后端 lingma（AI 结对）＋前端 autoclaw（墙协作）。
4. 前端轨派工已发布：wall/threads/2026-08-17-m1-kickoff.md 消息 M-115（@autoclaw，INBOX 已登记）。
