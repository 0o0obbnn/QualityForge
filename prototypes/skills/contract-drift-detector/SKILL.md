---
name: contract-drift-detector
description: 检测真实系统偏离已发布 Testing IR 契约的时刻。每个观测周期——CI 运行、定时探活、部署后检查——只要能拿到可与 IR 对照的真实 API、DB 或 UI 快照，就应使用。把每处 drift 归类为 COMPATIBLE（警告，流水线继续）或 BREAKING（阻断并强制人工 review）。不得用本 skill 更新或修复 IR。不得只在流水线启动时运行——drift 是持续的。不得把模糊的 drift 归为 compatible；不确定时默认 BREAKING。
---

# Contract Drift Detector

IR 契约的运行时守望者。IR 校验步骤在发布时校验 IR；本 skill 校验的是数小时或数周之后，*真实系统*是否仍与 IR 一致。

## 本 skill 为何存在

契约会腐烂。IR 发布时是对的，但系统在演进：API 加了字段、DB 列被改名、某个状态被移除。每一处这样的变化都是 drift，而未处理的 drift 是两类静默测试失败的根因：

1. **过期契约导致的假通过。** IR 说 `/orders` 响应有 `total` 字段；真实 API 把它改名为 `amount`。断言 `total` 的测试如今对着仍提供旧结构的 mock 通过，或对着真实 API 莫名失败。无论哪种，测试度量的都是虚构。
2. **伪装成演进的破坏性变更。** 响应里删了一个字段。没有对它断言的测试毫无察觉。契约已破坏而测试套件全绿。回归就是这样上线的。

探测器的职责是在 drift 被观测到的那一刻把它浮出水面、归类（compatible 对 breaking）、并相应路由。它不修复 IR——设计规则写得很明确：禁止自动更新 IR，因为 drift 修复必须经过人类检查点。修契约是经人工 review 路由的人类决策。

## 格式错误的快照绝不算 NO_DRIFT

第三种失败模式，也是最隐蔽的一种：**不可用的快照不得被解读为「未检测到 drift」。** 缺失、非对象或形状错误的快照意味着 drift 无法判定——在那里报告 `NO_DRIFT`，恰好会制造出本 skill 要防止的那种假通过。

- `--contract` 或 `--observed` 非对象是输入错误（exit 3），不是 verdict。
- `states` 的值不是字符串数组，或 `transitions` 条目不是对象，会以 `BREAKING` 严重级别发出 `MALFORMED_SNAPSHOT`。
- 未知的 `type` 是输入错误，不是干净通过。

## 运行确定性检查器

```bash
python scripts/drift_detect.py --contract path/to/ir_contract.json --observed path/to/observed.json [--out report.json]
```

Exit codes: `0` NO_DRIFT | `1` COMPATIBLE_DRIFT | `2` BREAKING_DRIFT | `3` invalid input.

## 两级分类

每处被观测到的 drift 恰好落入其中一级。没有「也许」——模糊的 drift 默认 BREAKING（更安全的那一级）。

```
Observed system vs IR contract
 │
 ▼
 ┌─ field added? ─────────────────────────┐
 │ optional & additive → COMPATIBLE │
 │ required or replaces existing → BREAKING│
 ├─ field removed? ────────────────────────┤
 │ always → BREAKING │
 ├─ field renamed? ────────────────────────┤
 │ always → BREAKING (removal + addition) │
 ├─ field type changed? ───────────────────┤
 │ widening (int→str, narrow→wide) → COMPATIBLE
 │ narrowing or cross-kind → BREAKING │
 ├─ state added? ──────────────────────────┤
 │ reachable from existing → COMPATIBLE │
 │ unreachable / orphan → COMPATIBLE warn │
 ├─ state removed? ────────────────────────┤
 │ always → BREAKING │
 ├─ transition added? ─────────────────────┤
 │ always → COMPATIBLE │
 ├─ transition removed? ───────────────────┤
 │ always → BREAKING │
 └─────────────────────────────────────────┘
 │
 ▼
 COMPATIBLE → WARN (raises a governance alert downstream)
 BREAKING → BLOCK (suspend cases, force human review human checkpoint)
```

分类背后的原则：**现有消费方可以忽略的增量变更是 compatible；会破坏现有消费方的删减或替换变更是 breaking。** 这与 Pact/PactFlow 契约测试社区收敛出的前向兼容规则一致（已获行业研究确认）。

## COMPATIBLE drift（警告）

示例：
- API 响应多出一个 IR 中没有的可选字段 `coupon_code`。
- 出现新状态 `PARTIAL_REFUND`，可从 `PAID` 到达。
- 新增迁移 `PAID→PARTIAL_REFUND`。
- 字段类型从 `int` 拓宽为 `str|`int`（API 现在两者都接受）。

处理：WARN。drift 被记录、浮出到下游治理报表的治理仪表盘，并以 `sample` 严重级别创建一条 human review 条目（非强制——compatible drift 不阻断）。IR 不会被自动更新；人类之后可以通过经 review 的修订把新增折入 IR。

## BREAKING drift（阻断）

示例：
- API 响应丢弃 `total` 字段。
- `total` 被改名为 `amount`。
- `total` 类型从 `str` 收窄为 `int`（传字符串的消费方会挂）。
- 状态机中移除状态 `SHIPPED`。
- 删除迁移 `PAID→SHIPPED`。

处理：BLOCK。所有绑定到受影响 IR 元素的测试用例都被挂起（对着已破坏的契约，它们无法有效运行）。创建一个强制的 human review 检查点——人类要么把系统修回与 IR 一致，要么通过正式发布路径修订 IR（上游 IR 编译步骤返工 + IR 校验步骤重新校验）。解决之前，流水线保持挂起。

## 「新需求」反模式（设计禁令）

本节编码的设计规则是一条禁令：drift 绝不能被悄悄重新标注为「新需求」。观测到 drift 时，探测器不得默默把它当作一条要折入 IR 的新需求。这个区别很关键：

- **新需求**来自人类决策（PRD 更新、上游 IR 编译步骤重新编译）。它有出处和 review 轨迹。
- **Drift** 是系统偏离契约的观测结果。它*可以*在人工 review 之后成为需求，但抢先称其为需求就绕过了 review，并把偏离固化进 IR。

探测器把 drift 报告为 drift。把它提升为需求是经 human review 路由的人类动作，不是自动重贴标签。

## 契约检查（承重部分）

```bash
python scripts/drift_detect.py --contract path/to/ir_contract.json --observed path/to/observed.json
```

检查器把 `observed` 快照（真实 API 响应结构、DB 列、在线状态）与 IR `contract`（单个 interface_contract 或 state_machine）对照，归类每一处差异，并输出逐 drift 的 findings + 总体 verdict。

| Verdict | 何时 |
|---|---|
| `NO_DRIFT` | 观测与契约完全一致。 |
| `COMPATIBLE_DRIFT` | 只有 compatible findings。流水线继续；下游治理报表收到警告。 |
| `BREAKING_DRIFT` | 存在任一 breaking finding。流水线阻断；强制 human review。 |

## 本 skill 禁止事项

- **绝不自动更新 IR。** 这是明令的设计禁令。IR 是契约；用观测去更新它等于让系统自己定义自己的规格，规格的存在意义就此归零。
- **绝不把 breaking drift 悄悄归为 compatible。** 模糊 = breaking。一次误 BLOCK 的代价是一场人工 review；一次漏掉 BLOCK 的代价是测试对着虚构运行。
- **绝不把 drift 重贴标签为新需求。** 见上文反模式。
- **绝不止运行一次。** drift 是持续的。本 skill 在每个观测周期（CI 运行、定时探活、部署后检查）被调用，而不只是在流水线启动时。

关于逐字段类型的拓宽/收窄规则与状态机 drift 的边界情况，见 `references/drift_rules.md`。

## 使用示例

**示例 1 —— 正确触发（BREAKING drift）**
```
/api/v1/orders 的 IR 契约声明响应字段：total (number)。
线上 API 快照显示字段：amount (number)。字段 total 缺失。
运行 drift 检查。
```
→ 字段被移除（total）= BREAKING；新增字段替换既有字段 = BREAKING。流水线 BLOCK；强制 human review。IR 不会被自动更新。

**示例 2 —— 正确触发（COMPATIBLE drift）**
```
/api/v1/orders 的 IR 契约声明：[order_id, status, total]。
线上 API 快照新增可选字段：coupon_code（可空、非必填）。
运行 drift 检查。
```
→ 可选的增量字段 = COMPATIBLE。记录 WARN；流水线继续。

**示例 3 —— 错误触发（不要使用本 skill）**
```
API 团队说他们把 total 改名成了 amount。请更新 IR 来匹配。
```
→ 本 skill 检测并归类 drift。更新 IR 是经正式 review 的人类决策，不是自动动作。请改用 IR 编译步骤。
