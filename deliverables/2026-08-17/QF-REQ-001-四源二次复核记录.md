# QualityForge QF-REQ-001 四源二次复核记录

> 日期：2026-08-17 ｜ 分支：`docs/qf-req-001-recheck` ｜ 执行人：lingma（后端轨，M1-B0 工作包第 1 项）
> 依据：问题台账 QF-REQ-001（deliverables/2026-08-13/QualityForge-问题台账-QF-REQ-001-048.md）、开发计划与方案 v1.1 §四 M1 后端验收第 4 条
> 前史：8-14 进度汇总判定「部分修复 3/6，存在二次假关闭风险」（L1 纠正报告误报）；本记录为 M1 开工之首的独立二次复核。

## 一、复核范围

QF-REQ-001 定义的 6 关键字段：`objective / acceptanceCriteria / requiresReview / lockVersion / constraints / agentId`（05 §5.5.3 规定）。

四个权威源（按 M1 实施计划 v1.1 口径）：

1. 源① 后端实现：`backend/src/qf/schemas/planning.py`（DTO）＋ `backend/src/qf/services/planning_workflow.py`（服务层落库）＋ `backend/src/qf/db/sqlite_store.py`（DDL）
2. 源② 契约：`docs/04-architecture/32-API规范.yaml`（WorkItem / WorkItemCreate schema）
3. 源③ 数据库设计：`docs/04-architecture/33-数据库Schema设计.md` `t_work_item` DDL
4. 源④ 领域模型：`docs/01-product/04-核心领域模型.md` §3.1（注：实际位于 01-product 目录，台账原文「04 §3.1」指向同一文件）

## 二、实测核对表（复核时点状态）

| 字段 | 源① 后端 | 源② 契约 32 | 源③ DDL 33 | 源④ 领域模型 04 |
|---|---|---|---|---|
| objective | ❌ 未建模 | ✅ WorkItem required + WorkItemCreate required（L809/820、L840/849） | ✅ `objective TEXT NOT NULL` | ✅ 必填行 |
| acceptanceCriteria | ❌ 未建模 | ✅ 双侧 required（L809/821、L840/850） | ✅ `acceptance_criteria TEXT NOT NULL DEFAULT '{}'` | ✅ 必填行 |
| requiresReview | ❌ 未建模 | ✅ 双侧 required，Create 带 `default: true`（L824、L853） | ✅ `requires_review BOOLEAN NOT NULL DEFAULT TRUE` | ✅ 必填行 |
| lockVersion | ❌ 未建模 | ✅ 仅 WorkItem required（L809/825），Create 不含（服务端初始化，口径正确） | ✅ `lock_version INT NOT NULL DEFAULT 0` | ✅ 必填行 |
| constraints | ❌ 未建模 | ✅ 双侧可选（L822、L851） | ✅ `constraints TEXT` 可空 | ✅ 可空行 |
| agentId | ❌ 未建模 | ✅ 双侧可选 uuid（L823、L852） | ✅ `agent_id UUID REFERENCES t_agent(id)` | ✅ 可空行 |
| **合计** | **0/6** | **6/6** | **6/6** | **6/6** |

**结论**：8-14「3/6」判定所指的三个文档源此后已被补齐至 6/6（实测确认）；真正的缺口整体转移到源①后端实现——DTO 与服务层 0/6。sqlite_store 为 payload JSON 整体存储（无独立列），字段随 payload 透传，不构成独立缺口。

## 三、本批复修（源①）

1. `schemas/planning.py` WorkItemCreate 补 5 字段：`objective`（必填，≤4000）、`acceptanceCriteria`（必填，≤8000）、`requiresReview`（必填 bool）、`constraints`（可空）、`agentId`（可空 uuid）。与契约 L840 required 列表逐字对齐；`lockVersion` 按契约不在 Create 内。
2. `planning_workflow.py` create_work_item 落库 6 字段（`lockVersion` 服务端初始化为 0），响应随实体返回，满足契约 WorkItem required 列表（L809）。
3. 三处既有测试载荷同步补齐；characterization 基线新增断言：六字段可见、`lockVersion==0`、`agentId` 缺省 None、缺 required 字段入口层 422。

**语义边界（明示，非遗漏）**：`requiresReview=false` 免审路径与 `lockVersion` 陈旧提交 409 的行为接线归 M1-B1（M1 实施计划 v1.1 §M1-B1 第 1 条已列）；本批只完成建模对齐。`workItemType` 后端 4 值子集（STRATEGY/PLAN/CASE/GENERAL）窄于契约 11 值枚举，为切片限制、与 QF-REQ-002 裁决（11 值为权威）不冲突，维持现状。

## 四、复核附带发现（登记增量台账，不当场扩围）

### QF-REQ-078 · 运行时会话状态枚举与契约枚举不一致 【严重】

- **问题**：`planning_workflow.py` 运行时 AgentSession 状态走 `RUNNING → PAUSED_FOR_HUMAN → COMPLETED`（L399、L403、L683-700），而 32 号契约 AgentSession.status 枚举为 `PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED/BLOCKED`（批次二十三已对齐 33 号 CHECK），且 `test_contract_enums.py` 明确将 `PAUSED_FOR_HUMAN/COMPLETED` 列入废弃值黑名单——现有契约测试只校验 yaml↔33 号，未覆盖运行时取值，故漂移未被拦截。
- **整改建议**：归 M1-B1 退回闭环一并收敛（会话生命周期状态映射到契约枚举），并补运行时枚举对齐断言。

### QF-REQ-079 · M1 实施计划现状表口径偏差（两行六个 operation） 【轻微】

- **问题**：M1 实施计划 v1.1 §一 将 `createTestStrategy/createTestPlan/createTestCase/createTestCaseVersion` 列为「已实现」，实测实现清单（test_openapi_contract.py EXPECTED_IMPLEMENTED_OPERATION_IDS，22 项）仅含对应四个 list，四个 create 均未实现。
- **处置**：本记录随批更正 M1 实施计划两行口径（改判「未实现，M1 范围再评估」），不扩围实现。

## 五、关闭判定

- 四源 6/6 对齐：文档三源实测齐全＋后端源本批复修，全部有测试固化。
- 双落账：内容提交＋CHANGELOG 批次二十九登记后 QF-REQ-001 标 CLOSED。
- 防二次假关闭：本记录所有「✅」均为当次 grep/Read 实测，未引用任何前轮报告的转述结论。
