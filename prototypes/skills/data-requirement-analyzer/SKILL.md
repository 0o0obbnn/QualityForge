---
name: data-requirement-analyzer
description: 校验逐用例的 Data Requirement Contract——数据链（需求、fixture DAG、清理）的第 1 阶段。在已从测试用例草拟出逐用例数据需求之后、fixture-dag-planner 运行之前使用。拒绝与其来源用例或 Testing IR 矛盾的需求。不得推断敏感性——它只能来自 IR。不得制备、生成或脱敏数据（改用 test-data-generator）。
---

# Data Requirement Analyzer

把测试用例桥接到 fixture 规划。对每个用例，它回答：哪些实体必须存在、
处于什么状态、数量多少、哪些字段敏感？

## Data Requirement 包含什么

| 字段                  | 含义                                        | 来源                      |
| --------------------- | ------------------------------------------- | ------------------------- |
| `case_id`             | 该需求所服务的用例。                        | 来自用例。                |
| `fixture_category`    | Static / Dynamic / Hybrid。                 | 从用例回显。              |
| `entities_needed`     | 需要存在的实体实例及目标状态。              | 来自前置条件 + entity_id。|
| `state_preconditions` | 必需的状态（必须在 IR 中可达）。            | 来自用例前置条件。        |
| `volume`              | 实例数量（1、100、边界集）。                | 来自用例输入/边界。       |
| `sensitive_fields`    | entities_needed 中标记 SENSITIVE 的字段。   | 来自 IR——绝不推断。       |
| `construction_steps`  | fixture 规划必须构建什么。                  | 由 entities_needed × volume 推导。 |

## 集成与检查

```bash
python scripts/requirement_check.py --requirements reqs.json --ir ir.json --cases cases.json
```
任何 REJECT 都会把该需求路由回分析器。详细契约检查与状态可达性逻辑见 `references/requirement_rules.md`。

## 使用示例

**正确：**
直接从 IR 定义取敏感性。
```json
{
  "case_id": "case-01",
  "fixture_category": "Dynamic",
  "entities_needed": [{"entity_id": "User", "target_state": "ACTIVE"}],
  "sensitive_fields": ["ssn", "password_hash"]
}
```

**错误：**
IR 未标注时推断敏感性，或漏掉 IR 标记 SENSITIVE 的字段。
```json
{
  "case_id": "case-02",
  "fixture_category": "Static",
  "entities_needed": [{"entity_id": "User", "target_state": "ACTIVE"}],
  "sensitive_fields": [] // REJECT: 'ssn' is marked SENSITIVE in the IR but omitted here
}
```

## 本 skill 禁止事项

- **绝不推断敏感性。** 敏感性来自 IR。在这里推断等于制造第二真相源。
- **绝不生成字段值。** 本 skill 列出需要*哪些*字段，而非它们的值。
- **绝不跳过敏感字段交叉核对。** 该检查对合规至关重要。
