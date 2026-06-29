# parent_record_id 关联实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 completion_records 表新增 parent_record_id 字段，精准关联 table 记录与 column 记录，替代 LIKE 前缀匹配，解决字段补全重复显示问题。

**Architecture:** 新增 Alembic 迁移添加列和索引；ORM 模型新增字段；complete.py 触发时标记旧记录为 superseded 并按批次写入 parent_record_id；review.py 的 columns 查询和 approve 级联改为按 parent_record_id 精准匹配。

**Tech Stack:** SQLAlchemy 2.0 + Alembic + SQLite / PostgreSQL

## Global Constraints

- SQLite 兼容：ALTER TABLE ADD COLUMN 语法
- 已有数据 parent_record_id 为 NULL，不破坏现有功能
- 前端无改动

---

### Task 1: Alembic 迁移 + ORM 模型

**Files:**
- Create: `backend/alembic/versions/xxxx_add_parent_record_id.py`
- Modify: `backend/app/models/completion.py:23-24`

**Interfaces:**
- Produces: `CompletionRecord.parent_record_id` (nullable String(36), indexed)

- [ ] **Step 1: 生成空迁移**

```bash
cd backend && source .venv/bin/activate && alembic revision -m "add parent_record_id to completion_records"
```

- [ ] **Step 2: 写迁移升级脚本**

用实际生成的 revision id 替换 `xxxx`，编辑迁移文件：

```python
"""add parent_record_id to completion_records

Revision ID: {auto_generated}
Revises: 05b83e3bfc58
Create Date: {auto_generated}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '{auto_generated}'
down_revision: Union[str, Sequence[str], None] = '05b83e3bfc58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "completion_records",
        sa.Column("parent_record_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_completion_records_parent_record_id",
        "completion_records",
        ["parent_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_completion_records_parent_record_id", "completion_records")
    op.drop_column("completion_records", "parent_record_id")
```

- [ ] **Step 3: 更新 ORM 模型**

编辑 `backend/app/models/completion.py`，在 `synced_at` 之后新增：

```python
parent_record_id: Mapped[str | None] = mapped_column(
    String(36), nullable=True, index=True, default=None,
)
```

- [ ] **Step 4: 运行迁移**

```bash
cd backend && source .venv/bin/activate && alembic upgrade head
```

预期输出: `INFO  [alembic.runtime.migration] Running upgrade ...`

- [ ] **Step 5: 提交**

```bash
git add backend/alembic/versions/xxxx_add_parent_record_id.py backend/app/models/completion.py
git commit -m "feat: add parent_record_id to completion_records for batch linking"
```

---

### Task 2: 补全触发 — 过期标记 + parent_record_id 级联

**Files:**
- Modify: `backend/app/api/complete.py:17-91`

**Interfaces:**
- Consumes: `CompletionRecord.parent_record_id`（Task 1）
- Produces: superseded 旧记录；新 column 记录带 parent_record_id

- [ ] **Step 1: 新增过期标记辅助函数**

在 `_fetch_columns` 之前插入：

```python
async def _supersede_old(db: AsyncSession, entity_id: str) -> int:
    """Mark pending/auto_approved records for the same entity as superseded."""
    from sqlalchemy import update as sql_update
    result = await db.execute(
        sql_update(CompletionRecord)
        .where(
            CompletionRecord.entity_id == entity_id,
            CompletionRecord.review_status.in_(["pending_review", "auto_approved"]),
        )
        .values(review_status="superseded")
    )
    return result.rowcount
```

- [ ] **Step 2: 触发补全时调用过期标记**

在 `target = req.target.model_dump(by_alias=True)` 之后，`pipeline.ainvoke` 之前插入：

```python
await _supersede_old(db, target["entity_id"])
```

- [ ] **Step 3: 列级联写入 parent_record_id**

列级联中 `CompletionRecord(...)` 新增 `parent_record_id=record.id`：

```python
col_record = CompletionRecord(
    entity_id=col_target["entity_id"],
    entity_type="column",
    target_data=col_target,
    completion_result=col_state.get("completion_result"),
    quality_check=col_state.get("quality_check"),
    review_status=col_state.get("review_status") or "rejected",
    parent_record_id=record.id,
)
```

- [ ] **Step 4: 手动验证**

```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000 &
sleep 2

# 触发 2 次补全
curl -s -X POST http://localhost:8000/api/v1/complete/trigger/manual \
  -H "Content-Type: application/json" \
  -d '{"target":{"entity_id":"test_batch_01","entity_type":"table","database":"test","schema":"test","table_name":"test_batch_01","columns":[{"name":"col_a","dataType":"varchar"}]}}' > /dev/null

curl -s -X POST http://localhost:8000/api/v1/complete/trigger/manual \
  -H "Content-Type: application/json" \
  -d '{"target":{"entity_id":"test_batch_01","entity_type":"table","database":"test","schema":"test","table_name":"test_batch_01","columns":[{"name":"col_a","dataType":"varchar"}]}}' > /dev/null

# 检查 DB
python3 -c "
import sqlite3
conn = sqlite3.connect('data/metadata.db')
rows = conn.execute(\"SELECT entity_id, entity_type, review_status, parent_record_id FROM completion_records WHERE entity_id LIKE 'test_batch_01%' ORDER BY entity_id, created_at\").fetchall()
for r in rows: print(r)
conn.close()
"
```

预期：table 的第 1 条 `superseded`，第 2 条 `pending_review`/`auto_approved`；column 同理，且第 2 条的 `parent_record_id` = 第 2 条 table record 的 id。

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/complete.py
git commit -m "feat: supersede old records and set parent_record_id on column cascade"
```

---

### Task 3: columns 查询 API 改为 parent_record_id

**Files:**
- Modify: `backend/app/api/review.py:83-121`

**Interfaces:**
- Consumes: `CompletionRecord.parent_record_id`（Task 1）

- [ ] **Step 1: 修改 `get_record_columns` 查询**

将查询改为按 `parent_record_id` 精准匹配（删除 `prefix = record.entity_id + ".%"`）：

```python
result = await db.execute(
    select(CompletionRecord)
    .where(
        CompletionRecord.entity_type == "column",
        CompletionRecord.parent_record_id == record_id,
    )
    .order_by(CompletionRecord.entity_id)
)
```

- [ ] **Step 2: 验证**

```bash
# 获取第 2 次的 record id
RECORD_ID=$(python3 -c "import sqlite3; conn=sqlite3.connect('data/metadata.db'); r=conn.execute(\"SELECT id FROM completion_records WHERE entity_id='test_batch_01' AND review_status!='superseded' ORDER BY created_at DESC LIMIT 1\").fetchone(); print(r[0] if r else '')")

# 查列
curl -s "http://localhost:8000/api/v1/review/$RECORD_ID/columns" | python3 -c "
import json,sys
d=json.load(sys.stdin)
cols=d.get('data',[])
print(f'{len(cols)} columns (expected: 1)')
"
```

预期：仅返回 1 列（而非所有历史批次的重复列）。

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/review.py
git commit -m "refactor: use parent_record_id for column lookup instead of LIKE prefix matching"
```

---

### Task 4: 审批级联改为 parent_record_id

**Files:**
- Modify: `backend/app/api/review.py:244-258`

- [ ] **Step 1: 修改审批级联查询**

将 `approve_review` 中的级联查询改为按 `parent_record_id`：

```python
if record.entity_type == "table":
    col_result = await db.execute(
        select(CompletionRecord).where(
            CompletionRecord.entity_type == "column",
            CompletionRecord.parent_record_id == record_id,
        )
    )
    for col in col_result.scalars().all():
        col.review_status = "approved"
        col.reviewer = reviewer
        col.reviewed_at = now
        cascade_count += 1
```

删除 `escaped = re.sub(r"([%_])", r"\\\1", record.entity_id)` 和 `prefix = escaped + ".%"`。

检查 `import re` 是否仅在 LIKE 转义中使用，若是则删除该 import。

- [ ] **Step 2: 验证**

```bash
# 审批通过第 2 次补全
curl -s -X POST "http://localhost:8000/api/v1/review/$RECORD_ID/approve" \
  -H "Content-Type: application/json" \
  -d '{"reviewer":"test"}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'cascade={d[\"data\"][\"cascade_columns\"]}')"

# 检查：仅当前批次列为 approved
python3 -c "
import sqlite3
conn = sqlite3.connect('data/metadata.db')
rows = conn.execute(\"SELECT entity_id, review_status FROM completion_records WHERE entity_id LIKE 'test_batch_01%' ORDER BY entity_id, created_at\").fetchall()
for r in rows: print(r)
conn.close()
"
```

预期：第 1 次 column records 保持 `superseded`，第 2 次 column records 变为 `approved`。

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/review.py
git commit -m "refactor: use parent_record_id for approve cascade instead of LIKE prefix matching"
```

---

### Task 5: 更新测试

**Files:**
- Modify: `backend/tests/test_review_columns.py`

- [ ] **Step 1: 更新 fixture，column 记录添加 parent_record_id**

- [ ] **Step 2: 新增多批次隔离测试**

```python
@pytest.mark.asyncio
async def test_get_columns_only_returns_current_batch(db_session):
    """两个批次的列记录不会互相干扰"""
    from app.models.completion import CompletionRecord

    b1 = CompletionRecord(id="b1-table", entity_id="db.s.t", entity_type="table",
                          target_data={}, review_status="superseded")
    b2 = CompletionRecord(id="b2-table", entity_id="db.s.t", entity_type="table",
                          target_data={}, review_status="pending_review")
    db.add_all([b1, b2])
    await db.flush()

    for i in range(2):
        db.add(CompletionRecord(id=f"b1-col-{i}", entity_id=f"db.s.t.col_{i}",
                entity_type="column", parent_record_id="b1-table",
                target_data={}, review_status="superseded"))
    for i in range(2):
        db.add(CompletionRecord(id=f"b2-col-{i}", entity_id=f"db.s.t.col_{i}",
                entity_type="column", parent_record_id="b2-table",
                target_data={}, review_status="pending_review"))
    await db.commit()

    from sqlalchemy import select
    result = await db.execute(
        select(CompletionRecord).where(
            CompletionRecord.entity_type == "column",
            CompletionRecord.parent_record_id == "b2-table",
        )
    )
    cols = result.scalars().all()
    assert len(cols) == 2
    for c in cols:
        assert c.parent_record_id == "b2-table"
```

- [ ] **Step 3: 运行全部测试**

```bash
cd backend && source .venv/bin/activate && pytest tests/ -v
```

- [ ] **Step 4: 提交**

```bash
git add backend/tests/test_review_columns.py
git commit -m "test: update review columns tests for parent_record_id linking"
```
