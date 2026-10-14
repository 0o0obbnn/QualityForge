# HITL Gatekeeper 策略

21号AI治理和34号认证授权是上位权威。`gate.py`只实现确定性路由，不判断业务质量、不批准产出物。

## 正式产出物

以下类型始终`BLOCK_HUMAN`：`test_strategy`、`test_plan`、`test_case`、`automation_script`、`result_analysis`、`defect`、`test_report`、`knowledge_entry`。模型分数、机器检查PASS、Agent自治等级或管理员开关均不能改变该规则。

ReviewTask必须绑定稳定artifact ID、不可变version ID、content digest和ReviewPolicy类型。缺少任一字段时输入无效，不能生成可供盖章的审核任务。

## 强制检查点

`critical_path`、`contract_mutation`、`breaking_drift`、`healing_overrun`和`ambiguity_flag`均路由`BLOCK_HUMAN`。它们可能针对中间产物，但仍需要人工裁决后才能继续高风险变化。

## 置信度不是授权

本Skill不内置0.7/0.9等通用阈值。非正式、非强制的机器步骤可以返回`PASS`继续固定Workflow；PASS只表示机器流程可继续，不表示任何资产`APPROVED/PUBLISHED`。置信度可记录用于排序/评测，但只有21号定义的有效版本化校准记录才能用于特定自动化策略。

缺少confidence的普通inference仍视为输入质量不足并`BLOCK_HUMAN`；这不是阈值判断，而是缺失元数据的失败关闭。

## 审核语义

1. `BLOCK_HUMAN`使调用Workflow暂停。
2. 应用服务创建ReviewTask并重新计算作用域RBAC、humanOnly、职责分离和blocking checks。
3. 只有UserIdentity可提交ReviewDecision。
4. 批准时重新校验version ID和content digest；陈旧任务拒绝。
5. 退回创建新产出版本和新审核，不覆盖历史。

## 范围外

- 资产质量由对应确定性检查、独立验证和人工审核负责。
- 修改/修复返回生成Agent创建新版本。
- SLA、通知和队列排序由任务看板与ReviewPolicy负责，不由Skill写死。
