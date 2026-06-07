"""测试 fixtures — 强制测试使用 SQLite 避免动到生产 PostgreSQL"""
import os

# 必须在任何 app 模块 import 之前设置，因为 get_settings() 在模块加载时执行
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test.db"

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import create_app


@pytest_asyncio.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
