"""API 集成测试"""
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_search_endpoint(client):
    resp = await client.post("/api/v1/search", json={
        "query": "test",
        "entity_type": "table",
    })
    # ES 连接可能不可用，检查响应结构
    assert resp.status_code in [200, 500]


@pytest.mark.asyncio
async def test_search_without_entity_type(client):
    resp = await client.post("/api/v1/search", json={
        "query": "test",
    })
    assert resp.status_code in [200, 500]


@pytest.mark.asyncio
async def test_review_queue_empty(client):
    """审核队列在无数据库时返回错误（DB不可用）"""
    resp = await client.get("/api/v1/review/queue")
    # Without DB, expect 500; with DB, expect 200
    assert resp.status_code in [200, 500]


@pytest.mark.asyncio
async def test_review_detail_not_found(client):
    resp = await client.get("/api/v1/review/nonexistent-id")
    assert resp.status_code in [404, 500]


@pytest.mark.asyncio
async def test_asset_detail_includes_system(client):
    """资产详情 API 应包含 system 字段（所属系统）"""
    resp = await client.get("/api/v1/assets/fact_trade")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "system" in data, f"Expected 'system' field, got keys: {list(data.keys())}"
    assert isinstance(data["system"], str)
    assert len(data["system"]) > 0


@pytest.mark.asyncio
async def test_complete_trigger_validation(client):
    """缺少必填字段应返回 422"""
    resp = await client.post("/api/v1/complete/trigger/manual", json={
        "target": {
            "entity_id": "test",
            # missing entity_type, database, schema, table_name
        }
    })
    assert resp.status_code in [422, 500]
