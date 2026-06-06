"""配置管理 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.schemas import PipelineConfigUpdateRequest
from app.services.config_service import config_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("")
async def get_config():
    return {"success": True, "data": config_service.get_config()}


@router.put("")
async def update_config(
    req: PipelineConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    partial = req.model_dump(exclude_none=True)
    merged = config_service.apply_partial(partial)
    await config_service.save_to_db(db, merged)
    return {"success": True, "data": config_service.get_config()}


@router.get("/defaults")
async def get_defaults():
    return {"success": True, "data": config_service.get_defaults()}
