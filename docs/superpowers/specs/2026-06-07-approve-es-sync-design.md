# 审批通过 ES 回写

**日期**: 2026-06-07
**状态**: 已确认
**方案**: B — ES 服务函数 + Celery 任务封装

## 需求

点击审核工作台确认按钮后，将审批通过的表补全信息和字段补全信息回写到 `metadata_index` / `metadata_columns` ES 索引，同时将表的补全状态标记为已补全。

## 设计决策

| 决策 | 选择 |
|------|------|
| 审批粒度 | 表审批通过 → 自动级联通过所有字段 |
| 补全状态字段 | 复用 `has_description`（false=未补全, true=已补全） |
| 写入 ES 的字段 | 表：display_name, description, tags；字段：completion_description, completion_tags, completion_time |
| 执行方式 | Celery 异步，approve 接口立即返回 |
| 架构 | ES 更新逻辑在 `services/elasticsearch.py`，Celery 任务在 `jobs/es_sync.py` |

## 数据流

```
用户点击「确认采纳」
  │
  ▼
POST /review/{record_id}/approve
  │
  ▼
approve_review 端点
  ├─ 更新表 record: review_status = "approved"
  ├─ 级联更新所有字段: review_status = "approved"
  ├─ 提交 DB
  └─ 派发 Celery: sync_approval_to_es.delay(record_id)
        │
        ▼ (异步)
      Celery Worker
        ├─ 查表 record + 所有字段 records
        ├─ update_completed_metadata() → metadata_index
        └─ update_completed_columns() → metadata_columns
```

## 后端改动

### 1. 改造 `approve_review` 端点

**文件**: `backend/app/api/review.py:232-259`

- 表审批时级联通过所有 `entity_id LIKE 'table_entity_id.%'` 的字段记录
- 提交 DB 后派发 Celery 任务 `sync_approval_to_es.delay(record.id)`
- 响应增加 `cascade_columns` 计数字段

### 2. ES 服务新增回写函数

**文件**: `backend/app/services/elasticsearch.py`

- `update_completed_metadata(entity_id, completion_result)` — 用 `es.update()` 部分更新 `metadata_index` 文档
- `update_completed_columns(entity_id, columns_data)` — 批量更新 `metadata_columns` 文档
- 文档不存在时捕获 `NotFoundError`，记录 warning 不阻塞

### 3. 新建 Celery 任务

**文件**: `backend/app/jobs/es_sync.py`

- `sync_approval_to_es(record_id)` — 查询 DB → 调用 ES 服务回写
- 使用同步 Session（`SessionLocal`），与现有 Celery 任务模式一致

## 前端

无需改动。approve 按钮调用逻辑不变。

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| ES 中不存在该表文档 | `NotFoundError` → warning 日志，不阻塞 |
| 字段不在 metadata_columns 中 | 跳过该字段，继续下一个 |
| Celery 任务执行失败 | Celery 默认最多重试 3 次 |
| completion_result 为空 | 任务跳过，返回 skipped |
| DB 查询失败 | 记录 error 日志 |

## 涉及文件

| 文件 | 改动类型 |
|------|----------|
| `backend/app/api/review.py` | 修改 `approve_review` |
| `backend/app/services/elasticsearch.py` | 新增 2 个函数 |
| `backend/app/jobs/es_sync.py` | 新建 |
| `backend/tests/test_es_sync.py` | 新建 |

## 测试要点

- [ ] approve 表后，所有关联字段的 review_status 变为 approved
- [ ] approve 后 Celery 任务被派发
- [ ] `update_completed_metadata` 正确更新 metadata_index 文档
- [ ] `update_completed_columns` 正确更新 metadata_columns 文档
- [ ] 文档不存在时不会崩溃
- [ ] 非表类型（单独审批字段）正常回写
- [ ] 审批非 pending_review 状态记录的行为
