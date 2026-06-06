"""Config API 集成测试"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import create_app
from app.services.config_service import config_service


@pytest.fixture(autouse=True)
def reset_config():
    config_service.reset()
    yield
    config_service.reset()


@pytest_asyncio.fixture
async def client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestConfigAPI:
    @pytest.mark.asyncio
    async def test_get_defaults_returns_config(self, client):
        config_service._cached = None
        response = await client.get("/api/v1/config/defaults")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["thresholds"]["auto_approve"] == 0.80

    @pytest.mark.asyncio
    async def test_get_config_returns_defaults_when_empty(self, client):
        config_service._cached = None
        response = await client.get("/api/v1/config")
        assert response.status_code == 200
        data = response.json()
        assert "thresholds" in data["data"]

    @pytest.mark.asyncio
    async def test_put_config_partial_update(self, client):
        config_service._cached = None
        partial = {"thresholds": {"auto_approve": 0.95}}
        response = await client.put("/api/v1/config", json=partial)
        assert response.status_code == 200
        assert response.json()["data"]["thresholds"]["auto_approve"] == 0.95
        assert response.json()["data"]["thresholds"]["pending_review"] == 0.60
