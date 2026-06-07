# 审批通过 ES 回写 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 审批通过后将表和字段的补全结果异步回写到 ES 的 metadata_index 和 metadata_columns 索引

**Architecture:** approve_review 端点改造为级联通过字段 + 派发 Celery 任务；elasticsearch.py 新增两个回写函数用 es.update() 部分更新文档；新建 jobs/es_sync.py 作为 Celery 任务入口

**Tech Stack:** Python/FastAPI/SQLAlchemy/Celery/Elasticsearch

---

### Task 1: 新建 ES 回写服务函数

**Files:**
- Modify: `backend/app/services/elasticsearch.py`（末尾追加）

- [ ] **Step 1: 新增 `update_completed_metadata` 函数**

在 `backend/app/services/elasticsearch.py` 末尾追加：

```python
def update_completed_metadata(entity_id: str, completion_result: dict) -> bool:
    """将审批通过的补全结果回写到 metadata_index。返回 True 表示成功。"""
    es = get_es_client()
    try:
        doc = {
            "display_name": completion_result.get("display_name", ""),
            "description": completion_result.get("description", ""),
            "tags": completion_result.get("tags", []),
            "has_description": True,
        }
        es.update(index=INDEX_NAME, id=entity_id, doc=doc)
        return True
    except NotFoundError:
        logger.warning(f"ES update skipped: {entity_id} not found in {INDEX_NAME}")
        return False
    except Exception as e:
        logger.error(f"ES update failed for {entity_id}: {e}")
        return False
```

- [ ] **Step 2: 新增 `update_completed_columns` 函数**

紧接着追加：

```python
def update_completed_columns(entity_id: str, columns_data: list[dict]) -> int:
    """批量回写字段补全结果到 metadata_columns。返回成功更新的数量。

    columns_data 每项包含: name (列名), description, tags
    """
    if not columns_data:
        return 0
    es = get_es_client()
    from datetime import datetime, timezone

    updated = 0
    for col in columns_data:
        col_id = f"{entity_id}.{col['name']}"
        try:
            doc = {
                "completion_description": col.get("description", ""),
                "completion_tags": col.get("tags", []),
                "completion_time": datetime.now(timezone.utc).isoformat(),
            }
            es.update(index=COLUMNS_INDEX, id=col_id, doc=doc)
            updated += 1
        except NotFoundError:
            logger.warning(f"Column ES update skipped: {col_id} not found")
        except Exception as e:
            logger.warning(f"Column ES update failed for {col_id}: {e}")
    return updated
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/elasticsearch.py
git commit -m "feat: add update_completed_metadata and update_completed_columns ES writeback functions"
```

---

### Task 2: 新建 Celery 异步回写任务

**Files:**
- Create: `backend/app/jobs/es_sync.py`
- Modify: `backend/app/celery_app.py`（注册新任务）
- Modify: `backend/app/database.py`（新增同步 session）

- [ ] **Step 1: database.py 新增同步 SessionLocal**

在 `backend/app/database.py` 的 `async_session` 定义之后追加同步引擎和 session：

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# 同步引擎（供 Celery 任务使用），将 async 驱动替换为同步驱动
_sync_url = settings.database_url.replace("+asyncpg", "+psycopg2").replace("+aiosqlite", "")
sync_engine = create_engine(_sync_url, echo=settings.debug)
SessionLocal = sessionmaker(bind=sync_engine, class_=Session, expire_on_commit=False)
```

- [ ] **Step 2: 创建 `backend/app/jobs/es_sync.py`**

```python
"""ES 回写异步任务"""
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.completion import CompletionRecord
from app.services.elasticsearch import update_completed_metadata, update_completed_columns
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="es_sync_approval", bind=True, max_retries=3, default_retry_delay=60)
def sync_approval_to_es(self, record_id: str):
    """审批通过后异步回写 ES"""
    db = SessionLocal()
    try:
        record = db.query(CompletionRecord).filter(
            CompletionRecord.id == record_id
        ).first()

        if not record or not record.completion_result:
            logger.warning(f"sync_approval_to_es: record {record_id} not found or no result")
            return {"status": "skipped", "record_id": record_id}

        # 回写表
        table_ok = update_completed_metadata(
            record.entity_id, record.completion_result
        )

        # 回写字段
        if record.entity_type == "table":
            prefix = record.entity_id + ".%"
            columns = db.query(CompletionRecord).filter(
                CompletionRecord.entity_type == "column",
                CompletionRecord.entity_id.like(prefix),
            ).all()

            columns_data = [
                {
                    "name": c.entity_id.split(".")[-1],
                    "description": (c.completion_result or {}).get("description", ""),
                    "tags": (c.completion_result or {}).get("tags", []),
                }
                for c in columns
                if c.completion_result
            ]
            col_count = update_completed_columns(record.entity_id, columns_data)
        else:
            col_count = 0

        logger.info(
            f"ES sync done: {record.entity_id} table={table_ok} columns={col_count}"
        )
        return {"status": "done", "record_id": record_id, "table_ok": table_ok, "columns": col_count}
    except Exception as e:
        logger.error(f"sync_approval_to_es failed for {record_id}: {e}")
        raise self.retry(exc=e)
    finally:
        db.close()
```

- [ ] **Step 3: 注册 Celery 任务**

在 `backend/app/celery_app.py` 第 11 行的 `include` 列表中添加 `es_sync`：

```python
celery_app = Celery(
    "metadata_completion",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.jobs.metadata_sync", "app.jobs.es_sync"],
)
```

- [ ] **Step 4: 验证导入**

```bash
cd backend && source .venv/bin/activate && python -c "from app.jobs.es_sync import sync_approval_to_es; print('import ok')"
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/jobs/es_sync.py backend/app/celery_app.py backend/app/database.py
git commit -m "feat: add Celery task for async ES writeback on approval"
```

---

### Task 3: 改造 `approve_review` 端点

**Files:**
- Modify: `backend/app/api/review.py:232-259`

- [ ] **Step 1: 替换 `approve_review` 函数体**

将 `backend/app/api/review.py` 中 `approve_review` 端点（第 232-259 行）替换为：

```python
@router.post("/{record_id}/approve")
async def approve_review(
    record_id: str,
    req: ReviewActionRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """确认补全 — 表级审批级联通过所有字段，异步回写 ES"""
    result = await db.execute(
        select(CompletionRecord).where(CompletionRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    reviewer = (req.reviewer if req and req.reviewer else "admin")
    now = datetime.now(timezone.utc)

    # 更新表记录
    record.review_status = "approved"
    record.reviewer = reviewer
    record.review_comment = req.comment if req else None
    record.reviewed_at = now

    cascade_count = 0
    if record.entity_type == "table":
        prefix = record.entity_id + ".%"
        col_result = await db.execute(
            select(CompletionRecord).where(
                CompletionRecord.entity_type == "column",
                CompletionRecord.entity_id.like(prefix),
            )
        )
        for col in col_result.scalars().all():
            col.review_status = "approved"
            col.reviewer = reviewer
            col.reviewed_at = now
            cascade_count += 1

    log = AuditLog(
        entity_id=record.entity_id, action="manual_approve",
        operator=reviewer,
        detail={"record_id": record_id, "cascade_columns": cascade_count},
    )
    db.add(log)
    await db.commit()

    # 异步回写 ES
    from app.jobs.es_sync import sync_approval_to_es
    sync_approval_to_es.delay(record.id)

    logger.info(f"Review approved: {record_id} -> {record.entity_id}, cascade={cascade_count}")
    return {"success": True, "data": {"status": "approved", "cascade_columns": cascade_count}}
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/api/review.py
git commit -m "feat: cascade column approval and dispatch ES sync on approve"
```

---

### Task 4: 编写测试

**Files:**
- Create: `backend/tests/test_es_sync.py`

- [ ] **Step 1: 创建测试文件 `backend/tests/test_es_sync.py`**

```python
"""测试 ES 回写函数"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.elasticsearch import update_completed_metadata, update_completed_columns


class TestUpdateCompletedMetadata:
    def test_success(self):
        with patch("app.services.elasticsearch.get_es_client") as mock_es:
            client = MagicMock()
            mock_es.return_value = client

            result = update_completed_metadata(
                "db.schema.table",
                {"display_name": "用户表", "description": "存储用户信息", "tags": ["用户"]},
            )

            assert result is True
            client.update.assert_called_once()

    def test_not_found(self):
        with patch("app.services.elasticsearch.get_es_client") as mock_es:
            from elasticsearch import NotFoundError
            client = MagicMock()
            client.update.side_effect = NotFoundError()
            mock_es.return_value = client

            result = update_completed_metadata(
                "db.schema.missing",
                {"display_name": "X", "description": "Y", "tags": []},
            )

            assert result is False


class TestUpdateCompletedColumns:
    def test_success(self):
        with patch("app.services.elasticsearch.get_es_client") as mock_es:
            client = MagicMock()
            mock_es.return_value = client

            count = update_completed_columns(
                "db.schema.table",
                [
                    {"name": "col_a", "description": "字段A", "tags": ["核心"]},
                    {"name": "col_b", "description": "字段B", "tags": []},
                ],
            )

            assert count == 2
            assert client.update.call_count == 2

    def test_empty_columns(self):
        count = update_completed_columns("db.schema.table", [])
        assert count == 0

    def test_skips_not_found(self):
        with patch("app.services.elasticsearch.get_es_client") as mock_es:
            from elasticsearch import NotFoundError
            client = MagicMock()
            client.update.side_effect = [None, NotFoundError(), None]
            mock_es.return_value = client

            count = update_completed_columns(
                "db.schema.table",
                [
                    {"name": "col_a", "description": "A", "tags": []},
                    {"name": "col_b", "description": "B", "tags": []},
                    {"name": "col_c", "description": "C", "tags": []},
                ],
            )

            assert count == 2  # col_b skipped
            assert client.update.call_count == 3
```

- [ ] **Step 2: 运行测试**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_es_sync.py -v
```

- [ ] **Step 3: 运行全部测试确认无回归**

```bash
cd backend && source .venv/bin/activate && pytest tests/ -v
```

- [ ] **Step 4: 提交**

```bash
git add backend/tests/test_es_sync.py
git commit -m "test: add unit tests for ES writeback functions"
```

---

### 验证清单

- [ ] `update_completed_metadata` 成功更新 metadata_index 文档
- [ ] `update_completed_metadata` 文档不存在时返回 False 且不崩溃
- [ ] `update_completed_columns` 正确批量更新 metadata_columns
- [ ] `update_completed_columns` 跳过不存在的文档，返回正确计数
- [ ] Celery 任务 `sync_approval_to_es` 可正确导入
- [ ] approve_review 表审批时级联通过所有字段
- [ ] approve_review 完成后派发 Celery 任务
- [ ] 响应中包含 `cascade_columns` 字段
- [ ] 全部已有测试无回归
