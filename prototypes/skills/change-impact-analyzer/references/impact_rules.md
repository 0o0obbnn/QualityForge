# 变更影响分析规则

## Finding codes

| Code | Severity | 含义 |
|---|---|---|
| `SHALLOW_PROPAGATION` | REJECT | 分析深度 < 2 跳。 |
| `UNCLASSIFIED_IMPACT` | REJECT | 资产未标注 direct/indirect。 |
| `SILENT_STATIC_FALLBACK` | REJECT | 使用了静态回退却未标注降级。 |

## 2 跳下限

1 跳只看到被改代码的直接调用方。2 跳能抓住常见链路：
test case -> rule -> changed requirement。没有第二跳，经由
traceability graph 的间接影响完全不可见。

风险加权可以超过 2 跳（高风险变更走到 3-4 跳），但 2 是下限。

## 降级置信度

图为空或部分缺失时，分析回退到静态代码分析。如果报告标注了
`degraded_confidence`，这是可接受的。静默回退会产出一份看起来
权威、却缺了间接影响的报告——最糟的假自信。
