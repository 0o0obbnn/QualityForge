# 18-旧CI/CD模块迁移说明

> 本文件保留编号和文件名以兼容历史引用，不再是现行一级模块PRD。现行一级模块只有8个。

## 1. 职责迁移

| 旧职责 | 现行Owner | 入口/实体 |
|---|---|---|
| Webhook或Pipeline触发测试 | 测试执行 | ExecutionPlanVersion 触发批次、ExecutionPlan、ExecutionTask（“Batch”为一次触发/attempt 口语，不建独立实体，裁决 2026-08-14 批次二） |
| Pipeline配置与运行回执 | 质量分析与缺陷 | PipelineConfig、PipelineRun |
| 智能回归范围建议 | 质量分析与缺陷 | ResultAnalysis/质量门禁建议，引用测试规划与变化影响 |
| QualityGate规则与判断 | 质量分析与缺陷 | QualityGate、QualityGateVersion、QualityGateEvaluation |
| Git/CI凭据与端点 | 平台管理 | Integration、Secret、AuthorizationDecision |
| Agent/Skill编排 | AI Agent中心 | AgentWorkflow、Session、Trace |

## 2. 迁移规则

- 旧`/cicd/*`路径不再使用；现行路径见32/37号。
- 自动测试选择可以由AI生成建议，但门禁规则必须确定、版本化、可解释。
- CI/Webhook 触发属 V2 范围（裁决 B2-9，2026-08-14）；V1 仅支持手工与计划触发，18 号职责迁移不改变该版本边界。
- 门禁放行、阻断豁免、外部评论/状态写入始终是humanOnly高价值动作。
- 流水线HTTP成功不等于测试有效通过；需区分PASSED、FAILED、ERROR、BLOCKED和未执行。

## 3. 验收

- **Given** 旧文档链接到18号；**When** 用户打开；**Then** 能找到每项职责的新Owner，不会把CI/CD当第9模块。
- **Given** AI建议放行；**When** 没有适用规则版本或人工权限；**Then** 外部发布状态不被写入。
