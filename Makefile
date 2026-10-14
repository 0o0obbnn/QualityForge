.PHONY: help install migrate dev test test-frontend test-skills contract lint format frontend clean eval eval-baseline

help: ## 显示所有可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装后端和前端依赖
	cd backend && uv sync
	cd frontend && npm install

migrate: ## 创建或升级本地SQLite文件
	cd backend && uv run python -m qf.db

frontend: ## 类型检查并构建审核工作台
	cd frontend && npm run build

test-frontend: ## 运行前端 vitest 组件测试
	cd frontend && npm run test

dev: frontend ## 启动本地一体化工作台（无需数据库服务或模型）
	cd backend && uv run uvicorn qf.main:app --reload --host 127.0.0.1 --port 8000

test: ## 运行后端测试、前端测试、Skill契约测试、Skill eval、Provider黄金集闸门和Agent治理校验
	cd backend && uv run pytest -v
	cd frontend && npm run test
	python3 -m unittest discover -s prototypes/skills/tests -p 'test_*.py' -v
	cd backend && uv run python ../prototypes/skills/run_all_evals.py
	cd backend && uv run python ../prototypes/skills/run_provider_eval.py
	cd backend && uv run python ../prototypes/agent-governance/validate.py

test-skills: ## Gate 0 Skill 契约回归 + 两条 E2E 链终态断言（127 个真实断言，不 mock）
	python3 -m unittest discover -s prototypes/skills/tests -p 'test_*.py' -v

contract: ## 使用官方validator验证OpenAPI
	cd backend && uv run openapi-spec-validator ../docs/04-architecture/32-API规范.yaml

eval: ## 评估闸门：Skill evals + Provider 黄金集闸门与基线核验（零 LLM-judge）
	cd backend && uv run python ../prototypes/skills/run_all_evals.py
	cd backend && uv run python ../prototypes/skills/run_provider_eval.py

eval-baseline: ## 归档 deterministic-local 黄金集基线（锚点/黄金集变更后重新归档）
	cd backend && uv run python ../prototypes/skills/run_provider_eval.py --write-baseline

lint: ## 代码检查（ruff + mypy）
	cd backend && uv run ruff check src tests && uv run mypy src

format: ## 格式化后端代码
	cd backend && uv run ruff format src tests && uv run ruff check --fix src tests

clean: ## 清理可重建缓存和前端构建产物（保留SQLite业务数据）
	find backend -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null; true
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache frontend/dist
