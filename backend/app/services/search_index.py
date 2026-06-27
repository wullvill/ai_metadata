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


def _ensure_data_dir() -> Path:
    p = Path("data/tantivy")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _register_cjk_tokenizer(index: "tantivy.Index") -> None:
    """Register a CJK-appropriate ngram tokenizer under the 'jieba' name on the index.

    This uses an ngram(1,3) tokenizer as an approximation of jieba segmentation
    for Chinese text. The tantivy 0.22 API supports index.register_tokenizer()
    but does not provide a native jieba implementation, so ngram is the closest
    available alternative for CJK character-level indexing.
    """
    import tantivy
    try:
        tokenizer = tantivy.Tokenizer.ngram(1, 3, False)
        builder = tantivy.TextAnalyzerBuilder(tokenizer)
        analyzer = builder.build()
        index.register_tokenizer("jieba", analyzer)
    except Exception:
        pass


def _build_main_schema() -> "tantivy.Schema":
    import tantivy
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
        index_path = _ensure_data_dir() / "metadata"
        index_path.mkdir(parents=True, exist_ok=True)
        _tantivy_index = tantivy.Index(schema, path=str(index_path))
        _register_cjk_tokenizer(_tantivy_index)
    return _tantivy_index


def _get_tantivy_columns_index():
    global _tantivy_columns_index
    if _tantivy_columns_index is None:
        import tantivy
        schema = _build_columns_schema()
        index_path = _ensure_data_dir() / "columns"
        index_path.mkdir(parents=True, exist_ok=True)
        _tantivy_columns_index = tantivy.Index(schema, path=str(index_path))
        _register_cjk_tokenizer(_tantivy_columns_index)
    return _tantivy_columns_index


def _hit_to_dict(hit, searcher=None) -> dict:
    """Convert a search hit (score, DocAddress) to a document dict."""
    doc_addr = hit[1] if isinstance(hit, tuple) else hit
    if searcher is not None:
        import tantivy
        if isinstance(doc_addr, tantivy.DocAddress):
            doc = searcher.doc(doc_addr)
            return doc.to_dict() if hasattr(doc, "to_dict") else {}
        else:
            doc = doc_addr
    else:
        doc = doc_addr
    return doc.to_dict() if hasattr(doc, "to_dict") else (dict(doc) if hasattr(doc, "__iter__") and not isinstance(doc, (str, bytes)) else {})


def _doc_to_dict(doc) -> dict:
    """Convert a tantivy.Document to a dict."""
    if doc is None:
        return {}
    return doc.to_dict() if hasattr(doc, "to_dict") else (dict(doc) if hasattr(doc, "__iter__") and not isinstance(doc, (str, bytes)) else {})


def _scan_all_docs(index, searcher, limit: int = 5000):
    """Scan all documents in the index using all_query (reliable cross-version)."""
    import tantivy
    all_q = tantivy.Query.all_query()
    results = searcher.search(all_q, limit)
    hits = results.hits if hasattr(results, "hits") else results
    for hit in hits:
        doc = _hit_to_dict(hit, searcher)
        if doc:
            yield doc


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
        doc = _hit_to_dict(hit, searcher)
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
    for doc in _scan_all_docs(index, searcher, top_k * 10):
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
        raw_hits = [(0.0, doc_dict) for doc_dict in _scan_all_docs(index, searcher, limit=top_k * 3)]

    for hit in raw_hits:
        doc = _hit_to_dict(hit, searcher) if isinstance(hit, tuple) else _doc_to_dict(hit)
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

    # Apply tiebreakers first (stable sort), then primary sort last.
    # Tiebreaker sorts must run BEFORE the primary sort so they only affect
    # items with equal primary sort keys (Python's sort is stable).
    if sort_by != "name":
        results.sort(key=lambda x: (x.get("table_name") or "").lower())
    if sort_by != "system":
        results.sort(key=lambda x: (x.get("system") or "").lower())
    results.sort(key=_sort_key, reverse=reverse)

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
    for doc in _scan_all_docs(index, searcher):
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
    for doc in _scan_all_docs(index, searcher):
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
    for doc in _scan_all_docs(index, searcher, limit=size * 2):
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
    target_set = set(entity_ids)

    # Collect ALL docs into memory, update is_sample for targets
    all_docs: list[dict] = []
    count = 0
    for doc_dict in _scan_all_docs(index, searcher):
        eid = _field_first(doc_dict, "entity_id")
        new_doc = dict(doc_dict)
        if eid in target_set:
            new_doc["is_sample"] = ["true"] if is_sample else ["false"]
            count += 1
        all_docs.append(new_doc)

    if not all_docs or count == 0:
        return 0

    # Delete all and rewrite (Tantivy doesn't support in-place update on text fields)
    writer = index.writer(50_000_000, 1)
    writer.delete_all_documents()
    for doc_dict in all_docs:
        td = tantivy.Document()
        for key, value in doc_dict.items():
            if isinstance(value, list):
                value = str(value[0]) if value else ""
            else:
                value = str(value) if value is not None else ""
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
    for doc in _scan_all_docs(index, searcher, limit=2000):
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
    for doc_dict in _scan_all_docs(index, searcher):
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
    for doc_dict in _scan_all_docs(index, searcher):
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
    for doc_dict in _scan_all_docs(index, searcher):
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
    for idx, hit in enumerate(raw_hits):
        doc = _hit_to_dict(hit, searcher)
        eid = _field_first(doc, "entity_id")
        if eid == exclude_entity_id:
            continue
        results.append({
            "_score": 20.0 - idx,
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
