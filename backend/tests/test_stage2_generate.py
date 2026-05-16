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
        assert model == "qwen-plus"

    def test_table_with_rich_siblings_uses_qwen_max(self):
        siblings = [{"description": "description_" + str(i)} for i in range(6)]
        model = select_model("table", siblings, [])
        assert model == "qwen-max"

    def test_table_sparse_siblings_uses_default(self):
        siblings = [{"description": ""} for _ in range(6)]
        model = select_model("table", siblings, [])
        assert model == "qwen-plus"
