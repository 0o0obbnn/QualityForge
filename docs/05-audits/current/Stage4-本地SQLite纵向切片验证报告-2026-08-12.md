# Stage 4 本地SQLite纵向切片验证报告

> 验证日期：2026-08-12。结论仅适用于本地Profile，不追溯改写既有审计，也不代表目标PostgreSQL、真实模型或八模块产品已经验收。

## 1. 结论

用户确认的五项工作均已完成并获得当前批次证据：SQLite持久化、本地JWT与作用域隔离、确定性Provider、React审核前端、真实浏览器E2E。纵向切片可在不安装数据库服务、不配置模型密钥的电脑上运行。

当前裁决为`LOCAL_SLICE_PASS_WITH_LIMITS`：允许继续开发“人工批改→生成新版本→再次复核”能力；不允许据此宣称生产可用、多租户数据库隔离已由RLS保障或AI模型效果达标。

## 2. 五项交付核对

| 项 | 已实现 | 当前证据 | 明确边界 |
|---|---|---|---|
| 1. SQLite | schema v2、顺序迁移、WAL、事务、外键、busy timeout、0600文件权限 | 自动化测试与真实服务重启后数据恢复；最终Session为`COMPLETED` | 单机应用层隔离，不是PostgreSQL RLS/高并发 |
| 2. JWT | 首用户setup、本地login/logout/me/status、scrypt、短时JWT、Cookie、CSRF、限流、成员资格复查 | setup仅一次、无登录拒绝、CSRF拒绝、Agent JWT审批拒绝、第二租户读取拒绝 | 进程重启轮换签名密钥；不是OIDC/MFA |
| 3. Provider | `PlanningGenerationProvider`协议与`deterministic-local@1.0.0` | 产出版本记录provider ID/version；离线生成策略、计划、正反用例 | 不读取模型Key，不代表模型效果 |
| 4. 前端 | 初始化、登录、创建演示任务、审核队列、精确版本/摘要/Provider/Trace、批准/退回/拒绝 | TypeScript与Vite生产构建通过；生产依赖审计0漏洞 | 仅最小审核工作台，不是八模块全量UI |
| 5. E2E | 浏览器完成setup→生成→逐项检查→四项批准→重启→重新登录→状态恢复 | 最终0项待处理、四项`APPROVED`、Session=`COMPLETED`、控制台0错误；截图见`output/playwright/stage4-review-complete.png` | 当前只覆盖planning happy path及后端负向安全测试 |

## 3. 数据与可信链

SQLite为不同聚合建立独立表并保留tenant/workspace索引，覆盖Tenant、Workspace、User、Membership、Requirement及版本、WorkItem、TestStrategy/TestPlan/TestCase及版本、ReviewTask、AgentSession、Trace、版本索引和幂等键。正式产出物仍采用稳定根与不可变版本，ReviewTask绑定`artifactId + artifactVersionId + contentDigest`。

浏览器批准的是精确版本而不是可变正文。服务端在决定前复核摘要、身份类型、能力和Workspace；全部审核完成后才将WorkItem与AgentSession推进至完成态。

## 4. 验证结果

| 检查 | 结果 |
|---|---|
| Ruff | PASS |
| Mypy strict | PASS，21个源文件 |
| Pytest | PASS，10项 |
| OpenAPI官方validator | PASS |
| OpenAPI规模 | 78 paths / 102 operations / 80 schemas；运行时22 operations |
| 前端生产构建 | PASS，2129 modules transformed |
| npm生产依赖审计 | PASS，0 vulnerabilities |
| Skill统一eval | PASS，30/30目录可发现，103 cases，14个确定性runner |
| Agent治理验证 | PASS，4 agents / 14 Gate 0 skills |
| 浏览器E2E | PASS，0 console errors / 0 warnings |
| SQLite现场状态 | schema v2；1个`COMPLETED` Session；4个`APPROVED` ReviewTask；文件0600 |

后端负向用例单独覆盖：缺失登录、CSRF缺失、需求摘要篡改、幂等冲突、Workspace越权、第二租户跨租户读取、AgentIdentity批准正式产出物。它们与浏览器happy path是不同证据层，未混成“全面产品验收”。

## 5. 安全与工程债务

1. SQLite文件拥有者可绕过API直接读取内容，因此只适合受控个人电脑。
2. 进程内JWT密钥避免硬编码Secret，但重启后必须重新登录；多人或部署环境需使用外部密钥管理与OIDC。
3. 前端CSP为Fluent UI运行时样式暂时允许`style-src 'unsafe-inline'`；扩大部署面前需用nonce/构建策略收紧。
4. 当前持久化采取小切片整状态事务写入，适合低数据量Spike；扩大数据量前需按聚合增量写入与并发压测。
5. 确定性Provider只证明工作流、版本和审核边界可运行，不评价生成质量。

## 6. 推荐后续顺序

1. 实现审核“批改并生成新版本”：保留旧版本、差异、批改意见、Agent再生成来源和二次ReviewTask。
2. 增加ReviewTask任务看板筛选、分派、优先级和逾期信息，但不复制产出物正文。
3. 扩展测试策略、计划和用例的结构化编辑器与版本diff，再补退回修改的浏览器E2E。
4. 接入接口自动化代码这一种新正式产出物，复用同一版本/摘要/人工代码审核门；不要同时铺开Web、报告、缺陷全部模块。
5. 只有出现多人并发、团队部署、原生RLS、向量检索或备份恢复需求时，再执行SQLite→PostgreSQL Profile迁移Spike。
6. 真实模型最后接入：先定义黄金集、质量指标、成本/延迟预算、降级和数据出站策略，再实现Provider适配；未通过评测不得替换确定性基线。
