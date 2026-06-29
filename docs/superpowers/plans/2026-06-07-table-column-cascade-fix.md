# 表级补全级联字段修复 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复表级补全时字段级联失败的问题，并在审核详情中展示字段补全结果

**Architecture:** 后端修复 ES 查询使 `_fetch_columns` 能正确获取表的字段列表；新增 `/review/{record_id}/columns` 端点返回字段补全记录；前端在 ReviewDetail 中新增「字段补全」Tab 展示字段补全结果

**Tech Stack:** Python/FastAPI/SQLAlchemy/Elasticsearch + Vue 3/TypeScript/TDesign

---

### Task 1: 修复 `_fetch_columns` ES 查询

**Files:**
- Modify: `backend/app/api/complete.py:102-116`

- [ ] **Step 1: 替换 `_fetch_columns` 函数**

将 `entity_id` term 匹配改为 `database` + `schema` + `table_name` 组合条件查询：

```python
async def _fetch_columns(target: dict) -> list[dict]:
    """从 ES 获取表的字段列表"""
    from app.services.elasticsearch import get_es_client
    try:
        es = get_es_client()
        must = []
        for field in ("database", "schema", "table_name"):
            val = target.get(field)
            if val:
                must.append({"term": {field: val}})
        if not must:
            return []
        body = {
            "query": {"bool": {"must": must}},
            "size": 200,
            "_source": ["entity_id", "column_id", "column_name", "data_type",
                        "original_description", "original_tags"],
        }
        resp = es.search(index="metadata_columns", body=body)
        return [h["_source"] for h in resp["hits"]["hits"]]
    except Exception as e:
        logger.warning(f"Failed to fetch columns for {target.get('entity_id')}: {e}")
        return []
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/api/complete.py
git commit -m "fix: correct _fetch_columns ES query to match by database/schema/table_name"
```

---

### Task 2: 新增后端 API `GET /review/{record_id}/columns`

**Files:**
- Modify: `backend/app/api/review.py`（在 `GET /{record_id}` 路由之前插入）
- Create: `backend/tests/test_review_columns.py`

- [ ] **Step 1: 新增端点**

在 `backend/app/api/review.py` 的 `get_review_queue` 之后（约第 78 行）、`get_review_detail`（第 81 行）之前插入：

```python
@router.get("/{record_id}/columns")
async def get_record_columns(record_id: str, db: AsyncSession = Depends(get_db)):
    """获取表级审核记录关联的字段补全列表"""
    result = await db.execute(
        select(CompletionRecord).where(CompletionRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="审核记录不存在")

    if record.entity_type != "table":
        return {"success": True, "data": []}

    prefix = record.entity_id + ".%"
    result = await db.execute(
        select(CompletionRecord)
        .where(
            CompletionRecord.entity_type == "column",
            CompletionRecord.entity_id.like(prefix),
        )
        .order_by(CompletionRecord.entity_id)
    )
    columns = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": c.id,
                "entity_id": c.entity_id,
                "entity_type": c.entity_type,
                "completion_result": c.completion_result,
                "quality_check": c.quality_check,
                "review_status": c.review_status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in columns
        ],
    }
```

**重要**：此端点放在 `GET /{record_id}`（当前第 81 行）之前，避免 FastAPI 将 `"columns"` 当作 `record_id` 匹配。

- [ ] **Step 2: 编写测试**

创建 `backend/tests/test_review_columns.py`：

```python
"""测试 GET /review/{record_id}/columns 端点"""
import pytest


@pytest.mark.asyncio
async def test_columns_endpoint_not_found(client):
    """不存在的记录应返回 404"""
    resp = await client.get("/api/v1/review/nonexistent-id/columns")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_columns_endpoint_non_table(client):
    """非 table 类型的记录应返回空列表"""
    resp = await client.get("/api/v1/review/some-column-record/columns")
    assert resp.status_code in [200, 404]
    if resp.status_code == 200:
        data = resp.json()
        assert data["success"] is True
        assert data["data"] == []
```

- [ ] **Step 3: 运行测试**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_review_columns.py -v
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/api/review.py backend/tests/test_review_columns.py
git commit -m "feat: add GET /review/{record_id}/columns endpoint for cascaded column results"
```

---

### Task 3: 前端新增 `getRecordColumns` API 函数

**Files:**
- Modify: `frontend/src/api/index.ts`

- [ ] **Step 1: 新增函数**

在 `frontend/src/api/index.ts` 中 `getReviewReferences` 函数之后（约第 123 行）添加：

```ts
export async function getRecordColumns(recordId: string): Promise<{ success: boolean; data: ReviewRecord[] }> {
  const { data } = await api.get(`/review/${recordId}/columns`)
  return data
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/api/index.ts
git commit -m "feat: add getRecordColumns API function for cascaded column results"
```

---

### Task 4: ReviewDetail 新增「字段补全」Tab

**Files:**
- Modify: `frontend/src/components/ReviewDetail.vue`

- [ ] **Step 1: 新增 import 和响应式状态**

在 `<script setup>` 顶部的 import 区域，`getReviewReferences` 之后添加 `getRecordColumns`（约第 314 行）：

```ts
import { approveReview, rejectReview, modifyReview, getReviewReferences, getRecordColumns } from '../api'
```

在 `const references = ref<ReferenceItem[]>([])` 之后（约第 343 行）添加字段补全状态：

```ts
const columns = ref<ReviewRecord[]>([])
const columnsLoading = ref(false)
```

在 `loadReferences` 函数之后（约第 360 行）添加加载字段补全的逻辑：

```ts
async function loadColumns() {
  if (!props.detail?.id || props.detail.entity_type !== 'table' || columns.value.length) return
  columnsLoading.value = true
  try {
    const res = await getRecordColumns(props.detail.id)
    if (res.success) columns.value = res.data
  } catch { /* mute */ }
  finally { columnsLoading.value = false }
}
```

在 `watch` 回调中（约第 372 行），`references.value = []` 之后添加：

```ts
columns.value = []
```

- [ ] **Step 2: 新增「字段补全」Tab 面板**

在「检索参考」Tab 面板之后（第 255 行 `</t-tab-panel>` 之后）、`</t-tabs>` 之前（第 256 行）插入：

```html
        <!-- Tab 5: 字段补全（仅表类型显示） -->
        <t-tab-panel
          v-if="detail.entity_type === 'table'"
          value="columns"
          label="字段补全"
        >
          <div v-if="columnsLoading" class="empty-note">
            <t-loading size="small" text="加载字段补全数据..." />
          </div>
          <template v-else-if="columns.length">
            <div class="columns-list">
              <div
                v-for="col in columns"
                :key="col.id"
                class="column-item"
              >
                <div class="column-item-top">
                  <span class="column-name">{{ col.entity_id }}</span>
                  <t-tag
                    variant="light"
                    :theme="col.review_status === 'pending_review' ? 'warning' : col.review_status === 'auto_approved' ? 'success' : 'default'"
                    size="small"
                  >
                    {{ col.review_status === 'pending_review' ? '待审核' : col.review_status === 'auto_approved' ? '已自动采纳' : col.review_status === 'rejected' ? '系统拒绝' : col.review_status }}
                  </t-tag>
                </div>
                <div class="column-item-body">
                  <div class="column-field">
                    <span class="column-field-label">建议中文名</span>
                    <span class="column-field-value">{{ col.completion_result?.display_name || '—' }}</span>
                  </div>
                  <div class="column-field">
                    <span class="column-field-label">描述</span>
                    <span class="column-field-value muted">{{ col.completion_result?.description || '—' }}</span>
                  </div>
                  <div class="column-field">
                    <span class="column-field-label">置信度</span>
                    <span class="column-field-value mono" :style="{ color: col.completion_result?.confidence ? (col.completion_result.confidence >= 0.8 ? 'var(--td-success-color)' : col.completion_result.confidence >= 0.6 ? 'var(--td-warning-color)' : 'var(--td-error-color)') : 'var(--td-text-color-placeholder)' }">
                      {{ col.completion_result?.confidence ? (col.completion_result.confidence * 100).toFixed(0) + '%' : '—' }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="empty-note">暂无字段补全记录</div>
        </t-tab-panel>
```

- [ ] **Step 3: 在 Tab 切换时触发加载**

在现有 `watch` 之后新增 watch 监听 tab 切换：

```ts
watch(activeTab, (tab) => {
  if (tab === 'columns') loadColumns()
})
```

- [ ] **Step 4: 添加字段补全列表样式**

在 `<style scoped>` 末尾（`</style>` 之前）添加：

```css
/* Columns list */
.columns-list {
  border: 1px solid var(--td-border-level-2-color, #e7e7e7);
  border-radius: 8px;
  overflow: hidden;
}

.column-item {
  padding: 12px 16px;
  border-bottom: 1px solid var(--td-border-level-2-color, #e7e7e7);
  background: var(--td-bg-color-container);
}

.column-item:last-child {
  border-bottom: none;
}

.column-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.column-name {
  font-family: 'JetBrains Mono', 'SF Mono', ui-monospace, monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--td-text-color-primary);
}

.column-item-body {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.column-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.column-field-label {
  font-size: 11px;
  color: var(--td-text-color-placeholder);
}

.column-field-value {
  font-size: 13px;
  color: var(--td-text-color-primary);
}

.column-field-value.muted {
  color: var(--td-text-color-placeholder);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/ReviewDetail.vue
git commit -m "feat: add cascaded column completion tab in ReviewDetail for table entities"
```

---

### 验证清单

- [ ] 后端 `_fetch_columns` 使用 `database/schema/table_name` 组合条件查询 ES
- [ ] `GET /review/{record_id}/columns` 对表类型返回字段补全记录列表
- [ ] `GET /review/{record_id}/columns` 对不存在记录返回 404
- [ ] `GET /review/{record_id}/columns` 对非表类型返回空列表
- [ ] 前端 `getRecordColumns` API 函数正确调用后端端点
- [ ] ReviewDetail 中表类型记录显示「字段补全」Tab
- [ ] 切换至「字段补全」Tab 时正确加载并展示字段列表
- [ ] 字段列表每行展示字段名、建议中文名、描述、置信度、审核状态
- [ ] 无数据时显示空状态提示
- [ ] 非表类型记录不显示该 Tab
