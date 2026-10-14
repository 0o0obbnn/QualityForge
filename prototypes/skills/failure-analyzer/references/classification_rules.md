# 失败分类规则

`scripts/classify.py` 是可执行编码；本文档是意图说明。

## 信号分类体系

分类器读取一个 `signal`，包含以下字段：

| 字段 | 类型 | 含义 |
|---|---|---|
| `failure_id` | string | 本次失败的标识。 |
| `error_type` | string | 错误类别（见下表）。 |
| `env_healthy` | bool / null | 环境是否已确认健康？`null` = 未检查。 |
| `data_valid` | bool / null | 测试数据是否已确认有效？`null` = 未检查。 |
| `message` | string（可选） | 原始错误信息，供上下文参考。 |

### ENVIRONMENT 错误类型

```
conn_refused, dns_error, healthcheck_fail, oom,
disk_full, infra_timeout, service_unavailable
```

来源：产品代码路径之外的基础设施。

### DATA 错误类型

```
fixture_build_fail, fk_violation, seed_missing,
field_not_in_response, data_type_mismatch
```

来源：测试的输入（fixture、种子数据）。注意 `field_not_in_response`
与 drift 检测有重叠——响应形状变了，但根因是测试自己的数据假设，
不是产品。

### PRODUCT_BUG 错误类型

```
assertion_mismatch, contract_violation, unexpected_exception,
wrong_status_code, wrong_response_body
```

来源：产品代码产生了错误输出。**前置条件：** 该类别要触发，
`env_healthy` 与 `data_valid` 必须都为 `True`。任一为 `null`
（未检查），分类器强制改判 TEST_ASSET_DEFECT——「过早产品 Bug」
防线。

### TEST_ASSET_DEFECT 错误类型

```
stale_locator, tautological_assert, orphan_assertion,
wrong_expected_value, element_not_found
```

来源：测试本身坏了。也是无规则命中时的默认兜底。

## 优先级顺序（承重墙）

规则按以下顺序检查，首个命中即生效：

1. **ENVIRONMENT**——最先检查。基础设施失败永远不是产品 Bug，
   无论断言怎么说。
2. **DATA**——第二检查，排在 product_bug 之前。数据失败伪装成
   产品 Bug 是最常见的误分类。
3. **PRODUCT_BUG**——只有 env 与 data 都确认干净才触发。这就是
   「前置条件」规则：`env_healthy is True AND data_valid is True`。
4. **TEST_ASSET_DEFECT**——显式信号命中，或默认兜底。

该顺序编码了设计禁令："在未分析数据层记录前不得直接
判定'产品 Bug'"。第 2 步（DATA）就是那条分析；第 2 步未清空
数据层之前，第 3 步（PRODUCT_BUG）不得触发。

## 过早产品 Bug 改判

如果信号的 `error_type` 属于 PRODUCT_BUG_ERRORS，但
`env_healthy` 或 `data_valid` 为 `null`（未检查），分类器改判：

```
classification: TEST_ASSET_DEFECT
rule_fired: "Override: PRODUCT_BUG premature (env/data not verified)"
confidence: 0.4
needs_human_review: True
```

这是前置条件的硬执行。没有 env/data 验证的产品 Bug 判定不被
允许，即使 error_type 看起来很像产品问题。改判路由到测试评审，
由人（或更充分的分析轮次）确认 env/data 后重新分类。

## 置信分层

| 区间 | 含义 | 动作 |
|---|---|---|
| ≥ 0.9 | 信号无歧义。 | 按类别自动路由。 |
| 0.7 – 0.9 | 命中但信号偏泛化。 | 路由，但标记抽查。 |
| < 0.7 | 默认兜底或过早改判。 | `needs_human_review = True`；不自动路由。 |

低置信不是静默的。它总是 emit `needs_human_review: True`，
流水线应将其视为路由挂起。

## 统计口径分离（对指标至关重要）

| 类别 | 计入产品缺陷统计？ |
|---|---|
| ENVIRONMENT | 否 |
| DATA | 否 |
| PRODUCT_BUG | **是**——唯一计入的类别 |
| TEST_ASSET_DEFECT | 否 |

正是这个分离让缺陷指标可信。把 TEST_ASSET_DEFECT 混进产品
缺陷计数，是测试抖动虚增表面缺陷率的经典路径，随后侵蚀工程侧
对指标的信任，演变成「别看缺陷看板」文化。

分类器的 `counts_as_product_defect` 字段把该规则做成可执行的：
下游缺陷跟踪应按该字段过滤，而不是按「任何失败都算」。

## 本分类器不做的事

- **定位到代码行级根因。** 它分类失败类别，不精确定位行或函数。
  那需要栈回溯分析，是独立的诊断步骤。
- **修复。** 分类负责路由；修复在下游。
- **重跑决策。** 是否重试抖动测试是独立策略（典型：ENVIRONMENT
  失败重试，其余不重试）。本分类器产出该策略消费的类别。
- **对错误信息做情绪分析。** 它读结构化的 `error_type`，不做
  自由文本解析。自由文本分类是 LLM 任务，在确定性门禁中没有
  位置。
