# 19-旧平台设置模块迁移说明

> 本文件保留编号和文件名以兼容历史引用，不再是独立一级模块。平台控制面统一由17号“平台管理”负责。

## 1. 职责迁移

| 旧职责 | 现行Owner/权威源 |
|---|---|
| Workspace、Release、环境、Secret、Runner、集成 | 17-平台管理 |
| 用户、角色、权限、审核策略 | 17-平台管理 + 34-认证授权 |
| LLM Provider/模型/预算/路由 | 17-平台管理；AI自治等级与阈值仍以21号为准 |
| Skill/Agent/Workflow发布 | 16-AI Agent中心 |
| AuditLog/AuthorizationDecision | 17-平台管理 + 33数据库 |
| 通知渠道 | 17-平台管理配置，任务看板/业务模块产生事件 |

## 2. 迁移规则

- 旧`/settings/*`迁移到`/platform/*`及相应资源路径。
- 平台设置不另立AI置信阈值；模型路由分数不能改变业务自治或人工硬门。
- PlatformAdmin/TenantAdmin/WorkspaceAdmin均不因管理身份自动拥有正式产出物批准、报告签署、外部写入批准或门禁豁免。
- Secret响应不返回明文；Agent不直接读取Secret。

## 3. 验收

- **Given** 旧引用打开19号；**When** 查找具体配置；**Then** 可定位17/21/34号现行Owner和规则。
- **Given** 管理员把某AI介入点设为L3；**When** Workflow到正式批准；**Then** 仍创建ReviewTask并等待符合策略的人类决定。
