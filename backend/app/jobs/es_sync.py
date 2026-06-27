"""ES 回写异步任务"""
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.completion import CompletionRecord
from app.services.search_index import reset_completion_status, update_completed_metadata, update_completed_columns
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="es_sync_approval", bind=True, max_retries=3, default_retry_delay=60)
def sync_approval_to_es(self, record_id: str):
    """审批通过后异步回写 ES"""
    db = SessionLocal()
    try:
        record = db.query(CompletionRecord).filter(
            CompletionRecord.id == record_id
        ).first()

        if not record or not record.completion_result:
            logger.warning(f"sync_approval_to_es: record {record_id} not found or no result")
            return {"status": "skipped", "record_id": record_id}

        # 回写表
        table_ok = update_completed_metadata(
            record.entity_id, record.completion_result
        )

        # 回写字段
        if record.entity_type == "table":
            columns = db.query(CompletionRecord).filter(
                CompletionRecord.entity_type == "column",
                CompletionRecord.parent_record_id == record_id,
            ).all()

            columns_data = [
                {
                    "name": c.entity_id.split(".")[-1],
                    "description": (c.completion_result or {}).get("description", ""),
                    "tags": (c.completion_result or {}).get("tags", []),
                }
                for c in columns
                if c.completion_result
            ]
            col_count = update_completed_columns(record.entity_id, columns_data)
        else:
            col_count = 0

        logger.info(
            f"ES sync done: {record.entity_id} table={table_ok} columns={col_count}"
        )
        return {"status": "done", "record_id": record_id, "table_ok": table_ok, "columns": col_count}
    except Exception as e:
        logger.error(f"sync_approval_to_es failed for {record_id}: {e}")
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(name="es_reset_asset_pending", bind=True, max_retries=3, default_retry_delay=60)
def reset_asset_to_pending(self, entity_id: str):
    """审核拒绝后异步重置 ES 资产状态为待补全"""
    try:
        ok = reset_completion_status(entity_id)
        logger.info(f"ES reset done: {entity_id} ok={ok}")
        return {"status": "done", "entity_id": entity_id, "ok": ok}
    except Exception as e:
        logger.error(f"reset_asset_to_pending failed for {entity_id}: {e}")
        raise self.retry(exc=e)
