"""Asset detail API"""
from fastapi import APIRouter, HTTPException
from app.services.elasticsearch import get_asset_by_id, get_columns

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.get("/{entity_id}")
async def get_asset_detail(entity_id: str):
    """Get asset detail with basic info + column list"""
    asset = get_asset_by_id(entity_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    columns = get_columns(entity_id)

    return {
        "success": True,
        "data": {
            **asset,
            "columns": columns,
        },
    }
