# QualityForge M1 实施计划 v1.0（需求与审核收口）

> 版本：v1.0 ｜ 日期：2026-08-17 ｜ 上级计划：`deliverables/2026-08-17/QualityForge-开发计划与方案-v1.0.md`
> 里程碑依据：`wall/reviews/stage5-planning/VERDICT.md` §四 M1 行；验收口径 GWT-5.5.12-2（05 §5.5.12）
> 排程原则：纵向切片、TDD 先行、每 WP 过 `make lint && make contract && make test`。

---

## 一、M1 目标与范围

**目标**：策略/计划/用例三类产出物走通「生成→审核→批改→新版本→二次复核」完整闭环，审核台达到最低信息标准。

**范围内 operation**（对照 `docs/04-architecture/32-API规范.yaml`）：

| operation | 现状 | M1 动作 |
|---|---|---|
| listTestStrategies / createTestStrategy | 已实现 | 复用，作为闭环第一类产出物 |
| createTestStrategyVersion | 未实现 | **新增**：退回后批改产生新版本 |
| listTestPlans / createTestPlan | 已实现 | 复用，闭环第二类产出物 |
| createTestPlanVersion | 未实现 | **新增** |
| listTestCases / createTestCase / listTestCaseVersions / createTestCaseVersion | 已实现 | 补齐版本链与新版本语义复核 |
| listReviewTasks / getReviewTask / getReviewArtifact / decideReviewTask | 已实现 | **增强**：退回(REWORK)分支、禁用原因、12 项信息 |
| transitionWorkItem | 未实现 | **新增**：PENDING_REVIEW → REWORK → PENDING_REVIEW 状态机迁移 |
| listWorkItemRuns | 未实现 | 可选（看板 M2 主用，M1 仅在审核台引用处留桩） |

**范围外**：执行、分析、Defect、报告、真实 Provider（归 M3/M4/M5）。

---

## 二、工作包（WP）拆解

### WP-0 QF-REQ-001 二次复核（M1 开工之首，用户裁决）

- 核对 WorkItem 6 关键字段（含 requiresReview / lockVersion）在四源一致：
  - 代码：`backend/src/qf/schemas/planning.py`
  - 契约：`docs/04-architecture/32-API规范.yaml` WorkItem schema
  - DB：`docs/04-architecture/33-数据库Schema设计.md` t_work_item + `backend/src/qf/db/sqlite_store.py` DDL
  - 文档：`docs/01-product/04-核心领域模型.md`
- 产出一份复核记录（差异清单 + 修复 commit），写入 `deliverables/2026-08-17/QF-REQ-001-二次复核记录.md`；关闭须 commit + CHANGELOG 双重落账（35 号文档）。

### WP-1 退回与新版本后端闭环（TDD）

1. 红：pytest 用例覆盖——decideReviewTask(REJECT) 后产出物状态回到草稿、编辑提交 createXxxVersion 产生新版本号、旧版本只读可查、新版本自动创建新 ReviewTask。
2. 绿：
   - `backend/src/qf/services/planning_workflow.py` 增补退回分支与版本递增逻辑。
   - 新增 createTestStrategyVersion / createTestPlanVersion 两个 operation（schemas → service → store → api 路由）。
   - `transitionWorkItem` 实现 REWORK 迁移路径（BACKLOG→…→PENDING_REVIEW→REWORK→PENDING_REVIEW）。
3. 约束：版本不可变；批准绑定精确内容摘要（digest）；lockVersion 乐观锁防陈旧提交（409）。

### WP-2 审核台 12 项最低信息 + 批准禁用原因（前端）

- 对照 `docs/06-wireframes/Page-Map` §3 逐项核对 `frontend/src/App.tsx` 审核台现有呈现，缺口补齐。
- 批准按钮禁用时必须渲染可见原因（权限不足 / 陈旧版本 / 前置审核未完成 / 摘要不一致）。
- 版本历史视图：同一产出物新旧版本可切换查看，Diff 摘要可见（完整 Diff 归 M2）。
- 前端测试：vitest 组件测试覆盖禁用原因渲染；关键旅程用 Playwright 冒烟（e2e-testing skill）。

### WP-3 6 项开放决策关闭

- 逐条从 `deliverables/需求全量评审报告-2026-08-15.md` 提取 6 项开放决策，逐项给出关闭证据或升级为用户裁决项。
- 关闭记录并入 M1 验收证据包。

### WP-4 分支 A 并行开工（不阻塞主线）

- Provider 接口先扩四项：超时 / 重试 / 降级 / 成本上报（`backend/src/qf/providers/__init__.py` 抽象层）。
- 坏 provider 防御测试：超时、错误输出、抛异常三类 fixture，验证 failover 到 deterministic-local。
- 准入验收归 M5，此处只做工程准备。

---

## 三、实施顺序与依赖

```
WP-0（复核）──┬──> WP-1（后端闭环）──> WP-2（前端审核台）──> M1 验收
              └──> WP-3（决策关闭，可与 WP-1 并行）
WP-4（分支 A）自首日并行，独立分支推进
```

每个 WP 内部遵循：契约核对 → 红用例 → 实现 → `make lint && make contract && make test` → commit。

Git 操作按主计划 §3.5 执行：每个 WP 一条短命分支（WP-0 用 `docs/qf-req-001-recheck`、WP-1 用 `feat/m1-wp1-review-rework`、WP-2 用 `feat/m1-wp2-review-console`、WP-3 用 `docs/m1-wp3-decisions-close`、WP-4 用 `feat/provider-interface-hardening`）；提交采用 Conventional Commits，契约修复与台账关闭必须注明编号；M1 验收通过后打标签 `v1.0-m1`。

---

## 四、M1 验收证据包（verification-before-completion）

| 验收标准 | 证据形式 |
|---|---|
| 三类产出物「生成→审核→批改→新版本→复核」闭环，旧版可查（GWT-5.5.12-2） | pytest 集成测试绿输出 + 手工演示记录（每类产出物一条） |
| 审核台 12 项最低信息 + 批准禁用态可见原因 | Page-Map §3 逐项核对表 + vitest/Playwright 输出 |
| QF-REQ-001 四源一致且有复核证据 | 二次复核记录文件 + commit 哈希 + CHANGELOG 条目 |
| 6 项开放决策关闭记录在案 | 决策关闭清单（逐条证据或升级说明） |
| 门禁 | `make lint` / `make contract` / `make test` 全绿输出存档 |

验收流程：证据齐备 → deep-review/code-review 双轴评审 → 用户确认 → 在对话墙发布 M1 VERDICT → 进入 M2。

---

## 五、风险

1. **版本模型歧义**：产出物「根+版本」与 WorkItem 状态机的耦合点若契约不清，先查 04 号领域模型与 33 号 Schema，仍歧义则上墙话题裁决，不私自决定。
2. **审核台 12 项信息缺定义**：若 Page-Map §3 条目与现有 API 字段不匹配，缺口字段随 WP-1 一并补契约（make contract 保护）。
3. **台账牵连**：WP 过程中如发现新的契约/实现不一致，登记增量台账（QF-REQ-049 起编号续编），不当场扩大范围。
