"""OpenMetadata 同步状态 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.completion import CompletionRecord

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.get("/status")
async def get_sync_status(db: AsyncSession = Depends(get_db)):
    """查询同步状态"""
    result = await db.execute(
        select(func.count(CompletionRecord.id)).where(
            CompletionRecord.synced_to_om == True
        )
    )
    synced_count = result.scalar() or 0

    total_result = await db.execute(
        select(func.count(CompletionRecord.id)).where(
            CompletionRecord.review_status.in_(["auto_approved", "approved", "modified"])
        )
    )
    pending_sync = total_result.scalar() or 0

    return {
        "success": True,
        "data": {
            "synced_count": synced_count,
            "pending_sync": pending_sync,
            "failed_count": 0,
        },
    }
