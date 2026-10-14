# 既有/本地测试脚本导入纳管 补充设计建议稿

> 状态：待裁决的设计建议稿（2026-08-15）。本文件是分析建议，不代表契约已变更。
> 若获批准，需同步修订：`01-product/05-功能模块重构方案.md` §5.8、`02-prd/13-PRD-Execution.md`、
> `04-architecture/32-API规范.yaml`、`04-architecture/33-数据库Schema设计.md`，并在
> `04-architecture/35-变更记录CHANGELOG.md` 登记。

---

## 1. 背景与问题

现行设计对自动化测试代码（`AutomationScript / AutomationScriptVersion`）定义了两条生产路径：

1. **AI 从零生成**（V1 MUST，13-PRD §4 主流程）：已批准用例/契约 → AI 草稿 → 检查 → CODE_REVIEW → 冻结执行；
2. **GIT 模式登记**（SHOULD，V1 末/V2）：代码权威源在团队仓库，平台按 repo + commit SHA + path + blob SHA 钉住版本。

但试点场景存在第三种现实状态：**团队已有一批测试脚本，散落在本地磁盘或无仓库管理的目录中**。
当前契约对这条"存量导入"路径没有正式定义，存在三个具体缺口：

| # | 缺口 | 后果 |
|---|------|------|
| G1 | 导入版本无法与已批准 `TestCaseVersion` 建立绑定（存量脚本往往没有对应正式用例） | §5.6.6 最低内容门禁要求"关联用例"才能进 PENDING_REVIEW，导入版本被门禁卡死，无合法出路 |
| G2 | `sourceTrace` 无法区分"人工导入"与"AI 生成" | 指标（M-05 自动化代码首版生成时间）统计被污染；审核风险定级缺少依据 |
| G3 | 本地脚本通常缺依赖锁与运行时指纹 | §5.8.4 要求 `dependencyLockRef/digest`、`runtimeSpec` 必填，导入版本无法满足，不可复现执行 |

对照参考：测试用例的存量迁移已有正式规则（11-PRD §3.3 字段映射表），自动化代码缺等价设计。

## 2. 设计目标与非目标

**目标**

- 存量/本地脚本能通过一条受治理的路径进入平台权威链，成为 MANAGED 不可变版本；
- 导入版本与 AI 生成版本共用同一套检查、CODE_REVIEW、冻结执行规则，不开审核后门；
- 导入来源可审计、可统计、可追溯。

**非目标**

- 不实现 IDE 级代码编辑、跨仓库编排（与 13-PRD 裁剪口径一致）；
- 不替代 GIT 模式：团队若已有仓库，推荐先入仓库再走 GIT 模式登记；
- 不承诺自动解析任意框架的脚本语义（导入是"登记 + 审核"，不是"理解 + 重构"）。

## 3. 导入路径总体设计

```text
组织导入包（代码文件 + 清单 manifest + 依赖锁 + 运行时声明）
→ 确定性导入预检（包结构/大小/密钥扫描/锁文件完整性）
→ 创建 AutomationScript 稳定根 + AutomationScriptVersion 草稿
   （sourceMode=MANAGED，originType=HUMAN_IMPORTED，importBatchId 留痕）
→ AutomationCheckRun（静态/安全/依赖检查；受控试跑可选）
→ 用例绑定（已有批准用例直接绑定；无用例时走"用例回填"子流程，见 §4.1）
→ CODE_REVIEW ReviewTask → 人工批准
→ 已批准版本可被 ExecutionPlanVersion 冻结
```

导入批次（`importBatchId`）是一次批量导入的编排单元，逐文件报告成功/失败，
部分成功必须明确展示（对齐 §5.9.8 Defect 批量提交的既定规则），不存在"整批成功"。

## 4. 三个缺口的处理方案

### 4.1 G1：无用例时的绑定出路——"用例回填"子流程

规则选择（建议采纳 B）：

- **A. 放宽门禁**：允许导入版本零绑定通过审核。❌ 不采纳——破坏 §5.6.6"关联用例"门禁，
  且执行侧无法做覆盖统计；
- **B. 用例回填**（建议）：导入预检发现无匹配已批准用例时，系统为每个脚本候选创建
  **用例回填 WorkItem**（type=TEST_DESIGN，origin=IMPORT_BACKFILL），由 AI 从脚本内容
  提取用例草稿（步骤/数据/断言反向映射），走标准 DesignTestCase 审核批准后，
  再回到脚本版本完成绑定；
- **C. 永久挂起**：只登记不绑定，执行永远禁止。仅作为 B 的兜底状态存在。

采纳 B 后的状态规则：

1. 未完成有效绑定的导入版本可以存在、可以过检查，但 `reviewStatus` 最高停在
   `CHANGES_REQUESTED` 语义的"待绑定"态，**不得进入 PENDING_REVIEW**；
2. 绑定到已批准 `TestCaseVersion` 后自动解锁进入 PENDING_REVIEW；
3. 正式执行前的绑定有效性检查（§5.8.5 既有规则）不变；
4. 回填用例的审核标准与正常用例一致，不得因为是"补手续"而降级为单人自批。

### 4.2 G2：来源可区分——新增 `originType` 字段

在 `AutomationScriptVersion` 上新增必填字段：

| 字段 | 约束 | 取值 |
|------|------|------|
| `originType` | 必填 | `AI_GENERATED` / `HUMAN_IMPORTED` / `HUMAN_AUTHORED`（平台内人工新建） |
| `importBatchId` | HUMAN_IMPORTED 必填 | 导入批次标识 |

规则：

- `originType=AI_GENERATED` 时 `generatedByAgentId` 维持现行"可选"但强烈推荐；
  `HUMAN_IMPORTED` 时 `generatedByAgentId` 必须为空，`sourceTrace` 记录原始来源
  （原路径/原系统/导入人/导入时间）；
- M-05 等"AI 生成"类指标统计必须过滤 `originType != AI_GENERATED`，防止导入冒充生成；
- 后续 AI 对导入版本做修改产生新版本时，新版本 `originType` 按主要生产者标注，
  并通过 `supersedesVersionId` 保留来源链。

### 4.3 G3：依赖锁与运行时指纹——导入即采集，缺失即拒绝

导入预检的确定性门禁（任一失败则该文件导入 REJECT，可修复后重导）：

1. **依赖锁必须随包提供**：Python 接受 `uv.lock`/`requirements.txt`（含 hash pin），
   Node 接受 `package-lock.json`；无锁文件时预检 REJECT 并给出补锁指引，
   不允许平台代为猜测依赖；
2. **运行时声明必填**：manifest 中声明语言/框架/运行时版本与入口命令，
   写入 `runtimeSpec`；与代码声明（如 pyproject `requires-python`）冲突时 REJECT；
3. **采集后固化**：平台对锁文件计算 `dependencyDigest`，与代码 `contentDigest`
   一同冻结进版本，Runner 按指纹还原环境（对齐 31-系统架构 §执行流程第 3 步）。

## 5. 安全边界（对齐既有供应链治理口径）

导入的是**可执行代码**，属于可执行供应链，按 CH-17（SkillCenter 沙箱模型）与
44-整体设计审计的既定原则叠加执行：

1. 导入预检执行明文密钥/凭证扫描，命中即 REJECT（对齐 13-PRD"代码与 Secret 分离"）；
2. 导入包限制：单文件大小上限、压缩炸弹防护、路径穿越校验（对齐 52-综合评估 §风险清单第 7 条）;
3. **导入过程不执行任何被导入代码**；受控试跑是批准前的独立可选步骤，
   沿用 B2-8 沙箱口径（非 root、只读工作目录、默认零外网、超时上限、产出白名单）；
4. 导入批准走 `CODE_REVIEW` 策略；HIGH/CRITICAL 或含危险操作（删除类 API、
   生产邻近操作）的脚本适用四眼原则（§5.6.3 既定规则，无需新增）。

## 6. 契约变更清单（批准后执行）

| 文档/契约 | 变更 |
|-----------|------|
| `05-功能模块重构方案.md` | §5.8.4 字段表新增 `originType`/`importBatchId`；新增 §5.8.7"存量脚本导入"小节 |
| `13-PRD-Execution.md` | §2 能力表新增"脚本导入"行；§7 版本范围标注导入能力级别（建议 SHOULD，V1 末） |
| `32-API规范.yaml` | 新增导入批次端点（创建批次/提交文件/查询逐文件结果）；`AutomationScriptVersionCreate` 增加 `originType`；用例回填 WorkItem 类型枚举扩展 `IMPORT_BACKFILL` |
| `33-数据库Schema设计.md` | `automation_script_version` 增加 `origin_type`（CHECK 三值）与 `import_batch_id`；新增 `script_import_batch` 表（批次/导入人/逐文件状态） |
| `35-变更记录CHANGELOG.md` | 登记本次契约修订条目 |

## 7. Given/When/Then 验收基线（草案）

1. **缺锁拒绝**：Given 导入包缺少依赖锁文件，When 提交导入预检，Then 该文件 REJECT 并展示补锁指引，同批次其余文件不受影响。
2. **密钥拦截**：Given 脚本含硬编码 API Key，When 预检扫描命中，Then 导入被拒绝且代码不进入任何版本存储。
3. **无绑定不可审**：Given 导入版本未绑定任何已批准用例，When 用户尝试送审，Then 系统拒绝并展示用例回填 WorkItem 入口。
4. **回填闭环**：Given 回填用例 v1 被批准，When 脚本版本绑定该用例版本，Then 版本解锁进入 PENDING_REVIEW，绑定角色与覆盖说明可审核。
5. **来源不冒充**：Given 一个 HUMAN_IMPORTED 版本，When 统计 M-05 生成时间指标，Then 该版本不计入 AI 生成口径。
6. **导入不执行**：Given 导入包通过预检，When 尚未完成 CODE_REVIEW，Then 系统未执行过被导入代码的任何部分（试跑除外且留痕）。

## 8. 待裁决问题

1. 导入能力定级：建议 **SHOULD（V1 末）**，与 GIT 模式同批次；若试点团队存量脚本规模大，可提前为 V1 MUST，需评估对 M3 里程碑的影响；
2. 用例回填是否允许 AI 自动绑定（不经人工）：本稿默认禁止，回填用例走完整审核；
3. 导入是否支持"仅登记 GIT 候选"（本地代码直接生成初始化仓库 + 首个 commit）：本稿不纳入，留待 GIT 模式成熟后评估；
4. 单次导入批量上限与配额归属（Workspace 级还是 Tenant 级）。
