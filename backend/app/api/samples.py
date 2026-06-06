"""补全样本管理 API"""
from fastapi import APIRouter
from app.services.elasticsearch import set_sample_flag, get_samples
from app.api.schemas import SampleSetRequest

router = APIRouter(prefix="/api/v1/samples", tags=["samples"])


@router.post("/set")
async def set_samples(req: SampleSetRequest):
    """批量设置/取消样本标记"""
    updated = set_sample_flag(req.entity_ids, req.is_sample)
    return {"success": True, "updated": updated}


@router.get("")
async def list_samples():
    """获取全部样本"""
    data = get_samples()
    return {"success": True, "data": data}
