"""元数据检索模块测试 — TDD RED phase"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.elasticsearch import (
    search_all, search_keyword, search_siblings,
)


class TestESSearchAll:
    def test_returns_list_of_dicts(self):
        mock_es = MagicMock()
        mock_es.search.return_value = {
            "hits": {"hits": [
                {"_source": {"entity_id": "t1", "entity_type": "table", "database": "ods_trade", "table_name": "fact_trade"}}
            ]}
        }
        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            results = search_all("交易")
        assert isinstance(results, list)
        assert len(results) > 0
        assert "entity_id" in results[0]

    def test_applies_entity_type_filter(self):
        mock_es = MagicMock()
        mock_es.search.return_value = {"hits": {"hits": []}}
        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            search_all("交易", entity_type="table")
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        assert any(c.get("term", {}).get("entity_type") == "table" for c in must)

    def test_applies_database_filter(self):
        mock_es = MagicMock()
        mock_es.search.return_value = {"hits": {"hits": []}}
        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            search_all("交易", database="ods_trade")
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        assert any(c.get("term", {}).get("database") == "ods_trade" for c in must)

    def test_no_filters_has_empty_must(self):
        mock_es = MagicMock()
        mock_es.search.return_value = {"hits": {"hits": []}}
        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            search_all("交易")
        assert mock_es.search.call_args[1]["body"]["query"]["bool"]["must"] == []

    def test_includes_highlight(self):
        mock_es = MagicMock()
        mock_es.search.return_value = {
            "hits": {"hits": [
                {"_source": {"entity_id": "t1", "table_name": "fact_trade"},
                 "highlight": {"table_name": ["<mark>fact</mark>"]}}
            ]}
        }
        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            results = search_all("fact")
        assert "highlight" in results[0]
        assert results[0]["highlight"]["table_name"] == ["<mark>fact</mark>"]


class TestESSearchKeyword:
    def test_keyword_returns_score(self):
        mock_es = MagicMock()
        mock_es.search.return_value = {
            "hits": {"hits": [
                {"_score": 2.5, "_source": {"entity_id": "d1", "entity_type": "table", "table_name": "dim_account", "description": "x"}}
            ]}
        }
        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            results = search_keyword("账户", entity_type="table")
        assert len(results) > 0
        assert results[0]["score"] == 2.5
        assert results[0]["source"] == "es"


class TestESSiblings:
    def test_siblings_sends_db_schema_type(self):
        mock_es = MagicMock()
        mock_es.search.return_value = {"hits": {"hits": []}}
        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            search_siblings("ods_trade", "public", "table", top_k=3)
        body = mock_es.search.call_args[1]["body"]
        terms = [c["term"] for c in body["query"]["bool"]["must"]]
        assert {"database": "ods_trade"} in terms
        assert {"schema_name": "public"} in terms
        assert {"entity_type": "table"} in terms


@pytest.mark.asyncio
class TestSearchAPI:
    async def test_search_endpoint_returns_200(self, client):
        with patch("app.api.search.search_all", return_value=[]):
            resp = await client.post("/api/v1/search", json={"query": "交易"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "data" in data

    async def test_search_handles_pagination(self, client):
        fake_results = [{"entity_id": f"e{i}", "entity_type": "table"} for i in range(30)]
        with patch("app.api.search.search_all", return_value=fake_results):
            resp = await client.post("/api/v1/search", json={"query": "x", "page": 2, "page_size": 10})
        data = resp.json()
        assert data["meta"]["page"] == 2
        assert len(data["data"]) == 10

    async def test_search_no_results(self, client):
        with patch("app.api.search.search_all", return_value=[]):
            resp = await client.post("/api/v1/search", json={"query": "nonexistent"})
        data = resp.json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["meta"]["total"] == 0
