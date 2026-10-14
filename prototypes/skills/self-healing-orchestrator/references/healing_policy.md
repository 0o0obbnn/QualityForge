# Self-Healing 策略参考

`scripts/healing_gate.py` 是可执行编码；本文件描述其意图。

## 策略常量

| 常量 | 值 | 含义 |
|---|---|---|
| `HEAL_WINDOW_DAYS` | 7 | healing 上限的滚动窗口。 |
| `HEAL_CAP` | 3 | 窗口内每个资产最多允许的 heal 次数。 |

这些是 healing orchestrator 的默认值。调整它们是基于观测到的 healing 模式做出的下游治理决策（governance reporting），绝不按单次请求覆盖。"只想在超限后再多 heal 一次"的请求，恰恰是上限要拦的失败模式。

## 关键路径分类

与人工审核的分类一致。即使声明了 `path_category=normal`，以下关键词仍会把资产标记为 critical（对错误分类的纵深防御）：

```
login, auth, authenticate, token, session,
payment, pay, charge, refund, payout, ledger,
permission, acl, role, privilege, grant, revoke
```

若 `path_category` 不是 `normal`（包括 `critical`、`ambiguous` 或缺失），资产按 critical 处理。关键词扫描是兜底，针对 critical 资产被错归为 `normal` 的情况——例如 "password-reset" 流程被标成 normal，因为开发者没把它当作 auth。

### 为什么需要关键词兜底

Self-healing 最坏的结局是在资金或权限路径上掩盖真实 bug。关键词扫描宁可把资产误判为 critical：一个名为 `login-button-locator` 的资产即使被归入 `normal`，仍会因 id 中出现 "login" 而被否决。代价是多一次多余的人工审核；收益是错误分类无法静默放行一次 critical heal。

## 护栏评估顺序

三条护栏按固定顺序评估，顺序有讲究：

1. **关键路径** — 最先检查。关键路径失败在查看 heal 类型或历史之前就被拒绝。这是刻意的：关键路径失败永远交给人，不论它碰巧涉及断言，也不论之前 heal 过多少次。
2. **断言保护** — 其次检查。触碰断言的 heal 不论历史如何一律拒绝。这是绝对的，不按次数门控。
3. **Healing 上限** — 最后检查。只有非 critical、不触碰断言、且历史干净（或未超限）的 heal 才被 ALLOW。

这个顺序意味着：一个触碰断言的关键路径 heal 又恰好超限，只会产生一条 `CRITICAL_PATH` 否决，而不是三条。这是正确的——第一条否决已经足够，且向人给出的理由是最根本的那条。

## 什么算"触碰期望值"

`touches_expected=True` 表示该 heal 会修改断言的 `expected` 字段（被测系统应当产出的值）。它与以下情形不同：

- 修复断言读取所经的 **locator** — 断言的 `expected` 不变，变的是取值路径。ALLOW（护栏允许的前提下）。
- 修复供测试 setup 的 **fixture** — 同理，断言的 `expected` 未被触碰。ALLOW。
- 因系统行为变化而更新 **断言的 expected** — DENY。这是规格变更，规格变更归人。

`heal_type=assertion` 捷径同样触发本护栏，因为 assertion 类型的 heal 定义上就在触碰断言语义。

## 审计记录（ALLOW 时）

每次被允许的 heal MUST 产生审计记录，包含：

| 字段 | 用途 |
|---|---|
| `event_id` | Traceability Graph 边的稳定 id。 |
| `before` / `after` | 被 heal 资产的快照（locator 字符串、fixture 内容等）。 |
| `reason` | heal 为何运行（来自上游失败分析的失败分类）。 |
| `heals_7d_after` | heal 之后的新计数——让下一个请求看到准确的历史。 |

没有审计记录的 heal 在上限计算上视同从未发生——即不计入下一次请求的 `heals_7d`。这是刻意的：未审计的 heal 是看不见的债，如果 heal 可以不记账，上限就毫无意义。强制写入审计是下游 fixture 规划/下游知识留存（graph 层）的职责，不是本 gate 的；gate 只在 ALLOW 时设置 `audit_required: True`。

## 已知天花板（ponytail）

本 gate 是确定性的护栏评估器。以下事情它 NOT 做：

- 决定*如何* heal（locator 重算、fixture 刷新）。那是执行逻辑，在 heal executor 里。
- 判断被允许的 heal 是否修向了*正确*的目标。那是人工审核抽样复查的兜底——gate 分不出一次正确的 locator 重算和一次找到了错误按钮的重算。
- 自行维护 7 天计数。计数是来自审计日志（下游知识留存）的输入。日志不全则计数就错；gate 信任其输入。

"判断 heal 是否修对了"的升级路径是 heal 后验证（重跑测试、确认它现在触达预期元素）。那是未来工作；今天的 gate 是护栏，不是验证器。
