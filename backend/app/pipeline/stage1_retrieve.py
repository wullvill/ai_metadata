"""Stage 1: 双路检索 (Milvus + ES)"""
import asyncio
from .state import CompletionState
from app.services import milvus, elasticsearch, embedding
from app.utils.logger import get_logger

logger = get_logger(__name__)


def rrf_merge(
    milvus_results: list[dict],
    es_results: list[dict],
    k: int = 60,
    top_n: int = 15,
) -> list[dict]:
    """Reciprocal Rank Fusion 两路合并排序"""
    scores: dict[str, float] = {}
    detail: dict[str, dict] = {}

    for rank, item in enumerate(milvus_results):
        eid = item["entity_id"]
        scores[eid] = scores.get(eid, 0) + 1 / (k + rank + 1)
        detail[eid] = {**item, "source": "milvus"}

    for rank, item in enumerate(es_results):
        eid = item["entity_id"]
        scores[eid] = scores.get(eid, 0) + 1 / (k + rank + 1)
        prev = detail.get(eid, {})
        source = "both" if prev.get("source") == "milvus" else "es"
        detail[eid] = {**prev, **item, "source": source}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [detail[eid] for eid, _ in ranked[:top_n]]


def build_retrieval_text(target: dict) -> str:
    """构建检索文本"""
    parts = [f"{target['database']}.{target['schema']}.{target['table_name']}"]
    if target.get("column_name"):
        parts[-1] += f".{target['column_name']}"
    if target.get("data_type"):
        parts.append(target["data_type"])
    return " ".join(parts)


async def stage1_retrieve(state: CompletionState) -> CompletionState:
    """Stage 1: 双路检索上下文"""
    target = state["target_entity"]
    search_text = build_retrieval_text(target)

    # 向量化检索文本
    query_embedding = await embedding.embed_text(search_text)

    # 并行双路检索
    db = target.get("database")
    schema_name = target.get("schema")

    loop = asyncio.get_event_loop()

    milvus_future = loop.run_in_executor(
        None,
        lambda: milvus.search_similar(
            query_embedding, target["entity_type"], top_k=20, database=db
        ),
    )

    es_future = loop.run_in_executor(
        None,
        lambda: elasticsearch.search_keyword(
            search_text, target["entity_type"], database=db, schema_name=schema_name, top_k=20
        ),
    )

    siblings_future = loop.run_in_executor(
        None,
        lambda: elasticsearch.search_siblings(
            db, schema_name, target["entity_type"], top_k=5
        ),
    )

    milvus_results = await milvus_future
    es_results = await es_future
    schema_context = await siblings_future

    # RRF 合并
    merged = rrf_merge(milvus_results, es_results, top_n=15)

    # 字段级补全：额外获取同表兄弟字段
    sibling_columns = []
    if target["entity_type"] == "column" and target.get("column_name"):
        sibling_columns = _get_sibling_columns(target)

    state["retrieved_context"] = merged
    state["schema_context"] = schema_context or []
    state["sibling_columns"] = sibling_columns

    logger.info(
        f"Stage 1 complete: {len(merged)} results "
        f"(milvus={len(milvus_results)}, es={len(es_results)})"
    )
    return state


def _get_sibling_columns(target: dict) -> list[dict]:
    """获取同表其他字段"""
    try:
        siblings = elasticsearch.search_all(
            query_text=target["table_name"],
            entity_type="column",
            top_k=20,
        )
        return [
            s for s in siblings
            if s.get("table_name") == target["table_name"]
            and s.get("column_name") != target.get("column_name")
        ][:10]
    except Exception:
        return []
