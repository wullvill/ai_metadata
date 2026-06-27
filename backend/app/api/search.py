"""元数据搜索 API"""
from fastapi import APIRouter
from app.services.search_index import search_all, get_filter_options
from app.api.schemas import SearchRequest

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("/filters")
async def get_filters():
    """获取检索过滤选项（系统/库/Schema 的全部可选值）"""
    options = get_filter_options()
    return {"success": True, "data": options}


@router.post("")
async def search_metadata(req: SearchRequest):
    """搜索元数据（ES 关键词检索）"""
    results = search_all(
        query_text=req.query,
        entity_type=req.entity_type,
        database=req.database,
        schema_name=req.schema_name,
        data_type=req.data_type,
        db_type=req.db_type,
        is_sample=req.is_sample,
        sort_by=req.sort_by,
        sort_desc=req.sort_desc,
        top_k=200,
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
