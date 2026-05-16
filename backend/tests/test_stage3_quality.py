"""Stage 3 质量校验测试"""
import pytest
from app.pipeline.stage3_quality import (
    calculate_adjusted_confidence,
    check_rules,
    check_conflict,
    decide_review_status,
)


class TestAdjustedConfidence:
    def test_high_confidence_passes(self):
        result = {"display_name": "订单表", "description": "订单信息记录表，包含交易核心数据", "tags": ["交易"], "confidence": 0.9}
        target = {"retrieved_context": [{"score": 0.1}] * 5}
        conf = calculate_adjusted_confidence(result, target)
        assert conf >= 0.85

    def test_short_description_penalized(self):
        result = {"display_name": "X", "description": "abc", "tags": [], "confidence": 0.9}
        target = {"retrieved_context": [{"score": 0.01}] * 5}
        conf = calculate_adjusted_confidence(result, target)
        assert conf < 0.7  # 检索差 + 描述短 + 无标签 -> 大幅降权


class TestCheckRules:
    def test_required_fields_critical(self):
        violations = check_rules(
            {"display_name": "", "description": "desc", "tags": []},
            {"entity_type": "table", "table_name": "t_order"},
        )
        assert any(v["severity"] == "critical" for v in violations)

    def test_display_name_no_code_warning(self):
        violations = check_rules(
            {"display_name": "userProfileTable", "description": "用户表", "tags": ["用户"]},
            {"entity_type": "table", "table_name": "t_order"},
        )
        assert any(v["rule"] == "display_name_no_code" for v in violations)

    def test_description_same_as_name_warning(self):
        violations = check_rules(
            {"display_name": "订单表", "description": "订单表", "tags": ["交易"]},
            {"entity_type": "table", "table_name": "t_order"},
        )
        assert any(v["rule"] == "description_not_copy_name" for v in violations)


class TestCheckConflict:
    def test_description_divergence_detected(self):
        conflicts = check_conflict(
            {"description": "全新的业务含义"},
            {"current_description": "旧的描述完全不同", "current_tags": []},
        )
        assert any(c["type"] == "description_divergence" for c in conflicts)

    def test_tag_overhaul_detected(self):
        conflicts = check_conflict(
            {"tags": ["新标签"]},
            {"current_tags": ["旧标签"]},
        )
        assert any(c["type"] == "tag_overhaul" for c in conflicts)

    def test_no_conflict_when_empty_current(self):
        conflicts = check_conflict(
            {"description": "新描述", "tags": ["新"]},
            {},
        )
        assert len(conflicts) == 0


class TestReviewStatus:
    def test_auto_approved(self):
        violations = []
        status = decide_review_status(0.85, violations)
        assert status == "auto_approved"

    def test_pending_review(self):
        violations = [{"severity": "warning"}]
        status = decide_review_status(0.75, violations)
        assert status == "pending_review"

    def test_rejected_low_confidence(self):
        status = decide_review_status(0.50, [])
        assert status == "rejected"

    def test_rejected_critical(self):
        violations = [{"severity": "critical"}]
        status = decide_review_status(0.90, violations)
        assert status == "rejected"
