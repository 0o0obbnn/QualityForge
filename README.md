# QualityForge

AI 原生端到端测试平台。当前已完成 Stage 4 本地纵向切片：Agent 以确定性 Provider 准备测试策略、测试计划和测试用例，测试人员在浏览器中核对精确版本、摘要和轨迹后批准或退回。

## 当前可运行能力

- Python 3.12 + FastAPI 后端；React + TypeScript + Vite + Fluent UI 前端。
- Python 内置 SQLite 持久化，不安装 PostgreSQL、Redis 或 Docker。
- 本地账号、短时 JWT、HttpOnly Cookie、CSRF 校验、能力校验和租户/Workspace 应用层隔离。
- `deterministic-local` Provider 离线生成固定结构产出，不读取或调用真实模型。
- 需求版本 → WorkItem → AgentSession → TestStrategy → TestPlan → TestCase → ReviewTask → 人工批准闭环。

SQLite 是本地单用户验证方案，不等于目标 PostgreSQL 的原生 RLS、并发和生产可用性。目标架构仍保留在设计文档中，待团队化部署阶段验证。

## 快速启动

```bash
make install
make migrate
make dev
```

浏览器访问 <http://127.0.0.1:8000>，首次打开时创建本地管理员。数据库默认保存在 `backend/data/qualityforge.sqlite3`；服务重启后数据保留，但出于本地安全默认需重新登录。

```bash
make test       # 后端测试、Skill eval、Agent治理校验
make contract   # OpenAPI官方校验
make lint       # Ruff + Mypy
make frontend   # 前端类型检查与生产构建
```

## 项目结构

```text
QualityForge/
├── backend/          # FastAPI、SQLite、JWT、确定性Provider
├── frontend/         # 审核工作台
├── docs/             # 产品、PRD、治理、架构与审计资料
├── prototypes/       # 30个Skill原型与Gate 0 Agent治理
└── output/playwright # 浏览器E2E截图证据
```

权威导航见[项目需求资料总索引](docs/00-navigation/54-项目需求资料总索引.md)，机器可读接口契约见[API规范](docs/04-architecture/32-API规范.yaml)。
