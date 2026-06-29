# 嵌入式依赖替换 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 7 个基础设施容器（PostgreSQL、Milvus+etcd+MinIO、ES、Redis）替换为嵌入式方案（SQLite、ChromaDB、Tantivy+jieba、SQLite broker），实现零外部容器即开即用。

**Architecture:** 新建 `vector_store.py` 和 `search_index.py` 两个 dispatch 模块，嵌入模式下用 ChromaDB/Tantivy，生产模式委托给原有 milvus.py/elasticsearch.py。所有调用方只改 import 路径，不改业务逻辑。

**Tech Stack:** ChromaDB ≥ 0.5、Tantivy ≥ 0.22、jieba ≥ 0.42、SQLite（已内置）

## Global Constraints

- `DEPLOYMENT_MODE=embedded` 默认启用嵌入式方案
- `DEPLOYMENT_MODE=production` 切回 Milvus + ES + Redis
- 公共 API 签名与现有 milvus.py / elasticsearch.py 完全一致
- 前端代码零改动
- Python 3.12+，type annotations 必填

---

### Task 1: 更新配置和依赖

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Consumes: 无
- Produces: `Settings.DEPLOYMENT_MODE`, `Settings.vector_store_backend`, `Settings.search_index_backend`, `Settings.celery_broker_url` → 各 service 模块使用

- [ ] **Step 1: 更新 config.py**

```python
"""应用配置管理"""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # 应用
    app_name: str = "metadata-completion"
    debug: bool = False
    DEPLOYMENT_MODE: Literal["embedded", "production"] = "embedded"
    database_url: str = "sqlite+aiosqlite:///data/metadata.db"

    # 阿里云百炼
    dashscope_api_key: str = "sk-a4663f488db84585aff4f9b0e28d767d"

    # Milvus (仅 production 模式使用)
    milvus_host: str = "172.17.5.229"
    milvus_port: int = 19530

    # Elasticsearch (仅 production 模式使用)
    es_host: str = "http://172.17.5.238:9220"
    es_user: str = "elastic"
    es_password: str = "Bonc@1234"

    # OpenMetadata
    om_base_url: str = "http://localhost:8585/api"
    om_jwt_token: str = ""

    # Redis (仅 production 模式使用)
    redis_url: str = "redis://:Bonc%401234@172.17.5.230:6379/0"

    # Celery — 根据模式自动选择 broker
    celery_broker_url: str = "sqla+sqlite:///data/celery.db"
    celery_result_backend: str = "db+sqlite:///data/celery.db"

    # 质量校验阈值
    auto_approve_threshold: float = 0.80
    pending_review_threshold: float = 0.60

    @property
    def vector_store_backend(self) -> str:
        return "chroma" if self.DEPLOYMENT_MODE == "embedded" else "milvus"

    @property
    def search_index_backend(self) -> str:
        return "tantivy" if self.DEPLOYMENT_MODE == "embedded" else "elasticsearch"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2: 更新 requirements.txt**

```txt
langchain>=0.3.0
langgraph>=0.2.0
langchain-community>=0.3.0
dashscope>=1.20.0
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
chromadb>=0.5.0
tantivy>=0.22.0
jieba>=0.42.0
sqlalchemy>=2.0.0
alembic>=1.13.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
httpx>=0.27.0
celery>=5.4.0
python-dotenv>=1.0.0
aiosqlite>=0.20.0
asyncpg>=0.30.0
psycopg2-binary>=2.9.0
greenlet>=3.0.0
```

- [ ] **Step 3: 安装新依赖**

```bash
cd backend && source .venv/bin/activate && pip install chromadb tantivy jieba
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/config.py backend/requirements.txt
git commit -m "feat: add DEPLOYMENT_MODE config and embedded dependencies"
```

---

### Task 2: 创建 ChromaDB 向量存储

**Files:**
- Create: `backend/app/services/vector_store.py`

**Interfaces:**
- Consumes: `app.config.get_settings()` → vector_store_backend
- Produces: `search_similar(embedding, entity_type, top_k, database) -> list[dict]`, `insert_embeddings(records) -> None`, `delete_by_entity_ids(entity_ids) -> None`

- [ ] **Step 1: 创建 vector_store.py**

```python
"""向量存储 — 嵌入模式 ChromaDB / 生产模式 Milvus"""
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

COLLECTION_NAME = "metadata_embeddings"


def _get_chroma_collection():
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    client = chromadb.PersistentClient(
        path="data/chroma",
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


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
    where = {"entity_type": entity_type, "has_description": True}
    if database:
        where["database"] = database

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
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/vector_store.py
git commit -m "feat: add vector_store dispatch (ChromaDB embedded / Milvus production)"
```

---

### Task 3: 创建 Tantivy 搜索索引

**Files:**
- Create: `backend/app/services/search_index.py`

**Interfaces:**
- Consumes: `app.config.get_settings()` → search_index_backend
- Produces: `search_keyword(...)`, `search_siblings(...)`, `search_all(...)`, `get_filter_options(...)`, `index_documents(...)`, `get_asset_by_id(...)`, `get_columns(...)`, `index_columns(...)`, `set_sample_flag(...)`, `get_samples(...)`, `update_completed_metadata(...)`, `reset_completion_status(...)`, `update_completed_columns(...)`, `search_reference(...)`, `ensure_index()`, `ensure_columns_index()`, `INDEX_NAME`, `COLUMNS_INDEX`

- [ ] **Step 1: 创建 search_index.py**

```python
"""搜索索引 — 嵌入模式 Tantivy / 生产模式 Elasticsearch"""
import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

INDEX_NAME = "metadata_index"
COLUMNS_INDEX = "metadata_columns"

_tantivy_index: "tantivy.Index | None" = None
_tantivy_columns_index: "tantivy.Index | None" = None
_jieba_registered: bool = False


def _ensure_data_dir() -> Path:
    p = Path("data/tantivy")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _register_jieba():
    global _jieba_registered
    if _jieba_registered:
        return
    import jieba
    import tantivy
    try:
        tantivy.tokenizer.register("jieba", lambda text: list(jieba.cut(text)))
    except ValueError:
        pass
    _jieba_registered = True


def _build_main_schema() -> "tantivy.Schema":
    import tantivy
    _register_jieba()
    sb = tantivy.SchemaBuilder()
    sb.add_text_field("entity_id", stored=True)
    sb.add_text_field("entity_type", stored=True)
    sb.add_text_field("database", stored=True)
    sb.add_text_field("schema_name", stored=True)
    sb.add_text_field("table_name", stored=True)
    sb.add_text_field("column_name", stored=True)
    sb.add_text_field("display_name", stored=True, tokenizer_name="jieba")
    sb.add_text_field("description", stored=True, tokenizer_name="jieba")
    sb.add_text_field("data_type", stored=True)
    sb.add_text_field("db_type", stored=True)
    sb.add_text_field("tags", stored=True)
    sb.add_text_field("search_text", stored=True)
    sb.add_text_field("has_description", stored=True)
    sb.add_text_field("completion_status", stored=True)
    sb.add_text_field("completion_time", stored=True)
    sb.add_text_field("updated_time", stored=True)
    sb.add_text_field("is_sample", stored=True)
    sb.add_text_field("system", stored=True)
    sb.add_text_field("schema", stored=True)
    return sb.build()


def _build_columns_schema() -> "tantivy.Schema":
    import tantivy
    sb = tantivy.SchemaBuilder()
    sb.add_text_field("column_id", stored=True)
    sb.add_text_field("entity_id", stored=True)
    sb.add_text_field("column_name", stored=True)
    sb.add_text_field("data_type", stored=True)
    sb.add_text_field("original_description", stored=True, tokenizer_name="jieba")
    sb.add_text_field("original_tags", stored=True)
    sb.add_text_field("completion_description", stored=True, tokenizer_name="jieba")
    sb.add_text_field("completion_tags", stored=True)
    sb.add_text_field("completion_time", stored=True)
    return sb.build()


def _get_tantivy_index():
    global _tantivy_index
    if _tantivy_index is None:
        import tantivy
        schema = _build_main_schema()
        index_path = str(_ensure_data_dir() / "metadata")
        _tantivy_index = tantivy.Index(schema, path=index_path)
    return _tantivy_index


def _get_tantivy_columns_index():
    global _tantivy_columns_index
    if _tantivy_columns_index is None:
        import tantivy
        schema = _build_columns_schema()
        index_path = str(_ensure_data_dir() / "columns")
        _tantivy_columns_index = tantivy.Index(schema, path=index_path)
    return _tantivy_columns_index


def _hit_to_dict(hit) -> dict:
    doc = hit[1] if isinstance(hit, tuple) else hit
    return dict(doc) if hasattr(doc, "__iter__") and not isinstance(doc, (str, bytes)) else {}


def _doc_to_dict(doc) -> dict:
    return dict(doc) if hasattr(doc, "__iter__") and not isinstance(doc, (str, bytes)) else {}


def _field_first(doc: dict, key: str, default: str = "") -> str:
    val = doc.get(key, default)
    if isinstance(val, list):
        return str(val[0]) if val else default
    return str(val) if val is not None else default


def _parse_tags(val) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        if len(val) > 0 and isinstance(val[0], str):
            return val
        return [str(v) for v in val[:1]]
    s = str(val)
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return [s] if s else []


# ---------- 公开接口 ----------

def ensure_index() -> None:
    if settings.search_index_backend == "tantivy":
        _get_tantivy_index()
    else:
        from app.services.elasticsearch import ensure_index as _es_ensure
        _es_ensure()


def ensure_columns_index() -> None:
    if settings.search_index_backend == "tantivy":
        _get_tantivy_columns_index()
    else:
        from app.services.elasticsearch import ensure_columns_index as _es_ensure
        _es_ensure()


def search_keyword(
    query_text: str,
    entity_type: str,
    database: str | None = None,
    schema_name: str | None = None,
    top_k: int = 20,
) -> list[dict]:
    if settings.search_index_backend == "tantivy":
        return _tantivy_search_keyword(query_text, entity_type, database, schema_name, top_k)
    else:
        from app.services.elasticsearch import search_keyword as _es_search
        return _es_search(query_text, entity_type, database, schema_name, top_k)


def _tantivy_search_keyword(
    query_text: str,
    entity_type: str,
    database: str | None = None,
    schema_name: str | None = None,
    top_k: int = 20,
) -> list[dict]:
    import tantivy
    index = _get_tantivy_index()
    index.reload()
    searcher = index.searcher()

    try:
        query = index.parse_query(query_text, ["table_name", "column_name", "display_name", "description"])
    except Exception:
        return []

    results = searcher.search(query, top_k)
    hits = results.hits if hasattr(results, "hits") else results

    output = []
    for hit in hits[:top_k]:
        doc = _hit_to_dict(hit)
        etype_val = _field_first(doc, "entity_type")
        if etype_val != entity_type:
            continue
        has_desc_val = _field_first(doc, "has_description")
        if has_desc_val.lower() not in ("true", "1"):
            continue
        if database:
            db_val = _field_first(doc, "database")
            if db_val != database:
                continue
        if schema_name:
            sn_val = _field_first(doc, "schema_name")
            if sn_val != schema_name:
                continue

        score = hit[0] if isinstance(hit, tuple) else 1.0
        output.append({
            "entity_id": _field_first(doc, "entity_id"),
            "entity_type": _field_first(doc, "entity_type"),
            "database": _field_first(doc, "database"),
            "schema_name": _field_first(doc, "schema_name"),
            "table_name": _field_first(doc, "table_name"),
            "column_name": _field_first(doc, "column_name"),
            "data_type": _field_first(doc, "data_type"),
            "search_text": _field_first(doc, "search_text"),
            "score": float(score),
            "source": "tantivy",
        })
    return output


def search_siblings(
    database: str, schema_name: str, entity_type: str, top_k: int = 5
) -> list[dict]:
    if settings.search_index_backend == "tantivy":
        return _tantivy_search_siblings(database, schema_name, entity_type, top_k)
    else:
        from app.services.elasticsearch import search_siblings as _es_siblings
        return _es_siblings(database, schema_name, entity_type, top_k)


def _tantivy_search_siblings(
    database: str, schema_name: str, entity_type: str, top_k: int = 5
) -> list[dict]:
    index = _get_tantivy_index()
    index.reload()
    searcher = index.searcher()
    output = []
    for doc_addr in range(searcher.num_docs):
        try:
            doc = _doc_to_dict(searcher.doc(doc_addr))
        except Exception:
            continue
        if _field_first(doc, "database") != database:
            continue
        if _field_first(doc, "schema_name") != schema_name:
            continue
        if _field_first(doc, "entity_type") != entity_type:
            continue
        output.append({
            "entity_id": _field_first(doc, "entity_id"),
            "table_name": _field_first(doc, "table_name"),
            "column_name": _field_first(doc, "column_name"),
            "display_name": _field_first(doc, "display_name"),
            "description": _field_first(doc, "description"),
        })
        if len(output) >= top_k:
            break
    return output


def search_all(
    query_text: str,
    entity_type: str | None = None,
    database: str | None = None,
    schema_name: str | None = None,
    data_type: str | None = None,
    db_type: str | None = None,
    is_sample: bool | None = None,
    sort_by: str | None = None,
    sort_desc: bool = False,
    top_k: int = 200,
) -> list[dict]:
    if settings.search_index_backend == "tantivy":
        return _tantivy_search_all(
            query_text, entity_type, database, schema_name,
            data_type, db_type, is_sample, sort_by, sort_desc, top_k,
        )
    else:
        from app.services.elasticsearch import search_all as _es_search_all
        return _es_search_all(
            query_text, entity_type, database, schema_name,
            data_type, db_type, is_sample, sort_by, sort_desc, top_k,
        )


def _tantivy_search_all(
    query_text: str,
    entity_type: str | None = None,
    database: str | None = None,
    schema_name: str | None = None,
    data_type: str | None = None,
    db_type: str | None = None,
    is_sample: bool | None = None,
    sort_by: str | None = None,
    sort_desc: bool = False,
    top_k: int = 200,
) -> list[dict]:
    import tantivy
    index = _get_tantivy_index()
    index.reload()
    searcher = index.searcher()

    has_query = bool(query_text.strip())
    has_filters = bool(entity_type or database or schema_name or data_type or db_type or is_sample is not None)

    results: list[dict] = []

    if has_query:
        try:
            query = index.parse_query(query_text, ["table_name", "column_name", "display_name", "description"])
        except Exception:
            query = None
        if query:
            hits = searcher.search(query, min(top_k * 3, 2000))
            raw_hits = hits.hits if hasattr(hits, "hits") else hits
        else:
            raw_hits = []
    else:
        raw_hits = [(0.0, searcher.doc(i)) for i in range(min(searcher.num_docs, top_k * 3))]

    for hit in raw_hits:
        doc = _hit_to_dict(hit)
        if entity_type and _field_first(doc, "entity_type") != entity_type:
            continue
        if database and _field_first(doc, "database") != database:
            continue
        if schema_name and _field_first(doc, "schema_name") != schema_name:
            continue
        if data_type and _field_first(doc, "data_type") != data_type:
            continue
        if db_type and _field_first(doc, "db_type") != db_type:
            continue
        if is_sample is True:
            sample_val = _field_first(doc, "is_sample", "false")
            if sample_val.lower() not in ("true", "1"):
                continue
        elif is_sample is False:
            sample_val = _field_first(doc, "is_sample", "false")
            if sample_val.lower() in ("true", "1"):
                continue

        score = hit[0] if isinstance(hit, tuple) else 1.0
        item = {
            "entity_id": _field_first(doc, "entity_id"),
            "entity_type": _field_first(doc, "entity_type"),
            "database": _field_first(doc, "database"),
            "schema_name": _field_first(doc, "schema_name"),
            "schema": _field_first(doc, "schema_name"),
            "table_name": _field_first(doc, "table_name"),
            "column_name": _field_first(doc, "column_name"),
            "display_name": _field_first(doc, "display_name"),
            "description": _field_first(doc, "description"),
            "data_type": _field_first(doc, "data_type"),
            "db_type": _field_first(doc, "db_type"),
            "tags": _parse_tags(doc.get("tags")),
            "has_description": _field_first(doc, "has_description"),
            "completion_status": _field_first(doc, "completion_status"),
            "completion_time": _field_first(doc, "completion_time"),
            "updated_time": _field_first(doc, "updated_time"),
            "is_sample": _field_first(doc, "is_sample"),
            "system": _field_first(doc, "system"),
            "score": float(score),
            "highlight": {},
        }
        results.append(item)
        if len(results) >= top_k:
            break

    _SORT_MAP = {
        "name": "table_name",
        "system": "system",
        "database": "database",
        "schema": "schema_name",
        "entity_type": "entity_type",
        "completion_status": "completion_status",
        "updated_time": "updated_time",
    }
    sort_field = _SORT_MAP.get(sort_by, "updated_time")
    reverse = sort_desc if sort_by else True

    def _sort_key(item):
        val = item.get(sort_field, "")
        if sort_field == "updated_time":
            return val or ""
        return (val or "").lower()

    results.sort(key=_sort_key, reverse=reverse)

    # Default multi-level sort tiebreakers: system then name
    if sort_by != "system":
        results.sort(key=lambda x: (x.get("system") or "").lower())
    if sort_by != "name":
        results.sort(key=lambda x: (x.get("table_name") or "").lower())

    return results[:top_k]


def get_filter_options() -> dict[str, list[str]]:
    if settings.search_index_backend == "tantivy":
        return _tantivy_filter_options()
    else:
        from app.services.elasticsearch import get_filter_options as _es_filters
        return _es_filters()


def _tantivy_filter_options() -> dict[str, list[str]]:
    index = _get_tantivy_index()
    index.reload()
    searcher = index.searcher()
    systems = set()
    databases = set()
    schemas = set()
    db_types = set()
    for i in range(searcher.num_docs):
        try:
            doc = _doc_to_dict(searcher.doc(i))
        except Exception:
            continue
        sys_val = _field_first(doc, "system")
        if sys_val:
            systems.add(sys_val)
        db_val = _field_first(doc, "database")
        if db_val:
            databases.add(db_val)
        sch_val = _field_first(doc, "schema_name")
        if sch_val:
            schemas.add(sch_val)
        dt_val = _field_first(doc, "db_type")
        if dt_val:
            db_types.add(dt_val)
    return {
        "systems": sorted(systems),
        "databases": sorted(databases),
        "schemas": sorted(schemas),
        "db_types": sorted(db_types),
    }


def index_documents(docs: list[dict]) -> None:
    if not docs:
        return
    if settings.search_index_backend == "tantivy":
        _tantivy_index_docs(docs)
    else:
        from app.services.elasticsearch import index_documents as _es_index
        _es_index(docs)


def _tantivy_index_docs(docs: list[dict]) -> None:
    import tantivy
    index = _get_tantivy_index()
    writer = index.writer(50_000_000, 1)
    for doc in docs:
        td = tantivy.Document()
        for key, value in doc.items():
            if isinstance(value, list):
                value = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, bool):
                value = "true" if value else "false"
            elif value is None:
                value = ""
            else:
                value = str(value)
            try:
                td.add_text(key, value)
            except Exception:
                pass
        try:
            writer.add_document(td)
        except Exception:
            pass
    writer.commit()


def get_asset_by_id(entity_id: str) -> dict | None:
    if settings.search_index_backend == "tantivy":
        return _tantivy_get_by_id(entity_id)
    else:
        from app.services.elasticsearch import get_asset_by_id as _es_get
        return _es_get(entity_id)


def _tantivy_get_by_id(entity_id: str) -> dict | None:
    index = _get_tantivy_index()
    index.reload()
    searcher = index.searcher()
    for i in range(searcher.num_docs):
        try:
            doc = _doc_to_dict(searcher.doc(i))
        except Exception:
            continue
        if _field_first(doc, "entity_id") == entity_id:
            return {
                "entity_id": _field_first(doc, "entity_id"),
                "entity_type": _field_first(doc, "entity_type"),
                "database": _field_first(doc, "database"),
                "schema_name": _field_first(doc, "schema_name"),
                "schema": _field_first(doc, "schema_name"),
                "table_name": _field_first(doc, "table_name"),
                "column_name": _field_first(doc, "column_name"),
                "display_name": _field_first(doc, "display_name"),
                "description": _field_first(doc, "description"),
                "data_type": _field_first(doc, "data_type"),
                "db_type": _field_first(doc, "db_type"),
                "tags": _parse_tags(doc.get("tags")),
                "has_description": _field_first(doc, "has_description"),
                "completion_status": _field_first(doc, "completion_status"),
                "completion_time": _field_first(doc, "completion_time"),
                "updated_time": _field_first(doc, "updated_time"),
                "is_sample": _field_first(doc, "is_sample"),
                "system": _field_first(doc, "system"),
            }
    return None


def get_columns(entity_id: str, size: int = 500) -> list[dict]:
    if settings.search_index_backend == "tantivy":
        return _tantivy_get_columns(entity_id, size)
    else:
        from app.services.elasticsearch import get_columns as _es_cols
        return _es_cols(entity_id, size)


def _tantivy_get_columns(entity_id: str, size: int = 500) -> list[dict]:
    index = _get_tantivy_columns_index()
    index.reload()
    searcher = index.searcher()
    results = []
    for i in range(searcher.num_docs):
        try:
            doc = _doc_to_dict(searcher.doc(i))
        except Exception:
            continue
        if _field_first(doc, "entity_id") == entity_id:
            results.append({
                "column_id": _field_first(doc, "column_id"),
                "entity_id": _field_first(doc, "entity_id"),
                "column_name": _field_first(doc, "column_name"),
                "data_type": _field_first(doc, "data_type"),
                "original_description": _field_first(doc, "original_description"),
                "original_tags": _field_first(doc, "original_tags"),
                "completion_description": _field_first(doc, "completion_description"),
                "completion_tags": _field_first(doc, "completion_tags"),
                "completion_time": _field_first(doc, "completion_time"),
            })
            if len(results) >= size:
                break
    results.sort(key=lambda x: x.get("column_name", ""))
    return results


def index_columns(entity_id: str, columns: list[dict]) -> None:
    if not columns:
        return
    if settings.search_index_backend == "tantivy":
        _tantivy_index_columns(entity_id, columns)
    else:
        from app.services.elasticsearch import index_columns as _es_idx_cols
        _es_idx_cols(entity_id, columns)


def _tantivy_index_columns(entity_id: str, columns: list[dict]) -> None:
    import tantivy
    index = _get_tantivy_columns_index()
    writer = index.writer(50_000_000, 1)
    for col in columns:
        td = tantivy.Document()
        td.add_text("column_id", f"{entity_id}.{col['name']}")
        td.add_text("entity_id", entity_id)
        td.add_text("column_name", col.get("name", ""))
        td.add_text("data_type", col.get("type", ""))
        td.add_text("original_description", col.get("origDesc", ""))
        td.add_text("original_tags", col.get("origTag", ""))
        td.add_text("completion_description", col.get("compDesc", ""))
        td.add_text("completion_tags", col.get("compTag", ""))
        td.add_text("completion_time", col.get("compTime", ""))
        writer.add_document(td)
    writer.commit()


def set_sample_flag(entity_ids: list[str], is_sample: bool) -> int:
    if not entity_ids:
        return 0
    if settings.search_index_backend == "tantivy":
        return _tantivy_set_sample(entity_ids, is_sample)
    else:
        from app.services.elasticsearch import set_sample_flag as _es_sample
        return _es_sample(entity_ids, is_sample)


def _tantivy_set_sample(entity_ids: list[str], is_sample: bool) -> int:
    import tantivy
    index = _get_tantivy_index()
    index.reload()
    searcher = index.searcher()
    writer = index.writer(50_000_000, 1)
    count = 0
    for i in range(searcher.num_docs):
        try:
            doc_dict = _doc_to_dict(searcher.doc(i))
        except Exception:
            continue
        eid = _field_first(doc_dict, "entity_id")
        td = tantivy.Document()
        for key, value in doc_dict.items():
            if isinstance(value, list):
                value = str(value[0]) if value else ""
            else:
                value = str(value) if value is not None else ""
            if key == "is_sample" and eid in entity_ids:
                value = "true" if is_sample else "false"
                count += 1
            td.add_text(key, value)
        writer.add_document(td)
    writer.commit()
    return count


def get_samples() -> list[dict]:
    if settings.search_index_backend == "tantivy":
        return _tantivy_get_samples()
    else:
        from app.services.elasticsearch import get_samples as _es_samples
        return _es_samples()


def _tantivy_get_samples() -> list[dict]:
    index = _get_tantivy_index()
    index.reload()
    searcher = index.searcher()
    results = []
    for i in range(searcher.num_docs):
        try:
            doc = _doc_to_dict(searcher.doc(i))
        except Exception:
            continue
        sample_val = _field_first(doc, "is_sample", "false")
        if sample_val.lower() not in ("true", "1"):
            continue
        results.append({
            "entity_id": _field_first(doc, "entity_id"),
            "entity_type": _field_first(doc, "entity_type"),
            "database": _field_first(doc, "database"),
            "schema_name": _field_first(doc, "schema_name"),
            "table_name": _field_first(doc, "table_name"),
            "column_name": _field_first(doc, "column_name"),
            "display_name": _field_first(doc, "display_name"),
            "description": _field_first(doc, "description"),
            "data_type": _field_first(doc, "data_type"),
            "db_type": _field_first(doc, "db_type"),
            "tags": _parse_tags(doc.get("tags")),
            "has_description": _field_first(doc, "has_description"),
            "completion_status": _field_first(doc, "completion_status"),
            "completion_time": _field_first(doc, "completion_time"),
            "updated_time": _field_first(doc, "updated_time"),
            "is_sample": _field_first(doc, "is_sample"),
            "system": _field_first(doc, "system"),
        })
        if len(results) >= 1000:
            break
    return results


def update_completed_metadata(entity_id: str, completion_result: dict) -> bool:
    if settings.search_index_backend == "tantivy":
        return _tantivy_update_completed(entity_id, completion_result)
    else:
        from app.services.elasticsearch import update_completed_metadata as _es_upd
        return _es_upd(entity_id, completion_result)


def _tantivy_update_completed(entity_id: str, completion_result: dict) -> bool:
    import tantivy
    index = _get_tantivy_index()
    index.reload()
    searcher = index.searcher()
    writer = index.writer(50_000_000, 1)
    now = datetime.now(timezone.utc).isoformat()
    updated = False
    for i in range(searcher.num_docs):
        try:
            doc_dict = _doc_to_dict(searcher.doc(i))
        except Exception:
            continue
        eid = _field_first(doc_dict, "entity_id")
        td = tantivy.Document()
        for key, value in doc_dict.items():
            if isinstance(value, list):
                value = str(value[0]) if value else ""
            else:
                value = str(value) if value is not None else ""
            if eid == entity_id:
                if key == "display_name":
                    value = completion_result.get("display_name", "")
                elif key == "description":
                    value = completion_result.get("description", "")
                elif key == "tags":
                    value = json.dumps(completion_result.get("tags", []), ensure_ascii=False)
                elif key == "has_description":
                    value = "true"
                elif key == "completion_status":
                    value = "completed"
                elif key == "completion_time":
                    value = now
                elif key == "updated_time":
                    value = now
                updated = True
            td.add_text(key, value)
        writer.add_document(td)
    writer.commit()
    return updated


def reset_completion_status(entity_id: str) -> bool:
    if settings.search_index_backend == "tantivy":
        return _tantivy_reset_status(entity_id)
    else:
        from app.services.elasticsearch import reset_completion_status as _es_reset
        return _es_reset(entity_id)


def _tantivy_reset_status(entity_id: str) -> bool:
    import tantivy
    index = _get_tantivy_index()
    index.reload()
    searcher = index.searcher()
    writer = index.writer(50_000_000, 1)
    now = datetime.now(timezone.utc).isoformat()
    updated = False
    for i in range(searcher.num_docs):
        try:
            doc_dict = _doc_to_dict(searcher.doc(i))
        except Exception:
            continue
        eid = _field_first(doc_dict, "entity_id")
        td = tantivy.Document()
        for key, value in doc_dict.items():
            if isinstance(value, list):
                value = str(value[0]) if value else ""
            else:
                value = str(value) if value is not None else ""
            if eid == entity_id:
                if key == "completion_status":
                    value = "pending"
                elif key == "updated_time":
                    value = now
                updated = True
            td.add_text(key, value)
        writer.add_document(td)
    writer.commit()
    return updated


def update_completed_columns(entity_id: str, columns_data: list[dict]) -> int:
    if not columns_data:
        return 0
    if settings.search_index_backend == "tantivy":
        return _tantivy_update_columns(entity_id, columns_data)
    else:
        from app.services.elasticsearch import update_completed_columns as _es_upd_cols
        return _es_upd_cols(entity_id, columns_data)


def _tantivy_update_columns(entity_id: str, columns_data: list[dict]) -> int:
    import tantivy
    index = _get_tantivy_columns_index()
    index.reload()
    searcher = index.searcher()
    writer = index.writer(50_000_000, 1)
    now = datetime.now(timezone.utc).isoformat()
    target_ids = {f"{entity_id}.{col['name']}" for col in columns_data}
    count = 0
    for i in range(searcher.num_docs):
        try:
            doc_dict = _doc_to_dict(searcher.doc(i))
        except Exception:
            continue
        col_id = _field_first(doc_dict, "column_id")
        td = tantivy.Document()
        for key, value in doc_dict.items():
            if isinstance(value, list):
                value = str(value[0]) if value else ""
            else:
                value = str(value) if value is not None else ""
            if col_id in target_ids:
                matching = next((c for c in columns_data if f"{entity_id}.{c['name']}" == col_id), None)
                if matching:
                    if key == "completion_description":
                        value = matching.get("description", "")
                    elif key == "completion_tags":
                        value = json.dumps(matching.get("tags", []), ensure_ascii=False)
                    elif key == "completion_time":
                        value = now
                    count += 1
            td.add_text(key, value)
        writer.add_document(td)
    writer.commit()
    return count


def search_reference(search_text: str, exclude_entity_id: str) -> list[dict]:
    """Search metadata_columns for reference (used by review API)"""
    if settings.search_index_backend == "tantivy":
        return _tantivy_search_reference(search_text, exclude_entity_id)
    else:
        from app.services.elasticsearch import get_es_client
        es = get_es_client()
        body = {
            "query": {
                "bool": {
                    "must_not": [{"term": {"entity_id": exclude_entity_id}}],
                    "should": [
                        {"match": {"completion_description": {"query": search_text, "boost": 2}}},
                        {"match": {"original_description": {"query": search_text, "boost": 1}}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            "size": 20,
            "_source": ["entity_id", "completion_description", "original_description", "column_name"],
        }
        resp = es.search(index=COLUMNS_INDEX, body=body)
        return resp["hits"]["hits"]


def _tantivy_search_reference(search_text: str, exclude_entity_id: str) -> list[dict]:
    import tantivy
    index = _get_tantivy_columns_index()
    index.reload()
    searcher = index.searcher()
    try:
        query = index.parse_query(search_text, ["completion_description", "original_description"])
    except Exception:
        return []
    hits = searcher.search(query, 40)
    raw_hits = hits.hits if hasattr(hits, "hits") else hits
    results = []
    for hit in raw_hits:
        doc = _hit_to_dict(hit)
        eid = _field_first(doc, "entity_id")
        if eid == exclude_entity_id:
            continue
        results.append({
            "_source": {
                "entity_id": eid,
                "completion_description": _field_first(doc, "completion_description"),
                "original_description": _field_first(doc, "original_description"),
                "column_name": _field_first(doc, "column_name"),
            },
        })
        if len(results) >= 20:
            break
    return results
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/search_index.py
git commit -m "feat: add search_index dispatch (Tantivy embedded / ES production)"
```

---

### Task 4: 更新 Pipeline 层 import

**Files:**
- Modify: `backend/app/pipeline/stage1_retrieve.py`

**Interfaces:**
- Consumes: `search_index.search_keyword`, `search_index.search_siblings`, `search_index.search_all`, `search_index.get_samples`, `vector_store.search_similar` (same signatures as before)
- Produces: `stage1_retrieve(state) -> CompletionState` (unchanged)

- [ ] **Step 1: 修改 stage1_retrieve.py**

Change line 4:
```python
from app.services import milvus, elasticsearch, embedding
```
to:
```python
from app.services import vector_store, search_index, embedding
```

Then update all usages:
- `milvus.search_similar` → `vector_store.search_similar`
- `elasticsearch.search_keyword` → `search_index.search_keyword`
- `elasticsearch.search_siblings` → `search_index.search_siblings`
- `elasticsearch.search_all` → `search_index.search_all`
- `elasticsearch.get_samples` → `search_index.get_samples`

- [ ] **Step 2: 提交**

```bash
git add backend/app/pipeline/stage1_retrieve.py
git commit -m "refactor: update stage1 imports to use vector_store and search_index"
```

---

### Task 5: 更新 API 层 import

**Files:**
- Modify: `backend/app/api/search.py`
- Modify: `backend/app/api/samples.py`
- Modify: `backend/app/api/assets.py`
- Modify: `backend/app/api/complete.py`
- Modify: `backend/app/api/review.py`

- [ ] **Step 1: 修改 search.py (line 3)**

```python
from app.services.search_index import search_all, get_filter_options
```

- [ ] **Step 2: 修改 samples.py (line 3)**

```python
from app.services.search_index import set_sample_flag, get_samples
```

- [ ] **Step 3: 修改 assets.py (line 2)**

```python
from app.services.search_index import get_asset_by_id, get_columns
```

- [ ] **Step 4: 修改 complete.py**

Line 11: Remove `from app.services.elasticsearch import get_es_client, INDEX_NAME`
Line 125: Change `from app.services.elasticsearch import get_columns` → `from app.services.search_index import get_columns`

Check if `get_es_client` or `INDEX_NAME` are used elsewhere in complete.py (read the file to verify, and if not used elsewhere, delete import).

- [ ] **Step 5: 修改 review.py (line 165)**

Replace the inline ES query block (lines 165-183) with:

```python
    from app.services.search_index import search_reference
    try:
        hits = search_reference(search_text, record.entity_id)
    except Exception as e:
        logger.warning(f"Failed to search reference for {record.entity_id}: {e}")
        hits = []
```

The `search_reference` return format (`_source` keys) is compatible with existing `hits` usage in review.py.

- [ ] **Step 6: 提交**

```bash
git add backend/app/api/search.py backend/app/api/samples.py backend/app/api/assets.py backend/app/api/complete.py backend/app/api/review.py
git commit -m "refactor: update API layer imports to use search_index"
```

---

### Task 6: 更新异步任务和 Celery 配置

**Files:**
- Modify: `backend/app/jobs/es_sync.py`
- Modify: `backend/app/celery_app.py`

- [ ] **Step 1: 修改 es_sync.py (line 5)**

```python
from app.services.search_index import reset_completion_status, update_completed_metadata, update_completed_columns
```

- [ ] **Step 2: 修改 celery_app.py**

Change worker_pool from `"gevent"` to `"solo"` for SQLite broker compatibility:

```python
    worker_pool="solo",
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/jobs/es_sync.py backend/app/celery_app.py
git commit -m "refactor: update celery config for embedded mode"
```

---

### Task 7: 更新 docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: 简化 docker-compose.yml**

```yaml
version: "3.8"

services:
  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DEPLOYMENT_MODE=embedded

  frontend:
    build: ./frontend
    command: npm run dev
    ports:
      - "5173:5173"
    depends_on:
      - backend

  celery-worker:
    build: ./backend
    command: celery -A app.celery_app worker -P solo --loglevel=info
    volumes:
      - ./data:/app/data
    environment:
      - DEPLOYMENT_MODE=embedded
    depends_on:
      - backend
```

- [ ] **Step 2: 提交**

```bash
git add docker-compose.yml
git commit -m "refactor: simplify docker-compose to 3 services"
```

---

### Task 8: 更新脚本 import

**Files:**
- Modify: `backend/scripts/import_columns.py`
- Modify: `backend/scripts/reset_entity_completion.py`

- [ ] **Step 1: 更新 import_columns.py (line 5)**

```python
from app.services.search_index import ensure_columns_index, index_columns, COLUMNS_INDEX
```

Remove the `get_es_client` import.

- [ ] **Step 2: 更新 reset_entity_completion.py (line 12)**

```python
from app.services.search_index import INDEX_NAME, COLUMNS_INDEX
```

- [ ] **Step 3: 提交**

```bash
git add backend/scripts/import_columns.py backend/scripts/reset_entity_completion.py
git commit -m "refactor: update script imports to use search_index"
```

---

### Task 9: 端到端验证

- [ ] **Step 1: 确保 data 目录存在**

```bash
mkdir -p data
```

- [ ] **Step 2: 启动后端**

```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
```

验证: `curl http://localhost:8000/docs` 返回 Swagger 页面

- [ ] **Step 3: 测试搜索 API**

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"用户","page":1,"page_size":20}'
```

验证: 返回 `{"success": true, "data": [...], "meta": {...}}`

- [ ] **Step 4: 测试筛选选项 API**

```bash
curl http://localhost:8000/api/v1/search/filters
```

验证: 返回 `{"success": true, "data": {"systems": [...], ...}}`

- [ ] **Step 5: 启动前端验证**

```bash
cd frontend && npm run dev
```

打开 http://localhost:5173/search，确认页面正常加载。

---

### Task 10: 最终提交

- [ ] **Step 1: 清理和提交**

```bash
git status
git add -A
git commit -m "feat: complete embedded dependencies migration

Replace Milvus+ES+Redis+PostgreSQL infrastructure with embedded
alternatives (ChromaDB+Tantivy+jieba+SQLite). Zero external containers
needed in embedded mode. DEPLOYMENT_MODE=production switches back.
"
```
