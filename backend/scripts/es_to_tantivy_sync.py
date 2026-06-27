"""从 ES 同步数据到 Tantivy — 清除本地 Tantivy 数据后全量导入"""
import json
import shutil
import sys
from pathlib import Path

from elasticsearch import Elasticsearch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.services.search_index import (
    _ensure_data_dir,
    _get_tantivy_index,
    _get_tantivy_columns_index,
    _tantivy_index_docs,
    _scan_all_docs,
)

settings = get_settings()

ES_INDEX = "metadata_index"
ES_COLUMNS_INDEX = "metadata_columns"
SCROLL_SIZE = 1000
SCROLL_KEEPALIVE = "2m"


def clean_tantivy() -> None:
    root = _ensure_data_dir()
    for sub in ("metadata", "columns"):
        p = root / sub
        if p.exists():
            shutil.rmtree(p)
            print(f"[CLEAN] removed {p}")


def scroll_all(es: Elasticsearch, index: str) -> list[dict]:
    """Scroll all documents from an ES index, returning _source dicts."""
    docs: list[dict] = []
    resp = es.search(
        index=index,
        body={"query": {"match_all": {}}, "size": SCROLL_SIZE},
        scroll=SCROLL_KEEPALIVE,
    )
    scroll_id = resp.get("_scroll_id")
    hits = resp["hits"]["hits"]
    docs.extend(h["_source"] for h in hits)

    while hits:
        resp = es.scroll(scroll_id=scroll_id, scroll=SCROLL_KEEPALIVE)
        scroll_id = resp.get("_scroll_id")
        hits = resp["hits"]["hits"]
        docs.extend(h["_source"] for h in hits)

    if scroll_id:
        es.clear_scroll(scroll_id=scroll_id)

    return docs


def index_columns_flat(docs: list[dict]) -> None:
    """Index column documents directly into Tantivy columns index."""
    import tantivy
    index = _get_tantivy_columns_index()
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


def count_docs(index) -> int:
    index.reload()
    searcher = index.searcher()
    return sum(1 for _ in _scan_all_docs(index, searcher))


def main() -> None:
    es = Elasticsearch(
        settings.es_host,
        basic_auth=(settings.es_user, settings.es_password),
    )

    if not es.ping():
        print(f"[ERROR] Cannot connect to ES at {settings.es_host}")
        sys.exit(1)
    print(f"[ES] connected to {settings.es_host}")

    # 1. Clean Tantivy data
    clean_tantivy()

    # Force re-init (creates fresh empty indexes)
    import app.services.search_index as si
    si._tantivy_index = None
    si._tantivy_columns_index = None

    # 2. Sync metadata_index
    print(f"[ES] scrolling {ES_INDEX} ...")
    main_docs = scroll_all(es, ES_INDEX)
    print(f"[ES] fetched {len(main_docs)} docs from {ES_INDEX}")

    if main_docs:
        _tantivy_index_docs(main_docs)
        print(f"[TANTIVY] indexed {len(main_docs)} docs into metadata_index")

    # 3. Sync metadata_columns
    print(f"[ES] scrolling {ES_COLUMNS_INDEX} ...")
    columns_docs = scroll_all(es, ES_COLUMNS_INDEX)
    print(f"[ES] fetched {len(columns_docs)} docs from {ES_COLUMNS_INDEX}")

    if columns_docs:
        index_columns_flat(columns_docs)
        print(f"[TANTIVY] indexed {len(columns_docs)} docs into metadata_columns")

    # Verify
    print(f"[VERIFY] main index: {count_docs(_get_tantivy_index())} docs")
    print(f"[VERIFY] columns index: {count_docs(_get_tantivy_columns_index())} docs")

    print("[DONE] ES → Tantivy sync complete")


if __name__ == "__main__":
    main()
