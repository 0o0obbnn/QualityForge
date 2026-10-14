---
name: plan-orchestrator
description: 校验草拟测试计划的阶段拓扑。在执行开始前、对计划文档使用。用 Kahn 算法从 depends_on_phases 计算无环性，要求每个阶段都有 entry_gate 和 exit_gate，拒绝后向跨阶段依赖与空阶段；PASS 时返回 phase_order。不得执行任务。不得评估 gate 条件是否为真（那需要 coverage-analyzer）。不得信任调用方提供的环标志。
---

# Plan Orchestrator

测试计划执行的结构校验器。它确保计划声明的各个阶段构成有效的有向无环图
（DAG），且依赖严格向前推进。

## 本 skill 为何存在

测试计划描述做*什么*，而编排器决定*怎么做*与*何时做*。带循环依赖的计划
（阶段 A 依赖阶段 B，阶段 B 又依赖阶段 A）在物理上不可执行。任务依赖更晚
阶段产出的计划则是时间悖论。本 skill 防止系统启动一个不可能执行的计划。

## Finding Codes 与路由

| 检查项 | Code | Severity | 含义 |
|---|---|---|---|
| 1 | `PHASE_CYCLE` | REJECT | 检测到阶段依赖环。 |
| 2 | `MISSING_ENTRY_GATE` | REJECT | 阶段缺 entry_gate。 |
| 2 | `MISSING_EXIT_GATE` | REJECT | 阶段缺 exit_gate。 |
| 3 | `BACKWARD_CROSS_PHASE_DEP` | REJECT | 任务依赖更晚的阶段。 |
| 4 | `EMPTY_PHASE` | REJECT | 阶段没有任何任务。 |
| 4 | `MISSING_PHASE_ID` | REJECT | 阶段没有 phase_id。 |
| 4 | `DUPLICATE_PHASE_ID` | REJECT | 同一 phase_id 声明了多次。 |
| 1/3 | `DANGLING_PHASE_DEPENDENCY` | REJECT | 依赖指向计划中不存在的阶段。 |
| 4 | `EMPTY_PLAN` | REJECT | 计划未声明任何阶段；无从校验。 |

处置：
- **REJECT**：计划结构无效，无法启动。必须退回规划步骤修正。

空计划判 REJECT，而不是轻飘的 PASS：没有声明任何阶段就没有计划可执行的
证据，而证据缺失绝不能读作干净通过的门禁。

## 运行确定性检查器

环检查用 Kahn 算法从图计算——绝不取自调用方提供的标志：

```bash
python scripts/plan_check.py --plan path/to/plan.json [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input. PASS 时报告携带
`phase_order`，即各阶段应当运行的顺序。

## Phase 拓扑序与 Gate 语义

阶段通过 `depends_on_phases[]` 声明依赖。gate 是任何非空值（字符串描述、
结构化条件或阈值引用）。
- `entry_gate`：阶段开始前检查。防止输入未就绪就启动。
- `exit_gate`：阶段完成前检查。防止带着未完成的工作推进。

## 本 skill 禁止事项

- **绝不执行任务。** 本 skill 校验结构；执行在下游。
- **绝不评估 gate 真值。** 验证字符串 "coverage >= 0.85" 是否为真需要 coverage-analyzer。本 skill 只确保 gate *存在*。
- **绝不优化计划。** 阶段排序是否最快或最省是规划质量问题，不是结构问题。
- **绝不信任调用方提供的环标志。** 无环性从 `depends_on_phases[]` 计算；问调用方自己的计划有没有环不叫检查。

## 使用示例

**示例 1 —— 正确触发**
```
编排新草拟的 UI Automation Plan 的执行。
```
→ 对阶段做拓扑排序。检查空阶段、缺失 gate 与跨阶段依赖。返回有效的
phase_order。

**示例 2 —— 错误触发（反模式）**
```
Phase 1 的 exit_gate 写着 "coverage >= 0.80"。查一下覆盖率是不是 0.80。
```
→ REJECT（概念上）。本 skill 不评估 gate 真值。交给 coverage-analyzer。
