# 变更日志 · 2026-07-31 · 纯修复类 + B-2 架构裁决（B-1 / C-1 / C-2 / B-2）

> 本轮整改对应审计 `总裁决报告.md` Phase 0 中的缺陷。
> 整改原则：AGENTS.md「修订文档的规则」—— 改术语/实体名先改术语表再同步领域模型/API/DB 四源。
> 第一批（B-1/C-1/C-2）：纯修复类，事实清楚、方向唯一。
> 第二批（B-2）：经用户架构裁决后整改——采用两阶段方案（DesignTestCase 临时表 → 审批 → TestCase 正式表）。

---

## 修复一：B-1 · RequirementDocument 状态枚举统一

**缺陷**：L1-001。PRD 11:75 用 `PENDING/PARSED/FAILED`（3值大写），领域模型 04:828 用 `Draft/Parsing/Completed/Failed`（4值）。AGENTS.md 规定"以领域模型为准"。

| 文件 | 改动 |
|---|---|
| `docs/02-prd/11-PRD-TestDesign.md:75` | `Default 'PENDING'` → `Default 'Draft'`；枚举 `PENDING,PARSED,FAILED` → `Draft,Parsing,Completed,Failed` |

**验证**：`grep "PENDING\|PARSED" docs/02-prd/11-PRD-TestDesign.md` 零命中。

---

## 修复二：C-1 · TestPlan 双语义拆分 + 外键补全

**缺陷**：L1-004 / C-1。TestPlan 丢失 Requirement 外键，且存在双语义冲突（术语表=发版里程碑 vs PRD=测试方案）。

**设计决策**：拆分为两个实体。
- `TestPlan`（保留）：发版发布节点语义，字段不变。
- `TestDesignPlan`（新增）：测试方案语义，承载 PRD 11:78-89 的字段。
- `TestScenario` 归属变更：`testPlanId` → `testDesignPlanId`。

**价值链**：`RequirementDocument → TestDesignPlan → TestScenario → TestCase`；`TestPlan`（发版）聚合多个 `TestDesignPlan`。

| # | 文件 | 改动 |
|---|---|---|
| 1 | `docs/01-product/04-核心领域模型.md` | ER 图：新增 TestDesignPlan 节点+关系线+属性块；TestScenario FK 改名。字段表：新增 §4.1 TestDesignPlan 实体；§5 TestScenario 的 testPlanId→testDesignPlanId |
| 2 | `docs/04-architecture/33-数据库Schema设计.md` | 新增 `t_test_design_plan` 表（含 requirement_document_id FK + test_plan_id 可选 FK）；`t_test_scenario` 的 test_plan_id→test_design_plan_id |
| 3 | `docs/04-architecture/32-API规范.yaml` | 新增 TestDesignPlan schema；TestScenario schema 的 testPlanId→testDesignPlanId；新增 `/test-designs/plans` 和 `/test-designs/plans/{planId}` CRUD 路径 |
| 4 | `docs/01-product/03-术语表Glossary.md` | TestPlan 条目后新增 TestDesignPlan 条目 |
| 5 | `docs/02-prd/11-PRD-TestDesign.md` | §3.1.2 TestPlan→TestDesignPlan（含修复说明）；§3.1.3 TestScenario 的 plan_id→test_design_plan_id |

**验证**：四源+PRD 均含 TestDesignPlan；TestScenario FK 一致指向 TestDesignPlan；无旧 testPlanId 残留。

---

## 修复三：C-2 · CoverageReport 实体补全

**缺陷**：L1-005 / C-2。覆盖率在领域模型/API/DB 零存在，但 Skill 12 (coverage-analyzer) 已有完整契约。

**设计决策**：不重新设计，忠实映射 Skill 12 的 `coverage_report_template.json` + `coverage.py` 实现提升为正式契约。补 testReportId 外键满足审计可追溯要求。

| # | 文件 | 改动 |
|---|---|---|
| 1 | `docs/01-product/04-核心领域模型.md` | ER 图：新增 TestReport→CoverageReport 关系线+属性块。字段表：新增 §17.1 CoverageReport 实体（含 Skill 映射说明）|
| 2 | `docs/04-architecture/33-数据库Schema设计.md` | 新增 `t_coverage_report` 表（含 test_report_id FK + 索引）|
| 3 | `docs/04-architecture/32-API规范.yaml` | 新增 CoverageReport schema；新增 `/intelligence/reports/{reportId}/coverage` 只读路径 |
| 4 | `docs/01-product/03-术语表Glossary.md` | TestReport 条目后新增 CoverageReport 条目 |

**验证**：四源+术语表均含 CoverageReport；TestReport→CoverageReport 关系线存在；字段与 Skill 12 契约可对照。

---

## 本轮未处理项（边界声明）

按计划仅处理纯修复类，以下不在本轮范围：

| 缺陷 | 原因 |
|---|---|
| B-2 DesignTestCase/TestCase 双状态机 | 需架构裁决（草稿→正式流转关系）|
| B-3 可信链 6 概念补契约（部分）| 本轮仅补了 CoverageReport；其余 5 概念（Assertion/Source Trace/Review Task/Testing IR/Business Rule）需架构设计 |
| B-4 AI 阈值散落 | 需先建校准数据集 |
| B-5 LLM 输出无外部 oracle | 需设计金标准集/抽检协议 |
| B-6 四大收益指标不可验收 | 需基线数据+测量方法 |
| C-3/C-4/C-5/C-6/C-7 | 各需架构/产品/资源决策 |

**C-2 的部分贡献**：CoverageReport 是可信链 6 概念之一，本轮已补入正式契约，部分缓解 B-3。
