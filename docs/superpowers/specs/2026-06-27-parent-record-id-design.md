# 审核工作台字段补全去重 — parent_record_id 关联设计

**日期**: 2026-06-27  
**状态**: 已确认

## 问题

同一资产多次申请补全后，审核详情的「字段补全」Tab 中每个字段出现多条补全记录。根因：`GET /review/{recordId}/columns` 通过 `entity_id LIKE 'table_id.%'` 查询所有历史批次中该表的全部列记录。

## 方案

在 `completion_records` 表新增 `parent_record_id` 字段，精准关联 table 记录与所属 column 记录，替代当前 LIKE 前缀匹配方式。每次新补全触发时，将同实体旧记录标记为 `superseded`。

---

## 数据库变更

### Alembic 迁移

`completion_records` 表新增字段：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `parent_record_id` | `String(36)` | nullable, index | 指向父 table 记录的 `id`，table 记录为 NULL |

`review_status` 列无枚举约束（String），`superseded` 为新增可选值，无需 DDL 变更。

已有数据 `parent_record_id` 为 NULL，行为不变（LIKE 查询仍匹配所有历史列记录，直至下次补全创建带 parent_record_id 的新记录）。

---

## 写入路径

### 1. 触发补全 — 过期标记 (`backend/app/api/complete.py`)

创建新 table 记录前，将同 `entity_id` 的旧未审批记录标记为 `superseded`：

```sql
UPDATE completion_records
SET review_status = 'superseded'
WHERE entity_id = :entity_id
  AND review_status IN ('pending_review', 'auto_approved')
```

**范围**：
- 仅同一 `entity_id`（table 只标记 table 的旧记录，column 各自标记自己的）
- 已人工审批的记录（`approved` / `human_rejected`）不标记

### 2. 列级联 — 写入 parent_record_id (`backend/app/api/complete.py`)

列级联创建 record 时新增 `parent_record_id=table_record.id`：

```python
CompletionRecord(
    entity_id=f"{table_id}.{col_name}",
    entity_type="column",
    parent_record_id=table_record.id,
    ...
)
```

---

## 读取路径

### 3. 列查询 API (`backend/app/api/review.py`)

`GET /review/{record_id}/columns` 改为按 `parent_record_id` 精准查询：

```sql
SELECT * FROM completion_records
WHERE entity_type = 'column'
  AND parent_record_id = :record_id
```

替代原有 `entity_id LIKE 'table_id.%'`。

### 4. 审批级联 (`backend/app/api/review.py` approve)

审批通过 table 记录时，级联更新仅作用于当前批次：

```sql
UPDATE completion_records
SET review_status = 'approved', reviewer = :reviewer, reviewed_at = :now
WHERE entity_type = 'column'
  AND parent_record_id = :record_id
```

替代原有 `entity_id LIKE 'table_id.%'`。

---

## 前端

无改动。API 返回的 columns 数组格式不变，每个字段仅一条记录且属于当前批次。

---

## 测试要点

| 场景 | 预期 |
|------|------|
| 第 1 次补全后查看详情 | 字段 Tab 显示 N 列，每条 parent_record_id = table_record.id |
| 第 2 次补全后查看第 1 次详情 | 字段 Tab 仍显示第 1 次的 N 列（不混入第 2 次） |
| 第 2 次补全后查看第 2 次详情 | 字段 Tab 显示第 2 次的 N 列 |
| 第 1 次的旧 table/column 记录 review_status | = `superseded` |
| 第 2 次审批通过 | 仅第 2 次的列记录变为 `approved`，第 1 次的保持 `superseded` |
| 历史查询 /complete/history | 仍可查到所有历史记录（含 superseded） |

---

## 涉及文件

| 文件 | 变更 |
|------|------|
| `backend/alembic/versions/xxxx_parent_record_id.py` | 新增迁移 |
| `backend/app/models/completion.py` | CompletionRecord 新增 `parent_record_id` 字段 |
| `backend/app/api/complete.py` | 触发时过期标记 + 列级联写入 parent_record_id |
| `backend/app/api/review.py` | columns 查询改 parent_record_id；approve 级联改 parent_record_id |
| `backend/app/api/schemas.py` | ReviewDetail schema 新增 parent_record_id（可选） |
| `backend/tests/test_review_columns.py` | 测试用例更新为 parent_record_id 关联 |
