# 需求质量门规则

## 审核包

```text
review_id
source_ids[]
assessments[]: dimension, status, rationale, finding_ids[]
findings[]: finding_id, code, severity, source_refs[], evidence, question
```

`source_refs` 必须指向已声明的来源根。质量门校验证据绑定与评估维度的完整覆盖；它不判断来源陈述本身是真是假。

## 允许的质量 finding codes

| Code | 最低 severity |
|---|---|
| `CROSS_SOURCE_CONFLICT` | REJECT |
| `ROLE_PERMISSION_CONFLICT` | REJECT |
| `UNTESTABLE_ACCEPTANCE_CRITERIA` | REJECT |
| `MISSING_REQUIRED_ACTOR` | REJECT |
| `UNMEASURABLE_NFR` | REJECT |
| `AMBIGUOUS_LANGUAGE` | REVIEW |
| `INCOMPLETE_REQUIREMENT` | REVIEW |
| `MISSING_EXCEPTION_BEHAVIOR` | REVIEW |

最低值是失败安全的。REVIEW 级 code 可以被审核者升级为 REJECT，但硬性 code 不得降级。

## 质量门结构 codes

缺失维度、格式错误的 assessment、缺失证据、重复 ID、未知 code、未声明的来源引用以及未绑定的 finding，一律 REJECT。
