"""Pipeline 样本提权测试"""
from app.pipeline.stage1_retrieve import rrf_merge


class TestSamplesBoost:
    def test_samples_placed_at_top_of_merged_results(self):
        """样本 rank=0 应排在非样本前面"""
        samples = [
            {"entity_id": "sample_a", "score": 0.5, "source": "es"},
            {"entity_id": "sample_b", "score": 0.6, "source": "milvus"},
        ]
        milvus_results = [{"entity_id": "x", "score": 0.9}]
        es_results = [{"entity_id": "x", "score": 0.8}]

        for i, s in enumerate(samples):
            milvus_results.insert(i, s)

        merged = rrf_merge(milvus_results, es_results, top_n=10)
        top_ids = [m["entity_id"] for m in merged[:2]]
        assert top_ids == ["sample_a", "sample_b"]
