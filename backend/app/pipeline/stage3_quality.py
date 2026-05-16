"""Stage 3: 质量校验"""
import re
from .state import CompletionState
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---- 规则引擎 ----

RULES = {
    "required_fields": {
        "check": lambda r, t: all(r.get(f) for f in ["display_name", "description"]),
        "severity": "critical",
        "message": "display_name 或 description 缺失",
    },
    "display_name_no_code": {
        "check": lambda r, t: not bool(re.search(r'[a-z]{3,}', r.get("display_name", "").lower())),
        "severity": "warning",
        "message": "中文名包含大段英文，疑似代码而非中文名",
    },
    "description_not_copy_name": {
        "check": lambda r, t: r.get("description", "").strip() != r.get("display_name", "").strip(),
        "severity": "warning",
        "message": "描述与中文名完全一致，描述应更详细",
    },
    "sensitive_level_valid": {
        "check": lambda r, t: r.get("sensitive_level") in [None, "L1", "L2", "L3", "L4"],
        "severity": "warning",
        "message": "敏感级别不在 L1-L4 范围内",
    },
    "tag_no_duplicates": {
        "check": lambda r, t: len(r.get("tags", [])) == len(set(r.get("tags", []))),
        "severity": "info",
        "message": "标签存在重复",
    },
    "business_domain_valid": {
        "check": lambda r, t: (
            r.get("business_domain") is None or len(str(r.get("business_domain", ""))) <= 20
        ),
        "severity": "info",
        "message": "业务域名过长",
    },
    "table_name_consistency": {
        "check": lambda r, t: (
            r.get("display_name", "").lower().replace("_", "")
            != t.get("table_name", "").lower().replace("_", "")
        ),
        "severity": "warning",
        "message": "中文名与英文表名相同，需要更具体的业务含义",
    },
}


def calculate_adjusted_confidence(result: dict, target: dict) -> float:
    """修正置信度得分"""
    score = result.get("confidence", 0.5)
    penalties = []

    # 检索质量降权
    scores = [ctx.get("score", 0) for ctx in target.get("retrieved_context", [])[:5]]
    if scores and (sum(scores) / len(scores)) < 0.05:
        penalties.append(0.15)

    # 描述长度异常
    desc = result.get("description", "")
    if len(desc) < 10:
        penalties.append(0.20)
    elif len(desc) > 300:
        penalties.append(0.10)

    # 中文名特殊字符
    if re.search(r'[{}[\]()\\]', result.get("display_name", "")):
        penalties.append(0.15)

    # 标签异常
    tags = result.get("tags", [])
    if len(tags) == 0:
        penalties.append(0.10)
    elif len(tags) > 8:
        penalties.append(0.05)

    adjusted = score - sum(penalties)
    return max(0.0, min(1.0, adjusted))


def check_rules(result: dict, target: dict) -> list[dict]:
    """执行规则引擎校验"""
    violations = []
    for rule_name, rule in RULES.items():
        passed = rule["check"](result, target)
        if not passed:
            violations.append({
                "rule": rule_name,
                "severity": rule["severity"],
                "message": rule["message"],
            })
    return violations


def check_conflict(result: dict, target: dict) -> list[dict]:
    """检查与已有元数据的冲突"""
    conflicts = []

    # 描述重叠检测
    if target.get("current_description") and result.get("description"):
        overlap = _text_overlap(result["description"], target["current_description"])
        if overlap < 0.3:
            conflicts.append({
                "type": "description_divergence",
                "severity": "warning",
                "message": f"新描述与已有描述差异大 (重叠度 {overlap:.2f})，请确认是否需要覆盖",
            })

    # 标签交集检测
    if target.get("current_tags") and result.get("tags"):
        old_set = set(target["current_tags"])
        new_set = set(result["tags"])
        if not old_set.intersection(new_set):
            conflicts.append({
                "type": "tag_overhaul",
                "severity": "info",
                "message": "新标签与已有标签无交集",
            })

    return conflicts


def decide_review_status(adjusted_confidence: float, violations: list[dict]) -> str:
    """根据置信度和违规决定审核状态"""
    has_critical = any(v["severity"] == "critical" for v in violations)
    has_warning = any(v["severity"] == "warning" for v in violations)

    if has_critical or adjusted_confidence < 0.60:
        return "rejected"
    elif adjusted_confidence >= 0.80 and not has_warning:
        return "auto_approved"
    else:
        return "pending_review"


def _text_overlap(text1: str, text2: str) -> float:
    """简单文本重叠度计算（Jaccard）"""
    set1 = set(text1)
    set2 = set(text2)
    if not set1 or not set2:
        return 0.0
    return len(set1.intersection(set2)) / len(set1.union(set2))


async def stage3_quality(state: CompletionState) -> CompletionState:
    """Stage 3: 质量校验"""
    if state.get("error") or state.get("completion_result") is None:
        state["quality_check"] = None
        state["review_status"] = "rejected"
        return state

    result = state["completion_result"]
    target = state["target_entity"]

    adjusted_confidence = calculate_adjusted_confidence(result, target)
    rule_violations = check_rules(result, target)
    conflicts = check_conflict(result, target)
    review_status = decide_review_status(adjusted_confidence, rule_violations)

    state["quality_check"] = {
        "original_confidence": result.get("confidence", 0),
        "adjusted_confidence": adjusted_confidence,
        "rule_violations": rule_violations,
        "conflicts": conflicts,
        "review_status": review_status,
    }
    state["review_status"] = review_status

    logger.info(
        f"Stage 3 complete: status={review_status}, "
        f"confidence={adjusted_confidence:.2f}, violations={len(rule_violations)}"
    )
    return state
