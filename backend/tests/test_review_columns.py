"""测试 GET /review/{record_id}/columns 端点"""
import pytest
import pytest_asyncio
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport
from app.main import create_app
from app.database import engine, async_session
from app.models.base import Base
from app.models.completion import CompletionRecord


@pytest_asyncio.fixture(autouse=True)
async def ensure_tables():
    """确保测试数据库中 completion_records 表存在"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seeded_records():
    """创建一条 table 记录和一条关联的 column 记录，返回 (table_id, column_id, table_entity_id)"""
    table_entity_id = "test_db.test_schema.test_table_for_columns"
    column_entity_id = f"{table_entity_id}.test_column"

    table_record = CompletionRecord(
        entity_id=table_entity_id,
        entity_type="table",
        target_data={"database": "test_db", "schema": "test_schema", "table_name": "test_table_for_columns"},
        review_status="pending_review",
    )
    column_record = CompletionRecord(
        entity_id=column_entity_id,
        entity_type="column",
        target_data={"column_name": "test_column"},
        completion_result={"display_name": "测试字段", "confidence": 0.85},
        review_status="pending_review",
    )

    async with async_session() as session:
        session.add_all([table_record, column_record])
        await session.commit()
        table_id = table_record.id
        column_id = column_record.id

    yield table_id, column_id, table_entity_id

    # 清理测试数据
    async with async_session() as session:
        result = await session.execute(
            select(CompletionRecord).where(
                CompletionRecord.id.in_([table_id, column_id])
            )
        )
        for r in result.scalars().all():
            await session.delete(r)
        await session.commit()


@pytest.mark.asyncio
async def test_columns_endpoint_not_found(client):
    """不存在的记录应返回 404"""
    resp = await client.get("/api/v1/review/nonexistent-id/columns")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_columns_endpoint_happy_path(client, seeded_records):
    """Happy path: table 记录有关联的 column 记录时返回该 column"""
    table_id, column_id, _table_entity_id = seeded_records
    resp = await client.get(f"/api/v1/review/{table_id}/columns")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]) >= 1
    column_ids = [c["id"] for c in data["data"]]
    assert column_id in column_ids


@pytest.mark.asyncio
async def test_columns_endpoint_non_table(client, seeded_records):
    """非 table 类型的记录应返回空列表"""
    _table_id, column_id, _table_entity_id = seeded_records
    resp = await client.get(f"/api/v1/review/{column_id}/columns")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"] == []
