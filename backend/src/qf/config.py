"""应用配置 — 从环境变量读取。

对应 .env.example 的变量定义。
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Stage 4本地运行时使用Python内置SQLite，不要求安装数据库服务。
    sqlite_path: Path = Path("data/qualityforge.sqlite3")
    frontend_dist: Path = Path("../frontend/dist")

    # 应用
    app_env: str = "development"
    jwt_issuer: str = "qualityforge-local"
    jwt_audience: str = "qualityforge-web"
    jwt_ttl_seconds: int = 28_800

    # M1-P1：生成链 Provider 加固（超时阈值，毫秒；超时后计入失败重试）
    generation_timeout_ms: int = 5000


settings = Settings()
