"""OpenMetadata 元数据同步 Job"""
from app.celery_app import celery_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="sync_metadata_from_om")
def sync_metadata_from_om():
    """从 OpenMetadata 同步元数据到本地索引"""
    logger.info("Starting metadata sync from OpenMetadata...")
    # TODO: 实现完整的同步逻辑
    # 1. 调用 OpenMetadata API 拉取表/字段列表
    # 2. 向量化并写入 Milvus
    # 3. 索引到 ES
    logger.info("Metadata sync completed")
    return {"status": "ok", "message": "sync completed"}
