# 变更日志 · 2026-08-04 · B-3 可信链剩余 5 概念补入四源

> 本轮整改对应审计 `总裁决报告.md` B-3（L1-003 / L4-005）的**收尾部分**。
> 前序：`CHANGELOG-2026-07-31` 已补入 CoverageReport（B-3 的 1/6）。本轮补入剩余 5/6。
> 整改原则：AGENTS.md「修订文档的规则」—— 改术语/实体名先改术语表再同步领域模型/API/DB 四源。
> 契约映射来源：Skill 原型的 JSON 模板是事实权威，本轮将它们提升为正式契约，不重新设计。

---

## 缺陷 B-3 · 可信链 6 概念全部进入正式契约

**缺陷**：L1-003 / L4-005。6 个可信链核心概念（Assertion / Source Trace / Review Task / Testing IR / Business Rule / Coverage Report）在 29 个 Skill 原型中高频使用（76/39/27/14/11/7 次命中），但在术语表 / 领域模型 / API / DB 四处零存在（CoverageReport 已于 2026-07-31 补入）。

**本轮处理**：剩余 5 个概念全部补入四源。

| # | 概念 | Skill 命中数 | 契约映射来源 | 性质 |
|---|---|---:|---|---|
| 1 | TestingIR | 14 | `ir-validator/evals/files/ir_clean.json` + `requirement-compiler/assets/compile_template.json` | 独立实体 |
| 2 | BusinessRule | 11 | `business-rule-extractor/assets/rule_template.json` | 独立实体 |
| 3 | Assertion | 76 | `assertion-generator/assets/batch_template.json` | 独立实体 |
| 4 | ReviewTask | 27 | `hitl-gatekeeper/assets/review_task_template.json` | 独立实体 |
| 5 | SourceTrace | 39 | 各 Skill 模板中的 `source_trace` 字段约定 | **字段约定**（非独立实体）|

**设计决策**：Source Trace 在所有 Skill 模板中均为其他实体上的字符串字段（格式 `"<source_id>§<section>"` 或 `"<skill-id>:<entity-id>:<req-id>"`），不建独立表。将其定义为正式字段约定，落实到 TestingIR / BusinessRule / Assertion 等实体的 `sourceTrace` 字段上。

---

## 逐文件改动

### 1. `docs/01-product/03-术语表Glossary.md`

| 段 | 改动 |
|---|---|
| §3 实体命名 | 追加 4 个实体：TestingIR / BusinessRule / Assertion / ReviewTask（在 CoverageReport 之后）|
| §4 状态命名 | 追加 3 组状态：IR 编译状态 (DRAFT/COMPILING/VALIDATED/FAILED)、评审工单状态 (OPEN/RESOLVED/EXPIRED)、断言校验状态 (VERIFIED/REJECTED/UNVERIFIED) |
| §5 AI 概念术语 | 追加 Source Trace 条目（在 Multi-Agent System 之后）|

### 2. `docs/01-product/04-核心领域模型.md`

| 段 | 改动 |
|---|---|
| 文档头部 | "38 个领域实体" → "42 个领域实体" |
| ER 图（关系线）| 追加 5 条关系线：RequirementDocument→TestingIR、TestingIR→BusinessRule、DesignTestCase→Assertion、TestCase→Assertion、Workspace→ReviewTask |
| ER 图（属性块）| 追加 4 个属性块：TestingIR / BusinessRule / Assertion / ReviewTask |
| 字段规范表 | 追加 §39 TestingIR / §40 BusinessRule / §41 Assertion / §42 ReviewTask（在 §38 KnowledgeVector 之后）|

### 3. `docs/04-architecture/32-API规范.yaml`

| 段 | 改动 |
|---|---|
| schemas | 追加 4 个 schema：TestingIR / BusinessRule / Assertion / ReviewTask |
| paths | 追加 7 个路径（9 个操作）：<br>• `GET /test-designs/{designId}/ir` — 获取 IR<br>• `POST /test-designs/{designId}/ir/recompile` — 重编译 IR<br>• `GET /test-designs/{designId}/rules` — 列出业务规则<br>• `GET/POST /assets/cases/{caseId}/assertions` — 用例断言列表/新增<br>• `PUT/DELETE /assets/assertions/{assertionId}` — 编辑/删除断言<br>• `GET/POST /reviews` — 评审工单列表/创建<br>• `PUT /reviews/{reviewId}/resolve` — 解决评审工单 |

### 4. `docs/04-architecture/33-数据库Schema设计.md`

追加 4 张表（编号 38-41，在 t_baseline_item 之后）：

| 表 | 关键约束 |
|---|---|
| `t_testing_ir` | `requirement_document_id` FK + `UNIQUE(workspace_id, requirement_document_id)` 保证每文档一份当前 IR |
| `t_business_rule` | `testing_ir_id` FK + `UNIQUE(workspace_id, rule_id)` |
| `t_assertion` | `test_case_id` / `design_test_case_id` 双 FK + `CHECK(test_case_id IS NOT NULL OR design_test_case_id IS NOT NULL)` |
| `t_review_task` | `UNIQUE(workspace_id, review_id)` + `asset_type`/`asset_id` 多态引用（不设 FK） |

所有表遵循现有风格：`id UUID PRIMARY KEY DEFAULT uuid_generate_v4()`、`tenant_id NOT NULL REFERENCES t_tenant(id) ON DELETE CASCADE`、`created_at/updated_at TIMESTAMP`。

---

## 验证

### 四源命中验证

```text
概念(PascalCase)    03术语  04领域  32API  33DB
TestingIR           3       7       8      1 (t_testing_ir)
BusinessRule        2       3       3      1 (t_business_rule)
Assertion           5       14      15     8
ReviewTask          2       4       6      1 (t_review_task)
Source Trace        1       1       3      3 (source_trace 字段)
```

### 计数验证

- API schema 总数：56（新增 4）
- DB CREATE TABLE 总数：50（新增 4，对应编号 38-41）
- 新增 API 路径：7 个路径 / 9 个操作

---

## B-3 整改完成声明

至此 B-3 的 6 个概念全部进入四源：

| 概念 | 补入批次 | 补入日期 |
|---|---|---|
| CoverageReport | 前序（CHANGELOG-2026-07-31）| 2026-07-31 |
| TestingIR | 本轮 | 2026-08-04 |
| BusinessRule | 本轮 | 2026-08-04 |
| Assertion | 本轮 | 2026-08-04 |
| ReviewTask | 本轮 | 2026-08-04 |
| SourceTrace | 本轮 | 2026-08-04 |

**B-3 关闭**。

---

## Phase 0 Blocker 状态汇总

| Blocker | 状态 | 关闭依据 |
|---|---|---|
| B-1 RequirementDocument 状态枚举冲突 | ✅ 已修复 | CHANGELOG-2026-07-31 修复一 |
| B-2 DesignTestCase 双状态机冲突 | ✅ 已修复 | CHANGELOG-2026-07-31 修复四（第二批）|
| B-3 可信链 6 概念零契约 | ✅ 已修复 | CoverageReport 见 07-31；剩余 5 概念见本文档 |
| B-4 AI 阈值散落无校准 | ❌ 未处理 | 需校准数据集，可与开发并行 |
| B-5 LLM 输出无外部 oracle | ❌ 未处理 | 需金标准集/抽检协议，可与开发并行 |
| B-6 四大收益指标不可验收 | ❌ 未处理 | 需基线+测量方法，可与开发并行 |

**Phase 0 核心结论**：B-1/B-2/B-3 三个阻断开发地基的 Blocker **全部解除**。B-4/B-5/B-6 属于"开发完能否验收"问题，不阻断契约实现，可与编码并行推进。

TestDesign 单模块 MVP 开发的契约障碍已清除。
