---
name: failure-analyzer
description: 把一次测试失败归类为四种根因之一——ENVIRONMENT、DATA、PRODUCT_BUG 或 TEST_ASSET_DEFECT——并附置信度。任何测试失败时都作为第一步使用，先于「是否修复、是否报缺陷、是否排查环境」的决策。未先检查环境与数据健康度，不得猜测分类。不得用本 skill 决定是否允许自动修复——那是 self-healing-orchestrator 的职责，它消费本分类结果。
---

# Failure Analyzer

测试失败后的第一个问题不是「怎么修」，而是「这是哪一种失败」。本 skill 回答这个问题。

## 本 skill 为何存在

一次测试失败是信号，不是 verdict。同一个红灯测试可能意味着四种完全不同的事：

1. **ENVIRONMENT** —— 基础设施故障。
2. **DATA** —— 测试输入/前置条件有误。
3. **PRODUCT_BUG** —— 产品代码确实坏了。
4. **TEST_ASSET_DEFECT** —— 测试本身有错。

完整的信号分类法、置信度规则与统计口径分离的细节，见 `references/classification_rules.md`。

## 运行确定性分类器

```bash
python scripts/classify.py --signal path/to/signal.json [--out report.json]
```

Exit codes: `0` classified (any class) | `3` invalid input. 这是分类器，不是门禁——成功时总是 exit 0。按输出中的 `classification`、`counts_as_product_defect` 与 `needs_human_review` 行动；只有 `PRODUCT_BUG` 计入缺陷统计。

## 本 skill 禁止事项

- **未检查环境与数据，绝不判为 PRODUCT_BUG。** 这是明令禁止项。环境/数据未验证的失败默认归为 TEST_ASSET_DEFECT，而不是 PRODUCT_BUG。
- **绝不把 TEST_ASSET_DEFECT 计入产品缺陷统计。** 统计口径分离是缺陷指标可信的根基。
- **绝不自动修复。** 分类负责路由，不负责修复。修复是下游的事。
- **绝不输出 `OTHER` 或 `UNKNOWN`。** 模糊 = 低置信度的 TEST_ASSET_DEFECT + review 标记。四个类别是完备的。

## 使用示例

**正确：**
User: 「测试失败，connection refused。」
Agent: 我看到了 connection refused。先检查环境健康度。既然环境已宕机，我把它归类为 ENVIRONMENT。

**错误：**
User: 「测试失败：断言不匹配。」
Agent: 我把它归类为 PRODUCT_BUG 并上报缺陷。
（为什么错误？Agent 在判定 PRODUCT_BUG 之前没有检查 `env_healthy` 与 `data_valid`。）
