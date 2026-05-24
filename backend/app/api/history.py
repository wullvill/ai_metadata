"""补全历史查询 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.completion import CompletionRecord

router = APIRouter(prefix="/api/v1/complete", tags=["history"])


@router.get("/history")
async def get_completion_history(
    entity_id: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """查询补全历史，支持按实体、状态、时间范围筛选"""
    query = select(CompletionRecord)

    if entity_id:
        query = query.where(CompletionRecord.entity_id == entity_id)
    if status:
        query = query.where(CompletionRecord.review_status == status)
    if start_date:
        query = query.where(CompletionRecord.created_at >= start_date)
    if end_date:
        query = query.where(CompletionRecord.created_at <= end_date)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(CompletionRecord.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "entity_id": r.entity_id,
                "entity_type": r.entity_type,
                "completion_result": r.completion_result,
                "quality_check": r.quality_check,
                "review_status": r.review_status,
                "reviewer": r.reviewer,
                "review_comment": r.review_comment,
                "synced_to_om": r.synced_to_om,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in records
        ],
        "meta": {"total": total, "page": page, "limit": limit},
    }
