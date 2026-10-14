# QualityForge B2 裁决整改执行包 · 契约联动项草案

> 裁决日期:2026-08-14 ｜ 裁决:11 项全部按推荐方案执行 ｜ 本文件为契约联动项(B2-1/2/3)的可粘贴修改草案;低风险项(B2-4/8/9/10/11)已直接落盘。
> 应用原则:按 54 号索引修改顺序——先裁决记录,再改 03/04,再改 PRD,再同步 32/33;应用后跑 `make contract` + L1 一致性扫描。

---

## B2-1 · CoverageReport 拆分为"设计覆盖分析 + 执行覆盖报告"(方案 A)

### 修改 1:12-PRD-TestAsset.md §6 AC-03(改写验收对象)

**原文**:
```text
### AC-03 覆盖分母透明

- **Given** CoverageReport声称90%；
- **When** 用户查看详情；
- **Then** 可见分子、分母、排除项、未覆盖项和每条SourceTrace。
```

**改为**(裁决 B2-1,2026-08-14:设计覆盖分析与执行 CoverageReport 分离):
```text
### AC-03 覆盖分析分母透明

- **Given** 设计覆盖分析声称90%；
- **When** 用户查看详情；
- **Then** 可见分子、分母、排除项、未覆盖项和每条SourceTrace。
- 注：设计覆盖分析（需求→用例映射）归本模块中间产物；执行覆盖率报告 CoverageReport 由 15 号质量分析与缺陷唯一写入（裁决 B2-1，2026-08-14）。
```

### 修改 2:15-PRD-SkillCenter.md §2 正式产出物表(补 CoverageReport 行)

在 §2 表格(ResultAnalysis/Defect/TestReport 行后)追加:
```text
| CoverageReport | 冻结范围与分母快照、已检查/偏差/未检查/不可判定数、规则/场景/状态/断言维度摘要 | 生成草稿与差异解释 | 批准分母口径与报告结论 |
```

### 修改 3:15-PRD-SkillCenter.md §3 关键规则(补覆盖语义规则)

追加:
```text
- CoverageReport 是执行覆盖率正式产出物（裁决 B2-1）：按批准的分母口径与快照生成；设计覆盖分析（需求→用例映射）归 12 号测试策划与设计，两概念不共用实体。
```

### 修改 4:05-功能模块重构方案.md §5.12.7(唯一写入边界加注)

在 `| CoverageReport | 现行t_coverage_report | 保留为可复现派生结果 | 质量模块按确定分母/快照生成，来源变化产生新报告 |` 行后加注:
```text
（裁决 B2-1，2026-08-14：CoverageReport 仅指执行覆盖报告；"设计覆盖分析"为测试策划与设计的中间产物，不写入本实体。）
```

### 修改 5:04-核心领域模型.md CoverageReport 实体处(加注)

在 04 中 CoverageReport 实体定义处加注:
```text
> 裁决 B2-1（2026-08-14）：本实体为执行覆盖报告，唯一业务写入者为质量分析与缺陷；测试策划与设计的"设计覆盖分析"为中间产物，不映射本实体。
```

### 修改 6:32-API规范.yaml(可选,随质量模块开工补)

质量模块开工时补 `CoverageReport`/`CoverageReportCreate` schema 与 `/quality/coverage-reports` 端点(当前属 V1 延期项,不阻塞)。

---

## B2-2 · ContractCheckResult 完整承接(方案 A)

### 修改 1:14-PRD-QualityIntelligence.md §2 功能表(补契约检查行)

在"执行任务"行后追加:
```text
| 契约检查 | 按ExecutionContractBaseline记录APIObservation与ContractCheckResult（MATCH/DEVIATION/NOT_CHECKED/INCONCLUSIVE）；未检查不能计为通过（裁决 B2-2，2026-08-14） | 自动检查与偏差标注 | 偏差证据只追加；INCONCLUSIVE 不得报告为契约一致 |
```

### 修改 2:14-PRD-QualityIntelligence.md §6 验收标准(补 AC)

追加:
```text
### AC-05 契约偏差事实留存

- **Given** 执行完成且部分Operation未检查；
- **When** 生成执行结果；
- **Then** ContractCheckResult 含 MATCH/DEVIATION/NOT_CHECKED/INCONCLUSIVE 四态且未检查不计为通过，INCONCLUSIVE 不被报告为契约一致。
```

### 修改 3:15-PRD-SkillCenter.md §3 报告行(补披露字段)

在 `| TestReport | ...` 功能行或关键规则中追加:
```text
- TestReport 必须披露契约检查摘要（裁决 B2-2，2026-08-14）：采用的执行基线摘要、已检查 Operation 数、偏差数、未检查数与不可判定数。
```

### 修改 4:32-API规范.yaml(补 schema,可粘贴)

在 components.schemas 追加:
```yaml
    ContractCheckResult:
      type: object
      required: [id, executionResultId, checkStatus]
      properties:
        id: { type: string }
        executionResultId: { type: string }
        baselineDigest: { type: string }
        checkStatus:
          type: string
          enum: [MATCH, DEVIATION, NOT_CHECKED, INCONCLUSIVE]
        expectedRef: { type: string }
        actualRef: { type: string }
        severity: { type: string }
        reason: { type: string }
    APIObservation:
      type: object
      required: [id, executionResultId, operationVersionId]
      properties:
        id: { type: string }
        executionResultId: { type: string }
        operationVersionId: { type: string }
        statusCode: { type: integer }
        latencyMs: { type: integer }
        contentDigest: { type: string }
        environmentSnapshotId: { type: string }
```

---

## B2-3 · AI 校准记录结构化载体(方案 A)

### 修改 1:33-数据库Schema设计.md(追加建表段,可粘贴)

在 t_eval_* 段后追加:
```sql
-- 裁决 B2-3（2026-08-14）：AI 介入点校准记录（21 号 §4 / AC-03 判定底座）
CREATE TABLE t_calibration_record (
    id               TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    workspace_id     TEXT,
    intervention_key TEXT NOT NULL,              -- 21 号介入点 key（21 个）
    subject_version  TEXT NOT NULL,              -- 被评对象版本（Skill/模型/策略版本）
    dataset_version  TEXT NOT NULL,              -- 评测集版本
    metric_definition TEXT NOT NULL,             -- 指标定义（准确率/召回率/路由正确率/越权率…）
    threshold        REAL NOT NULL,              -- 生效阈值
    sample_size      INTEGER NOT NULL,           -- 样本量
    baseline         TEXT,                       -- 人工基线引用
    valid_from       TEXT NOT NULL,
    expires_at       TEXT NOT NULL,
    fallback_level   TEXT NOT NULL,              -- 跌破/过期后回退等级
    created_by       TEXT NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_calibration_key ON t_calibration_record(intervention_key, valid_from, expires_at);
```

### 修改 2:32-API规范.yaml(补注册/查询 API,可粘贴)

在 /ai/eval-runs 端点附近追加:
```yaml
  /ai/calibrations:
    post:
      summary: 注册 AI 介入点校准记录
      operationId: createCalibration
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/CalibrationRecordCreate' }
      responses:
        '200':
          description: 校准记录已注册
          content:
            application/json:
              schema: { $ref: '#/components/schemas/CalibrationRecord' }
    get:
      summary: 查询有效校准记录（按介入点）
      operationId: listCalibrations
      parameters:
        - name: interventionKey
          in: query
          schema: { type: string }
      responses:
        '200':
          description: 校准记录列表
          content:
            application/json:
              schema:
                type: array
                items: { $ref: '#/components/schemas/CalibrationRecord' }
```

```yaml
    CalibrationRecord:
      type: object
      required: [id, interventionKey, threshold, sampleSize, validFrom, expiresAt, fallbackLevel]
      properties:
        id: { type: string }
        interventionKey: { type: string }
        subjectVersion: { type: string }
        datasetVersion: { type: string }
        metricDefinition: { type: string }
        threshold: { type: number }
        sampleSize: { type: integer }
        baseline: { type: string }
        validFrom: { type: string, format: date-time }
        expiresAt: { type: string, format: date-time }
        fallbackLevel: { type: string }
    CalibrationRecordCreate:
      type: object
      required: [interventionKey, metricDefinition, threshold, sampleSize, validFrom, expiresAt, fallbackLevel]
      properties:
        interventionKey: { type: string }
        subjectVersion: { type: string }
        datasetVersion: { type: string }
        metricDefinition: { type: string }
        threshold: { type: number }
        sampleSize: { type: integer }
        baseline: { type: string }
        validFrom: { type: string, format: date-time }
        expiresAt: { type: string, format: date-time }
        fallbackLevel: { type: string }
```

### 修改 3:16-PRD-AgentCenter.md §2 Eval 行(补校准引用)

在 Eval 功能行补:
```text
校准记录：按 21 号 §4 落 t_calibration_record；无有效校准记录时分数只排序、不驱动自治（裁决 B2-3，2026-08-14）。
```

---

## B2-5/6/7 · 里程碑建表清单 / 补证顺序 / PG 冒烟门禁(方案 A)

### 新文档:V1 里程碑建表清单(交付时生成)

按 Stage5 M1~M5 产出"每里程碑需建表清单",主链优先(来源固化→策略/计划/用例→脚本→执行→结果→分析/报告→知识),每表标注:表名/所属模块/对应里程碑/是否 V1 必需。

### 记录:补证顺序与 PG 冒烟门禁

- 补证顺序(裁决 B2-6):M3 执行与证据 → M4 分析与报告;Defect 可在 M4 提前。
- PG 冒烟(裁决 B2-7):M1 或 M2 门禁增加"PG 冒烟"验收点:104 表迁移 + RLS 策略 + 核心链路并发写入;通过后方可进入 M3。
- 以上两条并入 V1 排期(Stage5 执行计划)。

---

## 应用与验证清单

| 步骤 | 动作 | 验证 |
|---|---|---|
| 1 | 应用 B2-1 修改 1-5 | `grep -c "裁决 B2-1" 12-PRD 15-PRD 05 04` = 各 ≥1;四源 CoverageReport 归属一致 |
| 2 | 应用 B2-2 修改 1-4 | `make contract` PASS;14-PRD 含 AC-05;32 含 ContractCheckResult schema |
| 3 | 应用 B2-3 修改 1-3 | `make contract` PASS;`grep -c t_calibration_record 33` = 2(建表+索引) |
| 4 | 生成里程碑建表清单 | 清单表名与 33 一致(grep 比对) |
| 5 | 更新 35-CHANGELOG | 追加"批次十二:2026-08-14 B2 裁决整改"条目 |
| 6 | 重跑 L1 一致性扫描 | 无新增冲突 |
