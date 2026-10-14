# QualityForge M1 实施计划 v1.1（需求与审核收口 · 双轨）

> 版本：v1.1 ｜ 日期：2026-08-17 ｜ 上级计划：`deliverables/2026-08-17/QualityForge-开发计划与方案-v1.1.md`
> 取代：`QualityForge-M1实施计划-v1.0.md`（v1.0 保留作历史版本）
> 升版动因：开发分工裁决——后端＝lingma、前端＝autoclaw；承接评估整改 P0-1/P0-2/P1-1。
> 排程原则：契约先行、双轨并行、纵向切片、TDD 先行、每 WP 过 `make lint && make contract && make test`。

---

## 一、轨道与范围

**后端轨（lingma）**

| operation | 现状 | M1 动作 |
|---|---|---|
| listTestStrategies、listTestPlans | 已实现 | 复用 |
| createTestStrategy / createTestPlan | 未实现（2026-08-17 复核更正，见 QF-REQ-079） | M1 范围再评估（退回链路若需手工新建则升为新增） |
| createTestStrategyVersion / createTestPlanVersion | 未实现 | **新增**（退回后批改产生新版本） |
| listTestCases / listTestCaseVersions | 已实现 | 版本链语义复核 |
| createTestCase / createTestCaseVersion | 未实现（2026-08-17 复核更正，见 QF-REQ-079） | M1 范围再评估 |
| listReviewTasks / getReviewTask / getReviewArtifact / decideReviewTask | 已实现 | **增强**：退回(REWORK)分支、禁用原因字段 |
| transitionWorkItem | 未实现 | **新增**：PENDING_REVIEW → REWORK → PENDING_REVIEW |

**前端轨（autoclaw）**：审核台 12 项最低信息、批准禁用原因渲染、版本历史视图、Playwright 基础设施（设计基线＝docs/06-wireframes ＋ 自有 27 页原型）。

**范围外**：执行、分析、Defect、报告、真实 Provider 切换（归 M3/M4/M5）。

---

## 二、工作包

### M1-B0 QF-REQ-001 二次复核 ＋ characterization 基线（后端，开工之首）

分支：`docs/qf-req-001-recheck`（复核）＋ `test/m1-be-char-baseline`（基线测试）

1. 四源核对 WorkItem 6 关键字段（requiresReview/lockVersion 等）：schemas/planning.py ↔ 32-API规范.yaml ↔ 33-Schema＋sqlite_store DDL ↔ 04-核心领域模型.md；产出复核记录，双落账关闭。
2. **characterization 测试（整改 P1-1）**：先为既有 planning 链路（生成→审核→批准/退回、幂等、租户隔离）补齐现状行为固化测试；基线绿后才允许进入 M1-B1 改造。同时为 22 个既有 operation 补 happy-path 契约对齐测试。

### M1-B1 退回与新版本后端闭环（后端，TDD）

分支：`feat/m1-be-wp1-review-rework`

1. 红：decideReviewTask(REJECT) → 产出物回草稿态；createXxxVersion 版本号递增；旧版只读可查；新版本自动建新 ReviewTask；lockVersion 陈旧提交 409。
2. 绿：planning_workflow.py 退回分支＋版本递增；新增两个 Version operation；transitionWorkItem REWORK 路径。
3. 约束：版本不可变、批准绑定 digest、M1-B0 基线测试保持全绿。
4. **契约先行**：新增字段（如禁用原因 approveDisabledReason）先在 32-API规范.yaml 修订并 @前端轨确认（墙上消息 id 记入 commit），再实现。

### M1-B2 放行三条件关闭包（后端兼文档 Owner）

分支：`docs/m1-release-gate-closure`

- O2–O6 逐条关闭证据或升级用户裁决（O1 已由用户裁决关闭，见主计划 §六）。
- R1–R3 对策落位清单引用主计划对应章节。
- D1–D6 整改方案冻结记录（方案冻结于 M1，执行按主计划 §六 排期）。

### M1-F1 审核台前端（autoclaw）

分支：`feat/m1-fe-review-console`

1. 对照 Page-Map §3 逐项核对现有呈现，补齐 12 项最低信息。
2. 批准禁用态渲染可见原因（权限/陈旧版本/前置未完成/摘要不一致）。
3. 版本历史视图：新旧版本切换＋Diff 摘要。
4. vitest 组件测试覆盖 2/3；引入 Playwright 并覆盖「生成→审核→退回→复核」冒烟，纳入 frontend workflow（主计划 §3.4）。
5. 接口未就绪时按契约 mock 先行；联调窗口在 M1-B1 合入后。

### M1-P1 分支 A 并行（后端，低抢占）

分支：`feat/provider-interface-hardening`

- Provider 接口扩超时/重试/降级/成本四项；坏 provider 防御测试（超时/错误输出/异常三类 fixture，验证 failover 到 deterministic-local）。
- 节奏：M1 主链切片验收后再投入；准入验收归 M5。

---

## 三、依赖与节奏

```
M1-B0（复核+基线）──> M1-B1（后端闭环）──┐
                        ├─ 契约修订（墙确认）─> M1-F1（前端，可先 mock）──> I-1 集成验收
M1-B2（关闭包，并行）──┘
M1-P1（低抢占，主链验收后投入）
```

- 双轨每日各自推进，跨轨事项走墙（m1-kickoff 话题）；契约变更必须双轨确认。
- 联调窗口：M1-B1 合入 main 后开启，前端切换真实接口。

## 四、M1 验收证据包（三层，verification-before-completion）

| 层 | 验收标准 | 证据形式 |
|---|---|---|
| 后端 | 三类产出物退回→新版本→复核闭环（GWT-5.5.12-2）；3 个新 operation 契约绿；基线测试改造前后全绿；QF-REQ-001 双落账 | pytest 绿输出＋演示记录＋复核记录＋commit/CHANGELOG |
| 前端 | 12 项信息逐项核对表；禁用原因四类渲染；版本历史可切换；vitest＋Playwright 冒烟绿 | Page-Map §3 核对表＋vitest/Playwright 输出＋原型对照说明 |
| 集成 | 浏览器端三类产出物各走通一条全闭环；放行三条件关闭包在案 | 演示记录＋关闭包文档 |
| 门禁 | make lint / contract / test（含前端测试）全绿＋CI 三 workflow 绿 | 输出存档 |

> 验收口径速查（整改 P2-2）：GWT-5.5.12-2 关键句「审核退回后编辑产生新版本，旧版本保留可查，新版本重新进入审核」；Page-Map §3 的 12 项清单摘录随前端核对表一并归档。

验收流程：双轨证据齐备 → code-review/deep-review 双轴评审 → 用户确认 → 墙上发布 M1 VERDICT → 打标签 `v1.0-m1` → 进入 M2。

## 五、风险

1. **版本模型歧义**：先查 04 号领域模型与 33 号 Schema，仍歧义上墙裁决，不私自决定。
2. **契约与原型不匹配**：Page-Map §3 条目缺 API 字段支撑时，由前端轨在墙上发起契约变更，后端轨随 M1-B1 补齐（make contract 保护）。
3. **联调时序**：前端 mock 开发期间契约若变更，后端轨须当日在墙上通告。
4. **台账牵连**：新发现的不一致登记增量台账（QF-REQ-049 起续编），不当场扩围。
