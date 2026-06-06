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

    from app.services.config_service import config_service
    cfg = config_service.get_config()
    retrieval = cfg["retrieval"]

    # 向量化检索文本
    query_embedding = None
    try:
        query_embedding = await embedding.embed_text(search_text)
    except Exception as e:
        logger.warning(f"Embedding 失败，将降级到 ES-only 检索: {e}")

    # 并行双路检索
    db = target.get("database")
    schema_name = target.get("schema")

    loop = asyncio.get_event_loop()

    milvus_future = None
    if query_embedding is not None:
        milvus_future = loop.run_in_executor(
            None,
            lambda: milvus.search_similar(
                query_embedding, target["entity_type"], top_k=retrieval["milvus_top_k"], database=db
            ),
        )

    es_future = loop.run_in_executor(
        None,
        lambda: elasticsearch.search_keyword(
            search_text, target["entity_type"], database=db, schema_name=schema_name, top_k=retrieval["es_keyword_top_k"]
        ),
    )

    siblings_future = loop.run_in_executor(
        None,
        lambda: elasticsearch.search_siblings(
            db, schema_name, target["entity_type"], top_k=retrieval["es_siblings_top_k"]
        ),
    )

    # 带降级处理的检索结果获取
    milvus_results: list[dict] = []
    es_results: list[dict] = []
    milvus_ok = False
    es_ok = False

    if milvus_future is not None:
        try:
            milvus_results = await milvus_future
            milvus_ok = True
        except Exception as e:
            logger.warning(f"Milvus 检索失败，降级到 ES-only: {e}")

    try:
        es_results = await es_future
        es_ok = True
    except Exception as e:
        logger.warning(f"ES 检索失败，降级到 Milvus-only: {e}")

    try:
        schema_context = await siblings_future
    except Exception as e:
        logger.warning(f"ES siblings 检索失败: {e}")
        schema_context = []

    # 两路均不可用，返回错误
    if not milvus_ok and not es_ok:
        state["error"] = "双路检索均不可用"
        state["retrieved_context"] = []
        state["schema_context"] = schema_context or []
        state["sibling_columns"] = []
        logger.error("Stage 1 failed: 双路检索均不可用")
        return state

    # 查询样本并置顶
    if retrieval["sample_boost"]:
        try:
            sample_docs = elasticsearch.get_samples()
            if sample_docs:
                logger.info(f"Stage 1: {len(sample_docs)} samples found, boosting rank")
                for doc in sample_docs:
                    milvus_results.insert(0, {
                        "entity_id": doc["entity_id"],
                        "score": 1.0,
                        "source": "sample",
                        "table_name": doc.get("table_name"),
                        "display_name": doc.get("display_name"),
                        "description": doc.get("description"),
                        "search_text": doc.get("description", doc.get("table_name", "")),
                    })
        except Exception as e:
            logger.warning(f"Stage 1: failed to fetch samples: {e}")

    # RRF 合并或单路降级
    if milvus_ok and es_ok:
        merged = rrf_merge(milvus_results, es_results, k=retrieval["rrf_k"], top_n=retrieval["rrf_top_n"])
    elif milvus_ok:
        merged = [{**item, "source": "milvus"} for item in milvus_results[:15]]
        logger.info("Stage 1 fallback: Milvus-only retrieval (ES unavailable)")
    else:
        merged = [{**item, "source": "es"} for item in es_results[:15]]
        logger.info("Stage 1 fallback: ES-only retrieval (Milvus unavailable)")

    # 字段级补全：额外获取同表兄弟字段
    sibling_columns: list[dict] = []
    if target["entity_type"] == "column" and target.get("column_name"):
        sibling_future = loop.run_in_executor(
            None,
            lambda: _get_sibling_columns(target),
        )
        sibling_columns = await sibling_future

    state["retrieved_context"] = merged
    state["schema_context"] = schema_context or []
    state["sibling_columns"] = sibling_columns

    retrieved_count = len(milvus_results) + len(es_results) if (milvus_ok and es_ok) else (
        len(milvus_results) if milvus_ok else len(es_results)
    )
    logger.info(
        f"Stage 1 complete: {len(merged)} merged results "
        f"(milvus={'ok' if milvus_ok else 'down'}, es={'ok' if es_ok else 'down'}, "
        f"raw_total={retrieved_count})"
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
    except Exception as e:
        logger.warning(f"Failed to retrieve sibling columns for {target.get('table_name', '?')}: {e}")
        return []
