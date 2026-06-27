"""向量存储 — 嵌入模式 ChromaDB / 生产模式 Milvus"""
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

COLLECTION_NAME = "metadata_embeddings"

_chroma_collection = None


def _get_chroma_collection():
    global _chroma_collection
    if _chroma_collection is None:
        import chromadb
        from pathlib import Path

        chroma_path = str(Path(__file__).resolve().parent.parent.parent / "data" / "chroma")
        client = chromadb.PersistentClient(path=chroma_path)
        _chroma_collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _chroma_collection


def search_similar(
    embedding: list[float],
    entity_type: str,
    top_k: int = 20,
    database: str | None = None,
) -> list[dict]:
    if settings.vector_store_backend == "chroma":
        return _chroma_search_similar(embedding, entity_type, top_k, database)
    else:
        from app.services.milvus import search_similar as _milvus_search
        return _milvus_search(embedding, entity_type, top_k, database)


def _chroma_search_similar(
    embedding: list[float],
    entity_type: str,
    top_k: int = 20,
    database: str | None = None,
) -> list[dict]:
    collection = _get_chroma_collection()
    conditions = [
        {"entity_type": {"$eq": entity_type}},
        {"has_description": {"$eq": True}},
    ]
    if database:
        conditions.append({"database": {"$eq": database}})
    where: dict = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        where=where,
    )

    output = []
    ids = results.get("ids", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for i, eid in enumerate(ids):
        meta = metadatas[i] if i < len(metadatas) else {}
        dist = distances[i] if i < len(distances) else 0.0
        output.append({
            "entity_id": eid,
            "entity_type": meta.get("entity_type", entity_type),
            "database": meta.get("database"),
            "schema_name": meta.get("schema_name"),
            "table_name": meta.get("table_name"),
            "column_name": meta.get("column_name"),
            "data_type": meta.get("data_type"),
            "search_text": meta.get("search_text", ""),
            "score": 1.0 - dist,
            "source": "chroma",
        })
    return output


def insert_embeddings(records: list[dict]) -> None:
    if not records:
        return
    if settings.vector_store_backend == "chroma":
        _chroma_insert(records)
    else:
        from app.services.milvus import insert_embeddings as _milvus_insert
        _milvus_insert(records)


def _chroma_insert(records: list[dict]) -> None:
    collection = _get_chroma_collection()
    ids = [r["entity_id"] for r in records]
    embeddings = [r["embedding"] for r in records]
    metadatas = [
        {k: v for k, v in r.items() if k != "embedding"}
        for r in records
    ]
    collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas)


def delete_by_entity_ids(entity_ids: list[str]) -> None:
    if not entity_ids:
        return
    if settings.vector_store_backend == "chroma":
        collection = _get_chroma_collection()
        collection.delete(ids=entity_ids)
    else:
        from app.services.milvus import delete_by_entity_ids as _milvus_delete
        _milvus_delete(entity_ids)
