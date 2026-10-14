---
name: assertion-verifier
description: 验证生成的断言确实正确，而不只是存在。对每一批生成的断言、在 api-test-generator 或 ui-automation-generator 运行之前使用。运行三个阶段——静态 IR 检查、dry-run 执行与变异测试门禁——输出 PASS、REPAIR 或 REJECT。生成自动化代码之前不得跳过本步骤。不得用它编写或修复断言。不得把 REPAIR 判定当作 PASS。批次级弱断言分布请改用 assertion-generator。
---

# Assertion Verifier

流水线中每条 AI 生成断言的信任根。其他 skill 负责生成；本 skill 负责裁决
这次生成是否值得信任。

## 三阶段流水线

```
Assertions + Test Cases + Testing IR
 │
 ▼  Stage 1 — STATIC CHECK（确定性、廉价、总是运行）
    断言对照 IR 契约：字段、类型、范围、状态机、
    rule_id/req_id 绑定（强制——不允许孤儿断言）
 │  REJECT → 携带具体违规路由回 assertion-generator
 ▼  Stage 2 — DRY-RUN EXECUTION（需要 Fixture 快照或契约桩）
    回放或符号推断这条断言是否可能失败。
    不可用时：标记 SKIPPED，抬高 stage-3 门槛（见 references/pipeline.md）
 │  REPAIR → 断言可挽救但未获确认
 ▼  Stage 3 — MUTATION GATE（承重、昂贵）
    注入合成故障 → 计算 killed/total 变异数
    分数 ≥ 风险等级阈值则 PASS；低于则 REJECT
```

变异分数是唯一度量真实找 bug 能力的指标。
裸的行覆盖率不可作为替代。

## 判定路由

| Verdict | 路由至 |
|---|---|
| `PASS` | 下游覆盖核算 + 自动化生成器 |
| `REPAIR` | 断言生成步骤（生产方），附修复规格；重新生成的批次重新进入 assertion-generator 的批次门禁 |
| `REJECT` | 上游用例生成步骤；分子计零但**仍留在覆盖分母中** |

关键路径断言（认证/支付/权限）：REJECT 是**强制人工审查检查点**，
不是普通门禁。

## 使用示例

**示例 1 —— 正确触发**
```
assertion-generator 为 TC-001 到 TC-006 产出了 12 条断言。
在 api-test-generator 生成 pytest 脚本之前先跑 assertion-verifier。
```
→ Stage 1 把每条断言对照 IR 检查；Stage 3 为变异击杀打分。

**示例 2 —— 错误触发（不得使用本 skill）**
```
这些断言看起来不对。把它们修好。
```
→ 本 skill 只裁判，不修复。把 REPAIR 判定发给断言生成步骤。

## 运行确定性检查器

两个子命令：

```bash
python scripts/verify.py static-check --assertions path/to/assertions.json --ir path/to/testing_ir.json [--out report.json]
python scripts/verify.py mutation-score --killed <int> --total <int> --risk-class <class> [--stage2-status ran|skipped]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input. `--stage2-status skipped`
会抬高 stage-3 门槛，而不是豁免它。

## 本 skill 禁止事项

- **绝不自动修复断言。** REPAIR → 断言生成步骤；裁判 ≠ 修复者。
- **绝不让被 REJECT 的断言退出覆盖分母。** 分子计零，分母照全。
- **绝不对高风险断言跳过 stage 3。** 昂贵是设计使然。
- **绝不把裸行覆盖率报告为有效覆盖率。**
- **绝不对生产环境运行变异器。** 只允许隔离的 Fixture 环境。

变异器目录、阈值表、降级规则与成本预算：
读 `references/pipeline.md`。
