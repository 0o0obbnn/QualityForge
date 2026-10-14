# 17-PRD-平台管理

> 现行模块：平台管理。文件名为兼容历史链接保留。知识库职责迁至11号。

## 1. 目标与边界

提供Workspace、Release、成员、环境、Secret、Runner、集成、RBAC、ReviewPolicy、LLM配置、资源配额和审计等控制面。平台管理负责“系统如何安全运行”，不拥有策略、用例、脚本、结果或报告正文，也不自动获得业务批准权。

## 2. 功能需求

| 能力 | 需求 | 人工/安全控制 |
|---|---|---|
| Tenant/Workspace | 生命周期、成员和隔离；UI把Workspace展示为项目 | 不新增Project实体；归档保留历史引用 |
| Release | 范围、计划时间、状态和关联版本 | 关闭/归档前校验未完成工作和报告 |
| Environment | 类型、endpoint映射、能力、数据策略和secretRef | 不保存连接串明文 |
| Secret | 密文、keyVersion、作用域、过期、轮换和使用审计 | 元数据与使用权限分离，API不返回明文 |
| Runner/资源池 | 能力、运行时、健康、配额和Workspace范围 | 注册/隔离/撤销受平台权限控制 |
| Integration | Defect、Git、CI、通知等端点/凭据引用/作用域 | 出站allowlist、逐次高价值授权和回执 |
| RBAC | Permission、RoleDefinition、RoleBinding、ExplicitDeny和委派 | 四级作用域；管理员不能自我无限授权 |
| ReviewPolicy | 产出物/风险对应阶段、人数、能力、职责分离和blockingChecks | 平台最低要求只能调严，不能取消至少一名人类 |
| LLM配置 | Provider/模型/路由、数据区域、预算和允许用途 | 不在此设置业务自治阈值；版本变化触发重评 |
| 配置辅助 | CONFIG_ASSIST：解释配置、预检变更、生成最小权限建议（21 号默认 L1，裁决 2026-08-14 批次二） | AI 建议仅提示，不自动改配置；变更落审计 |
| 审计 | AuthorizationDecision、AuditLog、保留/导出 | 只追加、脱敏、访问受限 |
| 支持访问 | SupportAccessGrant：限时、最小能力、强审计的紧急访问（break-glass）；DelegationGrant 委派（05 §5.11.8/§5.12.9，裁决 2026-08-14 批次二） | 每次授权逐项审批、超时自动失效、全程审计，Agent 无权发起 |

## 3. 对象关系

- Tenant包含多个Workspace；Workspace包含多个Release。
- Environment、Integration和RoleBinding按Tenant/Workspace/Resource作用域生效。
- PlatformAdmin管理平台基础设施，不默认读取租户业务内容。
- TenantAdmin管理租户成员/策略，不默认批准Workspace正式产出物。
- WorkspaceAdmin管理工作条件，不默认签署报告或豁免门禁。

## 4. 主流程

```text
创建Tenant/Workspace → 建Release → 配成员/角色/ReviewPolicy
→ 配Environment/Secret/Runner/Integration → 权限预检
→ 业务模块按引用使用 → 每次高价值动作AuthorizationDecision+AuditLog
→ 轮换/撤销/归档时触发影响检查
```

## 5. 异常与降级

- 租户/Workspace上下文缺失：服务层和RLS同时拒绝。
- Secret过期/无权：执行阻塞，不回退到明文或默认凭据。
- Runner能力不足：明确阻塞并建议资源，不把任务发送到不兼容节点。
- 集成不可用：保留attempt/回执并人工处理，不假报外部成功。
- ReviewPolicy/RoleBinding变更：后续高价值动作重新计算，已签署历史保留策略快照。

## 6. 验收标准

### AC-01 项目等于Workspace

- **Given** 用户点击“新建项目”；
- **When** 保存；
- **Then** 只创建Workspace并返回workspaceId，不创建Project副本。

### AC-02 管理员不自动批准

- **Given** TenantAdmin未获目标业务审核能力；
- **When** 尝试批准TestReport；
- **Then** 403拒绝并记录AuthorizationDecision。

### AC-03 Secret不泄漏

- **Given** 用户有环境查看权限；
- **When** 查询环境/Secret；
- **Then** 只能看到引用和元数据，响应/日志/Trace无明文。

### AC-04 跨租户失败关闭

- **Given** 请求令牌与资源Tenant不一致；
- **When** 查询或写入；
- **Then** 服务层和RLS拒绝，且不泄漏资源存在性。

## 7. 版本范围

V1实现试点必需的Workspace/Release、环境、Secret引用、基础RBAC/审核和审计；V2增强多团队、集成、Runner和配额；V3增强企业隔离、合规和运营。
## 8. 指标承接(裁决 2026-08-14;指标口径见 20 号 §1.1 受控 metricKey 登记表,覆盖率口径见 22 号附录 C)

| 指标 | 本模块角色 | 基线 | 测量方法 | 验收 |
|---|---|---|---|---|
| 成功成本(M-45) | 生产 | 成本单位定义后批准 | 成功 WorkItem 的 AgentSession 成本合计/成功数 | AC:失败尝试成本单独报告;人工折算需注明系数 |
| P95 延迟(M-46) | 生产 | 试点负载模型后批准 | 按 API/AI 步骤/调度分层,遥测窗口滚动 14 天 | AC:无压测基线不得承诺数值 |
| 降级率(M-47) | 生产 | 试点后批准 | 触发降级中断的自动步骤/自动步骤总数 | AC:按 interventionKey+原因码分层 |
| 人工接管率(M-48) | 生产 | 试点后批准 | 人工接管 WorkItem 数/涉及 AI 运行数 | AC:与 AI 自动完成占比互补 |
| WIP/吞吐量(M-49/50) | 生产 | 试点后批准 | WorkItemEvent 当前态投影/窗口 DONE 数 | AC:不含 BACKLOG/READY;用于改进不作个人绩效 |
| SLA 超时率(M-51) | 生产 | 试点后批准 | 到期未完成数/到期总数,WorkItem.dueAt | AC:审核超时只产生 SLA 风险不自动批准 |
