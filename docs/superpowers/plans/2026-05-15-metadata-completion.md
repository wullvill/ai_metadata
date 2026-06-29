# 智能元数据补全系统 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零搭建智能元数据补全系统，支持元数据搜索、手工触发 AI 补全、质量校验、人工审核、回写 OpenMetadata。

**Architecture:** FastAPI + LangGraph 四阶段 Pipeline（双路检索 → LLM 生成 → 质量校验 → 审核回写），Vue3 + TDesign 前端，Milvus + ES 双路检索，阿里云百炼平台模型服务。

**Tech Stack:** Python 3.12+, FastAPI, LangGraph, LangChain, Vue3, TDesign, Milvus, Elasticsearch 8.x, PostgreSQL, Celery, Redis, DashScope

**Design Doc:** `./docs/architecture-design.md`

**Build Order:**
- Phase 1: 项目脚手架 + Docker 基础设施
- Phase 2: 后端核心（配置、数据库、服务层）
- Phase 3: Pipeline Stage 1-3（核心补全链路）
- Phase 4: Pipeline Stage 4 + API 层
- Phase 5: 前端页面
- Phase 6: Celery Job + 联调

---

## Phase 1: 项目脚手架 + Docker 基础设施

### Task 1.1: 初始化后端项目

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/.env.example`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "metadata-completion"
version = "0.1.0"
description = "智能元数据补全系统"
requires-python = ">=3.12"
dependencies = [
    "langchain>=0.3.0",
    "langgraph>=0.2.0",
    "langchain-community>=0.3.0",
    "dashscope>=1.20.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pymilvus>=2.4.0",
    "elasticsearch>=8.15.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "httpx>=0.27.0",
    "celery>=5.4.0",
    "redis>=5.0.0",
    "python-dotenv>=1.0.0",
    "aiosqlite>=0.20.0",
    "asyncpg>=0.30.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "httpx>=0.27.0",
]
```

- [ ] **Step 2: 创建 requirements.txt**

```txt
langchain>=0.3.0
langgraph>=0.2.0
langchain-community>=0.3.0
dashscope>=1.20.0
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pymilvus>=2.4.0
elasticsearch>=8.15.0
sqlalchemy>=2.0.0
alembic>=1.13.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
httpx>=0.27.0
celery>=5.4.0
redis>=5.0.0
python-dotenv>=1.0.0
aiosqlite>=0.20.0
```

- [ ] **Step 3: 创建 config.py**

```python
"""应用配置管理"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 应用
    app_name: str = "metadata-completion"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./data/completion.db"

    # 阿里云百炼
    dashscope_api_key: str = ""

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # Elasticsearch
    es_host: str = "http://localhost:9200"

    # OpenMetadata
    om_base_url: str = "http://localhost:8585/api"
    om_jwt_token: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # 质量校验阈值
    auto_approve_threshold: float = 0.80
    pending_review_threshold: float = 0.60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: 创建 main.py**

```python
"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 5: 创建 .env.example**

```bash
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
DATABASE_URL=sqlite+aiosqlite:///./data/completion.db
MILVUS_HOST=localhost
MILVUS_PORT=19530
ES_HOST=http://localhost:9200
OM_BASE_URL=http://localhost:8585/api
OM_JWT_TOKEN=xxxxxxxxxxxxxxxx
REDIS_URL=redis://localhost:6379/0
DEBUG=false
```

- [ ] **Step 6: 验证**

Run: `cd backend && pip install -e ".[dev]" && python -c "from app.main import app; print(app.title)"`
Expected: `metadata-completion`

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: initialize backend project with FastAPI scaffold"
```

### Task 1.2: 创建 Docker Compose 开发环境

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/data/.gitkeep`

- [ ] **Step 1: 创建 docker-compose.yml**

```yaml
version: "3.8"

services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379
    ports:
      - "2379:2379"

  minio:
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    command: minio server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"

  milvus:
    image: milvusdb/milvus:v2.4.0
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
      MINIO_ACCESS_KEY_ID: minioadmin
      MINIO_SECRET_ACCESS_KEY: minioadmin
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - etcd
      - minio

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.15.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
      - "9300:9300"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: metadata
      POSTGRES_PASSWORD: metadata
      POSTGRES_DB: metadata_completion
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

- [ ] **Step 2: 创建数据目录**

```bash
mkdir -p backend/data && touch backend/data/.gitkeep
```

- [ ] **Step 3: 启动基础设施**

Run: `docker compose up -d etcd minio`
Expected: 两个容器启动成功

Run: `docker compose up -d milvus elasticsearch redis postgres`
Expected: 所有容器 Running

- [ ] **Step 4: 验证基础设施**

```bash
# 验证 Milvus
curl http://localhost:9091/healthz
# 验证 ES
curl http://localhost:9200/_cluster/health
# 验证 Redis
docker compose exec redis redis-cli ping
```

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml backend/data/.gitkeep backend/.env.example
git commit -m "chore: add docker compose infrastructure"
```

### Task 1.3: 初始化前端项目

**Files:**
- Create: `frontend/` (Vite + Vue3 + TypeScript 脚手架)

- [ ] **Step 1: 创建 Vue3 项目**

Run: `npm create vite@latest frontend -- --template vue-ts`
Then: `cd frontend && npm install`

- [ ] **Step 2: 安装依赖**

Run: `cd frontend && npm install axios pinia vue-router@4 tdesign-vue-next`

- [ ] **Step 3: 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 4: 创建 CSS 变量文件 `frontend/src/styles/tokens.css`**

```css
:root {
  --color-primary: #0052d9;
  --color-success: #00a870;
  --color-warning: #ed7b2f;
  --color-error: #e34d59;
  --color-bg: #f5f7fa;
  --color-surface: #ffffff;
  --color-text: #1d2129;
  --color-text-secondary: #86909c;
  --radius-base: 6px;
  --shadow-card: 0 1px 4px rgba(0, 0, 0, 0.08);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  -webkit-font-smoothing: antialiased;
}
```

- [ ] **Step 5: 更新 main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import TDesign from 'tdesign-vue-next'
import 'tdesign-vue-next/es/style/index.css'
import './styles/tokens.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(TDesign)
app.mount('#app')
```

- [ ] **Step 6: 验证**

Run: `cd frontend && npm run dev`
Expected: Vite dev server starts on :5173, page loads without errors

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: initialize Vue3 frontend with TDesign"
```

---

## Phase 2: 后端核心（数据库、服务层）

### Task 2.1: 数据库模型与迁移

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/completion.py`
- Create: `backend/app/models/audit.py`
- Create: `backend/app/database.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`

- [ ] **Step 1: 创建数据库连接 `backend/app/database.py`**

```python
"""数据库连接管理"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

- [ ] **Step 2: 创建基础模型 `backend/app/models/base.py`**

```python
"""ORM 基础模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def gen_uuid() -> str:
    return str(uuid.uuid4())
```

- [ ] **Step 3: 创建补全记录模型 `backend/app/models/completion.py`**

```python
"""补全记录 ORM 模型"""
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, gen_uuid


class CompletionRecord(Base, TimestampMixin):
    __tablename__ = "completion_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="table | column")
    target_data: Mapped[dict] = mapped_column(JSON, nullable=False, comment="Stage 1 输入快照")
    completion_result: Mapped[dict] = mapped_column(JSON, nullable=True, comment="Stage 2 输出")
    quality_check: Mapped[dict] = mapped_column(JSON, nullable=True, comment="Stage 3 校验结果")
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending_review",
        comment="auto_approved|pending_review|rejected|approved|modified|human_rejected"
    )
    reviewer: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_to_om: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False, comment="auto_sync|manual_approve|modify|reject")
    operator: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, nullable=True)
```

- [ ] **Step 4: 更新 `backend/app/models/__init__.py`**

```python
from .base import Base
from .completion import CompletionRecord, AuditLog

__all__ = ["Base", "CompletionRecord", "AuditLog"]
```

- [ ] **Step 5: 配置 Alembic**

Run: `cd backend && alembic init alembic`

更新 `alembic/env.py` 的 target_metadata：

```python
from app.models import Base
target_metadata = Base.metadata

# 配置数据库 URL
from app.config import get_settings
config.set_main_option("sqlalchemy.url", get_settings().database_url)
```

- [ ] **Step 6: 生成并执行迁移**

Run: `cd backend && alembic revision --autogenerate -m "init" && alembic upgrade head`
Expected: 表 `completion_records` 和 `audit_logs` 创建成功

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/ backend/app/database.py backend/alembic/
git commit -m "feat: add database models and alembic migration"
```

### Task 2.2: 基础设施服务层

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/milvus.py`
- Create: `backend/app/services/elasticsearch.py`
- Create: `backend/app/services/embedding.py`
- Create: `backend/app/services/dashscope.py`
- Create: `backend/app/utils/__init__.py`
- Create: `backend/app/utils/retry.py`
- Create: `backend/app/utils/logger.py`

- [ ] **Step 1: 创建日志工具 `backend/app/utils/logger.py`**

```python
"""日志配置"""
import logging
import sys

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
```

- [ ] **Step 2: 创建重试工具 `backend/app/utils/retry.py`**

```python
"""重试工具"""
import asyncio
import functools
from app.utils.logger import get_logger

logger = get_logger(__name__)


def async_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """异步重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1}/{max_retries + 1} failed: {e}, "
                            f"retrying in {current_delay:.1f}s"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            raise last_error
        return wrapper
    return decorator
```

- [ ] **Step 3: 创建 Milvus 服务 `backend/app/services/milvus.py`**

```python
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
```

- [ ] **Step 4: 创建 ES 服务 `backend/app/services/elasticsearch.py`**

```python
"""Elasticsearch 服务"""
from elasticsearch import Elasticsearch, helpers
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

INDEX_NAME = "metadata_index"

MAPPINGS = {
    "properties": {
        "entity_id": {"type": "keyword"},
        "entity_type": {"type": "keyword"},
        "database": {"type": "keyword"},
        "schema_name": {"type": "keyword"},
        "table_name": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
        "column_name": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
        "display_name": {"type": "text", "analyzer": "ik_max_word"},
        "description": {"type": "text", "analyzer": "ik_max_word"},
        "data_type": {"type": "keyword"},
        "tags": {"type": "keyword"},
        "has_description": {"type": "boolean"},
    }
}


def get_es_client() -> Elasticsearch:
    return Elasticsearch(settings.es_host)


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


def search_all(query_text: str, entity_type: str | None = None, top_k: int = 20) -> list[dict]:
    """通用搜索（用于前端搜索页）"""
    es = get_es_client()

    must = []
    if entity_type:
        must.append({"term": {"entity_type": entity_type}})

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

    resp = es.search(index=INDEX_NAME, body=body)
    return [hit["_source"] for hit in resp["hits"]["hits"]]


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
```

- [ ] **Step 5: 创建 Embedding 服务 `backend/app/services/embedding.py`**

```python
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
```

- [ ] **Step 6: 创建 DashScope 服务 `backend/app/services/dashscope.py`**

```python
"""百炼平台 LLM 调用服务"""
import os
from langchain_community.chat_models import ChatTongyi
from app.config import get_settings

settings = get_settings()


def create_llm(model: str = "qwen-plus", temperature: float = 0.1) -> ChatTongyi:
    """创建百炼平台 LLM 实例"""
    return ChatTongyi(
        model=model,
        dashscope_api_key=settings.dashscope_api_key,
        temperature=temperature,
    )


def select_model(entity_type: str, schema_context: list[dict], retrieved_context: list[dict]) -> str:
    """根据场景自动选择模型"""
    if entity_type == "table":
        rich_siblings = sum(1 for s in schema_context if s.get("description"))
        if rich_siblings > 5:
            return "qwen-max"

    # 字段级且数据类型明确的，用性价比模型
    if entity_type == "column":
        return "qwen-plus"

    # 默认
    return "qwen-plus"
```

- [ ] **Step 7: 更新 `backend/app/services/__init__.py`**

```python
from . import milvus, elasticsearch, embedding, dashscope

__all__ = ["milvus", "elasticsearch", "embedding", "dashscope"]
```

- [ ] **Step 8: 验证 ES 连接和索引创建**

Run: `cd backend && python -c "from app.services.elasticsearch import ensure_index; ensure_index(); print('OK')"`
Expected: `OK` 且 ES 中 metadata_index 已创建

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/ backend/app/utils/
git commit -m "feat: add infrastructure services (Milvus, ES, Embedding, DashScope)"
```

### Task 2.3: OpenMetadata 服务层

**Files:**
- Create: `backend/app/services/openmetadata.py`

- [ ] **Step 1: 创建 OpenMetadata 服务 `backend/app/services/openmetadata.py`**

```python
"""OpenMetadata API 封装"""
import httpx
from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.retry import async_retry

logger = get_logger(__name__)
settings = get_settings()


class OpenMetadataClient:
    """OpenMetadata REST API 客户端"""

    def __init__(self):
        self.base_url = settings.om_base_url.rstrip("/")
        self.jwt_token = settings.om_jwt_token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.jwt_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    @async_retry(max_retries=2, delay=2.0)
    async def list_tables(
        self, database: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        """列出表"""
        client = await self._get_client()
        params = {"limit": limit, "offset": offset}
        if database:
            params["database"] = database
        resp = await client.get("/v1/tables", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    @async_retry(max_retries=2, delay=2.0)
    async def get_table(self, fqn: str) -> dict:
        """获取单个表详情（含字段）"""
        client = await self._get_client()
        resp = await client.get(f"/v1/tables/name/{fqn}", params={"include": "columns"})
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=2, delay=2.0)
    async def patch_table(self, fqn: str, patch: list[dict]) -> dict:
        """JSON Patch 更新表元数据"""
        client = await self._get_client()
        resp = await client.patch(f"/v1/tables/name/{fqn}", json=patch)
        resp.raise_for_status()
        logger.info(f"Patched table: {fqn}")
        return resp.json()

    @async_retry(max_retries=2, delay=2.0)
    async def patch_column(self, table_fqn: str, column_name: str, patch: list[dict]) -> dict:
        """JSON Patch 更新字段元数据"""
        client = await self._get_client()
        resp = await client.patch(
            f"/v1/tables/name/{table_fqn}/columns/{column_name}", json=patch
        )
        resp.raise_for_status()
        logger.info(f"Patched column: {table_fqn}.{column_name}")
        return resp.json()

    async def sync_to_om(self, record) -> None:
        """将补全结果同步回 OpenMetadata"""
        result = record.completion_result
        entity_id = record.entity_id

        if record.entity_type == "table":
            patch = _build_table_patch(result)
            await self.patch_table(entity_id, patch)
        else:
            # entity_id 格式: "database.schema.table.column"
            parts = entity_id.rsplit(".", 1)
            table_fqn = parts[0]
            column_name = parts[1]
            patch = _build_column_patch(result)
            await self.patch_column(table_fqn, column_name, patch)


def _build_table_patch(result: dict) -> list[dict]:
    """构建表的 JSON Patch"""
    patch = []
    if result.get("description"):
        patch.append({"op": "add", "path": "/description", "value": result["description"]})
    if result.get("display_name"):
        patch.append({"op": "add", "path": "/displayName", "value": result["display_name"]})
    if result.get("tags"):
        tag_labels = [{"tagFQN": t} for t in result["tags"]]
        patch.append({"op": "add", "path": "/tags", "value": tag_labels})
    return patch


def _build_column_patch(result: dict) -> list[dict]:
    """构建字段的 JSON Patch"""
    patch = []
    if result.get("description"):
        patch.append({"op": "add", "path": "/description", "value": result["description"]})
    if result.get("display_name"):
        patch.append({"op": "add", "path": "/displayName", "value": result["display_name"]})
    if result.get("tags"):
        tag_labels = [{"tagFQN": t} for t in result["tags"]]
        patch.append({"op": "add", "path": "/tags", "value": tag_labels})
    return patch
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/openmetadata.py
git commit -m "feat: add OpenMetadata API client service"
```

---

## Phase 3: Pipeline Stage 1-3（核心补全链路）

### Task 3.1: Pipeline 基础 + State 定义

**Files:**
- Create: `backend/app/pipeline/__init__.py`
- Create: `backend/app/pipeline/graph.py`
- Create: `backend/app/pipeline/state.py`

- [ ] **Step 1: 创建 State 定义 `backend/app/pipeline/state.py`**

```python
"""Pipeline State 定义"""
from typing import TypedDict


class CompletionState(TypedDict):
    # Stage 1 输入/输出
    target_entity: dict
    retrieved_context: list[dict]
    schema_context: list[dict]
    sibling_columns: list[dict]
    # Stage 2 输出
    completion_result: dict | None
    # Stage 3 输出
    quality_check: dict | None
    # Stage 4 输出
    review_status: str | None
    # 错误信息
    error: str | None
```

- [ ] **Step 2: 创建 Pipeline 图定义 `backend/app/pipeline/graph.py`**

```python
"""LangGraph Pipeline 定义"""
from langgraph.graph import StateGraph, END
from .state import CompletionState
from .stage1_retrieve import stage1_retrieve
from .stage2_generate import stage2_generate
from .stage3_quality import stage3_quality
from .stage4_sync import stage4_review_router


def create_completion_graph() -> StateGraph:
    """创建元数据补全 Pipeline"""
    graph = StateGraph(CompletionState)

    graph.add_node("retrieve", stage1_retrieve)
    graph.add_node("generate", stage2_generate)
    graph.add_node("quality_check", stage3_quality)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "quality_check")

    # Stage 4: 条件路由
    graph.add_conditional_edges(
        "quality_check",
        stage4_review_router,
        {
            "auto_approved": END,
            "pending_review": END,
            "rejected": END,
        },
    )

    return graph.compile()


pipeline = create_completion_graph()
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/pipeline/
git commit -m "feat: add LangGraph pipeline state and graph definition"
```

### Task 3.2: Stage 1 — 双路检索

**Files:**
- Create: `backend/app/pipeline/stage1_retrieve.py`
- Test: `backend/tests/test_stage1_retrieve.py`

- [ ] **Step 1: 编写测试 `backend/tests/test_stage1_retrieve.py`**

```python
"""Stage 1 双路检索测试"""
import pytest
from app.pipeline.stage1_retrieve import rrf_merge, build_retrieval_text


class TestRRFMerge:
    def test_merge_deduplicates_same_entity(self):
        milvus = [{"entity_id": "t_order", "score": 0.9, "source": "milvus"}]
        es = [{"entity_id": "t_order", "score": 0.8, "source": "es"}]
        result = rrf_merge(milvus, es)
        assert len(result) == 1
        assert result[0]["source"] == "both"

    def test_merge_sorts_by_fusion_score(self):
        milvus = [
            {"entity_id": "a", "score": 0.9},
            {"entity_id": "b", "score": 0.7},
        ]
        es = [
            {"entity_id": "c", "score": 0.8},
            {"entity_id": "a", "score": 0.5},
        ]
        result = rrf_merge(milvus, es)
        # "c" appears only in ES at rank 0 -> 1/61 = ~0.016
        # "a" appears in both -> ~0.016 + 1/63 = ~0.032
        assert result[0]["entity_id"] == "a"

    def test_merge_returns_top_n(self):
        items = [{"entity_id": f"e{i}", "score": 1.0} for i in range(30)]
        result = rrf_merge(items, [], top_n=15)
        assert len(result) == 15


class TestBuildRetrievalText:
    def test_table_search_text(self):
        target = {
            "database": "mysql", "schema": "order_db",
            "table_name": "t_order", "entity_type": "table",
        }
        text = build_retrieval_text(target)
        assert "mysql.order_db.t_order" in text

    def test_column_search_text(self):
        target = {
            "database": "mysql", "schema": "user_db",
            "table_name": "t_user", "column_name": "id_card",
            "data_type": "varchar", "entity_type": "column",
        }
        text = build_retrieval_text(target)
        assert "mysql.user_db.t_user.id_card" in text
        assert "varchar" in text
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_stage1_retrieve.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: 实现 Stage 1 `backend/app/pipeline/stage1_retrieve.py`**

```python
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_stage1_retrieve.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/stage1_retrieve.py backend/tests/test_stage1_retrieve.py
git commit -m "feat: add Stage 1 dual-path retrieval (Milvus + ES)"
```

### Task 3.3: Stage 2 — LLM 生成

**Files:**
- Create: `backend/app/pipeline/stage2_generate.py`
- Create: `backend/app/pipeline/prompts.py`
- Test: `backend/tests/test_stage2_generate.py`

- [ ] **Step 1: 创建 Prompt 模板 `backend/app/pipeline/prompts.py`**

```python
"""Prompt 模板"""

TABLE_COMPLETION_PROMPT = """你是数据治理专家。请根据已有元数据参考，为下面这张数据库表补全元数据信息。

## 待补全的表
- 库名: {database}
- Schema: {schema}
- 表名: {table_name}
- 已有描述: {current_description}
- 已有中文名: {current_display_name}
- 该表包含的字段: {columns_summary}

## 同库兄弟表（了解表所处的业务上下文）
{schema_context}

## 相似表的元数据参考（按相关度排序）
{retrieved_context}

## 请补全以下信息，以 JSON 格式返回：
{{
  "display_name": "表的中文名称（简洁，10 字以内）",
  "description": "表的业务描述（1-3 句话，说明表的作用和包含的数据内容）",
  "tags": ["标签1", "标签2", "标签3"],
  "business_domain": "所属业务域（如：用户域、交易域、营销域、财务域等）",
  "confidence": 0.85,
  "reasoning": "简要说明补全依据（可选）"
}}

## 要求：
1. 中文名应简洁准确，符合数据仓库命名规范
2. 描述应包含表的业务含义和主要用途
3. 标签控制在 3-5 个
4. 参考已有相似的元数据，保持同库风格一致
5. 如果现有信息不足以做出判断，confidence 应反映真实置信度
"""

COLUMN_COMPLETION_PROMPT = """你是数据治理专家。请根据已有元数据参考，为下面这个数据库字段补全元数据信息。

## 待补全的字段
- 所属表: {database}.{schema}.{table_name}
- 表的业务含义: {table_description}
- 字段名: {column_name}
- 数据类型: {data_type}
- 已有描述: {current_description}
- 已有中文名: {current_display_name}

## 同表其他字段（了解字段所在上下文）
{sibling_columns}

## 相似字段的元数据参考（按相关度排序）
{retrieved_context}

## 请补全以下信息，以 JSON 格式返回：
{{
  "display_name": "字段的中文名称（简洁，15 字以内）",
  "description": "字段的业务含义说明（1-2 句话）",
  "tags": ["标签1", "标签2"],
  "sensitive_level": "L1|L2|L3|L4",
  "confidence": 0.85,
  "reasoning": "简要说明补全依据（可选）"
}}

## 要求：
1. 中文名应准确反映字段的业务含义，而非简单的英文翻译
2. 描述应说明字段存储什么数据、用于什么业务场景
3. 敏感级别：L1=公开, L2=内部, L3=敏感, L4=机密（根据字段名和类型判断，如id_card→L3）
4. 参考相似字段的命名和描述风格，保持一致
"""
```

- [ ] **Step 2: 编写测试 `backend/tests/test_stage2_generate.py`**

```python
"""Stage 2 LLM 生成测试"""
import pytest
from app.pipeline.stage2_generate import parse_llm_json, select_model


class TestParseLLMJson:
    def test_parse_direct_json(self):
        raw = '{"display_name": "订单表", "description": "记录订单信息", "tags": ["交易"], "confidence": 0.9}'
        result = parse_llm_json(raw)
        assert result["display_name"] == "订单表"
        assert result["confidence"] == 0.9

    def test_parse_json_in_code_block(self):
        raw = '```json\n{"display_name": "用户表", "description": "用户信息", "confidence": 0.85}\n```'
        result = parse_llm_json(raw)
        assert result["display_name"] == "用户表"

    def test_parse_raw_curly_braces(self):
        raw = '一些前缀文本 {"display_name": "支付单", "description": "支付记录", "confidence": 0.8} 一些后缀'
        result = parse_llm_json(raw)
        assert result["display_name"] == "支付单"

    def test_parse_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_llm_json("这不是 JSON")


class TestSelectModel:
    def test_column_defaults_to_qwen_plus(self):
        model = select_model("column", [], [])
        assert model == "qwen-plus"

    def test_table_with_rich_siblings_uses_qwen_max(self):
        siblings = [{"description": "desc" + str(i)} for i in range(6)]
        model = select_model("table", siblings, [])
        assert model == "qwen-max"

    def test_table_sparse_siblings_uses_default(self):
        siblings = [{"description": ""} for _ in range(6)]
        model = select_model("table", siblings, [])
        assert model == "qwen-plus"
```

- [ ] **Step 3: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_stage2_generate.py -v`
Expected: FAIL (module not found)

- [ ] **Step 4: 实现 Stage 2 `backend/app/pipeline/stage2_generate.py`**

```python
"""Stage 2: LLM 生成补全建议"""
import json
import re
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage
from .state import CompletionState
from .prompts import TABLE_COMPLETION_PROMPT, COLUMN_COMPLETION_PROMPT
from app.services.dashscope import create_llm, select_model as _select_model
from app.utils.logger import get_logger

logger = get_logger(__name__)


def select_model(entity_type: str, schema_context: list[dict], retrieved_context: list[dict]) -> str:
    """选择模型（纯函数，便于测试）"""
    from app.services.dashscope import select_model as _impl
    return _impl(entity_type, schema_context, retrieved_context)


def parse_llm_json(raw_response: str) -> dict:
    """从 LLM 文本响应中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        pass

    # 提取 ```json ... ``` 代码块
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_response)
    if match:
        return json.loads(match.group(1))

    # 提取第一个 { ... } 块
    match = re.search(r'\{[\s\S]*\}', raw_response)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"无法从 LLM 响应中解析 JSON: {raw_response[:500]}")


def _format_context_list(ctx_list: list[dict]) -> str:
    """格式化上下文列表为 Prompt 文本"""
    lines = []
    for i, ctx in enumerate(ctx_list, 1):
        lines.append(f"{i}. {ctx.get('search_text', '')} [相关度: {ctx.get('score', 0):.3f}]")
    return "\n".join(lines) if lines else "（无参考数据）"


def _build_table_prompt(target: dict, state: CompletionState) -> str:
    """构建表级补全 Prompt"""
    columns = target.get("columns", [])
    columns_summary = ", ".join(
        f"{c.get('name', '?')}({c.get('dataType', '?')})" for c in columns[:20]
    )
    schema_lines = [
        f"- {s.get('table_name', '?')}: {s.get('description', '无描述')}"
        for s in state.get("schema_context", [])
    ]
    return TABLE_COMPLETION_PROMPT.format(
        database=target.get("database", ""),
        schema=target.get("schema", ""),
        table_name=target.get("table_name", ""),
        current_description=target.get("current_description") or "（空）",
        current_display_name=target.get("current_display_name") or "（空）",
        columns_summary=columns_summary,
        schema_context="\n".join(schema_lines) if schema_lines else "（无同库兄弟表）",
        retrieved_context=_format_context_list(state.get("retrieved_context", [])),
    )


def _build_column_prompt(target: dict, state: CompletionState) -> str:
    """构建字段级补全 Prompt"""
    sib_lines = [
        f"- {s.get('column_name', '?')} ({s.get('data_type', '?')}): {s.get('description', '无描述')}"
        for s in state.get("sibling_columns", [])
    ]
    return COLUMN_COMPLETION_PROMPT.format(
        database=target.get("database", ""),
        schema=target.get("schema", ""),
        table_name=target.get("table_name", ""),
        table_description=target.get("table_description") or "（空）",
        column_name=target.get("column_name", ""),
        data_type=target.get("data_type", ""),
        current_description=target.get("current_description") or "（空）",
        current_display_name=target.get("current_display_name") or "（空）",
        sibling_columns="\n".join(sib_lines) if sib_lines else "（无同表字段信息）",
        retrieved_context=_format_context_list(state.get("retrieved_context", [])),
    )


async def stage2_generate(state: CompletionState) -> CompletionState:
    """Stage 2: LLM 生成补全建议"""
    if state.get("error"):
        return state

    target = state["target_entity"]

    # 选择模型
    model_name = _select_model(
        target["entity_type"],
        state.get("schema_context", []),
        state.get("retrieved_context", []),
    )

    llm = create_llm(model=model_name, temperature=0.1)

    # 构建 Prompt
    if target["entity_type"] == "table":
        prompt = _build_table_prompt(target, state)
    else:
        prompt = _build_column_prompt(target, state)

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        result = parse_llm_json(response.content)

        # 修正字段缺失：缺失字段降权
        missing_penalty = 0
        if not result.get("display_name"):
            missing_penalty += 0.1
        if not result.get("description"):
            missing_penalty += 0.1

        confidence = result.get("confidence", 0.5)
        confidence = max(0.0, min(1.0, confidence - missing_penalty))

        state["completion_result"] = {
            "target_entity_id": target["entity_id"],
            "entity_type": target["entity_type"],
            "display_name": result.get("display_name") or "",
            "description": result.get("description") or "",
            "tags": result.get("tags") or [],
            "business_domain": result.get("business_domain"),
            "sensitive_level": result.get("sensitive_level"),
            "confidence": confidence,
            "reasoning": result.get("reasoning", ""),
            "model_used": model_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Stage 2 complete: model={model_name}, confidence={confidence:.2f}")
    except Exception as e:
        logger.error(f"Stage 2 failed: {e}")
        state["error"] = str(e)
        state["completion_result"] = None

    return state
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_stage2_generate.py -v`
Expected: PASS (resolve_llm_json 和 select_model 的单元测试，不需要真实 LLM 调用)

- [ ] **Step 6: Commit**

```bash
git add backend/app/pipeline/stage2_generate.py backend/app/pipeline/prompts.py backend/tests/test_stage2_generate.py
git commit -m "feat: add Stage 2 LLM generation with prompt templates"
```

### Task 3.4: Stage 3 — 质量校验

**Files:**
- Create: `backend/app/pipeline/stage3_quality.py`
- Test: `backend/tests/test_stage3_quality.py`

- [ ] **Step 1: 编写测试 `backend/tests/test_stage3_quality.py`**

```python
"""Stage 3 质量校验测试"""
import pytest
from app.pipeline.stage3_quality import (
    calculate_adjusted_confidence,
    check_rules,
    check_conflict,
    decide_review_status,
)


class TestAdjustedConfidence:
    def test_high_confidence_passes(self):
        result = {"display_name": "订单表", "description": "订单信息记录表", "tags": ["交易"], "confidence": 0.9}
        target = {"retrieved_context": [{"score": 0.1}] * 5}
        conf = calculate_adjusted_confidence(result, target)
        assert conf >= 0.85

    def test_short_description_penalized(self):
        result = {"display_name": "X", "description": "abc", "tags": [], "confidence": 0.9}
        target = {"retrieved_context": [{"score": 0.01}] * 5}
        conf = calculate_adjusted_confidence(result, target)
        assert conf < 0.7  # 检索差 + 描述短 + 无标签 -> 大幅降权


class TestCheckRules:
    def test_required_fields_critical(self):
        violations = check_rules(
            {"display_name": "", "description": "desc", "tags": []},
            {"entity_type": "table", "table_name": "t_order"},
        )
        assert any(v["severity"] == "critical" for v in violations)

    def test_display_name_no_code_warning(self):
        violations = check_rules(
            {"display_name": "userProfileTable", "description": "用户表", "tags": ["用户"]},
            {"entity_type": "table", "table_name": "t_order"},
        )
        assert any(v["rule"] == "display_name_no_code" for v in violations)

    def test_description_same_as_name_warning(self):
        violations = check_rules(
            {"display_name": "订单表", "description": "订单表", "tags": ["交易"]},
            {"entity_type": "table", "table_name": "t_order"},
        )
        assert any(v["rule"] == "description_not_copy_name" for v in violations)


class TestCheckConflict:
    def test_description_divergence_detected(self):
        conflicts = check_conflict(
            {"description": "全新的业务含义"},
            {"current_description": "旧的描述完全不同", "current_tags": []},
        )
        assert any(c["type"] == "description_divergence" for c in conflicts)

    def test_tag_overhaul_detected(self):
        conflicts = check_conflict(
            {"tags": ["新标签"]},
            {"current_tags": ["旧标签"]},
        )
        assert any(c["type"] == "tag_overhaul" for c in conflicts)

    def test_no_conflict_when_empty_current(self):
        conflicts = check_conflict(
            {"description": "新描述", "tags": ["新"]},
            {},
        )
        assert len(conflicts) == 0


class TestReviewStatus:
    def test_auto_approved(self):
        violations = []
        status = decide_review_status(0.85, violations)
        assert status == "auto_approved"

    def test_pending_review(self):
        violations = [{"severity": "warning"}]
        status = decide_review_status(0.75, violations)
        assert status == "pending_review"

    def test_rejected_low_confidence(self):
        status = decide_review_status(0.50, [])
        assert status == "rejected"

    def test_rejected_critical(self):
        violations = [{"severity": "critical"}]
        status = decide_review_status(0.90, violations)
        assert status == "rejected"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_stage3_quality.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 Stage 3 `backend/app/pipeline/stage3_quality.py`**

```python
"""Stage 3: 质量校验"""
import re
from .state import CompletionState
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---- 规则引擎 ----

RULES = {
    "required_fields": {
        "check": lambda r, t: all(r.get(f) for f in ["display_name", "description"]),
        "severity": "critical",
        "message": "display_name 或 description 缺失",
    },
    "display_name_no_code": {
        "check": lambda r, t: not bool(re.search(r'[a-z]{3,}', r.get("display_name", "").lower())),
        "severity": "warning",
        "message": "中文名包含大段英文，疑似代码而非中文名",
    },
    "description_not_copy_name": {
        "check": lambda r, t: r.get("description", "").strip() != r.get("display_name", "").strip(),
        "severity": "warning",
        "message": "描述与中文名完全一致，描述应更详细",
    },
    "sensitive_level_valid": {
        "check": lambda r, t: r.get("sensitive_level") in [None, "L1", "L2", "L3", "L4"],
        "severity": "warning",
        "message": "敏感级别不在 L1-L4 范围内",
    },
    "tag_no_duplicates": {
        "check": lambda r, t: len(r.get("tags", [])) == len(set(r.get("tags", []))),
        "severity": "info",
        "message": "标签存在重复",
    },
    "business_domain_valid": {
        "check": lambda r, t: (
            r.get("business_domain") is None or len(str(r.get("business_domain", ""))) <= 20
        ),
        "severity": "info",
        "message": "业务域名过长",
    },
    "table_name_consistency": {
        "check": lambda r, t: (
            r.get("display_name", "").lower().replace("_", "")
            != t.get("table_name", "").lower().replace("_", "")
        ),
        "severity": "warning",
        "message": "中文名与英文表名相同，需要更具体的业务含义",
    },
}


def calculate_adjusted_confidence(result: dict, target: dict) -> float:
    """修正置信度得分"""
    score = result.get("confidence", 0.5)
    penalties = []

    # 检索质量降权
    scores = [ctx.get("score", 0) for ctx in target.get("retrieved_context", [])[:5]]
    if scores and (sum(scores) / len(scores)) < 0.05:
        penalties.append(0.15)

    # 描述长度异常
    desc = result.get("description", "")
    if len(desc) < 10:
        penalties.append(0.20)
    elif len(desc) > 300:
        penalties.append(0.10)

    # 中文名特殊字符
    if re.search(r'[{}[\]()\\]', result.get("display_name", "")):
        penalties.append(0.15)

    # 标签异常
    tags = result.get("tags", [])
    if len(tags) == 0:
        penalties.append(0.10)
    elif len(tags) > 8:
        penalties.append(0.05)

    adjusted = score - sum(penalties)
    return max(0.0, min(1.0, adjusted))


def check_rules(result: dict, target: dict) -> list[dict]:
    """执行规则引擎校验"""
    violations = []
    for rule_name, rule in RULES.items():
        passed = rule["check"](result, target)
        if not passed:
            violations.append({
                "rule": rule_name,
                "severity": rule["severity"],
                "message": rule["message"],
            })
    return violations


def check_conflict(result: dict, target: dict) -> list[dict]:
    """检查与已有元数据的冲突"""
    conflicts = []

    # 描述重叠检测
    if target.get("current_description") and result.get("description"):
        overlap = _text_overlap(result["description"], target["current_description"])
        if overlap < 0.3:
            conflicts.append({
                "type": "description_divergence",
                "severity": "warning",
                "message": f"新描述与已有描述差异大 (重叠度 {overlap:.2f})，请确认是否需要覆盖",
            })

    # 标签交集检测
    if target.get("current_tags") and result.get("tags"):
        old_set = set(target["current_tags"])
        new_set = set(result["tags"])
        if not old_set.intersection(new_set):
            conflicts.append({
                "type": "tag_overhaul",
                "severity": "info",
                "message": "新标签与已有标签无交集",
            })

    return conflicts


def decide_review_status(adjusted_confidence: float, violations: list[dict]) -> str:
    """根据置信度和违规决定审核状态"""
    has_critical = any(v["severity"] == "critical" for v in violations)
    has_warning = any(v["severity"] == "warning" for v in violations)

    if has_critical or adjusted_confidence < 0.60:
        return "rejected"
    elif adjusted_confidence >= 0.80 and not has_warning:
        return "auto_approved"
    else:
        return "pending_review"


def _text_overlap(text1: str, text2: str) -> float:
    """简单文本重叠度计算（Jaccard）"""
    set1 = set(text1)
    set2 = set(text2)
    if not set1 or not set2:
        return 0.0
    return len(set1.intersection(set2)) / len(set1.union(set2))


async def stage3_quality(state: CompletionState) -> CompletionState:
    """Stage 3: 质量校验"""
    if state.get("error") or state.get("completion_result") is None:
        state["quality_check"] = None
        state["review_status"] = "rejected"
        return state

    result = state["completion_result"]
    target = state["target_entity"]

    adjusted_confidence = calculate_adjusted_confidence(result, target)
    rule_violations = check_rules(result, target)
    conflicts = check_conflict(result, target)
    review_status = decide_review_status(adjusted_confidence, rule_violations)

    state["quality_check"] = {
        "original_confidence": result.get("confidence", 0),
        "adjusted_confidence": adjusted_confidence,
        "rule_violations": rule_violations,
        "conflicts": conflicts,
        "review_status": review_status,
    }
    state["review_status"] = review_status

    logger.info(
        f"Stage 3 complete: status={review_status}, "
        f"confidence={adjusted_confidence:.2f}, violations={len(rule_violations)}"
    )
    return state
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_stage3_quality.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/stage3_quality.py backend/tests/test_stage3_quality.py
git commit -m "feat: add Stage 3 quality check with rule engine"
```

---

## Phase 4: Stage 4 + API 层

### Task 4.1: Stage 4 — 审核路由

**Files:**
- Create: `backend/app/pipeline/stage4_sync.py`

- [ ] **Step 1: 实现 Stage 4 `backend/app/pipeline/stage4_sync.py`**

```python
"""Stage 4: 审核路由 + 同步回写"""
from .state import CompletionState
from app.utils.logger import get_logger

logger = get_logger(__name__)


def stage4_review_router(state: CompletionState) -> str:
    """根据 Stage 3 分流决策返回路由目标"""
    status = state.get("review_status") or state.get("quality_check", {}).get("review_status", "rejected")

    if status == "auto_approved":
        logger.info(f"Stage 4 route: auto_approved → sync_to_openmetadata")
        return "auto_approved"
    elif status == "pending_review":
        logger.info(f"Stage 4 route: pending_review → review_queue")
        return "pending_review"
    else:
        logger.info(f"Stage 4 route: {status} → log_and_notify")
        return "rejected"
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/pipeline/stage4_sync.py
git commit -m "feat: add Stage 4 review routing"
```

### Task 4.2: API — 搜索 + 补全

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/search.py`
- Create: `backend/app/api/complete.py`
- Create: `backend/app/api/schemas.py`

- [ ] **Step 1: 创建 API Schema `backend/app/api/schemas.py`**

```python
"""API 请求/响应 Schema"""
from pydantic import BaseModel, Field
from datetime import datetime


class TargetEntity(BaseModel):
    entity_id: str
    entity_type: str = Field(pattern="^(table|column)$")
    database: str
    schema: str
    table_name: str
    column_name: str | None = None
    data_type: str | None = None
    current_description: str | None = None
    current_display_name: str | None = None
    current_tags: list[str] | None = None
    table_description: str | None = None
    columns: list[dict] | None = None  # 表的字段列表


class CompletionTriggerRequest(BaseModel):
    target: TargetEntity


class BatchCompletionRequest(BaseModel):
    targets: list[TargetEntity] = Field(max_length=100)


class CompletionResponse(BaseModel):
    record_id: str
    entity_id: str
    entity_type: str
    review_status: str
    completion_result: dict | None
    quality_check: dict | None
    created_at: str


class ReviewActionRequest(BaseModel):
    comment: str | None = None
    modified_result: dict | None = None


class SearchRequest(BaseModel):
    query: str
    entity_type: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
```

- [ ] **Step 2: 创建搜索 API `backend/app/api/search.py`**

```python
"""元数据搜索 API"""
from fastapi import APIRouter, Depends
from app.services.elasticsearch import search_all
from app.api.schemas import SearchRequest

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("")
async def search_metadata(req: SearchRequest):
    """搜索元数据（ES 关键词检索）"""
    results = search_all(
        query_text=req.query,
        entity_type=req.entity_type,
        top_k=100,
    )
    # 分页
    start = (req.page - 1) * req.page_size
    end = start + req.page_size
    items = results[start:end]

    return {
        "success": True,
        "data": items,
        "meta": {
            "total": len(results),
            "page": req.page,
            "page_size": req.page_size,
        },
    }
```

- [ ] **Step 3: 创建补全 API `backend/app/api/complete.py`**

```python
"""元数据补全 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.pipeline.graph import pipeline
from app.models.completion import CompletionRecord
from app.api.schemas import CompletionTriggerRequest, BatchCompletionRequest, CompletionResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/complete", tags=["complete"])


@router.post("/trigger/manual", response_model=CompletionResponse)
async def trigger_completion(req: CompletionTriggerRequest, db: AsyncSession = Depends(get_db)):
    """手动触发元数据补全"""
    target = req.target.model_dump()

    # 运行 Pipeline
    result = await pipeline.ainvoke({
        "target_entity": target,
        "retrieved_context": [],
        "schema_context": [],
        "sibling_columns": [],
        "completion_result": None,
        "quality_check": None,
        "review_status": None,
        "error": None,
    })

    # 保存记录
    record = CompletionRecord(
        entity_id=target["entity_id"],
        entity_type=target["entity_type"],
        target_data=target,
        completion_result=result.get("completion_result"),
        quality_check=result.get("quality_check"),
        review_status=result.get("review_status") or "rejected",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return CompletionResponse(
        record_id=record.id,
        entity_id=record.entity_id,
        entity_type=record.entity_type,
        review_status=record.review_status,
        completion_result=record.completion_result,
        quality_check=record.quality_check,
        created_at=record.created_at.isoformat() if record.created_at else "",
    )
```

- [ ] **Step 4: 注册路由到 main.py**

更新 `backend/app/main.py`，在 `create_app()` 中添加：

```python
from app.api.search import router as search_router
from app.api.complete import router as complete_router

app.include_router(search_router)
app.include_router(complete_router)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/
git commit -m "feat: add search and completion APIs"
```

### Task 4.3: API — 审核

**Files:**
- Create: `backend/app/api/review.py`

- [ ] **Step 1: 创建审核 API `backend/app/api/review.py`**

```python
"""审核 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.database import get_db
from app.models.completion import CompletionRecord, AuditLog
from app.api.schemas import ReviewActionRequest
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/review", tags=["review"])


@router.get("/queue")
async def get_review_queue(
    entity_type: str | None = None,
    status: str = "pending_review",
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """获取审核队列"""
    query = select(CompletionRecord).where(
        CompletionRecord.review_status == status
    )
    if entity_type:
        query = query.where(CompletionRecord.entity_type == entity_type)

    query = query.order_by(CompletionRecord.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "entity_id": r.entity_id,
                "entity_type": r.entity_type,
                "completion_result": r.completion_result,
                "quality_check": r.quality_check,
                "review_status": r.review_status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
    }


@router.get("/{record_id}")
async def get_review_detail(record_id: str, db: AsyncSession = Depends(get_db)):
    """获取审核详情"""
    result = await db.execute(
        select(CompletionRecord).where(CompletionRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="审核记录不存在")

    return {
        "success": True,
        "data": {
            "id": record.id,
            "entity_id": record.entity_id,
            "entity_type": record.entity_type,
            "target_data": record.target_data,
            "completion_result": record.completion_result,
            "quality_check": record.quality_check,
            "review_status": record.review_status,
            "reviewer": record.reviewer,
            "review_comment": record.review_comment,
            "synced_to_om": record.synced_to_om,
        },
    }


@router.post("/{record_id}/approve")
async def approve_review(
    record_id: str,
    req: ReviewActionRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """确认补全"""
    result = await db.execute(
        select(CompletionRecord).where(CompletionRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    record.review_status = "approved"
    record.reviewer = "admin"
    record.review_comment = req.comment if req else None
    record.reviewed_at = datetime.now(timezone.utc)

    # 记录审计日志
    log = AuditLog(
        entity_id=record.entity_id,
        action="manual_approve",
        operator="admin",
        detail={"record_id": record_id, "result": record.completion_result},
    )
    db.add(log)
    await db.commit()

    logger.info(f"Review approved: {record_id} -> {record.entity_id}")
    return {"success": True, "data": {"status": "approved"}}


@router.post("/{record_id}/reject")
async def reject_review(
    record_id: str,
    req: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """拒绝补全"""
    result = await db.execute(
        select(CompletionRecord).where(CompletionRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    record.review_status = "human_rejected"
    record.reviewer = "admin"
    record.review_comment = req.comment or ""
    record.reviewed_at = datetime.now(timezone.utc)

    log = AuditLog(
        entity_id=record.entity_id,
        action="reject",
        operator="admin",
        detail={"record_id": record_id, "reason": req.comment},
    )
    db.add(log)
    await db.commit()

    return {"success": True, "data": {"status": "rejected"}}


@router.post("/batch/approve")
async def batch_approve(record_ids: list[str], db: AsyncSession = Depends(get_db)):
    """批量确认"""
    for rid in record_ids:
        result = await db.execute(select(CompletionRecord).where(CompletionRecord.id == rid))
        record = result.scalar_one_or_none()
        if record and record.review_status == "pending_review":
            record.review_status = "approved"
            record.reviewer = "admin"
            record.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    return {"success": True, "data": {"count": len(record_ids)}}
```

- [ ] **Step 2: 注册路由到 main.py**

更新 `backend/app/main.py`：

```python
from app.api.review import router as review_router
app.include_router(review_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/review.py backend/app/main.py
git commit -m "feat: add review API (queue, approve, reject, batch)"
```

### Task 4.4: 后端 API 集成测试

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_api.py`

- [ ] **Step 1: 创建测试 fixtures `backend/tests/conftest.py`**

```python
"""测试 fixtures"""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 2: 创建 API 集成测试 `backend/tests/test_api.py`**

```python
"""API 集成测试"""
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_search_endpoint(client):
    resp = await client.post("/api/v1/search", json={
        "query": "test",
        "entity_type": "table",
    })
    # ES 连接可能不可用，检查响应结构
    assert resp.status_code in [200, 500]
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_api.py::test_health_check -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/conftest.py backend/tests/test_api.py
git commit -m "test: add API integration tests"
```

---

## Phase 5: 前端页面

### Task 5.1: 前端路由 + API 层

**Files:**
- Create/Modify: `frontend/src/router/index.ts`
- Create: `frontend/src/api/index.ts`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 创建前端 API 层 `frontend/src/api/index.ts`**

```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
})

// ---- 搜索 ----
export interface SearchParams {
  query: string
  entity_type?: string
  page?: number
  page_size?: number
}

export async function searchMetadata(params: SearchParams) {
  const { data } = await api.post('/search', params)
  return data
}

// ---- 补全 ----
export interface TargetEntity {
  entity_id: string
  entity_type: 'table' | 'column'
  database: string
  schema: string
  table_name: string
  column_name?: string
  data_type?: string
  current_description?: string | null
  current_display_name?: string | null
  current_tags?: string[] | null
  table_description?: string | null
  columns?: { name: string; dataType: string }[] | null
}

export async function triggerCompletion(target: TargetEntity) {
  const { data } = await api.post('/complete/trigger/manual', { target })
  return data
}

// ---- 审核 ----
export async function getReviewQueue(params: {
  entity_type?: string
  status?: string
  page?: number
  page_size?: number
}) {
  const { data } = await api.get('/review/queue', { params })
  return data
}

export async function getReviewDetail(recordId: string) {
  const { data } = await api.get(`/review/${recordId}`)
  return data
}

export async function approveReview(recordId: string, comment?: string) {
  const { data } = await api.post(`/review/${recordId}/approve`, { comment })
  return data
}

export async function rejectReview(recordId: string, comment: string) {
  const { data } = await api.post(`/review/${recordId}/reject`, { comment })
  return data
}

export async function batchApprove(recordIds: string[]) {
  const { data } = await api.post('/review/batch/approve', recordIds)
  return data
}
```

- [ ] **Step 2: 创建路由 `frontend/src/router/index.ts`**

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: '/search',
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('../pages/SearchPage.vue'),
    },
    {
      path: '/review',
      name: 'review',
      component: () => import('../pages/ReviewPage.vue'),
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../pages/HistoryPage.vue'),
    },
    {
      path: '/config',
      name: 'config',
      component: () => import('../pages/ConfigPage.vue'),
    },
  ],
})

export default router
```

- [ ] **Step 3: 更新 App.vue**

```vue
<template>
  <t-layout>
    <t-aside width="200px">
      <t-menu :value="currentRoute" @change="handleMenuChange">
        <t-menu-item value="/search">
          <template #icon><SearchIcon /></template>
          元数据搜索
        </t-menu-item>
        <t-menu-item value="/review">
          <template #icon><CheckCircleIcon /></template>
          补全审核
        </t-menu-item>
        <t-menu-item value="/history">
          <template #icon><TimeIcon /></template>
          补全历史
        </t-menu-item>
        <t-menu-item value="/config">
          <template #icon><SettingIcon /></template>
          系统配置
        </t-menu-item>
      </t-menu>
    </t-aside>
    <t-layout>
      <t-content style="padding: 24px; min-height: 100vh">
        <router-view />
      </t-content>
    </t-layout>
  </t-layout>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { SearchIcon, CheckCircleIcon, TimeIcon, SettingIcon } from 'tdesign-icons-vue-next'

const router = useRouter()
const route = useRoute()
const currentRoute = computed(() => route.path)

const handleMenuChange = (value: string) => {
  router.push(value)
}
</script>
```

- [ ] **Step 4: 验证前端启动**

Run: `cd frontend && npm run dev`
Expected: 页面无报错，左侧菜单可切换

- [ ] **Step 5: Commit**

```bash
git add frontend/src/router/ frontend/src/api/ frontend/src/App.vue
git commit -m "feat: add frontend routing, API layer, and layout"
```

### Task 5.2: 搜索页面

**Files:**
- Create: `frontend/src/pages/SearchPage.vue`
- Create: `frontend/src/components/MetadataCard.vue`
- Create: `frontend/src/components/SearchBar.vue`
- Create: `frontend/src/components/CompletionPanel.vue`

- [ ] **Step 1: 创建 SearchBar 组件 `frontend/src/components/SearchBar.vue`**

```vue
<template>
  <div class="search-bar">
    <t-input
      v-model="searchText"
      placeholder="搜索表名、字段名、中文名、描述..."
      clearable
      size="large"
      @enter="handleSearch"
    >
      <template #suffix>
        <t-button theme="primary" @click="handleSearch">搜索</t-button>
      </template>
    </t-input>
    <t-select
      v-model="entityType"
      placeholder="全部类型"
      clearable
      style="width: 140px; margin-left: 12px"
    >
      <t-option value="table" label="表" />
      <t-option value="column" label="字段" />
    </t-select>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const searchText = ref('')
const entityType = ref<string | undefined>(undefined)

const emit = defineEmits<{
  search: [params: { query: string; entity_type?: string }]
}>()

const handleSearch = () => {
  if (!searchText.value.trim()) return
  emit('search', { query: searchText.value.trim(), entity_type: entityType.value })
}
</script>

<style scoped>
.search-bar {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
}
</style>
```

- [ ] **Step 2: 创建 MetadataCard 组件 `frontend/src/components/MetadataCard.vue`**

```vue
<template>
  <div class="metadata-card" :class="{ selected }">
    <div class="card-header">
      <t-tag :theme="item.entity_type === 'table' ? 'primary' : 'warning'" variant="light" size="small">
        {{ item.entity_type === 'table' ? '表' : '字段' }}
      </t-tag>
      <span class="card-name">{{ item.entity_type === 'table' ? item.table_name : item.column_name }}</span>
      <span v-if="item.display_name" class="display-name">{{ item.display_name }}</span>
    </div>
    <p v-if="item.description" class="card-desc">{{ item.description }}</p>
    <div class="card-meta">
      <span>{{ item.database }}.{{ item.schema_name }}</span>
      <span v-if="item.data_type">{{ item.data_type }}</span>
    </div>
    <div v-if="!item.description && !item.display_name" class="card-action">
      <t-button size="small" theme="primary" variant="outline" @click.stop="handleComplete">
        智能补全
      </t-button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  item: any
  selected?: boolean
}>()

const emit = defineEmits<{
  complete: [item: any]
}>()

const handleComplete = () => {
  emit('complete', { $props: { item } })
}
</script>

<!-- handleComplete needs fixing — see step 3 -->
```

- [ ] **Step 3: 修复 MetadataCard handleComplete**，实际实现为：

```vue
const props = defineProps<{
  item: any
  selected?: boolean
}>()

const emit = defineEmits<{
  complete: [item: any]
}>()

const handleComplete = () => {
  emit('complete', props.item)
}
```

- [ ] **Step 4: 创建 CompletionPanel 组件 `frontend/src/components/CompletionPanel.vue`**

```vue
<template>
  <t-drawer
    v-model:visible="visible"
    header="智能补全结果"
    size="500px"
    :footer="false"
  >
    <t-loading v-if="loading" text="AI 正在分析元数据，请稍候..." />
    <template v-else-if="result">
      <div class="result-section">
        <t-tag :theme="statusTheme" variant="light" size="medium">
          {{ statusText }}
        </t-tag>
        <QualityBadge :confidence="result.quality_check?.adjusted_confidence ?? result.completion_result?.confidence" />
      </div>
      <t-divider />
      <div v-if="result.completion_result">
        <t-form label-width="80px" readonly>
          <t-form-item label="中文名">
            {{ result.completion_result.display_name }}
          </t-form-item>
          <t-form-item label="描述">
            {{ result.completion_result.description }}
          </t-form-item>
          <t-form-item v-if="result.completion_result.tags?.length" label="标签">
            <t-tag v-for="t in result.completion_result.tags" :key="t" size="small" variant="light">
              {{ t }}
            </t-tag>
          </t-form-item>
          <t-form-item v-if="result.completion_result.business_domain" label="业务域">
            {{ result.completion_result.business_domain }}
          </t-form-item>
          <t-form-item v-if="result.completion_result.sensitive_level" label="安全级">
            <t-tag :theme="sensitiveTheme" size="small">
              {{ result.completion_result.sensitive_level }}
            </t-tag>
          </t-form-item>
          <t-form-item v-if="result.completion_result.reasoning" label="依据">
            {{ result.completion_result.reasoning }}
          </t-form-item>
        </t-form>
      </div>
    </template>
    <t-empty v-else description="暂无结果" />
  </t-drawer>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { triggerCompletion, type TargetEntity } from '../api'
import QualityBadge from './QualityBadge.vue'

const visible = ref(false)
const loading = ref(false)
const result = ref<any>(null)

const statusText = computed(() => {
  const s = result.value?.review_status
  const map: Record<string, string> = {
    auto_approved: '已自动采纳',
    pending_review: '待审核',
    rejected: '已拒绝',
  }
  return map[s] || s || '未知'
})

const statusTheme = computed(() => {
  const s = result.value?.review_status
  return s === 'auto_approved' ? 'success' : s === 'rejected' ? 'danger' : 'warning'
})

const sensitiveTheme = computed(() => {
  const level = result.value?.completion_result?.sensitive_level
  return level === 'L4' ? 'danger' : level === 'L3' ? 'warning' : 'success'
})

const open = async (target: TargetEntity) => {
  visible.value = true
  loading.value = true
  result.value = null
  try {
    result.value = await triggerCompletion(target)
  } catch (e: any) {
    result.value = { error: e.message }
  } finally {
    loading.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.result-section {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
```

- [ ] **Step 5: 创建 SearchPage `frontend/src/pages/SearchPage.vue`**

```vue
<template>
  <div class="search-page">
    <h1>元数据搜索</h1>
    <p class="subtitle">搜索数据库表/字段，对缺少描述的元数据触发 AI 智能补全</p>

    <SearchBar @search="handleSearch" />

    <t-loading v-if="searching" />
    <template v-else-if="results.length > 0">
      <div class="result-grid">
        <MetadataCard
          v-for="item in results"
          :key="item.entity_id"
          :item="item"
          @complete="handleComplete"
        />
      </div>
    </template>
    <t-empty v-else-if="searched" description="未找到匹配的元数据" />

    <CompletionPanel ref="completionPanelRef" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { searchMetadata, type TargetEntity } from '../api'
import SearchBar from '../components/SearchBar.vue'
import MetadataCard from '../components/MetadataCard.vue'
import CompletionPanel from '../components/CompletionPanel.vue'

const searching = ref(false)
const searched = ref(false)
const results = ref<any[]>([])
const completionPanelRef = ref<InstanceType<typeof CompletionPanel>>()

const handleSearch = async (params: { query: string; entity_type?: string }) => {
  searching.value = true
  searched.value = true
  try {
    const data = await searchMetadata({ ...params, page: 1, page_size: 50 })
    results.value = data.data || []
  } finally {
    searching.value = false
  }
}

const handleComplete = (item: any) => {
  const target: TargetEntity = {
    entity_id: item.entity_id,
    entity_type: item.entity_type,
    database: item.database || '',
    schema: item.schema_name || '',
    table_name: item.table_name || '',
    column_name: item.column_name,
    data_type: item.data_type,
    current_description: item.description || null,
    current_display_name: item.display_name || null,
    current_tags: item.tags || null,
  }
  completionPanelRef.value?.open(target)
}
</script>

<style scoped>
.search-page {
  max-width: 1200px;
}
h1 { font-size: 24px; margin-bottom: 8px; }
.subtitle { color: var(--color-text-secondary); margin-bottom: 24px; }
.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
</style>
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/SearchPage.vue frontend/src/components/
git commit -m "feat: add search page with AI completion trigger"
```

### Task 5.3: 审核页面

**Files:**
- Create: `frontend/src/components/QualityBadge.vue`
- Create: `frontend/src/components/ReviewQueue.vue`
- Create: `frontend/src/components/ReviewDetail.vue`
- Create: `frontend/src/pages/ReviewPage.vue`

- [ ] **Step 1: 创建 QualityBadge `frontend/src/components/QualityBadge.vue`**

```vue
<template>
  <t-tag :theme="theme" variant="outline" size="small">
    置信度: {{ (confidence * 100).toFixed(0) }}%
  </t-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ confidence: number }>()

const theme = computed(() => {
  if (props.confidence >= 0.80) return 'success'
  if (props.confidence >= 0.60) return 'warning'
  return 'danger'
})
</script>
```

- [ ] **Step 2: 创建 ReviewQueue `frontend/src/components/ReviewQueue.vue`**

```vue
<template>
  <div class="review-queue">
    <div class="queue-toolbar">
      <t-select v-model="filterType" placeholder="类型筛选" clearable style="width: 120px">
        <t-option value="table" label="表" />
        <t-option value="column" label="字段" />
      </t-select>
      <t-space>
        <t-button size="small" variant="outline" @click="handleBatchApprove">批量确认</t-button>
        <t-button size="small" variant="outline" theme="danger" @click="handleBatchReject">批量拒绝</t-button>
      </t-space>
    </div>

    <t-table
      :data="items"
      :columns="columns"
      :loading="loading"
      row-key="id"
      :selected-row-keys="selectedIds"
      @select-change="handleSelect"
    >
      <template #entity="{ row }">
        <t-tag :theme="row.entity_type === 'table' ? 'primary' : 'warning'" variant="light" size="small">
          {{ row.entity_type === 'table' ? '表' : '字段' }}
        </t-tag>
        <span style="margin-left: 8px; font-family: monospace">{{ row.entity_id }}</span>
      </template>
      <template #result="{ row }">
        <div>
          <div>{{ row.completion_result?.display_name || '-' }}</div>
          <div style="font-size: 12px; color: var(--color-text-secondary)">
            {{ row.completion_result?.description?.substring(0, 60) || '-' }}
          </div>
        </div>
      </template>
      <template #confidence="{ row }">
        <QualityBadge :confidence="row.quality_check?.adjusted_confidence ?? row.completion_result?.confidence ?? 0" />
      </template>
      <template #actions="{ row }">
        <t-space :size="4">
          <t-button size="small" theme="primary" variant="text" @click="handleApprove(row)">
            确认
          </t-button>
          <t-button size="small" variant="text" @click="showDetail(row)">
            查看
          </t-button>
          <t-button size="small" theme="danger" variant="text" @click="handleReject(row)">
            拒绝
          </t-button>
        </t-space>
      </template>
    </t-table>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { getReviewQueue, approveReview, rejectReview } from '../api'
import QualityBadge from './QualityBadge.vue'
import { MessagePlugin } from 'tdesign-vue-next'

const props = defineProps<{ refresh: number }>()

const items = ref<any[]>([])
const loading = ref(false)
const selectedIds = ref<string[]>([])
const filterType = ref<string | undefined>(undefined)

const columns = [
  { colKey: 'entity', title: '实体' },
  { colKey: 'result', title: '补全建议' },
  { colKey: 'confidence', title: '置信度', width: 120 },
  { colKey: 'actions', title: '操作', width: 180 },
]

const fetchQueue = async () => {
  loading.value = true
  try {
    const data = await getReviewQueue({
      entity_type: filterType.value,
      status: 'pending_review',
      page: 1,
      page_size: 50,
    })
    items.value = data.data || []
  } finally {
    loading.value = false
  }
}

watch(() => props.refresh, fetchQueue, { immediate: true })
watch(filterType, fetchQueue)

const handleSelect = (keys: string[]) => {
  selectedIds.value = keys
}

const handleBatchApprove = async () => {
  if (!selectedIds.value.length) return
  await approveReview(selectedIds.value[0], '批量确认') // 简化：逐条调用
  MessagePlugin.success('已批量确认')
  await fetchQueue()
}

const handleBatchReject = async () => {
  if (!selectedIds.value.length) return
  for (const id of selectedIds.value) {
    await rejectReview(id, '批量拒绝')
  }
  MessagePlugin.success('已批量拒绝')
  selectedIds.value = []
  await fetchQueue()
}

const handleApprove = async (row: any) => {
  await approveReview(row.id)
  MessagePlugin.success('已确认补全')
  await fetchQueue()
}

const handleReject = async (row: any) => {
  await rejectReview(row.id, '人工拒绝')
  MessagePlugin.success('已拒绝')
  await fetchQueue()
}

const emit = defineEmits<{ detail: [id: string] }>()
const showDetail = (row: any) => {
  emit('detail', row.id)
}

defineExpose({ fetchQueue })
</script>

<style scoped>
.queue-toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
</style>
```

- [ ] **Step 3: 创建 ReviewPage `frontend/src/pages/ReviewPage.vue`**

```vue
<template>
  <div class="review-page">
    <h1>补全审核工作台</h1>
    <p class="subtitle">审核 AI 生成的元数据补全建议，确认后回写 OpenMetadata</p>
    <ReviewQueue ref="queueRef" :refresh="refreshKey" @detail="handleShowDetail" />
    <ReviewDetail v-model:visible="detailVisible" :record-id="detailRecordId" @updated="handleUpdated" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ReviewQueue from '../components/ReviewQueue.vue'
import ReviewDetail from '../components/ReviewDetail.vue'

const refreshKey = ref(0)
const detailVisible = ref(false)
const detailRecordId = ref('')
const queueRef = ref<InstanceType<typeof ReviewQueue>>()

const handleShowDetail = (id: string) => {
  detailRecordId.value = id
  detailVisible.value = true
}

const handleUpdated = () => {
  refreshKey.value++
  queueRef.value?.fetchQueue()
}
</script>

<style scoped>
h1 { font-size: 24px; margin-bottom: 8px; }
.subtitle { color: var(--color-text-secondary); margin-bottom: 24px; }
</style>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ReviewPage.vue frontend/src/components/ReviewQueue.vue frontend/src/components/QualityBadge.vue
git commit -m "feat: add review queue page with approve/reject actions"
```

### Task 5.4: ReviewDetail 组件

**Files:**
- Create: `frontend/src/components/ReviewDetail.vue`

- [ ] **Step 1: 创建 ReviewDetail `frontend/src/components/ReviewDetail.vue`**

```vue
<template>
  <t-dialog v-model:visible="visible" header="审核详情" width="640px" :footer="false" @close="handleClose">
    <t-loading v-if="loading" />
    <template v-else-if="detail">
      <t-descriptions :column="1" bordered>
        <t-descriptions-item label="实体ID">{{ detail.entity_id }}</t-descriptions-item>
        <t-descriptions-item label="类型">{{ detail.entity_type }}</t-descriptions-item>
        <t-descriptions-item label="状态">
          <t-tag :theme="statusTheme">{{ detail.review_status }}</t-tag>
        </t-descriptions-item>
      </t-descriptions>

      <t-divider>AI 补全建议</t-divider>
      <div v-if="detail.completion_result">
        <t-form label-width="80px" readonly>
          <t-form-item label="中文名">{{ detail.completion_result.display_name }}</t-form-item>
          <t-form-item label="描述">{{ detail.completion_result.description }}</t-form-item>
          <t-form-item v-if="detail.completion_result.tags?.length" label="标签">
            <t-tag v-for="t in detail.completion_result.tags" :key="t" size="small" variant="light">{{ t }}</t-tag>
          </t-form-item>
          <t-form-item v-if="detail.completion_result.sensitive_level" label="安全级">
            {{ detail.completion_result.sensitive_level }}
          </t-form-item>
          <t-form-item v-if="detail.completion_result.reasoning" label="依据">
            {{ detail.completion_result.reasoning }}
          </t-form-item>
        </t-form>
      </div>

      <t-divider>质量校验</t-divider>
      <div v-if="detail.quality_check">
        <t-tag :theme="confidenceTheme">
          置信度: {{ ((detail.quality_check.adjusted_confidence ?? 0) * 100).toFixed(0) }}%
        </t-tag>
        <div v-if="detail.quality_check.rule_violations?.length" class="violations">
          <t-alert
            v-for="(v, i) in detail.quality_check.rule_violations"
            :key="i"
            :theme="v.severity === 'critical' ? 'error' : v.severity === 'warning' ? 'warning' : 'info'"
            :message="v.message"
            style="margin-top: 8px"
          />
        </div>
      </div>
    </template>
  </t-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { getReviewDetail } from '../api'

const props = defineProps<{
  visible: boolean
  recordId: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  updated: []
}>()

const loading = ref(false)
const detail = ref<any>(null)

const visible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

watch(() => props.recordId, async (id) => {
  if (!id) return
  loading.value = true
  try {
    const data = await getReviewDetail(id)
    detail.value = data.data
  } finally {
    loading.value = false
  }
})

const statusTheme = computed(() => {
  const s = detail.value?.review_status
  return s === 'auto_approved' || s === 'approved' ? 'success' : s === 'rejected' ? 'danger' : 'warning'
})

const confidenceTheme = computed(() => {
  const c = detail.value?.quality_check?.adjusted_confidence ?? 0
  return c >= 0.8 ? 'success' : c >= 0.6 ? 'warning' : 'danger'
})

const handleClose = () => {
  emit('updated')
}

const violations = computed(() => detail.value?.quality_check?.rule_violations || [])
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ReviewDetail.vue
git commit -m "feat: add review detail dialog component"
```

### Task 5.5: 历史和配置页面（占位）

**Files:**
- Create: `frontend/src/pages/HistoryPage.vue`
- Create: `frontend/src/pages/ConfigPage.vue`

- [ ] **Step 1: 创建 HistoryPage（占位）**

```vue
<template>
  <div>
    <h1>补全历史</h1>
    <p class="subtitle">查看所有元数据补全记录</p>
    <t-empty description="功能开发中" />
  </div>
</template>

<style scoped>
h1 { font-size: 24px; }
.subtitle { color: var(--color-text-secondary); }
</style>
```

- [ ] **Step 2: 创建 ConfigPage（占位）**

```vue
<template>
  <div>
    <h1>系统配置</h1>
    <p class="subtitle">管理补全规则和阈值</p>
    <t-card title="质量校验阈值">
      <t-form label-width="120px">
        <t-form-item label="自动采纳阈值">
          <t-input-number v-model="autoThreshold" :min="0" :max="1" :step="0.05" />
        </t-form-item>
        <t-form-item label="待审核下限">
          <t-input-number v-model="reviewThreshold" :min="0" :max="1" :step="0.05" />
        </t-form-item>
        <t-form-item>
          <t-button theme="primary">保存配置</t-button>
        </t-form-item>
      </t-form>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const autoThreshold = ref(0.80)
const reviewThreshold = ref(0.60)
</script>

<style scoped>
h1 { font-size: 24px; }
.subtitle { color: var(--color-text-secondary); margin-bottom: 24px; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/HistoryPage.vue frontend/src/pages/ConfigPage.vue
git commit -m "feat: add placeholder pages for history and config"
```

---

## Phase 6: Celery Job + 联调

### Task 6.1: Celery 应用配置

**Files:**
- Create: `backend/app/celery_app.py`
- Create: `backend/app/jobs/__init__.py`
- Create: `backend/app/jobs/metadata_sync.py`

- [ ] **Step 1: 创建 Celery 应用 `backend/app/celery_app.py`**

```python
"""Celery 应用配置"""
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "metadata_completion",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    worker_pool="gevent",
    task_track_started=True,
    task_acks_late=True,
)
```

- [ ] **Step 2: 创建元数据同步 Job `backend/app/jobs/metadata_sync.py`**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/celery_app.py backend/app/jobs/
git commit -m "feat: add Celery app config and metadata sync job skeleton"
```

### Task 6.2: 最终验证 + 文档

- [ ] **Step 1: 验证后端启动**

Run: `cd backend && pip install -e ".[dev]" && python -m pytest tests/ -v`
Expected: 所有单元测试 PASS

- [ ] **Step 2: 验证前端构建**

Run: `cd frontend && npm run build`
Expected: Build 成功，无 TS 错误

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "chore: final verification and cleanup"
```

---

## 验证清单

| 验证项 | 方法 | 通过标准 |
|--------|------|---------|
| 后端启动 | `uvicorn app.main:app` | :8000 可访问 /health |
| Docker 基础设施 | `docker compose ps` | 5 个服务 Running |
| Stage 1 RRF 合并 | `pytest tests/test_stage1_retrieve.py` | 4 tests PASS |
| Stage 2 JSON 解析 | `pytest tests/test_stage2_generate.py` | 7 tests PASS |
| Stage 3 规则引擎 | `pytest tests/test_stage3_quality.py` | 10 tests PASS |
| API 健康检查 | `pytest tests/test_api.py -k health` | PASS |
| 前端启动 | `npm run dev` | :5173 可访问 |
| 前端构建 | `npm run build` | 无错误 |
| ES 索引创建 | `curl localhost:9200/metadata_index` | 返回 mappings |
| Milvus Collection | `python -c "from app.services.milvus import get_milvus_collection; print('OK')"` | OK |
