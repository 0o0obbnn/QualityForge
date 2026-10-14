# QualityForge 29 Skill 五维评估报告

> **快照边界**：本报告冻结于 2026-08-07，仅覆盖当时纳入评估的 29 个 Skill。2026-08-10 项目目录已核实为 30 个 Skill、20 个标准 `evals/evals.json`；原评分与比例不追溯改写，新增 Skill 和 Agent 治理配置须另行复审。

**评估日期**: 2026-08-07
**方法**: 五维双层评估（Layer 1 命令行结构统计 + Layer 2 全文通读质量评分）
**来源标注**: [P]=预训练知识, [W]=联网搜索, [F]=项目文件, [I]=推理归纳

---

## 一、评估框架

经过 Phase 0 多源校准（联网搜索 Sundaebar/SurePrompts/阿里 skill-up），确定五维评估标准：

| 维度 | 1 分 | 3 分 | 5 分 |
|------|------|------|------|
| **D1 清晰性** | 触发条件模糊，判据靠"理解上下文" | 触发条件明确，判据可机械化执行 | 每条指令仅一种理解方式，输出有 Schema |
| **D2 边界完整性** | 无 Must Not、无异常处理 | 有 Must Not，覆盖常见异常 | 硬约束 ≥3 条，降级策略明确，退出码语义完整 |
| **D3 可维护性** | 规则散落正文，无交叉引用 | 规则与逻辑分离，有 references/ | 配置集中管理，版本兼容声明 |
| **D4 可验证性** | 检查项无法独立测试，无 CLI | 有 CLI 入口和确定性脚本 | 有 evals/ + 基准数据 + Given/When/Then |
| **D5 结构完整性** | 缺 name/desc/Why/集成/示例中 ≥3 项 | 缺 Why 或集成或反例中的一项 | 全要素齐全 |

**评级阈值**: 22+ ⭐⭐⭐⭐⭐ | 17-21 ⭐⭐⭐⭐ | 12-16 ⭐⭐⭐ | 7-11 ⭐⭐ | ≤6 ⭐

---

## 二、全量评分表

| Skill | D1 | D2 | D3 | D4 | D5 | 总分 | 评级 | 流水线阶段 |
|-------|----|----|----|----|----|------|------|-----------|
| contract-drift-detector | 5 | 5 | 5 | 3 | 5 | 23 | ⭐⭐⭐⭐⭐ | 覆盖率与质量治理 |
| assertion-verifier | 4 | 5 | 5 | 4 | 2 | 20 | ⭐⭐⭐⭐ | 断言层 |
| ir-validator | 5 | 4 | 4 | 3 | 3 | 19 | ⭐⭐⭐⭐ | IR 发布门禁 |
| scenario-generator | 4 | 4 | 4 | 4 | 3 | 19 | ⭐⭐⭐⭐ | 测试设计层 |
| test-case-generator | 4 | 4 | 4 | 4 | 3 | 19 | ⭐⭐⭐⭐ | 测试设计层 |
| strategy-planner | 4 | 4 | 4 | 4 | 3 | 19 | ⭐⭐⭐⭐ | 测试设计层 |
| test-data-generator | 3 | 4 | 4 | 4 | 4 | 19 | ⭐⭐⭐⭐ | 测试数据与 Fixture |
| hitl-gatekeeper | 4 | 5 | 4 | 4 | 2 | 19 | ⭐⭐⭐⭐ | 人机协同门禁 |
| self-healing-orchestrator | 4 | 5 | 3 | 4 | 3 | 19 | ⭐⭐⭐⭐ | 运行时与修复 |
| change-impact-analyzer | 4 | 4 | 4 | 4 | 3 | 19 | ⭐⭐⭐⭐ | 运行时与修复 |
| requirement-quality-gate | 3 | 4 | 4 | 4 | 3 | 18 | ⭐⭐⭐⭐ | 需求处理层 |
| data-cleanup-manager | 3 | 4 | 4 | 4 | 3 | 18 | ⭐⭐⭐⭐ | 测试数据与 Fixture |
| ui-automation-generator | 4 | 3 | 4 | 4 | 3 | 18 | ⭐⭐⭐⭐ | 测试代码生成 |
| coverage-analyzer | 4 | 4 | 4 | 3 | 3 | 18 | ⭐⭐⭐⭐ | 覆盖率与质量治理 |
| data-requirement-analyzer | 3 | 3 | 4 | 4 | 3 | 17 | ⭐⭐⭐⭐ | 需求处理层 |
| business-rule-extractor | 4 | 3 | 4 | 3 | 3 | 17 | ⭐⭐⭐⭐ | 需求处理层 |
| api-test-generator | 4 | 3 | 4 | 3 | 3 | 17 | ⭐⭐⭐⭐ | 测试代码生成 |
| security-test-generator | 4 | 3 | 4 | 3 | 3 | 17 | ⭐⭐⭐⭐ | 测试代码生成 |
| quality-governance | 3 | 3 | 3 | 4 | 4 | 17 | ⭐⭐⭐⭐ | 覆盖率与质量治理 |
| failure-analyzer | 3 | 4 | 3 | 4 | 3 | 17 | ⭐⭐⭐⭐ | 运行时与修复 |
| regression-planner | 3 | 4 | 3 | 4 | 3 | 17 | ⭐⭐⭐⭐ | 运行时与修复 |
| requirement-compiler | 3 | 3 | 4 | 3 | 3 | 16 | ⭐⭐⭐ | 需求处理层 |
| state-machine-builder | 3 | 3 | 4 | 3 | 3 | 16 | ⭐⭐⭐ | 需求处理层 |
| assertion-generator | 3 | 3 | 3 | 3 | 4 | 16 | ⭐⭐⭐ | 断言层 |
| fixture-dag-planner | 3 | 4 | 4 | 3 | 2 | 16 | ⭐⭐⭐ | 测试数据与 Fixture |
| domain-model-extractor | 3 | 3 | 4 | 3 | 2 | 15 | ⭐⭐⭐ | 需求处理层 |
| performance-test-generator | 1 | 2 | 3 | 3 | 1 | 10 | ⭐⭐ | 测试代码生成 |
| locator-discovery | 1 | 3 | 2 | 3 | 1 | 10 | ⭐⭐ | 测试代码生成 |
| plan-orchestrator | 1 | 2 | 2 | 3 | 1 | 9 | ⭐⭐ | 流程编排与知识 |
| knowledge-memory | 1 | 2 | 2 | 3 | 1 | 9 | ⭐⭐ | 流程编排与知识 |

---

## 三、评级分布

| 评级 | 数量 | 占比 |
|------|------|------|
| ⭐⭐⭐⭐⭐ | 1 | 3% |
| ⭐⭐⭐⭐ | 20 | 67% |
| ⭐⭐⭐ | 5 | 17% |
| ⭐⭐ | 4 | 13% |
| ⭐ | 0 | 0% |

---

## 四、按流水线阶段的维度平均分

| 流水线阶段 | D1 均 | D2 均 | D3 均 | D4 均 | D5 均 | 总均 | Skill 数 |
|-----------|-------|-------|-------|-------|-------|------|---------|
| 需求处理层 | 3.2 | 3.2 | 4.0 | 3.3 | 2.8 | 16.5 | 6 |
| IR 发布门禁 | 5.0 | 4.0 | 4.0 | 3.0 | 3.0 | 19.0 | 1 |
| 测试设计层 | 4.0 | 4.0 | 4.0 | 4.0 | 3.0 | 19.0 | 3 |
| 断言层 | 3.5 | 4.0 | 4.0 | 3.5 | 3.0 | 18.0 | 2 |
| 测试数据与 Fixture | 3.0 | 4.0 | 4.0 | 3.7 | 3.0 | 17.7 | 3 |
| 测试代码生成 | 2.8 | 2.8 | 3.4 | 3.2 | 2.2 | 14.4 | 5 |
| 覆盖率与质量治理 | 4.0 | 4.0 | 4.0 | 3.3 | 4.0 | 19.3 | 3 |
| 人机协同门禁 | 4.0 | 5.0 | 4.0 | 4.0 | 2.0 | 19.0 | 1 |
| 运行时与修复 | 3.5 | 4.2 | 3.2 | 4.0 | 3.0 | 18.0 | 4 |
| 流程编排与知识 | 1.0 | 2.0 | 2.0 | 3.0 | 1.0 | 9.0 | 2 |

---

## 五、Top 5

### contract-drift-detector — [5/5/5/3/5] 总分 23 ⭐⭐⭐⭐⭐

- **[I] 亮点**: 唯一含 ASCII 决策树 + 两类漂移（兼容性/破坏性）完整分类 + 3 个完整使用示例 + 反模式声明
- **[F] 数据**: 183 行，是均值 48 行的 3.8 倍
### assertion-verifier — [4/5/5/4/2] 总分 20 ⭐⭐⭐⭐

- **[I] 亮点**: 三阶段流水线（静态检查→干运行→变异测试门禁）+ 决策路由表 + Must Not 硬约束
- **[I] 弱项**: D5=2，缺 Why 章节、集成接口声明、反例
### ir-validator — [5/4/4/3/3] 总分 19 ⭐⭐⭐⭐

- **[I] 评价**: D5=3，缺 Why 章节或集成接口
### scenario-generator — [4/4/4/4/3] 总分 19 ⭐⭐⭐⭐

- **[I] 评价**: D5=3，缺 Why 章节或集成接口
### test-case-generator — [4/4/4/4/3] 总分 19 ⭐⭐⭐⭐

- **[I] 评价**: D5=3，缺 Why 章节或集成接口

---

## 六、Bottom 5

### domain-model-extractor — [3/3/4/3/2] 总分 15 ⭐⭐⭐

- **[I] 问题**: D5=2，缺 Why 章节和集成接口声明，结构与高质量 skill 有明显代差
### performance-test-generator — [1/2/3/3/1] 总分 10 ⭐⭐

- **[F] 严重问题**: 正文仅 15-16 行，核心逻辑全部 defer 到 references/，SKILL.md 失去自解释能力
- **[F] 缺失**: 无 Why 章节、无反例声明、无 CLI 入口、无 evals/
### locator-discovery — [1/3/2/3/1] 总分 10 ⭐⭐

- **[F] 严重问题**: 正文仅 15-16 行，核心逻辑全部 defer 到 references/，SKILL.md 失去自解释能力
- **[F] 缺失**: 无 Why 章节、无反例声明、无 CLI 入口、无 evals/
### plan-orchestrator — [1/2/2/3/1] 总分 9 ⭐⭐

- **[F] 严重问题**: 正文仅 15-16 行，核心逻辑全部 defer 到 references/，SKILL.md 失去自解释能力
- **[F] 缺失**: 无 Why 章节、无反例声明、无 CLI 入口、无 evals/
### knowledge-memory — [1/2/2/3/1] 总分 9 ⭐⭐

- **[F] 严重问题**: 正文仅 15-16 行，核心逻辑全部 defer 到 references/，SKILL.md 失去自解释能力
- **[F] 缺失**: 无 Why 章节、无反例声明、无 CLI 入口、无 evals/

---

## 七、关键发现 [I]

1. **结构断层**：4 个「薄」skill（正文 15-16 行）与次低的 32 行有 2x 断层。核心逻辑 defer 到 references/，SKILL.md 失去自解释能力。

2. **D5 是最大短板**：仅 contract-drift-detector 得分 5。7/29 有 Why 章节。反例（counter-example）几乎全域缺失。

3. **D4 可验证性普遍薄弱**：仅 5/29 有 evals/ 目录，0/29 有 Given/When/Then 验收标准。CLI 覆盖率 9/29。

4. **D2 相对较好**：全部 29 个都有 Must Not，多数有明确退出码语义。但降级策略覆盖率仅 20.7%（6/29）。

5. **阶段差异显著**：流程编排与知识层最低（9.0），覆盖率与质量治理最高（19.3）。测试代码生成层被 2 个薄 skill 拉低到 14.4。

6. **行业对照 [W]**：对照阿里 skill-up 的「可评测回归」理念，29 个 skill 在 D4 普遍不足。

---

## 八、优化建议优先级

| 优先级 | 目标 | 说明 |
|--------|------|------|
| **P0 (Blocker)** | 4 个薄 skill | knowledge-memory/plan-orchestrator/performance-test-generator/locator-discovery 必须在 SKILL.md 中补充核心检查逻辑，不再纯 defer 到 references/ |
| **P1 (Critical)** | D5 补强 | 为所有 skill 补「Why this skill exists」章节 + 集成接口声明（输入/输出/依赖） |
| **P2 (Major)** | D4 补强 | 为关键路径 skill 补 evals/ 目录 + Given/When/Then 验收标准，使 skill 可被独立验证 |
| **P3 (Minor)** | D1/D5 提升 | 为低分 skill 补反例声明、决策树和更精确的量化阈值 |
