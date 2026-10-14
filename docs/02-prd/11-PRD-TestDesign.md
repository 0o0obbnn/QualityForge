# 11-PRD-知识库

> 现行模块：知识库。文件名为兼容历史链接保留。测试设计职责已迁至12号；本模块是需求、APIContract和已审核知识的唯一Owner。

## 1. 目标与边界

把需求、OpenAPI、流量观察、仓库资料和测试经验转成有来源、有版本、有适用范围的测试依据，解决资料分散、契约漂移、AI引用过期内容和知识污染问题。

本模块不拥有TestCase、AutomationScript、ExecutionResult或ResultAnalysis；只提供它们引用的精确来源/契约/知识版本。

## 2. 功能需求

| 能力 | 需求 | AI作用 | 人工控制 |
|---|---|---|---|
| 来源导入 | 支持文件、URL、集成、手工、流量等来源，固化原文/定位、摘要、授权和时间 | 解析、分类、敏感性提示 | 确认导入范围和冲突来源 |
| 需求版本 | RequirementDocument稳定根+不可变版本，保留SourceTrace | 抽取章节、规则和变更摘要 | 裁决歧义和业务规则 |
| API契约 | APIContract稳定根、Version、Operation/Schema版本及DECLARED/OBSERVED分层 | 规范化、差异和漂移分析 | 批准契约版本/基线，决定冲突 |
| 契约基线 | 为Release和用途固定契约版本/摘要集合 | 推荐受影响契约 | 人工确认关键接口范围 |
| 知识条目 | 草稿、审核、发布、失效、归档；记录适用/失效条件和来源 | 从已审核结果提炼Pattern草稿 | 发布、纠错和失效判断 |
| 检索 | 关键词/向量/图谱混合检索，返回来源、版本和相关性解释 | 排序、摘要、上下文组装 | 命中不等于可信；用户可排除错误来源 |
| 候选治理 | 处理重复、冲突、陈旧、敏感和低证据候选 | 聚类与合并建议 | 人工决定合并/发布/拒绝 |

## 3. 关键规则

- SourceSnapshot不可变；重新抓取产生新快照。
- APIContract由本模块唯一拥有；Mock、设计与执行只引用APIContractVersion/Baseline。
- DECLARED、OBSERVED、MANUAL、MERGED必须标记来源，不静默覆盖。
- KnowledgeEntry是八类正式产出物之一，至少一名人类批准后才可`PUBLISHED`。
- 检索结果必须带sourceTrace、version、digest和适用范围；Agent不得把高相似度当事实。
- 来源撤权/敏感性变化时停止新增使用，并标记受影响产出物待重评，不删除历史证据。

## 4. 主流程

```text
导入来源 → SourceSnapshot → 解析需求/API候选 → 冲突与敏感预检
→ 创建稳定根和不可变版本 → 人工裁决/批准基线
→ 被TestingIR、Mock、执行和分析按精确版本引用
→ 已审核经验形成KnowledgeEntry草稿 → 人工发布/失效
```

## 5. 异常与降级

- 文档破损/加密/格式不支持：保留导入失败记录，转人工补录或转换，不编造解析内容。
- DECLARED与OBSERVED冲突：同时保留，创建冲突WorkItem，禁止自动合并为权威。
- 依赖内容摘要变化：使用方版本标记`STALE`并重新评估。
- 无有效Eval校准记录：检索分数仅排序，不自动发布知识或选择契约真相。

## 6. 验收标准

### AC-01 来源可追溯

- **Given** AI从需求文档提取BusinessRule；
- **When** 用户查看规则；
- **Then** 可定位SourceSnapshot、文档版本和原文位置，摘要匹配（判定口径：随机抽检≥5条规则，比对摘要与原文定位一致，裁决 2026-08-14 批次二）。

### AC-02 契约冲突不静默覆盖

- **Given** OpenAPI声明响应字段必填但流量中缺失；
- **When** 导入Observation；
- **Then** 两类证据并存并创建冲突，不自动修改已批准APIContractVersion。

### AC-03 知识发布需要人

- **Given** AI从失败历史生成Pattern草稿；
- **When** 生成完成；
- **Then** 状态为`PENDING_REVIEW`且ReviewTask绑定版本/摘要，Agent不能发布。

### AC-04 精确基线可复现

- **Given** Release已批准APIContractBaseline；
- **When** 后续契约出现新版本；
- **Then** 原执行仍能解析到旧版本及摘要，新版本不自动替换历史基线。

## 7. 版本范围

V1支持Markdown/OpenAPI导入、版本、基础检索和人工知识发布；V2增强流量/仓库、漂移、混合检索和反馈；V3增强企业级来源治理和知识运营。
## 8. 指标承接(裁决 2026-08-14;指标口径见 20 号 §1.1 受控 metricKey 登记表,覆盖率口径见 22 号附录 C)

| 指标 | 本模块角色 | 基线 | 测量方法 | 验收 |
|---|---|---|---|---|
| 知识条目过期率(M-31) | 生产 | 试点后批准(22 §6) | 窗口内 STALE/到期未复核条目/活跃条目,KnowledgeEntryVersion.reviewStatus,整 Release | AC:过期率可复算且按条目类型分层 |
| 正向/反向链完整率(M-43) | 生产(SourceTrace 载体) | 试点后批准 | 关键跳转有 CONFIRMED/INFERRED 边的链数/应覆盖链数,SourceTraceEdge,整 Release | AC:链完整率按 evidenceClass 分层报告 |
| 知识条目复用命中率(M-30) | 生产(载体 V2) | 载体建立后批准 | 检索命中且采纳条目/检索命中总数 | AC:检索日志载体建立前不报目标值 |
