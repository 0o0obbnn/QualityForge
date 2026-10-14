---
name: domain-model-extractor
description: 在 Testing IR 融合前校验已抽取的领域实体。在 LLM 或解析器产出实体草稿 packet 之后、对该 packet 使用。拒绝畸形 packet、空模型、重复或畸形的 ID 与字段、无类型字段、悬空实体引用。不得使用本 skill 从 PRD 抽取实体——它是只做裁决的结构门禁。不得捏造缺失实体或静默丢弃畸形记录。实体生命周期改用 state-machine-builder。
---

# Domain Model Extractor

这是针对已抽取实体的只做裁决的结构门禁。它不推断实体，也不修复
被 REJECT 的 packet。

## 契约

- 输入：`{ "entities": [...] }`。
- 每个实体有唯一的 `ENT-{UPPERCASE}-{NNN}` ID、非空名称和至少一个
  字段。
- 每个字段是一个对象，带唯一非空名称和已知字符串类型。
- 字段可用 `references` 或 `fk_reference`，绝不同时用；出现时，
  值必须是同一 packet 中存在的非空实体 ID。
- 输出：`PASS` 或 `REJECT`，附确定性 findings。

运行：

```bash
python scripts/entity_check.py --packet path/to/entities.json
```

承重检查是 `DUPLICATE_ENTITY_ID`、`DUPLICATE_FIELD_NAME`、
`UNTYPED_FIELD` 和 `DANGLING_ENTITY_REF`。畸形容器/条目形状同样是
REJECT，而非运行时错误。

## 禁止

- 不得捏造缺失的实体、字段、类型或引用。
- 不得静默丢弃畸形记录。
- 不得把空实体集当作成功。



## 本 skill 禁止事项

- **反模式**：绝不捏造来源文本中不存在的实体。绝不无别名规则地合并不同概念。

## 使用示例

**正确用法：**
校验一份实体 JSON packet，当 `ENT-USER-001` 存在重复字段 `email` 时拒绝它。

**错误用法：**
自动补齐缺失的字段类型（例如给无类型字段加 `string`）来让校验通过。

全部 finding code 见 `references/entity_extraction_rules.md`。
