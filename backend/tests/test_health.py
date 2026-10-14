"""健康检查冒烟测试。"""


async def test_health(client) -> None:
    """GET /health 返回 200 + status=ok。"""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["runtime"] == "stage4-local-sqlite"
