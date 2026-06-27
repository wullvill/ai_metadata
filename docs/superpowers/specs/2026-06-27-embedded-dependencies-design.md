# 嵌入式依赖替换 — 设计文档

> 版本: v1.0 | 日期: 2026-06-27 | 状态: 设计完成

---

## 1. 目标

将开发/演示环境中 7 个基础设施容器（PostgreSQL、Milvus、etcd、MinIO、Elasticsearch、Redis、Celery Worker）替换为嵌入式方案，实现 `pip install` + `python main.py` 即可启动，无需 docker compose。

生产环境仍可通过配置切换回外部服务。

## 2. 组件替换方案

| 组件 | 当前 | 替换为 | 新增 pip 依赖 | 移除 pip 依赖 |
|------|------|--------|-------------|-------------|
| 数据库 | PostgreSQL | SQLite（dev 已用，无变化） | — | — |
| 向量检索 | Milvus (含 etcd+MinIO) | ChromaDB 持久化模式 | `chromadb>=0.5` | `pymilvus>=2.4` |
| 关键词检索 | Elasticsearch 8.x | Tantivy + jieba 分词 | `tantivy>=0.22`, `jieba>=0.42` | `elasticsearch>=8.15` |
| Celery broker | Redis | SQLite broker | — | `redis>=5.0` |
| Celery result backend | Redis | SQLite db backend | — | — |

**容器数：7 → 0**（仅保留后端 + 前端两个应用容器）

## 3. 架构对比

```
之前: docker compose up (7 容器)
┌────────────────────────────────────────┐
│ postgres  redis  etcd  minio           │
│ milvus    elasticsearch  celery_worker │
└────────────────────────────────────────┘

之后: python app/main.py (0 容器)
┌────────────────────────────────────────┐
│ 嵌入式依赖 (Python 进程内)             │
│ ├── chromadb    → data/chroma/         │
│ ├── tantivy     → data/tantivy/        │
│ ├── sqlite3     → data/metadata.db     │
│ └── celery[sql] → data/celery.db       │
└────────────────────────────────────────┘
```

数据全部存储在 `data/` 目录下，挂载到容器卷即可持久化。

## 4. 各组件详细设计

### 4.1 数据库 — SQLite 不变

开发现有已使用 SQLite + aiosqlite + SQLAlchemy，无需任何改动。

### 4.2 异步队列 — Celery 配 SQLite broker

```python
# backend/app/config.py
CELERY_BROKER_URL = "sqla+sqlite:///data/celery.db"
CELERY_RESULT_BACKEND = "db+sqlite:///data/celery.db"
```

SQLite broker 在低并发演示场景足够，高并发生产环境切回 Redis。

### 4.3 向量检索 — ChromaDB 替换 Milvus

**新建文件**: `backend/app/services/vector_store.py`（替代 `services/milvus.py`）

ChromaDB 与 Milvus 的 API 对比：

| 操作 | Milvus | ChromaDB |
|------|--------|----------|
| 初始化 | `connections.connect()` + `Collection()` | `PersistentClient(path=...)` |
| 创建 Collection | `Collection(name, schema)` | `get_or_create_collection(name, metadata)` |
| 插入 | `collection.insert(data)` | `collection.add(ids, embeddings, metadatas)` |
| 查询 | `collection.search(expr=...)` | `collection.query(where=...)` |
| 相似度 | COSINE (索引参数) | `hnsw:space=cosine` (metadata) |
| 过滤 | `filter="has_description==true"` | `where={"has_description": True}` |
| 删除 | `collection.delete(expr=...)` | `collection.delete(ids=...)` |

关键差异：
- Milvus 的 `FieldSchema` → ChromaDB 的 `metadata` dict（自动索引用于过滤）
- 不再需要 etcd/MinIO 依赖
- ChromaDB 底层也使用 SQLite 持久化

### 4.4 关键词检索 — Tantivy 替换 Elasticsearch

**新建文件**: `backend/app/services/search_index.py`（替代 `services/elasticsearch.py`）

Tantivy 与 ES 的 API 对比：

| 操作 | ES | Tantivy |
|------|-----|---------|
| 创建索引 | `indices.create(mappings=...)` | `SchemaBuilder().build()` + `Index(schema, path)` |
| 写入 | `bulk(body=docs)` HTTP | `writer.add_document()` + `commit()` 本地文件 |
| 查询 | `search(query=multi_match)` HTTP | `index.parse_query()` + `searcher.search()` 本地 |
| 中文分词 | ik_max_word (插件) | jieba (Python 注册 tokenizer) |
| fuzzy 查询 | fuzziness=AUTO | 不支持，用 prefix/term 替代 |

关键差异：
- ES HTTP 协议请求 → Tantivy 本地文件操作（零网络开销）
- ik_max_word → jieba 分词（精度略降但演示够用）
- 不支持 fuzzy 查询，使用 Tantivy 的 term/prefix 查询替代模糊匹配

### 4.5 检索流程不变

```
Stage 1 双路检索保持不变：
  输入 → embedding (百炼 text-embedding-v3)
       → ChromaDB.search() ──────┐
       → Tantivy.search() ───────┤
                                  ├── RRF 合并 → Top 15 → Stage 2
```

`stage1_retrieve.py` 只需修改 import 和服务类名，核心 RRF 算法、检索流程、上下文增强逻辑全部不变。

## 5. docker-compose.yml 简化

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
```

移除了 etcd、minio、milvus、elasticsearch、redis、postgres 六个服务。

## 6. 配置切换——嵌入模式 vs 生产模式

通过 `DEPLOYMENT_MODE` 环境变量控制：

```python
# backend/app/config.py
class Settings(BaseSettings):
    DEPLOYMENT_MODE: Literal["embedded", "production"] = "embedded"

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///data/metadata.db"

    # 向量检索
    @property
    def vector_store_backend(self) -> str:
        if self.DEPLOYMENT_MODE == "embedded":
            return "chroma"    # data/chroma/
        return "milvus"

    # 关键词检索
    @property
    def search_index_backend(self) -> str:
        if self.DEPLOYMENT_MODE == "embedded":
            return "tantivy"   # data/tantivy/
        return "elasticsearch"

    # 异步队列
    @property
    def celery_broker_url(self) -> str:
        if self.DEPLOYMENT_MODE == "embedded":
            return "sqla+sqlite:///data/celery.db"
        return "redis://localhost:6379/0"
```

## 7. 影响范围

### 需要修改的文件

| 文件 | 改动 |
|------|------|
| `backend/requirements.txt` | 替换依赖 |
| `backend/app/config.py` | 添加 DEPLOYMENT_MODE 配置 |
| `backend/app/services/milvus.py` → `vector_store.py` | ChromaDB 实现 |
| `backend/app/services/elasticsearch.py` → `search_index.py` | Tantivy 实现 |
| `backend/app/pipeline/stage1_retrieve.py` | 更新 import |
| `backend/app/jobs/es_sync.py` | 更新同步目标 |
| `backend/app/api/search.py` | 更新服务调用 |
| `docker-compose.yml` | 简化为 2 服务 |

### 不需要修改的文件

- 前端全部代码
- LangGraph Pipeline 核心逻辑 (stage2/stage3/stage4)
- API 路由接口
- ORM 数据模型
- embedding 服务 (仍用百炼 text-embedding-v3)

## 8. 依赖变更清单

```diff
# backend/requirements.txt
- pymilvus>=2.4.0
- elasticsearch>=8.15.0,<9.0.0
- redis>=5.0.0
+ chromadb>=0.5.0
+ tantivy>=0.22.0
+ jieba>=0.42.0
```

## 9. 风险与缓解

| 风险 | 缓解 |
|------|------|
| Tantivy Python 绑定不稳定 | 封装统一接口，异常时降级到简单 LIKE 查询 |
| ChromaDB 并发写入性能 | 演示环境单用户，不做并发优化；生产切 Milvus |
| SQLite broker 锁竞争 | 演示环境串行任务，无竞争；生产切 Redis |
| jieba 中文分词不如 ik_max_word | 演示环境检索精度要求低，可接受 |

## 10. 验收标准

- [ ] `docker compose up` 仅启动 backend + frontend 两个服务
- [ ] 搜索页面能正常返回结果（ChromaDB + Tantivy 双路检索）
- [ ] 补全功能端到端流程通过（检索 → LLM 生成 → 质量校验 → 审核）
- [ ] Celery 异步任务正常执行（SQLite broker）
- [ ] `DEPLOYMENT_MODE=production` 仍可切回原服务
- [ ] 数据持久化到 `data/` 目录，重启不丢失
