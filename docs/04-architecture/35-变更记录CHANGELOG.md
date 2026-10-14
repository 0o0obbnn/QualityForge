# 35-变更记录 CHANGELOG

> 本文档记录对 QualityForge 设计文档集的一致性修复与设计缺陷修正。
> 每条变更附**问题**、**修复**、**受影响文件**、**权威依据**,便于追溯。
> 变更批次:2026-07-18(第三方独立评估修复轮)

---

## 批次 2026-07-18 —— 独立评估修复轮

本轮修复源于对全部设计文档的独立深度评估(核心技术文档逐行审读 + 跨文档交叉校验 + 外部多源印证:Gartner AI-Augmented Testing 市场定义、PostgreSQL RLS 官方行为)。修复覆盖 **实体命名一致性、状态枚举矛盾、多租户安全漏洞、AI 置信度阈值、功能划分补齐** 五大类,共 11 组变更。

> 说明:本轮同时证伪了 `00-设计文档全面审计报告-v2.md` 中"跨文档状态一致性:0 处冲突"的结论——该结论未覆盖 9 份模块 PRD 的一致性回归。

---

### 一、P0 实体命名对齐(开发阻塞项)

模块 PRD(10–19)大量使用术语表明确标注为"废弃/别名"的实体名建模,与领域模型(04)、Schema(33)、API 规范(32)的规范名不一致,开发照 PRD 编码将与库表/接口对不上。

#### C-1: `ExecutionJob` → `ExecutionTask`,`ExecutionLog` → `ExecutionResult`

- **问题**:13-PRD-Execution 整篇用 `ExecutionJob`/`ExecutionLog`/`job_id` 建模;规范名为 `ExecutionTask`/`ExecutionResult`(术语表 03:56/58,Schema `t_execution_task`/`t_execution_result`)。
- **修复**:实体表头、字段名(`job_id`→`execution_task_id`)、依赖章节、API 路径(`/executions/jobs/*`→`/executions/tasks/*`)、响应字段(`job_id`→`taskId`)全部对齐;同步修正 32-API 规范中 `/executions/jobs/run` → `/executions/tasks/run`、`jobId`→`taskId`。
- **受影响**:`13-PRD-Execution.md`、`32-API规范.yaml`
- **依据**:`03-术语表` L56/58、`33-Schema` `t_execution_task`/`t_execution_result`

#### C-2: `TestScene` → `TestScenario`,`scene_id` → `scenario_id`

- **问题**:11-PRD-TestDesign 用 `TestScene`/`scene_id`;规范名 `TestScenario`(Schema `t_test_scenario`,API `TestScenario`)。
- **修复**:实体表头、正文术语、FK 字段名、JSON 示例字段统一为 `TestScenario`/`scenario_id`。
- **受影响**:`11-PRD-TestDesign.md`
- **依据**:`03-术语表` L47、`33-Schema` `t_test_scenario`、`32-API` L1322

#### C-3: `MockRule` → `MockConfig`

- **问题**:12-PRD-TestAsset 用 `MockRule`;规范名 `MockConfig`(Schema `t_mock_config`,API `MockConfig`)。
- **修复**:实体表头改为 `MockConfig`。
- **受影响**:`12-PRD-TestAsset.md`
- **依据**:`03-术语表` L52、`33-Schema` `t_mock_config`、`32-API` L1414

#### C-4: Locator 状态枚举统一

- **问题**:12-PRD 用 `VERIFIED/FLAKY/BROKEN`;领域模型(04:477)、Schema、API(32:1466)三方一致为 `Verified/Decaying/Failed/Healed`。
- **修复**:字段说明、状态机、页面线框、UI 文案、降级策略全部改为规范枚举,并保留旧称映射(FLAKY→Decaying、BROKEN→Failed);状态机补 `Healed` 节点。
- **受影响**:`12-PRD-TestAsset.md`
- **依据**:`04-核心领域模型` L477、`33-Schema` `t_locator`、`32-API` Locator schema

---

### 二、P0 Workspace 状态枚举矛盾

#### C-5: 业务生命周期与 AI 扫描生命周期解耦

- **问题**:`t_workspace.status` DDL 仅允许 `Active/Archived`(10-PRD:82、Schema),但状态机使用 `CREATING/SCANNING/READY/ERROR/ARCHIVED`,创建 API 还返回非法值 `"status":"CREATING"`(写库会失败);扫描生命周期无落地字段。
- **修复**:
  1. `Workspace.status` 只承载业务态(`Active`/`Archived`)。
  2. 新增 `WorkspaceAIContext.scan_status`(`Pending/Scanning/Ready/Error`)+ `last_scan_error` 承载扫描过程态。
  3. 状态机拆为两条独立状态线。
  4. 创建 API 返回 `status:Active` + `scan_status:Pending`;`ai-scan` 返回 `scan_status:Scanning`。
  5. 补齐缺失的 `3.1.4` 表编号(原文从 3.1.3 直接跳到 3.1.5)。
- **受影响**:`10-PRD-Workspace.md`、`33-Schema`(t_ai_context 新增 scan_status/last_scan_error)、`03-术语表`(新增 scan_status 枚举)、`32-API`(Workspace schema 补 status/scanStatus)
- **依据**:`33-Schema` `t_workspace.status` 注释、`04-核心领域模型` Workspace 实体

---

### 三、P0 多租户安全漏洞

#### C-6: RLS 绕过风险(致命)

- **问题**:RLS 策略仅 `ENABLE`,未 `FORCE`;PostgreSQL 表 owner 与超级用户**默认绕过 RLS**(官方文档 + 多源印证)。若应用以建表账号连库(常见默认),RLS 形同虚设,跨租户数据全裸。且 `tenant_id` 为空时策略 fail-open。
- **修复**:批量 DDL 增加 `FORCE ROW LEVEL SECURITY`;新增专用非 owner 低权限连接角色 `qf_app`;策略改为 tenant 上下文缺失时 **fail-closed**(拒绝而非放行)。
- **受影响**:`33-数据库Schema设计.md` §4
- **依据(外部)**:[PostgreSQL RLS — Neon 文档](https://neon.com/postgresql/administration/row-level-security)、[activerecord-tenant-level-security](https://github.com/yuki24/activerecord-tenant-level-security)(均警告 owner/postgres 默认 BYPASSRLS)

#### C-7: `SET LOCAL` 事务陷阱 + SQL 注入

- **问题**:RLS 切面用 `String.format("SET LOCAL ... '%s'", tenantId)` 拼接(注入风险);`SET LOCAL` 仅事务内有效,只读查询若无显式事务则设置立即失效,RLS 读到空租户;连接池下若误用 `SET`(非 LOCAL)会污染连接。
- **修复**:切面改用参数化 `set_config('app.current_tenant_id', ?, true)`;强制方法处于 `@Transactional` 边界;注入前做 UUID 格式校验;缺租户上下文时抛异常(fail-closed)。
- **受影响**:`34-认证授权设计.md` §3
- **依据**:PostgreSQL `SET LOCAL` 事务语义

#### C-8: 网关 Header 信任边界缺失

- **问题**:下游微服务"直接读 `X-Tenant-ID` 不再校验",但未要求网络层保证服务不可被绕过网关直连;任何能直连 Java/Python 服务的路径都可伪造 Header 越权。
- **修复**:补充信任边界强制要求(服务间 mTLS / 服务网格 / K8s NetworkPolicy,仅允许网关来源流量)。
- **受影响**:`34-认证授权设计.md` §1.2

#### C-9: 明文数据库连接串

- **问题**:`WorkspaceEnvironment.db_connection_string` 为明文 `TEXT`,内含库账号密码,绕过了平台自身的双信封加密安全模型。
- **修复**:改为双信封加密存储(与 WorkspaceSecret 一致),PRD 与 Schema 注释同步标注加密要求。
- **受影响**:`10-PRD-Workspace.md`、`33-数据库Schema设计.md`(t_environment)

---

### 四、P1 AI 置信度阈值统一

#### C-10: 阈值以 21 号矩阵为单一事实源

- **问题**:模块 PRD 的自动化门槛与 `21-AI介入点降级矩阵`(全局权威)数字不一致:用例生成 PRD `0.75` vs 矩阵 `0.80`;Locator 自愈 PRD `0.90/0.70` vs 矩阵 `0.92/0.80`。同一"是否自动执行"的安全边界出现两个值。
- **修复**:回填 11-PRD 用例生成 Level-1 门槛为 `> 0.80`;12-PRD Locator 自愈自动阈值 `> 0.92`、降级阈值 `< 0.80`;两处均注明"以 21 号矩阵为单一事实源"。
- **受影响**:`11-PRD-TestDesign.md`、`12-PRD-TestAsset.md`
- **依据**:`21-AI介入点降级矩阵.md`

#### C-11(附带): 降级伪代码桩修正

- **问题**:`31-系统架构` 的 `_check_confidence` 恒返回 `True`(置信度校验永远通过,与整套阈值降级体系冲突);`fallback_rules[scenario]` 对未登记场景会 KeyError。
- **修复**:`_check_confidence` 改为读取响应置信度与场景阈值比较的真实逻辑说明;`fallback_rules` 缺场景时兜底为"转人工"而非崩溃。
- **受影响**:`31-系统架构设计.md` §5.2

---

### 五、P1 功能划分补齐

#### C-12: APIContract 功能落地

- **问题**:功能地图(01:56)把"契约管理"列为 TestAsset 一级能力,Schema 有 `t_api_contract`、API 有 `APIContract` schema,但 12-PRD 正文无对应功能与实体表,契约仅作为 Mock 输入被提及(功能悬空)。
- **修复**:扩展 §2.4 增加契约 CRUD 与 Swagger 差分对比能力;新增 `3.1.6 APIContract` 实体字段表(对齐 `t_api_contract`)。
- **受影响**:`12-PRD-TestAsset.md`

---

### 六、DesignTestCase 编号稳定性(设计取舍)

- **问题**:11-PRD `DesignTestCase.case_code` 原为 `Unique`,审批入库时碰撞则重新生成,导致评审期看到的编号入库后变化。
- **修复**:草稿期 `case_code` 改为可空、仅展示、不做唯一约束;入库转 `TestCase` 时由资产服务分配稳定正式编号。409 冲突处理保留于入库时刻,语义自洽。
- **受影响**:`11-PRD-TestDesign.md`

---

---

## 批次二:线上契约命名统一(snake_case → camelCase)

### CH-11:PRD 请求/响应 JSON 示例统一为 camelCase

- **问题**:10 份模块 PRD 的 ```json 示例键为 snake_case,而 `32-API规范.yaml` 为 camelCase,同一字段两种线上写法。
- **修复**:以脚本仅重写 ```json 围栏块内的**键名**为 camelCase(值、SQL DDL、实体字段表的 snake_case 物理列名一律不动)。共 10 份文件、约 156 处键名。
- **约定固化**:`32-API规范.yaml` 顶部 `info.description` 增加权威约定注记——线上 JSON 一律 camelCase,数据库物理列一律 snake_case,由持久层做映射。
- **校验**:JSON 块内残留 snake 键 = 0;`33-Schema` DDL 与 PRD 实体表 snake_case 物理列保持不变。
- **受影响**:`10`–`19` PRD、`32-API规范.yaml`

---

## 批次三:WebSocket 实时契约补齐

### CH-12:新增 `36-WebSocket实时契约.md`

- **问题**:Execution/Agent 多处依赖 WebSocket 实时日志/Trace/进度流,但 `32-API规范.yaml` 为纯 REST,长期缺 WS 契约(历史审计 M-8 未闭环)。
- **修复**:新增独立实时契约文档,覆盖:
  - 握手鉴权(JWT `Sec-WebSocket-Protocol` 承载,禁 query token)、租户校验、连接生命周期
  - 3 条通道:执行日志流 / Agent Trace 流 / 工作台大盘推送
  - 统一信封 `{type, channel, seq, ts, tenantId, data}`;服务端消息类型 `log.line`/`case.result`/`task.progress`/`anomaly.alert`/`locator.healing`/`agent.trace`/`error`/`pong`;客户端 `subscribe`/`unsubscribe`/`ping`
  - 断线重连 + `seq` 续传、心跳、背压丢弃策略、200ms 推送延迟(对齐 NFR)、错误码
  - payload 复用既有 REST 模型(`ExecutionResult`/`AgentTraceNode`),camelCase 一致
- **关联更新**:`32-API规范.yaml` 注记指向本契约;`13-PRD-Execution.md` 日志端点标注握手指向本契约;`02-PRD总纲.md` 增加技术规范文档索引。
- **受影响**:`36-WebSocket实时契约.md`(新增)、`32`、`13`、`02`

---

---

## 批次四:全局架构一致性修复(P0)

源于一次自上而下(全局→分支)的系统性方案评估,修复两处架构级硬伤。

### CH-13:统一"工作空间初始化 Saga"为单一事实源

- **问题**:同一个 Saga 在两份文档定义**不一致**——`31-系统架构` 用 `Pending→Ready` 状态、步骤为「空间→AIContext→环境」;`20-非功能需求` 用 `Initialization Failed` 状态、步骤为「元数据→知识存储→Webhook→扫描」。且这些 Workspace 状态词与上轮收敛后的 `Active/Archived` 冲突,补偿链也不同。开发无所适从。
- **修复**:
  - 以 `31-系统架构设计.md` §4 为**权威流程**,重绘 Saga 图:S1 建空间(status=Active)+AIContext(scan_status=Pending) → S2 写 AIContext 明细 → S3 建默认环境;逆序补偿 C3→C2→C1(物理删除+审计留痕)。
  - 明确**关键路径边界**:AI 扫描、CI/CD Webhook 绑定**不在**创建 Saga 同步路径内(异步/独立后续)。
  - 状态口径归一:Saga 全程只碰 `Workspace.status`(Active/Archived)与 `scan_status`(Pending/Scanning/Ready/Error),废除 `Pending`/`Ready`/`Initialization Failed` 中间业务态。
  - `20-非功能需求.md` 改为**引用**权威流程,不再重复定义,杜绝漂移。
- **受影响**:`31-系统架构设计.md`、`20-非功能需求.md`

### CH-14:定义系统接口知识图谱的存储载体

- **问题**:多处承诺"系统接口知识图谱",但技术选型只定义了 PGVector(向量,解决相似度),`t_ai_context` 仅有 `graph_version` 版本号字段,**没有任何图谱本体(节点/边)存储表**——"图谱"是空承诺。图(实体-关系)与向量是两种存储模型,PGVector 覆盖不了。
- **修复**:
  - Schema 新增 `t_kg_node`(节点:Service/Endpoint/Entity/ExternalDep)+ `t_kg_edge`(有向边:Calls/DependsOn/Reads/Writes/Exposes),在 PostgreSQL 内以**邻接表**建模图,含 `graph_version` 版本指针与唯一约束/索引。
  - 两表均带 `tenant_id`,自动纳入 §4.2 动态 RLS + FORCE RLS 隔离,无需额外改动。
  - `30-技术选型决策.md` 记录决策:**不引入独立图库(Neo4j)**,理由是查询以取子图/一两跳影响面为主,关系表+递归 CTE 足够,且与主库同事务/同 RLS/同备份;并给出升级触发条件(>4 跳深遍历高并发时再评估)。
- **受影响**:`33-数据库Schema设计.md`、`30-技术选型决策.md`

---

## 批次五:架构选型收敛为纯 Python（2026-07-18）

### CH-15:技术栈由 Java+Python 混合微服务改为纯 Python(FastAPI)

- **问题（决策论证错误 + 复杂度过高）**:原选型用"纯 Python 因 GIL 锁导致核心 API 延迟飙升"作为引入 Java 的核心论据。该论证技术上不成立——平台 AI 操作以**等待 LLM 返回的 I/O 为主**,asyncio 恰好擅长,GIL 不是瓶颈;真正的性能瓶颈是 LLM 调用本身(秒级),与 Web 框架语言无关。用错误理由支撑的双语言栈徒增运维/团队复杂度。
- **决策**:经确认,平台**无真正的 CPU 密集常驻任务**,统一为**纯 Python 3.12 + FastAPI** 单语言栈。原 Java 的企业级能力用成熟 Python 库补齐:事务用 SQLAlchemy 2.0 `async with session.begin()` 显式边界、SSO/OAuth2 用 Authlib、LDAP 用 python-ldap。少量 CPU 密集活(万级聚合/文档解析)下推 SQL 或交 Celery worker + C 扩展库(执行时释放 GIL)。
- **修复**:
  - `30-技术选型决策.md`:§1 三方案对比与结论整体改写为"纯 Python(最终选型) vs 混合 vs 纯 Java";删除 GIL 谬误,保留"故障域隔离"作为部署级(独立容器)而非语言级要求;§2.2 后端栈合并为单一 Python 栈。
  - `31-系统架构设计.md`:C4 图去掉 Java/Spring 子集群,全部服务标注 Python/FastAPI;`gateway-service` 由 Spring Cloud Gateway 改为 FastAPI+Uvicorn(可选 Traefik/APISIX 边缘代理);服务职责表语言列统一。
  - `34-认证授权设计.md`:RLS 多租户切面由 Java/Spring AOP + Hibernate 重写为 **FastAPI 依赖注入 + SQLAlchemy `event`/`set_config`** 实现,三条安全约束(事务内注入、参数化防注入、UUID 校验 fail-closed)全部保留;鉴权流程图"业务微服务(Java)"改为统一 Python 服务。
  - `20-非功能需求.md`:熔断器由 Resilience4j 改为 Python 生态(如 `purgatory`/自研 asyncio 断路器);OTel 埋点对象由"Spring Boot 后端"改为"FastAPI 服务"。
  - `33-数据库Schema设计.md`:RLS 事务边界说明由 Spring `@Transactional` 改为 SQLAlchemy 显式事务。
- **保留项**:所有文档中作为**被测系统技术栈示例**的 `Spring Boot`(如 Workspace 技术栈下拉、TestDesign 上下文示例)予以保留——平台需要能测 Java 系统,这与平台自身用什么语言无关。
- **受影响**:`30`、`31`、`34`、`20`、`33`

### CH-16:LlmConfig 大模型密钥改为租户级隔离

- **问题**:`LlmConfig`(大模型网关配置)的租户归属未定,API Key 到底全局共享还是每租户自配不明确,直接影响 RLS 与计费归属。
- **决策**:**每租户自配**——各租户使用自己的大模型 API Key,数据与成本隔离。
- **修复**:
  - `LlmConfig` **新增 `tenant_id`**(原表缺失,并非已有);自动纳入 §4.2 FORCE RLS 隔离。
  - `model_name` 唯一约束由**全局唯一**改为**租户内唯一**(`UNIQUE(tenant_id, model_name)`),否则不同租户无法配置同名模型。
  - `api_key_encrypted` 由 `VARCHAR(256)` 放宽为 `TEXT`(容纳"密文 Key + 密文 DEK + nonce + auth tag"打包)。
- **补齐 DDL**:`33-数据库Schema设计.md` 原**无 `t_llm_config` 建表脚本**(该实体此前仅存在于 19-PRD 实体表),本次已补齐 `t_llm_config` DDL(含 `tenant_id`、`UNIQUE(tenant_id, model_name)`、`api_key_encrypted TEXT`),带 `tenant_id` 自动纳入动态 FORCE RLS。
- **受影响**:`19-PRD-PlatformSettings.md`、`33-数据库Schema设计.md`

### CH-17:补齐 SkillCenter 自定义 Skill 运行时沙箱安全模型

- **问题（最高危攻击面无防护）**:SkillCenter 允许测试工程师上传**任意 Python/JS 脚本**并在 Runner 节点执行(§1.2、路径二),但整份 PRD **未定义任何运行时安全模型**——恶意/失误脚本可导致 RCE、横向渗透内网、窃取其他租户 Secrets、资源耗尽 DoS。且 `Skill`/`SkillInvocation` 表缺 `tenant_id`,`name` 为全局 UNIQUE(跨租户会冲突/泄露)。
- **修复**:
  - `15-PRD-SkillCenter.md` 新增 **§4.5 运行时沙箱安全模型**,在 [20-非功能需求.md §2.1](../03-governance/20-非功能需求.md) 的 Runner 沙箱基础上叠加强化,含六个子域:①隔离边界(一次调用一容器/非 root/只读根 FS/seccomp+可选 gVisor/禁提权)、②资源配额(CPU/内存/pids limit + 超时销毁整容器防 DoS)、③网络出口默认零出站 + Manifest 白名单 + 禁直连内部面/云 IMDS、④Secrets 最小注入不落盘 + 输出脱敏、⑤注册准入(依赖受信源白名单防投毒 + 出站声明必填 + 高危人工审批)、⑥审计。
  - `15-PRD-SkillCenter.md` 的 `Skill`/`SkillInvocation` 实体表补 `tenant_id` 列说明,与权威 DDL 对齐。
  - §7 错误处理新增 `RESOURCE_LIMIT_EXCEEDED`、`EGRESS_DENIED`、`DEPENDENCY_UNTRUSTED`,并修正 `INVOCATION_TIMEOUT` 为"销毁整容器"(原"中断子线程"对已 fork 子进程无效)。
- **受影响**:`15-PRD-SkillCenter.md`

### CH-18:核对并纠正 settings 域 DDL "缺失" 的误判

- **背景**:CH-16/CH-17 曾判定 `t_skill`、`t_skill_invocation`、`t_runner_node` 在 `33-数据库Schema设计.md` 中"缺失 DDL"。**该结论为误判**(源于一次错误的 grep 过滤),经逐表核对予以纠正。
- **核对结论**:
  - `t_skill`(§24)、`t_skill_invocation`(§32)、`t_runner_node`(§17)、`t_llm_config`(§17b,CH-16 新补)**均已存在**且带 `tenant_id` + FORCE RLS。
  - `t_skill` 设计优于此前 PRD 表述:`tenant_id` **可空**(NULL=内置全局共享能力,非空=租户私有),命名唯一性由两个条件唯一索引保证(`uq_skill_global_name` / `uq_skill_tenant_name`)。
  - 19-PRD 的 `SystemSecret` 实体对应已有的 `t_workspace_secret`(§5),非独立缺失表。
- **修复**:回改 `15-PRD-SkillCenter.md` 的 `Skill` 表,使 `tenant_id`/命名唯一性表述与权威 `t_skill` DDL 一致(此前误写为 `tenant_id NOT NULL` + 全局改租户内唯一);删除待处理项中错误的"补齐 settings 域 DDL"条目。
- **教训**:判定"某表缺失"前必须以 `grep -n "CREATE TABLE"` 全量列出实际 DDL 逐一核对,不能依赖带过滤条件的部分匹配。
- **受影响**:`15-PRD-SkillCenter.md`、`35-变更记录CHANGELOG.md`

### CH-19:修复共享目录型表(t_skill/t_agent)被 RLS 统一策略隐藏内置能力的漏洞

- **问题(功能性 + 安全性双缺陷)**:§4.2 对"所有含 `tenant_id` 的表"套统一 `FOR ALL USING (tenant_id = current_setting(...)::uuid)` 策略。但 `t_skill`、`t_agent`、`t_agent_prompt_version` 三张表 `tenant_id` **可空**(NULL=平台内置全局共享)。`NULL = uuid` 结果为 NULL(非 TRUE),导致**开箱即用的内置 Skill/Agent 对所有租户完全不可见**——直接违背 §1.2/路径一"内置能力开箱即用"。
- **为何不能简单加 `OR tenant_id IS NULL`**:统一策略是 `FOR ALL`(读写合一),`USING` 在写路径同时充当 `WITH CHECK`。若直接 `OR tenant_id IS NULL`,任意租户即可 `INSERT` 一条 `tenant_id=NULL` 的**伪全局** Skill/Agent 使其对所有租户可见,或篡改/删除他人依赖的内置能力——跨租户投毒。
- **修复(采用多租户 RLS "共享参考数据" 标准范式,读写分离)**:
  - 统一 LOOP **排除**这 3 张共享目录型表(其余 36 张 NOT NULL 表策略不变)。
  - 为 3 张表单独挂策略:`SELECT` 放行 `本租户 OR tenant_id IS NULL`(读到自有+内置共享);`INSERT/UPDATE/DELETE` 的 `USING`/`WITH CHECK` 严格限本租户,**无法创建/改动/删除全局行**。
  - 内置全局行(`tenant_id IS NULL`)**只能由 owner/迁移角色**经 DDL 种子写入;运行期 `qf_app_user`(NOBYPASSRLS)受写策略约束,与 §4.1 "迁移/DDL 由 owner 执行" 一致。含义:平台内置 Skill/Agent 的"安装/升级"走**部署迁移通道**,而非租户运行期 API。
- **受影响**:`33-数据库Schema设计.md`(新增 §4.2 分类说明 + §4.2.1 读写分离策略)

### CH-20:新增工作空间级能力启用关系表(承载内置能力的启用态)

- **背景(CH-19 衍生)**:内置 Skill/Agent 为全局共享行(`tenant_id IS NULL`),其 `status` 字段对所有租户共享,无法表达"某工作空间是否启用该能力"。若租户点"启用"去改全局 `status`,会波及所有租户。
- **粒度定位**:据 UI 证据(`/workspace/:id/skills`、`/workspace/:id/agents`,路径二"当前工作空间内可调用")确定启用态是**工作空间级**,非租户级——修正了 CH-19 待办条目中"租户级"的初判。
- **修复**:`33-数据库Schema设计.md` 新增两张对称关系表:
  - **§24b `t_workspace_skill_enablement`**:`(workspace_id, skill_id)` 唯一,含 `enabled`/`config`/`enabled_by`;`skill_id` 可指向全局或私有 Skill。
  - **§25b `t_workspace_agent_enablement`**:对称结构,`config_override` 承载工作空间对 Agent 的私有覆盖(temperature、system_prompt 增量)。
  - 两表 `tenant_id NOT NULL`,自动纳入 §4.2 标准 FORCE RLS(无需 §4.2.1 特殊处理)。
- **同步**:`15-PRD-SkillCenter.md` §3.1.1 说明改为指向 `t_workspace_skill_enablement`,明确启用态为工作空间级。
- **受影响**:`33-数据库Schema设计.md`、`15-PRD-SkillCenter.md`

---

## 批次六:P2 合理性优化（2026-07-18）

### CH-21:AI 介入点默认自主级别按"可逆性×影响面"重定为默认安全

- **问题**:降级矩阵 9 个介入点大多把 **Level 1(完全自主、直接改资产/写外部系统/控发布闸门,无人工确认)**设为默认态。对企业测试平台,高危动作默认全自主会导致:AI 误判即污染缺陷库(自动提 JIRA)、错误放行/阻断发布(自主门禁)、静默改坏用例库。
- **设计原则(行业最佳实践:高后果动作 human-in-the-loop)**:默认自主级别 = f(动作可逆性 × 影响范围)。
  - **默认 L2(需人工确认)**:写外部系统(提 JIRA)、控发布闸门(阻断/放行 CI/CD)、部署可执行代码(Skill 发布)、改既有资产(用例重构/覆盖率入库)、Workspace 依赖图谱(污染下游)。
  - **默认 L1(可保持自主)**:只读观测上报(运行期异常检测)、可逆且带阈值兜底(Locator 自愈 >0.92 失败回退)、内部编排(Multi-Agent 调度)。
- **机制**:新增 `21-AI介入点降级矩阵.md` §1.x「默认自主级别策略」——默认安全,租户管理员可在设置中对具体介入点**显式上调**到 L1 并承担风险(opt-in 激进);置信度/健康度触发的动态降级(§三)不变。
- **受影响**:`21-AI介入点降级矩阵.md`

### CH-22:删除未落地的 gRPC 声明,服务间通信统一 REST

- **问题**:架构声明服务间"REST/gRPC 混合",但全平台**无任何 `.proto`/端口/服务契约**落地;且与"纯 Python 单语言栈、极低复杂度"的选型基调冲突(引入 gRPC 徒增 IDL/代码生成/调试成本)。
- **决策(用户拍板)**:**删除 gRPC,服务间同步调用统一 REST**(异步仍走 AMQP)。
- **修复**:`31-系统架构设计.md` §3「REST/gRPC 混合」改为「REST(同步)+ AMQP(异步)」;`34-认证授权设计.md` 服务间身份透传说明去掉 gRPC。保留项:SkillCenter 的「HTTP/gRPC 用例」(那是 API Testing Skill 的**被测协议**能力,非平台内部通信)、30-选型中作为**已拒方案**描述的 gRPC sidecar。
- **受影响**:`31-系统架构设计.md`、`34-认证授权设计.md`

### CH-23:澄清 Execution 与 QualityIntelligence 的运行期异常检测职责边界

- **问题**:Execution「AI 运行时劣化观察」与 QI「运行期异常检测/RCA」表述重叠,读起来像两个模块各做一套异常检测。
- **修复(职责切分,非删功能)**:在 `13-PRD-Execution.md` §8 依赖关系明确边界——
  - **Execution = 运行期实时**:只做在线采集(日志/Trace/时延/截图)、基于 3σ 的**实时劣化打标**(`degradation_flag`)与 WebSocket 呈现,**不做**跨用例聚类与代码级归因。
  - **QI = 执行后深度**:消费 Execution 产出的结果集,做失败聚类、代码级 RCA、缺陷提单与发布风险预测。
  - 一句话:Execution 打标"这条变慢了/报错了",QI 回答"为什么、是不是同一根因、要不要提单"。
- **受影响**:`13-PRD-Execution.md`

### CH-24:激进 NFR 指标标注"待压测验证"

- **问题**:部分性能指标(如 >10000 用例报告聚合 <15s、AI 总结 P95<8s、单租户 50000+ 并发 API)在真实 LLM 延迟与数据规模下偏乐观,直接作为硬性验收基线有风险。
- **修复**:`20-非功能需求.md` §一 增加总注——性能指标为**设计目标值(design target)**,须经容量/压力测试(基准+阶梯负载)实测校准后方作为验收 SLA;LLM 相关指标只统计平台侧开销,不含大模型供应商推理耗时。
- **受影响**:`20-非功能需求.md`

---

## 批次七:收尾对齐（2026-07-18）

### CH-25:统一 SystemSecret / WorkspaceSecret / t_workspace_secret 为单一实体

- **问题**:同一张凭证表在三处分叉——19-PRD `SystemSecret`(缺 `tenant_id`/`target_env_id`,字段名 `secret_val_encrypted`)、10-PRD `WorkspaceSecret`、33-Schema `t_workspace_secret`(权威,含 `tenant_id`+`target_env_id`+`secret_value`)。字段集与命名不一致,开发会照哪份写不定。
- **修复**:以 `t_workspace_secret` + 10-PRD `WorkspaceSecret` 为**单一事实源**,回改 19-PRD §3.1.3:补 `tenant_id`/`target_env_id`,字段名 `secret_val_encrypted`→`secret_value`,唯一约束对齐 `(workspace_id, secret_key, target_env_id)`;加注说明三者同一实体。API `POST /settings/secrets` 请求补可选 `targetEnvId`(为空=全局通用)。
- **受影响**:`19-PRD-PlatformSettings.md`

### CH-26:标注 00-审计报告-v2 的过时结论

- **问题**:该报告"跨文档状态一致性:0 处冲突 ✅"已被本轮工作证伪(实测发现实体命名分裂、Workspace 状态枚举冲突、AI 阈值冲突、Saga 双份定义、RLS 隐藏内置能力等)。留着会误导。
- **修复**:报告顶部加**过时警示 banner**,指向本 CHANGELOG;"0 冲突"单元格就地标注 `⚠️ 已过时`,说明其只覆盖核心四件套、未纳入 9 份模块 PRD 的一致性回归。
- **受影响**:`00-设计文档全面审计报告-v2.md`

### CH-27:视觉 AI(Visual/Cognitive Perception)补入 V3 规划

- **问题**:行业 6 大核心能力覆盖 5/6,视觉回归/CV 一直未规划(与 Applitools 类竞品的明显差距),之前仅在报告里"待补充"。
- **修复**:`22-MVP版本规划v2.0.md` V3 Scope 补入——QI 增「视觉回归与多模态缺陷识别」(截图基线 diff + 多模态 LLM 判定布局错乱/文案溢出/元素缺失,过滤动态区域);Skill Center 增内置 `Visual Testing Skill`(截图捕获/像素+感知哈希 diff/基线管理,供自愈与 QI 复用)。定位 V3,不影响 V1/V2。
- **受影响**:`22-MVP版本规划v2.0.md`

---

## 批次八:接口文档统一入口（2026-07-18）

### CH-28:新建 37-API接口总览,裁决路径冲突,补齐端点差集核对

- **问题**:接口文档存在但**散落无统一入口**——机器可读契约在 `32-API规范.yaml`(仅 22 端点)、人读端点表分散在 10~19 各 PRD §6(共 ~43 端点)、实时通道在 36、鉴权在 34。前端不知从何看起;且经差集核对发现 **PRD 声明的 ~30 个端点未进 OpenAPI**、YAML 有 6 个端点未在 PRD 出现、**5 处同一操作两个路径的命名冲突**。
- **修复**:
  - 新建 **`37-API接口总览.md`** 作为前后端联调唯一导航入口:按 9+1 模块索引全部 ~43 REST + 2 WS 端点(标注鉴权/幂等/YAML 覆盖状态);集中沉淀全局约定——`ResponseEnvelope` 信封、分页、JWT/API Key/Runner Token 鉴权、camelCase、幂等键、错误码总表、WebSocket 通道。
  - **裁决 5 处路径冲突**(REST 资源归属原则,定权威+标废弃):C1 心跳归 `/settings/runners/heartbeat`(弃 `/executions/...`);C2 `POST /skills`(弃 `/skills/register`);C3 `POST /agents/{id}/sessions`(弃 `/session/start`);C4 `POST /knowledge/entries`(弃 `/knowledge/upload`);C5 补 `PUT /cicd/configs/{id}`。
  - `02-PRD总纲.md` 技术规范索引新增 37;并修正 30 条目陈述("混合微服务"→"纯 Python")。
- **遗留(下一步)**:约 21 个 🔶 端点待回填进 `32-API规范.yaml` 的请求/响应 schema(路径以 37 冲突裁决为准),回填后覆盖状态全部转 ✅。
- **受影响**:`37-API接口总览.md`(新增)、`02-PRD总纲.md`

### CH-29:全实体 CRUD 矩阵 + 端点表补齐 + YAML 100% 回填

- **问题**:CH-28 只补了差集,但未回答"哪些实体**该**有 CRUD、哪些**绝不该**有写端点"——这是更系统性的设计缺口。盘点 38 个领域实体后发现:
  - **8 个用户管理型实体零端点**(Environment/TestPlan/TestSuite/MockConfig/APIContract/AgentWorkflow/QualityGate/User),前端管理页无接口可调;
  - **15 个实体只有部分端点**(TestCase/Locator/Skill/Agent/PipelineConfig 等缺增改删);
  - 而系统生成型实体(ExecutionResult/TestReport/FailureCluster 等)若被误加写端点,即破坏审计可信度——需显式禁止。
- **修复**:
  - **37 新增 §三 实体 CRUD 策略矩阵**作为端点设计权威判据:按"数据由谁创造"分 4 类——A 用户管理型(需 CRUD)、B 系统生成型(**只读,禁写**)、C 关联子资源(随父资源)、D 平台超管域。矩阵明确标注每个实体的 C/R/U/D 开放度。
  - **37 §二 端点表全面补齐**:从 ~43 端点扩到 **149 REST + 3 WS**。Workspace/Environment/AIContext/Secrets/TestDesign(需求文档 CRUD + 草稿用例 GET/DELETE)/TestAsset(TestCase 完整 CRUD + 版本历史、TestSuite/MockConfig/APIContract/Locator/TestDataProfile 全 CRUD)/Execution(ExecutionPlan CRUD + 任务取消/状态/结果)/QI(报告/失败明细只读 + 诊断核实 + 缺陷导出)/Skill(详情/改/卸载/invoke)/Agent(详情/改/删 + Prompt 激活 + 工作流 CRUD)/Knowledge(条目/基线 CRUD)/CICD(配置详情/删 + 门禁 CRUD)/Settings(LLM/Runner/Secrets/User 完整管理)。
  - **32-YAML 100% 回填**:从 29 ✅ + 120 🔶 补齐到 **149 ✅**。复用已有 43 个 component schemas,统一 CRUD 模板 `$ref`。修正 2 处路径参数命名冲突(`/test-designs/{id}` → `{designId}`、`/agents/sessions/{id}` → `{sessionId}`,对齐同模块具名约定)。校验:37 × YAML 双向 diff **零缺失/零多余**,YAML 通过 `yaml.safe_load` 解析。
- **设计意义**:CRUD 矩阵把"只读实体禁写"这条隐含约束**显式固化**,防止后续给 ExecutionResult 之类误加 POST/PUT/DELETE(那等于伪造测试证据)。这条线本身就是设计正确性的体现。
- **受影响**:`37-API接口总览.md`(§二端点表扩容 + §三新增 CRUD 矩阵 + §七覆盖率 100%)、`32-API规范.yaml`(回填 12 个缺失端点 + 2 处命名修正,行数 2959→~3120)

---

## 待处理项(后续批次)

| 项                                                | 状态      | 说明                               |
| :------------------------------------------------ | :-------- | :--------------------------------- |
| ~~回填端点 schema 进 32-API规范.yaml~~            | ✅ 已完成 | 见 CH-29(149/149 = 100%)           |
| ~~8 个零端点实体 + 15 个部分端点实体补 CRUD~~     | ✅ 已完成 | 见 CH-29 §三 CRUD 矩阵             |
| ~~SystemSecret 与 t_workspace_secret 字段名对齐~~ | ✅ 已完成 | 见 CH-25                           |
| ~~内置 Skill/Agent 的"每租户启用态"关系表~~       | ✅ 已完成 | 见 CH-20(粒度修正为**工作空间级**) |
| ~~高自主 AI 介入点改为可配置成熟度(默认 L2)~~     | ✅ 已完成 | 见 CH-21                           |
| ~~Execution 与 QI 运行期异常检测职责去重~~        | ✅ 已完成 | 见 CH-23                           |
| ~~gRPC 声明未落地~~ / ~~NFR 激进指标待压测标注~~  | ✅ 已完成 | 见 CH-22 / CH-24                   |
| ~~视觉 AI(Visual/Cognitive)模块~~                 | ✅ 已完成 | 见 CH-27(V3 规划)                  |
| ~~`00-审计报告-v2` "0 冲突"结论过时~~             | ✅ 已完成 | 见 CH-26                           |

> 截至批次八(CH-29),API 契约层(37 导航 + 32-YAML schema)已达 100% 覆盖且双向一致。

---

## 批次九：P0 Gate 0 Skill 加固（2026-08-03）

### CH-30：修复 IR 核心链的可绕过门禁，新增需求质量前置 Gate

- **问题**：断言 Coverage 仅以 `PASS` 为分母，`REJECT` 可被排除后得到虚高覆盖率；空需求源、空 IR 和空状态集可通过；状态机的初始态由无序集合隐式选取；推断业务规则的置信度脚本阈值与文档契约不一致。同时，IR 形成前没有可执行的需求质量裁决器。
- **修复**：
  - `coverage-analyzer` 改为按必需 `assertion_id` 与 `PASS/REPAIR/REJECT/UNVERIFIED` 一对一计算；重复、额外或畸形 verdict 不得抬高分子，任一 `REJECT` 或证据错误独立使断言维失败。门禁用未舍入比例比较，空分母默认失败，仅 Strategy 显式声明时为 `NOT_APPLICABLE`。
  - `requirement-compiler` 引入显式源可用性状态；空源/空 IR 拒绝，未提供或不适用的源进入 `PASS_WITH_REVIEW`，不再假设所有源都“满血”可用。
  - `state-machine-builder` 和 `ir-validator` 强制显式 `initial_state`，拒绝空状态集、端点缺失、重复转换和不可达状态。
  - `business-rule-extractor` 统一为推断规则 `confidence > 0.7` 拒绝。
  - `assertion-generator` 同时接受对象包装和 E2E 顶层数组格式，避免合法样例在批量质量检查时崩溃。
  - 所有本批 checker 对非对象根、错误集合/元素类型和不可写输出路径稳定失败，不再以 traceback 中断；IR 版本改为精确 `1.0[.numeric]` 校验并强制六个冻结模型数组；断言必须具备最小可执行比较结构。
  - 新增 `requirement-quality-gate`，对歧义、一致性、可测试性、完整性、NFR 可度量性、角色权限执行确定性裁决。
  - 为上述 Skill 补充标准 `evals.json` 与 P0 回归测试。
- **范围决策**：两组不使用 Skill 的压力基线已能识别显式质量缺陷并完成多源冲突保留，因此本批不新增职责重复的 `requirement-quality-analyzer`；先以 Gate 的误报/漏报评测证明增量价值。
- **受影响**：`prototypes/skills/requirement-quality-gate/`、`requirement-compiler/`、`business-rule-extractor/`、`state-machine-builder/`、`ir-validator/`、`assertion-generator/`、`assertion-verifier/`、`coverage-analyzer/`、`prototypes/skills/tests/`、`11-PRD-TestDesign.md`、`53-需求评审审计方案.md`、`54-项目需求资料总索引.md`。

---

## 批次十：P1 Gate 0 Golden 链闭环（2026-08-03）

### CH-31：补齐剩余核心 Skill 评测入口并建立正向可放行证据

- **问题**：Gate 0 的 `domain-model-extractor`、`strategy-planner`、`scenario-generator`、`test-case-generator` 尚无标准 `evals.json`；场景未校验 `req_id` 是否存在于 IR，用例未校验与绑定场景的需求/规则一致性，也未强制非空步骤和期望结果；策略校验把 auth/payment/permission 当成所有项目的固定关键路径，存在跨领域误报；既有 E2E 只有最终 `GATE_FAILURE` 的负向样例，无法证明完整合法链可以放行。
- **修复**：
  - 领域模型 checker 拒绝空字段集、重复/空白字段名、竞争引用别名、非法引用类型和畸形容器，所有坏输入稳定输出 findings。
  - 策略 checker 改为由项目显式声明 `Critical_Paths`，通过 `IN_SCOPE` 特性绑定或 `OUT_OF_SCOPE` 理由证明处置，不再猜测固定业务关键词；同时校验有限数值、分布和为 1、非空唯一 ID/门禁、disposition 及 mock 集合结构。
  - 场景 checker 同时校验 IR 中的需求与规则绑定，并对畸形 IR transition、facet、场景根和场景项稳定拒绝。
  - 用例 checker 强制 case↔scenario 的 `req_id/rule_id` 一致，且场景自身必须具备完整追踪绑定；同时强制非空步骤与期望结果，并校验步骤端点、显式状态机和期望结构。
  - 四个 Skill 补齐标准 `evals.json`，使 Gate 0 核心 13 个 Skill 全部具备标准评测入口。
  - 新增独立 `prototypes/e2e-validation-golden/`，六个阶段 checker 全部 PASS，Coverage 的 rule/scenario/state/assertion 四维均为 1.0，最终 `GATE_PASS`；原 `prototypes/e2e-validation/` 继续作为负向阻断证据。
- **范围决策**：本批不新增 `nfr-extractor` 或 `business-scenario-modeler`。先用完整正反链和标准 eval 建立现有核心链的可测基线，再依据真实样本的独立增益决定是否扩 Skill 数量。
- **受影响**：上述四个 Skill 的 `SKILL.md`、references、assets、checker 与 evals，`prototypes/skills/tests/`、`prototypes/e2e-validation-golden/`、`54-项目需求资料总索引.md`。

---

## 批次十一：Gate 0 Agent/Skill 运行治理闭环（2026-08-10）

### CH-32：建立最小 Subagent、权限、触发与 Workflow 真相源

- **问题**：项目已有 30 个 Skill 和 Agent Center PRD，但 `.agents/` 无可执行角色定义；缺少 Agent→Skill allowlist、机器身份权限、固定 Gate 0 DAG、触发协议与统一 SOP。PRD 中还存在未注册 Tool 示例和独立 `0.88/0.75` 阈值，容易把“Skill 已存在”误判为“Agent 可任意调用”。
- **修复**：
  - 新增 `55-Agent与Skill运行治理SOP.md`，定义真相源层级、1 Supervisor + 3 Subagent、默认最小权限、触发协议、运行/审批/异常 SOP 与 Given/When/Then。
  - 新增 `prototypes/agent-governance/agents.json`、`gate0-workflow.json` 和 stdlib `validate.py`；只覆盖 Gate 0，不新增运行服务或依赖。
  - `16-PRD-AgentCenter.md` 对齐 V0 边界、Skill allowlist、生成/验证分离、默认零网络/无 Secret，并移除 PRD 自立阈值。
  - `21` 号 AI 治理补充：只有固定 Workflow、最小权限、仅写运行草稿的编排可按 L1；正式资产和外部写入仍为 L2。
  - `34` 号授权增加 Skill/Agent 用户 RBAC，并明确最终权限为用户 RBAC、Agent 权限、Workflow 权限的交集。
- **安全修复**：Agent Trace 从隐藏思维链/CoT 改为 `DecisionSummary` + 证据引用 + 脱敏 Tool I/O，同步术语、领域、API、DB、WebSocket 与 Agent PRD。
- **范围决策**：不新增 `AgentSkillGrant` 数据库实体、消息队列、分布式 Runner 或宿主专用配置；先以机器可读原型和真实 Gate 0 试点验证必要性。
- **受影响**：`AGENTS.md`、`03`、`04`、`16`、`21`、`34`、`35`、`36`、`54`、`55`、`prototypes/agent-governance/`。

---

## 批次十二：开发准入前主线决策裁决（2026-08-11）

> 本批次针对 2026-07-30 独立审计中标注"未处理"的两个 Critical（C-6 角色定义矛盾、C-3 自治等级冲突）进行源文档层修订，解锁 RBAC、审批流、AI 介入点的编码路径。**审计签字关闭待 L1 一致性复扫**，本次为源文档修订。

### CH-33：裁决角色模型——"用户只有一个"修订为四角色矩阵（C-6）

- **问题**：`02-PRD总纲` §四"核心设计原则"声明"用户只有一个"，但 `16-PRD-AgentCenter`（审批人）、`18-PRD-CICD`（平台管理员）、`19-PRD-PlatformSettings`（LDAP/GitHub 组织权限、多租户）、`10-PRD-Workspace`（Tenant 实体 + RLS）、`04-核心领域模型`（User/Tenant/ownerId/assignedDeveloperId）、`34-认证授权设计`（RBAC 三角色矩阵）、`55-Agent与Skill运行治理SOP`（RBAC 权限审批人）客观存在多角色。这是全平台一致性缺陷的单点根源（C-6）。
- **修复**：
  - `02-PRD总纲.md` §四：将"用户只有一个"修订为"多角色协作，测试工程师为核心"，明确 4 种角色（Tester / Approver / TenantAdmin / PlatformAdmin），测试工程师为主要使用者，但审批流、平台运维、多租户隔离需要其他角色；引用 `04` 领域模型和 `34` RBAC 为权威源。
  - `19-PRD-PlatformSettings.md` §1.1：将"剔除了角色权限矩阵，专门面向测试工程师角色"修订为"服务全部 4 种角色，用户偏好面向 Tester 轻量化，租户/平台级配置由 TenantAdmin / PlatformAdmin 管理"。
- **未改动**：`04`、`32`、`33`、`34` 已是多角色/多租户的权威定义，无需修改。
- **受影响**：`02-PRD总纲.md`、`19-PRD-PlatformSettings.md`
- **依据**：`04-核心领域模型`（User/Tenant/ownerId/assignedDeveloperId）、`34-认证授权设计`（RBAC 三角色矩阵）、`55-Agent与Skill运行治理SOP` §7.6（RBAC 权限审批人）

### CH-34：统一 TestDesign/QI 自治阈值到 21 号矩阵（C-3）

- **问题**：`21-AI介入点降级矩阵` §一·补"默认自主级别策略"已确立 Safe-by-default 原则（TestDesign 默认 L2、QI 写 JIRA 默认 L2），但下游 PRD 未遵从：
  - `11-PRD-TestDesign` §5.3 Level 1 写"AI 自动生成完整用例列表"，§5.4 写"置信度 > 0.80 ... 批量自动入库"——违反 21 号"Test Design 默认 L2，入库前须人工终审，禁止静默合成入库"。
  - `14-PRD-QualityIntelligence` §5.3 写"L1 自动模式 置信度≥0.90 自动写入数据库"，§5.4 写"自动分类 0.90 / 一键提单 0.85"——与 21 号"QI 写 JIRA 默认 L2、矩阵阈值 >0.85"冲突。
  - `19-PRD-PlatformSettings` §5.3/5.4 的 Token Router 0.90 阈值——21 号矩阵未列此介入点，属散落。
- **修复**：
  - `11-PRD-TestDesign` §5.3/5.4：Level 1 改为"能力边界描述（默认不启用，需 TenantAdmin opt-in）"，新增"默认级别 L2"声明；删除"批量自动入库"，改为"入库须人工终审"；0.80 保留为置信度下限（低于触发重生成，高于仍为草稿态需人工确认）。
  - `14-PRD-QualityIntelligence` §5.3/5.4：Level 1 改为能力边界描述，新增"默认级别 L2"声明；阈值从 0.90 对齐到 21 号矩阵的 0.85；"一键提单"明确为 L2 动作（须人工确认后提交）。
  - `19-PRD-PlatformSettings` §5.3/5.4：明确 LLM 网关路由"不是 AI 介入点，不参与自治分级"，0.90 标注为"网关内部路由置信度"（技术降级参数），路由决策的自治级别由下游介入点继承，本模块不自立阈值。
- **未改动**：`21` 号矩阵自身（已是权威源）、`16-PRD-AgentCenter`（CH-32 已对齐）。
- **受影响**：`11-PRD-TestDesign.md`、`14-PRD-QualityIntelligence.md`、`19-PRD-PlatformSettings.md`
- **依据**：`21-AI介入点降级矩阵` §一·补"默认自主级别策略"、§二"全模块 AI 介入点降级矩阵"
- **注**：审计 B-4（AI 阈值散落无校准）中"校准集缺失"部分仍未处理，与本批次正交，可与开发并行。

---

## 批次十三：P0 技术契约补齐（2026-08-11）

> 本批次补齐评审报告中识别的 4 个 P0 技术阻塞项（审计表缺失、Alembic 迁移约定缺失、LangGraph Agent 编排图缺失、错误码未契约化），使技术契约达到"可驱动开发"的颗粒度。

### CH-35：新增 `t_audit_log` 表 DDL + append-only 权限规范

- **问题**：[31 系统架构设计](31-系统架构设计.md) Saga 补偿（含 `Saga-Correlation-ID`）、[34 认证授权设计](34-认证授权设计.md) 越权探测、[21 AI 介入点降级矩阵](../03-governance/21-AI介入点降级矩阵.md) opt-in 配置变更记录全部依赖审计日志表，但 `33` 号 Schema 的 50 张表中没有 `t_audit_log`。这是安全合规与分布式事务留痕的硬阻塞。
- **修复**：
  - `33` 号 Schema 新增 §3.7 审计与合规日志，定义 `t_audit_log` 表（13 字段：actor_id/actor_type/action/resource_type/resource_id/result/ip_address/user_agent/saga_correlation_id/request_id/detail/created_at + tenant_id），含 5 个索引（租户+时间、资源、操作者、Saga 链路、动作）。
  - §4.1 新增 `REVOKE UPDATE, DELETE ON t_audit_log FROM qf_app_user`，保证 append-only（应用角色仅 INSERT + SELECT）。
  - §4.2 纯租户数据表计数从 36 张更新为 37 张（含审计表）。
  - §3.7 附写入规范：敏感字段脱敏、Saga 留痕（action=SAGA_COMPENSATE）、AI 治理变更（action=AI_AUTONOMY_OPT_IN）、越权探测（result=DENIED）。
- **受影响**：`33-数据库Schema设计.md`
- **依据**：`31` Saga 补偿要求、`34` 越权探测、`21` opt-in 记录、`20` 非功能需求审计日志

### CH-36：业务错误码契约化进入 32-YAML

- **问题**：`37` 号 API 接口总览 §五的错误码总表（16 条业务错误码）仅在 Markdown 中，`32-API规范.yaml` 的 `ResponseEnvelope.code` 是无约束 `string` 类型，无 enum。前后端联调时错误处理无法契约化，存在漂移风险。
- **修复**：
  - `32-YAML` 的 `ResponseEnvelope.code` 新增 `enum`（16 值：OK / VALIDATION_FAILED / UNAUTHORIZED / FORBIDDEN / NOT_FOUND / IDEMPOTENCY_CONFLICT / ERR_DESIGN_APPLY_CONFLICT / ERR_EXEC_MAX_RETRY_EXCEEDED / RESOURCE_LIMIT_EXCEEDED / EGRESS_DENIED / DEPENDENCY_UNTRUSTED / INVOCATION_TIMEOUT / LLM_AUTH_FAILED / DECRYPTION_FAILED / DATA_SOURCE_MISSING / HEARTBEAT_TIMEOUT），与 37 号总表逐条对齐。
  - `32-YAML` 的 `components.responses` 新增 10 个业务错误码可复用响应（IdempotencyConflict / DesignApplyConflict / ExecMaxRetryExceeded / ResourceLimitExceeded / EgressDenied / DependencyUntrusted / InvocationTimeout / LlmAuthFailed / DecryptionFailed / DataSourceMissing），每个用 `allOf` 继承 ResponseEnvelope 并约束 `code` enum 到具体值。
  - YAML 经 `yaml.safe_load` 解析通过，可复用响应总数从 5 增至 15。
- **受影响**：`32-API规范.yaml`
- **依据**：`37-API接口总览.md` §五错误码总表

### CH-37：新增数据库迁移与种子数据约定（38 号文档）

- **问题**：`30` 号技术选型点名 Alembic，`33` 号 Schema 给了 51 张表 DDL，但迁移目录结构、命名约定、env.py 模板、初始迁移分组策略、种子数据加载方式全部空白。开发第一步就是建库，这是硬阻塞。
- **修复**：新增 `38-数据库迁移与种子数据约定.md`，定义：
  - 目录结构（`migrations/versions/` + `env.py` + `script.py.mako`）。
  - 命名约定（`YYYYMMDD_NNNN_<描述>.py`，revision ID 不复用）。
  - 初始迁移分组策略（12 个 revision：8 个域 DDL + 1 个审计表 + 1 个 RLS + 2 个种子）。
  - env.py 异步 engine 配置（owner 角色执行，绕过 RLS）。
  - 种子数据原则（仅 `tenant_id IS NULL` 全局行走种子迁移；租户级数据走运行期 CLI）。
  - 内置 Skill/Agent 种子来源映射（`prototypes/skills/` 29 个 → t_skill；`prototypes/agent-governance/agents.json` 4 个 → t_agent）。
  - 种子迁移模板（`ON CONFLICT DO NOTHING` 幂等 + `WHERE tenant_id IS NULL` 安全 downgrade）。
  - 约束门禁（禁止 autogenerate 直接入库、数据迁移与 DDL 分离、种子不可重复修改）。
- **受影响**：新增 `38-数据库迁移与种子数据约定.md`
- **依据**：`30-技术选型决策.md`（Alembic）、`33-数据库Schema设计.md` §4.2.1（内置全局行只能由 owner 写入）

### CH-38：新增 LangGraph Agent 编排架构（31 号 §6）

- **问题**：`agent-service` 承载自愈、智能设计、RCA 等核心工作流，`30` 号点名 LangGraph，但全仓库无 Agent DAG / 状态机编排图。节点、状态、工具挂载点、HITL 卡点、降级分支全靠文字描述，开发无法确定实现边界。这是 AI 原生平台的"灵魂"部分。
- **修复**：`31` 号系统架构设计新增 §6 Multi-Agent 编排架构（LangGraph）：
  - §6.1 选型理由（条件分支 + HITL 中断 + 状态持久化 → 用图而非链）。
  - §6.2 Gate 0 编排拓扑（Mermaid DAG 图：13 节点，Supervisor + 3 Subagent 四泳道，完整裁决路由 PASS/REJECT/BLOCK_HUMAN）。
  - §6.3 LangGraph State 定义（Gate0State TypedDict + 条件路由函数代码）。
  - §6.4 HITL 中断与恢复（interrupt_before + checkpointer + thread_id 恢复代码）。
  - §6.5 降级与异常处理表（REJECT/超时/循环/LLM 不可用/生成者-验证者冲突）。
  - §6.6 后续工作流占位（自愈/RCA/回归 V1+ 待设计，当前不预实现）。
- **受影响**：`31-系统架构设计.md`
- **依据**：`55-Agent与Skill运行治理SOP.md`（1 Supervisor + 3 Subagent 模型）、`prototypes/agent-governance/gate0-workflow.json`（13 节点 DAG）、`21-AI介入点降级矩阵.md`（自治级别约束）

---

## 批次十四：L1 复扫遗留 Critical 修复（2026-08-11）

> L1 一致性复扫（`docs/05-audits/current/L1-一致性复扫报告-2026-08-11.md`）发现 L1-001~003/005/006 + C-3/C-6 均已关闭，唯一遗漏的 Critical L1-004 在本批次修复。

### CH-39：TestPlan 补 RequirementDocument 外键（L1-004 / C-1）

- **问题**：L1 一致性复扫发现 `t_test_plan` 表无 `requirement_document_id` 外键，无法从测试计划回溯到需求文档，破坏正向追踪性（RTM Forward）。总裁决报告（2026-07-30）§3.2 列为待修行动项，但 CH-29 ~ CH-38 均遗漏此项。
- **修复**：
  - `33-数据库Schema设计.md` `t_test_plan` 新增 `requirement_document_id UUID REFERENCES t_requirement_document(id) ON DELETE SET NULL`（SET NULL 因计划可脱离需求独立存在）+ 部分索引。
  - `04-核心领域模型.md` §4 TestPlan 字段表新增 `requirementDocumentId`（VARCHAR(36), FOREIGN KEY, NULLABLE）。
  - `32-API规范.yaml` TestPlan schema 新增 `requirementDocumentId`（string, uuid, nullable）。
- **受影响**：`33-数据库Schema设计.md`、`04-核心领域模型.md`、`32-API规范.yaml`
- **依据**：L1-一致性复扫报告-2026-08-11.md §一 L1-004、总裁决报告 §3.2 C-1 行动项
- **验证**：L1 复扫报告已更新，L1-004 状态从"仍开放"改为"已关闭"。L1 层面所有 Blocker + Critical 清零。

---

## 批次十五：功能模块重构权威源同步（2026-08-11）

> 本批次依据`05-功能模块重构方案.md`已完成的Gate A/B/C产品裁决，开始Gate D权威契约同步。此前审计结论保持时间点原文；本批次写入文档不等于Gate E独立复审通过。

### CH-40：重写术语表与核心领域模型（Gate D1）

- **问题**：现行`03`仍以旧9模块为权威，`04`仍包含TestDesignPlan、可写AIContext、通用BaselineItem、单Endpoint APIContract、单用例AutomationScript、Jira耦合FailureCluster和粗粒度角色等已被产品裁决否定的模型。继续在其上修改API/DB会扩大双写和语义冲突。
- **修复**：
  - `03-术语表Glossary.md`重写为8个一级模块，明确“项目=Workspace”、Release、八类正式产出物、稳定领域名、页面名、废弃别名、审核策略、RBAC职责和核心状态。
  - `04-核心领域模型.md`按8个唯一业务Owner重构，定义WorkItem/Review、Source/APIContract版本、TestStrategy/TestPlan、自动化代码版本、执行证据、Defect、报告、Agent治理和作用域RBAC聚合。
  - 正式产出物统一为“稳定身份+不可变版本”，审核绑定精确versionId+contentDigest；ExecutionResult不可被分析反写；Agent不能批准正式产出物。
  - TestDesignPlan、AIContext和BaselineItem退场并保留legacyRef/Source Trace迁移；Runner统一为RunnerNode；FailureCluster移除Jira字段；manualVerified改为正式ReviewTask。
  - 补WorkItem、Release、Defect、APIContractVersion、AutomationScriptVersion、ResultAnalysis、RoleBinding等状态机和关键约束。
- **受影响**：`03-术语表Glossary.md`、`04-核心领域模型.md`、`05-功能模块重构方案.md`
- **兼容结论**：当前无应用代码、生产数据或已发布客户端，不保留运行时双写实体；旧名只保留于迁移表、历史审计和CHANGELOG。
- **验证**：两份Markdown连续表格列数检查通过；无TODO/TBD/file URL占位。API/DB、治理和下游PRD尚未同步，Gate D/Gate E仍未完成。

### CH-41：重写OpenAPI与数据库Schema（Gate D2核心）

- **问题**：旧`32/33`仍按Workspace/TestDesign/TestAsset/Intelligence/CI-CD/Settings路径族和51张可变实体表组织，缺WorkItem、Release、正式产出物版本、Defect、APIContract版本/基线、作用域RBAC等目标契约，并存在单用例脚本、Jira字段耦合和布尔审核等冲突。
- **修复**：
  - `32-API规范.yaml`更新为OpenAPI 3.0.3、`2.0.0-draft`，按8个Owner提供71个资源路径、94个operation和63个公开Schema（含WebSocket一次性票据接口）。
  - 新API增加`/work-items`、`/review-tasks`、`/knowledge/api-contracts`、`/test-strategies`、`/automation/scripts`、`/quality/defects`、`/ai/*`、`/platform/*`等标准资源；移除旧设计稿路径族。
  - 写操作统一Idempotency-Key，高价值动作绑定精确版本/摘要；Defect外部同步拆为逐条sync-attempt；Secret响应不返回明文。
  - `33-数据库Schema设计.md`按8个业务域重写为104张目标表，覆盖稳定根/不可变版本、WorkItem/Review、Source Trace、APIContract、Automation、Execution证据、Defect、Agent Eval及RBAC治理。
  - 所有tenant表要求FORCE RLS；15类审计/结果/Trace表撤销应用UPDATE/DELETE；稳定根版本指针在版本表建立后统一补FK。
- **受影响**：`32-API规范.yaml`、`33-数据库Schema设计.md`
- **兼容结论**：当前无已发布客户端/生产数据，直接替换设计契约，不实现旧路径或旧表双写；映射保留在05、33迁移表和CHANGELOG。发现真实消费者时另行建立限期适配。
- **验证**：
  - OpenAPI YAML解析通过：71 paths、94 operations、63 schemas；operationId无重复/缺失；组件引用无缺失。
  - DB静态检查：104个CREATE TABLE均唯一；356个REFERENCES均存在且按文档执行顺序无前向依赖；SQL代码块闭合；Markdown表格列数一致。
- **未完成**：36/37/38技术配套、21/34/55治理、PRD和原型仍待同步；本项不是Gate E验收结论。

### CH-42：同步实时、API导航与数据库迁移契约（Gate D2配套）

- **问题**：`36/37/38`仍引用旧`/executions`、`/agents`、51张表、29个Skill及旧业务分组，且WebSocket缺少资源绑定的一次性鉴权入口；继续保留会使研发从说明文档实现出第二套契约。
- **修复**：
  - `36-WebSocket实时契约.md`重写为ExecutionTask、WorkItem、Agent Trace、Workspace四类流，采用一次性短时资源绑定票据，禁止通过WebSocket执行批准、发布、Defect外部同步等高价值命令。
  - `32-API规范.yaml`新增`POST /auth/ws-tickets`及`WebSocketTicketCreate`，契约规模更新为71 paths、94 operations、63 schemas。
  - `37-API接口总览.md`按8模块重写操作导航、错误码、旧路径迁移和静态验收边界，与32号机器契约一致。
  - `38-数据库迁移与种子数据约定.md`按104张目标表重写15步首建链，补稳定根指针、全量RLS、只追加权限、RBAC/ReviewPolicy、30个Skill和Gate 0 Agent种子约束。
- **受影响**：`32-API规范.yaml`、`36-WebSocket实时契约.md`、`37-API接口总览.md`、`38-数据库迁移与种子数据约定.md`
- **验证**：三份Markdown连续表格列数检查通过，未发现file URL、TODO/TBD、51张表或29个Skill旧口径；OpenAPI解析、operationId唯一性和Schema引用检查通过。
- **限制**：这是目标技术契约的静态一致性，不代表WebSocket、API或Alembic工程已经实现和运行。

### CH-43：统一AI自治、作用域授权与Gate 0运行治理（Gate D3）

- **问题**：旧21号矩阵仍按9个旧模块组织，允许TenantAdmin把正式资产入库、外部写入和质量门禁上调为全自动，并散落多个未校准阈值；旧34号只定义3个粗粒度角色且让管理员具备业务批准；Gate 0缺TestPlan产出、精确版本审核绑定和机器可检验的humanOnly约束。
- **修复**：
  - `21-AI介入点降级矩阵.md`按L0-L3重构：L2受限代理为默认产品模式，L3仍保留正式审核/外部写入/签署/门禁人工硬门；新增8模块20个介入点和基于Eval证据的版本化校准治理，删除管理员绕过底线的opt-in。
  - `34-认证授权设计.md`重构为User/Service/Agent/APIKey/WebSocketTicket身份、平台/租户/Workspace/资源四级RBAC、6个内置角色模板、humanOnly权限、ReviewPolicy授权算法、RLS和Secret安全。
  - `55-Agent与Skill运行治理SOP.md`把Gate 0扩展为“需求→策略→计划→用例→审核”，明确14个Skill、ReviewTask精确版本/摘要绑定、管理员不自动获得业务批准。
  - `agents.json`和`gate0-workflow.json`升级到schemaVersion 2.0，新增L2默认、权限交集、humanOnly动作、TestPlan节点、不可变产出与正式产出物ReviewTask策略。
  - `validate.py`新增上述治理约束检查。
- **受影响**：`21-AI介入点降级矩阵.md`、`34-认证授权设计.md`、`55-Agent与Skill运行治理SOP.md`、`prototypes/agent-governance/agents.json`、`gate0-workflow.json`、`validate.py`
- **验证**：JSON解析通过；治理验证器返回`PASS: 4 agents, 14 Gate 0 skills`，并确认DAG无环、默认零网络、无Secret、正式批准humanOnly、审核绑定精确版本与摘要；三份Markdown表格结构检查通过。
- **限制**：30个Skill中仅20个有标准eval；治理配置通过不代表Agent运行时或业务正确率已经验证。

### CH-44：重写产品总纲、八模块PRD与版本规划（Gate D4）

- **问题**：01/02/10-19/22/54仍以旧9模块+平台设置为产品结构，把Workspace当业务模块、TestAsset混合用例/代码/契约、CI/CD独立成模块，并保留无基线性能/收益数字和AI高分自动入库路径。
- **修复**：
  - 01/02按“AI主生产、测试人员主审核和总体把控”重写产品定义、用户、八模块、正式产出物、核心旅程和度量方法。
  - 10-17在保留历史文件名的前提下重写为任务看板、知识与契约、测试规划与设计、自动化工作台、测试执行、质量中心、AI Agent中心、平台管理8份现行PRD。
  - 每份现行PRD补Owner边界、AI/人工分工、正式产出/事实、异常降级和Given/When/Then；18/19改为旧CI/CD与平台设置迁移说明，不再计作一级模块。
  - 22改为V0设计准入、V1单Workspace闭环、V2团队协同、V3企业规模路线，删除无工作负载/基线的预设并发、延迟和收益承诺。
  - 54重写权威源、8模块、技术/治理、原型和审计导航。
- **受影响**：`01-产品功能地图v2.0.md`、`02-PRD总纲.md`、`docs/02-prd/10-19`、`22-MVP版本规划v2.0.md`、`54-项目需求资料总索引.md`
- **验证**：上述Markdown连续表格列数检查通过；旧模块词只保留在兼容文件名、迁移说明或明确废弃映射中。

### CH-45：同步NFR、架构、体验与E2E/Skill原型（Gate D5）

- **问题**：20/30/31/53和线框仍引用AIContext、旧服务/路径、9模块和未经实测的硬指标；E2E样例仍把`confidence>0.80`自动入库作为成功路径；`hitl-gatekeeper`和`business-rule-extractor`仍内置通用置信阈值影响路由。
- **修复**：
  - 20重写为需基线/工作负载/口径的可验收NFR；30选择模块化单体优先和待Spike技术；31按8模块、事实/推断/决定分层、WorkItem/ReviewTask和Agent/Runner边界重写。
  - 53审计范围改为8模块、迁移说明、71 API paths、104目标表及30 Skill动态盘点；页面地图/UIUX计划改为8模块和任务/审核主流程，Drawio更新现行模块/策略标签。
  - Gate 0正向样例重建为TestCaseVersion精确摘要人工审核链，重新生成报告后IR/Scenario/Assertion均PASS、Case为PASS_WITH_REVIEW、Coverage为GATE_PASS。
  - 负向样例把高分自动入库改为Agent审批应被FORBIDDEN，保留Coverage GATE_FAILURE作为预期阻断证据。
  - `hitl-gatekeeper`移除0.7/0.9通用阈值和抽样自动PASS，八类正式产出物始终BLOCK_HUMAN并要求artifact/version/digest/policy绑定；`business-rule-extractor`改为推断规则无论分数均NEED_HUMAN_REVIEW。
- **受影响**：`20`、`30`、`31`、`53`、`docs/06-wireframes`、`prototypes/e2e-validation*`、`domain-model-extractor`、`hitl-gatekeeper`、`business-rule-extractor`、`strategy-planner`
- **验证**：Golden链6个报告结果符合预期；负向链最终Coverage=`GATE_FAILURE`；Agent治理验证仍PASS；相关Python和JSON可解析。
- **限制**：原型检查证明的是样例/结构，不是运行时业务正确率；仍有10个Skill缺标准eval，需在开发准入审计中列为开放项。

### CH-46：Gate E静态复审修正

- **问题**：最终跨契约复验发现ExecutionTask调度状态与ExecutionResult业务结论曾在质量PRD中混用；RequirementDocumentVersion解析初始态被误写为`PENDING`；KnowledgeEntryVersion缺`agentRunId`；三组包含可空列的业务唯一键在PostgreSQL默认NULL语义下可被重复插入；Golden E2E两个用例未绑定状态机，使文档声明的全零退出与实际`PASS_WITH_REVIEW`退出1不一致。
- **修复**：
  - 14号PRD明确ExecutionTask=`PENDING/QUEUED/RUNNING/COMPLETED/FAILED/CANCELLED/TIMED_OUT/BLOCKED`，ExecutionResult=`PASSED/FAILED/SKIPPED/ERROR/INCONCLUSIVE`。
  - `03/04/32/33`将RequirementDocumentVersion解析状态对齐为`DRAFT/PARSING/COMPLETED/FAILED`，并与审核状态分字段。
  - `t_knowledge_entry_version`补`agent_run_id`，使八类正式版本均可追溯AI参与运行。
  - Secret、IntegrationConfig和ExecutionResult的可空复合业务键改用PostgreSQL 16 `UNIQUE NULLS NOT DISTINCT`。
  - 修复`knowledge-memory`、`locator-discovery`、`performance-test-generator`和`plan-orchestrator`中与现行原型资产不一致的eval测试器。
  - Golden E2E的`TC-rv-101/103`补精确状态机实体绑定，用例检查由`PASS_WITH_REVIEW`改为`PASS`，不改变正式产出物仍必须人工审核的业务规则。
- **受影响**：`03`、`04`、`14`、`32`、`33`以及4个Skill eval测试器。
- **验证**：57个原型单元测试全部通过；14个eval运行器全部通过；Agent治理验证返回`PASS: 4 agents, 14 Gate 0 skills`；Golden链6步均退出0且Coverage=`GATE_PASS`；负向链前5步退出0、Coverage退出2且=`GATE_FAILURE`；OpenAPI YAML、DB引用与原型JSON静态检查通过。
- **开放项**：OpenAPI仍大量使用通用对象/列表响应，10个Skill仍缺标准eval，且尚无真实API、PostgreSQL、Agent运行时和浏览器E2E证据；详见同日现状独立复审报告。

### CH-47：完成Gate E当前态复审

- **新增**：`docs/05-audits/current/现状独立复审报告-2026-08-11.md`，从现行文件和可重跑原型重新检查，不改写旧审计结论。
- **裁决**：8模块、Workspace作用域、8类正式产出物、L2默认模式和人工硬门可冻结；允许启动一条纵向切片Spike，不允许全量并行开发或宣称产品验收。
- **开放**：94个operation中73处成功响应仍为Generic；10个Skill缺标准`evals/evals.json`；104表DDL、RLS、API、Agent和Runner均无真实运行证据。
- **导航**：54号总索引已链接新报告并更新当前状态；37号API总览已更新为71 paths / 94 operations / 64 schemas。

### CH-48：完成Stage 3 planning工程纵向切片

- **目标**：按8月11日复审推荐，依次完成API响应契约收敛、30个Skill eval标准化，以及“需求版本→策略→计划→用例→人工审核”的最小可运行闭环。
- **API契约**：OpenAPI更新为72 paths / 96 operations / 75 schemas；需求、策略、计划、用例和AgentSession相关17个operation改用具体成功响应Schema，并新增AgentSession创建/查询契约。官方OpenAPI validator通过；全契约仍有58处Generic成功响应。
- **Skill eval**：30/30 Skill均具有标准`evals/evals.json`；统一入口发现103个eval case并运行14个确定性runner。该结果不等于真实模型效果评测。
- **参考运行时**：新增FastAPI单进程参考实现，覆盖需求及版本、WorkItem、AgentSession/Trace、策略、计划、用例版本和ReviewTask；生成资产使用不可变版本与SHA-256摘要绑定，状态停在`PENDING_REVIEW`/`PAUSED_FOR_HUMAN`，仅UserIdentity可作审核决定。
- **安全边界**：缺失身份fail-closed；租户隔离、产物摘要、能力和幂等键均校验；Agent审批被拒绝；异常响应不返回堆栈。参考生成器不读取模型Secret。开发身份请求头不是生产认证。
- **验证**：Ruff、Mypy、10项Pytest、OpenAPI官方校验、30套Skill eval、治理结构验证和Uvicorn启动冒烟均通过。
- **未完成**：状态仍为单进程内存；尚无PostgreSQL持久化/RLS实测、生产JWT/OIDC、真实模型适配、通用Agent/Runner平台和浏览器E2E。Stage 4应继续验证同一闭环，不横向铺开新模块。

### CH-49：完成Stage 4本地SQLite审核纵向切片

- **决策**：个人电脑暂不安装PostgreSQL，也暂不接真实模型；用SQLite、本地JWT、确定性Provider和浏览器审核工作台验证同一闭环。目标PostgreSQL契约保留为团队/生产Profile。
- **实现**：SQLite schema v2持久化planning与本地身份；应用层强制tenant/workspace作用域；本地账号使用scrypt，JWT使用HttpOnly Cookie、CSRF、限流和请求时成员资格复查；`deterministic-local@1.0.0`生成策略、计划和正反用例；React工作台展示精确版本、摘要、Provider、Trace和人工决定。
- **契约**：OpenAPI更新为78 paths / 102 operations / 80 schemas，当前运行时实现22个operation；补本地认证和精确审核产物读取契约。
- **验证**：Ruff、严格Mypy、10项Pytest、OpenAPI官方validator、前端生产构建、npm生产依赖审计、30套Skill eval和Agent治理验证通过。真实浏览器完成初始化、生成、四项人工批准、服务重启后登录与数据恢复，最终0项待处理、Session=`COMPLETED`、控制台0错误。
- **边界**：SQLite没有原生RLS、目标并发和PGVector；本地JWT不是OIDC/MFA；确定性Provider不是模型效果证据；仍不得宣称八模块完整开发或产品验收。

### CH-50：完成功能模块重构文档收口

- **问题**：05号方案页头、Gate D/E和后续步骤仍停留在“待同步”时点；现行资料同时使用“知识与契约/知识库、测试规划与设计/测试策划与设计、自动化工作台/自动化测试开发、质量中心/质量分析与缺陷”两套展示名；组件库还用未经校准的0.70/0.85固定阈值渲染可信等级。
- **修复**：05号更新为Gate D已完成、Gate E静态复审已通过，并把全量运行时证据保留为版本验收项；所有非历史现行产品、PRD、治理、架构导航和线框统一采用03号术语表的四个规范展示名；ConfidenceBadge删除通用阈值，未校准分数只能中性展示且不得参与决策。
- **兼容**：英文领域名、API前缀、数据库Owner、状态、历史PRD文件名和历史审计原文均不变；本次不引入运行时接口或数据迁移。
- **验证要求**：现行资料旧展示名零命中（明确历史/迁移材料除外）；Markdown表格与本地链接通过；OpenAPI、后端、前端、Skill eval和Agent治理回归不得退化。

### CH-51：新增独立平台评审Agent治理平面

- **目标**：增加一个独立于Gate 0生产Agent的测试平台评审角色，对平台本身进行跨产品、需求、架构、契约、安全、AI治理、可测试性、体验和验收证据评审，避免生产角色参与建设后再自我评价。
- **设计**：新增`qf-platform-reviewer`独立配置和固定只读Workflow；不加入`agents.json`、不接受Supervisor委派、不调度生产Agent，网络deny-all、无Secret、无外部写入，只能在独立`platform-review-runs/{reviewRunId}`目录输出咨询性Finding与报告。
- **职责分离**：评审输入必须为带路径、摘要、排除项的冻结快照；评审Agent不能修改文档、源码、测试或证据，不能整改/关闭Finding，也不能替代UserIdentity处置报告或批准平台验收。
- **复用边界**：只读复用`quality-governance`和`contract-drift-detector`；前者校验指标与治理报告诚实性，后者仅在存在声明/观察快照时检查契约漂移，均不获得修复权。
- **受影响**：`03`术语表、`04`领域模型、`16`号PRD、`21`号矩阵、`55`号SOP，以及`platform-review-agent.json`、`platform-review-workflow.json`、`validate.py`。
- **实施边界**：本轮交付机器可读治理原型和结构验证，不接真实模型、不声称已完成模型评审效果或平台产品验收。

---

## 批次十六：B2 裁决整改与批次 1 执行（2026-08-14）

> 依据:8-13 需求评审 48 条台账 + 8-14 B2 裁决(11 项全部按推荐方案)+ 修复方案 v2.0(QF-FIX-2026-0814)。
> 本轮执行批次 1 全部文档修订,验证门禁:逐条打勾 + grep 证据 + OpenAPI validator PASS。

### 一、QF-REQ-001 WorkItem 字段补齐(阻断,6/6 打勾)

- **问题**:acceptanceCriteria/constraints/agentId 三字段在 04/32/33 缺失(8-13 仅补 objective/requiresReview/lockVersion)。
- **修复**:04 §3.1 字段表补 3 行;32 WorkItem/WorkItemCreate required+properties 补 3 字段(acceptanceCriteria 必填);33 t_work_item 补 acceptance_criteria/constraints/agent_id 三列。
- **验证**:grep 三源各≥1;对照整改建议 6/6 打勾。
- **受影响**:`04-核心领域模型.md`、`32-API规范.yaml`、`33-数据库Schema设计.md`。

### 二、B2-1 CoverageReport 拆分(严重)

- **裁决**:设计覆盖分析(需求→用例映射)归 12 号中间产物;CoverageReport 为执行覆盖报告,唯一写入归 15 号。
- **修复**:12-PRD AC-03 改写为"覆盖分析分母透明";15-PRD §2 补 CoverageReport 产出物行、§3 补覆盖能力行、§4 补语义规则;05 §5.12.7 CoverageReport 行加注;04 CoverageReport 实体加注。
- **受影响**:`12-PRD-TestAsset.md`、`15-PRD-SkillCenter.md`、`05-功能模块重构方案.md`、`04-核心领域模型.md`。

### 三、B2-2 ContractCheckResult 承接(严重)

- **修复**:14-PRD §2 补契约检查功能行、新增 AC-05(四态事实留存,未检查不计通过);15-PRD §4 补 TestReport 契约检查披露字段;32 新增 ContractCheckResult/APIObservation schema。
- **受影响**:`14-PRD-QualityIntelligence.md`、`15-PRD-SkillCenter.md`、`32-API规范.yaml`。

### 四、B2-3 AI 校准记录载体(严重)

- **修复**:33 新增 t_calibration_record(9 字段+索引);32 新增 /ai/calibrations 注册/查询端点 + CalibrationRecord/CalibrationRecordCreate schema;16-PRD §2 Eval 行补校准引用(无有效校准记录不驱动自治)。
- **受影响**:`33-数据库Schema设计.md`、`32-API规范.yaml`、`16-PRD-AgentCenter.md`。

### 五、QF-REQ-005 核心链响应契约收敛(严重)

- **动作**:核心链 5 模块(TestPlanning/Execution/Quality)23 个 operation 从 Generic 响应切换为专用响应;新增 18 个核心实体骨架 schema(TestingIR/TestScenario/TestSuite/ExecutionPlan/ExecutionPlanVersion/ExecutionTask/ExecutionResult/ExecutionArtifact/ResultAnalysis/FailureCluster/DefectVersion/DefectSyncAttempt/TestReport/QualityGate/PipelineConfig/PipelineRun,字段取自 04 权威模型)与 21 个响应定义;顺带修复 4 处 create operation 201 响应误引用 List 的错误。
- **结果**:核心链 Generic 残留 38→0;非核心链 37 处保持 KNOWN_DEFERRED(随模块开发收敛)。
- **验证**:openapi-spec-validator PASS。

### 六、B2-4/8/9/10 与 22 号同步(本轮早前已落盘,补记)

- 15-PRD §4/22 §3:V1 手工外部同步走 DefectSyncAttempt+批准记录+回执(B2-4)。
- 13-PRD §3:试运行沙箱量化验收口径(非 root/只读工作目录/零外网/超时 120s/产出白名单,每条有检查命令)(B2-8)。
- 14-PRD §2/18-PRD §2:CI/Webhook 触发归 V2,V1 仅手工+计划(B2-9)。
- 04 §3.3 加 ReviewDecision 投影说明;03 迁移表措辞统一 ReviewTask/ReviewAssignment(B2-10)。
- **受影响**:`13-PRD-Execution.md`、`14-PRD-QualityIntelligence.md`、`15-PRD-SkillCenter.md`、`18-PRD-CICD.md`、`22-MVP版本规划v2.0.md`、`03-术语表Glossary.md`、`04-核心领域模型.md`。

### 七、遗留(非本轮范围)

- QF-REQ-005 非核心链 37 处:随批次 3/4 模块开发收敛。
- 里程碑对照表(QF-REQ-007):由对照表 Agent 产出,单独交付。
- 批次 2(27 条):M1 期间并行,准出前置。

---

## 批次十七：批次 2 文档一致性收口（2026-08-14）

> 依据:修复方案 v2.0 批次 2(27 条,全部"向权威源收敛");验证:OpenAPI validator PASS + 27/27 grep 实证。

- **008**:05 §5.6.2 reviewStatus 回改九值(CHANGES_REQUESTED/STALE,删 REWORK)。
- **009**:04 §11.1 状态机补齐 6 条迁移(IN_PROGRESS→DONE、PENDING_REVIEW→BLOCKED/CANCELLED、REWORK→CANCELLED、APPROVED→BLOCKED、BLOCKED→CANCELLED),权威声明以 05 §5.5.4 为准。
- **010**:05 §5.5.6 WorkItemRun 枚举对齐 33(PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED;TIMEOUT 归 error_code;成本字段声明来源)。
- **011**:15-PRD/32 DefectSyncAttempt 命名统一(ExternalSyncAttempt→DefectSyncAttempt、approvalReviewTaskId→approvalId)。
- **012**:32 ReviewTask.agentSessionId 改可选(人工直接修改提交审核场景)。
- **013**:13-PRD §7 版本范围逐项 MUST/SHOULD/LATER 标注。
- **014**:10-PRD 状态链修正(REWORK→IN_PROGRESS)。
- **015/016**:14-PRD 术语改 ExecutionContractBaseline;§5 补基线撤销→BLOCKED 触发。
- **017**:16-PRD §6 补 21§6.1 三触发(校准过期/跌破门槛/误放误阻)。
- **018/019**:17-PRD 补 SupportAccessGrant(break-glass)与 CONFIG_ASSIST 承接。
- **020**:37 号操作数按 32 实算修正(看板 10/AI 10/平台 22)。
- **021**:01 §2 Requirement→RequirementDocument。
- **022**:18-PRD Batch 口语裁决(不建独立实体,为一次触发/attempt)。
- **023**:21 号新增 INDEPENDENT_VERIFY 介入点;16-PRD 承接三层证据口径。
- **035**:54 索引"文件名↔模块"映射加显式裁决注。
- **037**:05 §5.5.5 role 标注(API/DB 侧 relation_type,含 SUPERSEDES)。
- **038**:12-PRD BLOCK_HUMAN 标注来源(55-SOP);10-PRD 移除 HTTP 409 细节。
- **040**:11-PRD AC-01 补判定口径(随机抽检≥5 条)。
- **041**:16-PRD L0-L3 显式引用 21 号 SSOT。
- **043**:14-PRD 补 V1 重试上限(默认一次受控重试)。
- **044**:16-PRD platform-review 文件补完整路径。
- **046**:03 术语表 §13.8-13.12 编号重排(消除重复)。
- **047**:15-PRD 知识回流补 V1/V2 边界。
- **N4**:37/54 Generic 计数口径更新(核心链已收敛,剩余 37 处非核心链 KNOWN_DEFERRED)。
- **N5**:05 §5.5.3 humanAssigneeId→assigneeId。
- **N6**:03 术语表 WorkItem 行加注 TEST_DESIGN 同名不同义。
- **042/045**:B2-9/B2-10 已落盘项复核通过(本批无新增改动)。

**受影响**:03/04/05、01/02-prd 10-18、03-governance 21/22、04-architecture 32/33/35/37、00-navigation 54。

---

## 批次十八：批 3 收口(2026-08-14)

- **QF-REQ-036 校准绑定列(双源同步,方案 A)**:33 t_calibration_record 新增 subject_operation/subject_table(TEXT 存 JSON 数组字符串,NULL 可空:一介入点多实现点、无单一归属介入点如 INDEPENDENT_VERIFY 可空);32 CalibrationRecord/CalibrationRecordCreate 同步新增 subjectOperation/subjectTable(**不进 required**,避免破坏既有校准注册调用)。验证:三源 grep + openapi-spec-validator PASS。
- **INDEPENDENT_VERIFY M1 最小落点(前序,复核入册)**:33 新建 t_verify_verdict(四态 CHECK+输入摘要+唯一约束);32 新增 /ai/independent-verify + VerifyVerdict/VerifyVerdictCreate/VerifyVerdictResponse。
- **覆盖率口径契约层落地(前序,复核入册)**:33 t_coverage_report.denominator_definition_ref 五类 CHECK;04 CoverageReport 实体加五类说明;22 号附录 C 写入五类权威口径定义。
- **对账遗留**:33 号目标表 104→105(t_calibration_record 为 8-14 新增,标题已同步);里程碑对照表补 t_calibration_record(M5)/t_verify_verdict(M1),V1 涉及 93/105=88.57%。
- **受影响**:`33-数据库Schema设计.md`、`32-API规范.yaml`、`04-核心领域模型.md`、`22-MVP版本规划v2.0.md`、`35-变更记录CHANGELOG.md`、里程碑对照表。

---

## 批次十九：独立复核残留清理（2026-08-14）

> 依据:独立机械扫描复扫发现批次十七/十八后的三处 Minor 残留;验证:grep 实证。

- **048**:11-PRD AC-01 删除批次 040 遗留的旧版 Then 行(与带判定口径的新版 Then 近似重复),保留裁决 2026-08-14 批次二口径行。验证:全 PRD 无单 AC 双 Then。
- **049**:12-PRD §9 标题悬空引用修正,"口径见指标数据字典"(该文件不存在)→"口径见22号附录C五类覆盖率权威口径"(批次十八落盘的权威出处)。
- **050**:12-PRD §9 设计覆盖测量方法分母笔误,"需条目总数"→"需求条目总数",与 22 附录 C DESIGN 口径分母一致。
- **受影响**:`docs/02-prd/11-PRD-TestDesign.md`、`docs/02-prd/12-PRD-TestAsset.md`、`docs/04-architecture/35-变更记录CHANGELOG.md`。

---

## 批次十九：第 0 周补丁(2026-08-14,QF-CA-2026-0814 反方审查后)

- **B2 INDEPENDENT_VERIFY 行为契约**:16-PRD 新增 AC-07(独立性定义/裁决组合规则/失败流向/超时 60s/三层证据呈现,含 FAIL→REWORK 的 GWT);21 号修正对 05 §5.6.3 的错误引用(实为参与者与责任,改为 05 §5.6 通用审核契约 + 16-PRD AC-07)。
- **B3 执行域三件套**:32 ExecutionTask status 枚举对齐 33 八值(PENDING/QUEUED/RUNNING/COMPLETED/FAILED/CANCELLED/TIMED_OUT/BLOCKED);33 t_execution_task 补 timeout_seconds/lease_expires_at;32 新增 /runners/heartbeat + RunnerHeartbeat;33 新增 t_execution_task_event 只追加事件表(补 20 §4.2 缺口)。
- **B5 CoverageReport API**:32 新增 /quality/coverage-reports(GET/POST)+ CoverageReport/CoverageReportCreate schema + 两个响应;33 t_coverage_report 加注 EXECUTABLE/HUMAN_ACCEPTANCE 汇总方案(13/14 号与 15 号侧汇总)。
- **B1 口径全库收敛**:38 号(3 处)、53 号(1 处)、05 §5.12 历史段统一为 106 表/80 路径;L1 复扫新增"38/53 迁移文档口径核对"检查项(v3 通过)。
- **B4 PAUSED 语义**:14-PRD 注记"暂停=BLOCKED+blockedReasonCode=PAUSED_BY_USER(复用统一状态机,不新增 PAUSED;裁决假设待 PO 最终确认)"。
- **框架固化**:里程碑复核基线(反方五步框架)成文,作为 M1~M5 复核固定基线。
- **验证**:openapi-spec-validator PASS;L1 复扫 v3(28 项,含 38/53 口径检查)通过。
- **受影响**:32/33/38、14/16-PRD、21/53、05、35-CHANGELOG。

---

## 批次二十：B4 裁决落地(2026-08-14)

- **B4 blocked_reason 字段落点**(PO 裁决:同意 BLOCKED+原因码复用,不新增 PAUSED):33 t_execution_task 补 `blocked_reason VARCHAR(40)`(枚举 USER_PAUSED/DEPENDENCY_BLOCKED/ENV_ISSUE/PERMISSION/QUALITY,仅 status=BLOCKED 时有值);05 §5.5.4 BLOCKED 行补"用户主动暂停=BLOCKED+blocked_reason=USER_PAUSED";14-PRD 由注记改为正式引用。三源(05/33/14)落在一处;字段并入 M1 建表,避免 M3 迁移。
- **验证**:grep 三源 USER_PAUSED 各 1 处;blocked_reason 33 号 3 处(列定义+CHECK+注释)。

---

## 批次二十一：遗留项修复(2026-08-15)

- **表数口径**:33 号实算 107 张(8-14 新增 t_verify_verdict/t_execution_task_event 后),38/53/05 口径由 106 修正为 107。
- **approval_id 约束修复**:33 号 t_defect_sync_attempt.approval_id 注释曾插在类型与约束之间,吞并 NOT NULL REFERENCES;已恢复为真实约束并后置注释。
- **8 条占位 FR 补全**:FR-001/009/017/025/034/044/053/062 描述原为模板占位文本(数据提取缺陷),已从 8 个 PRD §2 功能表补全真实内容;需求说明书 v3.2 附录 A/B 同步更新。
- **GWT 口径确认**:05 §5.5.12 实测 8 组(非任务口述 10 组),测试计划已按实测编写。
- **受影响**:38/53/05/33、srs_fr_items.md、需求说明书 v3.2。
- **落账**:本批次内容已于 commit 8793144 入库(2026-08-15 存量落账，用户拍板)。

---

## 批次二十二：B 类裁决执行与 C 类决策记录(2026-08-15)

- **B1**:05 §5.8.4 gitCommitSha→fullCommitSha(以 04/32 为准)。
- **B2**:04 Skill 状态机补 ERROR→INSTALLING/RETIRED + ACTIVE→ERROR 入边;Release TESTING→ARCHIVED(中止归档,不新增 HOLD);ReviewTask/Assignment 超时语义(EXPIRED 终态,超时=新建 Assignment+原置 REASSIGNED);Locator 三源同步 PENDING 初始态(04/33;03 待登记)。
- **B4**:05 §5.6.2 APPROVED/PUBLISHED 语义精确化(签署对象=APPROVED 待发布版本,签署通过→PUBLISHED)。
- **B5**:32 AutomationScriptVersionCreate.bindings/DefectVersionCreate.evidence minItems:1→0(创建期不强制,门禁在 05 §5.8.5 正式执行前)。
- **B6**:Defect.releaseId 可空注(04/32)。
- **B7**:32 ExecutionTask 删 attempt(与 33 对齐,保留 retryOfTaskId)。
- **B8**:04 Skill 稳定根+不可变版本注(完整改造 V2 前)。
- **B9**:05 §5.13.4 V2 准出以 22 号为唯一源注。
- **B11**:15-PRD M-16 与 12-PRD 版本级主口径一致注。
- **B12**:20 §1.1 M-41 公式注(Σ(attemptNo−1)/任务数;主载体 ExecutionTask.retryOfTaskId)。
- **B13**:20 §1.1 M-20 键名 qual_false_accept_rate;21 §6.1 警戒线参数化(N/阈值试点后批准)。
- **B14**:actorType 以 33 四值(HUMAN/AGENT/SERVICE/SYSTEM)为基线;32 L827/L906 与 04 currentActorType 同步(USER→HUMAN)。
- **B15**:16-PRD 校准记录 V1 即承担自治判定底座(非 V2 增强)。
- **C 类**:8 条决策已采纳并记录(见 deliverables/2026-08-15/QualityForge-C类决策记录.md)。
- **验证**:openapi-spec-validator PASS(32 号多次修改后)。
- **受影响**:32/33/34/37/38/53、04/05、12/15/16-PRD、20/21/22、CHANGELOG。
- **落账**:本批次内容已于 commit 8793144 入库(2026-08-15 存量落账，用户拍板)。

---

## 批次二十三：VERDICT 契约修复批次 + 存量落账(2026-08-15)

执行依据:wall/reviews/req-contract-reconciliation/VERDICT.md(话题已关帖);用户 2026-08-15 拍板全部采纳协调人建议。

**用户裁决记录(Owner 拍板,2026-08-15)**:
1. 存量修复立即 commit 落账(已执行,commit 8793144)。
2. 契约修复批次立即开工,由 lingma 执行(本批次)。
3. 合规 5 缺口(GDPR/数据主体权利、保留期限数字、LLM 出站审批、指标数据字典、permissionKey 目录)列为待补需求项,不阻塞 V1;其中出站审批与保留期限须在 V1 接真实模型前关闭,指标字典建议先于报告签署验收落地。
4. V1 维持全八模块范围,逐模块冻结「最小入口」可验收切片(切片清单冻结为后续任务)。
5. C-C5(docs/30 双轨消除)经复核确认 autoclaw 已落地(M-107 回执属实),不再重做。

**P0-1 TestReport 版本层补齐(纯 API 增量)**:32 新增 TestReportVersion schema(与 33 t_test_report_version 全列对齐,含 reviewStatus 九值枚举);TestReport 增 releaseId/reportKey/currentVersionId/publishedVersionId 与 status 枚举(ACTIVE/ARCHIVED),移除库表无承载的根级 scopeSnapshotRef/contentDigest/signedBy(已下沉版本层);版本查询 operation 路径待后端接入时补,届时同步 KNOWN_DEFERRED_COUNT。

**P0-2 PipelineRun 双维度拆分**:32 PipelineRun.status 改为运行状态五值(PENDING/RUNNING/COMPLETED/FAILED/CANCELLED),新增 gateDecision 门禁结论五值(PASSED/WARNED/BLOCKED/QUARANTINED/INCONCLUSIVE),与 33 t_pipeline_run 双列逐字对齐;原 TitleCase 压扁单枚举废弃。

**P0-3 AgentSession 三方对齐(以 33 为权威基线,VERDICT D-1)**:32 AgentSession/AgentSessionCreate 字段与枚举向 33 t_agent_session 对齐(status 六值 PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED/BLOCKED,新增 workItemRunId/agentId/workflowVersionId/promptVersionId/inputDigest/outputDigest/tokenUsage/cost/errorCode);Stage 4 过渡字段(workItemId/workflowKey/reviewTaskIds 等)显式标注待迁移移除;artifactRefs 根级字段移除(产物引用由 ReviewTask/产出物承载);03 §13 新增 13.13 AgentSession 状态条目(含 COMPLETED/PAUSED_FOR_HUMAN 废弃声明);frontend/types.ts 补全字段与 AgentSessionStatus 类型;App.tsx 清除 BLOCK_HUMAN 幽灵值。

**C-8 附带项**:32 AutomationScriptVersionCreate 补 sourceTrace 字段(MANAGED 模式必填)。

**契约测试断言(批次结束条件)**:新增 backend/tests/test_contract_enums.py(6 组枚举与 33 CHECK 逐字对齐 + 废弃值黑名单 + TestReport 版本层存在性);新增 frontend/src/statusBadge.test.ts(FAILED→danger + 六值文案 + 幽灵值无语义映射,4 例);statusLabel/StatusBadge 映射抽为 frontend/src/statusBadge.ts 纯函数。

**落账纪律(C-6)**:存量修复已于 commit 8793144 落账(含防漂移计数 KNOWN_DEFERRED_COUNT 80→86);本批次 commit 哈希:931db92(本条 CHANGELOG 落账提交见 git log 后续一条)。VERDICT 三项 P0 + 03 §13.13 + 前端幽灵值清除 + 契约测试断言全部完成并入库,台账状态由「工作区已修、待提交」改为「已关闭」。

**验证**:backend pytest 15/15 PASS(含 openapi-spec-validator 与新增枚举断言);frontend tsc --noEmit PASS + vitest 10/10 PASS。

**受影响**:32、03 §13、frontend/src(App.tsx/types.ts/statusBadge.ts)、backend/tests、CHANGELOG。

---

## 批次二十四（2026-08-15）：docx 交付物审查修复（需求说明书 + 接口文档）

**触发**：对 deliverables/2026-08-15 两份 docx 交付物的三维度审查（规范性/完善性/正确性），叠加外部标准基线（GB/T 9385-2008、ISO/IEC/IEEE 29148:2018、OpenAPI 规范、Stripe/ReadMe 等 API 文档行业标杆）。审查结论：有条件通过，修复后重新生成。

**接口文档 v3.0（QualityForge-接口文档-v3.0.docx，文档版本 V1.0→V1.1）**：
1. §1 tag 明细表改为按 32 号契约动态解析生成（消除硬编码），修正 Quality 13→15、AIAgentCenter 10→11、Platform 22→23，合计 104→108 并新增合计行——消除文档内部数字不一致（29148 §5.2.5 一致性缺陷）。
2. §7 变更记录补记 2026-08-15 契约修复批次（TestReportVersion/gateDecision/AgentSession 三源对齐/sourceTrace）与本文档 V1.1 修订。
3. §4 为 Stage 4 已实现 22 个 operation 补真实请求/响应示例（字段对齐 backend/src/qf/schemas 与 32 号契约；AgentSession 示例用契约目标态枚举并注过渡值说明）——补齐行业标杆"端点示例"缺口。
4. §8.3 刷新 CI 校验时间戳（2026-08-15 复验）并新增生成谱系段。

**需求说明书 v3.2（QualityForge-需求说明书-v3.2.docx）**：
1. 封面版本号 V1.0→V3.2 与文件名统一；版本历史补 V3.1/V3.2 两条演进记录；编制日期更正为 2026-08-15。
2. §13.1 数据表数口径 106→107（按 33 号 CREATE TABLE 逐表校准）；§13.2 契约口径 79 路径/104 operation→82 路径/108 operation（按 32 号 openapi-spec-validator 与防漂移测试校准）；§15.2 M2 门禁表数同步 107；未核实项悬置标注全部消除并记闭环。
3. 新增第 16 章开放问题清单（ISO 29148 文档级信息项要求）：OPN-01~07，其中 OPN-01/02/03 本次闭环，OPN-04~07 开放（合规 5 缺口、TestReport 版本查询 operation、V1 切片清单冻结、DDL PG 实测）。
4. 附录 B 统计矛盾裁决：经逐项核实，此前"8 条 FR（FR-001/009/017/025/034/044/053/062）为模板占位、无对应原始需求"定性不成立——8 条均有实质内容与来源标注且附录 B 有反查引用，撤销定性、条目保留、待裁决项闭环。

**生成器**：`.cluster/qf-b3-20260814/build_api_doc_v3.py` 与 `build_srs_v3.py`（本地工具不入库）；tag 统计改为契约解析动态生成，杜绝口径再次漂移。

**落账纪律（C-6）**：本批次 commit 哈希为 `f258fd2`（修复本体，含两份 docx 重新生成与本批次登记）；本回填行为后续 commit。

**受影响**：deliverables/2026-08-15 两份 docx（重新生成）、CHANGELOG。

---

## 批次二十五（2026-08-16）——需求说明书表述规范化（V3.2 → V3.3）

**触发**：用户审查指出《需求说明书》正文大量使用 Given/When/Then 测试用例写法与代码层英文字段名（frameworkVersion、blocking check 等），不符合需求文档面向业务与评审读者的表述要求；原则：除必要的英文（无中文对应的领域实体名、通用缩略语）外，一律使用中文。

**修复内容**：
1. 第 3~10 章共 8 个模块的"主要验收标准（AC 摘选）"全部 33 条，由 Given/When/Then 三行式改写为中文语句（表述前提、触发与系统响应），保留 AC 编号与来源标注的可追溯性；
2. 代码层字段名与状态码转为中文描述：frameworkVersion→框架版本、blocking check→阻断检查、PENDING_REVIEW→"待审核"、DENY→拒绝、attempt1/2→第一/二次尝试、MATCH/DEVIATION/NOT_CHECKED/INCONCLUSIVE→符合/偏差/未检查/无法判定 等；
3. 保留的英文仅限无中文对应的领域实体名（ReviewTask、TestPlanVersion 等，第 11 章术语表与 §1.4 已声明"领域实体使用稳定的英文规范名，以 03 号术语表为唯一权威源"）与通用缩略语（OpenAPI、RBAC、RLS 等，首现附中文释义）；
4. §12.9 非功能需求总验收中"20 号 Given/When/Then 门禁"改为"20 号文档的场景式门禁验收条款"；
5. 封面版本升级 V3.3、编制日期 2026-08-16，版本历史补第 4 行；输出为新文件 `QualityForge-需求说明书-v3.3.docx`（v3.2 被取代，保留待处置）。

**复验**：docx 正文提取实测——Given/When/Then 零残留（版本历史说明行除外）、frameworkVersion/blocking check 零残留、33 条 AC 全部在文、前批次修复项不回退（107 张表、第 16 章 OPN-01~07、附录 B 裁决均保持）。

**生成器**：`.cluster/qf-b3-20260814/build_srs_v3.py` + `req_doc_content.md` + `srs_nfr_risk.md`（本地工具不入库）。

**落账纪律（C-6）**：本批次 commit 哈希为 `bcd106a`（需求说明书 V3.3 与本批次登记）；本回填行为后续 commit。

**受影响**：deliverables/2026-08-15 新增 需求说明书-v3.3.docx（v3.2 被取代）、CHANGELOG。

---

## 批次二十六（2026-08-16）——需求说明书表述规范化（续）：全局代码层英文中文化（V3.3 → V3.4）

**触发**：用户复核指出批次二十五仅覆盖 33 条验收标准，正文仍大量残留代码层英文（如状态机 BACKLOG/IN_PROGRESS、字段 artifactType/contentDigest、审核动作 APPROVE/REQUEST_CHANGES/REJECT、fail-closed 等），要求"全局都过一遍"；原则不变：除必要英文外一律中文。

**修复范围与内容**（五份渲染素材 req_doc_content.md / srs_ch1_ch2.md / srs_nfr_risk.md / srs_fr_items.md / trace_matrix.md，本轮累计约 130 处）：
1. 状态机状态码按 03 号术语表 §13 权威译名中文化：BACKLOG→待办、READY→就绪、IN_PROGRESS→进行中、PENDING_REVIEW→"待审核"、REWORK→返工、APPROVED→"已批准"、DONE→"已完成"、BLOCKED→"受阻"、CANCELLED→已取消、STALE→"待复核"等，首现处括注状态码出处；USER_PAUSED 表述为"暂停按'受阻'处理、阻塞原因记为'用户主动暂停'"（裁决 2026-08-14 B4）；
2. 字段名中文化：metricKey→指标键名、operationId→操作标识、interventionKey→介入点标识、contentDigest→内容摘要、allowedSkills→允许技能清单、blockingChecks→阻断检查项、secretRef→密钥引用标识、keyVersion→密钥版本、supersedes→取代关系、attempt→尝试、payload→提交内容、AuthorizationDecision/AuditLog→授权决定/审计日志、SupportAccessGrant/DelegationGrant→支持访问授权/委派授权 等；
3. 动作与枚举中文化：APPROVE/REQUEST_CHANGES/REJECT→批准/要求修改/拒绝、ALLOW/DENY→允许/拒绝、MUST/SHOULD/LATER→必须/应当/延后、DECLARED/OBSERVED→"声明/观察"、MATCH/DEVIATION/NOT_CHECKED/INCONCLUSIVE→符合/偏差/未检查/无法判定、CONFIG_ASSIST→"配置辅助"介入点、WIP→在制品、Golden Set→黄金样本集、DAG→有向无环图、human checkpoints→人工检查点、Finding→发现项、Code Review→代码评审、Eval/eval→评测、Provider→提供方；
4. 21 个业务错误码全部中文化（括注"规范码名见 32 号契约 §错误码"）；角色名中文化：PlatformAdmin/TenantAdmin/WorkspaceAdmin/TestLead/TestEngineer/ViewerAuditor→平台管理员/租户管理员/项目管理员/测试负责人/测试工程师/只读审计员；安全术语注译：fail-closed→失败即关闭、mTLS→双向 TLS、HttpOnly→仅 HTTP 可读、SameSite=Strict→严格同源、break-glass→应急特权、allowlist→允许清单、IdP/SCIM/SLO 首现括注中文；
5. "必要英文"边界（本批口径登记）：领域实体规范名（WorkItem、ReviewTask、ExecutionResult、APIObservation、ContractCheckResult 等，依据 §1.4 与 03 号术语表）、t_ 数据库表名（33 号 107 张表）、文件名/文档编号/附录 B 来源列 PRD 引用、通用缩略语（RBAC/SLA/OpenAPI/RLS/SSO/JWT/UUID/SHA/OIDC 等）、"中文在前、首现括注英文"的注译模式；
6. 封面版本升级 V3.4、版本历史补第 5 行；输出新文件 `QualityForge-需求说明书-v3.4.docx`（v3.3 被取代，保留待处置）。

**复验**：docx 正文提取实测——代码层英文零残留（剩余 27 处命中均为必要英文：ReviewTask/ReviewPolicy/EvalDataset 等实体名、t_ 表名、第 11 章术语表、附录 B 来源列、版本历史元数据、中文在前括注）；前批次不回退（107 张表、82 路径/108 operation、第 16 章 OPN-01~07、33 条中文 AC、附录 A 74 行、附录 B 66 条统计段均保持）。

**生成器**：`.cluster/qf-b3-20260814/build_srs_v3.py` + 五份素材（本地工具不入库）。

**落账纪律（C-6）**：本批次 commit 哈希为 `f192643`（需求说明书 V3.4 与本批次登记）；本回填行为后续 commit。

**受影响**：deliverables/2026-08-15 新增需求说明书-v3.4.docx（v3.3 被取代）、CHANGELOG。

---

## 批次二十七（2026-08-17）——需求说明书按参考 PRD 编写规范重组（V3.4 → V4.0）

**触发**：用户要求参考《国家在线业务管理平台V2_Beta_PRD_20260811.docx》的编写规范与风格，先分析后抽离应用到 QualityForge 需求说明书。

**参考规范抽离结果**（从参考文档 586 段落/30 表格实证提取）：①文档骨架=封面（产品名+文档名+版本+修订记录表）→ 系统功能设计（H1）→ 模块（H2）→ 功能点（H3）→ 功能模块概述/功能描述（H4）→ 页面级（H5）→ 非功能需求（H1）→ API 接口；②模块级先给【业务流程】【业务规则】；③页面级固定模板=【原型图】+图 N 题注 →【业务规则】编号条目（触发时机、初始值、校验规则、提示文案）→【界面元素】三列表（类型|字段|字段描述，含控件类型与交互描述）；④行文为陈述句、具体数字与文案、中文序号 1、2、①②。

**修复范围与内容**：
1. 全文重组为参考风格：封面（QualityForge+需求说明书+V4.0+修订记录表）→ 1 系统功能设计（登录与权限缺省页 + 8 模块共 21 个页面，23 张图题注、8 段模块级业务流程、38 段【业务规则】、30 张【界面元素】三列表、23 组功能模块概述/功能描述）→ 2 非功能需求（八类分组、指标条目式写法，保留"先测基线、再批准目标"原则，未实测数字标候选值）→ 3 API 接口（八模块接口地图表：82 路径/108 operation、21 个业务错误码指引）→ 4 开放问题清单（OPN-01~07 沿用）→ 附录 A/B（沿用 V3.4 追溯矩阵，不回退）。
2. 内容来源为 V3.4 权威素材（八模块能力表、关键规则、AC、非功能需求）与页面地图（docs/06-wireframes/QualityForge-Page-Map.md）；页面级业务规则由各模块关键规则与裁决落到具体页面，表述沿用中文化口径。
3. 新增渲染器 `.cluster/qf-b3-20260814/build_srs_v4.py` 与四份素材 prd_mod_a/b/c.md、prd_nfr_api.md（本地工具不入库）。

**复验**：docx 正文提取实测——五级结构、封面修订记录、23 图题、38 段【业务规则】、30 张【界面元素】表齐全；代码层英文残留扫描 0 命中；附录 A（FR- 出现 140 次）、附录 B（PRDxx-Rx 66 条）与统计段保持；82 路径/108 operation、失败即关闭、黄金样本集等关键项不回退。产物 559 段落/35 表格。

**落账纪律（C-6）**：本批次 commit 哈希为 `f98f9d5`（需求说明书 V4.0 与本批次登记）；本回填行为后续 commit。

**受影响**：deliverables/2026-08-17 新增需求说明书-v4.0.docx（按参考规范重组的现行版；V3.4 保留作 GB/T 9385 骨架版本）、CHANGELOG。

---

## 批次二十八（2026-08-17）——计划体系 v1.1 生效批次：P0-1 门禁整改落账 + 用户裁决记录

**触发**：① 2026-08-17 开发计划评估报告（8.2/10，2 P0+3 P1+5 P2）核验认可后的整改落地；② 用户两项裁决；③ autoclaw 对 v1.1 的评估（9.0/10）N1 项——Makefile 门禁整改须 commit+CHANGELOG 双落账后方可标 CLOSED。

**用户裁决记录（本批次权威依据）**：
1. O1 关闭：接受「定性成功标准＋基线后量化」路径——定性标准 D1–D5 写入主计划 §四，量化目标值按 22 号文档 §6 于 V1 试点基线后批准；
2. 开发分工：后端＝lingma、前端＝autoclaw（前端原型即 autoclaw 设计），计划体系据此升版 v1.1 双轨重构；
3. 批准 N1 落账提交（本批次即执行）。

**变更内容**：
1. **P0-1 门禁整改（commit `15ef64a`，chore(ci)）**：Makefile 新增 `test-frontend` target（vitest run）并纳入 `test` 聚合——`make test` 现为后端 pytest＋前端 vitest＋30 Skill evals＋Agent 治理校验四段；实测前端 10/10 绿、全聚合通过。伴随提交 `a981d41`（fix(test)）：门禁复跑拦截到 `test_contract_enums.py` 存量 E501 长行（批次二十三引入），拆分修复后三重门禁全绿。至此 P0-1 满足 §3.5 双落账条件，标 CLOSED；
2. **计划体系 v1.1 生效批次（commit `5bb6438`，docs(deliverables)）**：入库《开发计划与方案》v1.0/v1.1、《M1 实施计划》v1.0/v1.1、两轮计划评估报告 html（外部评估 8.2/10 与 autoclaw 评估 9.0/10）。v1.1 要点：新增 §3.0 双轨协作模型（契约唯一接缝、mock 先行、升级触发权对等）、验收标准重构为后端/前端/集成三层、§六放行三条件关闭包、生效批注（原型路径钉死 `deliverables/2026-08-12/prototype/`、M2 收缩优先保留分派视图）；
3. 墙上协调记录：M-114 开工通告、M-115 前端轨派工（@autoclaw，M-117 已接收确认）、M-116 评估处置回执——对话墙为仓库外协调机制（`.gitignore` 既定边界），不入本批次。

**复验**：三重门禁实测全绿（ruff+mypy、openapi-spec-validator、pytest 15/15、vitest 10/10、Skill evals 103 例、治理校验 PASS）。

**遗留**：`deliverables/2026-08-15/用户故事集-2026-08-15.md` 仍为未跟踪文件（批次二十三前遗留，与本批次无关），待下一批次处置。

**落账纪律（C-6）**：本批次内容提交哈希为 `a981d41`、`15ef64a`、`5bb6438`；本登记行为后续回填 commit。

---

## 批次二十九（2026-08-17）——M1-B0：characterization 基线 + QF-REQ-001 四源二次复核关闭

**触发**：M1 实施计划 v1.1 M1-B0 工作包（开工之首）：整改 P1-1（测试基线薄弱）＋关闭 QF-REQ-001（防二次假关闭）。

**变更内容**：
1. **characterization 基线（commit `3469fe1`，test(backend)，分支 test/m1-be-char-baseline）**：新增 test_planning_characterization.py（7 例：工作项创建形状、三类产出物生成与人工门禁暂停、全批准 COMPLETED、退回 REWORK、旧摘要/已决策/短 Idempotency-Key 守卫、列表可见性、重挂持久化）＋ test_operations_happy_path.py（22 个已实现 operation 依序全绿＋覆盖集与实现清单双向对齐）。后端测试 15→23；
2. **QF-REQ-001 源①复修（commit `22d4d3f`，fix(backend)）**：WorkItemCreate 补齐契约六关键字段（objective/acceptanceCriteria/requiresReview 必填，constraints/agentId 可空）并落库（lockVersion 服务端初始 0）；requiresReview 免审语义与 lockVersion 409 接线明示归 M1-B1；
3. **复核记录与台账（commit `3a12c76`，docs(deliverables)，分支 docs/qf-req-001-recheck）**：《QF-REQ-001 四源二次复核记录》（四源实测核对表，全部当次 grep/Read 实证）；台账续编 QF-REQ-078（运行时会话状态枚举与契约不一致，严重，归 M1-B1 收敛）与 QF-REQ-079（M1 计划现状表四个 create operation 误标已实现，已随批更正）。

**关闭判定**：QF-REQ-001 四源 6/6 对齐（文档三源实测齐全＋后端源本批复修＋测试固化），满足双落账条件，标 CLOSED。

**复验**：提交前 make lint（ruff+mypy）与后端 pytest 23/23 全绿。前端 vitest 当前红为前端轨 M1-F1 进行中文件（仓库外工作区）所致，与本批次无关，待前端轨落账后恢复聚合绿。

**落账纪律（C-6）**：本批次内容提交哈希为 `3469fe1`、`22d4d3f`、`3a12c76`；本登记行为后续回填 commit。

---

## 批次三十（2026-08-17）——M1-B1：退回→新版本后端闭环（TDD 红绿 + QF-REQ-078 收敛 + 契约先行双确认）

**触发**：M1 实施计划 v1.1 §M1-B1 工作包（后端轨，分支 feat/m1-be-wp1-review-rework，TDD）：四红项——① decideReviewTask(REJECT/REQUEST_CHANGES)→产出物回草稿态；② createTestStrategyVersion/createTestPlanVersion 版本递增、旧版只读可查、新版本自动建新 ReviewTask；③ transitionWorkItem REWORK 路径；④ lockVersion 陈旧提交 409。附带收敛台账 QF-REQ-078。

**变更内容**：
1. **契约先行（commit `b19420f`、`d0174db`，docs(contract)）**：32 号 ReviewTask 新增计算字段 `approveDisabledReason: string|null`（枚举 TASK_CLOSED/STALE_VERSION/PERMISSION_DENIED/PRECONDITION_PENDING，后两值预留）；WorkItemTransition 新增必填 `lockVersion: integer≥0`（乐观锁）。墙上 M-120 发起双轨确认（裁决单值而非 autoclaw M-118a 提案的 string[]，附枚举映射表；24h 无回帖按裁决推进条款生效，合入时仍无回帖）；
2. **TDD 红（commit `7304f0f`，test(backend)）**：新增 test_rework_closed_loop.py（9 例：REQUEST_CHANGES→DRAFT/BLOCKED/REWORK、REJECT→DRAFT/FAILED/completedAt、策略 v2 版本递增+新任务+STALE_VERSION/null、闭环 SUCCEEDED+旧任务 409、计划 v2、transitionWorkItem 五断言、legacy 归一、枚举守卫 parametrize）；characterization 3 处断言同步新枚举；契约清单 22→25、延期 86→83；happy-path 纳入 3 新 operation；
3. **TDD 绿（commit `f53ed00`，feat(m1-be)）**：退回回草稿态（REJECT 另终态会话 FAILED+trace human_gate_rejected）；_advance_session_after_review 四分支收敛且排除被取代旧任务（契约无 SUPERSEDED 态，仅排除出判定）；create_strategy_version/create_plan_version（版本不可变、新摘要自动建 OPEN 审核任务、_review_context_of_artifact 反查审核上下文）；transition_work_item（幂等+lockVersion 409 STALE_LOCK_VERSION+expectedCurrentStatus 守卫，切片仅 REWORK）；approveDisabledReason 优先级：会话终态 TASK_CLOSED > STALE_VERSION > TASK_CLOSED；QF-REQ-078 收敛：PAUSED_FOR_HUMAN→BLOCKED、COMPLETED→SUCCEEDED，存量加载归一（_LEGACY_SESSION_STATUS_MAP）；新增能力位 work_item.transition/artifact.test_strategy.submit/artifact.test_plan.submit；
4. **台账登记（commit `f5ecb4b`，docs(deliverables)）**：QF-REQ-078 标已关闭（运行时枚举收敛+存量归一+测试守卫）；QF-REQ-080 新登记（切片 DTO 长度/格式约束严于契约，归 M2 对齐）。

**复验**：后端测试 23→33（新增 10：红 9+契约清单 1 口径变化），提交前与合入后两次三重门禁全绿（ruff+mypy、openapi-spec-validator、pytest 33/33）。前端 vitest 红仍为 autoclaw M1-F1 WIP（已 stash 保护，不合入本批）。

**遗留/开放项**：M-120 无回帖（裁决已按条款推进，autoclaw 保留合入前反案权，若反案则另起批次回滚修订）；autoclaw M-118a 次要请求四项归 M2（M1-B2 关闭包登记 O 系列）。

**落账纪律（C-6）**：本批次内容提交哈希为 `b19420f`、`d0174db`、`7304f0f`、`f53ed00`、`f5ecb4b`（分支 ff 合入 main）；本登记行为后续回填 commit。

---

## 批次三十一（2026-08-17）——M1-F1：前端轨审核台交付落账（autoclaw，验收复扫通过）

**触发**：前端轨 M1-F1 工作包完成（autoclaw 交付，墙 M-119a/M-123），协调人验收复扫后合入 main 并双落账（§3.5 跨轨纪律：前端轨提交由 autoclaw 作出，CHANGELOG 登记由协调人编排）。

**变更内容**：
1. **M1-F1 本体（commit `6474873`，feat(frontend)，分支 feat/m1-fe-wp1-review-bench）**：审核台 15 项信息（reviewInfo）、批准禁用原因门禁（approveGate）、决策面板（DecisionPanel）、审核详情（ReviewDetail）、版本历史+Diff 摘要（VersionHistory）＋五个配套测试；mock 数据层、Playwright 冒烟（review-smoke/evidence-screenshots）与 CI Playwright step；DELIVERY/ 四件交付物与截图证据 4 张入库；33 文件；
2. **契约对齐修订（commit `508ba67`，fix(frontend)）**：对齐 M-120/M-121 裁决——approveDisabledReason 改单值 string|null（mock 用契约实际值 TASK_CLOSED/STALE_VERSION）、createWorkItem 补齐 objective/acceptanceCriteria/requiresReview 三必填；6 文件。

**验收复扫（协调人实测）**：后端/契约零污染（diff 不含 backend/与 docs/）；make test 聚合全绿（后端 pytest 33/33、vitest 34/34、Skill evals 103 例、治理校验 PASS）；Playwright 9/9 实测属实；合入后复验仍全绿。

**复验**：两提交 ff 合入 main（main=`508ba67`），分支已删；工作区仅余既定排除物（.qoder/、evolution-drafts/、用户故事集历史遗留、frontend/DELIVERY/ 截图副本）。

**契约状态**：M-120 裁决获 autoclaw 确认无反案（M-123），契约先行双确认闭环；M1 双轨 M1-B1/M1-F1 均已落账。

**落账纪律（C-6）**：本批次内容提交哈希为 `6474873`、`508ba67`（autoclaw 作出，ff 合入 main）；本登记行为后续回填 commit。

---

## 批次三十二（2026-08-17）——M1-B2：放行三条件关闭包（文档 Owner，纯文档批次）

**触发**：M1 实施计划 v1.1 §M1-B2 工作包（后端兼文档 Owner，分支 docs/m1-release-gate-closure）：需求全量评审 §5.6 V1 准入 gate 三条件逐条承接。

**变更内容**：
1. **关闭包正文（commit `09d7c93`，docs(deliverables)）**：《QualityForge-M1-放行三条件关闭包.md》——条件 1：O1 引用关闭（用户裁决）、O4/O5 证据关闭（覆盖维度落地时间链三处书面明确；L3 演进路径与委派深度 21 号权威源治理闭环）、O6 判定编号多报证据关闭，O2（手工测试纳入 V1）/O3（指标载体缺失项验收处置）升级用户裁决并附推荐方案；条件 2：R1–R3 对策落位清单（评审报告口径，引用主计划 §二/§四/§五/§六 与 M1-P1，附 R 编号双口径消歧）；条件 3：D1–D6 冻结记录（方案/排期/现状实证三列，D2 已提前执行、D3/D4 待 O2/O3 拍板后随批、D6 统一裁决台账列为后续执行项）；
2. **台账登记（同 commit）**：QF-REQ-081（评审报告 O6 编号多报，已处置）。

**gate 判定**：条件 2/3 满足；条件 1 为 4/6 关闭，O2/O3 待用户拍板（墙 M-125 发起升级裁决）；拍板前维持「需求未验收」口径（PASS_WITH_ACTIONS 约束不变）。

**复验**：纯文档批次，后端 pytest 33/33 全绿，零代码变更。

**落账纪律（C-6）**：本批次内容提交哈希为 `09d7c93`（分支 ff 合入 main）；本登记行为后续回填 commit。

---

## 批次三十三（2026-08-17）——O2/O3 用户裁决落地：V1 准入 gate 三条件全部满足

**触发**：用户对墙 M-125 升级裁决的两项开放决策拍板——O2（手工测试纳入 V1）与 O3（指标载体三档处置）均采纳推荐方案；批次三十二遗留的条件 1 最后两项随批关闭。

**变更内容**（commit `f6b1e50`，docs(gate)，分支 docs/m1-release-gate-o2o3-close ff 合入）：
1. **O2 落地**：14-PRD §2 手工测试行标注裁决（纳入 V1）；05 §4.5「如纳入范围」模糊表述替换为显式范围声明（手工测试作为平台记录的执行形态：人工记录步骤结果与证据、AI 仅辅助整理，不增加自动化执行实现面）。
2. **O3 落地**：20 §1.1 metricKey 登记表表头增三档处置口径注记——✅ 可计算项验收要求事件采集管道产出（无手工录入）；⚠️ 部分载体项仅要求采集不断档＋基线可建；❌ 无载体项验收豁免并声明延后 V2；与 O1「基线后量化」裁决同构。
3. **关闭包升级**：《QualityForge-M1-放行三条件关闭包.md》条件 1 从 4/6 升级 **6/6 关闭**；D3/D4 冻结记录更新为「已执行/口径已落」；gate 总判定改为**三条件全部满足**。

**gate 判定（更新）**：V1 准入 gate 正式关闭——「需求未验收」口径（评审报告 PASS_WITH_ACTIONS 约束）自本批次起解除，需求体系进入「已验收、按基线执行」状态。主计划 §六 挂账随本批次清零。

**复验**：纯文档批次，零代码变更；diff 四文件（关闭包/05/14-PRD/20）逐行核验与裁决口径一致。

**落账纪律（C-6）**：本批次内容提交哈希为 `f6b1e50`（分支 ff 合入 main）；本登记行为后续回填 commit。

---

## 批次三十四（2026-08-17）——I-1 集成验收启动：后端侧就绪证据包

**触发**：用户授权推动 I-1 集成验收（M1 实施计划 v1.1 §四 集成层：浏览器端三类产出物各走通一条全闭环）；协调人完成后端侧就绪自检并归档演示证据，墙上发起前端轨联调。

**变更内容**（commit `80f0c1a`，feat(tools)，分支 feat/i1-backend-smoke ff 合入）：
1. **后端侧演示冒烟脚本**：`backend/scripts/i1_backend_smoke.py`——对运行中的真实服务（非测试替身）走通 gate0-planning-slice 全链路：身份 setup/login → 需求源 → 工作项 → 会话生成三类产出物（4 条审核任务：strategy/plan 各 1 + case 2）→ TEST_STRATEGY/TEST_PLAN 退回→产出物回 DRAFT→新版本递增+新审核任务+旧任务 STALE_VERSION→批准；TEST_CASE 批准链路；陈旧任务决策 409 拦截；会话收敛 SUCCEEDED、工作项 APPROVED、终态任务 TASK_CLOSED。实测 **24/24 断言全绿**，ruff/mypy 干净。
2. **联调环境就绪实证**：后端服务 23 paths 存活；前端 vite dev 代理（5173 → 8000）实测连通（/health 与 /api/v1/auth/status 双通）；本地 dev 库已重置为全新（setupRequired=true），旧冒烟库归档 /tmp 可恢复。
3. **前端接缝核实**：api.ts 已含信封/CSRF/credentials 真实客户端；审核台现走 src/mock，切换数据源为前端轨联调唯一主要改动面。

**待办**：前端轨切真实 API 后在浏览器走通三类产出物全闭环（演示记录+截图归档）；双轨证据齐备后走 M1 验收流程（双轴评审 → 用户确认 → M1 VERDICT → v1.0-m1 标签）。

**落账纪律（C-6）**：本批次内容提交哈希为 `80f0c1a`（分支 ff 合入 main）；本登记行为后续回填 commit。

---

## 批次三十五（2026-08-18）——M1-P1：LangGraph 编排承载 Provider 四项加固

**触发**：M1 实施计划 v1.1 §M1-P1 分支 A（Provider 接口扩超时/重试/降级/成本四项＋坏 provider 防御测试）；用户授权结合 langchain/langgraph 技能继续后端开发。

**变更内容**（commit `1d34c13`，feat(M1-P1)，分支 feat/provider-interface-hardening ff 合入）：
1. **依赖**：引入 `langgraph>=1.0,<2.0`（实装 1.2.11，langchain-core 1.5.5 / langsmith 0.11.0 传递引入，符合 LangChain 1.0 LTS 基线）；`uv.lock` 随批提交。
2. **LangGraph 编排图**（新 `backend/src/qf/orchestration/planning_graph.py`）：`PlanningState` TypedDict（failover_events 挂 operator.add reducer），summarize→strategy→plan→cases 四节点确定性链，节点挂 `RetryPolicy(max_attempts=3)` 兜底；版本 ID 由服务层预分配经 state 注入；节点只返回 partial update。
3. **Provider 四项加固**（新 `backend/src/qf/providers/hardening.py`）：`HardenedPlanningProvider` 装饰器——超时（`generation_timeout_ms` 配置项，默认 5000ms）、重试（max_attempts=3，backoff 可注入）、降级（重试耗尽或输出结构判分失败→failover 到 deterministic-local；降级目标也失败则 fail-closed 抛 503 GENERATION_UNAVAILABLE）、成本（每次调用追加一行到 `provider_call_records`，sqlite_store 增量 v3 建表，只追加不参与全量快照）。
4. **输出结构判分**：strategy/plan 复用既有 Pydantic schemas（TestStrategyVersionCreate/TestPlanVersionCreate），cases 按确定性 provider 输出契约做形状校验。
5. **产出物追溯**：artifact 的 providerId/providerVersion 改为按生成方法追溯实际成功提供者（failover 后落 deterministic-local）。
6. **测试**（新 `backend/tests/test_provider_hardening.py`）：三类坏 provider fixture（Timeout/InvalidOutput/Exploding）验证 failover、成本记录断言、图编排顺序与 failover 留痕；**38/38 全绿**（既有 33 条 characterization 零回退）。

**门禁实证**：ruff 干净；mypy strict 24 文件零错；`make contract` 绿（外部契约零变更）。

**待办**：I-1 联调复验（smoke 脚本对 LangGraph 链路等价性 24/24 + 重置 dev 库）；前端轨闭环仍按批次三十四待办推进。

**落账纪律（C-6）**：本批次内容提交哈希为 `1d34c13`（分支 ff 合入 main）；本登记行为后续回填 commit。

---

## 批次三十六（2026-08-18）——M2 后端：看板数据面 3 operation + 列表过滤/分页

**触发**：用户指令「根据计划和方案继续完成开发，目标是把项目后端开发完成」；开发计划与方案-v1.1 §四 M2 验收标准（看板 7 类视图查询/筛选/分派数据接口）。

**变更内容**（commit `dc18b0e`，feat(m2)，分支 feat/m2-be-workboard ff 合入）：
1. **新 operation ×3**（25→28，延期 83→80）：
   - `getWorkItem`（GET /work-items/{workItemId}，未知 ID 404 NOT_FOUND）；
   - `listWorkItemRuns`（GET /work-items/{workItemId}/runs，关联 Agent Session 按启动时间倒序，看板 Diff/追溯数据面）；
   - `createReviewTask`（POST /review-tasks，201，手工分派入口：Idempotency-Key 幂等 + contentDigest 与当前版本不一致则 409 STALE_ARTIFACT_VERSION；无会话链接，decide_review 对手工任务容错跳过会话收敛）。
2. **查询增强**：`listWorkItems` 加 status 过滤（WorkItemStatus 枚举 Literal 校验）与 page/pageSize 分页（GenericListResponse 信封：page/pageSize/total 与 data 同级；无分页参数保持数组返回兼容既有测试）；`listReviewTasks` 加 assigneeId/status 过滤。
3. **能力与 schema**：`ALL_LOCAL_CAPABILITIES` 加 `review.create`；新增 `ReviewTaskCreate`/`ReviewTaskAssignee`（extra=forbid，契约 32 号字段）与 `success_paged()` 分页信封。
4. **修复**：幂等指纹对嵌套 UUID（assignees 列表）深度序列化（新增 `_serialize_entry`）。
5. **测试**：新 `tests/test_m2_workboard.py`（6 条：详情/404、运行历史、手工分派+幂等+陈旧 digest、status 过滤+分页信封、assignee/status 过滤、资源校验）；`test_openapi_contract.py` 三处同步（25→28、清单+3、KNOWN_DEFERRED_COUNT 83→80）；`test_operations_happy_path.py` 链路补齐 3 新 operation 覆盖。

**门禁实证**：44/44 全绿；ruff 干净；mypy strict 24 文件零错；`make contract` 绿（外部契约零变更）。

**待办**：墙通告 M-130 @autoclaw（看板数据面就绪）；随后按同纪律推进 M3 执行链路。

**落账纪律（C-6）**：本批次内容提交哈希为 `dc18b0e`（分支 ff 合入 main）；本登记行为后续回填 commit。

---

## 批次三十七（2026-08-18）——M3 后端：执行链路 4 operation + 不可变证据人工批准 + 存储 v4

**触发**：用户指令「根据计划和方案继续完成开发，目标是把项目后端开发完成」；开发计划与方案-v1.1 §四 M3 验收标准（治理先行、3 执行 operation、不可变证据、三条隔离验证 P2-4、C3 存储增量改造 P2-5）。

**变更内容**（治理先行 commit `60fb8a3` + 业务 commit `3592248`，分支 feat/m3-be-execution ff 合入 main）：
1. **治理先行（验收条件 1）**：`execution-workflow.json` 先于业务代码合入（4 节点 DAG：fixture→test-data→execution_run→evidence_gate BLOCK_HUMAN，createsReviewTasksFor EXECUTION_EVIDENCE，intersection_fail_closed + humanOnlyActions 含 approve_execution_evidence）；`agents.json` 新增 qf-execution（deniedActions 含 modify_test_or_evidence）；`validate.py` 扩展同构校验（allowedSkills/DAG 拓扑/evidence_gate/runner），PASS：5 agents。
2. **新 operation ×4**（28→32，延期 80→76）：`createExecutionPlan`（201，自动生成冻结首版，contentDigest 服务端计算）、`startExecutionPlan`（202，Idempotency-Key 幂等；同版本重放 409 EXECUTION_ALREADY_RUN）、`listExecutionResults`（executionTaskId 必填）、`listExecutionTasks`（workspaceId 过滤）。
3. **不可变证据（验收条件 2）**：每用例一条证据（stdout/stderr/exitCode），digest＝服务端对三字段规范化 JSON 的 sha256，客户端无从注入；证据走 append-only 表（不参与全量快照 save），不被分析覆盖；每条证据自动创建 EXECUTION_EVIDENCE 审核任务（SINGLE_REVIEW，digest 一致才放行批准，能力键 evidence.approve）；decideReviewTask 三处容错支持非正式产出物类型。
4. **三条隔离验证（验收条件 3，P2-4）**：直写 store 篡改（json_set exitCode）→ verify_evidence_integrity fail-closed 409 EVIDENCE_TAMPERED；伪造 digest（服务端规范化计算断言）；重放旧摘要（版本重放 409 + 批准陈旧 digest 409 STALE_ARTIFACT_VERSION）。启动加载时自动校验，篡改存储拒绝服务。
5. **C3 存储增量改造（验收条件 4，P2-5）**：SCHEMA_VERSION 3→4（执行 4 集合表 + execution_evidence 只追加表，_ensure_collection_tables 幂等补建存量库）；并发回归（3 路同键 start 收敛为一个任务）；最薄恢复证据口径（_reload_store_state 模拟重启后完整性校验通过）；最薄性能基线哨兵（save 1.2ms / load 1.2ms / 证据追加 0.4ms，>1s 视为数量级退化）。
6. **测试与契约同步**：新 `tests/test_m3_execution.py`（7 条）；`test_openapi_contract.py` 四处同步（28→32、清单+4、KNOWN_DEFERRED_COUNT 80→76、注释）；happy-path 链路补执行链段（createExecutionPlan→startExecutionPlan→listExecutionTasks→listExecutionResults）。

**门禁实证**：51/51 全绿；ruff 干净；mypy strict 25 文件零错；`make contract` 绿（外部契约零变更）；validate.py PASS（5 agents）。

**待办**：墙通告 M-131 @autoclaw（执行链就绪，证据审核页数据面）；随后推进 M4 分析/Defect/报告纵向切片。

**落账纪律（C-6）**：本批次内容提交哈希为 `60fb8a3`（治理）与 `3592248`（业务，ff 合入 main）；本登记行为后续回填 commit。

---

## 批次三十八（2026-08-18）——M4 后端：质量域纵向切片 11 operation + 存储 v5

**触发**：用户指令「根据计划和方案继续完成开发，目标是把项目后端开发完成」；开发计划与方案-v1.1 §四 M4 验收标准（ResultAnalysis/Defect/TestReport/知识回流纵向切片、Defect 与 FailureCluster 分离、B2-4 外部同步批准+回执、覆盖率 effective 口径）。

**变更内容**（commit `903a687`，分支 feat/m4-be-quality ff 合入 main）：
1. **新 operation ×11**（32→43，延期 76→65）：`createResultAnalysis`（结论三层分离 facts/inferences/decisions，digest 服务端算）、`listFailureClusters`、`createDefect`、`listDefects`、`createDefectVersion`（自动建 DEFECT_VERSION 审核任务）、`createDefectSyncAttempt`、`createTestReport`、`listTestReports`、`createCoverageReport`、`listCoverageReports`、`createKnowledgeEntry`。
2. **Defect 与 FailureCluster 分离（验收条件）**：failure_clusters 独立集合；对 FAILED/ERROR 结果按 {status, stderr} 规范化 digest 派生 clusterKey，同签名归并 memberCount+=1，新簇 status OPEN；缺陷另走 defects/defect_versions 生命周期。
3. **B2-4 外部同步批准+回执（验收条件）**：同步必须引用已批准且指向该版本的审核任务否则 403；payloadDigest 与服务端重算不一致 422 PAYLOAD_DIGEST_MISMATCH（回显 expectedDigest）；成功 202 ACKNOWLEDGED + receiptDigest（七字段规范化摘要）；payload writeOnly 不落库不回显；Idempotency-Key 重放同 id。
4. **覆盖率 effective 口径强制（验收条件）**：五维度（rule/scenario/state/assertion/api）分母互不推导，至少一个显式提供否则 422；EFFECTIVE 口径强制 ruleDimension；verdict（SATISFIED/PARTIAL/INSUFFICIENT）服务端计算，客户端无从操纵。
5. **批准挂钩**：decide_review 批准 DEFECT_VERSION 时回填根记录 approvedVersionId（同步前置）；APPROVAL_CAPABILITIES 新增 artifact.defect_version.approve；auth 新增 quality.write/quality.sync/artifact.defect_version.approve/knowledge.publish 四能力。
6. **存储 v5**：SCHEMA_VERSION 4→5，+8 集合表（result_analyses/failure_clusters/defects/defect_versions/defect_sync_attempts/test_reports/coverage_reports/knowledge_entries），_ensure_collection_tables 幂等补建存量库。
7. **测试与契约同步**：新 `tests/test_m4_quality.py`（6 条：全链、未批准 403、伪造摘要 422、维度强制、资源 404×2）；`test_openapi_contract.py` 四处同步（32→43、清单+11、KNOWN_DEFERRED_COUNT 76→65）；happy-path 链路补质量域段（11 个 record 调用）。

**门禁实证**：57/57 全绿；ruff 干净；mypy strict 27 文件零错；`make contract` 绿（外部契约零变更）。

**待办**：墙通告 M-132 @autoclaw（质量域数据面就绪）；随后推进 M5 Provider 切换面 + make eval 基线。

**落账纪律（C-6）**：本批次内容提交哈希为 `903a687`（ff 合入 main）；本登记行为后续回填 commit。

---

## 批次三十九（2026-08-18）——M5 后端：Provider 黄金集评估闸门 + make eval 基线归档（C2/C8）

**触发**：用户指令「根据计划和方案继续完成开发，目标是把项目后端开发完成」；开发计划与方案-v1.1 §四 M5 验收标准（黄金集达标＋结构判分通过方可切换，不达标走 Plan B；make eval baseline 归档；deterministic-local 保留为 failover 与评估锚点）。

**变更内容**（commit `a85ed94`，分支 feat/m5-be-eval-gate ff 合入 main）：
1. **黄金集评估闸门**（`providers/golden_eval.py`）：固定黄金集语料四步回放（summarize/strategy/plan/cases），结构判分复用硬化层同一套契约校验器；2 条负例（空摘要/缺必填字段）零容忍，false-accept 必须为 0；零 LLM-judge。
2. **切换面 fail-closed**：`switch_provider` 候选不达标 422 PROVIDER_GATE_REJECTED（details 含 structureFailures/falseAccepts），当前 provider 保持（Plan B）；达标切换后重建加固层与 LangGraph 编排图；每次尝试（成/败）落 PROVIDER_SWITCH 不可变台账，供版本门禁 AI 类证据审计。
3. **基线归档**（`prototypes/skills/evals/baseline/planning-golden-baseline.json`）：deterministic-local 锚点生成，逐字节确定性（剔除 plan 日期漂移字段）；核验对漂移/缺失 fail-closed。
4. **Makefile**：新增 `make eval`（Skill evals + Provider 闸门与基线核验）、`make eval-baseline`（重新归档）；`make test` 纳入闸门回归。
5. **踩坑**：黄金集固定 ID 必须为合法 UUID（plan 校验 uuid_parsing），改用 uuid5；基线摘要须剔除 plan 的 startDate/endDate 否则每天漂移。

**门禁实证**：61/61 全绿；ruff 干净；mypy strict 28 文件零错；`make contract` 绿；`make eval` PASS（30 套件 103 用例 14 runners + 结构判分 4/4 + 负例 false-accept=0）。

**待办**：墙通告 M-134 @autoclaw（降级状态呈现的数据面：切换拒绝/降级事件可观测）。

**落账纪律（C-6）**：本批次内容提交哈希为 `a85ed94`（ff 合入 main）；本登记行为后续回填 commit。

---

## 批次四十（2026-08-18）——V1 版本门禁六类证据包归档 + 78203cd 污染事故与恢复

**触发**：22 号文档 §7 六类版本门禁 × 开发计划与方案-v1.1 §四「V1 试点总验收」第 3 条；V1 后端轨收口后组装门禁证据基线包。

**变更内容**：
1. **证据包归档（commit `78203cd` 中的证据包文件部分）**：`deliverables/2026-08-18/V1版本门禁六类证据包-2026-08-18.md`——产品/质量/安全/AI/运行/发布六类必需证据逐条指针化（文件/命令 → 结果，全部可复跑）；运行类最薄口径实证：全新库启动→建数据→`kill -9` 强杀→同库重启→启动完整性校验通过、数据无损（PASS）；试点前置遗留四项（用户验收记录/人工验收实测/人工修改率/合规五缺口）书面列明。
2. **事故记录（commit `78203cd` 非预期部分）**：该提交在归档证据包时误带入基于批次三十五状态的旧工作区快照，连带回滚了 M2–M5 后端成果（quality.py/golden_eval.py 等 4 源文件与 4 个 M 级测试文件被删、planning_workflow/sqlite_store 回退、治理 execution-workflow.json 与黄金集基线被删）并抹除本文件批次三十六～三十九条目；同时混入 autoclaw 前端轨 WIP 快照。
3. **恢复（commit `1699d81`，fix(recovery) 合入 main）**：从 `56218e9` 逐字节恢复 24 文件（恢复后 `git diff 56218e9` 于 backend/prototypes/Makefile/docs 路径为空）；恢复后五门禁全绿复验：pytest 61/61、ruff+mypy strict 28 文件零错、`make contract` OK、`make eval` PASS（结构判分 4/4、负例 false-accept=0）、治理校验 PASS（5 agents）；前端文件不在恢复范围，保持不动。

**教训**：归档提交前必须 `git status` + `git diff --stat HEAD` 全量核实暂存面与 HEAD 的偏差，工作区存在并行轨 WIP 时只允许按文件路径精确 add，禁止全量提交。

**落账纪律（C-6）**：本批次内容提交哈希为 `78203cd`（证据包，含污染）与 `1699d81`（恢复）；本登记行为后续回填 commit。

---

## 批次四十一（2026-08-18）——V1 试点总验收后端工作包：事件采集管道与 D3 指标计算

**触发**：开发计划与方案-v1.1 §四「V1 试点总验收」第 4 条 D3（事件采集管道正常产出效率指标、无手工录入）× 20 号文档 §1.1 O3 裁决（✅ 可计算项 25 个 metricKey 须管道产出）；契约先行双人确认（§3.0）由墙 M-136 发起。

**变更内容**：
1. **契约先行（commit `af8088a`）**：`32-API规范.yaml` 新增 Observability tag 与两个只读 op（108→110，不占延期口径）——`listEvents`（GET /observability/events，workspaceId/subjectType/eventType 过滤 + 分页信封）、`listMetrics`（GET /observability/metrics，逐项 metricKey/value/numerator/denominator/window/computedAt/basis，显式分母口径、无目标值，AC-04 合规）；墙 M-136 通告 @autoclaw 契约增量。
2. **存储 v6（实现 commit `a800b5d`）**：SCHEMA_VERSION 5→6，新 `domain_events` append-only 表（event_id/occurred_at/actor_id/workspace_id 可空/subject_type/subject_id/event_type/correlation_id/payload_json/payload_digest/prev_digest）+ 两索引；哈希链（prev_digest 串链，GENESIS 起步）；不进全量快照；启动加载与查询前 fail-closed 校验（EVENT_CHAIN_TAMPERED 409）；`_ensure_collection_tables` 幂等补建。
3. **领域事件管道（服务端独占生成，无客户端写入面）**：`services/events.py` DomainEventService（emit/verify_chain/list_events/load_events）；10 类事件登记表钉死：artifact.version.generated / review.decided / work_item.transitioned / session.converged(SUCCEEDED/FAILED/BLOCKED) / execution.started / execution.finished / evidence.appended / defect.version.created / provider.switched / provider.failover；planning_workflow 埋点 12 处（provider 两类为全局事件 workspace_id=None、tenant=SYSTEM）。
4. **指标计算服务**：`services/metrics.py` 25 项 ✅ metricKey 全部纯服务端计算（eff×6、qual×8、ai×9、trace_version_summary_completeness、ops_degrade_rate），零手工录入；事件流型从 domain_events 计算，台账型从 provider_call_records/golden_eval/defects/knowledge 等既有台账计算；ai_gs_accuracy/recall 以黄金集闸门级代理口径实时评估并显式声明；每项输出 numerator/denominator/basis，window=FULL_HISTORY；无目标值字段（AC-04）。
5. **API 只读双面**：`api/v1/observability.py`（listEvents/listMetrics，workspaceId 403 门控，能力只读）；main.py 注册。
6. **测试与冒烟**：新 `tests/test_v1_events_metrics.py` 8 例（登记表钉死、未登记类型拒绝、sqlite 直写篡改检出与还原恢复、无写入面断言、fixture 口径、HTTP 双面 200、篡改 409 fail-closed、口令卫生）；契约测试 43→45（延期 65 不变）；happy-path 补链 2 op；冒烟脚本扩展 Journey C 执行链 + D3 断言（事件流非空 + 6 类核心事件齐备 + 25 项 metricKey + 5 个 eff 事件流型 key 非 None），全新库 8001 端口隔离实证 32/32，输出归档 `deliverables/2026-08-18/D3事件管道冒烟输出-2026-08-18.txt`。

**门禁实证**：69/69 全绿；ruff 干净；mypy strict 31 文件零错；`make contract` 绿（openapi-spec-validator）；`make eval` PASS（30 套件 103 用例 14 runners + 黄金集闸门 4/4、负例 false-accept=0）；D3 冒烟 32/32。

**待办**：墙通告 M-137 @autoclaw（数据面接口说明：GET /api/v1/observability/events|metrics）；试点 Workspace 选定后 D4 基线数据随试点自然产出；合规五缺口（24-合规与隐私设计.md）为接真实模型前置的下一候选批次。

**落账纪律（C-6）**：本批次内容提交哈希为 `af8088a`（契约先行）与 `a800b5d`（实现，直推 main）；本登记行为后续回填 commit。

---

## 批次四十二（2026-08-18）——合规五缺口文档批次：立项 24-合规与隐私设计.md（OPN-04 关闭）

**触发**：台账裁决（批次三十三：合规 5 缺口不阻塞 V1，但出站审批与保留期限须在接真实模型前关闭）× 40 号产品全面评估报告 D.1.5/D.3（新建 24-合规与隐私设计.md）× 用户拍板（文档批次收口全部五缺口；强制项给数字/流程，其余给策略声明）。

**变更内容**：
1. **新建 `docs/03-governance/24-合规与隐私设计.md`**（commit `b8fbcf4`，合规与隐私域现行权威源）：五章对应五缺口——①GDPR/数据主体权利（数据驻留策略：V1 本地单区零跨境；被遗忘权五步删除流程复用 clear_workflow；导出权经既有只读面自取，专用 op 延后 V2）；②保留期限数字（强制）：domain_events/provider_call_records/defect_sync_attempts 365 天、execution_evidence 180 天、业务数据随租户存续；策略设计值标注试点后校准，到期清理实装归接真实模型批次（含哈希链重锚方案声明）；③LLM 出站审批（强制）：切换真实 Provider 双闸门（M5 黄金集闸门已实现 + 出站审批记录台账）+ Prompt 脱敏最小化出站白名单；V1 deterministic-local 零出站口径显式声明；④指标数据字典：51 项登记表字典化，25 项 ✅ 基线指向 metrics.py/listMetrics 实装，✅ 未入基线 3 项/⚠️/❌ 项按 O3 三档处置声明；⑤permissionKey 目录：ALL_LOCAL_CAPABILITIES 16 项能力键语义表 + V1 单租户全量授予口径。
2. **指针同步**：20-非功能需求.md §5 安全与隐私加指针；54-总索引 §4 登记 24 号文档。
3. **OPN-04 关闭**：SRS docx 开放问题清单不重新生成，状态以本登记与墙 M-138 为准。

**门禁实证**：本批纯文档零代码面：`make contract` 绿（契约零变更回归）；backend/ 与 main 逐字节一致（git show main:逐文件 diff 四新文件 OK）；五缺口逐项自查：两项强制含数字/流程、三项含声明与豁免清单。

**待办**：接真实模型批次（C2 前置）按 24 号文档 §2.2/§3.2 实装到期清理与出站审批台账（契约先行另起工作包）；试点 Workspace 选定与 D1/D2/D4 联调仍归用户决策/autoclaw 轨。

**落账纪律（C-6）**：本批次内容提交哈希为 `b8fbcf4`（plumbing 直推 main）；本登记行为后续回填 commit。

---

## 批次四十三（2026-08-18）——TestReport 版本层完整审核链接入（P0-1 裁决挂账闭合，45→47）

**触发**：CHANGELOG 契约修复批次 P0-1 裁决挂账（「版本查询 operation 路径待后端接入时补，届时同步 KNOWN_DEFERRED_COUNT」）× 三向差距实证（契约有 TestReportVersion schema 与根双指针但版本层 op 缺失、TestReportCreate 请求体残留根层字段的内部矛盾、后端根层错位双指针恒 None）× 用户拍板（完整审核链模式，对齐 defect_version）。

**变更内容**：
1. **契约先行（commit `84d2b3c`）**：`32-API规范.yaml` 110→112（不占延期口径，延期仍 65）——新增 `listTestReportVersions`（GET /quality/reports/{testReportId}/versions 分页信封）与 `createTestReportVersion`（POST 同路径 201，请求体 scopeSnapshotRef/executionSnapshotRef/qualityConclusion/changeSummary 必填 + 四可选，version/contentDigest/reviewStatus/supersedesVersionId 服务端产出）；TestReportCreate required 收紧为 [workspaceId, releaseId, reportKey]（移除两快照字段，消 P0-1 契约内部矛盾，破坏性收紧已墙 M-139 显式告知）；新增 TestReportVersionResponse/TestReportVersionListResponse。
2. **后端实现（commit `93d6e6b`，对齐 defect_version 模式）**：schemas TestReportVersionCreate（StrictRequest）；存储 v7（SCHEMA_VERSION 6→7，test_report_versions 集合映射登记 + _apply_v7 幂等补建）；planning_workflow create_test_report_version（PENDING_REVIEW + contentDigest 服务端计算 + 自动 TEST_REPORT_VERSION 审核任务 + _index_version + supersedesVersionId 上一版指针）、list_test_report_versions（404 NOT_FOUND + workspaceId 403 门控）、decide_review APPROVE 分支回填根 currentVersionId；APPROVAL_CAPABILITIES + 项；auth_service ALL_LOCAL_CAPABILITIES 16→17（artifact.test_report_version.approve）；API 两路由（quality.write）。报告版本不入事件登记表（10 类 EVENT_TYPES 钉死，指标无依赖）。
3. **测试**：契约清单 45→47（KNOWN_DEFERRED_COUNT=65 不变）；test_m4_quality 步骤 6 扩为根→版本→审核任务→APPROVE→根指针回填全链（含 publishedVersionId 维持 None、404 负例）；happy-path 补两 op 链；24-合规与隐私设计.md §5 permissionKey 目录 16→17。

**门禁实证**：pytest 69/69（既有零回退）；ruff 干净；mypy strict 31 文件零错；`make contract` 绿；`make eval` PASS（30 套件 103 用例 + 黄金集闸门 4/4、负例 false-accept=0）；契约/DDL/后端三向一致自查（TestReportVersion 字段、双指针语义、九值 reviewStatus）。

**待办**：publishedVersionId 与 REPORT_SIGNOFF 签署流程归后续切片（根 docstring 已声明）；墙 M-139 契约确认按 R7 口径（无回帖异议继续）。

**落账纪律（C-6）**：本批次内容提交哈希为 `84d2b3c`（契约先行）与 `93d6e6b`（实现，plumbing 直推 main）；本登记行为后续回填 commit。

---

## 批次四十四（2026-08-19）——看板工作项分派 + SLA 面板两 op 接入（M2/U3-U4，47→49）

**触发**：开发计划看板增强切片 M2/U3（看板 SLA 面板：按优先级逾期/达成呈现）× M2/U4（工作项分派落库）；契约先行双人确认（§3.0）由墙 M-141 发起。

**变更内容**：
1. **契约先行（commit `a0ca77c`）**：`32-API规范.yaml` 112→114（不占延期口径，延期仍 65）——新增 `listWorkItemSlaOverview`（GET /work-items/sla-overview，workspaceId 403 门控，按优先级 P0/P1/P2 分组 {total, met, overdue, metRate} + 整体汇总）与 `assignWorkItem`（POST /work-items/{workItemId}/assign 200，请求体 workspaceId + assigneeId 必填）；新增 WorkItemAssignRequest / WorkItemSlaGroup / WorkItemSlaOverview schema 与 WorkItemSlaOverviewResponse；墙 M-141 通告 @autoclaw 契约增量。
2. **后端实现（commit `b58472a`）**：
   - **SLA 面板（服务端独占口径）**：SLA_WINDOW_HOURS 常量（P0=24h/P1=48h/P2=72h）；截止 = createdAt + 窗口；DONE/APPROVED 且 updatedAt ≤ 截止 = met，未完成且已过截止 = overdue；P3/缺创建时间（无 due）只计 total 不算 overdue；CANCELLED 只计 total；metRate = met/total（total=0 时 0）。
   - **幂等分派**：工作项不存在/跨 workspace 404；同人重分派为 no-op（不落 updatedAt、不产生事件）；变更分派落 updatedAt 并追加 work_item.assigned 事件（事件登记表 10→11 类，payload 含 fromAssigneeId/toAssigneeId）；操作天然幂等无需 Idempotency-Key。
   - **能力键**：ALL_LOCAL_CAPABILITIES 17→18（work_item.assign）；24 号文档 §5 目录同步 + 变更记录。
3. **测试**：契约清单 47→49（KNOWN_DEFERRED_COUNT=65 不变）；happy-path 补两 op 链（分派 + 同人重分派幂等断言 + SLA 面板分组序与 total>0）；事件登记表钉死测试同步 11 类。

**门禁实证**：pytest 72/72 全绿（69→72，既有零回退）；ruff 干净；mypy strict 31 文件零错（修复一处 priority 窄化 index 报错）；`make contract` 绿（openapi-spec-validator）；`make eval` PASS（30 套件 103 用例 14 runners + 黄金集闸门 4/4、负例 false-accept=0）；agent-governance validate PASS。

**待办**：墙 M-142 完成通告 @autoclaw（数据面接口说明）；前端看板 SLA 面板与分派交互归 autoclaw 轨。

**落账纪律（C-6）**：本批次内容提交哈希为 `a0ca77c`（契约先行）与 `b58472a`（实现，plumbing 直推 main）；本登记行为后续回填 commit。

---

## 批次四十五（2026-08-19）——审核队列版本 Diff 数据面接入（M2 后端轨收口，49→50）

**触发**：开发计划 v1.1 §M2 后端轨剩余项「版本 Diff 数据接口」（SLA 已在批次四十四完成）；10 号 PRD §3 审核队列「预检摘要、证据、Diff 和阻断检查」的 Diff 承载面；契约先行双人确认（§3.0）由墙 M-143 发起。

**变更内容**：
1. **契约先行（commit `87ac436`）**：`32-API规范.yaml` 114→115（不占延期口径，延期仍 65）——新增 `getReviewArtifactDiff`（GET /review-tasks/{reviewTaskId}/artifact/diff，200/404）；新增 ReviewArtifactDiff / ReviewArtifactDiffField schema 与 ReviewArtifactDiffResponse；墙 M-143 通告 @autoclaw 契约增量。
2. **后端实现（commit `b75a6b0`）**：
   - **base 推导（设计裁决）**：实现期实证 `supersedesVersionId` 仅 TEST_REPORT_VERSION 独有，故不新增回填字段，改为同根兄弟版本运行时推导（复用既有 `_artifact_id` 根 id 判定）：version_index 内同类型同根、版本号小于 head 的最大版本为 base（正常链即 version-1 相邻）；契约 yaml 描述同步修正并随实现入库。
   - **字段级 diff（服务端独占口径）**：content 顶层字段对比剔除 tenantId/workspaceId（与 getReviewArtifact 同口径）；ADDED/REMOVED/CHANGED 三枚举，值按 JSON 等价比较，fields 按字段名字典序，changedCount = len(fields)；首版或 base 链断裂降级 hasBaseline=false + fields 空数组（不报错）；只读投影不产生事件。
3. **测试**：契约清单 49→50（KNOWN_DEFERRED_COUNT=65 不变）；test_m2_workboard 新增 diff 专项（首版降级 + 二版 CHANGED 字段断言与字典序 + 404 负例）；happy-path 补 getReviewArtifactDiff 链。

**门禁实证**：pytest 73/73 全绿（72→73，既有零回退）；ruff 干净；mypy strict 31 文件零错；`make contract` 绿；`make eval` PASS（30 套件 103 用例 + 黄金集闸门）；agent-governance validate PASS。

**待办**：墙 M-144 完成通告 @autoclaw（含 supersedes→同根推导口径修正说明）；前端审核队列 Diff 呈现归 autoclaw 轨。至此 M2 后端轨全部收口。

**落账纪律（C-6）**：本批次内容提交哈希为 `87ac436`（契约先行）与 `b75a6b0`（实现，plumbing 直推 main；首次实现提交 `ec33eb5` 因跨 shell 会话丢失 GIT_INDEX_FILE 致树基于陈旧分支索引，已重建为 `b75a6b0` 并验证树完整性）；本登记行为后续回填 commit。

---

## 批次四十六（2026-08-19）——前端真实模式联调面补齐六 op（50→56，联调缺口清零）

**触发**：2026-08-19 后端进度盘点 §三 联调缺口（前端 dataService 注释登记的「契约有定义、后端暂无路由」四项 + fetchAnalyses/ProviderStatus 两个在调未入契约面）× 墙 M-136 autoclaw 请求（Provider 状态数据面）× 契约先行双人确认（§3.0）墙 M-145。

**变更内容**：
1. **B1 补全先行（commit `3cd8254`）**：基线核验发现 main 为红（B1 测试已在 main 但存储 v8 迁移与 ExecutionResult 响应模型缺失，72/73）——内容取自 `9d04f72` 严格超集校验后逐字节恢复（存储 v8 迁移/响应模型/三层一致测试），main 由红转绿 73/73。
2. **契约先行（commit `d0fc4b4`）**：`32-API规范.yaml` 115→117——新增 `listResultAnalyses`（GET /quality/result-analyses，workspaceId 403 门控分页信封）与 `getProviderStatus`（GET /ai/provider/status，响应 status NOMINAL|DEGRADED + providerId/providerVersion/fallbackProviderId?/reason?/since?，与前端 ProviderStatus 类型对齐）；新增面不占延期口径。
3. **后端实现（commit `e43545f`，六 op 补齐）**：
   - 契约新增两面：`listResultAnalyses`（只读投影，workspaceId 403 门控）；`getProviderStatus`（服务端独占口径：DEGRADED 仅当硬化层最近 24h 内记录到 failover（PROVIDER_DEGRADED_WINDOW_HOURS），过期自动回落 NOMINAL；V1 deterministic-local 默认链路恒 NOMINAL，前端直接呈现勿重算）。
   - 契约既有四 op 补路由：`listExecutionPlans`/`listKnowledgeEntries`/`listEnvironments`（均为只读投影 + workspaceId 403 门控）/`createEnvironment`（workspaceId 取路径参数不在请求体；capabilities/secretRefs 可选缺省落 {}/[]；能力键 `environment.create` 18→19，ALL_LOCAL_CAPABILITIES 同步）。
   - 存储：`environments` 集合映射登记，`_ensure_collection_tables` 幂等补建存量库。
4. **测试**：契约清单 50→56；KNOWN_DEFERRED_COUNT 65→61（口径修正：M-145 墙上「65→59」为笔误，实为 117−56=61，以契约测试断言为准）；新 `test_batch46_integration_gaps.py`（环境创建→列表回环缺省落默认值、403 门控、DEGRADED 窗口口径）；happy-path 补链。

**门禁实证**：pytest 77/77 全绿（73→77，既有零回退）；ruff 干净；mypy strict 31 文件零错；契约测试内嵌 openapi-spec-validator 校验绿（权威 yaml 合法 + 运行时切片 operationId 逐一比对）。

**待办**：墙 M-146 完成通告 @autoclaw（六 op 数据面接口说明 + createExecutionPlan 真实模式 payload 错位提醒重申）；前端真实模式接入归 autoclaw 轨。至此联调缺口（契约有定义后端无路由）清零。

**落账纪律（C-6）**：本批次内容提交哈希为 `3cd8254`（B1 补全修复）、`d0fc4b4`（契约先行）与 `e43545f`（实现，plumbing 直推 main）；本登记行为后续回填 commit。另登记：会话恢复时发现 git 索引被意外清空（ls-files=0 全量 staged deletion），以 `git read-tree HEAD` 无损恢复，工作区零丢失；后续 plumbing 链提交前先 `git ls-files | wc -l` 自检。

---

## 批次四十七（2026-08-27）——57项产品裁决需求基线回填

1. 新增`06-人机协作与V1业务基线`，统一产品定义、4类V1人类角色、四产品平面、单一主旅程、阶段显式交接、对话+结构化工作台、独立评估Agent和V1边界。
2. 新增`23-产品裁决追溯矩阵`，将QF-PD-001～057逐项映射到产品、PRD、治理、架构和实现状态。
3. 新增`39-人机协作目标契约`，冻结Conversation、Clarification、TaskCard/AgentPlan、RunCommand、EvaluationRun与三类投影的目标契约和激活门禁。
4. 回填01/02/03/04/05、10/16、21/22/55、31/32/33/36/37/54，消除“八个能力域=八个一级菜单”、“三条并列旅程”、“V1无对话/人工运行控制/评估Agent”等旧口径。
5. 本批次是需求与目标契约基线，不包含业务代码、DDL迁移、新API路由或前端交互实现；新能力统一标记为`CONTRACT_PENDING/IMPLEMENTATION_PENDING`。

---

## 批次四十八（2026-08-27）——V1目标契约激活与实现Backlog

1. 新增`40-V1目标契约激活与实现Backlog`，将57项裁决分配到WP-00～WP-08，定义契约、DB、后端、前端、正反测试和验收证据的完成口径。
2. 确定首个开发切片为`WP-01A 真实项目/Release上下文`，先消除前端固定样例项目和随机releaseId，不提前开始首屏视觉改版。
3. 在Backlog拆分时发现并修正导航口径冲突：四个分面是业务组织，八个能力域是Owner边界，具体一级导航数量留待原型阶段裁决；只有“测试产出物取消一级菜单”已被QF-PD-010确认。
4. 本批次只完成Backlog和口径收口；WP-01A尚未修改OpenAPI、DDL或业务代码。

---

## 批次四十九（2026-08-30）——feat/m3-fe-execution 工作区收编与 WP-01A 后端开工

**触发**：分支自批次四十三后分叉，main 已推进批次四十四～四十六（b58472a/b75a6b0/e43545f 直推），且 2026-08-27 需求基线（批次四十七/四十八）与 WP-01A 起步工作长期滞留工作区未提交（含一个缩进破损的 happy-path 扩链），门禁无法整链运行。

**变更内容**：
1. **基线文档落库**：批次四十七/四十八全部产物（06/23/24/39/40 新文档 + 19 份权威源回填 + 复核报告 + deliverables/2026-08-27 诊断报告）提交入库。
2. **分支对齐重铺**：批次四十四～四十六后端成果以内容等价方式重铺本分支（六 op + 存储 v8 + B1 三层一致），后续 merge main 验证收敛。
3. **WP-01A 后端面开工**：`listWorkspaces`/`listReleases` 两路由 + 存储 v9（releases 集合表 + listReleases 服务面）+ happy-path 扩链（修复 08-29 编辑事故造成的 IndentationError）+ 契约清单 58/KNOWN_DEFERRED 59 口径落定。
4. **Skill 资产收编**：30 份 SKILL.md 描述精简重写 + `using-qualityforge` 路由元技能补齐（evals 清单 5 例 + 治理不变量 30→31）+ api-test-suite 74 用例资产 + test-skills 目标入 Makefile；127 断言/31 清单/14 runner 全绿。
5. **前端首屏口径**：ArtifactHub 页（/artifacts）+「测试产出物」一级菜单 + Release 名称接 profile.releaseName（WP-01A 前端面起步）。

**门禁实证**：pytest 77/77；ruff/mypy strict 零告警；make contract 绿；make test-skills 127 OK；make eval PASS（31 清单 108 用例 + 黄金集闸门 + 治理 31/31）；前端 vitest 49/49 + typecheck + lint 零告警。

**落账纪律（C-6）**：本批次为工作区收编提交，登记先于哈希；后续 merge main 后按超集取侧收敛。

---

## 批次五十（2026-08-30）——WP-01A 切片推进：Release 归属门控 + 前端全局上下文

**触发**：40 号 Backlog WP-01A（§6.1/§6.2）首个开发切片，承接批次四十九工作区收编。

**变更内容**：
1. **后端门控（QF-PD-001/002 承载面）**：createWorkItem 携带 releaseId 时必须存在、ACTIVE 且属于当前 Workspace，否则 409 RELEASE_NOT_IN_WORKSPACE（跨 Workspace/已归档/不存在同码拒绝）；32 号 createWorkItem description 同步登记。缺 releaseId 的交付任务必填门控依赖 WP-03 TaskContract 语义，届时落地。
2. **测试口径改造**：删除固定 RELEASE_ID（…-20）假归属写法，全部用例经 active_release_id/listReleases 取真实种子 Release；新增 test_wp01a_workspace_context.py 三用例（成员域投影/409 拒绝/种子通过）。
3. **前端全局上下文**：App 持有 workspaces/releases 状态，resolveProfileContext 统一解析当前 Release（pickCurrentRelease 服务端口径：ACTIVE 且 updatedAt DESC 取首位）；顶栏项目/Release 双切换器接真实列表（告别 toast 演示），切换 Workspace 重置 Release 且 profile 换引用触发全站查询刷新（不残留）。
4. **集成对齐**：e2e-integration 落地页断言从「工作看板」改为「测试产出物」（/artifacts 首屏口径）后显式导航看板。

**门禁实证**：pytest 80/80；ruff/mypy strict 干净；make contract 绿；前端 vitest 51/51 + typecheck + lint 零告警；真实后端集成 e2e 3/3（登录→建工作项落库走新门控全链）；mock 全量 e2e 82/82。

**未含（WP-01A 收尾件）**：lastBusinessUpdatedAt 服务端口径与排序负向（轮询/Trace 不刷新排序）、切换 Workspace 浏览器级 e2e（当前单 Workspace 种子，需二工作区种子面）。

---

## 批次五十一（2026-08-30）——WP-01A 收口件：lastBusinessUpdatedAt 口径 + 专用切换命令 + 双工作区 e2e

**触发**：批次五十登记的未含收尾件（40 号 Backlog §6.2 切换与排序负向）。

**变更内容**：
1. **lastBusinessUpdatedAt 服务端口径**：listWorkspaces 投影附该字段并按其 DESC 排序；口径 = 9 类业务领域事件（artifact/review/work_item/session/execution/evidence/defect）最大 occurredAt，显式排除 provider.switched/provider.failover 运行面事件，无事件回退 createdAt；32 号 Workspace schema 与 listWorkspaces description 登记。只读查询与 Agent Trace 不产生领域事件，故天然不刷新。
2. **成员关系存储 v10**：tenant_memberships 主键 (tenant_id, user_id) → (tenant_id, user_id, workspace_id)（表重建搬数），解除单用户单工作区假设；get_membership 加 rowid 确定性排序，新增 get_membership_for_workspace。
3. **专用切换命令 switchLocalWorkspace**（契约 118 个 op，实现 59 / 延期 59）：POST /auth/switch-workspace，成员关系校验通过后重签 JWT（新增 workspaceId claim，旧 token 无 claim 回退首行成员）+ 刷新会话 cookie；资源型端点 actor 工作区随切换生效（不落库、无通用 PATCH）。负向：非成员工作区 403；切换后旧工作区写入 403 隔离。
4. **种子面与 e2e**：`scripts/qf_seed_workspace.py`（幂等）+ `e2e-integration/workspace-switch.spec.ts`（切换→Release 重置→旧数据不残留→新上下文可写，未种子 skip）；README 路由修正 /execution-plans→/execution；.gitignore 补工具产物目录；HANDOFF 增补 WP-01A 节。

**门禁实证**：pytest 83/83（新增排序口径/只读与 provider 事件负向/切换命令绑定与隔离三件）；ruff/mypy strict 干净；make contract 绿（59/118/59）；前端 vitest 51/51 + typecheck + lint 零告警；真实后端集成 e2e 4/4（含新切换链）；mock 全量 e2e 回归见落账提交说明。

---

## 批次五十二（2026-08-30）——WP-01 收口：驾驶舱投影 + 常用项目置顶 + Release 归档（59→62 op）

**触发**：40 号 Backlog WP-01 剩余三件（39 号 §7.2 投影 / QF-PD-026 常用项目 / 归档数据面）；按 39 号 §10 激活门逐项落实。

**变更内容**：
1. **getProjectContextProjection**（GET /workspaces/{id}/context-proprojection）：当前 Workspace/Release、常用项目、lastBusinessUpdatedAt 与三类待办计数（ReviewTask=OPEN、WorkItem∈五活跃态、ExecutionTask=RUNNING）。只读无写入；成员职责/环境授权投影随 WP-04/06 扩展（最小切片口径已登记契约描述）。
2. **setWorkspacePin**（POST /workspaces/{id}/pin）：用户级常用项目置顶，幂等；授权按成员关系（可置顶任意成员工作区）；登录默认工作区 = 最近置顶（auth _issue 默认解析），未置顶回退首行成员关系；listWorkspaces 行内附 pinned 并置顶组优先排序。存储 v11（workspace_pins，33 号 t_workspace_pin 对齐）。用户偏好不产生领域事件（lastBusinessUpdatedAt 口径不受影响）。
3. **archiveRelease**（POST /workspaces/{id}/releases/{rid}/archive）：ACTIVE→ARCHIVED 单向（能力键 release.archive，19→21 键）；归档后从切换面消失、createWorkItem 同码 409、重复归档 409 RELEASE_ALREADY_ARCHIVED、不存在 404。配置域命令不产生领域事件（同批次四十六口径）。
4. **前端**：切换器行内置顶/取消置顶按钮（行改 div 承载双操作）；置顶组优先展示；dataService setWorkspacePin 双模式。投影接口数据面就绪，UI 消费归 WP-03 首屏（fetchReviewCount 已随 profile 刷新，无接管增益，不做无收益改造）。
5. **测试**：pytest 83→86（投影计数与置顶链 / 登录默认置顶 / 归档负向四连）；happy-path 补投影+置顶+归档链（切换器行定位随 div 化同步修正）；契约 62/121/59。

**门禁实证**：pytest 86/86；ruff/mypy strict 干净；make contract 绿；前端 vitest 51/51 + typecheck + lint 零告警；真实后端集成 e2e 4/4；mock 全量 e2e 82/82。

---

## 批次五十三（2026-08-31）——WP-03 契约激活（39 号 §3 入 32 号，11 op 全登记延期）+ WP-02 Spike

**触发**：WP-01 收口后双线并行的既定路线（批次五十二落账预告）。

**变更内容**：
1. **WP-03 契约激活（121→132 op，实现 62 不变，延期 59→70）**：39 号 §3 全部 11 个目标 REST 面入 32 号（listConversations/createConversation、listConversationMessages/createConversationMessage、listClarificationRequests/createClarificationRequest、respondClarification、createTaskCard、listAgentPlans/createAgentPlan、decideAgentPlan）+ 14 个实体 schema（Conversation/Message、ClarificationRequest/Response、TaskCard、AgentPlan/Step/Decision，字段对齐 39 §3 与 04 号实体表）+ Collaboration tag。每个 op 描述按 39 号 §10.1 落 Owner/能力键/幂等/状态码/负例；事件登记与 36 号 stream 主题留待实现批次。全部 KNOWN_DEFERRED，未实现。
2. **状态回填**：23 号矩阵 QF-PD-003/011/022/052 → IMPLEMENTATION_PENDING（§3 契约已激活）；QF-PD-023/024 → IMPLEMENTATION_PENDING（批次五十一/五十二已实现最小面，待 E2E 证据 VERIFIED）；04 号 CONTRACT_PENDING 注记更新（§3 实体 OpenAPI 已激活，DDL/实现仍缺）。
3. **WP-02 Spike（41 号新文档）**：多格式摄取选型框架（分格式专用库主选，markitdown/unstructured/docling 备选，确定性优先）+ PoC 验收清单 + L1-L4 门禁数据模型草案（dataClass 四级与 §3 消息分级同轴）+ 24 号合规搭车项清单 + 3 个待裁决开放问题。54 号索引登记 39/40/41。

**门禁实证**：openapi-spec-validator 绿；pytest 86/86；契约测试 62/132/70；ruff/mypy 干净。

**落账纪律（C-6）**：本批次为纯契约与文档批次，无业务代码实现；登记先于哈希，后续回填。

---

## 批次五十四（2026-08-31）——WP-03 实施切片一：协作对话 4 op 落地（62→66，延期 70→66）

**触发**：批次五十三 WP-03 契约激活后的首个垂直切片（对话会话 + 只追加消息）。

**变更内容**：
1. **4 op 从延期转实现**：listConversations / createConversation / listConversationMessages / createConversationMessage。新增第五路由面 `api/v1/collaboration.py`；消息两面按契约不带 workspaceId，工作区取 actor 绑定（资源型端点口径，随 switchLocalWorkspace 生效）。
2. **存储 v12**：conversations / conversation_messages 集合表（_ensure_collection_tables 幂等补建）；33 号目标 DDL 补 t_conversation / t_conversation_message（只追加，无 UPDATE/DELETE 授权路径）。
3. **事件登记表 11→12 类**：新增 conversation.message.appended（只追加写）；钉死断言显式更新（test_event_registry_pins_instrumentation_catalog 的设计意图）。listWorkspaces 的 lastBusinessUpdatedAt 口径同步为 10 类业务事件（32 号描述 + store 注释）。
4. **语义门**：幂等重放（_resolve_idempotency/_remember_idempotency 既有模式）；dataClass 四级枚举与 §3 消息分级同轴（pydantic 校验 422）；contentDigest 64 位十六进制；AGENT 消息 fail-closed 403（会话归属 Session 证明未建，本切片不开放）；跨 Workspace 查询 403、会话不存在 404；lastActivityAt 随消息推进。
5. **能力键 21→23**：conversation.write / conversation.read。

**门禁实证**：pytest 88/88（新增 test_wp03_conversations 2 条：生命周期与隔离/消息规则与事件联动；happy-path 补 4 op 链）；ruff/mypy strict（33 文件）干净；openapi-spec-validator 绿；契约口径 66/132/66。

**未含（切片二预告）**：澄清三 op（listClarificationRequests/createClarificationRequest/respondClarification，需 Session↔Conversation 映射与 BLOCKED 联动）、任务卡与 AgentPlan 四 op、前端对话 UI（可基于本切片真实接口开发）。

---

## 批次五十五（2026-08-31）——WP-03 实施切片二：澄清链路 2 op 落地（66→68，延期 66→64）

**触发**：批次五十四切片一预告的澄清链（39 号 §3：提出后 Session 转 BLOCKED、人工答复形成 CONFIRMED 证据）。

**变更内容**：
1. **HTTP 面 2 op**：listClarificationRequests（跨 Workspace 403 / Session 不存在 404）与 respondClarification（仅 USER；ANSWERED→409 CLARIFICATION_ALREADY_ANSWERED、非 OPEN→409 CLARIFICATION_NOT_OPEN、404；evidenceClass 服务端钉死 CONFIRMED；幂等重放先于状态校验——同键同指纹返回原结果，状态已推进不打断重放）。
2. **raise 保持 HTTP 延期、服务面实现**：createClarificationRequest 以 AGENT/SERVICE 角色门承载（USER 冒用 403、终态 Session 409、可选 conversationId 归属校验）；本地认证只签 USER 令牌，正路归 agent 运行时（WP-04）内部调用——契约不虚报可实现面。
3. **BLOCKED 联动**：提出后归属 Session RUNNING→BLOCKED；人工答复后该 Session 无其他 OPEN 澄清则回 RUNNING（解除语义落位）。
4. **存储 v13**（clarifications / clarification_responses 集合表）+ 33 号 t_clarification_request / t_clarification_response（答复每请求至多一条，UNIQUE 承载）。事件登记表 12→14 类（clarification.requested / clarification.responded，钉死断言显式更新）；lastBusinessUpdatedAt 口径同步 12 类。能力键 23→25（clarification.raise / clarification.respond）。

**门禁实证**：pytest 90/90（新增 test_wp03_clarifications 2 条：角色门与阻塞联动 / 答复证据与解除联动；happy-path 补 2 op 链）；ruff/mypy strict（33 文件）干净；openapi-spec-validator 绿；契约口径 68/132/64。

**未含（切片三预告）**：EXPIRED 到期收敛（requiredBy 扫描面）、createClarificationRequest HTTP 路由（随 WP-04 agent 运行时）、TaskCard/AgentPlan 四 op、前端对话与澄清 UI。

---

## 批次五十六（2026-08-31）——WP-03 实施切片三：任务卡/AgentPlan 四 op 落地（68→72，延期 64→60）

**触发**：切片二预告的 TaskCard → AgentPlan → 人工裁决链（39 号 §3：对话意图固化为结构化任务、计划人工确认后生效）。

**变更内容**：
1. **createTaskCard**：提交即 SUBMITTED（对话生成或人工填写），contentDigest 服务端规范化计算；同工作项旧卡（SUBMITTED/ACTIVE）被新版本取代（不可静默扩展 → 变更走新版本）；未解澄清阻塞 409 CLARIFICATION_OPEN；工作项与卡均无 Release 409 TASK_CARD_REQUIRES_RELEASE。
2. **createAgentPlan/listAgentPlans**：基于 SUBMITTED/ACTIVE TaskCard 编制，落地即 PENDING_APPROVAL；planVersion 工作项内自增（UNIQUE 承载），新版本使旧非终态计划 SUPERSEDED（APPROVED/REJECTED 保留审计）。
3. **decideAgentPlan**：仅 USER（AGENT 自批 403，服务面角色门已证）；expectedContentDigest 对账，摘要漂移 409 STALE_ARTIFACT_VERSION；APPROVE → 计划 APPROVED + TaskCard SUBMITTED→ACTIVE 联动；非 PENDING_APPROVAL 409 INVALID_STATE_TRANSITION；幂等重放先于状态校验（延续切片二次序裁决）。
4. **存储 v14**（task_cards / agent_plans / agent_plan_decisions 集合表）+ 33 号三表目标 DDL；事件登记表 14→16 类（task_card.created / agent_plan.decided，钉死断言显式更新）；lastBusinessUpdatedAt 口径同步 14 类；能力键 25→29。

**门禁实证**：pytest 92/92（新增 test_wp03_taskcards_agentplans 2 条：全生命周期与裁决链含漂移门 / 澄清阻塞解除与 Release 门与自批拒绝；happy-path 补 4 op 链）；ruff/mypy strict（33 文件）干净；openapi-spec-validator 绿；契约口径 72/132/60。

**未含（WP-03 收尾预告）**：仅批准计划可启动 Session 的强制门（start_session 目前不校验 plan）、前端对话/澄清/任务卡 UI（真实接口已就绪）、36 号 Conversation Stream 主题。

---

## 批次五十七（2026-08-31）——start_session 批准门（§3 语义闭合）+ WP-04 契约激活（132→140）

**触发**：批次五十六预告的两件事：WP-03 收尾强制门；WP-04 契约激活。

**变更内容**：
1. **QF-PD-003 强制门**：createAgentSession 要求工作项存在 APPROVED 状态 AgentPlan，否则 409 AGENT_PLAN_NOT_APPROVED（32 号 createAgentSession description 登记）。测试助手 prepare_source_and_work_item 自动走 卡→计划→批准 链（覆盖 26 处会话创建调用面）；新增负向专项（真实需求版本 + 无计划 → 409）。
2. **修复批次五十六遗留的 happy-path 结构缺陷**：前次移动脚本因切片区间倒置（结束标记位于起始之前）复制了 需求链/工作项/会话 整段两份，因 observed 字典幂等静默通过；本次重建为单份并重排（任务卡链在会话创建之前）。
3. **WP-04 契约激活（140 op，实现 72 不变，延期 60→68）**：39 号 §5 八个 REST 面入 32 号——commandAgentSession/commandExecutionTask（六类命令只追加，Receipt 唯一生效事实）、getRunCommandReceipt、listRuntimeAuthorizations/createRuntimeAuthorization（AUTHORIZE/REVOKE 只追加决定，SecretRef 不泄露明文）、getWorkItemBudget/updateWorkItemBudget（Agent 无权上调）、listRunCheckpoints（不可变，恢复前重新预检）；实体 schema 七件 + WorkItem 补 parentWorkItemId/stage 九值阶段字段（39 号 §4 父子阶段）；RunControl tag。每 op 落 Owner/能力键/幂等/状态码/负向。
4. **状态回填**：QF-PD-004/005/035/036 → IMPLEMENTATION_PENDING（契约已激活）；04 号 RunCommand 注记更新（EvaluationRun 仍 CONTRACT_PENDING）。

**门禁实证**：pytest 93/93（新增批准门专项；全量会话链经批准面重建）；ruff/mypy strict（33 文件）干净；openapi-spec-validator 绿；契约口径 72/140/68。

**未含（WP-04 实施预告）**：命令/回执/授权/预算/检查点的运行时实现（垂直切片逐 op 推进）、StageActivated/StageInvalidated 事件登记、36 号命令回执主题。

---

## 批次五十八（2026-08-31）——WP-04 实施切片一：运行命令 3 op 落地（72→75，延期 68→65）

**触发**：批次五十七 WP-04 契约激活后的首个垂直切片（命令 + 回执，39 号 §5）。

**变更内容**：
1. **三 op 从延期转实现**：commandAgentSession / commandExecutionTask / getRunCommandReceipt；第六路由面 `api/v1/run_control.py`。
2. **实装范围诚实收敛**：PAUSE/RESUME/CANCEL 完整落地（状态迁移矩阵：会话 RUNNING/BLOCKED/PAUSED 三源态、执行任务 RUNNING/PAUSED；PAUSED/CANCELLED 为新增状态）；RETRY/AUTHORIZE/REVOKE 契约枚举保留、运行时 422 显式拒绝（"未实装"入 message），不虚报可实装面。
3. **回执语义**：命令只追加、内嵌 CommandReceipt 是生效唯一事实；同步运行时"安全点"= 状态迁移边界，受理即生效，safePointRef 形如 `agent_session:{id}@RUNNING>PAUSED`，reasonCode=EFFECTIVE_AT_STATUS_BOUNDARY。
4. **门**：仅 USER（Agent 403）；跨 Workspace 403/404；终态目标 409 INVALID_STATE_TRANSITION；幂等重放同键返回原命令；事件登记表 16→17 类（run_command.recorded）；能力键 29→31；存储 v15（run_commands 集合表）；listWorkspaces 口径同步 15 类。

**门禁实证**：pytest 95/95（新增 test_wp04_run_commands 2 条：会话命令全迁移矩阵与回执/执行任务命令与事件；happy-path 补 3 op 链）；ruff/mypy strict（34 文件）干净；openapi-spec-validator 绿；契约口径 75/140/65。

**未含（WP-04 后续切片预告）**：RETRY 新 attempt（引用原失败记录）、AUTHORIZE/REVOKE 运行时授权面、预算策略两 op、检查点列表、RESUME 重新预检（输入摘要/预算/环境对账）。

---

## 批次五十九（2026-08-31）——WP-04 实施切片二：授权/预算/检查点 5 op 落地（75→80，延期 65→60）

**触发**：切片一预告的授权与预算面（39 号 §5）。

**变更内容**：
1. **授权两 op**：createRuntimeAuthorization（AUTHORIZE/REVOKE 只追加决定；REVOKE 将交叠权限键的 ACTIVE 授权置 REVOKED、不删历史；有效期倒置 422；Agent 决定 403；SecretRef 只引用不落明文）+ listRuntimeAuthorizations（审计全量）。
2. **预算两 op**：getWorkItemBudget（无策略时合成默认值返回，读无副作用、不落库）+ updateWorkItemBudget（仅 USER；部分字段合并更新，未提供项保持；幂等重放返回原策略）。本切片无消耗追踪，status 恒 NORMAL，上限自动暂停随执行主体（WP-06）接入。
3. **检查点一 op**：listRunCheckpoints（targetType 校验 422 / 目标 404 / 跨 ws 403）；**PAUSE 命令同步落检查点**（stage=迁移前状态、inputDigest=目标快照规范化摘要），检查点成为真实数据而非装饰。
4. **存储 v16**（runtime_authorizations / budget_policies / run_checkpoints 集合表）；事件登记表 17→19 类（runtime_authorization.decided / budget.updated）；lastBusinessUpdatedAt 口径同步 17 类；能力键 31→36。

**门禁实证**：pytest 98/98（新增专项 3 条：授权决定与 REVOKE 联动 / 预算默认与更新 / PAUSE 落检查点；happy-path 补 5 op 链）；ruff/mypy strict（34 文件）干净；openapi-spec-validator 绿；契约口径 80/140/60。

**未含（WP-04 收尾预告）**：RETRY 新 attempt（依赖 agent 运行时重执行面）、RunCommand AUTHORIZE/REVOKE 类型与授权记录联动、RESUME 重新预检（检查点 inputDigest 对账）、预算消耗追踪与自动暂停。

---

## 批次六十（2026-08-31）——前端协作 UI 切片一：协作对话页接入真实接口

**触发**：批次五十九判断后端契约面已厚（WP-03/04 真实接口就绪），转前端最大欠账。

**变更内容**：
1. **协作对话页 /conversations**（QF-PD-052 用户与协调 Agent 对话的首个真实承载面）：左栏会话列表（服务端最近活跃口径）+ 新建会话弹层；右栏只追加消息流 + 发送（actor 区分我/Agent/系统、时间、数据分级徽标）。
2. **contentRef 分级策略落地前端**：PUBLIC/INTERNAL 低敏正文内联发送；CONFIDENTIAL/RESTRICTED 自动转 `conv-ref://` 引用并以 chip 呈现——与服务端"敏感正文按引用存储"同口径（本地运行时简化：低敏内联，正式正文服务归 WP-02 资料域）。
3. **数据层四函数双模式**：fetchConversations/createConversation/fetchConversationMessages/appendConversationMessage（真实分支带 Idempotency-Key；mock 台账模块级可变）。
4. **导航**：工作组新增「协作对话」入口。

**门禁实证**：vitest 54/54（+3 组件测试：列表与消息流/发送追加/新建必填与切换）；typecheck/lint 零告警；mock 全量 e2e 84/84（+2：发送与引用分级/新建切换）；真实后端集成 e2e 4/4（+1 对话链：新建→内联发送→CONFIDENTIAL 转引用→刷新持久）。

**未含（前端后续切片预告）**：澄清卡（对齐 listClarificationRequests/respondClarification，嵌入对话流）、任务卡/AgentPlan 裁决 UI（工作项详情扩展）、运行命令条（暂停/取消/回执，执行监控页）、对话页真实流式（36 号 Conversation Stream 归后端实装）。

---

## 批次六十一（2026-08-31）——前端协作 UI 切片二：任务卡/计划裁决 UI + 执行命令条 + listTaskCards 契约补面

**触发**：批次六十预告的前端切片二；澄清卡因 raise 面归 agent 运行时（真实模式无数据源）明确延后，不做空壳。

**变更内容**：
1. **WorkItemPage 两面板**：任务卡（固化弹层六字段、SUBMITTED/ACTIVE/SUPERSEDED 版本状态、摘要短显）；AgentPlan（版本链、状态徽标、批准/拒绝弹层展示内容摘要对账——决定携带 plan.contentDigest，漂移 409 由后端拦）。批准后任务卡 SUBMITTED→ACTIVE 联动在前端可见。
2. **ExecutionMonitorPage 命令条**：RUNNING 行 暂停/取消、PAUSED 行 恢复/取消（stopPropagation 防行导航）；回执 effectiveStatus 入 toast（回执是生效唯一事实的前端呈现）。
3. **契约补面 listTaskCards**（140→141）：39 号 §3.1 未列读面、前端纵向需要，契约先行补 GET（能力键 task_card.read，37 键）；实现+happy-path 同批落位。
4. **修复两处真实模式缺陷（e2e 穿透发现）**：①看板乐观行使用假 id（WI-900x 式）点击进详情 404——createWorkItem 真实分支改返回后端 id；②createTaskCard body 携带多余 workspaceId → 422 extra_forbidden（StrictRequest）。e2e 的 toast 断言改为目标文本断言（跨步骤残留 toast 会掩盖失败）。
5. **范围决策**：澄清卡 UI 延后——raise 只有服务面（AGENT/SERVICE 角色门），真实模式无澄清数据源，接 UI 即空壳；待 WP-04/WP-06 agent 运行时落地后随真实澄清接入。

**门禁实证**：pytest 98/98（含 listTaskCards 链）；契约 81/141/60；ruff/mypy（34 文件）干净；vitest 54/54；mock 全量 e2e 87/87（+3：批准链/固化取代/执行命令）；真实后端集成 e2e 5/5（+1 裁决链：建项→固化→计划→批准→刷新持久）。

---

## 批次六十二（2026-09-04）——prototypes/skills 语言分层中文化（30+1 skill 全量）

**触发**：技能原型三层语言与产品中文口径不一致——调用方中文下达任务（agents.json objective、用户提问）、执行方为国内模型、产物语言已被中文基线锁定（planning-golden-baseline、api-test-suite cases.json），而 SKILL.md/references/脚本文案全部英文。按 skill 编写最佳实践（指针语言匹配调用方、示例锚定产物语言）做语言分层判定后全量中文化。

**变更内容**：
1. **语言分层契约**（本批确立）：机器绑定层——枚举/finding code/verdict/severity/classification、JSON key、CLI flag、exit code、skill 名与文件名——一律保留英文；LLM 指令层（SKILL.md description/正文/示例、references）与展示层（assets 模板说明、evals 清单散文、脚本 finding 文案与注释）中文化。对齐 backend「英文错误码 + 中文 message」既有模式。
2. **四批落地**（每批独立 commit 可回滚）：批一 61 文件——28 个 assets 模板 + 31 个 evals 清单（108 条）+ hitl-gatekeeper refs 标题；批二 48 文件——42 个脚本文案/注释 + gate.py/drift_detect.py + test_p2_gate0 七处英文逐字断言同步中文 + p0/p1 授权报告 drift 登记 8 项；批三 31 份 SKILL.md（需求设计 10 / 生成 11 / 执行治理 9 含 using-qualityforge 路由页，以 api-test-generator 为范文统一标准）；批四 31 份 references（引用的中文上位规则原文保留）。
3. **配套修复**：gate.py 两处既有悬空 policy_clause 锚点（#ambiguity-flag、#missing-confidence）随中文锚点同步修复指向实际章节；test-case-generator 中文弱断言功能词表（大约/大概/roughly）零改动。
4. **promptfoo CI 对冲**：SKILL.md 翻译保留全部枚举码表与示例 token 锚点（REJECT/HARDCODED_SECRET 等），确定性替代校验为逐文件枚举 token 译前/译后计数对比（全量零缺失）。

**门禁实证**：make test-skills → 127/127（含 test_p2 中文断言与 attestation drift 声明）；make eval → 31 清单 schema lint + 14 确定性 runner（实跑 exit=0）+ provider 黄金集闸门（结构判分 4/4、false-accept=0）全 PASS；脚本 py_compile 全过。未验证：promptfoo LLM 评测（本地无 OpenAI/Anthropic key，留 CI skill-eval.yml 兜底）。

**未含**：promptfoo vars.input 保持英文（维持 CI 门禁可比性，待真实中文语料接入后二次迭代）；prototypes/agent-governance/gate0-planning-slice.json 英文 description 与 prototypes/e2e-validation/README.md 英文（范围外，仅记录）。

---

## 批次六十三（2026-09-05）——feat/skills-zh 合回 main + WP-05 契约激活（各 Owner 发布链五 op 入 32 号，141→146，延期 65）

**触发**：批次六十二落账预告的分支合并；40 号 Backlog §4 WP-05 既定下一步（契约激活先行）。

**变更内容**：
1. **分支合并**：feat/skills-zh（批次六十二，6 commit 24a2e49..98cf967）fast-forward 合回 main（合并前 0 落后/6 领先），合并后 pytest 98/98 sanity 绿；批次六十二落账自此在 main 生效。
2. **WP-05 契约激活（146 op，实现 81 不变，延期 60→65）**：各 Owner `APPROVED → PUBLISHED` 发布命令五 op 入 32 号——publishTestStrategyVersion / publishTestPlanVersion / publishTestCaseVersion（TestPlanning tag，类型化 VersionResponse）、publishAutomationScriptVersion（Automation tag，对齐 runAutomationChecks 的 script-versions 平面路径风格）、publishKnowledgeCandidate（Knowledge tag，QF-PD-014；能力键复用既有 knowledge.publish，其余为 artifact.*.publish 新键）。审核继续复用 ReviewTask/Decision，无新增实体（39 号 §10 第 2 条同步义务不触发）；每 op 落 Owner/能力键/幂等/状态码/负向（仅 USER、Agent 自批自发布 403、非 APPROVED 409 ASSET_NOT_APPROVED、幂等重放同键同指纹返回原结果）。
3. **StageActivated/StageInvalidated 事件**：按 39 号 §4 语义在发布 op description 登记"发布不自动改写已激活下游，上游输入变化由 StageInvalidated 事件联动 STALE/BLOCKED"；事件登记表与 36 号 stream 主题留待实现批次（沿批次五十三先例）。
4. **状态回填**：23 号矩阵 QF-PD-007/014/039 → IMPLEMENTATION_PENDING（发布链契约已激活，批次六十三）；QF-PD-019 维持 BASELINED（质量门槛面为 M4 既有延期 op，本批次无新增激活）；QF-PD-016 维持 CONTRACT_PENDING（39 号 §6 ExecutionPlanVersion 冻结字段随 WP-06 契约激活）。
5. **契约测试口径**：test_openapi_contract.py 的 KNOWN_DEFERRED_COUNT 60→65，注释同步 81/146/65 与延期构成说明（含修正原注释中过期的 140/72/68 口径）。

**门禁实证**：openapi-spec-validator 绿（146 op）；pytest 98/98（契约测试含新延期口径双向断言）；ruff/mypy strict（34 文件）干净。

**落账纪律（C-6）**：本批次为契约与文档批次，无业务代码实现；登记先于哈希，后续回填。

**未含（WP-05 实施预告）**：五 op 运行时实现（垂直切片推进，含 ASSET_NOT_APPROVED/INVALID_CANDIDATE_STATUS 语义与旧 PUBLISHED 版本 STALE 联动）、StageActivated/StageInvalidated 事件登记与 36 号主题、风险分级审核策略与可选双人复核、KnowledgeCandidate 发布存储面、发布后下游失效投影；37 号 API 接口总览的口径数字长期未随批次维护（仍为 56/61/117），另行处理。

---

## 批次六十四（2026-09-05）——WP-05 实施切片一：资产发布链 3 op 落地（81→84，延期 65→62）

**触发**：批次六十三 WP-05 契约激活后的首个垂直切片（TestPlanning 三资产的 APPROVED → PUBLISHED 发布命令）。

**变更内容**：
1. **3 op 从延期转实现**：publishTestStrategyVersion / publishTestPlanVersion / publishTestCaseVersion（planning.py 内 TestPlanning 命令面，无新路由面）。publishAutomationScriptVersion / publishKnowledgeCandidate 维持延期——上游 createAutomationScript 面与 KnowledgeCandidate 存储面均未实现，接了即空壳（沿批次六十一"不做空壳"纪律）；能力键 artifact.automation_script.publish 随其实现切片登记。
2. **发布语义（39 号 §10）**：仅 USER（Agent 自批自发布服务面 403）；仅 APPROVED 可发布（409 ASSET_NOT_APPROVED）；APPROVED → PUBLISHED 回填根 publishedVersionId，同资产旧 PUBLISHED 版本转 STALE；幂等重放先于状态校验（同键同指纹返回原发布结果，operation 键含 versionId）；跨 Workspace 资源隐藏 404（对齐 createXxxVersion/decideReview 既有口径，批次六十三契约描述中"跨 Workspace 403"同步修正为资源隐藏 404）。发布不自动改写已激活下游（39 号 §4 StageInvalidated 联动随后续批次）。
3. **事件登记表 19→20 类**：新增 asset.published（subjectType=资产类型，payload 含 versionId/version/supersededVersionId）；lastBusinessUpdatedAt 口径 17→18 类（32 号 listWorkspaces 描述与 store 注释同步）；钉死断言显式更新。能力键 37→40（artifact.test_strategy.publish / artifact.test_plan.publish / artifact.test_case.publish）。
4. **无存储版本升级**：发布仅既有版本实体状态迁移，不新增集合表（v16 维持）。
5. **测试**：新增 test_wp05_publish 2 条（批准门/幂等重放/角色门/未知版本 404；新旧版本取代链 + asset.published 事件断言，事件定位按 versionId 与返回序无关）；happy-path 补 3 op 链（plan/case 批准→发布、策略发布后根回填断言）。

**门禁实证**：pytest 100/100；契约口径 84/146/62；ruff/mypy strict（34 文件）干净；openapi-spec-validator 绿。

**落账纪律（C-6）**：登记先于哈希，后续回填。

**未含（WP-05 后续预告）**：publishAutomationScriptVersion / publishKnowledgeCandidate（随各自 create 面切片）、StageActivated/StageInvalidated 事件登记与 36 号主题、风险分级审核策略与可选双人复核、发布后下游 STALE/BLOCKED 联动投影、前端发布按钮与统一待办（WP-05 前端切片）。

---

## 批次六十五（2026-09-05）——WP-05 实施切片二：风险分级审核政策与双人复核（QF-PD-007）

**触发**：切片一（批次六十四）后的审核治理语义切片；负向验收"单人绕过双审"与"AI 自批"承载面。

**变更内容**：
1. **政策路由（服务端派生）**：ReviewTask 创建时按 WorkItem riskLevel 派生政策——CRITICAL → FOUR_EYES/minApprovers=2，其余（HIGH/MEDIUM/LOW）→ SINGLE_REVIEW/1（04 号 ReviewPolicy 平台最低基线，服务端钉死；ReviewPolicy 配置面 CRUD 后置，基线只能调严）。HIGH 维持单人档（主测试助手语义不变）。手工 createReviewTask 按 policyType 设 minApprovers；执行证据内联门任务补齐同名字段（默认单人）。
2. **FOUR_EYES 双人门（decideReviewTask）**：APPROVE 逐人追加 approvals（actorId/comments/decidedAt）；同一审批人二次批准 409 FOUR_EYES_SAME_APPROVER（单人绕过双审被拒）；达到 minApprovers 才置任务 APPROVED 与版本 reviewStatus=APPROVED，部分批准任务 IN_PROGRESS、版本保持 PENDING_REVIEW、会话保持 BLOCKED。退回（REQUEST_CHANGES/REJECT）不要求双人——阻断项单人直接退回（06 号 §9）。review.decided 事件对部分批准同样落账（payload 增 approvals/minApprovers）。
3. **自审隔离口径（诚实边界）**：AI 自批由既有 AGENT 角色门承载（AI 无审核权）；人侧 separationRules 属 04 号 ReviewPolicy 配置面——V1 单人可兼任（QF-PD-001）故不强制提交人≠审批人，契约 ReviewTask schema 描述注记，不虚报已实装。
4. **契约**：ReviewTask schema 增 minApprovers（integer≥1）与 approvals（数组）字段及政策派生/双人门描述。
5. **测试**：新增 test_wp05_review_policy 3 条——CRITICAL 双人链（部分批准状态机/绕双审 409/双审批准后收敛 SUCCEEDED/发布链可用）、非 CRITICAL 默认单人档 + REJECT 单人终态、手工 FOUR_EYES 任务双人门。

**门禁实证**：pytest 103/103；ruff/mypy strict（34 文件）干净；openapi-spec-validator 绿；契约口径不变 84/146/62（本批次为语义切片，无 op 增减）。

**落账纪律（C-6）**：登记先于哈希，后续回填。

**未含（WP-05 切片三预告）**：发布后下游失效（39 号 §4 StageInvalidated → STALE/BLOCKED 联动）与 StageActivated/StageInvalidated 事件登记（事件表 20→22 类）、ReviewPolicy 配置面 CRUD、前端发布按钮与统一待办（WP-05 前端切片）。

---

## 批次六十六（2026-09-05）——WP-05 实施切片三：发布取代下游失效 + stage.invalidated 事件（39 号 §4）

**触发**：切片二（批次六十五）预告的下游失效联动；40 号 WP-05 后端行"新版本失效下游"。

**变更内容**：
1. **级联失效（策略发布链）**：publishTestStrategyVersion 取代旧发布版本时，引用被取代版本的全部测试计划版本（同 Workspace，reviewStatus ∈ DRAFT/PENDING_REVIEW/APPROVED/PUBLISHED）转 STALE，其未决审核任务（OPEN/IN_PROGRESS）置 CANCELLED——只失效不删除（历史任务与版本保留，39 号 §4"不得删除历史任务或证据"）。REJECTED/STALE 终态不受影响。
2. **事件登记表 20→21 类**：新增 stage.invalidated（39 号 §4 StageInvalidated 的资产层落地——subjectType=TEST_PLAN，payload 携 invalidatedVersionId/trigger=UPSTREAM_PUBLISHED_VERSION_SUPERSEDED/supersededVersionId/publishedVersionId）；stage.activated 登记随阶段激活实现切片（不预登记无发射面的事件类型）。lastBusinessUpdatedAt 口径 18→19 类（32 号 listWorkspaces 描述与 store 注释同步）。
3. **诚实边界**：执行计划级联（publishTestPlanVersion → ExecutionPlanVersion.testPlanVersionId 引用面）随 WP-06 冻结字段落地，本切片不虚构其状态迁移；publishTestPlanVersion/publishTestCaseVersion 契约描述同步改为"下游失效随相应实现切片"。
4. **测试**：test_wp05_publish 增下游失效专项 1 条——v2 取代 v1 后下游计划版本 STALE、未决任务 CANCELLED、stage.invalidated 事件逐版本登记（触发源/取代指针断言）、历史版本仍可读。

**门禁实证**：pytest 104/104；ruff/mypy strict（34 文件）干净；openapi-spec-validator 绿；契约口径不变 84/146/62（语义切片，无 op 增减）。

**落账纪律（C-6）**：登记先于哈希，后续回填。

**未含（WP-05 收尾预告）**：ReviewPolicy 配置面 CRUD、前端发布按钮与统一待办（WP-05 前端切片）、publishAutomationScriptVersion/publishKnowledgeCandidate（随各自 create 面切片）。

---

## 批次六十七（2026-09-05）——WP-05 前端切片：审核台就地发布 + 双人复核进度展示

**触发**：批次六十四~六十六发布链与双人复核后端就绪后的前端纵向切片（40 号 WP-05 前端行"统一待办与业务页就地审核、状态机明确"）。

**变更内容**：
1. **审核台就地发布**：ReviewsPage 对 status=APPROVED 的三资产任务（TEST_STRATEGY/TEST_PLAN/TEST_CASE）显示「发布版本」入口 + 确认弹层（发布语义提示：APPROVED→PUBLISHED、回填发布指针、下游失效提示）；确认后调对应 publish 接口（Idempotency-Key），成功 toast 携 reviewStatus PUBLISHED 并翻转「已发布」禁用态；失败透出后端 message（如 409 ASSET_NOT_APPROVED）。任务已 APPROVED 时批准/退回/拒绝按钮禁用（前端呈现，非授权边界）。
2. **双人复核进度展示**：任务详情 kv 增「复核进度 N/M 名审批人已批准 · 双人复核」（minApprovers>1 时显示）；队列投影 mapReviewTask 携带 taskStatus/artifactId/artifactTypeCode/minApprovers/approvals。
3. **dataService**：新增 publishStrategyVersion/publishPlanVersion/publishCaseVersion（真实 POST + Idempotency-Key，mock 合成 PUBLISHED）；planning 三页真实投影状态修正——按 publishedVersionId 判定已发布/待审核，不再硬编码"已发布"。
4. **mock/徽标**：mock 队列增 q7（已批准待发布策略，含 minApprovers/approvals 示例数据），AppShell 待审核徽标 6→7；ReviewTask/ReviewDetailData 类型补齐 WP-05 字段。
5. **测试**：vitest 新增 ReviewsPage.test 3 条（FOUR_EYES 进度、发布成功链含调用参数断言、失败透出后端 message）；e2e 新增 publish-flow 2 条（发布入口可见性与确认→toast→翻转；未批准任务无发布入口）；review-smoke 队列与徽标计数 6→7。

**门禁实证**：vitest 57/57；tsc+vite build 绿；mock 全量 e2e 89/89（+2）；后端不动（pytest 104/104、契约口径 84/146/62 维持）。

**落账纪律（C-6）**：登记先于哈希，后续回填。

**未含**：planning 三页版本级视图与业务页就地发布按钮（策略/计划无版本列表读面，随读面补齐切片）、真实后端集成 e2e 发布变体（可复用 integration-flow 扩展）、ReviewPolicy 配置 UI。

---

## 批次六十八（2026-09-05）——api-test-suite 对齐再生成：56→84 op 口径（rules 50 / IR 84 契约 / 场景 92 / 用例 92）

**触发**：批次六十三预告的测试资产对齐欠账——套件停在 2026-08-30 的 56 op 时点，WP-01/03/04/05 四个工作包新增的 28 个已实现 op 不在覆盖内。

**变更内容**：
1. **增量清单（机械推导）**：以 test_openapi_contract 的 EXPECTED_IMPLEMENTED_OPERATION_IDS（84）对 IR interface_contracts（56）求差，得 28 op——WP-01 上下文/驾驶舱 6（switchLocalWorkspace/getProjectContextProjection/setWorkspacePin/archiveRelease/listWorkspaces/listReleases）、WP-03 协作 11（对话 4/澄清 2/任务卡 2/AgentPlan 3）、WP-04 运行控制 8（命令/回执/授权/预算/检查点）、WP-05 发布链 3。
2. **rules.json 35→50**：新增 15 条（R-CTX-001~003/R-COL-001~005/R-RC-001~004/R-RT-009/R-PUB-001~002），全部带 source_trace（批次五十四~六十六实现锚点）；rule_check PASS 0 findings。
3. **testing_ir.json**：interface_contracts 56→84；requirements 15→19（+Q-CTX/COL/RC/PUB 四族）；business_rules 同步 50；entities 3→8（AssetVersion/TaskCard/AgentPlan/Clarification/AgentSession）；state_machines 2→7（+5 新机、SM-REVIEWTASK 扩 IN_PROGRESS/CANCELLED 与 FOUR_EYES 门），已实现迁移 4→27；EXPIRED 澄清与 RETRY/AUTHORIZE/REVOKE 命令未实现不声明；validate.py PASS 0 findings（修死端 3 处：CANCELLED 补终态、ACTIVE/BLOCKED 补出边）。
4. **scenarios.json 57→92**：新增 35（含 24 state_transition 场景携带 transition_ref，27 迁移全覆盖）；scenario_check PASS 27/27 覆盖 0 findings。
5. **cases.json 74→92**：新增 18 条（TC-CTX 3/TC-COL 6/TC-RC 4/TC-PUB 4/TC-RT-015），断言精确到错误码（ASSET_NOT_APPROVED/FOUR_EYES_SAME_APPROVER/AGENT_PLAN_NOT_APPROVED/STALE_ARTIFACT_VERSION/RELEASE_NOT_IN_WORKSPACE/CLARIFICATION_ALREADY_ANSWERED/INVALID_STATE_TRANSITION 全家族）与幂等重放、级联失效（stage.invalidated 事件断言）；case_check PASS 0 findings；端点占位符与契约参数名逐字对齐（camelCase）。
6. **覆盖机械验证**：84/84 已实现 op 全覆盖（0 缺失）；29 端点被 ≥2 用例覆盖。README 口径同步更新；四份 *_report.json 重跑落盘。

**门禁实证**：四门禁终跑全 PASS（rule 50 条/ir 六族/scenario 92 场景 27 迁移/case 92 用例，均 0 findings）；覆盖验证脚本 84/84。

**落账纪律（C-6）**：登记先于哈希，后续回填。

**未含**：tests/ 可执行层仍为 56 op 口径（89 项）——新增 18 条用例的 fixture 变量（{alt_workspace_id}/{critical_task_id} 等）与可执行脚本随下一执行批次扩展；37 号 API 接口总览口径刷新另行处理。

---

## 批次六十九（2026-09-05）——api-test-suite 可执行层扩展：89→107 项（新增 4 域 18 用例）+ 基线修复 + 37 号总览刷新

**触发**：批次六十八预告的执行层扩展；执行前发现既有 89 项已红 11 项。

**变更内容**：
1. **基线修复（11 项红→绿）**：可执行层滞后于实现——conftest 的 gate0 会话链被批次五十七批准门（409 AGENT_PLAN_NOT_APPROVED）与批次五十 Release 归属门（TASK_CARD_REQUIRES_RELEASE/RELEASE_NOT_IN_WORKSPACE）打破。修复：工作项携带动态获取的 ACTIVE releaseId（替代硬编码常量），会话创建前补 任务卡→AgentPlan→人工批准 链；删除死常量 RELEASE_ID。
2. **新增 4 个可执行文件（18 用例，覆盖批次六十八新增 28 op）**：test_06_context（TC-CTX-001~003：投影/切换/驾驶舱、置顶排序、归档门）、test_07_collaboration（TC-COL-001~006：对话只追加、澄清答复闭环、任务卡固化、摘要漂移 409 与批准联动、终态重复裁决、批准门；澄清种子经服务面 AGENT 角色构造——HTTP raise 面随 agent 运行时）、test_08_run_control（TC-RC-001~004：PAUSE 回执唯一事实、幂等重放与终态 409、执行任务命令与检查点不可变字段、授权只追加与预算）、test_09_publish（TC-PUB-001~004 + TC-RT-015：发布回填指针、非 APPROVED 409 与重放、计划/用例两面、取代级联 stage.invalidated 事件、FOUR_EYES 同人二次批准 409）。
3. **执行发现并修正 1 处设计用例漂移**：TC-COL-002 设计断言 respondClarification 返回 200，实现实际 201（Created）——可执行层证伪设计用例（沿 2026-08-27 执行批次先例），cases.json 同步修正并重过 case_check 门禁 PASS。
4. **测试自身修正（非实现缺陷）**：驾驶舱投影实际字段为 workspace/currentRelease/pinnedWorkspaces/openReviewCount 等（无 currentWorkspaceId）；decideAgentPlan 返回决定记录（无顶层 status，经 listAgentPlans 验证计划状态）；gate0 会话 PAUSE 源态为 BLOCKED（safePointRef BLOCKED>PAUSED）；GET 面（agent-plans/budgets/authorizations/checkpoints/run-commands/task-cards/clarifications）均要求 workspaceId query；pin 请求体仅 {pinned} 且要求 Idempotency-Key。
5. **37 号 API 接口总览口径刷新**：当前规模 106 paths/146 operations（批次六十七后实算）；实现口径 56/61/117 → 84/146/62（批次六十八）；"待激活接口族"段更新——协作/运行控制/发布链已激活，评估面（EvaluationRun/Rubric/Calibration/Benchmark）随 WP-07。

**门禁实证**：可执行层 98 passed / 4 skipped / 5 xfailed（107 项，0 failed）；case_check 复验 92 用例 0 findings；后端与前端不动（pytest 104/104、vitest 57/57 口径不变）。

**落账纪律（C-6）**：登记先于哈希，后续回填。

**未含**：execution-report.json 仍为 2026-08-27 执行记录（本轮结果待随下次全量执行批次归档）；WP-05 前端切片的集成 e2e 发布变体。
