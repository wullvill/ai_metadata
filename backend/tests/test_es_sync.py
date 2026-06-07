"""测试 ES 回写函数"""
from unittest.mock import patch, MagicMock


class TestUpdateCompletedMetadata:
    def test_success(self):
        from app.services.elasticsearch import update_completed_metadata

        mock_es = MagicMock()

        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            result = update_completed_metadata(
                "db.schema.table",
                {"display_name": "用户表", "description": "存储用户信息", "tags": ["用户"]},
            )

        assert result is True
        mock_es.update.assert_called_once()
        call_args = mock_es.update.call_args
        assert call_args.kwargs["index"] == "metadata_index"
        assert call_args.kwargs["id"] == "db.schema.table"
        assert call_args.kwargs["doc"]["display_name"] == "用户表"
        assert call_args.kwargs["doc"]["description"] == "存储用户信息"
        assert call_args.kwargs["doc"]["tags"] == ["用户"]
        assert call_args.kwargs["doc"]["has_description"] is True

    def test_not_found(self):
        from app.services.elasticsearch import update_completed_metadata

        mock_es = MagicMock()
        from elasticsearch import NotFoundError
        mock_es.update.side_effect = NotFoundError(
            message="document missing",
            meta=MagicMock(),
            body={"_index": "metadata_index", "_id": "db.schema.missing"},
        )

        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            result = update_completed_metadata(
                "db.schema.missing",
                {"display_name": "X", "description": "Y", "tags": []},
            )

        assert result is False

    def test_empty_tags(self):
        from app.services.elasticsearch import update_completed_metadata

        mock_es = MagicMock()

        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            result = update_completed_metadata(
                "db.schema.empty",
                {"display_name": "空标签表", "description": "无标签", "tags": []},
            )

        assert result is True
        assert mock_es.update.call_args.kwargs["doc"]["tags"] == []


class TestUpdateCompletedColumns:
    def test_success(self):
        from app.services.elasticsearch import update_completed_columns

        with patch("app.services.elasticsearch.helpers.bulk") as mock_bulk:
            mock_bulk.return_value = (2, [])

            count = update_completed_columns(
                "db.schema.table",
                [
                    {"name": "col_a", "description": "字段A", "tags": ["核心"]},
                    {"name": "col_b", "description": "字段B", "tags": []},
                ],
            )

        assert count == 2

    def test_empty_columns(self):
        from app.services.elasticsearch import update_completed_columns

        with patch("app.services.elasticsearch.helpers.bulk") as mock_bulk:
            count = update_completed_columns("db.schema.table", [])

        assert count == 0
        mock_bulk.assert_not_called()

    def test_partial_failure(self):
        from app.services.elasticsearch import update_completed_columns

        with patch("app.services.elasticsearch.helpers.bulk") as mock_bulk:
            mock_bulk.return_value = (1, [{"update": {"error": "not found"}}])

            count = update_completed_columns(
                "db.schema.table",
                [
                    {"name": "col_a", "description": "A", "tags": []},
                    {"name": "col_b", "description": "B", "tags": []},
                ],
            )

        assert count == 1

    def test_bulk_actions_are_properly_formed(self):
        from app.services.elasticsearch import update_completed_columns

        with patch("app.services.elasticsearch.helpers.bulk") as mock_bulk:
            mock_bulk.return_value = (3, [])

            count = update_completed_columns(
                "table_x",
                [
                    {"name": "c1", "description": "desc1", "tags": ["t1"]},
                    {"name": "c2", "description": "desc2", "tags": ["t2", "t3"]},
                    {"name": "c3", "description": "desc3", "tags": []},
                ],
            )

        assert count == 3
        # helpers.bulk(es, actions, ...) is called — verify actions list
        call_args = mock_bulk.call_args
        actions = call_args[0][1]  # second positional arg
        assert len(actions) == 3

        assert actions[0]["_op_type"] == "update"
        assert actions[0]["_index"] == "metadata_columns"
        assert actions[0]["_id"] == "table_x.c1"
        assert actions[0]["doc"]["completion_description"] == "desc1"
        assert actions[0]["doc"]["completion_tags"] == ["t1"]

        assert actions[2]["_id"] == "table_x.c3"
        assert actions[2]["doc"]["completion_tags"] == []
