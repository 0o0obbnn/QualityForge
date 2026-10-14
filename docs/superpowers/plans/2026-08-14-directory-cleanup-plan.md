# QualityForge 根目录结构整理计划

> 状态：已批准的分析与建议稿（2026-08-14）。本文件仅为计划文档，不代表任何结构变更已执行。
> 实施入口见第 6 节分阶段步骤；每个阶段需独立确认后执行。

**勘察基线**：2026-08-14，git 追踪 980 个文件，工作区总体量约 550MB（其中 backend/.venv 145M、qa/ 截图 62M、.git 62M、.opencode/node_modules 61M 为体量大头）。本计划仅为分析与建议，不移动、修改、删除任何现有文件。

---

## 1. 当前目录结构问题清单（按严重度排序）

### A. 根目录指令文件泛滥（最影响检索）
- 根目录聚集 22 个 Agent 指令/人格类 .md：`AGENTS.md`、`AUTO_DESIGNER.md`、`SOUL.md`、`IDENTITY.md`、`DESIGN.md`、`INDEX.md`、`INTERACTIONS.md`、`OUTPUT_RULES.md`、`TASK_ROUTER.md`、`REDESIGN.md`、`CODE_INGESTION.md`、`PRD_INGESTION.md`、`IMAGE_GENERATION.md`、`UI-check.md`、`visual-asset-director.md`、`SELF_INTRO.md`、`HEARTBEAT.md`、`MEMORY.md`、`PRODUCT.md`、`TOOLS.md`、`USER.md`、`CLAUDE.md`，与真正的工程入口（`README.md`、`Makefile`）混杂。
- 其中 5 个新文件（`REDESIGN.md`、`CODE_INGESTION.md`、`IMAGE_GENERATION.md`、`UI-check.md`、`visual-asset-director.md`）处于"既未追踪、也未忽略"的悬挂状态，与 `.gitignore` 中同类文件的排除策略不一致。

### B. QA 快照多版本堆积（qa/ 62M，380 张 PNG）
- 三组版本链并存：`full_api_render` → v2 → v3（49/45/45 文件）、`pages_api` → v2 → v3（65/57/0，**v3 为空目录**）、`pages_prd` vs `pages_prd_v11`、`full_prd_render` vs `full_prd_v11_render`。
- 版本命名方案不统一（`_v2` 后缀 vs `_v11` 内容版本号 vs `full_`/`pages_` 前缀语义不明），无法判断哪份是当前基线。

### C. 交付物目录无索引、双格式重复（deliverables/ 9.7M）
- 按日期组织但无 `MANIFEST.md`/README，文件命名混用中文长名；`2026-08-13` 评审报告同时存在 `.docx` + `.html` 两份；`2026-08-10` 存在 PRD v1.0 与 v1.1 并存，未标注哪份为准。
- `2026-08-12/` 混装报告与完整原型工程（prototype/redesign/ui-audit 三个子目录），与根级 `prototypes/` 职责重叠。

### D. 工具状态目录污染代码区
- `prototypes/skills/` 内散落 8+ 个 `.remember/` 目录、`assertion-verifier-workspace/`、`hitl-gatekeeper-workspace/iteration-1/`、多处 `__pycache__/`，以及 `prototypes/.DS_Store`——均为工具运行残留，混在受追踪的 Skill 代码中。

### E. 语义混淆的空/近空目录
- `output/`（仅 1 张 playwright 截图）、`outputs/`（空）、`data/`（空）、`archive/`（空）四个目录职责重叠且无约定说明；`config/` 仅含 `mcporter.json` 一个文件。

### F. 隐藏工具目录缺乏登记
- 14 个隐藏目录（`.cluster`、`.omo`、`.omx`、`.openclaw`、`.opencode`、`.playwright-cli`、`.qoder`、`.remember`、`.serena`、`.workbuddy`、`.zcode`、`.agents`、`.claude`、`.trae`、`.obsidian` + `.codegraph` 符号链接）已在 `.gitignore` 分组忽略，但没有任何一处文档说明各自归属哪个工具、是否可清理。`.opencode/node_modules` 独占 61M。

### G. 记忆/日志双轨
- 根级 `memory/`（AGENTS.md 引用的每日笔记）与 `.remember/`（另一工具的 today-*.md 日志）职责重复；`.serena/memories`、`.workbuddy/memory` 又是两套独立记忆。

### H. 审计证据位置错放
- `eval-evidence-ai.md`、`eval-evidence-audit.md` 位于根目录，但其自述用途是支撑 `docs/05-audits/current/产品评估报告.md`，应归入审计目录。

### I. 文档体系局部破例
- `docs/superpowers/plans/` 游离于编号体系外（可接受，属过程计划）；`.trae/documents/QualityForge-UIUX-Design-Plan.md` 与 `docs/06-wireframes/QualityForge-UIUX-Design-Plan.md` 同名，疑似重复副本。

### J. 临时文件残留
- `_tmp_generate_pages.py`（44K，已被 `_tmp_*` 规则忽略但常驻根目录）。

### K. 外部参考库占据根目录
- `审美相关skill/`（11M，外部 skill 库）、`design-assets-index/`、`infinite-canvas-output/` 均为非项目代码的外部资源，与项目目录平级。

### L. 原型双副本职责不明
- `prototypes/e2e-validation/` 与 `e2e-validation-golden/` 内容高度同构但逐文件不同（golden 为基线、前者含运行产物如 `blind_spot_report.json`），无 README 说明二者关系。

### M. git 工作区未提交变更积累
- 17 个文档修改 + 8 个未追踪文件待处理（含 `deliverables/2026-08-14/`、`backend/src/qf/log.py`），整理前需先收口。

---

## 2. 目标目录结构与职责边界

```
QualityForge/
├── README.md                  # 项目概述 + 顶层导航地图（新增"目录速查表"章节）
├── AGENTS.md                  # 唯一保留在根目录的 Agent 入口（引用路径需同步更新）
├── Makefile / .env.example / setup_skills.py   # 工程入口，不动
│
├── agent-rules/               # 【新建】20 个设计流指令文件集中收纳
│   └── (SOUL/DESIGN/INDEX/.../UI-check/visual-asset-director 等)
│
├── docs/                      # 核心文档，编号体系不动
│   ├── 05-audits/current/     # + 接收根级 eval-evidence-*.md（更名加日期前缀）
│   └── ...
├── deliverables/              # 阶段交付物，YYYY-MM-DD/ + 每日 MANIFEST.md
├── prototypes/                # 原型与 Skill 注册中心（清理工具残留后保持现状）
├── qa/                        # 仅保留各组最新版本；旧版进 qa/archive/（tar.gz）
├── backend/ frontend/ tools/  # 代码工程，结构不动
├── memory/                    # 运行时每日笔记（保持 gitignore）
├── wall/                      # 多 Agent 协作墙（保持现状，是否入 git 见待确认项）
├── archive/                   # 【激活】根级过期产物归档区，按年-月子目录
├── references/                # 【新建】外部参考资源：审美相关skill、
│                              #   design-assets-index、infinite-canvas-output
└── .toolstate/                # 【不强制】隐藏目录维持现状，仅在文档登记
```

职责边界要点：
- `agent-rules/`：只放 Agent 工作流指令，不放项目文档；`AGENTS.md` 留根目录作为唯一调度入口。
- `qa/`：只存"当前有效基线快照"；历史版本压缩归档到 `qa/archive/`，不再以 `_v2` 平铺目录形式存在。
- `deliverables/`：只放面向人的交付成品；原型工程类内容若需长期演进应迁 `prototypes/`。
- `references/`：只放第三方/外部技能与素材库，全部 gitignore。
- `archive/`：只进不出，按 `archive/YYYY-MM/` 组织，附一行说明文件。

## 3. 文件迁移 / 归档 / 保留 / 压缩 / 待删除建议

| 动作 | 对象 | 说明 |
|---|---|---|
| 迁移 | 20 个指令 .md → `agent-rules/` | 必须同步更新 `AGENTS.md` 等文件中的引用路径 |
| 迁移 | `eval-evidence-ai.md`、`eval-evidence-audit.md` → `docs/05-audits/current/` | 更名加日期前缀，如 `2026-08-07-eval-evidence-ai.md` |
| 迁移 | `审美相关skill/`、`design-assets-index/`、`infinite-canvas-output/` → `references/` | 同步更新 `.gitignore` 与 `AGENTS.md` 相对路径引用 |
| 压缩归档 | `qa/` 的 `full_api_render`、`full_api_render_v2`、`pages_api`、`pages_api_v2`、`pages_prd`、`full_prd_render` | 各组仅保留最新一版，旧版 tar.gz 至 `qa/archive/`（预计释放约 35M 平铺体积并保持可恢复） |
| 归档 | `docs/06-wireframes/legacy/` 已在 legacy，无需动；`deliverables/2026-08-10/` PRD v1.0 | 标注 v1.1 为准，v1.0 移入 `deliverables/2026-08-10/superseded/` |
| 保留不动 | `backend/`、`frontend/`、`tools/`、`docs/` 编号体系、`prototypes/skills` 30 个 Skill、`.git*`、`Makefile` | 核心工程资产 |
| 保留+登记 | 全部 14 个隐藏工具目录 | 不移动，写入 `docs/00-navigation/` 的工具状态登记表 |
| 待删除（P3 阶段、trash 方式） | `qa/pages_api_v3/`（空）、`outputs/`、`data/`、`output/`（先迁其中 1 张截图） | 均为空或语义重复目录 |
| 待删除 | `prototypes/skills/**/.remember/`、`*-workspace/`、`__pycache__/`、各级 `.DS_Store` | 工具运行残留；删除前先确认 workspace 内无未归档的迭代产物 |
| 待删除 | `_tmp_generate_pages.py` | 确认 qa 生成流程已由 `tools/` 脚本替代后再删 |
| 可清理（重装可恢复） | `.opencode/node_modules`（61M）、根级与 backend 的 `.mypy_cache`（合计 54M） | 纯缓存，`make clean` 已覆盖部分 |

## 4. 命名规范与交付物组织规则

- **日期格式**：统一 `YYYY-MM-DD`（目录与文件名一致）；过程计划沿用 `docs/superpowers/plans/YYYY-MM-DD-主题.md`。
- **交付物**：`deliverables/YYYY-MM-DD/QualityForge-<主题>-<类型>.<ext>`，同日多交付必须附 `MANIFEST.md`（列出文件、用途、状态、取代关系）；同一报告避免 docx+html 双格式，以 html 为准、docx 按需生成。
- **QA 快照**：命名 `qa/<对象>-<内容版本>/`，废弃 `_v2` 增量后缀；被取代版本一律压缩进 `qa/archive/`，压缩包命名 `<目录名>-<生成日期>.tar.gz`。
- **审计文档**：`docs/05-audits/current/` 文件加日期前缀；保持"current/historical 不改写历史结论"的既有约定。
- **版本化**：文档正式版沿用"稳定根 + 不可变版本"；被取代版本进 `superseded/` 子目录而非删除。
- **通用**：禁用 `_tmp_` 前缀文件进入 git；禁止 `.DS_Store` 入库（已在 ignore，需清理存量）。

## 5. 检索效率提升：索引与导航

- `README.md` 增补"目录速查表"：每个顶层目录一行（职责 + 何时来这里找）。
- `docs/00-navigation/54-项目需求资料总索引.md` 扩展：补充交付物、QA 基线、原型、审计证据四个区块的链接。
- 新增 `docs/00-navigation/工具状态目录登记.md`：14 个隐藏目录逐一登记（归属工具、内容性质、可否清理、重建方式）。
- `deliverables/MANIFEST.md`（根级）：按日期倒序汇总各批次交付物与一句话摘要。
- `qa/README.md`：声明当前基线快照组 + archive 内容清单。
- `agent-rules/README.md`：指令文件清单 + 调度关系图（由 AGENTS.md 触发的读取顺序）。

## 6. 分阶段实施步骤

**P0 · git 收口（无结构变动，最先做）**
提交或裁决当前 17 处修改 + 8 个未追踪文件；为 5 个悬挂指令文件做出"追踪或忽略"的决定并更新 `.gitignore`。验收：`git status` 干净；回滚：常规 git 操作。

**P1 · 根目录减负**
指令文件迁 `agent-rules/` 并全量更新引用路径（改后跑一次 `AGENTS.md` 引用路径核对）；`eval-evidence-*` 入审计目录；外部库入 `references/`。风险：引用断链——每迁一个文件即 grep 全库引用；回滚：`git mv` 逆操作 + 引用还原。验收：根目录可见 .md ≤ 4 个；grep 无失效引用。

**P2 · qa 与 deliverables 归序**
qa 各组确认最新版后压缩旧版；deliverables 各日期目录补 MANIFEST、superseded 分离。风险：误压当前基线——压缩前逐组核对文件数与日期；回滚：tar 解压即还原。验收：qa/ 顶层目录 ≤ 7 个；每个交付日期目录有 MANIFEST。

**P3 · 清理残留（先 trash 后确认）**
删除空目录、`.remember`/`__pycache__`/`.DS_Store` 残留、确认后的 `_tmp_generate_pages.py`；清理缓存（.mypy_cache、.opencode/node_modules）。风险：workspace 目录可能含未归档产物——删除前列内容清单供确认；回滚：trash 可恢复。验收：`find . -name .remember -not -path './.remember/*'` 为空。

**P4 · 导航建设**
落地第 5 节的 6 个索引/README 文件。验收：从 README 出发 2 次点击内可定位任一顶层区块。

**全局风险控制**：所有移动用 `git mv`（受追踪文件）保留历史；删除一律 `trash` 不用 `rm`；每个阶段独立提交、独立可回滚；涉及 AGENTS.md 引用路径的变更在低活跃时段执行并全量回归引用。

## 待确认项（不擅自决定）

1. `AGENTS.md` 引用的指令文件是否允许迁入 `agent-rules/`（涉及桌面端 AutoClaw 对固定路径的依赖，需用户确认工具侧是否按相对路径读取）。
2. `wall/` 当前被 gitignore，但含多 Agent 裁决记录（VERDICT.md 等），是否转为版本化资产？
3. `memory/` 与 `.remember/` 双轨日志：是否保留 `.remember/`（属外部工具自管，可能不宜触碰）？
4. `qa/` 旧版快照压缩后是否仍有随时展开的需求（影响是否保留 tar 而非移出库外）。
5. `deliverables/2026-08-12/prototype/`（34 页完整原型）是留交付物目录还是迁 `prototypes/` 长期演进。
6. `.trae/documents/` 与 `docs/06-wireframes/` 的同名 UIUX 设计计划，哪份是权威副本。
7. `prototypes/e2e-validation/` 中的运行产物（blind_spot_report 等）是否为一次性产物可清理，golden 是否为唯一基线。
