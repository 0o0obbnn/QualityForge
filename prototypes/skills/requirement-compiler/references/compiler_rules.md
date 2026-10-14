# 编译融合规则

## Finding Codes

| Code | Severity | 含义 |
|---|---|---|
| `CONFLICT_SINGLE_VERSION` | REJECT | 冲突的来源版本数 <2。 |
| `CONFLICT_REF_NOT_AVAILABLE` | REJECT | 冲突证据不是 AVAILABLE 的已声明来源。 |
| `EMPTY_SOURCE_MANIFEST` | REJECT | 未声明任何证据来源。 |
| `EMPTY_IR_DRAFT` | REJECT | 不存在编译产出的需求。 |
| `SOURCE_SILENTLY_DROPPED` | REJECT | 已声明的来源零贡献。 |
| `SOURCE_UNAVAILABLE` | REVIEW | 来源缺失或不可读，置信度降级。 |
| `MISSING_SOURCE_TRACE` | REJECT | 编译元素没有溯源。 |
| `FABRICATED_SOURCE_TRACE` | REJECT | source_trace 的根不在已声明来源中。 |
| `SOURCE_TRACE_UNAVAILABLE` | REJECT | source_trace 指向不可用的证据。 |
| `DEFAULT_CONFIDENCE` | REJECT | 置信度可疑地"整"，且没有理由。 |

## 冲突多版本规则

一个冲突必须保留至少两个根为 AVAILABLE 已声明来源、且互相不一致的版本。单版本的"冲突"是静默裁决——模型选了一边，还把它称作冲突。真正的冲突由人工裁决，而人工需要看到所有立场。

## 默认置信度启发式

取值 {0.5, 0.9, 0.95, 1.0, 0.0} 且没有 `confidence_rationale` 的置信度被标记为可疑默认值。真实的置信度来自证据（匹配强度、来源权威性）；默认值说明抽取器根本没有评估过确定性。

## 来源不完整的降级

证据缺失不等于静默丢弃证据。被标记为 `NOT_PROVIDED`、`UNREADABLE` 或 `EXPECTED_MISSING` 的来源产生 REVIEW，并阻止干净的 PASS。`NOT_APPLICABLE` 不产生 finding。只有 `AVAILABLE` 来源负有贡献义务。
