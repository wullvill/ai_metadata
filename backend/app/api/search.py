"""元数据搜索 API"""
from fastapi import APIRouter
from app.services.elasticsearch import search_all
from app.api.schemas import SearchRequest

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("")
async def search_metadata(req: SearchRequest):
    """搜索元数据（ES 关键词检索）"""
    results = search_all(
        query_text=req.query,
        entity_type=req.entity_type,
        database=req.database,
        schema_name=req.schema_name,
        data_type=req.data_type,
        top_k=100,
    )
    # 分页
    start = (req.page - 1) * req.page_size
    end = start + req.page_size
    items = results[start:end]

    return {
        "success": True,
        "data": items,
        "meta": {
            "total": len(results),
            "page": req.page,
            "page_size": req.page_size,
        },
    }
