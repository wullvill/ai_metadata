"""Elasticsearch 服务"""
from elasticsearch import Elasticsearch, helpers, NotFoundError
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

INDEX_NAME = "metadata_index"

COLUMNS_INDEX = "metadata_columns"

COLUMNS_MAPPINGS = {
    "properties": {
        "column_id": {"type": "keyword"},
        "entity_id": {"type": "keyword"},
        "column_name": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
        "data_type": {"type": "keyword"},
        "original_description": {"type": "text"},
        "original_tags": {"type": "keyword"},
        "completion_description": {"type": "text"},
        "completion_tags": {"type": "keyword"},
        "completion_time": {"type": "date"},
    }
}

MAPPINGS = {
    "properties": {
        "entity_id": {"type": "keyword"},
        "entity_type": {"type": "keyword"},
        "database": {"type": "keyword"},
        "schema_name": {"type": "keyword"},
        "table_name": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
        "column_name": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
        "display_name": {"type": "text"},
        "description": {"type": "text"},
        "data_type": {"type": "keyword"},
        "db_type": {"type": "keyword"},
        "tags": {"type": "keyword"},
        "has_description": {"type": "boolean"},
    }
}


def get_es_client() -> Elasticsearch:
    return Elasticsearch(settings.es_host, basic_auth=(settings.es_user, settings.es_password))


def ensure_index() -> None:
    """确保 ES 索引存在"""
    es = get_es_client()
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME, mappings=MAPPINGS)
        logger.info(f"Created ES index: {INDEX_NAME}")


def search_keyword(
    query_text: str,
    entity_type: str,
    database: str | None = None,
    schema_name: str | None = None,
    top_k: int = 20,
) -> list[dict]:
    """ES 关键词检索"""
    es = get_es_client()

    must_clauses = [
        {"term": {"has_description": True}},
        {"term": {"entity_type": entity_type}},
    ]
    if database:
        must_clauses.append({"term": {"database": database}})
    if schema_name:
        must_clauses.append({"term": {"schema_name": schema_name}})

    body = {
        "query": {
            "bool": {
                "must": must_clauses,
                "should": [
                    {"multi_match": {
                        "query": query_text,
                        "fields": ["table_name^3", "column_name^3", "display_name^2", "description"],
                        "fuzziness": "AUTO",
                    }},
                ],
            }
        },
        "size": top_k,
    }

    resp = es.search(index=INDEX_NAME, body=body)
    return [
        {
            "entity_id": hit["_source"]["entity_id"],
            "entity_type": hit["_source"]["entity_type"],
            "database": hit["_source"].get("database"),
            "schema_name": hit["_source"].get("schema_name"),
            "table_name": hit["_source"].get("table_name"),
            "column_name": hit["_source"].get("column_name"),
            "data_type": hit["_source"].get("data_type"),
            "search_text": _build_search_text(hit["_source"]),
            "score": hit["_score"],
            "source": "es",
        }
        for hit in resp["hits"]["hits"]
    ]


def search_siblings(database: str, schema_name: str, entity_type: str, top_k: int = 5) -> list[dict]:
    """查询同库同 Schema 下的兄弟实体"""
    es = get_es_client()
    body = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"database": database}},
                    {"term": {"schema_name": schema_name}},
                    {"term": {"entity_type": entity_type}},
                ],
            }
        },
        "size": top_k,
    }
    resp = es.search(index=INDEX_NAME, body=body)
    return [
        {
            "entity_id": hit["_source"]["entity_id"],
            "table_name": hit["_source"].get("table_name"),
            "column_name": hit["_source"].get("column_name"),
            "display_name": hit["_source"].get("display_name"),
            "description": hit["_source"].get("description"),
        }
        for hit in resp["hits"]["hits"]
    ]


def search_all(
    query_text: str,
    entity_type: str | None = None,
    database: str | None = None,
    schema_name: str | None = None,
    data_type: str | None = None,
    db_type: str | None = None,
    top_k: int = 20,
) -> list[dict]:
    """通用搜索（用于前端搜索页）"""
    es = get_es_client()

    must = []
    if entity_type:
        must.append({"term": {"entity_type": entity_type}})
    if database:
        must.append({"term": {"database": database}})
    if schema_name:
        must.append({"term": {"schema_name": schema_name}})
    if data_type:
        must.append({"term": {"data_type": data_type}})
    if db_type:
        must.append({"term": {"db_type": db_type}})

    has_query = bool(query_text.strip())
    has_filters = bool(must)

    if not has_query and not has_filters:
        body: dict = {"query": {"match_all": {}}, "size": top_k}
    elif not has_query and has_filters:
        body = {"query": {"bool": {"must": must}}, "size": top_k}
    else:
        body = {
            "query": {
                "bool": {
                    "must": must,
                    "should": [
                        {"multi_match": {
                            "query": query_text,
                            "fields": ["table_name^3", "column_name^3", "display_name^2", "description"],
                            "fuzziness": "AUTO",
                        }},
                    ],
                }
            },
            "size": top_k,
        }

    if has_query:
        body["highlight"] = {
            "fields": {
                "table_name": {},
                "column_name": {},
                "display_name": {},
                "description": {},
            },
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"],
        }

    resp = es.search(index=INDEX_NAME, body=body)
    return [
        {
            **hit["_source"],
            "schema": hit["_source"].get("schema_name"),
            "highlight": hit.get("highlight", {}),
        }
        for hit in resp["hits"]["hits"]
    ]


def get_filter_options() -> dict[str, list[str]]:
    """获取 system/database/schema 的全部 distinct 值"""
    es = get_es_client()
    body = {
        "size": 0,
        "aggs": {
            "systems": {"terms": {"field": "database", "size": 100}},
            "schemas": {"terms": {"field": "schema_name", "size": 100}},
            "db_types": {"terms": {"field": "db_type", "size": 20}},
        },
    }
    resp = es.search(index=INDEX_NAME, body=body)
    aggs = resp["aggregations"]
    return {
        "systems": [b["key"] for b in aggs["systems"]["buckets"]],
        "databases": [b["key"] for b in aggs["systems"]["buckets"]],
        "schemas": [b["key"] for b in aggs["schemas"]["buckets"]],
        "db_types": [b["key"] for b in aggs["db_types"]["buckets"]],
    }


def index_documents(docs: list[dict]) -> None:
    """批量索引文档"""
    if not docs:
        return
    es = get_es_client()
    actions = [
        {"_index": INDEX_NAME, "_id": doc["entity_id"], "_source": doc}
        for doc in docs
    ]
    success, errors = helpers.bulk(es, actions, raise_on_error=False)
    if errors:
        logger.warning(f"ES bulk index: {success} ok, {len(errors)} errors")


def _build_search_text(source: dict) -> str:
    """构建可展示的检索文本"""
    parts = []
    if source.get("database") and source.get("schema_name") and source.get("table_name"):
        parts.append(f"{source['database']}.{source['schema_name']}.{source['table_name']}")
    if source.get("column_name"):
        parts.append(f"字段:{source['column_name']}")
    if source.get("data_type"):
        parts.append(f"类型:{source['data_type']}")
    if source.get("display_name"):
        parts.append(f"中文名:{source['display_name']}")
    if source.get("description"):
        parts.append(f"描述:{source['description']}")
    if source.get("tags"):
        parts.append(f"标签:{','.join(source['tags'])}")
    return " | ".join(parts)


def ensure_columns_index() -> None:
    """Ensure metadata_columns index exists"""
    es = get_es_client()
    if not es.indices.exists(index=COLUMNS_INDEX):
        es.indices.create(index=COLUMNS_INDEX, mappings=COLUMNS_MAPPINGS)
        logger.info(f"Created ES index: {COLUMNS_INDEX}")


def _normalize_datetime(value: str | None) -> str | None:
    """Convert 'YYYY-MM-DD HH:MM' to ISO 'YYYY-MM-DDTHH:MM:SS' for ES date type"""
    if not value:
        return None
    if "T" in value:
        return value
    s = value.replace(" ", "T")
    if s.count(":") >= 2:
        return s
    return s + ":00"


def index_columns(entity_id: str, columns: list[dict]) -> None:
    """Batch index column documents"""
    if not columns:
        return
    es = get_es_client()
    actions = [
        {
            "_index": COLUMNS_INDEX,
            "_id": f"{entity_id}.{col['name']}",
            "_source": {
                "column_id": f"{entity_id}.{col['name']}",
                "entity_id": entity_id,
                "column_name": col["name"],
                "data_type": col.get("type", ""),
                "original_description": col.get("origDesc", ""),
                "original_tags": [t for t in col.get("origTag", "").split(",") if t.strip()] if col.get("origTag") else [],
                "completion_description": col.get("compDesc", ""),
                "completion_tags": [t for t in col.get("compTag", "").split(",") if t.strip()] if col.get("compTag") else [],
                "completion_time": _normalize_datetime(col.get("compTime")),
            },
        }
        for col in columns
    ]
    success, errors = helpers.bulk(es, actions, raise_on_error=False)
    if errors:
        logger.warning(f"ES columns bulk index: {success} ok, {len(errors)} errors")


def get_columns(entity_id: str, size: int = 500) -> list[dict]:
    """Get all columns for a given entity"""
    es = get_es_client()
    body = {
        "query": {"term": {"entity_id": entity_id}},
        "size": size,
        "sort": [{"column_name.raw": "asc"}],
    }
    resp = es.search(index=COLUMNS_INDEX, body=body)
    return [hit["_source"] for hit in resp["hits"]["hits"]]


def get_asset_by_id(entity_id: str) -> dict | None:
    """Get asset info by exact entity_id from metadata_index"""
    es = get_es_client()
    try:
        resp = es.get(index=INDEX_NAME, id=entity_id)
        return resp["_source"]
    except NotFoundError:
        return None


def set_sample_flag(entity_ids: list[str], is_sample: bool) -> int:
    """批量设置/取消样本标记，返回更新数"""
    if not entity_ids:
        return 0
    es = get_es_client()
    resp = es.update_by_query(
        index=INDEX_NAME,
        body={
            "query": {"terms": {"entity_id": entity_ids}},
            "script": {
                "source": f"ctx._source.is_sample = {'true' if is_sample else 'false'}"
            },
        },
        refresh=True,
    )
    return resp.get("updated", 0)


def get_samples() -> list[dict]:
    """获取全部样本"""
    es = get_es_client()
    resp = es.search(
        index=INDEX_NAME,
        body={
            "query": {"term": {"is_sample": True}},
            "size": 1000,
        },
    )
    return [hit["_source"] for hit in resp["hits"]["hits"]]
