"""审核 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.database import get_db
from app.models.completion import CompletionRecord, AuditLog
from app.api.schemas import ReviewActionRequest
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/review", tags=["review"])


@router.get("/queue")
async def get_review_queue(
    entity_type: str | None = None,
    status: str = "pending_review",
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """获取审核队列"""
    query = select(CompletionRecord).where(
        CompletionRecord.review_status == status
    )
    if entity_type:
        query = query.where(CompletionRecord.entity_type == entity_type)

    query = query.order_by(CompletionRecord.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

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
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
    }


@router.get("/{record_id}")
async def get_review_detail(record_id: str, db: AsyncSession = Depends(get_db)):
    """获取审核详情"""
    result = await db.execute(
        select(CompletionRecord).where(CompletionRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="审核记录不存在")

    return {
        "success": True,
        "data": {
            "id": record.id,
            "entity_id": record.entity_id,
            "entity_type": record.entity_type,
            "target_data": record.target_data,
            "completion_result": record.completion_result,
            "quality_check": record.quality_check,
            "review_status": record.review_status,
            "reviewer": record.reviewer,
            "review_comment": record.review_comment,
            "synced_to_om": record.synced_to_om,
        },
    }


@router.post("/{record_id}/approve")
async def approve_review(
    record_id: str,
    req: ReviewActionRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """确认补全"""
    result = await db.execute(
        select(CompletionRecord).where(CompletionRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    record.review_status = "approved"
    record.reviewer = "admin"
    record.review_comment = req.comment if req else None
    record.reviewed_at = datetime.now(timezone.utc)

    log = AuditLog(
        entity_id=record.entity_id,
        action="manual_approve",
        operator="admin",
        detail={"record_id": record_id, "result": record.completion_result},
    )
    db.add(log)
    await db.commit()

    logger.info(f"Review approved: {record_id} -> {record.entity_id}")
    return {"success": True, "data": {"status": "approved"}}


@router.post("/{record_id}/reject")
async def reject_review(
    record_id: str,
    req: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """拒绝补全"""
    result = await db.execute(
        select(CompletionRecord).where(CompletionRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    record.review_status = "human_rejected"
    record.reviewer = "admin"
    record.review_comment = req.comment or ""
    record.reviewed_at = datetime.now(timezone.utc)

    log = AuditLog(
        entity_id=record.entity_id,
        action="reject",
        operator="admin",
        detail={"record_id": record_id, "reason": req.comment},
    )
    db.add(log)
    await db.commit()

    return {"success": True, "data": {"status": "rejected"}}


@router.post("/batch/approve")
async def batch_approve(record_ids: list[str], db: AsyncSession = Depends(get_db)):
    """批量确认"""
    for rid in record_ids:
        result = await db.execute(select(CompletionRecord).where(CompletionRecord.id == rid))
        record = result.scalar_one_or_none()
        if record and record.review_status == "pending_review":
            record.review_status = "approved"
            record.reviewer = "admin"
            record.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    return {"success": True, "data": {"count": len(record_ids)}}
