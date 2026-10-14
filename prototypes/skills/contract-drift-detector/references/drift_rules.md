# Drift 分类规则

`scripts/drift_detect.py` 是可执行编码；本文档是意图说明。

## 接口契约 drift

比较 `response_schema` / `request_schema` 的字段集合与类型。

| 观察到的变化 | 分类 | Code | 原因 |
|---|---|---|---|
| 出现新字段 | COMPATIBLE | `FIELD_ADDED` | 加法变更；既有消费方忽略未知字段。 |
| 字段消失 | BREAKING | `FIELD_REMOVED` | 依赖它的消费方会坏。 |
| 类型变宽（int→str、int→float、VARCHAR→TEXT、INTEGER→BIGINT） | COMPATIBLE | `TYPE_WIDENED` | 旧取值仍合法；传入更窄取值的消费方不受影响。 |
| 类型变窄（str→int、float→int、TEXT→VARCHAR） | BREAKING | `TYPE_NARROWED` | 传入更宽类型的消费方现在会失败。 |
| 类型跨类变化（str→bool、int→array） | BREAKING | `TYPE_CHANGED` | 有歧义；默认取更安全的一档。 |

字段重命名会呈现为 `FIELD_REMOVED`（旧名）+ `FIELD_ADDED`
（新名）——两条 finding，其中被移除的那条是 BREAKING。这是正确的：
对每个引用旧名的消费方来说，重命名就是破坏性变更，即使新名
「等价」。

### 变宽矩阵

类型变化检查使用一个小而显式的矩阵，而不是完整的 JSON Schema
兼容性校验器：

```
WIDENING = {
 ("int", "str"): True,
 ("int", "float"): True,
 ("bool", "str"): True,
 ("VARCHAR", "TEXT"): True,
 ("INTEGER", "BIGINT"): True,
}
```

`(old, new)` 在矩阵中 → COMPATIBLE。反向 `(new, old)` 在矩阵中
→ BREAKING（变窄）。其余一律 BREAKING（歧义默认取更安全侧）。

这是刻意粗糙的。真实部署应换成正经的 JSON Schema 兼容性检查
（`jsonschema` 库，或 Pact 的 diff 引擎）。该矩阵只覆盖 IR 常见
产出；未知组合默认 BREAKING，避免任何变化以「大概没事」溜过去。

## 状态机 drift

| 观察到的变化 | 分类 | Code |
|---|---|---|
| 出现新状态 | COMPATIBLE | `STATE_ADDED` |
| 状态消失 | BREAKING | `STATE_REMOVED` |
| 出现新迁移 | COMPATIBLE | `TRANSITION_ADDED` |
| 迁移消失 | BREAKING | `TRANSITION_REMOVED` |

新增状态在*结构上*永远兼容——即使新状态不可达，它也不会破坏
既有用例（没有任何用例断言过一个不存在的状态）。IR 校验步骤的
可达性检查作用于发布时的 IR；这里观察的是运行中的系统，一个
不可达的新状态只是异常现象，不是契约破坏。

迁移消失是最容易造成静默 false-pass 的破坏性 drift：走过
`PAID→SHIPPED` 的用例现在发现迁移没了，要么报错（可见），要么
被跳过（静默）。无论哪种，契约都已破坏；检测器负责标记它。

## 为什么歧义默认 BREAKING

检测器无法证明一个歧义变更是安全的。两个选项：

- 判为 COMPATIBLE：判错时，测试跑在破坏的契约上，产出假通过
  或莫名其妙的失败。代价：一次带病回归上线。
- 判为 BREAKING：判错时，人工看一眼后驳回。代价：几分钟评审。

不对称性极其悬殊。歧义默认 BREAKING，与人工审核的「存疑即拦」、
断言验证步骤的「存疑即 REJECT」是同一哲学：系统宁可暴露不确定，
也不把它藏起来。

## 本检测器不做的事

- **不更新 IR。** 检测器只报告 drift；IR 只能经 IR 编译步骤 →
  05 发布链路更新，且须先过人工审核。用观察结果自动改写 IR 是
  设计明令禁止的反模式。
- **不做语义等价检查。** 字段 `total` 改名 `amount` 且类型相同，
  报告为 REMOVE+ADD，而不是「重命名」。判断两者语义相同需要
  人类判断（或 LLM——而 LLM 在确定性门禁里没有位置）。
- **不做频次追踪。** 观察到一次的 drift 可能是瞬时现象；每个
  周期都观察到才是结构性的。频次追踪是 Skill 30（治理）的
  职责——检测器逐次报告每条观察，由下游治理报表做关联。
