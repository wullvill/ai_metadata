"""Stage 1 双路检索测试"""
import pytest
from app.pipeline.stage1_retrieve import rrf_merge, build_retrieval_text


class TestRRFMerge:
    def test_merge_deduplicates_same_entity(self):
        milvus = [{"entity_id": "t_order", "score": 0.9, "source": "milvus"}]
        es = [{"entity_id": "t_order", "score": 0.8, "source": "es"}]
        result = rrf_merge(milvus, es)
        assert len(result) == 1
        assert result[0]["source"] == "both"

    def test_merge_sorts_by_fusion_score(self):
        milvus = [
            {"entity_id": "a", "score": 0.9},
            {"entity_id": "b", "score": 0.7},
        ]
        es = [
            {"entity_id": "c", "score": 0.8},
            {"entity_id": "a", "score": 0.5},
        ]
        result = rrf_merge(milvus, es)
        # "a" appears in both paths -> highest fusion score
        assert result[0]["entity_id"] == "a"

    def test_merge_returns_top_n(self):
        items = [{"entity_id": f"e{i}", "score": 1.0} for i in range(30)]
        result = rrf_merge(items, [], top_n=15)
        assert len(result) == 15


class TestBuildRetrievalText:
    def test_table_search_text(self):
        target = {
            "database": "mysql", "schema": "order_db",
            "table_name": "t_order", "entity_type": "table",
        }
        text = build_retrieval_text(target)
        assert "mysql.order_db.t_order" in text

    def test_column_search_text(self):
        target = {
            "database": "mysql", "schema": "user_db",
            "table_name": "t_user", "column_name": "id_card",
            "data_type": "varchar", "entity_type": "column",
        }
        text = build_retrieval_text(target)
        assert "mysql.user_db.t_user.id_card" in text
        assert "varchar" in text
