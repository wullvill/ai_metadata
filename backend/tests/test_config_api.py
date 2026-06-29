"""Config API 集成测试"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import create_app
from app.services.config_service import config_service, ConfigService
from app.database import engine
from app.models.base import Base


@pytest_asyncio.fixture(autouse=True)
async def ensure_table():
    """Ensure pipeline_config table exists in test DB."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Clean up any leftover row from previous runs
    from app.models.config import PipelineConfig
    from app.database import async_session
    async with async_session() as session:
        result = await session.execute(__import__('sqlalchemy').select(PipelineConfig).where(PipelineConfig.id == 1))
        row = result.scalar_one_or_none()
        if row:
            await session.delete(row)
            await session.commit()


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
        ConfigService._cached = None
        response = await client.get("/api/v1/config/defaults")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["thresholds"]["auto_approve"] == 0.80

    @pytest.mark.asyncio
    async def test_get_config_returns_defaults_when_empty(self, client):
        ConfigService._cached = None
        response = await client.get("/api/v1/config")
        assert response.status_code == 200
        data = response.json()
        assert "thresholds" in data["data"]

    @pytest.mark.asyncio
    async def test_put_config_partial_update(self, client):
        ConfigService._cached = None
        partial = {"thresholds": {"auto_approve": 0.95}}
        response = await client.put("/api/v1/config", json=partial)
        assert response.status_code == 200
        assert response.json()["data"]["thresholds"]["auto_approve"] == 0.95
        assert response.json()["data"]["thresholds"]["pending_review"] == 0.60
