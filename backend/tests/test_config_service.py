import pytest
from app.services.config_service import ConfigService, DEFAULTS


class TestConfigService:
    def test_defaults_returns_four_sections(self):
        svc = ConfigService()
        config = svc.get_defaults()
        assert "thresholds" in config
        assert "models" in config
        assert "retrieval" in config
        assert "rules" in config

    def test_defaults_match_hardcoded_values(self):
        svc = ConfigService()
        config = svc.get_defaults()
        assert config["thresholds"]["auto_approve"] == 0.80
        assert config["thresholds"]["pending_review"] == 0.60
        assert config["models"]["default"] == "qwen-plus"
        assert config["retrieval"]["milvus_top_k"] == 20
        assert config["retrieval"]["rrf_k"] == 60
        assert config["retrieval"]["rrf_top_n"] == 15
        assert config["rules"]["required_fields"]["enabled"] is True

    def test_load_returns_defaults_when_no_cache(self):
        svc = ConfigService()
        svc._cached = None
        config = ConfigService.get_config()
        assert config["thresholds"]["auto_approve"] == 0.80

    def test_partial_update_merges_correctly(self):
        svc = ConfigService()
        svc._cached = dict(DEFAULTS)
        partial = {"thresholds": {"auto_approve": 0.90}}
        updated = svc.apply_partial(partial)
        assert updated["thresholds"]["auto_approve"] == 0.90
        assert updated["thresholds"]["pending_review"] == 0.60  # unchanged
        assert updated["models"]["default"] == "qwen-plus"      # unchanged

    def test_partial_update_keeps_unrelated_sections(self):
        svc = ConfigService()
        svc._cached = dict(DEFAULTS)
        partial = {"retrieval": {"rrf_top_n": 10}}
        updated = svc.apply_partial(partial)
        assert updated["retrieval"]["rrf_top_n"] == 10
        assert updated["retrieval"]["rrf_k"] == 60  # unchanged
        assert updated["thresholds"]["auto_approve"] == 0.80   # unchanged section
