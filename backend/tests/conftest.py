"""Isolated SQLite and HTTP fixtures for the Stage 4 local runtime."""

from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from qf.main import app
from qf.services.auth_service import auth_service
from qf.services.planning_workflow import planning_workflow_service


@pytest.fixture(autouse=True)
def sqlite_path(tmp_path: Path) -> Generator[Path, None, None]:
    path = tmp_path / "qualityforge-test.sqlite3"
    planning_workflow_service.reconfigure(str(path))
    auth_service.reconfigure(str(path))
    planning_workflow_service.reset()
    auth_service.reset_for_tests()
    yield path


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as api_client:
        yield api_client
