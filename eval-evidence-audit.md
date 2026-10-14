# QualityForge 产品评估 · 审计证据提取报告

> **提取日期**: 2026-08-07
> **提取范围**: `docs/05-audits/current/` 全量 11 份文件
> **审计日期**: 2026-07-30
> **审计方法**: Fagan Inspection + IEEE 830/29148 + Wiegers 十特性 + PBR + RE-for-ML + RTM + ISTQB 分级

---

## 一、审计文档清单

| # | 文件路径 | 内容摘要 |
|---|---|---|
| 1 | `docs/05-audits/current/00-审计清单.md` | 47 份被审文档索引 + 审计基线依据 |
| 2 | `docs/05-audits/current/L1-一致性缺陷清单.md` | 6 条跨契约硬冲突（3 Blocker / 2 Critical / 1 Major） |
| 3 | `docs/05-audits/current/L2-模块审查汇总.md` | 10 模块 Wiegers 十特性评分 + 系统性缺陷分析 |
| 4 | `docs/05-audits/current/L3-视角审查汇总.md` | 6 个 PBR 视角阻塞清单 |
| 5 | `docs/05-audits/current/L4-AI专项审计.md` | 5 子项 + LLM-Native 视角（8 缺陷，3 Blocker） |
| 6 | `docs/05-audits/current/L5-追踪矩阵.md` | RTM 双向追踪（核心价值链 6/8 断点） |
| 7 | `docs/05-audits/current/L5-收益可验收性表.md` | 4 大核心收益指标可验收性评估 |
| 8 | `docs/05-audits/current/L5-范围资源适配.md` | 规模 vs 资源中立比对 |
| 9 | `docs/05-audits/current/总裁决报告.md` | 缺陷总清单 + 整改路线图 + 最终裁决 |
| 10 | `docs/05-audits/current/概念权威基线.json` | L1 机器扫描对照基准（实体/状态机/阈值） |
| 11 | `docs/05-audits/current/skill-audit-2026-08-07.md` | 29 个 Skill 五维评估报告 |

---

## 二、Blocker 缺陷清单（B-1 ~ B-6）

| ID | 缺陷描述 | 产品后果（一句话） | 证据来源 | 修复方向 |
|---|---|---|---|---|
| **B-1** | RequirementDocument 状态枚举跨文档冲突：领域模型/API 规范定义 `Draft/Parsing/Completed/Failed`，但 TestDesign PRD 使用 `PENDING/PARSED/FAILED`（全大写，且缺少 Parsing 状态） | 开发时无法确定以哪套枚举为准，状态机实现会产生死代码或漏分支 | `L1-一致性缺陷清单.md` 第一节；`04-核心领域模型.md:828`；`32-API规范.yaml:3101`；`11-PRD-TestDesign.md:75` | 统一为领域模型定义的 4 值，修订 11 号 PRD |
| **B-2** | DesignTestCase 未进入正式契约：术语表/领域模型/API 规范/DB Schema 中均无 DesignTestCase；且与 TestCase 存在双状态机冲突（DRAFT/GENERATING/REVIEWING/APPROVED vs Draft/Reviewed/Deprecated），草稿→正式的映射规则完全未定义 | 核心价值链"需求→测试资产"的数据落地无统一契约，前后端/AI 服务/资产服务将各按各自理解实现 | `L1-一致性缺陷清单.md` 第二节；`11-PRD-TestDesign.md:101/112/120-125` | 裁决草稿/正式关系，补入领域模型/API/DB，定义状态流转 |
| **B-3** | 可信链 6 核心概念（Testing IR / Assertion / Source Trace / Review Task / Business Rule / Coverage Report）在 Skill 中高频使用，但在术语表/领域模型/API/DB 中全部零命中 | Skill 产出的核心数据无处持久化、无 API 可查、无领域模型可依，形成可信链的物理断层 | `L1-一致性缺陷清单.md` 第三节；`L4-AI专项审计.md` 子项 4；`概念权威基线.json` `skills_used_concepts_not_in_domain` | 补入术语表/领域模型/API/DB，建立持久化契约 |
| **B-4** | 6 种 AI 置信度/相似度阈值（0.80 / 0.85 / 0.88 / 0.90 / 0.92 / 0.95）散落在 6 个模块中，无集中管理，且没有任何阈值标注校准集 | 0.80 与 0.85/0.92 等差异无 empirical 依据，AI 自治决策沦为拍脑袋，无法保证 functional correctness | `L4-AI专项审计.md` 子项 2；`概念权威基线.json` `ai_thresholds_observed` | 建立集中阈值表 + 每个阈值配校准集 |
| **B-5** | LLM 输出无外部 oracle：AI 生成用例后无非 LLM 的客观验收手段，陷入"AI 自评 AI"循环 | 用户无法判断 AI 产出是否正确，AI 能力的可信度无法被独立验证 | `L4-AI专项审计.md` 子项 4 与 v2.1；`L3-视角审查汇总.md` 视角 1 | 为 AI 输出设计非 LLM 的客观验收手段（金标准集 / 人工抽检协议） |
| **B-6** | 四大核心收益指标全部不可验收：均无 BASELINE（基线）、无 MEASUREMENT（测量方法）、无验收门槛 | 即使平台全部开发完成，也无法回答"我们是否达成了产品目标"，等同于无目标开发 | `L5-收益可验收性表.md`；`总裁决报告.md` 第二章 | 每个指标补 BASELINE + MEASUREMENT + 门槛 |

---

## 三、Critical 缺陷清单（C-1 ~ C-7）

| ID | 缺陷描述 | 产品后果（一句话） | 证据来源 |
|---|---|---|---|
| **C-1** | TestPlan 丢失 Requirement 外键关联：领域模型字段表与 ER 图均确认 TestPlan 仅关联 TestScenario，无 `requirementId`/`requirementDocumentId` | 无法从测试计划回溯到需求文档，需求变更时无法自动评估受影响的 TestPlan，正向追踪性断裂 | `L1-一致性缺陷清单.md` 第四节；`04-核心领域模型.md:365-377` |
| **C-2** | 覆盖率（Coverage）无正式领域语义：领域模型/API/DB 中无 Coverage 实体，PRD 仅以"比例"形式出现，无分子/分母定义、无版本化实体、无覆盖率类型 | 质量门禁依赖覆盖率判定，但覆盖率本身无契约定义，门禁规则无法真正实现 | `L1-一致性缺陷清单.md` 第五节；`L5-追踪矩阵.md` |
| **C-3** | TestDesign 自治等级冲突：降级矩阵（L2 权威）规定"用例生成入库前须人工终审"，但 TestDesign PRD 允许置信度 >0.80 时 L1 自动入库 | AI 人机控制边界不一致，违背了 Safe-by-default 原则，用户可能在不知情下接受未经审核的 AI 用例 | `L4-AI专项审计.md` 子项 1；`21-AI介入点降级矩阵.md:27`；`11-PRD-TestDesign.md:214-216` |
| **C-4** | Skill 标准评测覆盖率仅 10.3%：29 个 Skill 中仅 3 个有 evals.json | 90% 的 AI 能力无标准化评测，PRD 声明的 AI 功能不可验证 | `L4-AI专项审计.md` 子项 3；`skill-audit-2026-08-07.md` 第七节 |
| **C-5** | AI 正确性评测协议完全缺失：RCA 分类准确率、聚类纯度、TIA Recall 均无定义、无标注集 | "精准分类""自愈""TIA 精准选择"等 AI 能力无法被证伪或验收 | `L4-AI专项审计.md` 子项 3；`L2-模块审查汇总.md` L2-D |
| **C-6** | 总纲"用户只有一个测试工程师"是全平台一致性缺陷根源 | 单一用户定位与审批人、平台管理员、LDAP/SSO、多租户隔离等多角色需求直接矛盾，导致设计一致性系统性失守 | `L2-模块审查汇总.md` 第二节；`L3-视角审查汇总.md` 视角 3/4；`总裁决报告.md` 第二章 |
| **C-7** | 基础设施无单机 MVP 降级路径：分布式 Runner 集群、K8s+gVisor/Kata 沙箱、K6 压测 + OWASP_ZAP 等企业级基础设施无轻量化方案 | 在单人/单机/0 行代码现状下，MVP 无法落地，企业级目标与原型阶段资源严重错配 | `L2-模块审查汇总.md` L2-E；`L5-范围资源适配.md`；`总裁决报告.md` 第二章 |

---

## 四、Major 级关注项

| ID / 代号 | 描述 | 产品后果 | 证据来源 |
|---|---|---|---|
| **L2-A** | 全平台 10 份 PRD 零条 Given/When/Then 验收标准 | 所有功能无法被独立验证，IEEE 830「Verifiable」特性全线崩塌 | `L2-模块审查汇总.md` 第一节；`总裁决报告.md` 第二章 |
| **L2-B** | 四大收益指标无基线/无评测协议 | 无法衡量产品成功，与 B-6 同源 | `L2-模块审查汇总.md` 第一节；`L5-收益可验收性表.md` |
| **L2-D** | AI 正确性不可证伪（RCA/聚类/TIA） | AI 能力宣称不可验证 | `L2-模块审查汇总.md` |
| **L2-F** | 模糊词泛滥："精准""智能""高仿真""充分覆盖"等无准确率定义 | 需求歧义，验收标准无法量化 | `L2-模块审查汇总.md` 第三节；`L3-视角审查汇总.md` |
| **L4-006** | batch-approve 无审计实体：无 ReviewDecision / Diff / 事件原子性实体 | 批量审批无法被审计，人机协作可逆性深度不足 | `L4-AI专项审计.md` 子项 5；`总裁决报告.md` 第二章 |
| **L4-008** | Prompt 未作为受控制品管理：Prompt 内容本身未纳入变更控制流程 | Agent 行为难以复现、难以审计、难以维护 | `L4-AI专项审计.md` v2.1 节；`总裁决报告.md` 第二章 |
| **L1-006** | DB Schema 表数（43）与领域模型实体数（38）不匹配，差值 5 张表未登记 | 无法确认差额表是关联表还是业务表，领域模型可能滞后或 DB 存在隐式业务表 | `L1-一致性缺陷清单.md` 第六节；`总裁决报告.md` 第二章 |
| **L3-Top1** | 角色定义矛盾（单一用户 vs 实际多角色） | 多视角共同阻塞点，与 C-6 同源 | `L3-视角审查汇总.md` 跨视角汇总 |
| **L3-Top2** | AI 正确性无外部 oracle（置信度自评循环） | 与 B-5 同源 | `L3-视角审查汇总.md` 视角 1 |
| **L3-Top4** | 基础设施无单机降级 | 与 C-7 同源 | `L3-视角审查汇总.md` 视角 4 |
| **L3-Top5** | 收益指标无基线 | 与 B-6 同源 | `L3-视角审查汇总.md` 视角 1/3 |

---

## 五、四大核心收益指标（ verbatim 原文 + 评估）

来源：`docs/05-audits/current/L5-收益可验收性表.md`

| # | 指标原文（verbatim） | 出处 | BASELINE | MEASUREMENT | VERDICT |
|---|---|---|---|---|---|
| 1 | "实现需求到测试方案/用例的端到端生成，将手工编写测试设计大纲的耗时缩短 80% 以上。" | `11:15` | ❌ 无（缩短自多少？人工编写 N 条用例耗时 T0 未定义） | ❌ 无（AI 生成耗时 T1 如何测、取 P50/P90 未定义） | **UNSUPPORTED** |
| 2 | "在 15 秒内将失败类型精准分类，将人工排查时间降低 80% 以上。" | `14:9` | ❌ 无（现状人工排查耗时基线未定义） | ❌ 无（15 秒 SLA 无 LLM 推理时延论证；80% 如何测未定义） | **UNSUPPORTED** |
| 3 | "使 AI Agent 设计测试用例时的信息关联相关度达到 95% 以上。" | `17:9` | ❌ 无（"相关度"本身未定义） | ❌ 无（Recall@K？NDCG？人工一致率 Kappa？评测集来源？） | **AMBIGUOUS** |
| 4 | "在保障覆盖率的前提下，使 CI 回归用例执行时间缩短 60% 以上。" | `18:9` | ❌ 无（全量回归耗时基线未定义） | ❌ 无（TIA 增量 vs 全量？取 P50？覆盖率保障前提下如何测？） | **UNSUPPORTED** |

### L5-收益可验收性表裁决

> **四大核心收益指标全部不可验收**（3 个 UNSUPPORTED + 1 个 AMBIGUOUS）。
> 这意味着：**即使平台全部开发完成，也无法回答"我们是否达成了产品目标"**。这是产品定义层面的致命缺陷——没有成功标准，就无法判断成功。

---

## 六、范围 vs 资源适配数据

来源：`docs/05-audits/current/L5-范围资源适配.md`

### 6.1 需求规模（客观度量）

| 维度 | 数量 | 出处 |
|---|---|---|
| 核心模块 | 9 + 平台设置 = **10** | `02-PRD总纲` |
| PRD 文档总行数 | ~**3,125** 行 | `10-19` + `02` + `20` |
| 领域实体 | **38** | `04-核心领域模型` |
| API 路径 | **88** | `32-API规范.yaml` |
| DB 表 | **43** | `33-数据库Schema设计` |
| Skill 原型 | **29** | `prototypes/skills/` |
| WebSocket 事件 | **5** | `36-WebSocket实时契约` |
| AI 介入点 | **13** | `21-降级矩阵` |
| NFR 目标项 | **5 大维度**（性能/安全/高可用/可观测/数据一致性） | `20-非功能需求` |

### 6.2 技术栈复杂度

| 层 | 技术 | 复杂度信号 |
|---|---|---|
| 后端业务 | Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Alembic | 中高（全异步栈） |
| 后端 AI | LangGraph + Pydantic v2 + asyncio | 高（Agent 编排） |
| 前端 | React 18.3 + TS + Vite + Zustand + Radix UI | 中 |
| 存储 | PostgreSQL 16 + PGVector + Redis 7 + RabbitMQ + Redis Streams | 高（5 种存储） |
| 基础设施 | K8s + gVisor/Kata + KEDA + 分布式 Runner | **极高** |
| 安全 | RLS + 双信封加密 + LDAP/SSO + NetworkPolicy | 高 |

### 6.3 可用资源（客观度量）

| 维度 | 现状 | 证据 |
|---|---|---|
| 人力 | **单人** | 项目无团队结构、无协作痕迹 |
| 设备 | **单台 MacBook** | `30-技术选型决策` 上下文；无服务器/集群声明 |
| 代码 | **0 行应用代码**（仅 Skill 校验脚本） | 探索确认无 src/backend/frontend |
| 阶段 | **纯文档设计** | 50 份文档，无实现 |

### 6.4 规模—资源适配性比对（节选）

| 需求规模维度 | 单人单机承载能力评估 | 证据/推理 |
|---|---|---|
| 9 模块企业级平台 | ⚠️ 偏重 | 企业级测试平台通常由 10+ 人团队开发 |
| 分布式 Runner 集群 | 🔴 不匹配 | "数以万计用例"（`13:17`）需多节点集群 |
| K8s + gVisor/Kata 沙箱 | 🔴 不匹配 | 需 K8s 集群 + 安全容器运行时（`15:137-141`） |
| K6 压测 + OWASP_ZAP | 🟠 勉强 | 可单机运行但资源开销大 |
| 5,000/50,000 API 并发（NFR） | 🔴 不匹配 | NFR 是 SLO Target，但单机无法验证 |
| LangGraph Agent 编排 | ✅ 可行 | 单机可跑 |
| PGVector RAG | ✅ 可行 | 单机 PostgreSQL 可承载 |
| 全异步 Python 栈 | ✅ 可行 | 单机开发无障碍 |

### 6.5 L5-范围资源适配结论

> **客观事实**：
> 1. 需求规模（9 模块 / 38 实体 / 88 API / 43 表 / 29 Skill）对应的是企业级平台。
> 2. 可用资源（单人 / 单机 / 0 行代码）对应的是原型/MVP 阶段。
> 3. 两者存在客观落差，尤其在分布式 Runner、K8s 沙箱、高并发 NFR 三个维度。

---

## 七、L2 模块十特性评分

来源：`docs/05-audits/current/L2-模块审查汇总.md`

### 7.1 模块成熟度裁决汇总

| # | 模块 | 均分 | 裁决 | Blocker | Critical |
|---|:---:|---|:---:|---|---|
| 11 | TestDesign | 2.7 | **REVISE** | 3 | 0 |
| 12 | TestAsset | 2.8 | **REVISE** | 1 | 0 |
| 13 | Execution | 3.0 | PASS_WITH_ACTIONS | 0 | 1 |
| 14 | QualityIntelligence | 2.9 | **REVISE_AND_FOCUS** | 0 | 2 |
| 15 | SkillCenter | 3.3 | PASS_WITH_ACTIONS | 0 | 1 |
| 16 | AgentCenter | 3.6 | PASS_WITH_ACTIONS | 0 | 0 |
| 17 | KnowledgeCenter | 3.5 | PASS_WITH_ACTIONS | 0 | 1 |
| 18 | CICD | 3.6 | PASS_WITH_ACTIONS | 0 | 1 |
| 19 | PlatformSettings | 3.9 | PASS_WITH_ACTIONS | 0 | 0 |
| 02 | 总纲 | 3.0 | **REVISE** | 0 | 1 |

**加权整体均分：3.2 / 5.0**

### 7.2 各特性均分雷达（Wiegers 十特性）

| 特性 | 均分 | 评级 |
|---|:---:|---|
| Necessary 必要性 | 4.6 | ✅ 强 |
| Prioritized 优先级 | 3.4 | ⚠️ 两极分化 |
| Feasible 可行性 | 3.3 | ⚠️ 基础设施错配 |
| Correct 正确性 | 4.0 | ✅ 强 |
| Traceable 可追踪性 | 3.3 | ⚠️ 无 REQ-ID 体系 |
| Atomic 原子性 | 3.3 | ⚠️ 功能捆包过粗 |
| Complete 完整性 | 2.8 | 🔴 验收标准缺失 |
| Consistent 一致性 | 2.6 | 🔴 角色矛盾 |
| Unambiguous 无歧义 | 2.7 | 🔴 模糊词泛滥 |
| Verifiable 可验证性 | 1.8 | 🔴 全线崩塌 |

### 7.3 L2 跨模块系统性缺陷（按十特性维度）

1. **Verifiable 可验证性 —— 全平台最弱（均分 ~1.8/5）🔴**
   - 所有 10 份 PRD 零条 Given/When/Then 验收标准。
   - 三大/四大核心收益指标全部不可验收。

2. **Consistent 一致性 —— 第二弱（均分 ~2.6/5）🔴**
   - 根因：总纲 L73「用户只有一个测试工程师」是全平台一致性缺陷的源头。
   - 子模块实际涉及审批人、平台管理员、LDAP/GitHub 组织权限、多租户隔离。

3. **Unambiguous 无歧义 —— 模糊词泛滥（均分 ~2.7/5）🟠**
   - 高频模糊词："精准""智能提取""自动抽离""高仿真""充分覆盖""海量失败"等。

4. **Feasible 可行性 —— 基础设施与资源错配（均分 ~3.0/5）🟠**
   - 重型基础设施：分布式 Runner 集群、K8s+gVisor/Kata 沙箱、K6+ZAP、5,000/50,000 并发 NFR。
   - 所有模块只给 AI 降级策略，未给基础设施降级/MVP 路径。

---

## 八、总裁决报告缺陷总清单与路线图

来源：`docs/05-audits/current/总裁决报告.md`

### 8.1 全平台成熟度裁决

**加权整体均分：3.2 / 5.0**

**裁决：REVISE_AND_FOCUS**

**硬门禁触发**：TestDesign 模块存在 3 个 Blocker（B-1 / B-2 / B-3）→ 核心价值链模块有 Blocker → 全平台不得 PASS，需在完成关键整改后复审。

### 8.2 缺陷总清单（已在上文 B/C 节详列，此处为总裁决汇总）

| 级别 | 数量 | 缺陷 ID |
|---|---|---|
| Blocker | 6 | B-1 ~ B-6 |
| Critical | 7 | C-1 ~ C-7 |
| Major | 多项 | L2-A/F、L4-006/008、L1-006 等 |

### 8.3 整改优先级路线图

#### Phase 0 · 必须先做（解锁一切后续工作）

| 序 | 整改项 | 解决的缺陷 | 预估工作量 |
|---|---|---|---|
| 0.1 | 裁决并统一 DesignTestCase / TestCase 关系 | B-2 | 中（需架构决策） |
| 0.2 | 补可信链 6 概念的正式契约（术语/领域/API/DB） | B-3 | 大（涉及全链路） |
| 0.3 | 修订总纲角色定义（解决"单一用户"矛盾） | C-6 | 小（但影响面大） |

#### Phase 1 · 核心价值链可验收化

| 序 | 整改项 | 解决的缺陷 |
|---|---|---|
| 1.1 | 为 TestDesign + TestAsset 每个功能补 Given/When/Then | B-6 部分 / L2-A |
| 1.2 | 四大收益指标补 BASELINE + MEASUREMENT + 门槛 | B-6 |
| 1.3 | 建立 AI 阈值集中表 + 校准集规划 | B-4 |
| 1.4 | 为 AI 输出设计外部 oracle（金标准集 / 人工抽检协议） | B-5 |

#### Phase 2 · AI 可信化

| 序 | 整改项 | 解决的缺陷 |
|---|---|---|
| 2.1 | 定义 RCA/聚类/TIA 的准确率目标 + 标注评测集 | C-5 |
| 2.2 | 补全 29 个 Skill 的 evals.json | C-4 |
| 2.3 | 统一自治等级，消除矩阵 vs PRD 冲突 | C-3 |

#### Phase 3 · 一致性与追踪性

| 序 | 整改项 | 解决的缺陷 |
|---|---|---|
| 3.1 | 统一 RequirementDocument 状态枚举 | B-1 |
| 3.2 | 补 TestPlan→Requirement 外键 | C-1 |
| 3.3 | 补 Coverage 领域语义 | C-2 |
| 3.4 | 建立 REQ-ID 体系 + 追踪矩阵 | L5-追踪 |

#### Phase 4 · 可行性与范围（决策者主导）

| 序 | 整改项 | 解决的缺陷 |
|---|---|---|
| 4.1 | 各模块补单机 MVP / 基础设施降级路径 | C-7 |
| 4.2 | 范围战略决策（收敛 vs 扩张资源） | L5-适配 |

### 8.4 总裁决最终结论

> QualityForge 的需求体系**广度完整（PRD/API/DB/架构/NFR/AI治理齐全）但深度不足**（验收标准全线缺失、AI 可信性未建立、核心契约有断层），成熟度 **3.2/5.0**，裁决 **REVISE_AND_FOCUS**。

三个核心判断：
1. **方向正确，但"可信链"有物理断层**：Testing IR / Assertion / Coverage 等核心概念被 Skill 使用但无正式契约（B-3）——这是最优先修复的，否则开发无地基。
2. **AI 能力宣称领先于可验证性**：四大收益指标全不可验收（B-6），AI 正确性无评测（C-5），阈值无校准（B-4）——这意味着"开发完成"无法等同于"达成目标"。
3. **一致性根源在总纲**：角色定义矛盾（C-6）是全平台一致性缺陷的单点根源，修复成本最低、收益最高。

---

## 九、L5 端到端追踪矩阵摘要

来源：`docs/05-audits/current/L5-追踪矩阵.md`

### 9.1 核心价值链追踪断点

| 目标 | 功能 | API | DB 实体 | 验收标准 | 断点 |
|---|---|---|---|---|---|
| 需求自动解析 | TestDesign 需求解析(`11:44`) | ❓ | RequirementDocument | ❌ 无 G/W/T | 🔴 断 |
| 生成测试用例 | AI 用例生成(`11:49`) | ❓ | **DesignTestCase** | ❌ 无 G/W/T | 🔴 不在正式契约 |
| 用例评审入库 | TestCase Review(`11:135`) | ❓ | TestCase | ❌ 无 G/W/T | 🔴 状态流转未定义 |
| 生成测试断言 | Assertion 生成(Skill) | ❌ 无 | ❌ 无 | ❌ 无 G/W/T | 🔴 **L1-003 全链断** |
| 覆盖率分析 | Coverage(Skill) | ❌ 无 | ❌ 无 | ❌ 无 G/W/T | 🔴 **L1-005 全链断** |
| 用例执行 | Execution(`13`) | ✅ 有 | ExecutionTask | ❌ 无 G/W/T | 🟡 验收断 |
| 根因分析 | RCA(`14:21`) | ✅ 有 | FailureAnalysis | ❌ 无 G/W/T | 🔴 AI 正确性无评测 |
| 知识沉淀 | KnowledgeEntry(`17`) | ✅ 有 | KnowledgeEntry | ❌ 无 G/W/T | 🟡 "95%相关度"无基线 |

**追踪结论**：核心价值链 8 个环节，**6 个存在断点**（🔴4 + 🟡2）。只有 Execution 和 RCA 的 API/DB 层贯通，但验收标准层全断。

### 9.2 反向孤儿检测

| 制品 | 类型 | 判定 |
|---|---|---|
| 88 条 API 路径 | API | 大部分有来源，但 Testing IR/Assertion/Coverage 相关路径缺失 |
| 43 张 DB 表 | DB | 38 张映射领域实体，5 张差额待核实（L1-006） |
| 29 个 Skill | Skill 原型 | ✅ 有功能来源 |
| DesignTestCase 表 | DB(PRD 内) | ✅ 有功能来源，但未进正式领域（正向断） |

### 9.3 追踪性总评

- Forward 正向追踪：🔴 严重断裂（6/8 环节有断点）
- Backward 反向追踪：🟡 基本正常（无孤儿，但正向缺口多）
- REQ-ID 体系：❌ 全平台无需求 ID，无法条目化追踪
- 跨文档引用：🟢 较好

---

## 十、Skill 原型评估摘要

来源：`docs/05-audits/current/skill-audit-2026-08-07.md`

### 10.1 五维评估框架

| 维度 | 1 分 | 3 分 | 5 分 |
|---|---|---|---|
| D1 清晰性 | 触发条件模糊 | 触发条件明确，判据可机械化执行 | 每条指令仅一种理解方式，输出有 Schema |
| D2 边界完整性 | 无 Must Not、无异常处理 | 有 Must Not，覆盖常见异常 | 硬约束 ≥3 条，降级策略明确，退出码语义完整 |
| D3 可维护性 | 规则散落正文 | 规则与逻辑分离，有 references | 配置集中管理，版本兼容声明 |
| D4 可验证性 | 检查项无法独立测试，无 CLI | 有 CLI 入口和确定性脚本 | 有 evals/ + 基准数据 + Given/When/Then |
| D5 结构完整性 | 缺 name/desc/Why/集成/示例中 ≥3 项 | 缺 Why 或集成或反例中的一项 | 全要素齐全 |

### 10.2 全量评分（节选 Top/Bottom）

| Skill | D1 | D2 | D3 | D4 | D5 | 总分 | 评级 |
|---|---|---|---|---|---|---|---|
| contract-drift-detector | 5 | 5 | 5 | 3 | 5 | 23 | ⭐⭐⭐⭐⭐ |
| assertion-verifier | 4 | 5 | 5 | 4 | 2 | 20 | ⭐⭐⭐⭐ |
| scenario-generator | 4 | 4 | 4 | 4 | 3 | 19 | ⭐⭐⭐⭐ |
| test-case-generator | 4 | 4 | 4 | 4 | 3 | 19 | ⭐⭐⭐⭐ |
| ...（共 29 个） | ... | ... | ... | ... | ... | ... | ... |
| performance-test-generator | 1 | 2 | 3 | 3 | 1 | 10 | ⭐⭐ |
| locator-discovery | 1 | 3 | 2 | 3 | 1 | 10 | ⭐⭐ |
| plan-orchestrator | 1 | 2 | 2 | 3 | 1 | 9 | ⭐⭐ |
| knowledge-memory | 1 | 2 | 2 | 3 | 1 | 9 | ⭐⭐ |

### 10.3 评级分布

| 评级 | 数量 | 占比 |
|---|---|---|
| ⭐⭐⭐⭐⭐ | 1 | 3% |
| ⭐⭐⭐⭐ | 20 | 67% |
| ⭐⭐⭐ | 5 | 17% |
| ⭐⭐ | 4 | 13% |
| ⭐ | 0 | 0% |

### 10.4 关键发现

1. **结构断层**：4 个「薄」skill（knowledge-memory / plan-orchestrator / performance-test-generator / locator-discovery）正文仅 15-16 行，核心逻辑 defer 到 references/，SKILL.md 失去自解释能力。
2. **D5 是最大短板**：仅 contract-drift-detector 得分 5；7/29 有 Why 章节；反例几乎全域缺失。
3. **D4 可验证性普遍薄弱**：仅 5/29 有 evals/ 目录，0/29 有 Given/When/Then 验收标准；CLI 覆盖率 9/29。
4. **D2 相对较好**：全部 29 个都有 Must Not，但降级策略覆盖率仅 20.7%（6/29）。

---

## 十一、概念权威基线关键字段（JSON 摘要）

来源：`docs/05-audits/current/概念权威基线.json`

### 11.1 38 个领域实体

Workspace, Environment, AIContext, TestPlan, TestScenario, TestCase, TestSuite, AutomationScript, TestData, MockConfig, Locator, APIContract, ExecutionPlan, ExecutionTask, Runner, ExecutionResult, TestReport, FailureCluster, FailureAnalysis, Skill, Agent, AgentWorkflow, KnowledgeEntry, PipelineConfig, PipelineRun, QualityGate, SkillInvocation, AgentPromptVersion, AgentSession, AgentTraceNode, TestDataProfile, BaselineItem, Tenant, User, WorkspaceSecret, RequirementDocument, TestSuiteCaseMapping, KnowledgeVector.

### 11.2 权威状态枚举（节选）

| 实体 | 权威状态值 |
|---|---|
| RequirementDocument | Draft / Parsing / Completed / Failed |
| TestCase | Draft / Reviewed / Deprecated |
| ExecutionTask | Pending / Running / Completed / Failed / Cancelled |
| KnowledgeEntry | Draft / PendingReview / Published / Archived |
| Locator | Verified / Decaying / Failed / Healed |

### 11.3 AI 介入点权威等级（节选）

| 介入点 | 权威等级 |
|---|---|
| TestDesign 用例生成 | L2（入库前须人工终审） |
| TestAsset Locator 自愈 | L1（可逆 + 阈值 0.92 + 失败回退） |

### 11.4 Skill 使用但无契约的概念（可信链缺口）

| 概念 | Skill 命中文件数 | 术语表 | 领域模型 | API | DB |
|---|---|---|---|---|---|
| Assertion | 76 | 0 | 0 | 0 | 0 |
| Source_Trace | 39 | 0 | 0 | 0 | 0 |
| Review_Task | 27 | 0 | 0 | 0 | 0 |
| Testing_IR | 14 | 0 | 0 | 0 | 0 |
| Business_Rule | 11 | 0 | 0 | 0 | 0 |
| Coverage_Report | 7 | 0 | 0 | 0 | 0 |

### 11.5 散落阈值分布

| 阈值 | 出现次数 |
|---|---|
| 0.80 | 18 |
| 0.85 | 10 |
| 0.90 | 8 |
| 0.92 | 6 |
| 0.88 | 4 |
| 0.95 | 3 |
| 0.50 / 0.60 / 0.70 | 各若干 |

---

## 十二、下游代理可复用速查表

### 12.1 Blocker/Critical 缺陷编号速查

| 编号 | 一句话产品后果 | 关联维度 |
|---|---|---|
| B-1 | 状态枚举不一致导致实现二义性 | 一致性 / 技术可行性 |
| B-2 | 核心价值链数据契约缺失 | 范围与 MVP / 技术可行性 |
| B-3 | AI 可信链物理断层 | AI 可信度 / 技术可行性 |
| B-4 | AI 阈值无校准，决策无据 | AI 可信度 |
| B-5 | AI 输出无法被客观验证 | AI 可信度 / 产品价值 |
| B-6 | 四大收益指标不可验收 | 产品价值 / ROI |
| C-1 | 需求→计划追踪断裂 | 范围与 MVP |
| C-2 | 覆盖率语义缺失导致门禁失效 | 范围与 MVP / AI 可信度 |
| C-3 | 用例生成自治等级冲突 | AI 可信度 |
| C-4 | 90% Skill 无 evals | AI 可信度 / 技术可行性 |
| C-5 | AI 正确性评测协议缺失 | AI 可信度 |
| C-6 | 单一用户定位与多角色需求矛盾 | 产品定位与价值 |
| C-7 | 企业级基础设施无单机 MVP 路径 | 技术可行性与工作量 |

### 12.2 关键数据点

| 数据项 | 数值 | 来源 |
|---|---|---|
| 模块数 | 10 | L2 |
| PRD 总行数 | ~3,125 | L5-范围资源适配 |
| 领域实体 | 38 | 04-核心领域模型 / 概念权威基线 |
| API 路径 | 88 | 32-API规范.yaml |
| DB 表 | 43 | 33-数据库Schema设计 |
| Skill 原型 | 29 | prototypes/skills/ |
| 整体成熟度 | 3.2 / 5.0 | 总裁决报告 |
| Blocker | 6 | 总裁决报告 |
| Critical | 7 | 总裁决报告 |
| 四大收益指标可验收性 | 0/4 | L5-收益可验收性表 |
| 核心价值链追踪断点 | 6/8 | L5-追踪矩阵 |
| Skill evals 覆盖率 | 10.3% | L4-AI专项审计 / skill-audit |

---

*本报告仅提取审计事实，不做产品判断。产品评估判断应由下游代理结合本证据与计划框架进行。*
