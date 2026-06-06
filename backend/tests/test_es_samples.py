"""ES sample flag 测试"""
from unittest.mock import patch, MagicMock


class TestSetSampleFlag:
    def test_set_sample_flag_calls_update_by_query_with_correct_params(self):
        from app.services.elasticsearch import set_sample_flag

        mock_es = MagicMock()
        mock_es.update_by_query.return_value = {"updated": 3}

        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            result = set_sample_flag(["a", "b", "c"], True)

        assert result == 3
        call_args = mock_es.update_by_query.call_args
        assert call_args.kwargs["index"] == "metadata_index"
        body = call_args.kwargs["body"]
        assert body["query"]["terms"] == {"entity_id": ["a", "b", "c"]}
        assert "ctx._source.is_sample = true" in body["script"]["source"]

    def test_set_sample_flag_unset(self):
        from app.services.elasticsearch import set_sample_flag

        mock_es = MagicMock()
        mock_es.update_by_query.return_value = {"updated": 2}

        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            result = set_sample_flag(["x", "y"], False)

        assert result == 2
        body = mock_es.update_by_query.call_args.kwargs["body"]
        assert "ctx._source.is_sample = false" in body["script"]["source"]

    def test_set_sample_flag_empty_list_returns_zero(self):
        from app.services.elasticsearch import set_sample_flag

        with patch("app.services.elasticsearch.get_es_client") as mock_client:
            result = set_sample_flag([], True)

        assert result == 0
        mock_client.assert_not_called()
