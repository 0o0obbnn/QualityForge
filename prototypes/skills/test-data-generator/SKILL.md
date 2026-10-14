---
name: test-data-generator
description: AI 生成测试数据的合规门禁。只要字段级测试数据已经产出，在它进入任何日志、IR 草稿或贴近生产的系统之前使用。对 SENSITIVE 字段强制 masking_policy、禁止明文密钥、禁止生产目标、要求记录 seed。不得用本 skill 自行生成数据——它只校验合规规则。不得用它规划数据需求（改用 data-requirement-analyzer）。
---

# Test Data Generator (Compliance Gate)

数据层的安全阀。其他 skill 生成字段值；本 skill 决定这些值是否允许离开
生成器。

## 本 skill 为何存在

测试数据是合规事故的诞生地。这套设计加入四条硬规则，在数据扩散之前拦住
问题。本 skill 是这些规则的可执行编码。它不生成值；它强制执行合规契约。

## 四条硬规则

1. **SENSITIVE 字段必须有处于激活状态的 masking_policy**：`pseudonymize`、`tokenize`、`synthesize` 或 `suppress`。
2. **SENSITIVE 值不得以明文出现**：无论在日志还是 IR 表示中。
3. **不得面向生产环境生成**：`target_environment` 不得为 prod。
4. **可复现的 seed**：每次生成运行必须声明一个 `seed`。

详细的策略目录、明文定义、生产环境别名与最严格优先的敏感性判定，见 `references/compliance_rules.md`。

## 集成

- **输入**：生成好的字段值 packet、IR `sensitivity_level` 注解、逐字段的 `masking_policy` 声明。
- **输出**：下游 fixture 执行、治理报告，以及（REJECT 时的）人工审查检查点。
- **硬性顺序**：下游 fixture 执行不得注入尚未通过本门禁的数据。



## 本 skill 禁止事项

- **反模式**：绝不用生产 PII 生成测试数据。绝不在并行运行之间共享测试数据命名空间。

## 使用示例

### ✅ 正确用法

```bash
# Pass output from generation step into compliance_check.py
python scripts/compliance_check.py --packet data.json --ir ir.json
```

packet 应形如：
```json
{
  "run_id": "req-123",
  "seed": 42,
  "target_environment": "staging",
  "fields": [
    {
      "name": "email",
      "value": "test@example.com",
      "masking_policy": "synthesize",
      "masked": true
    }
  ]
}
```

### ❌ 错误用法

- 不得在生成器未显式执行的情况下，自动给 SENSITIVE 字段加掩码让 packet 通过。
- 不得接受"只读测试可以用生产环境"。
- 不得跳过 seed 检查。

## 存疑时

无法判断一个字段是否敏感时，按 SENSITIVE 处理。更多背景见 `references/compliance_rules.md`。
