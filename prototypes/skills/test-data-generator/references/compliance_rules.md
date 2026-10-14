# 测试数据合规规则

`scripts/compliance_check.py` 是可执行编码；本文件描述其意图。两者不一致时，脚本决定行为，本文描述意图。

## masking_policy 目录（Rule 1）

SENSITIVE 字段的 `masking_policy` 只接受以下四个值：

| Policy | 作用 | 适用时机 |
|---|---|---|
| `pseudonymize` | 替换为可逆的假值（确定性假名、假但稳定的电话）。 | 测试需要字段看起来真实 AND 跨运行可关联时。 |
| `tokenize` | 替换为不透明 token；真值放在 vault，绝不进数据包。 | 测试只需要稳定标识符、不需要真实值时。实际可用的最强保护。 |
| `synthesize` | 生成与任何真实记录无关的全新合成值。 | 纯新场景（hybrid 策略的 "synthetic" 分支）。 |
| `suppress` | 不产出值（null / 省略字段）。 | 该字段本测试完全用不到时。最安全的策略。 |

`masking_policy: null` 的 SENSITIVE 字段是 `SENSITIVE_NO_POLICY` REJECT。生成器必须说明它如何保护了该字段——"敏感但没策略"正是本规则要抓的失败模式。

### 什么 NOT 算合法策略

- `encrypt`：拒绝。加密是传输/存储控制，不是脱敏策略——密钥可达时，能解密回真实 PII 的密文仍是 PII。改用 `tokenize`（vault 保管）。
- `hash`：除非加盐并截断到 token 程度，否则拒绝。裸 hash 可被再识别。改用 `tokenize`。
- `none` / `""`：显然拒绝。

## 明文规则（Rule 2）

SENSITIVE 值算"明文"的条件：

- `value` 字段存在（非 null），AND
- `masked` 标志为 False。

明文触发硬 REJECT 的两种场景：

| 场景 | 标志 | 为什么重要 |
|---|---|---|
| 被记录的字段 | `logged: true` | 值将出现在日志行里。日志是意外暴露 PII 的头号途径——被送往聚合系统、保留数周、运维团队可读。 |
| IR 绑定字段 | `ir_bound: true` | 值将被写入 Testing IR 的数据表示。IR 是共享语义契约；PII 进了 IR 就会传播到每个下游 skill。 |

`logged: true` 但 `masked: true` 的 SENSITIVE 字段没问题——被记录的是掩码。检查针对的是组合，不是只看字段名。

### "被 suppress 却被记录"的例外

`masking_policy: suppress` 的字段 `value: null`。Rule 2 的 `value is not None` 守卫意味着被 suppress 的字段即使 `logged: true` 也通过——因为没有什么可泄露。这是正确的：可以记录"字段 X 被抑制"，而不记录 X 的值。

## 生产目标规则（Rule 3）

`target_environment` 字段不得匹配任何生产别名：

```
production, prod, prd, live, production-readonly, prod-readonly
```

列入 `*-readonly` 别名是刻意的。"只读生产"是常见的自我开脱（"我们只是读，无害"）——但跑在生产上的测试依然会触发生产代码路径、生产限流和生产可观测性。本规则没有豁免口。

如果测试确实需要生产级真实数据，答案是**掩码投影**（在测试看到之前已完成脱敏的视图或导出），而不是把生成指向生产。这类配置的 `target_environment` 是投影的环境（如 `staging-masked-view`），不是 `production`。

## 种子规则（Rule 4）

每个数据包 MUST 携带 `seed`。该 seed：

- 是生成器驱动其 RNG 的任意 JSON 可序列化值（int、string）。
- MUST 随消费该数据包的测试一起进版本控制。没提交的 seed 下次运行就会丢，破坏可复现性。

缺失 seed 是 `MISSING_SEED` REJECT——不是 REVIEW。该设计把可复现性当作硬约束：不可复现的运行不可审计；一条"我们生成了些数据"却无法重新生成的审计线索不是审计线索。

## 最严者胜的敏感度解析

`_sensitivity_map` 辅助函数跨所有 IR 实体构建 `field_name → level` 映射。当两个实体用不同级别声明同一字段名时，**最严者**胜出（SENSITIVE > INTERNAL > PUBLIC）。理由：只要任何实体把 `phone` 视为 SENSITIVE，数据生成器就必须把每个 `phone` 都当作 SENSITIVE——少掩一次就是事故，而生成器无法知道某个值会绑定到哪个实体。

这是保守启发式。真实系统可能按实体路径界定敏感度；本检查器为简单与安全起见按字段名界定。升级路径就在 `references/compliance_rules.md`（本节）：若 IR 引入实体限定的字段路径，映射键将变为 `entity_id.field_name`。

## 本检查器 NOT 验证什么

- **masking_policy 选得对不对。** 在 `pseudonymize` 与 `tokenize` 之间选择，是基于测试是否需要仿真值的数据工程判断。检查器只验证声明并应用了合法策略。
- **合成数据对测试是否"好"。** 边界值覆盖是数据生成步骤的采样逻辑；本检查器不评估它。
- **seed 是否进了版本控制。** 那是仓库层面的事。检查器验证数据包里存在 seed；强制提交是 CI/治理（下游 governance reporting）的职责。
- **跨系统引用完整性。** hybrid 策略对此讨论的是掩码真实数据 vs 合成数据；它是生成指导，不是合规门检查。
