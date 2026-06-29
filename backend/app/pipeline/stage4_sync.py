"""Stage 4: 审核路由 + 同步回写"""
from types import SimpleNamespace

from .state import CompletionState
from app.services.openmetadata import OpenMetadataClient
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


async def stage4_sync(state: CompletionState) -> CompletionState:
    """Stage 4: 将 auto_approved 记录同步到 OpenMetadata"""
    status = state.get("review_status") or state.get("quality_check", {}).get("review_status", "rejected")

    if status != "auto_approved":
        logger.info(f"Stage 4 sync: skip (status={status})")
        return state

    completion_result = state.get("completion_result")
    target = state.get("target_entity", {})

    if not completion_result or not target:
        logger.warning("Stage 4 sync: missing completion_result or target_entity, skip sync")
        return state

    try:
        client = OpenMetadataClient()
        try:
            record = SimpleNamespace(
                entity_id=target["entity_id"],
                entity_type=target["entity_type"],
                completion_result=completion_result,
            )
            await client.sync_to_om(record)
            logger.info(
                f"Stage 4 sync: successfully synced {target['entity_id']} to OpenMetadata"
            )
        finally:
            await client.close()
    except Exception as e:
        logger.error(
            f"Stage 4 sync failed for {target.get('entity_id', '?')}: {e}"
        )
        # 同步失败不阻塞 Pipeline，仅记录日志
        state["sync_error"] = str(e)

    return state
