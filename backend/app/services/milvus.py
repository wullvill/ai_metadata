"""Milvus 向量数据库服务"""
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

COLLECTION_NAME = "metadata_embeddings"
DIM = 1024


def get_milvus_collection() -> Collection:
    """获取或创建 Milvus Collection"""
    connections.connect(host=settings.milvus_host, port=settings.milvus_port)

    if utility.has_collection(COLLECTION_NAME):
        return Collection(COLLECTION_NAME)

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="entity_id", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="entity_type", dtype=DataType.VARCHAR, max_length=32),
        FieldSchema(name="database", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="schema_name", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="table_name", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="column_name", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="data_type", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="search_text", dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name="has_description", dtype=DataType.BOOL),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIM),
    ]

    schema = CollectionSchema(fields, description="元数据向量索引")
    collection = Collection(COLLECTION_NAME, schema)

    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "COSINE",
        "params": {"nlist": 128},
    }
    collection.create_index("embedding", index_params)
    collection.load()

    logger.info(f"Created Milvus collection: {COLLECTION_NAME}")
    return collection


def search_similar(
    embedding: list[float],
    entity_type: str,
    top_k: int = 20,
    database: str | None = None,
) -> list[dict]:
    """向量相似检索"""
    collection = get_milvus_collection()

    filter_expr = f'entity_type == "{entity_type}" and has_description == true'
    if database:
        filter_expr += f' and database == "{database}"'

    results = collection.search(
        data=[embedding],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 16}},
        limit=top_k,
        expr=filter_expr,
        output_fields=["entity_id", "entity_type", "database", "schema_name",
                       "table_name", "column_name", "data_type", "search_text"],
    )

    return [
        {
            "entity_id": hit.entity.get("entity_id"),
            "entity_type": hit.entity.get("entity_type"),
            "database": hit.entity.get("database"),
            "schema_name": hit.entity.get("schema_name"),
            "table_name": hit.entity.get("table_name"),
            "column_name": hit.entity.get("column_name"),
            "data_type": hit.entity.get("data_type"),
            "search_text": hit.entity.get("search_text"),
            "score": hit.score,
            "source": "milvus",
        }
        for hit in results[0]
    ]


def insert_embeddings(records: list[dict]) -> None:
    """批量插入向量"""
    if not records:
        return
    collection = get_milvus_collection()
    collection.insert(records)
    collection.flush()


def delete_by_entity_ids(entity_ids: list[str]) -> None:
    """按 entity_id 删除向量"""
    collection = get_milvus_collection()
    ids_str = ", ".join(f'"{eid}"' for eid in entity_ids)
    collection.delete(f'entity_id in [{ids_str}]')
