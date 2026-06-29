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

    def test_long_description_penalized(self):
        result = {"display_name": "订单表", "description": "x" * 301, "tags": ["交易"], "confidence": 0.9}
        target = {"retrieved_context": [{"score": 0.1}] * 5}
        conf = calculate_adjusted_confidence(result, target)
        assert conf <= 0.80  # -0.10 for long description

    def test_special_chars_in_name_penalized(self):
        result = {"display_name": "订单[表]", "description": "订单信息记录表", "tags": ["交易"], "confidence": 0.9}
        target = {"retrieved_context": [{"score": 0.1}] * 5}
        conf = calculate_adjusted_confidence(result, target)
        assert conf <= 0.75  # -0.15 for special chars

    def test_too_many_tags_penalized(self):
        result = {"display_name": "订单表", "description": "订单信息记录表", "tags": ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9"], "confidence": 0.9}
        target = {"retrieved_context": [{"score": 0.1}] * 5}
        conf = calculate_adjusted_confidence(result, target)
        assert conf <= 0.85  # -0.05 for >8 tags

    def test_no_retrieved_context_no_penalty(self):
        result = {"display_name": "订单表", "description": "记录订单的完整业务信息包括交易核心数据", "tags": ["交易"], "confidence": 0.9}
        target = {"retrieved_context": []}
        conf = calculate_adjusted_confidence(result, target)
        assert conf == 0.9  # No penalty when no retrieval context


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

    def test_sensitive_level_invalid_warning(self):
        violations = check_rules(
            {"display_name": "订单表", "description": "订单信息表", "tags": [], "sensitive_level": "L5"},
            {"entity_type": "table", "table_name": "t_order"},
        )
        assert any(v["rule"] == "sensitive_level_valid" for v in violations)

    def test_duplicate_tags_info(self):
        violations = check_rules(
            {"display_name": "订单表", "description": "订单信息表", "tags": ["交易", "交易"]},
            {"entity_type": "table", "table_name": "t_order"},
        )
        assert any(v["rule"] == "tag_no_duplicates" for v in violations)

    def test_business_domain_too_long_info(self):
        violations = check_rules(
            {"display_name": "订单表", "description": "订单信息表", "tags": ["交易"],
             "business_domain": "a" * 21},
            {"entity_type": "table", "table_name": "t_order"},
        )
        assert any(v["rule"] == "business_domain_valid" for v in violations)

    def test_table_name_same_as_display_name_warning(self):
        violations = check_rules(
            {"display_name": "tOrder", "description": "订单信息表", "tags": ["交易"]},
            {"entity_type": "table", "table_name": "tOrder"},
        )
        assert any(v["rule"] == "table_name_consistency" for v in violations)

    def test_all_rules_pass(self):
        violations = check_rules(
            {"display_name": "订单表", "description": "记录订单的完整信息", "tags": ["交易", "订单"],
             "sensitive_level": "L2", "business_domain": "交易域"},
            {"entity_type": "table", "table_name": "t_order"},
        )
        assert len(violations) == 0


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

    def test_boundary_60_pending_review(self):
        status = decide_review_status(0.60, [])
        assert status == "pending_review"  # 0.60 is NOT < 0.60, so not rejected

    def test_boundary_80_no_warnings_auto_approved(self):
        status = decide_review_status(0.80, [])
        assert status == "auto_approved"

    def test_boundary_80_with_warning_pending(self):
        violations = [{"severity": "warning"}]
        status = decide_review_status(0.80, violations)
        assert status == "pending_review"
