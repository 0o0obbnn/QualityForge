---
name: assertion-generator
description: 生成断言的批次级质量门禁。在一批断言已产出之后、逐条验证运行之前使用一次。拒绝被弱断言主导的批次——这是逐条检查在结构上看不见的分布问题。不得用它评估语义层面的弱（那需要运行时执行）。不得用它编写或自动加强断言——它只审计上游生成步骤。小批次不得跳过本检查。逐条正确性请改用 assertion-verifier。
---

# Assertion Generator (Batch Quality Gate)

尽管名字如此，本 skill **审计**一批断言；它不编写断言。断言由上游的断言
生成步骤（LLM 或模板过程）产出；本 skill 是这批断言必须通过的门禁。

逐条验证检查每条断言的契约一致性。本 skill 检查的是批次的质量*分布*——
那是逐条检查在结构上看不见的东西。

## 本 skill 为何存在

1. **逐条问题（由验证捕获）**：某一条断言引用了不存在的字段。
2. **批次级问题（由本 skill 捕获）**：40 条断言里有 30 条在检查
   `status_code == 200`。批次覆盖率数字漂亮，找 bug 的能力却接近于零。

本门禁在验证环节把预算花向已知偏弱的批次之前，先拦下第二层问题。

## 修复回路

`assertion-verifier` 的 `REPAIR` 判定会路由回**断言生成步骤**（生产方），
而不是本 skill。重新生成的批次会再次进入这里做全新的批次质量检查，然后
才重新运行验证。本 skill 只裁判；从不修复。

## 集成

- **输入**：一批生成好的断言 + `weak_assertion_threshold`（默认 0.3）。
- **输出**：PASS 或 REJECT（附弱断言 ID 列表）。

弱断言分类、结构有效性与批次比例检查的详细规则，读 `references/generation_rules.md`
与 `references/assertion_batch_rules.md`。



## 运行确定性检查器

```bash
python scripts/batch_check.py --batch path/to/assertions.json [--threshold 0.3] [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input. `--threshold` 是可容忍的
最大弱断言比例（默认 0.3）。

## 本 skill 禁止事项

- **反模式**：绝不生成重言式断言（如 assert true == true）。绝不对动态时间戳做无掩码断言。

## 使用示例

### 正确用法
```json
// 输入：10 条断言。2 条是仅查 status 的检查，8 条是具体字段检查。
// 阈值：0.3
// 弱断言比例：0.2
// 输出：PASS
```

### 错误用法
```json
// 输入：3 条断言。全部 3 条都是 "response is not None"。
// 阈值：0.3
// 行为：skill 自动改写断言去检查具体字段。
// 为什么错：skill 不得自动加强断言。它应当 REJECT 该批次并返回弱断言 ID 列表。
```
