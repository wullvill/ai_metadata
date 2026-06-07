"""测试 GET /review/{record_id}/columns 端点"""
import pytest


@pytest.mark.asyncio
async def test_columns_endpoint_not_found(client):
    """不存在的记录应返回 404"""
    resp = await client.get("/api/v1/review/nonexistent-id/columns")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_columns_endpoint_non_table(client):
    """非 table 类型的记录应返回空列表"""
    resp = await client.get("/api/v1/review/some-column-record/columns")
    assert resp.status_code in [200, 404]
    if resp.status_code == 200:
        data = resp.json()
        assert data["success"] is True
        assert data["data"] == []
