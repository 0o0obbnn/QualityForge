# 评审问题解决契约

评审问题解决包只表达已获得的决定和证据，不负责猜测答案：

```json
{
  "resolutions": [{
    "finding_id": "RQF-...",
    "decision": "RESOLVE",
    "resolution": "失败时返回错误码 E001 且不保存数据",
    "source_refs": ["SRC-...:L120"],
    "assessment_updates": [{
      "requirement_id": "REQ-...",
      "dimension": "testability",
      "status": "CLEAR",
      "rationale": "补充材料定义了可观察失败结果",
      "source_refs": ["SRC-...:L120"]
    }]
  }]
}
```

来源单元语义处置使用 `source_unit_reviews[]`，用于把 `review_required` 更新为
`requirement / finding / no_output / unavailable`。每项必须绑定已有 `unit_id`、给出理由，
引用需求或 finding 时 ID 必须存在。合并后重新计算来源覆盖、未评审数量、errors 和 warnings，
不得保留旧批次统计。

决定允许 `RESOLVE / WITHDRAW / ACCEPT_RISK / KEEP_OPEN / CONFIRM`。`RESOLVE / WITHDRAW / CONFIRM` 必须有解决说明和来源引用；`ACCEPT_RISK` 仍属于未解决事实，不可放行相关测试维度。`CONFIRM` 表示 AI 或人工已回读来源并确认候选问题客观成立，问题仍保持 `OPEN`，同时把 `certainty` 更新为 `confirmed`、记录语义复核依据。确认问题还影响其他已验证需求时，可用 `add_requirement_ids / add_function_ids / add_atomic_ids` 增补影响范围；这些 ID 必须已存在。若候选内容本身需要改写，撤回旧 finding 并用 `new_findings[]` 写入修订后的完整 finding，避免静默篡改原始候选证据。合并器同步重新计算逐需求评估、总体评估、生命周期和下游资格。

队列中的 `assessment_reviews[]` 用于执行模型或人工完成尚未评审的维度。每项必须填写 `CLEAR / FINDING / NOT_APPLICABLE` 和可核验理由；`CLEAR / NOT_APPLICABLE` 还必须填写实际检查过的 `source_refs`。选择 `FINDING` 时应先新增并绑定 finding，不能用空引用冒充已评审。扫描器零命中不能作为评审理由。

语义评审发现队列中不存在的新问题时，先在 `new_findings[]` 登记完整 finding，再由 `assessment_reviews[].finding_ids` 绑定。新 finding 必须使用稳定 ID，包含 `code / severity / certainty / evidence_type / requirement_ids / source_refs / evidence / question / recommendation`；`CONFLICT` 至少保留两个不同来源引用，`ABSENCE` 必须包含 `inspected_scope / expected_element`。

逐需求评估只能绑定 `requirement_ids` 中包含当前需求的 finding。共享问题必须先通过 `CONFIRM` 增补已核实的影响范围，再写入对应 `assessment_reviews`；不能仅因为标题相同或功能相邻就跨需求引用。

只改变 finding 状态、没有更新对应评估的做法不构成闭环。合并器在问题关闭而评估没有同步更新时，把该维度恢复为 `NOT_REVIEWED`，不会自动改成 `CLEAR`。
