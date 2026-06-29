"""Pipeline 样本提权测试"""
from app.pipeline.stage1_retrieve import rrf_merge


class TestSamplesBoost:
    def test_samples_appear_in_top_results(self):
        """样本以 rank=0 插入后应出现在合并结果的靠前位置"""
        samples = [
            {"entity_id": "sample_a", "score": 0.5, "source": "sample"},
            {"entity_id": "sample_b", "score": 0.6, "source": "sample"},
        ]
        milvus_results = [{"entity_id": "x", "score": 0.9}]
        es_results = [{"entity_id": "y", "score": 0.8}]

        for i, s in enumerate(samples):
            milvus_results.insert(i, s)

        merged = rrf_merge(milvus_results, es_results, top_n=10)
        top_ids = [m["entity_id"] for m in merged]
        assert "sample_a" in top_ids[:3]
        assert "sample_b" in top_ids[:3]
