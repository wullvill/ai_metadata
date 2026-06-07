"""Stage 2 LLM 生成测试"""
import pytest
from app.pipeline.stage2_generate import parse_llm_json, select_model


class TestParseLLMJson:
    def test_parse_direct_json(self):
        raw = '{"display_name": "订单表", "description": "记录订单信息", "tags": ["交易"], "confidence": 0.9}'
        result = parse_llm_json(raw)
        assert result["display_name"] == "订单表"
        assert result["confidence"] == 0.9

    def test_parse_json_in_code_block(self):
        raw = '```json\n{"display_name": "用户表", "description": "用户信息", "confidence": 0.85}\n```'
        result = parse_llm_json(raw)
        assert result["display_name"] == "用户表"

    def test_parse_raw_curly_braces(self):
        raw = '一些前缀文本 {"display_name": "支付单", "description": "支付记录", "confidence": 0.8} 一些后缀'
        result = parse_llm_json(raw)
        assert result["display_name"] == "支付单"

    def test_parse_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_llm_json("这不是 JSON")


class TestSelectModel:
    def test_column_defaults_to_qwen_plus(self):
        model = select_model("column", [], [])
        assert model == "qwen3.7-plus"

    def test_table_with_rich_siblings_uses_qwen_max(self):
        siblings = [{"description": "description_" + str(i)} for i in range(6)]
        model = select_model("table", siblings, [])
        assert model == "qwen-max"

    def test_table_sparse_siblings_uses_default(self):
        siblings = [{"description": ""} for _ in range(6)]
        model = select_model("table", siblings, [])
        assert model == "qwen3.7-plus"


class TestBuildTablePrompt:
    def test_builds_prompt_with_context(self):
        from app.pipeline.stage2_generate import _build_table_prompt
        from app.pipeline.state import CompletionState

        target = {
            "database": "mysql", "schema": "order_db",
            "table_name": "t_order",
            "current_description": None,
            "current_display_name": None,
            "columns": [{"name": "id", "dataType": "bigint"}, {"name": "status", "dataType": "varchar"}],
            "entity_id": "mysql.order_db.t_order",
        }
        state: CompletionState = {
            "target_entity": target,
            "retrieved_context": [
                {"search_text": "order_db.t_payment | 支付单", "score": 0.089}
            ],
            "schema_context": [
                {"table_name": "t_payment", "description": "支付流水表"}
            ],
            "sibling_columns": None,
            "completion_result": None,
            "quality_check": None,
            "review_status": None,
            "error": None,
        }
        prompt = _build_table_prompt(target, state)
        assert "mysql" in prompt
        assert "t_order" in prompt
        assert "t_payment" in prompt
        assert "支付流水表" in prompt
        assert 'id(bigint)' in prompt
        assert 'status(varchar)' in prompt

    def test_columns_truncated_at_20(self):
        from app.pipeline.stage2_generate import _build_table_prompt
        from app.pipeline.state import CompletionState

        target = {
            "database": "db", "schema": "s",
            "table_name": "t",
            "current_description": None,
            "current_display_name": None,
            "columns": [{"name": f"col{i}", "dataType": "int"} for i in range(25)],
            "entity_id": "db.s.t",
        }
        state: CompletionState = {
            "target_entity": target,
            "retrieved_context": None,
            "schema_context": None,
            "sibling_columns": None,
            "completion_result": None,
            "quality_check": None,
            "review_status": None,
            "error": None,
        }
        prompt = _build_table_prompt(target, state)
        # col19 should be present (index 19 is the 20th column)
        assert "col19" in prompt
        # col20 should NOT be present (index 20 is the 21st column, truncated)
        assert "col20" not in prompt


class TestBuildColumnPrompt:
    def test_builds_prompt_with_siblings(self):
        from app.pipeline.stage2_generate import _build_column_prompt
        from app.pipeline.state import CompletionState

        target = {
            "database": "mysql", "schema": "user_db",
            "table_name": "t_user", "column_name": "id_card",
            "data_type": "varchar",
            "table_description": "用户信息表",
            "current_description": None,
            "current_display_name": None,
            "entity_id": "mysql.user_db.t_user.id_card",
        }
        state: CompletionState = {
            "target_entity": target,
            "retrieved_context": [
                {"search_text": "user_db.t_user.id_number | 身份证号", "score": 0.092}
            ],
            "schema_context": None,
            "sibling_columns": [
                {"column_name": "user_name", "data_type": "varchar", "description": "用户姓名"},
                {"column_name": "phone", "data_type": "varchar", "description": "手机号"},
            ],
            "completion_result": None,
            "quality_check": None,
            "review_status": None,
            "error": None,
        }
        prompt = _build_column_prompt(target, state)
        assert "mysql.user_db.t_user" in prompt
        assert "id_card" in prompt
        assert "varchar" in prompt
        assert "用户信息表" in prompt
        assert "user_name" in prompt
        assert "用户姓名" in prompt
        assert "phone" in prompt


class TestFormatContextList:
    def test_formats_with_scores(self):
        from app.pipeline.stage2_generate import _format_context_list

        ctx = [
            {"search_text": "t_order | 订单表", "score": 0.089},
            {"search_text": "t_payment | 支付单", "score": 0.045},
        ]
        text = _format_context_list(ctx)
        assert "1." in text
        assert "0.089" in text
        assert "2." in text
        assert "0.045" in text
        assert "t_order" in text
        assert "t_payment" in text

    def test_returns_placeholder_when_empty(self):
        from app.pipeline.stage2_generate import _format_context_list

        text = _format_context_list([])
        assert "无参考数据" in text
