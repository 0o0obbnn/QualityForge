# 37-API接口总览

> 本文是产品与研发共同阅读的接口导航，不替代机器可读契约。现行机器可读契约以[32-API规范](32-API规范.yaml)为准；2026-08-27新增的人机协作目标面以[39-人机协作目标契约](39-人机协作目标契约.md)为准，在激活前不是可调用API。

## 1. 契约基线

| 项目 | 当前约定 |
|---|---|
| OpenAPI | 3.0.3 |
| 契约版本 | `2.0.0-draft` |
| Base URL | `/api/v1` |
| 认证 | Bearer JWT或本地HttpOnly Cookie；WebSocket目标使用一次性资源绑定票据 |
| JSON字段 | `camelCase` |
| 数据库字段 | `snake_case`，不得直接泄漏为外部字段 |
| 当前规模 | 106 paths / 146 operations（以32号于2026-09-05批次六十七后本地解析实算为准；schemas 数随激活面增长，以 32 号为准） |
| 幂等 | 关键写操作使用`Idempotency-Key` |
| 返回结构 | `code`、`message`、`traceId`、`data` |

后端契约测试当前登记实现84个operation，主动延期62个（口径 84/146/62，批次六十八）。这只说明路由/契约实现覆盖，不代表全部页面、真实AI/Runner、生产安全或端到端业务闭环已验收。2026-08-27新增的人机协作接口族已随批次五十三（WP-03）、五十七（WP-04）、六十三（WP-05 发布链）激活并入 32 号计数。

产品版本V0/V1/V2/V3描述交付范围；`/api/v1`描述接口兼容代际，两者不是同一个概念。预发布阶段不为旧设计稿建立兼容承诺。

### 1.1 2026-08-27需求基线待激活接口族

Conversation/Message、ClarificationRequest/Response、TaskCard、AgentPlan/TaskContract、RunCommand/CommandReceipt、Budget/Checkpoint 已随批次五十三/五十七/六十三激活入 32 号（WP-03/04/05 实现推进中）；EvaluationRun 及评估面（RubricVersion/CalibrationSample/BenchmarkRun）仍冻结在 39 号，随 WP-07 契约激活并入。激活必须同一批次完成OpenAPI、DDL/迁移、RBAC/humanOnly、实时事件、后端路由、前端调用和正反E2E。

## 2. 八模块接口地图

| 模块 | 路径前缀 | 核心职责 | 操作数 |
|---|---|---|---:|
| 任务看板 | `/work-items`、`/review-tasks` | 统一工作流、AI运行记录、人工审核 | 10 |
| 知识库 | `/knowledge` | 来源快照、需求、API契约、知识条目 | 15 |
| 测试策划与设计 | `/test-strategies`、`/test-plans`、`/testing-irs`、`/test-*` | 策略、计划、可信设计链、正式用例 | 16 |
| 自动化测试开发 | `/automation` | Web/API等自动化代码及配套资产 | 9 |
| 测试执行 | `/execution-plans`、`/execution-tasks`、`/execution-results` | 版本冻结、调度、执行事实和证据 | 9 |
| 质量分析与缺陷 | `/quality` | 分析、Defect、报告、门禁和流水线 | 13 |
| AI Agent中心 | `/ai` | Skill、Agent、Workflow、Trace、Eval和独立验证 | 11 |
| 平台管理 | `/workspaces`、`/platform`、`/auth` | Workspace、Release、环境、密钥、RBAC与审计 | 22 |

## 3. 操作目录

### 3.1 任务看板

| 方法与路径 | operationId | 作用 |
|---|---|---|
| `GET/POST /work-items` | `listWorkItems` / `createWorkItem` | 查询或创建统一工作项 |
| `GET /work-items/{workItemId}` | `getWorkItem` | 获取工作项 |
| `POST /work-items/{workItemId}/transitions` | `transitionWorkItem` | 受状态机与权限控制地流转 |
| `GET /work-items/{workItemId}/runs` | `listWorkItemRuns` | 查询AI/人工/系统运行记录 |
| `GET/POST /review-tasks` | `listReviewTasks` / `createReviewTask` | 查询或创建绑定精确产出物版本的审核任务 |
| `GET /review-tasks/{reviewTaskId}` | `getReviewTask` | 获取审核任务与分派 |
| `GET /review-tasks/{reviewTaskId}/artifact` | `getReviewArtifact` | 读取审核绑定的精确不可变版本与摘要 |
| `POST /review-tasks/{reviewTaskId}/decisions` | `decideReviewTask` | 人工批准、退回或拒绝 |

### 3.2 知识库

| 路径组 | 操作 | 关键约束 |
|---|---|---|
| `/knowledge/source-imports`、`/source-snapshots/{id}` | 导入来源、读取不可变快照 | 外部内容先固化来源与摘要 |
| `/knowledge/requirements` | 查询/创建需求文档、创建版本 | 稳定根与不可变版本分离 |
| `/knowledge/api-contracts` | 查询/创建契约、创建版本 | APIContract是契约唯一归属模块 |
| `/knowledge/api-contract-baselines` | 创建版本基线 | 设计、Mock、分析必须固定精确版本和摘要 |
| `/knowledge/entries` | 查询/创建知识条目、创建版本 | 正式知识需审核后发布 |
| `/knowledge/candidates`、`/knowledge/search` | 候选治理、检索 | 检索命中不等于内容可信或已批准 |

### 3.3 测试策划与设计

| 路径组 | 操作 | 关键约束 |
|---|---|---|
| `/test-strategies` | 查询/创建策略、创建版本 | 策略是正式产出物 |
| `/test-plans` | 查询/创建计划、创建版本 | 计划绑定Release和已选策略版本 |
| `/testing-irs` | 编译、读取TestingIR | 保留来源追踪、规则、断言与覆盖链 |
| `/test-scenarios` | 创建场景 | 场景归属计划版本 |
| `/test-case-drafts/generate` | 生成设计草稿 | AI生成物不得直接成为正式用例 |
| `/test-cases` | 查询/创建正式用例、管理版本 | DesignTestCase与TestCase生命周期分离 |
| `/test-suites` | 查询/创建套件 | 套件成员固定用例版本 |

### 3.4 自动化测试开发

| 路径组 | 操作 | 关键约束 |
|---|---|---|
| `/automation/scripts` | 查询/创建脚本、创建版本 | 版本记录框架、运行时、依赖锁和内容摘要 |
| `/automation/script-versions/{id}/checks` | 发起代码检查 | 检查结果是审核输入，不替代人工代码审核 |
| `/automation/locators` | 查询/创建Locator版本 | 保留替代关系与验证结果 |
| `/automation/mocks` | 创建Mock配置 | 必须绑定APIContractVersion |
| `/automation/data-profiles` | 创建数据档案 | 定义生成、脱敏与清理规则 |
| `/automation/visual-baselines` | 创建视觉基线 | 固定视口、遮罩和内容摘要 |

### 3.5 测试执行

| 路径组 | 操作 | 关键约束 |
|---|---|---|
| `/execution-plans` | 查询/创建执行计划、创建版本、启动 | 启动时冻结全部资产版本和授权上下文 |
| `/execution-tasks` | 查询任务、读取详情、取消 | 任务状态是调度真相源 |
| `/execution-results` | 查询结果与证据 | 结果只追加；重跑创建新事实而非覆盖 |

### 3.6 质量分析与缺陷

| 路径组 | 操作 | 关键约束 |
|---|---|---|
| `/quality/result-analyses`、`/failure-clusters` | 创建结果分析、查询失败聚类 | AI推断与执行事实分层 |
| `/quality/defects` | 查询/创建Defect、创建版本、流转 | 缺陷是正式产出物，版本与生命周期分离 |
| `/quality/defects/{id}/sync-attempts` | 创建外部同步尝试 | 每次外部写入绑定批准记录、幂等键和负载摘要 |
| `/quality/reports` | 查询/创建报告 | 报告固定范围、执行与指标快照 |
| `/quality/gates` | 查询/创建质量门禁 | 规则版本化，不将AI判断直接等同放行 |
| `/quality/pipelines`、`/pipeline-runs` | 创建流水线配置、查询运行 | 外部回调与内部执行事实可追踪 |

### 3.7 AI Agent中心

| 方法与路径 | operationId | 作用 |
|---|---|---|
| `GET /ai/skills` | `listSkills` | 查询能力注册表 |
| `GET /ai/agents` | `listAgents` | 查询职责与权限边界 |
| `GET /ai/workflows` | `listAgentWorkflows` | 查询工作流版本 |
| `GET /ai/sessions` | `listAgentSessions` | 查询运行会话 |
| `GET /ai/sessions/{agentSessionId}/trace` | `getAgentSessionTrace` | 获取可审计Trace |
| `POST /ai/eval-runs` | `createEvalRun` | 对Agent/Skill/Prompt/Workflow固定版本评测 |

### 3.8 平台管理

| 路径组 | 操作 | 关键约束 |
|---|---|---|
| `/workspaces`、`/workspaces/{id}/releases` | 管理Workspace与Release | UI“项目”即Workspace；Release是其内交付批次 |
| `/platform/workspaces/{id}/environments` | 管理环境 | 环境只保存密钥引用，不返回密钥明文 |
| `/platform/workspaces/{id}/secrets` | 查询元数据、写入密钥 | 读接口不得返回secretValue |
| `/platform/runners` | 查询/注册Runner | 能力、运行时与资源池显式登记 |
| `/platform/integrations` | 查询/创建集成 | 凭据通过Secret引用 |
| `/platform/role-bindings` | 查询/创建角色绑定 | 权限按平台、租户、Workspace或资源作用域生效 |
| `/platform/audit-logs` | 查询审计日志 | 只追加且受专门审计权限保护 |
| `/auth/ws-tickets` | 创建WebSocket票据 | 一次性、短时、资源绑定、不扩大权限 |

## 4. 状态码与错误码

| HTTP | 含义 | 典型错误码 |
|---:|---|---|
| 400 | 请求或业务输入无效 | `VALIDATION_FAILED`、`DATA_SOURCE_MISSING`、`RUNNER_CAPABILITY_MISSING` |
> 错误码全集共 21 个(与 32-API ErrorEnvelope 枚举一致,2026-08-15 全量精读修复:补 429 行与 INVALID_CREDENTIALS/CSRF_VALIDATION_FAILED/SETUP_ALREADY_COMPLETED) |
| 401 | 未认证或令牌无效 | `UNAUTHORIZED`、`INVALID_CREDENTIALS` |
| 403 | 缺权限或违反职责分离 | `FORBIDDEN`、`CSRF_VALIDATION_FAILED`、`REVIEW_REQUIRED`、`SEPARATION_OF_DUTIES_VIOLATION`、`EGRESS_DENIED`、`SECRET_ACCESS_DENIED` |
| 404 | 资源不存在或不可见 | `NOT_FOUND` |
| 409 | 状态、幂等或版本冲突 | `CONFLICT`、`SETUP_ALREADY_COMPLETED`、`IDEMPOTENCY_CONFLICT`、`INVALID_STATE_TRANSITION`、`STALE_ARTIFACT_VERSION`、`EXTERNAL_SYNC_CONFLICT` |
| 429 | 触发限流 | `RATE_LIMITED` |
| 503 | 依赖暂时不可用 | `DEPENDENCY_UNAVAILABLE` |
| 500 | 未分类内部错误 | `INTERNAL_ERROR` |

服务端不得把数据库异常、密钥、内部路径或第三方原始敏感响应直接写入`message`或`details`。`traceId`用于关联审计和运行证据。

## 5. 旧路径迁移

| 旧设计路径族 | 现行归属 |
|---|---|
| `/test-designs/*` | `/test-strategies`、`/test-plans`、`/testing-irs`、`/test-cases` |
| `/assets/*` | `/automation/*`或`/knowledge/api-contracts/*` |
| `/executions/*` | `/execution-plans`、`/execution-tasks`、`/execution-results` |
| `/intelligence/*` | `/quality/*`或`/knowledge/*` |
| `/cicd/*` | `/quality/gates`、`/quality/pipelines` |
| `/agents`、`/skills` | `/ai/agents`、`/ai/skills` |
| `/reviews/*` | `/review-tasks/*` |
| `/settings/*` | `/platform/*` |

这些旧路径从未成为已发布运行时接口，因此直接迁移，不提供双写、转发或兼容窗口。

## 6. 契约验收

1. OpenAPI必须能被标准解析器加载。
2. 每个operation必须有唯一`operationId`。
3. 所有`#/components/schemas/*`引用必须可解析。
4. 模块、实体和状态枚举必须与03、04、33号权威源一致。
5. WebSocket票据接口与36号实时契约一致。
6. 产品仍处设计阶段；静态契约通过不等于API已开发、部署或通过端到端验收。
