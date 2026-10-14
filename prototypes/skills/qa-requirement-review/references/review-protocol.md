# 全量需求评审协议

## 评审顺序

1. 固化来源版本与权威级别。
2. 建立来源单元台账。
3. 建立需求条目和现有图谱追踪。
4. 逐需求完成六维评审。
5. 跨需求、跨模块和跨来源复核。
6. 生成测试点与就绪度。
7. 运行确定性校验并渲染报告。

分批执行时，每一批必须写回同一个台账。批次完成以需求和来源单元对账为准，不以生成了报告为准。

## 评审主体与候选扫描

执行模型或人工评审者负责第 3 至第 6 步的语义判断。确定性脚本可以发现文字模式、结构缺口和图谱显式冲突，但这些输出只用于建立候选队列；评审者必须阅读候选项对应的原始段落、上下文、表格和关联资料后再作结论。

- `CLEAR`：已检查该维度需要的来源范围，并有来源引用和明确理由支持“未发现问题”。
- `FINDING`：已验证问题成立，并通过 finding 保存 QUOTE、ABSENCE 或 CONFLICT 证据。
- `NOT_APPLICABLE`：已读取来源并说明为什么该维度不适用，同时保留来源引用。
- `NOT_REVIEWED`：尚未阅读完整上下文、证据不足或无法可靠判断。

扫描器零命中、图谱字段非空、存在动作名或存在数值，都不能单独支持 `CLEAR`。

## 检查清单

- `ambiguity`：主体、动作、对象、条件、范围、术语和量化标准。
- `consistency`：正文、表格、原型、接口、状态、字段和复用基线之间的冲突。
- `testability`：可构造触发、可控制输入、可观察结果和可判定 oracle。
- `completeness`：正常、异常、边界、数据、并发、状态、依赖、超时、重试和恢复。
- `nfr_measurability`：适用质量特性的范围、负载、环境、指标、阈值和观察窗口。
- `role_permission`：角色、组织、数据范围、允许/拒绝行为、导出和脱敏。

## Finding codes

| Code                             | 最低严重度 |
| -------------------------------- | ---------- |
| `CROSS_SOURCE_CONFLICT`          | REJECT     |
| `INTRA_DOCUMENT_CONFLICT`        | REJECT     |
| `ROLE_PERMISSION_CONFLICT`       | REJECT     |
| `UNTESTABLE_ACCEPTANCE_CRITERIA` | REJECT     |
| `MISSING_REQUIRED_ACTOR`         | REJECT     |
| `UNMEASURABLE_NFR`               | REJECT     |
| `AMBIGUOUS_LANGUAGE`             | REVIEW     |
| `INCOMPLETE_REQUIREMENT`         | REVIEW     |
| `MISSING_EXCEPTION_BEHAVIOR`     | REVIEW     |

`INTRA_DOCUMENT_CONFLICT` 由结构化冲突检测器产生：同字段多处枚举不一致、同锚点（如位次定义）多处口径不一致、同一指标出现多个不同数值。它必须携带 CONFLICT 证据并保留冲突双方原文与定位。

REVIEW code 可以升级为 REJECT，REJECT code 不能降级。

## 证据判定

- `QUOTE` 证明原文明示内容。
- `ABSENCE` 证明在声明的检查范围内没有找到预期要素。
- `CONFLICT` 证明两段有来源的内容不能同时成立。

“需求没有写”是范围化结论。ABSENCE 必须列出检查过的章节、表格或接口定义。

## 总体判定

- `PASS`：全量评审完成，无 finding，产物可正式下游使用。
- `PASS_WITH_REVIEW`：无 REJECT finding，但存在 REVIEW finding；不能作为正式下游基线。
- `REJECT`：存在 REJECT finding、来源遗漏或评审未完成。
- `NOT_RUN`：仅建立草稿或尚未执行验收。

结构校验只验证产物内部一致性。语义验收还要抽样或基于基准需求核对问题召回、误报、跨段冲突和 `CLEAR` 的证据充分性。
