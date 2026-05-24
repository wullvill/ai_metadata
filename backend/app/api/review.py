"""审核 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
from app.database import get_db
from app.models.completion import CompletionRecord, AuditLog
from app.api.schemas import ReviewActionRequest, BatchRejectRequest
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/review", tags=["review"])


@router.get("/queue")
async def get_review_queue(
    entity_type: str | None = None,
    status: str = "pending_review",
    confidence_min: float | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", pattern=r"^(entity_id|entity_type|created_at|review_status)$"),
    sort_dir: str = Query("desc", pattern=r"^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    """获取审核队列，支持筛选、排序和分页"""
    query = select(CompletionRecord).where(CompletionRecord.review_status == status)
    if entity_type:
        query = query.where(CompletionRecord.entity_type == entity_type)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    order_col = getattr(CompletionRecord, sort_by)
    query = order_col.desc() if sort_dir == "desc" else order_col.asc()
    query = select(CompletionRecord).where(CompletionRecord.review_status == status)
    if entity_type:
        query = query.where(CompletionRecord.entity_type == entity_type)
    if sort_dir == "desc":
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    records = result.scalars().all()

    items = [
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
    ]

    if confidence_min is not None:
        items = [
            r for r in items
            if r["completion_result"]
            and isinstance(r["completion_result"], dict)
            and r["completion_result"].get("confidence", 0) >= confidence_min
        ]

    return {
        "success": True,
        "data": items,
        "meta": {"total": total, "page": page, "page_size": page_size},
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

    reviewer = (req.reviewer if req and req.reviewer else "admin")
    record.review_status = "approved"
    record.reviewer = reviewer
    record.review_comment = req.comment if req else None
    record.reviewed_at = datetime.now(timezone.utc)
    log = AuditLog(
        entity_id=record.entity_id, action="manual_approve",
        operator=reviewer,
        detail={"record_id": record_id, "result": record.completion_result},
    )
    db.add(log)
    await db.commit()
    logger.info(f"Review approved: {record_id} -> {record.entity_id}")
    return {"success": True, "data": {"status": "approved"}}


@router.post("/{record_id}/modify")
async def modify_review(
    record_id: str,
    req: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """修改后确认补全"""
    if not req.modified_result:
        raise HTTPException(status_code=400, detail="缺少 modified_result")
    result = await db.execute(
        select(CompletionRecord).where(CompletionRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    reviewer = req.reviewer or "admin"
    current = record.completion_result or {}
    record.completion_result = {**current, **req.modified_result}
    record.review_status = "modified"
    record.reviewer = reviewer
    record.review_comment = req.comment or "修改后确认"
    record.reviewed_at = datetime.now(timezone.utc)
    log = AuditLog(
        entity_id=record.entity_id, action="modify_approve",
        operator=reviewer,
        detail={"record_id": record_id, "modified": req.modified_result},
    )
    db.add(log)
    await db.commit()
    logger.info(f"Review modified: {record_id}")
    return {"success": True, "data": {"status": "modified"}}


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

    reviewer = req.reviewer or "admin"
    record.review_status = "human_rejected"
    record.reviewer = reviewer
    record.review_comment = req.comment or ""
    record.reviewed_at = datetime.now(timezone.utc)
    log = AuditLog(
        entity_id=record.entity_id, action="reject",
        operator=reviewer,
        detail={"record_id": record_id, "reason": req.comment},
    )
    db.add(log)
    await db.commit()
    return {"success": True, "data": {"status": "rejected"}}


@router.post("/batch/approve")
async def batch_approve(record_ids: list[str], db: AsyncSession = Depends(get_db)):
    """批量确认"""
    count = 0
    for rid in record_ids:
        result = await db.execute(select(CompletionRecord).where(CompletionRecord.id == rid))
        record = result.scalar_one_or_none()
        if record and record.review_status == "pending_review":
            record.review_status = "approved"
            record.reviewer = "admin"
            record.reviewed_at = datetime.now(timezone.utc)
            count += 1
    await db.commit()
    return {"success": True, "data": {"count": count}}


@router.post("/batch/reject")
async def batch_reject(req: BatchRejectRequest, db: AsyncSession = Depends(get_db)):
    """批量驳回"""
    reviewer = req.reviewer or "admin"
    count = 0
    for rid in req.record_ids:
        result = await db.execute(select(CompletionRecord).where(CompletionRecord.id == rid))
        record = result.scalar_one_or_none()
        if record and record.review_status == "pending_review":
            record.review_status = "human_rejected"
            record.reviewer = reviewer
            record.review_comment = req.reason
            record.reviewed_at = datetime.now(timezone.utc)
            log = AuditLog(
                entity_id=record.entity_id, action="batch_reject",
                operator=reviewer,
                detail={"record_id": rid, "reason": req.reason},
            )
            db.add(log)
            count += 1
    await db.commit()
    return {"success": True, "data": {"count": count}}
