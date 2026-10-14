---
name: requirement-quality-gate
description: 需求质量评审报告的确定性与路由门禁。在 Test Design Agent 已评审来源并写出报告之后、这些来源被融合为 IR 草稿之前使用。检查全部六个评估维度均已呈现且已路由。不得使用本 skill 评估需求、重读来源或捏造缺失项——它审计的是评审报告，不是需求本身。融合后的 IR 草稿改用 requirement-compiler；已校验的 IR 改用 ir-validator。
---

# Requirement Quality Gate

这是需求质量评审报告的确定性完整性与路由门禁。它不重读需求、不捏造
业务事实、不替代 Test Design Agent 的语义分析。

## 必备评估维度

每份报告显式评估全部六个维度：

| 维度                | 问题                                            |
| ------------------- | ----------------------------------------------- |
| `ambiguity`         | 是否仍存在主观或未定义的表述？                  |
| `consistency`       | 来源、术语、状态与规则之间是否互相矛盾？        |
| `testability`       | 是否定义了可观察的结果或验收边界？              |
| `completeness`      | actor、触发、结果、异常与依赖的缺口是否被记录？ |
| `nfr_measurability` | 范围内的 NFR 是否定义或显式要求了可度量标准？   |
| `role_permission`   | actor、角色层级与权限是否无矛盾？               |

每项评估取值 `CLEAR`、`FINDING` 或 `NOT_APPLICABLE`，并附理由。
`FINDING` 引用绑定证据的 finding ID。

## 判定

- `REJECT`：报告结构不完整、证据缺失，或残留硬缺陷
  （`CROSS_SOURCE_CONFLICT`、`ROLE_PERMISSION_CONFLICT`、
  `UNTESTABLE_ACCEPTANCE_CRITERIA`、`MISSING_REQUIRED_ACTOR`、
  `UNMEASURABLE_NFR`）。
- `PASS_WITH_REVIEW`：仅剩 REVIEW 级 finding，例如需要 owner 澄清的
  歧义表述。
- `PASS`：所有维度均已评估且无剩余 finding。

运行：

```bash
python scripts/gate_check.py --review path/to/requirement_quality_review.json
```

## 本 skill 禁止事项

- 绝不捏造阈值、actor、规则或裁决。
- 绝不为了让流水线继续而把硬 finding 降级为 REVIEW。
- 绝不把被省略的评估维度当作 CLEAR。
- 绝不声称语义完备；本门禁证明的是评审覆盖度与证据完整性，
  而不是「未陈述的业务需求不存在」。

详细 code 与 packet 规则见 `references/gate_rules.md`。

## 使用示例

**正确**：语义分析完成后，触发本 skill 审计 `report.json`。
**错误**：要求本 skill 从零生成初始需求质量评审报告。
