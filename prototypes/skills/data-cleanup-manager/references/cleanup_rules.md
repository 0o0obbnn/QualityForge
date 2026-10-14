# 清理规则参考

`scripts/cleanup_check.py` 是可执行编码；本文档是意图说明。

## Finding codes

| 检查 | Code | Severity | 含义 |
|---|---|---|---|
| 1 | `WRONG_CLEANUP_ORDER` | REJECT | 清理顺序不是构建顺序的逆序。 |
| 2 | `STATIC_BASELINE_IN_CLEANUP` | REJECT | 清理清单里出现 Static baseline。 |
| 3 | `MISSING_CLEANUP_STATUS` | REJECT | 清理步骤没有 status。 |
| 3 | `SILENCED_FAILURE` | REJECT | failed/skipped 的步骤没有 reason。 |
| 4 | `RESIDUALS_NOT_CHECKED` | REJECT | 完全没有 residuals 字段。 |
| 4 | `UNTRACKED_RESIDUAL` | REJECT | 残留项没有 reason。 |

## LIFO 规则（检查 1）

构建：A → B → C（A 最先，C 最后）。
清理必须是：C → B → A（C 最先，A 最后）。

原因：B 依赖 A。如果 A 先被移除而 B 还引用它，数据库会抛外键
违例（或引用悬空）。逆序移除保证依赖方先于其依赖被移除。

检查将清理清单与 `reversed(construction_order)` 对比。任何位置
偏差都是 REJECT，并附上精确位置与期望取值。

## Static baseline 规则（检查 2）

Static baseline 声明在 `static_baselines[]` 中。它们是跨 session
持久存在的共享 fixture——不属于任何单个 phase，也不允许被某个
phase 拆除。

某个 phase 的清理清单里出现 Static id 一律 REJECT，无论给出什么
理由。baseline 的生命周期在 session 层管理，不在 phase 层。

## 失败报告（检查 3）

`results[]` 里的每个清理步骤必须有：
- `status`：`success` / `failed` / `skipped` 三者之一。
- 若为 `failed` 或 `skipped`：一个 `reason` 字段。

缺 status 意味着该步骤结果未知——可能成功、失败或根本没跑。
结果未知按失败处理（清理的安全默认值）。

failed/skipped 却不带 reason 是被消音的失败——有人决定不解释
为什么没清理干净。脏状态就是这样扩散的。

## 残留报告（检查 4）

清理之后，报告必须包含 `residuals` 清单：
- 空清单 `[]`：显式确认无残留。
- 缺失（null）：「没检查」——REJECT。
- 非空：每个残留项必须有 `reason`（为什么删不掉："FK constraint
  from external system"、"snapshot-restore pending"）。

不带 reason 的残留是失管的状态泄漏——它们跨 phase 累积，最终
引发环境类测试失败。

## 本检查器不做的事

- **执行拆除。** 本检查器校验计划 + 结果；执行在下游。
- **验证拆除正确性。** 拆除是否真的删掉了正确的数据是运行时
  问题。本检查器只查报告是否诚实、完整。
- **恢复快照。** 快照级恢复是兜底机制；本检查器只验证主清理
  被诚实地尝试过。
