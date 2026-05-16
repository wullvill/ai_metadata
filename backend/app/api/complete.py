"""元数据补全 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.pipeline.graph import get_pipeline
from app.models.completion import CompletionRecord
from app.api.schemas import CompletionTriggerRequest, CompletionResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/complete", tags=["complete"])


@router.post("/trigger/manual", response_model=CompletionResponse)
async def trigger_completion(req: CompletionTriggerRequest, db: AsyncSession = Depends(get_db)):
    """手动触发元数据补全"""
    target = req.target.model_dump()

    pipeline = get_pipeline()

    # 运行 Pipeline
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

    # 保存记录
    record = CompletionRecord(
        entity_id=target["entity_id"],
        entity_type=target["entity_type"],
        target_data=target,
        completion_result=result.get("completion_result"),
        quality_check=result.get("quality_check"),
        review_status=result.get("review_status") or "rejected",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return CompletionResponse(
        record_id=record.id,
        entity_id=record.entity_id,
        entity_type=record.entity_type,
        review_status=record.review_status,
        completion_result=record.completion_result,
        quality_check=record.quality_check,
        created_at=record.created_at.isoformat() if record.created_at else "",
    )
