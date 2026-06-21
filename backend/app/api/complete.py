"""元数据补全 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.pipeline.graph import get_pipeline, get_stages
from app.models.completion import CompletionRecord
from app.api.schemas import CompletionTriggerRequest, CompletionResponse
from datetime import datetime, timezone

from app.utils.logger import get_logger
from app.services.elasticsearch import get_es_client, INDEX_NAME

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/complete", tags=["complete"])


@router.post("/trigger/manual", response_model=CompletionResponse)
async def trigger_completion(req: CompletionTriggerRequest, db: AsyncSession = Depends(get_db)):
    """手动触发元数据补全。表级补全会级联补全其所有字段。"""
    target = req.target.model_dump(by_alias=True)

    pipeline = get_pipeline()

    result = await pipeline.ainvoke({
        "target_entity": target,
        "retrieved_context": None,
        "schema_context": None,
        "sibling_columns": None,
        "completion_result": None,
        "quality_check": None,
        "review_status": None,
        "error": None,
    })

    record = CompletionRecord(
        entity_id=target["entity_id"],
        entity_type=target["entity_type"],
        target_data=target,
        completion_result=result.get("completion_result"),
        quality_check=result.get("quality_check"),
        review_status=result.get("review_status") or "rejected",
    )
    db.add(record)

    # 表级补全：级联补全所有字段
    if target["entity_type"] == "table":
        stage2, stage3 = get_stages()
        columns = await _fetch_columns(target)
        if columns:
            logger.info(f"Cascading completion to {len(columns)} columns of {target['entity_id']}")
            table_desc = (result.get("completion_result") or {}).get("description", "")
            for col in columns:
                col_target = {
                    "entity_id": col.get("column_id", f"{target['entity_id']}.{col['column_name']}"),
                    "entity_type": "column",
                    "database": target.get("database", ""),
                    "schema": target.get("schema", ""),
                    "table_name": target.get("table_name", ""),
                    "column_name": col["column_name"],
                    "data_type": col.get("data_type", ""),
                    "current_description": col.get("original_description") or "",
                    "current_display_name": col.get("column_name", ""),
                    "current_tags": col.get("original_tags") or [],
                    "table_description": table_desc,
                }
                col_state = {
                    "target_entity": col_target,
                    "retrieved_context": result.get("retrieved_context"),
                    "schema_context": result.get("schema_context"),
                }
                try:
                    col_state = await stage2(col_state)
                    if not col_state.get("error"):
                        col_state = await stage3(col_state)
                except Exception as e:
                    logger.warning(f"Column completion failed for {col['entity_id']}: {e}")
                    col_state["completion_result"] = None
                    col_state["quality_check"] = None
                    col_state["review_status"] = "rejected"

                col_record = CompletionRecord(
                    entity_id=col_target["entity_id"],
                    entity_type="column",
                    target_data=col_target,
                    completion_result=col_state.get("completion_result"),
                    quality_check=col_state.get("quality_check"),
                    review_status=col_state.get("review_status") or "rejected",
                )
                db.add(col_record)

    await db.commit()
    await db.refresh(record)

    # 同步标记 ES 为处理中
    try:
        es = get_es_client()
        es.update(index=INDEX_NAME, id=target["entity_id"], doc={
            "completion_status": "processing",
            "updated_time": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass

    # 自动采纳：异步回写 ES（与人工审批逻辑一致）
    if record.review_status == "auto_approved":
        try:
            from app.jobs.es_sync import sync_approval_to_es
            sync_approval_to_es.delay(record.id)
        except Exception as e:
            logger.warning(f"Failed to dispatch ES sync for auto_approved {record.id}: {e}")

    return CompletionResponse(
        record_id=record.id,
        entity_id=record.entity_id,
        entity_type=record.entity_type,
        review_status=record.review_status,
        completion_result=record.completion_result,
        quality_check=record.quality_check,
        created_at=record.created_at.isoformat() if record.created_at else "",
    )


async def _fetch_columns(target: dict) -> list[dict]:
    """从 ES 获取表的字段列表"""
    from app.services.elasticsearch import get_columns
    try:
        return get_columns(target.get("entity_id", ""))
    except Exception as e:
        logger.warning(f"Failed to fetch columns for {target.get('entity_id')}: {e}")
        return []
