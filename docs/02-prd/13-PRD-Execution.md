# 13-PRD-自动化测试开发

> 现行模块：自动化测试开发。文件名为兼容历史链接保留。测试执行职责迁至14号。

## 1. 目标与边界

把Web、API、移动、性能、安全等自动化代码作为正式产出物管理，让AI承担生成、检查和修复建议，测试开发人员完成代码审核和关键判断。解决脚本散落、代码与用例一对一僵化、依赖/运行时不可复现和自愈静默污染资产的问题。

## 2. 功能需求

| 能力 | 需求 | AI作用 | 人工控制 |
|---|---|---|---|
| 脚本稳定根/版本 | AutomationScript按能力命名，版本记录语言、框架、运行时、依赖锁、来源模式和摘要 | 生成新版本和变更摘要 | 代码Review并批准版本 |
| 用例绑定 | 一个脚本版本可覆盖多个TestCaseVersion，一个用例可有多种自动化实现 | 推荐绑定和覆盖类型 | 审核绑定真实性 |
| Web自动化 | 页面对象/组件、Locator、等待、截图/视频配置 | 生成和诊断候选 | 审核关键路径、稳定性和敏感操作 |
| API自动化 | 基于APIContractVersion生成请求、断言、鉴权引用和数据 | 生成契约测试代码 | 审核业务码/字段/副作用断言 |
| 代码检查 | 格式、类型、静态安全、依赖、契约绑定和受控试跑 | 自动执行和解释 | 检查PASS不替代代码批准 |
| Locator | 稳定根/版本、主/备选择器、证据和supersedes | 发现/自愈候选并验证 | 写正式LocatorVersion需审核 |
| Mock/数据/视觉 | Mock绑定契约版本；数据含生成/脱敏/清理；视觉含视口/遮罩/摘要 | 生成候选配置 | 审核业务约束和隐私风险 |
| Git模式 | 固定repo、完整commit SHA、path、blob SHA和digest | 生成PR/补丁候选 | 仓库写入另行人工批准 |

## 3. 关键规则

- AutomationScript是八类正式产出物之一；AI不能把检查PASS直接变成`APPROVED/PUBLISHED`。
- 试运行沙箱量化验收口径（裁决 B2-8，2026-08-14）：进程非 root 运行、工作目录只读挂载、默认零外网（网络命名空间禁出站）、单次执行超时上限（默认 120s）、产出目录白名单；每条均有可执行检查命令，检查 PASS 不替代代码批准。
- 执行只接收已批准脚本版本和完整依赖/运行时指纹；运行时临时修复产生候选新版本，不覆盖已冻结版本。
- 代码正文和Secret分离；脚本只引用secretRef，日志/Trace中不得出现明文。
- API代码绑定APIContractVersion；契约变化触发影响分析而不是静默重生成覆盖。
- Locator自愈默认只在单次运行尝试，正式资产变更走Diff和ReviewTask。

## 4. 主流程

```text
选择已批准TestCaseVersion/APIContractBaseline
→ AI生成AutomationScriptVersion草稿
→ 确定性检查/受控试跑 → 代码Diff与证据
→ CODE_REVIEW ReviewTask → 人工批准/退回
→ 已批准版本可被ExecutionPlanVersion冻结
```

## 5. 异常与降级

- 框架/Runner能力不匹配：返回`RUNNER_CAPABILITY_MISSING`并阻塞，不降级为错误框架。
- 依赖无锁/来源不可信/安全扫描失败：禁止批准或执行。
- Secret未授权：生成可审查模板但不试跑，记录`SECRET_ACCESS_DENIED`。
- Locator多候选冲突或连续失败：停止自愈并人工定位。

## 6. 验收标准

### AC-01 多对多绑定

- **Given** 一段登录setup服务于10个用例；
- **When** 创建脚本版本；
- **Then** 可绑定10个精确TestCaseVersion并分别标注coverageType，无需复制10份脚本。

### AC-02 依赖可复现

- **Given** 脚本准备批准；
- **When** 缺frameworkVersion、runtimeVersion或dependencyDigest；
- **Then** blocking check失败，不能发布或进入执行计划。

### AC-03 自愈不污染正式资产

- **Given** 运行中AI找到新Locator并重试成功；
- **When** 运行结束；
- **Then** 原LocatorVersion不变，新候选带证据进入ReviewTask。

### AC-04 API副作用受控

- **Given** AI生成删除类API测试；
- **When** 目标环境或清理策略未授权；
- **Then** 代码可保持草稿，但试跑/执行被拒绝并说明条件。

## 7. 版本范围（逐项标注，裁决 2026-08-14 批次二）

- **MUST（V1）**：Web/API 代码生成、AutomationScript 稳定根+不可变版本、用例绑定（多对多精确版本）、静态/受控检查、隔离试运行（B2-8 量化口径）、人工 Code Review 与版本批准。
- **SHOULD（V1 末/V2）**：Git 模式（固定 repo+SHA+blob 摘要证据）、Locator 候选、Mock、测试数据。
- **LATER（V3）**：性能/安全/视觉自动化与企业级供应链治理。
- Owner：自动化测试开发模块；验收证据：各能力对应 AC 与切片证据（见 V1 里程碑对照表 M3）。
## 8. 指标承接(裁决 2026-08-14;指标口径见 20 号 §1.1 受控 metricKey 登记表,覆盖率口径见 22 号附录 C)

| 指标 | 本模块角色 | 基线 | 测量方法 | 验收 |
|---|---|---|---|---|
| 自动化代码首版生成时间(M-05) | 生产 | 试点后批准(22 §6) | WorkItem(AUTOMATION)创建→首个脚本草稿创建,WorkItemEvent,按 Web/API 分层 | AC:双时点口径(草稿/可审核)分列报告 |
| 静态检查通过率(M-24) | 生产 | 试点后批准 | STATIC 检查 PASS 脚本版本/检查版本总数,AutomationCheckRun | AC:阻断检查失败不可人工备注放行 |
| 试运行通过率(M-25) | 生产 | 试点后批准 | isExperimental 试运行通过数/总数,ExecutionResult | AC:试运行与正式执行分层报告 |
