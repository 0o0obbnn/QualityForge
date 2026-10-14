# 测试计划校验规则

`scripts/plan_check.py` 是可执行编码；本文件描述其意图。

## Finding Codes

| Check | Code | Severity | 含义 |
|---|---|---|---|
| 1 | `PHASE_CYCLE` | REJECT | 检测到 Phase 依赖成环。 |
| 2 | `MISSING_ENTRY_GATE` | REJECT | Phase 缺少 entry_gate。 |
| 2 | `MISSING_EXIT_GATE` | REJECT | Phase 缺少 exit_gate。 |
| 3 | `BACKWARD_CROSS_PHASE_DEP` | REJECT | 任务依赖了更晚的 Phase。 |
| 4 | `EMPTY_PHASE` | REJECT | Phase 没有任何任务。 |
| 4 | `MISSING_PHASE_ID` | REJECT | Phase 缺少 phase_id。 |

## Phase 拓扑序（Check 1）

Phase 通过 `depends_on_phases[]` 声明依赖。检查器运行 Kahn 算法得出合法执行顺序。一旦存在环，就不存在合法顺序——计划无法执行。

输出的 `phase_order` 是 Phase 应当运行的先后序列。Phase 内部任务按列出顺序执行（不做 Phase 内依赖检查——默认 Phase 内任务相互独立，或以列出顺序为序）。

## Gate 语义（Check 2）

| Gate | 检查时机 | 保护什么 |
|---|---|---|
| `entry_gate` | Phase 开始前。 | 前置条件已满足（如 "IR published"）。防止输入未就绪就开工。 |
| `exit_gate` | Phase 完成前。 | 目标已达成（如 "coverage >= 0.85"）。防止带着未完成的工作推进。 |

gate 是任意非空值（字符串描述、结构化条件或阈值引用）。检查器只验证存在性；判定 gate 真假是下游的事（覆盖率 gate 评估器、测试运行器）。

检查器 NOT 做的事：校验 gate 的内容。写着 `exit_gate: 'good enough'` 的 gate 结构上存在但语义空洞。要抓住这一点需要内容分析，超出本范围。

## 跨 Phase 依赖（Check 3）

任务的 `phase_dependency` 引用它需要其产出的 Phase。被引用的 Phase 在拓扑序中必须出现在任务所属 Phase **之前**。

该检查以列出顺序（拓扑排序前）作为启发式——如果依赖在列表中是向前的，拓扑排序后几乎必然也是向后的。前向引用无法满足：Phase 1 运行时，Phase 3 还没产出。

## 空 Phase（Check 4）

零任务的 Phase 只能是：
- 计划笔误（本想加任务，没加）。
- 遗留在计划里的废弃 Phase。
- 从未填充的占位符。

三者都会虚增表面范围、干扰进度追踪。REJECT。

## 本检查器 NOT 做的事

- **执行任务。** 这里只校验计划结构；执行在下游。
- **判定 gate 真假。** gate 条件是否实际成立，由运行时的 gate 评估器检查，不在这里。
- **优化计划。** Phase 排序是否最快/最省是计划质量问题，不是结构问题。
- **检查任务内容。** 任务步骤写得对不对是任务作者的事。
