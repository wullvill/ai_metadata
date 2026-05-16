"""Stage 4: 审核路由 + 同步回写"""
from .state import CompletionState
from app.utils.logger import get_logger

logger = get_logger(__name__)


def stage4_review_router(state: CompletionState) -> str:
    """根据 Stage 3 分流决策返回路由目标"""
    status = state.get("review_status") or state.get("quality_check", {}).get("review_status", "rejected")

    if status == "auto_approved":
        logger.info(f"Stage 4 route: auto_approved → sync_to_openmetadata")
        return "auto_approved"
    elif status == "pending_review":
        logger.info(f"Stage 4 route: pending_review → review_queue")
        return "pending_review"
    else:
        logger.info(f"Stage 4 route: {status} → log_and_notify")
        return "rejected"
