# Fixture DAG 规则参考

`scripts/dag_check.py` 是可执行编码；本文档是意图说明。

## Finding codes（完整清单）

| 检查 | Code | Severity | 含义 |
|---|---|---|---|
| 1 | `CYCLE_DETECTED` | REJECT | 存在依赖环；拓扑排序失败。 |
| 2 | `MISSING_TEARDOWN` | REJECT | 带 `creates` 的节点没有 `teardown`。 |
| 2 | `BASELINE_NOT_DECLARED` | REJECT | Static 节点的 `baseline_ref` 不在图的 `baseline_refs` 中。 |
| 3 | `DANGLING_DEPENDENCY` | REJECT | `depends_on` 引用不存在的 node_id。 |
| 4 | `MISSING_NODE_ID` | REJECT | 节点没有 `node_id`。 |
| 4 | `DUPLICATE_NODE_ID` | REJECT | 两个节点共用 `node_id`。 |
| 4 | `MISSING_SCOPE` | REJECT | 节点没有 `scope`。 |
| 4 | `INVALID_SCOPE` | REJECT | `scope` 不在 `{session, module, function}` 内。 |
| 4 | `MISSING_TYPE` | REJECT | 节点没有 `type`。 |
| 4 | `INVALID_TYPE` | REJECT | `type` 不在 `{Static, Dynamic, Hybrid}` 内。 |

## 拓扑排序（检查 1）

使用 Kahn 算法：
1. 计算每个节点的入度（指向它的 `depends_on` 边数）。
2. 入度为零的节点入队作为种子。
3. 反复出队一个节点、追加到顺序末尾，并将其后继的入度减一。
4. 所有节点处理完 → 是合法 DAG，该顺序即合法的构建序列。
5. 还有节点剩下 → 存在环；回溯出环用于错误信息。

输出的 `topological_order` 是构建序列。拆除序列是它的**逆序**
（LIFO）——后构建的先拆除。这一点重要：早构建的 fixture 可能
依赖晚构建者仍然在场；按构建顺序拆除会破坏这一点。

## 拆除规则（检查 2）

抓住两种情况：

- 有 `creates`、无 `teardown` → `MISSING_TEARDOWN`。该节点把
  东西带进了世界却从不移除。这是设计出来的状态泄漏。
- 有 `creates`、`teardown` 为 `null` 或空字符串 → 同一 code。
  显式 null 不是拆除。

不检查的：拆除是否是 creates 的*正确*逆操作。节点创建了一行、
拆除却删了*另一*行，是本检查器无法发现的语义错误。要抓住它
需要运行时验证（拆除确实撤销了创建），那是 fixture 执行步骤的
职责。

## Baseline 交叉引用（检查 2，Static 规则）

Static 节点通过 `baseline_ref`（如 `VIP_USER_001`）引用预构建的
baseline。图在 `baseline_refs[]` 中声明自己已知的 baseline。检查
内容：Static 节点的每个 `baseline_ref` 必须出现在图的
`baseline_refs` 中。

这对版本管理的意义：baseline `VIP_USER_001` 变更时，「哪些 DAG
受影响？」要靠查所有 `baseline_refs` 包含它的图来回答。引用了
未声明 baseline 的 Static 节点对这类查询不可见——该 DAG 静默
假设了一个系统其他部分不追踪的 baseline。

## Scope 语义

| Scope | 生命周期 | 典型用途 |
|---|---|---|
| `session` | 整个测试 session（全部测试）。 | 昂贵的共享状态：运行中的服务、播种好的主 DB。 |
| `module` | 一组相关测试。 | 某测试类需要的一组订单。 |
| `function` | 单个测试函数。 | 测试要改动、需要全新的特定行。 |

检查器只验证 scope 取值合法。*选*的 scope 对不对是规划质量问题
——一个本应 `session` 的 fixture 被错标为 `function` 会跑 60 次
而不是 1 次，但 DAG 仍然合法。抓住那个需要用量分析，不在这里。

## 本检查器不做的事

- **执行 DAG。** 构建在下游。本检查器校验的是 DAG 计划。
- **生成字段取值。** 每个 fixture 里放什么是数据生成步骤的职责。
- **验证拆除正确性。** 如上——运行时问题。
- **追踪 baseline 版本。** 检查器强制的是声明；版本管理是
  配置/CI 的事。
- **检测过宽或过窄的 scope。** 合法取值都通过；选得对不对是
  判断题。
