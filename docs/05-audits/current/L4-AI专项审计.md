# L4 AI 系统专项审计（批次 3 产物）

> 方法：RE for ML/AI（Ahmad 2023; SEI/CMU）+ ISO/IEC 25059:2023（AI 质量模型）+ ISO/IEC 23053:2022（AI 框架）+ LLM-Native RE 视角（2025-2026 研究）。
> 本层是 AI-Native 平台独有的审计维度，普通需求评审（IEEE 830 等）的盲区。
> 审查日期：2026-07-30

---

## 子项 1：自治等级与降级矩阵一致性

**🟠 Critical · 自治等级直接冲突**

| 介入点 | 降级矩阵（21 号，权威）规定 | 模块 PRD 实际规定 | 冲突 |
|---|---|---|---|
| Test Design 用例生成 | **L2**（"入库前须人工终审"，21:27）| 允许置信度 >0.80 达 **L1 自动入库**（11:214-216）| 🔴 **直接冲突** |
| Test Asset Locator 自愈 | L1（可逆 + 阈值0.92 + 失败回退，21:30）| 三档：>0.92 自动 / 0.80-0.92 确认 / 连续3次失败（12:244-248）| ✅ 一致 |
| QI 失败根因分析 | L2（写 JIRA，21:32）| §5.3 置信度 ≥0.90 自动 / §5.4 另立 0.85 一键提单（14:157-162）| 🟡 **阈值口径内部冲突** |

**根因**：降级矩阵声明"默认安全、可选激进"（21:15），但 TestDesign PRD 把"可选激进"（L1 自动入库）写成了默认行为，违背了矩阵的 Safe-by-default 原则。按 ISO/IEC 23053 框架要求，AI 系统的人机控制边界必须显式且一致——此处不一致。

---

## 子项 2：阈值集中管理与校准

**🔴 Blocker · 阈值散落无校准，违反 ISO/IEC 25059 functional correctness 特性**

扫描发现置信度/相似度阈值分布（见 `概念权威基线.json`）：

| 阈值值 | 出现次数 | 出处示例 | 是否有校准集 |
|---|:---:|---|:---:|
| 0.80 | 18 | 11:214（用例自动入库）、18:195（TIA） | ❌ |
| 0.85 | 10 | 14:162（一键提单） | ❌ |
| 0.88 | 4 | 16:186（Agent 最高置信度） | ❌ |
| 0.90 | 8 | 14:157（自动分类）、19:182（Token Router） | ❌ |
| 0.92 | 6 | 12:244（Locator 自愈自动合并）、21:30 | ❌ |
| 0.95 | 3 | 17:9（RAG 相关度）、17:169 | ❌ |

**问题**：
1. **6 种不同阈值散落在 6 个模块**，无集中管理，无统一校准。
2. **没有任何阈值标注了校准集**（calibration set）。按 ISO/IEC 25059:2023，AI 系统的 functional correctness "不能在所有观察情形下保证"，因此阈值必须有校准数据集支撑——否则 0.80 和 0.85 的差异无依据，纯粹是拍脑袋。
3. **0.80 vs 0.85 vs 0.88 vs 0.90 vs 0.92 vs 0.95 的梯度关系无解释**——为什么用例生成是 0.80 而自愈是 0.92？风险维度不同应有论证，但文档无。

---

## 子项 3：评测覆盖度

**🟠 Critical · RE 与模型评估之间的鸿沟（SEI 指出的核心难题）**

| 评测维度 | 现状 | 缺口 |
|---|---|---|
| Skill 标准评测（evals.json）| 29 个 Skill 中仅 **3 个**有 evals.json（10.3%）| 90% 的 AI 能力无标准化评测 |
| E2E Coverage Gate | 存在于 prototypes/e2e-validation/06-gate | 规则覆盖 75%、场景覆盖 33.3%、状态转换覆盖 25%（**不达标**）|
| AI 正确性评测协议 | **完全缺失** | RCA 分类准确率、聚类纯度、TIA Recall 均无定义、无标注集 |

**SEI/CMU 明确指出**："RE 与 ML 模型评估之间的鸿沟是 ML 开发中最难的任务之一。"本项目正好卡在这个鸿沟上：需求（PRD）声明了 AI 能力（"精准分类""自愈"），但模型评估（evals）严重滞后，导致这些能力不可验证（呼应 L2 Verifiable 均分 1.8）。

---

## 子项 4：可信链证据完整性

**🔴 Blocker · 核心数据流无持久化契约**

详细证据见 L1-003。此处补充 AI 视角的分析：

Skill 原型的核心数据流是：
```
PRD → Testing IR → Business Rule → Scenario → TestCase → Assertion → Coverage Report → Review Task
```

这条链的每一环都被 Skill 使用（76~14 次命中），但**链上 6 个节点在正式契约（术语表/领域模型/API/DB）中零存在**。

按 ISO/IEC 25059:2023 的 traceability 特性和 Ahmad 2023 的 RE-for-AI 框架，AI 输出的可追溯性是关键 NFR。本项目的状态是：**AI 产出的核心数据无处落地、无法查询、无法审计**。如果 Skill 跑出一条 Assertion，它存哪？哪个 API 能查？哪个表有记录？——全无答案。

---

## 子项 5：人机协作可逆性

**🟡 Major · 有基本覆盖但深度不足**

| 可逆性维度 | 覆盖情况 | 证据 |
|---|---|---|
| 驳回/退回 | ✅ 多模块有 | 11/12/13/16/17 含"驳回/reject/回滚" |
| KnowledgeEntry 驳回 | ✅ 状态机有 | 04 状态机 §5：PendingReview→Draft |
| batch-approve 审计 | ❌ 缺失 | 无 ReviewDecision/Diff/事件原子性实体 |
| AI 决策回滚 | ⚠️ 部分 | Locator 自愈有"失败回退"，但用例自动入库无回滚 |
| Trace 审计展示 | ❌ 未定义 | AgentTraceNode 记录了 Trace，但审批界面是否展示未定义 |

---

## v2.1 新增 · LLM-Native RE 视角

> 基于 LLM-for-RE SLR（arXiv:2509.11446）、Hemmat 2025、Stein 2026。本项目自身即"LLM 增强的 RE 系统"，有特殊风险。

| 检查点 | 现状 | 风险 |
|---|---|---|
| **LLM 输出可验证性** | ❌ AI 生成用例后，无非 LLM 的客观验收手段 | 陷入"AI 自评 AI"循环（L3 视角 1 已确认）|
| **Prompt 契约工程化** | ⚠️ 有 AgentPromptVersion 实体（04:719）和 Prompt Versioning 概念（03:123） | 但 Prompt 内容本身未作为受评审的制品管理，无变更控制流程 |
| **LLM 幻觉/漂移防护** | ⚠️ 有 Source Trace 概念（Skill 中 39 次命中） | 但 Source Trace 未进正式契约（L1-003），无法保证落地 |
| **数据-模型-集成三件套（ISO/IEC 23053）** | ❌ 三件套分别约束缺失 | 训练/示例数据无管理规范；LLM 模型选择无约束（仅 19 号提"Token Router"）；集成层无契约 |

---

## L4 汇总：AI 系统专项缺陷清单

| ID | 缺陷 | Severity | ISO/25059 对应特性 |
|---|---|---|---|
| L4-001 | TestDesign 自治等级冲突（矩阵 L2 vs PRD L1）| 🟠 Critical | Controllability |
| L4-002 | 6 种阈值散落无校准集 | 🔴 Blocker | Functional Correctness |
| L4-003 | Skill evals 覆盖率仅 10.3% | 🟠 Critical | Appropriate（适宜性）|
| L4-004 | AI 正确性评测协议完全缺失 | 🟠 Critical | Functional Correctness |
| L4-005 | 可信链 6 概念无契约（同 L1-003）| 🔴 Blocker | Traceability |
| L4-006 | batch-approve 无审计实体 | 🟡 Major | Auditability |
| L4-007 | LLM 输出无外部 oracle（AI 自评循环）| 🔴 Blocker | Verifiability |
| L4-008 | Prompt 未作为受控制品管理 | 🟡 Major | Maintainability |

**Blocker 数：3（L4-002/005/007）**

---

## 本层结论

QualityForge 作为 AI-Native 平台，其 AI 系统的需求工程成熟度严重不足。核心问题不在"AI 能力是否存在"，而在"**AI 能力是否可信、可验证、可控**"：

1. **不可信**：阈值无校准（L4-002），AI 正确性无评测（L4-003/004）
2. **不可验证**：LLM 输出陷于自评循环（L4-007），可信链数据无处落地（L4-005）
3. **不可控**：自治等级冲突（L4-001），审计不完整（L4-006）

按 ISO/IEC 25059:2023 的判定，一个 AI 系统如果 functional correctness 不可保证且无校准，其质量模型评分应低于可接受阈值。本项目的 AI 专项在修订前**不得进入开发**。
