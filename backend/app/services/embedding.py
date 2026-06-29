"""向量嵌入服务"""
from dashscope import TextEmbedding
from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.retry import async_retry

logger = get_logger(__name__)
settings = get_settings()


@async_retry(max_retries=2, delay=1.0)
async def embed_text(text: str) -> list[float]:
    """文本向量化"""
    resp = TextEmbedding.call(
        model="text-embedding-v3",
        input=text,
        api_key=settings.dashscope_api_key,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Embedding API error: {resp.code} - {resp.message}")
    return resp.output["embeddings"][0]["embedding"]


def build_table_search_text(
    database: str, schema_name: str, table_name: str,
    display_name: str = "", description: str = "", tags: list[str] | None = None,
    columns_summary: str = "",
) -> str:
    """构建表的向量化文本"""
    parts = [f"{database}.{schema_name}.{table_name}"]
    if display_name:
        parts.append(f"中文名:{display_name}")
    if description:
        parts.append(f"描述:{description}")
    if tags:
        parts.append(f"标签:{','.join(tags)}")
    if columns_summary:
        parts.append(f"字段:{columns_summary}")
    return " | ".join(parts)


def build_column_search_text(
    database: str, schema_name: str, table_name: str, column_name: str,
    data_type: str = "", display_name: str = "", description: str = "",
) -> str:
    """构建字段的向量化文本"""
    parts = [f"{database}.{schema_name}.{table_name}.{column_name}"]
    if data_type:
        parts.append(f"类型:{data_type}")
    if display_name:
        parts.append(f"中文名:{display_name}")
    if description:
        parts.append(f"描述:{description}")
    return " | ".join(parts)
