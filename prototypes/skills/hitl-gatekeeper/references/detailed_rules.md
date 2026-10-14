# HITL Gatekeeper 详细规则

## 触发条件

- 任一八类正式产出物准备提交审核/发布。
- 关键路径、契约/IR变更、breaking drift、Locator反复自愈或上游`NEED_HUMAN_REVIEW`。
- Workflow明确声明human checkpoint。

## 执行流程

1. 收集event、asset type、source trace、proposed action和可选confidence。
2. 正式产出物必须同时提供artifact ID、version ID、content digest和policy type。
3. 运行`scripts/gate.py`，不得在Prompt中重新发明路由。
4. `PASS`只允许非正式机器节点进入下一机器节点。
5. `BLOCK_HUMAN`暂停Workflow，由应用服务创建ReviewTask；Skill不自行批准或修改资产。

## 禁止事项

- 不得按置信度自动批准或发布正式产出物。
- 不得输出缺版本/摘要的ReviewTask。
- 不得把Agent/Service当人工审核人。
- 不得修改被审核版本或跳过SourceTrace。
