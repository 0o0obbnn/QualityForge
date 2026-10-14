# QualityForge V1 接口测试用例（api-test-suite）

基于 [32-API规范.yaml](../../docs/04-architecture/32-API规范.yaml)（契约 v2.0.0-draft）与后端已实现运行时行为，使用 `prototypes/skills/` 下的技能链生成的接口测试用例资产。

## 生成链路

```
32-API规范.yaml + 后端实现
        │ 提取
        ▼
rules.json（50 条业务规则）
        │ rule_check.py（business-rule-extractor）── PASS（50 条）
        ▼
testing_ir.json（Testing IR v1.0.0）
        │ validate.py（ir-validator）────────────── PASS（六族 0 findings）
        ▼
scenarios.json（92 个场景，五面）
        │ scenario_check.py（scenario-generator）── PASS（迁移覆盖 27/27）
        ▼
cases.json（92 条测试用例）✅ 本次交付物
        │ case_check.py（test-case-generator）───── PASS（0 findings）
        ▼
（下游：断言经 assertion-verifier 验证后，由 api-test-generator 生成可执行 pytest/httpx 脚本）
```

## 范围

- **覆盖面**：后端已实现的 84 个 operation（批次六十七时点：WP-01 上下文/驾驶舱 6 + WP-03 协作 11 + WP-04 运行控制 8 + WP-05 发布链 3 + 既有 56）全部纳入 IR `interface_contracts`；92 条用例按 operation 粒度（method+path）步骤覆盖 84/84，其中 29 个核心 operation 被 ≥2 条用例从不同面测试；缺陷导向用例覆盖 409 全家族错误码（ASSET_NOT_APPROVED/FOUR_EYES_SAME_APPROVER/AGENT_PLAN_NOT_APPROVED/STALE_ARTIFACT_VERSION/RELEASE_NOT_IN_WORKSPACE/CLARIFICATION_ALREADY_ANSWERED 等）与幂等重放、级联失效。
- **用例重点**：认证（setup/login/me/logout/限流）、工作项（创建/查询/流转/分派/SLA）、审核（任务/产物/Diff/决策）、执行计划、质量（报告/缺陷/分析）、观测（事件/指标）、全局契约（响应信封/camelCase/幂等键/分页边界）。
- **状态机如实收窄**：WorkItem 状态机按 M1 切片只声明 `BACKLOG->REWORK`；批次六十八扩展 6 个新状态机（AssetVersion 五态含发布链、TaskCard、AgentPlan、Clarification、AgentSession 六态、ReviewTask 扩 IN_PROGRESS/CANCELLED）并声明 27 条已实现迁移（RETRY/AUTHORIZE/REVOKE 命令与 EXPIRED 澄清未实现，不声明）。

## 用例分布

| 维度     | 分布                                                                            |
| -------- | ------------------------------------------------------------------------------- |
| 场景五面 | normal 24 / abnormal 19 / boundary 5 / permission 4 / state_transition 40        |
| 模块     | AUTH 9 / WI 18 / RT 15 / EX 4 / QA 3 / OBS 3 / ENV 2 / PLN 10 / CTX 3 / COL 6 / RC 4 / PUB 4 |
| 断言类型 | 状态码 + 错误码 + 字级断言（lockVersion、contentDigest、metRate、camelCase 等） |

## 机器验证记录（全部实跑）

| 门禁       | 命令                                                                                                                             | 结果                           |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| 规则包     | `python3 ../skills/business-rule-extractor/scripts/rule_check.py --packet rules.json`                                            | PASS，35 条规则 0 findings     |
| Testing IR | `python3 ../skills/ir-validator/scripts/validate.py --ir testing_ir.json`                                                        | PASS，六族检查 0 findings      |
| 场景图     | `python3 ../skills/scenario-generator/scripts/scenario_check.py --scenarios scenarios.json --ir testing_ir.json`                 | PASS，92 场景，IR 迁移覆盖 27/27 |
| 测试用例   | `python3 ../skills/test-case-generator/scripts/case_check.py --cases cases.json --ir testing_ir.json --scenarios scenarios.json` | PASS，92 用例 0 findings       |

各门禁完整报告见 `rule_report.json` / `ir_report.json` / `scenario_report.json` / `case_report.json`。

## 字段占位符约定

用例 `input` 中的 `{placeholder}` 为执行期注入变量（`{workspace_id}`、`{sha256_digest}`、`{unique_key_16_128}` 等），由 fixture DAG 生成；转为可执行脚本时须按 api-test-generator 契约声明 fixture 依赖并从 `os.environ` 注入，不得硬编码。

## 用例设计方法对照

| 方法 | 使用情况 |
|---|---|
| 等价类划分 | 有效/无效类代表值（必填缺失按同一校验路径归并，未逐字段重复展开） |
| 边界值分析 | password 12/256、title 256、pageSize 1/200、Idempotency-Key 16/128、metRate total=0 |
| 状态迁移法 | 乐观锁 409、终态 409、非法迁移 422、并发竞争恰好一个成功 |
| 判定表 | approveDisabledReason 三分支（TASK_CLOSED/STALE_VERSION/null）、决策映射 |
| 场景法 | 退回→版本回 DRAFT、流转→事件检索、logout→me 401、幂等重放链 |
| 错误推测法 | 畸形 JSON、错误 Content-Type、特殊字符/超长、重复 setup、限流、跨 workspace |
| 正交实验法 | 未使用（当前无多参数组合需正交表的场景） |

设计立场：测试的目的是发现缺陷而非证明无缺陷——断言精确到错误码、以破坏性输入与并发竞争为主攻方向。

## 自动化执行（2026-08-27）

`tests/` 为可执行层（pytest + httpx ASGITransport，function 级独立 SQLite，配置经 `QF_TEST_PASSWORD` 注入）：

```
cd backend && uv run pytest ../prototypes/api-test-suite/tests
```

结果：**89 项 = 80 passed / 4 skipped / 5 xfailed(strict)**（xfail 即缺陷证据，修复实现后应转为 XPASS 告警）。

执行发现 4 个契约-实现漂移缺陷（详见 `execution-report.json`）：actorType=USER 违反 B14 裁决、初始态 READY 违反 Schema DEFAULT BACKLOG、createWorkItem 无幂等键声明与幂等实现、coverage 维度契约 required 缺失。执行同时证伪并修正了 3 处用例断言（决策响应不回传 decision 字段、runs 宽松语义、事件字段名 eventType）。

## 已知边界

- 未覆盖 32 号规范中尚未实现的 49 个目标契约 operation（KNOWN_DEFERRED，按模块开发收敛后再入 IR）。
- SLA `met`/`overdue` 的完整口径验证依赖 DONE/APPROVED 状态可置位（M1 流转仅支持 REWORK），当前用例断言聚焦分组结构、P3 只计 total 与 metRate 除零口径。
- 下游可执行化前置：用例 expected_results 需先经 `assertion-verifier` 验证断言契约，再走 `api-test-generator` 生成 pytest 脚本（本包已完成到用例层）。

## 对齐再生成（2026-09-05，批次六十八）

WP-01（上下文/驾驶舱）、WP-03（协作）、WP-04（运行控制）、WP-05（发布链）合入后按 84 op 口径增量再生成：
rules 35→50、IR interface_contracts 56→84（+19 需求引用 +8 实体 +7 状态机 27 迁移）、
scenarios 57→92、cases 74→92；四门禁重跑全 PASS（0 findings），覆盖机械验证 84/84。
`tests/` 可执行层仍为 2026-08-27 的 56 op 口径（89 项），随下次执行批次扩展。
