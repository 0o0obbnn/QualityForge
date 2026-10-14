# QualityForge V1 里程碑执行对照表(QF-REQ-007 整改项 + B2-5 建表清单)

> 起草员:subagent_03(里程碑对照表起草员)｜ 起草时间:2026-08-14 15:1x (GMT+8)｜ 方式:只读实算,未改写任何文档
> 依据:05-功能模块重构方案 §十一/§5.13、33-数据库Schema设计(105 张 CREATE TABLE 实算,含 8-14 新增 t_calibration_record)、04-核心领域模型(域归属)、22-MVP版本规划v2.0(V1 范围)、subagent_02_snapshot(Stage5 裁决主线)、Stage4 报告(22/102 ops、3 类产出物)
> 对应整改:QF-REQ-007(后续步骤未绑定里程碑/验收证据/Owner/DoD)+ B2-5(每里程碑需建表清单,105 张目标表逐表标注)

---

## 1. 执行摘要

- **Stage5 已裁决主线**:M1 需求与审核收口(批改→新版本→二次复核)→ M2 任务看板工作化(分派/优先级/SLA/版本Diff)→ M3 执行与证据(AutomationScript 闭环)→ M4 分析与报告(ResultAnalysis/Defect/TestReport/KnowledgeEntry 运行证据)→ M5 真实模型准入(Golden Set)。
- **与 05 §十一 一一对应**:①→M1(策略/计划/用例批改闭环)、②→M2(看板分派/优先级/SLA/Diff)、③→M3(接口自动化代码闭环)、④→M4(四类产出物运行证据)、⑤→M5(黄金集评测后替换确定性 Provider)。
- **105 表实算实标**:M1 需建表 **54 张**(其中 47 张 V1 必需=是、7 张=部分)、M2 **1 张**(t_work_item_dependency,部分)、M3 **15 张**(13 是 + 2 部分)、M4 **18 张**(15 是 + 3 部分)、M5 **5 张**(全 是,含 8-14 新增 t_calibration_record 与 t_verify_verdict);V2+/V3 **12 张**(否)。
- **V1 必需统计**:是=80(76.19%)、部分=13(12.38%)、否=12(11.43%);V1 涉及(是+部分)合计 **93/105 = 88.57%**。
- **关键发现**:M2 是"能力里程碑"而非"建表里程碑"——分派/优先级/SLA/Diff 所需字段(M1 已建表的 assignee_id/priority/sla_seconds/artifact 版本)在 M1 建表时即落地,M2 主要做 API/前端能力与契约收敛。
- **核心链收敛义务**(QF-REQ-005,核心链=策略/计划/用例/执行/分析 5 模块):核心链共 41 paths / 53 ops(实算);每里程碑关闭前,其覆盖的 operation 响应 schema 必须为具体 schema(非 Generic),通过 openapi-spec-validator,并与 KNOWN_DEFERRED_COUNT(80→82,execution-design 裁决)台账对账。
- **口径提示**:本表解析 32-API 得 79 paths / 104 ops,快照 grep 口径为 78/102(差 1 path / 2 ops,属解析口径差异,已列入未核实项)。

---

## 2. 里程碑 × 步骤 × 验收证据 × Owner × DoD 对照表

Owner 缩写:项目负责人=PO(用户/主 agent 总协调)、工程=ENG(backend/frontend 实施,当前单人 yount 兼任)、评审=REV(qf-independent-verifier 独立评审 Agent)。
验收证据均须落在 `docs/05-audits/current/` 新报告 + `output/` 可重跑脚本/截图,不允许无基线宣称(05 §5.13.7/§5.13.3 退出条件)。

| 里程碑 | 05§十一 步骤 | 范围与需建表 | 验收证据(具体文件/检查项) | Owner 建议 | DoD(完成定义) |
|---|---|---|---|---|---|
| **M1 需求与审核收口** | ①人工批改→新版本→二次复核,先覆盖策略、计划和用例 | 知识库导入与契约版本化 + 策划设计域审核闭环 + 平台/RBAC/看板最小集 + AI 中心最小运行(54 张表,见 §3) | ①E2E:浏览器完成"策略/计划/用例 草稿→批改→生成新版本→二次 ReviewTask→批准/退回/拒绝",0 console errors(扩展 `output/playwright/` 既有 stage4 截图链);②ReviewTask 绑定 `artifactId+artifactVersionId+contentDigest` 服务端复核断言(pytest 新增用例);③三种正式产出物各验证:批准、退回、新版本失效、禁止 AI 自批(负向用例,参照 Stage4 负向 7 类安全用例);④32 号 `openapi-spec-validator` PASS;⑤M1 建表清单落库:`.tables` 覆盖 §3 M1 54 张(SQLite Profile 或目标 PG,见未核实项 6);⑥产出 `docs/05-audits/current/Stage5-M1-验收报告-*.md` | PO(范围/基线)+ ENG(批改-新版本-复核实现 + E2E)+ REV(审核矩阵独立复核) | 全部 M1 表建表+迁移可重复执行;策略/计划/用例三类正式产出物完整审核闭环 E2E 通过;核心链 策略/计划/用例 16 ops 响应契约收敛(无 Generic);三个"正式产出物审核矩阵"检查项全绿;无未处置 Blocker |
| **M2 任务看板工作化** | ②任务看板分派、优先级、SLA 和版本Diff | 新表仅 t_work_item_dependency(部分);分派/优先级/SLA/Diff 复用 M1 表字段与版本表 | ①前端看板页(React 19 + Fluent UI,追认裁决)五能力 E2E:分派(assignee_id)、优先级(P0~P3 排序)、SLA 逾期标识(sla_seconds/due_at)、阻塞原因展示、产出物版本Diff 入口;②`/work-items`、`/review-tasks` 响应契约含分派/优先级/SLA/Diff 字段(具体 schema);③`t_work_item_dependency` 依赖边落库+校验用例(自环/循环 CHECK);④看板"我的待审核"队列与 ReviewTask 分派联动;⑤验收报告 `Stage5-M2-验收报告-*.md` | ENG(前端+API)+ PO(优先级/SLA 规则确认)+ REV(契约抽查) | 五能力全部可演示 E2E;看板 API 10 ops 契约收敛完成;依赖表 CHECK 约束单测通过;无静默降级(未实现项明确标注"规划中"不入完成率,05 §5.13.7) |
| **M3 执行与证据** | ③AutomationScript 正式产出物闭环,从接口自动化代码开始 | 自动化开发域 10 张 + 测试执行域 8 张 + t_api_contract_baseline + t_runner_node(15 张,见 §3) | ①AutomationScript 闭环 E2E:代码生成→精确用例绑定→静态/安全检查(check_run)→隔离试运行→人工 Code Review→版本批准;②执行链 E2E:ExecutionPlan 冻结(资产/环境/契约版本)→ExecutionTask→execution_result/artifact/api_observation 落库,请求响应证据不可变(contentDigest);③四类样例各至少 1 条:成功/业务失败/环境失败/脚本失败(05 §5.13.3,先 API 侧,Web 侧可紧随);④冻结版本/环境快照断言(execution_contract_baseline entries/masking);⑤取消/超时/一次受控重试用例;⑥验收报告 `Stage5-M3-验收报告-*.md` | ENG(执行引擎+Runner 注册)+ REV(证据不可变性与失败样例复核)+ PO(取消/重试策略) | AutomationScript 作为第 4 类正式产出物走通"版本/摘要/人工代码审核门";四类样例证据齐全且可从结果追溯至脚本版本+用例+契约版本;KNOWN_DEFERRED 台账与运行时 op 数对账一致;执行证据不可被分析结论覆盖(§5.13.6) |
| **M4 分析与报告** | ④ResultAnalysis、Defect、TestReport 和 KnowledgeEntry 运行证据 | 质量分析域 17 张(M3 已建 pipeline/quality_gate 除外,见 §3 标注)+ 知识库 KnowledgeEntry 3 张 + vector(18 张,见 §3) | ①四类正式产出物运行证据 E2E:AI 生成草稿(ResultAnalysis/Defect/TestReport/KnowledgeEntry)→人工复核/签署→版本落库;②反向追溯链验证脚本:报告/Defect → 执行 → 代码 → 用例 → 规则 → 原始来源(05 §5.13.3 退出条件);③Defect 生命周期(状态机)与缺陷证据(defect_evidence)落库;④外部同步按裁决 B2-4:手工同步仍须落 `t_defect_sync_attempt` + 批准记录 + 回执;⑤覆盖率/失败聚类基础汇总(coverage_report/failure_cluster);⑥验收报告 `Stage5-M4-验收报告-*.md` | ENG(分析生成+签署流)+ REV(报告一致性、追溯链独立验证)+ PO(签署与发布决策) | 四类产出物各至少 1 条"草稿→审核→签署/发布"完整证据;追溯链脚本 PASS;DefectSyncAttempt 手工同步记录在案;TestReport 签署后不可覆盖(只追加);KnowledgeCandidate 人工发布流程可用 |
| **M5 真实模型准入** | ⑤真实模型黄金集与效果评测,通过准入后再替换确定性 Provider 基线 | AI 中心 Eval 4 张表(t_eval_dataset/case/run/result)+ t_calibration_record(8-14 已建)+ t_verify_verdict(M1 落点,裁决 8-14) | ①黄金集落地:t_eval_dataset/case 至少 N=10 样本、风险标签、期望引用(provider-eval-gate 共识 B-C1);②双层闸门:`make eval`(promptfoo 30 Skill eval + Golden Set 评测)全绿;③阶梯熔断:坏 provider 防御 BP-01~10 样例验证(B-C2~B-C10);④准入报告:质量指标/成本/延迟/降级/数据出站策略齐备(05 §5.13.3/Stage4 §6);⑤仅评测通过后替换确定性 Provider,替换前确定性基线继续运行;⑥验收报告 `Stage5-M5-准入报告-*.md` | REV(评测设计独立审定)+ ENG(Provider 适配)+ PO(准入裁决,唯一可批准替换) | 黄金集评测 PASS 且熔断机制有效;准入报告含指标基线(无基线数字不得宣称提升);未通过评测不得替换确定性 Provider(硬门禁);替换后 e2e golden/negative 双链重跑 PASS |
| **V1 收口(横切)** | §5.13.3 V1 退出条件 | 八模块最小能力 + 八类正式产出物全人工批准 | ①单 Workspace 主流程完整跑通(22 号试点验收);②权限验证:跨 Workspace 拒绝/管理员非业务批准/外部写入拒绝/Secret 不泄漏;③基线记录:人工净处理时间/AI 草稿采用率/退回原因/执行稳定性/报告一致性;④每版本项 MUST/SHOULD/LATER+Owner+证据(§5.13.7) | PO(总收口)+ REV(独立复审) | V1 退出条件逐条证据化;无拼接历史样例冒充本轮通过(§5.13.7);独立复审无未处置 Blocker |

---

## 3. 104 张表逐表标注(实算实标)

> 来源:33-数据库Schema设计.md `grep -n 'CREATE TABLE'` = 104 行(与快照 104 一致)。模块按 33 号域标题 + 04 域归属;里程碑按"该表首次必须落库并产生运行证据的阶段"标注;V1必需=是(主链必须)/部分(V1 最小能力,完整能力 V2+)/否(V2+/V3)。
> 注:已切片 = Stage4 SQLite 纵向切片已实现雏形(报告 §3),V1 仍需按 33 号目标 Schema 正式化。

| # | 表名 | 所属模块 | 里程碑 | V1必需 | 备注 |
|---|---|---|---|---|---|
| 1 | t_tenant | 平台管理 | M1 | 是 | 主链;已切片 |
| 2 | t_user | 平台管理 | M1 | 是 | 主链;已切片 |
| 3 | t_workspace | 平台管理 | M1 | 是 | 主链;已切片 |
| 4 | t_release | 平台管理 | M1 | 是 | 主链锚点;策划/执行冻结引用(Release-TestPlan 状态机) |
| 5 | t_environment | 平台管理 | M1 | 是 | 环境快照;执行冻结前置 |
| 6 | t_workspace_secret | 平台管理 | M1 | 是 | 安全底线:Secret 双信封引用,业务接口不返回明文 |
| 7 | t_runner_node | 平台管理 | M3 | 是 | 单 Runner 注册(V1 平台最小项);状态机含 DRAINING |
| 8 | t_llm_config | 平台管理 | M1 | 是 | 模型配置;确定性 Provider 起步,M5 切换真实模型 |
| 9 | t_integration_config | 平台管理 | M1 | 部分 | V1 文件导入不依赖;URL/仓库/外部同步集成 V2+ |
| 10 | t_audit_log | 平台管理 | M1 | 是 | 只追加审计;安全底线 |
| 11 | t_role_definition | 平台管理(RBAC) | M1 | 是 | 内置角色模板(PlatformAdmin~ViewerAuditor) |
| 12 | t_permission | 平台管理(RBAC) | M1 | 是 | permissionKey 全局唯一;批准/签署 humanOnly |
| 13 | t_role_permission | 平台管理(RBAC) | M1 | 是 | effect=ALLOW/DENY,Deny 优先 |
| 14 | t_role_binding | 平台管理(RBAC) | M1 | 是 | 作用域绑定;高权限自授需复核 |
| 15 | t_explicit_deny | 平台管理(RBAC) | M1 | 部分 | V1 默认拒绝基线;规则运营/批量治理 V2+ |
| 16 | t_review_policy | 平台管理(RBAC/审核策略) | M1 | 是 | 审核策略核心:requiredStages/minApprovers/separationRules |
| 17 | t_authorization_decision | 平台管理(RBAC) | M1 | 是 | 授权决策每次重算只追加;主链安全证据 |
| 18 | t_delegation_grant | 平台管理(RBAC) | V2+ | 否 | 委派/四眼复核(V2 团队);不可委托 Agent 批准正式产出物 |
| 19 | t_support_access_grant | 平台管理(RBAC) | V2+ | 否 | 平台支持访问治理;默认只读限时 |
| 20 | t_work_item | 任务看板 | M1 | 是 | 主链;已切片;assignee/priority/sla_seconds 字段 M2 启用 |
| 21 | t_work_item_artifact | 任务看板 | M1 | 是 | 产出物版本证据;M2 版本Diff 数据源 |
| 22 | t_work_item_run | 任务看板 | M1 | 是 | AI 运行状态(WorkItem 状态机) |
| 23 | t_work_item_event | 任务看板 | M1 | 是 | 事件只追加;看板动态/审计支撑 |
| 24 | t_work_item_dependency | 任务看板 | M2 | 部分 | M2 依赖边最小落地(自环/循环 CHECK);跨团队复杂依赖 V2+ |
| 25 | t_review_task | 任务看板 | M1 | 是 | 审核任务核心;已切片;绑定 artifact+version+contentDigest |
| 26 | t_review_assignment | 任务看板 | M1 | 是 | 审核分派;M2 看板队列强化 |
| 27 | t_source_snapshot | 知识库 | M1 | 是 | 导入来源快照(raw_digest/fetch_status);已切片雏形 |
| 28 | t_requirement_document | 知识库 | M1 | 是 | 需求文档;已切片雏形 |
| 29 | t_requirement_document_version | 知识库 | M1 | 是 | 来源版本;已切片雏形 |
| 30 | t_source_trace_edge | 知识库 | M1 | 是 | 溯源边(Source Trace 主链;追溯链根基) |
| 31 | t_ai_context_snapshot | 知识库 | M1 | 是 | AI 上下文快照;批改→再生成证据(来源/策略/环境引用) |
| 32 | t_api_contract | 知识库 | M1 | 是 | OpenAPI 规范化/审核 |
| 33 | t_api_contract_version | 知识库 | M1 | 是 | 契约版本审核(APIContractVersion 状态机) |
| 34 | t_api_operation_version | 知识库 | M1 | 是 | 操作级版本(method+normalized_path 唯一) |
| 35 | t_api_contract_baseline | 知识库 | M3 | 是 | 执行冻结契约基线(TEST_DESIGN/MOCK/CONTRACT_ANALYSIS) |
| 36 | t_knowledge_entry | 知识库 | M4 | 是 | KnowledgeEntry 正式产出物 |
| 37 | t_knowledge_entry_version | 知识库 | M4 | 是 | 知识版本(稳定根不可变) |
| 38 | t_knowledge_candidate | 知识库 | M4 | 是 | 知识候选人工发布 |
| 39 | t_knowledge_vector | 知识库 | M4 | 部分 | 基础检索/RAG(V1 最小);向量运营/检索增强 V2+ |
| 40 | t_knowledge_graph_node | 知识库 | V2+ | 否 | 自动知识图谱运营(V2) |
| 41 | t_knowledge_graph_edge | 知识库 | V2+ | 否 | 同上 |
| 42 | t_test_strategy | 测试策划与设计 | M1 | 是 | 主链;已切片;八类正式产出物之一 |
| 43 | t_test_strategy_version | 测试策划与设计 | M1 | 是 | 已切片 |
| 44 | t_test_plan | 测试策划与设计 | M1 | 是 | 主链;已切片;Release-TestPlan 状态机 |
| 45 | t_test_plan_version | 测试策划与设计 | M1 | 是 | 已切片 |
| 46 | t_testing_ir | 测试策划与设计 | M1 | 是 | 需求分析中间产物(compile 入口) |
| 47 | t_business_rule | 测试策划与设计 | M1 | 是 | 业务规则 |
| 48 | t_test_scenario | 测试策划与设计 | M1 | 是 | 场景 |
| 49 | t_design_test_case | 测试策划与设计 | M1 | 是 | 设计用例 |
| 50 | t_test_case | 测试策划与设计 | M1 | 是 | 主链;已切片;八类正式产出物之一 |
| 51 | t_test_case_version | 测试策划与设计 | M1 | 是 | 已切片 |
| 52 | t_assertion | 测试策划与设计 | M1 | 是 | 断言(被拒断言不离覆盖率分母) |
| 53 | t_test_suite | 测试策划与设计 | M1 | 部分 | V1 套件最小可用;批量/组合增强 V2+ |
| 54 | t_test_suite_version | 测试策划与设计 | M1 | 部分 | 同上 |
| 55 | t_test_suite_case_mapping | 测试策划与设计 | M1 | 部分 | 同上 |
| 56 | t_automation_script | 自动化测试开发 | M3 | 是 | AutomationScript 闭环;八类正式产出物之一 |
| 57 | t_automation_script_version | 自动化测试开发 | M3 | 是 | MANAGED 代码版本(不依赖 Git 模式,V1 增强项) |
| 58 | t_automation_script_version_case_binding | 自动化测试开发 | M3 | 是 | 精确用例绑定 |
| 59 | t_automation_check_run | 自动化测试开发 | M3 | 是 | 静态/安全检查记录(试运行/Code Review 门) |
| 60 | t_test_data | 自动化测试开发 | M3 | 部分 | 测试数据最小集;数据增强 V2+ |
| 61 | t_test_data_profile | 自动化测试开发 | V2+ | 否 | 数据 Profile(V2) |
| 62 | t_locator | 自动化测试开发 | V2+ | 否 | Locator 自愈候选(V2) |
| 63 | t_mock_config | 自动化测试开发 | V2+ | 否 | Mock 增强(V2) |
| 64 | t_visual_baseline | 自动化测试开发 | V3 | 否 | 视觉扩展(V3) |
| 65 | t_performance_baseline | 自动化测试开发 | V3 | 否 | 性能扩展(V3) |
| 66 | t_execution_plan | 测试执行 | M3 | 是 | 冻结执行计划 |
| 67 | t_execution_plan_version | 测试执行 | M3 | 是 | 精确资产/环境/契约版本冻结 |
| 68 | t_execution_contract_baseline | 测试执行 | M3 | 是 | 环境快照/entries/凭证引用/masking 冻结 |
| 69 | t_execution_task | 测试执行 | M3 | 是 | Runner 执行任务(状态机:取消/超时/受控重试) |
| 70 | t_execution_result | 测试执行 | M3 | 是 | 不可变结果(执行证据不可被分析结论覆盖) |
| 71 | t_execution_artifact | 测试执行 | M3 | 是 | 日志/证据制品 |
| 72 | t_api_observation | 测试执行 | M3 | 是 | API 请求响应证据(主链:request/response 摘要) |
| 73 | t_contract_check_result | 测试执行 | M3 | 部分 | ContractCheckResult 承接(L1-复验遗留 4 项之一);规则引擎 V2+ |
| 74 | t_result_analysis | 质量分析与缺陷 | M4 | 是 | 结果分析草稿;八类正式产出物之一 |
| 75 | t_result_analysis_version | 质量分析与缺陷 | M4 | 是 | 版本审核 |
| 76 | t_failure_analysis | 质量分析与缺陷 | M4 | 是 | 基础 RCA |
| 77 | t_failure_cluster | 质量分析与缺陷 | M4 | 是 | 失败聚类建议 |
| 78 | t_failure_cluster_member | 质量分析与缺陷 | M4 | 是 | 聚类成员 |
| 79 | t_coverage_report | 质量分析与缺陷 | M4 | 是 | 基础覆盖/风险汇总(覆盖率分母口径) |
| 80 | t_defect | 质量分析与缺陷 | M4 | 是 | Defect 主表(状态机) |
| 81 | t_defect_version | 质量分析与缺陷 | M4 | 是 | Defect 版本/审核;八类正式产出物之一 |
| 82 | t_defect_evidence | 质量分析与缺陷 | M4 | 是 | 缺陷证据 |
| 83 | t_defect_status_event | 质量分析与缺陷 | M4 | 是 | 生命周期只追加 |
| 84 | t_external_defect_link | 质量分析与缺陷 | M4 | 部分 | V1 手工同步落库(裁决 B2-4);自动双向同步 V2+ |
| 85 | t_defect_sync_attempt | 质量分析与缺陷 | M4 | 部分 | 手工同步仍须落尝试记录+批准+回执(裁决 B2-4) |
| 86 | t_test_report | 质量分析与缺陷 | M4 | 是 | TestReport 生成/签署;八类正式产出物之一 |
| 87 | t_test_report_version | 质量分析与缺陷 | M4 | 是 | 签署后不可覆盖(只追加) |
| 88 | t_quality_gate | 质量分析与缺陷 | V2+ | 否 | 规则型门禁(V2;V1 不自动阻断,数据表可预留) |
| 89 | t_pipeline_config | 质量分析与缺陷 | V2+ | 否 | CI 触发/流水线(V2) |
| 90 | t_pipeline_run | 质量分析与缺陷 | V2+ | 否 | 同上 |
| 91 | t_skill | AI Agent中心 | M1 | 是 | allowlist Skill 目录 |
| 92 | t_workspace_skill_enablement | AI Agent中心 | M1 | 是 | 工作区 Skill 启用 |
| 93 | t_agent | AI Agent中心 | M1 | 是 | 治理 Agent 目录(1 Supervisor + 3 Subagent) |
| 94 | t_workspace_agent_enablement | AI Agent中心 | M1 | 是 | 工作区 Agent 启用 |
| 95 | t_agent_skill_grant | AI Agent中心 | M1 | 是 | 最小权限授予 |
| 96 | t_agent_workflow | AI Agent中心 | M1 | 是 | 固定 Workflow(gate0-workflow.json 落库) |
| 97 | t_agent_prompt_version | AI Agent中心 | M1 | 部分 | 固定 Prompt 版本化;灰度/自动优化 V2+ |
| 98 | t_agent_session | AI Agent中心 | M1 | 是 | 会话;已切片(Provider 版本/摘要/Trace 记录) |
| 99 | t_agent_trace_node | AI Agent中心 | M1 | 是 | Trace 节点;已切片(失败原因/成本时长) |
| 100 | t_skill_invocation | AI Agent中心 | M1 | 部分 | Skill 调用证据最小集;规模化统计/预算 V2+ |
| 101 | t_eval_dataset | AI Agent中心(Eval) | M5 | 是 | 黄金集数据集(approval_status/content_digest) |
| 102 | t_eval_case | AI Agent中心(Eval) | M5 | 是 | 评测用例(risk_tags/expected_ref) |
| 103 | t_eval_run | AI Agent中心(Eval) | M5 | 是 | 评测运行(target AGENT/SKILL/PROMPT/WORKFLOW) |
| 104 | t_eval_result | AI Agent中心(Eval) | M5 | 是 | 逐 case 裁决(PASS/FAIL/ERROR/SKIPPED) |
| 105 | t_calibration_record | AI Agent中心(校准,8-14 B2-3 已建) | M5 | 是 | 介入点校准记录;待扩展 subject_operation/subject_table 绑定列(裁决 8-14) |
| 106 | t_verify_verdict | AI Agent中心(独立验证,M1 最小落点,裁决 8-14) | M1 | 是 | INDEPENDENT_VERIFY 裁决表:三层证据第二层落点,支撑"禁止 AI 自批"负向用例 |

---

## 4. 每里程碑核心链 API 响应契约收敛义务(QF-REQ-005)

> 背景:8-11 复审 OpenAPI 实现准入 REVISE(73 处通用响应);32 号 $ref 引用 80 个 schema 名但实际仅定义 32 个块,48 个"被引用未定义"(多为 XxxCreate/状态枚举,含核心链模块);KNOWN_DEFERRED_COUNT=80→82(execution-design 裁决);Stage4 运行时 22/102 ops。
> 收敛规则(每个里程碑):①其覆盖 operation 的响应/请求 schema 必须在 32 号落地为具体定义(不得引用 Generic/未定义块);②`openapi-spec-validator` PASS;③运行时 op 数进入 KNOWN_DEFERRED 台账对账,防静默漂移测试保持;④路径级数量以本表解析为准(79 paths/104 ops,与 grep 口径 78/102 差 1/2,见未核实项)。

| 里程碑 | 核心链收敛范围(paths / ops,实算) | 收敛义务与检查项 |
|---|---|---|
| **M1** | 策略 4/5(/test-strategies×2、/testing-irs×2)+ 计划 2/3(/test-plans×2)+ 用例 5/8(/test-scenarios、/test-case-drafts/generate、/test-cases×2、/test-suites)+ 知识库支撑 7/9(导入/需求/契约/搜索) | 草稿生成、批改、新版本、二次复核相关响应必须含 versionId/contentDigest/审核状态;XxxCreate 请求体定义补齐;TestStrategy/TestPlan/TestCase 三模块 16 ops 收敛,知识库 9 ops 收敛(APIContract 是策略/用例输入源);Stage4 已运行时 22 ops 中 planning 链 ops 复核响应结构 |
| **M2** | 看板/审核 8/10(/work-items×4、/review-tasks×4)+ t_work_item_dependency 关联 API | work-items 响应含 assignee_id/priority/sla_seconds/due_at/blocked 字段与筛选参数;review-tasks 队列/分派/逾期契约;看板为编排支撑域(非核心链 5 模块),但作为核心链入口须先收敛 |
| **M3** | 执行/自动化 16/19(/execution-plans×3、/execution-tasks×3、/execution-results×2、/automation/scripts×2、/automation/script-versions/{id}/checks、locators/mocks/data-profiles/visual-baselines×4)+ 契约基线 1/1 | 执行结果响应含不可变证据 ref(contentDigest)、环境快照;AutomationScript 版本/检查响应;locators/mocks/data-profiles/visual-baselines 4 paths 属 V2+ 契约,可显式进入 KNOWN_DEFERRED 台账(不得静默缺失);execution-contract-baseline 冻结响应 |
| **M4** | 分析 10/14(/quality/result-analyses、failure-clusters、defects×4、reports)+ 知识库产出 3/4(entries、candidates、search)+ gates/pipelines×3 | result-analysis/defect/report 草稿→审核→签署响应收敛;gates/pipelines/pipeline-runs 3 paths 属 V2+,显式台账;knowledge entries/candidates 发布响应;追溯链查询契约(报告→执行→代码→用例→来源) |
| **M5** | AI 中心 10/12(/ai/skills、agents、workflows、sessions×2、eval-runs、calibrations×2、independent-verify) | eval-runs 创建/结果响应(metrics/verdict 结构);sessions/trace 响应含 provider ID/version(替换 Provider 的识别基线);skills/agents/workflows 目录契约 |

**核心链合计(严格 5 模块:策略/计划/用例/执行/分析)= 41 paths / 53 ops**(占全量 104 ops 的 51.0%);加支撑域(知识库/看板/AI)后 V1 主链覆盖约 80 ops,其余为平台与 V2+ 契约。收敛完成标志:核心链 53 ops 全部具体 schema、validator PASS、无 Generic 响应残留(8-11 的 73 处通用响应逐处关闭清单)。

---

## 5. V1 必需表汇总统计(104 张实算)

| 维度 | 数量 | 占比 | 说明 |
|---|---|---|---|
| V1 必需=是 | **79** | 75.96% | M1=47、M3=13、M4=15、M5=4;M2 新增 0(能力里程碑) |
| V1 必需=部分 | **13** | 12.50% | M1=7、M2=1、M3=2、M4=3(最小能力/手工模式,V2+ 完整化) |
| V1 涉及合计(是+部分) | **92** | 88.46% | V1 主链 + 最小支撑 |
| V1 必需=否 | **12** | 11.54% | 全部 V2+/V3:delegation/support_access、graph_node/edge、test_data_profile、locator、mock_config、visual/performance_baseline、quality_gate、pipeline_config/run |
| 按里程碑建表 | M1=54、M2=1、M3=15、M4=18、M5=4 | — | 合计 92(V1 涉及);V2+/V3=12 |
| 模块覆盖 | 8/8 模块均有 V1 必需表 | — | 任务看板 7、知识库 15、策划设计 14、自动化 10、执行 8、质量分析 17、AI 中心 14(含 Eval 4)、平台 19(含 RBAC 9) |

---

## 6. 未核实项

1. **32-API 路径/操作口径差**:本表解析 79 paths / 104 ops;快照 grep 口径 78 / 102。差 1 path / 2 ops,疑为路径键含子路径或 $ref 内 path 键,未逐行核对差异行;建议下次审计统一口径(不影响 104 表结论)。
2. **48 个"被引用未定义"schema 归属**:未逐一核对哪些属核心链(§4 收敛义务按 path 组划定,未按 schema 名核对)。
3. **M1 建表落地数据库 Profile 未定**:V1 沿用 SQLite(Stage3/4 切片)还是切目标 PostgreSQL(RLS/只追加),未在现有 VERDICT 中找到裁决(execution-design 共识仅覆盖 execution-workflow 极小 DAG);M1 开工前需确认,否则建表清单的"落库"载体有二义性。
4. **t_quality_gate 数据表预留**:标注"V2+ 否",但若 V1 需要记录门禁建议(非阻断)需复核 05 §5.13.3 质量分析 V1 范围("自动质量门禁阻断"明确延后,规则型 QualityGate 在 V2)——维持"否"。
5. **测试套件 V1 必要性**:05 §5.13.3 策划设计 V1 未点名 TestSuite(场景/用例/断言/覆盖缺口已点名),本表按"部分"处理;若 M1 主流程不需要套件聚合,可降为 V2+(以 M1 实现时确认为准)。
6. **Owner 落位**:当前单人实施(yount),Owner 建议中的"工程/评审"角色在单飞模式下由同一人兼任,但验收职责分离仍按 REV(qf-independent-verifier)独立出报告,不因单人实施而合并证据链。
7. **stage4 E2E 截图与现场库**:现场 SQLite 业务数据 0 行(快照 §2.2),M1 验收需重跑生成新证据,不得引用空库状态。

---

## 裁决记录(2026-08-14,项目负责人确认)

| # | 待裁决项 | 最终裁决 |
|---|---|---|
| ① | V1 落地数据库 Profile + PG 冒烟时点 | **PG 冒烟门禁定为 M2 准出、进 M3 前**;验收点 = 104 表迁移 + RLS 策略 + 核心链并发写入,通过后放行 M3。M1 建表载体:V1 继续 SQLite 切片(与 B2-7、QF-REQ-034 一致) |
| ② | t_quality_gate 标注 V2+ | **接受**(V1 不自动阻断;V1 覆盖率/聚类汇总走 coverage_report/failure_cluster) |
| ③ | TestSuite 三表"部分" | **接受**(M1 建表最小能力,V2+ 完整化) |

> 本裁决同步记录于 docs/05-audits/current/L1-一致性复验纠正-2026-08-13.md 补记段(2026-08-14)。

---

## 准出压力 Owner 与验收时点(2026-08-14 拍板)

> 澄清:复核报告将 PG 冒烟计入"M1 压力"属口径混淆——按 B2-7 裁决,PG 冒烟门禁为 **M2 准出、进 M3 前**,不提前到 M1。M1 准出压力实际为以下两项:

| 项 | Owner | 验收时点 | 验收 DoD | 绑定 |
|---|---|---|---|---|
| INDEPENDENT_VERIFY 运行时 | ENG 实现 + REV 独立审定 | **M1 准出** | /ai/independent-verify 可落 t_verify_verdict;verifier 与生产 Agent 权限隔离可验证 | M1 DoD"禁止 AI 自批"负向用例(对照表 §2 M1 验收③) |
| 031 六条负向用例(N1-N6) | ENG 实现 | **M1 准出** | N1 悬空引用/N2 跨租户/N3 审核绑定漂移/N4 溯源断链/N5 环依赖/N6 跨版本绑定 全 PASS | 进 M1 验收清单(对照表 §2 M1 验收③ 扩展) |
| PG 冒烟 | ENG 执行 + PO 验收 | **M2 准出、进 M3 前**(B2-7,不提前) | 104/106 表迁移 + RLS 策略 + 核心链并发写入 PASS | M2 门禁;M1 仅排期预留不验收 |

> 口径声明:完善度 88.8% 为**文档层+方案层**口径(方案就绪计 0.5 分);运行时验证(031 负向用例、034 PG 冒烟、032/033/048 证据、006 实例)接近零,不构成"接近完成"的读数。运行时维度另以 M1/M2 准出验收为度量。
