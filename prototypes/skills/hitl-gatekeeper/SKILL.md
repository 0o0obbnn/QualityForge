---
name: hitl-gatekeeper
description: 对 AI 生成产物做 human-in-the-loop 路由决策。每个正式产物都要用；任一步骤命中关键路径、契约变更、breaking drift 或修复超限时也要用。只决定机器路由。不得批准、发布或修改产物。不得把置信度分数当作人类授权。
---

# HITL Gatekeeper

整个 AI 测试流水线的安全阀。它决定生成资产能否继续推进，防止幻觉断言、捏造的业务规则与静默的契约漂移。

**详细流程规则、触发条件与约束见 `references/detailed_rules.md`。**

## 高层摘要

- 接收来自 AI 生成步骤的输入（置信度、事件元数据、source trace）。
- 运行确定性路由器（`scripts/gate.py`）决定路由。
- 输出 `PASS` 或 `BLOCK_HUMAN`。
- 被阻断时发出 ReviewTask 请求并写入审计记录。
- 每个正式产物无论置信度多高都路由到 `BLOCK_HUMAN`。
- ReviewTask 输出必须绑定 `artifactType`、`artifactId`、`artifactVersionId`、`contentDigest`、`policyType`、所需能力与职责分离上下文。
- `PASS` 只表示一个非正式的机器步骤可以继续；它绝不意味着 `APPROVED` 或 `PUBLISHED`。

## 「必须有人来看」的规范化映射

流水线里的各 skill 对同一个底层状态发出八种不同的 token。它们**不是**彼此独立的结果：每一个都是必须路由进本门禁的触发器，而本门禁是唯一能产出带绑定契约的 ReviewTask 的组件。

| 发出方 skill | Token | 路由入口 |
|---|---|---|
| hitl-gatekeeper | `BLOCK_HUMAN` | （终点——本门禁） |
| ir-validator, requirement-compiler, requirement-quality-gate | `PASS_WITH_REVIEW` | `--event-type ambiguity_flag` |
| scenario-generator, test-case-generator, strategy-planner, locator-discovery | `REVIEW` | `--event-type ambiguity_flag` |
| business-rule-extractor | `NEED_HUMAN_REVIEW` | `--event-type ambiguity_flag` |
| assertion-verifier | `REPAIR` | 生产方重跑；在关键路径上则 `--event-type critical_path` |
| contract-drift-detector | `BREAKING_DRIFT` / `WARN` | `--event-type breaking_drift` |
| self-healing-orchestrator | `DENY` | `--event-type healing_overrun` |
| coverage-analyzer | `GATE_FAILURE` | `--event-type critical_path` |

一个 skill 发出这些 token 之一就停下，并没有创建一次 review——它只是发起了请求。没有 ReviewTask 绑定的自由散文式「路由到人工 review」，是一次无法问责的交接。

## 运行门禁决策

```bash
python scripts/gate.py \
  --confidence <float> \
  --event-type <inference|critical_path|contract_mutation|...> \
  --asset-type <test_case|test_plan|assertion|rule|...> \
  --source-trace "<trace>" \
  --proposed-action "<action>" \
  --artifact-id "<stable-id>" \
  --artifact-version-id "<immutable-version-id>" \
  --content-digest "<sha256>" \
  --policy-type "<SINGLE_REVIEW|FOUR_EYES|...>"
```

## 使用示例

### ✅ 正确用法
当一份正式 TestCase 就绪时，带上它精确的不可变绑定运行门禁。无论置信度多高，它都输出 BLOCK_HUMAN。
```bash
python scripts/gate.py --confidence 0.99 --event-type inference --asset-type test_case \
  --source-trace "test-case-generator:TC-42:req-1" --proposed-action "publish TestCase" \
  --artifact-id "tc-42" --artifact-version-id "tcv-7" \
  --content-digest "<sha256>" --policy-type "SINGLE_REVIEW"
```
*门禁正确输出 BLOCK_HUMAN，因为 TestCase 是正式产物。*

Exit codes: `0` PASS | `2` BLOCK_HUMAN | `3` invalid input (including a formal
artifact missing any of the four binding fields).

## 本 skill 禁止事项

- **绝不把置信度当作授权。** 高分是证据，不是批准。*缺失*的分数同样不是高分——它直接阻断。
- **绝不批准、发布或修改产物。** 本 skill 只决定路由；ReviewDecision 属于被授权的人。
- **绝不让正式产物凭任何置信度通过。** 全部八种正式资产类型一律无条件 `BLOCK_HUMAN`。
- **绝不发出缺少完整绑定的 ReviewTask。** `artifactId`、`artifactVersionId`、`contentDigest` 与 `policyType` 是必填项——未绑定的 review 无法审计。
- **绝不在散文中重新推导这套路由逻辑，也绝不跳过 `scripts/gate.py`。**

### ❌ 错误用法
因为置信度高就跳过门禁或自动批准。
```python
# 不要这样做
if asset.confidence > 0.9:
    return "APPROVED" # 无效：置信度不是人类授权。
```
绝不在散文中重新推导该逻辑，也绝不跳过 `scripts/gate.py`。

门禁输出中引用的策略条款见 `references/policy.md`；完整的触发与 SLA 表见 `references/detailed_rules.md`。
