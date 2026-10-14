# 实体抽取规则

`scripts/entity_check.py` 是可执行行为的权威。

| Code | 含义 |
|---|---|
| `INVALID_ENTITY_PACKET` | 根节点不是对象。 |
| `INVALID_ENTITY_COLLECTION` | `entities` 不是数组。 |
| `INVALID_ENTITY` | 实体项不是对象。 |
| `EMPTY_ENTITY_SET` | 未提供任何实体。 |
| `MISSING_ENTITY_ID` / `MALFORMED_ENTITY_ID` | ID 缺失，或不符合 `ENT-{UPPERCASE}-{NNN}`。 |
| `DUPLICATE_ENTITY_ID` | 实体 ID 重复。 |
| `MISSING_ENTITY_NAME` | Name 缺失或为空。 |
| `INVALID_FIELD_COLLECTION` / `INVALID_ENTITY_FIELD` | 字段容器或字段项形状不对。 |
| `EMPTY_ENTITY_FIELDS` | 实体没有任何字段。 |
| `MISSING_FIELD_NAME` / `DUPLICATE_FIELD_NAME` | 字段名缺失，或在同一实体内重复。 |
| `UNTYPED_FIELD` | Type 缺失、为空、非字符串或为 `unknown`。 |
| `INVALID_ENTITY_REF` | 引用存在但不是非空字符串。 |
| `AMBIGUOUS_ENTITY_REF` | 字段同时给出 `references` 与 `fk_reference`；别名不许竞争。 |
| `DANGLING_ENTITY_REF` | 引用指向未声明的实体。 |

所有 finding 一律 REJECT。ID 中段使用大写字母，序号为至少三位、
零填充的数字。
