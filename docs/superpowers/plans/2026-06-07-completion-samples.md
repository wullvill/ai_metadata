# Completion Samples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在资产搜索页面增加补全样本管理功能，支持单个/批量标记，样本在 Pipeline 检索阶段自动提权

**Architecture:** ES metadata_index 新增 is_sample boolean 字段，后端新增 samples CRUD API，Pipeline Stage 1 检索时查询样本并提权混入 RRF，前端 SearchPage 增加样本列和批量操作按钮

**Tech Stack:** FastAPI + Elasticsearch + LangGraph + Vue 3 + TDesign + TypeScript

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `backend/app/services/elasticsearch.py` | 修改 | 新增 `set_sample_flag`、`get_samples` |
| `backend/app/api/schemas.py` | 修改 | 新增 `SampleSetRequest` |
| `backend/app/api/samples.py` | 新建 | Samples Router |
| `backend/app/main.py` | 修改 | 注册 sample_router |
| `backend/app/pipeline/stage1_retrieve.py` | 修改 | 样本查询 + 提权 |
| `frontend/src/api/types.ts` | 修改 | `MetadataEntity.is_sample` |
| `frontend/src/api/index.ts` | 修改 | 新增 `setSamples` |
| `frontend/src/pages/SearchPage.vue` | 修改 | 样本列 + 批量按钮 |

---

### Task 1: ES 服务方法 — `set_sample_flag`

**Files:**
- Modify: `backend/app/services/elasticsearch.py`
- Test: `backend/tests/test_es_samples.py`（新建）

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_es_samples.py
"""ES sample flag 测试"""
import pytest
from unittest.mock import patch, MagicMock


class TestSetSampleFlag:
    def test_set_sample_flag_calls_update_by_query_with_correct_params(self):
        from app.services.elasticsearch import set_sample_flag

        mock_es = MagicMock()
        mock_es.update_by_query.return_value = {"updated": 3}

        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            result = set_sample_flag(["a", "b", "c"], True)

        assert result == 3
        call_args = mock_es.update_by_query.call_args
        assert call_args.kwargs["index"] == "metadata_index"
        body = call_args.kwargs["body"]
        assert body["query"]["terms"] == {"entity_id": ["a", "b", "c"]}
        assert "ctx._source.is_sample = true" in body["script"]["source"]

    def test_set_sample_flag_unset(self):
        from app.services.elasticsearch import set_sample_flag

        mock_es = MagicMock()
        mock_es.update_by_query.return_value = {"updated": 2}

        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            result = set_sample_flag(["x", "y"], False)

        assert result == 2
        body = mock_es.update_by_query.call_args.kwargs["body"]
        assert "ctx._source.is_sample = false" in body["script"]["source"]

    def test_set_sample_flag_empty_list_returns_zero(self):
        from app.services.elasticsearch import set_sample_flag

        with patch("app.services.elasticsearch.get_es_client") as mock_client:
            result = set_sample_flag([], True)

        assert result == 0
        mock_client.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_es_samples.py::TestSetSampleFlag -v
```
Expected: FAIL — "set_sample_flag not defined"

- [ ] **Step 3: Implement `set_sample_flag`**

在 `elasticsearch.py` 末尾添加：

```python
def set_sample_flag(entity_ids: list[str], is_sample: bool) -> int:
    """批量设置/取消样本标记，返回更新数"""
    if not entity_ids:
        return 0
    es = get_es_client()
    resp = es.update_by_query(
        index=INDEX_NAME,
        body={
            "query": {"terms": {"entity_id": entity_ids}},
            "script": {
                "source": f"ctx._source.is_sample = {'true' if is_sample else 'false'}"
            },
        },
        refresh=True,
    )
    return resp.get("updated", 0)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_es_samples.py::TestSetSampleFlag -v
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/elasticsearch.py backend/tests/test_es_samples.py
git commit -m "feat: add set_sample_flag to ES service"
```

---

### Task 2: ES 服务方法 — `get_samples`

**Files:**
- Modify: `backend/app/services/elasticsearch.py`
- Modify: `backend/tests/test_es_samples.py`

- [ ] **Step 1: Write the failing test**

在 `backend/tests/test_es_samples.py` 中添加：

```python
class TestGetSamples:
    def test_get_samples_queries_by_is_sample_true(self):
        from app.services.elasticsearch import get_samples

        mock_es = MagicMock()
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"entity_id": "a", "is_sample": True}},
                    {"_source": {"entity_id": "b", "is_sample": True}},
                ]
            }
        }

        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            result = get_samples()

        assert len(result) == 2
        assert result[0]["entity_id"] == "a"
        assert result[1]["entity_id"] == "b"
        body = mock_es.search.call_args.kwargs["body"]
        assert body["query"]["term"] == {"is_sample": True}

    def test_get_samples_empty(self):
        from app.services.elasticsearch import get_samples

        mock_es = MagicMock()
        mock_es.search.return_value = {"hits": {"hits": []}}

        with patch("app.services.elasticsearch.get_es_client", return_value=mock_es):
            result = get_samples()

        assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_es_samples.py::TestGetSamples -v
```
Expected: FAIL

- [ ] **Step 3: Implement `get_samples`**

在 `elasticsearch.py` 末尾添加：

```python
def get_samples() -> list[dict]:
    """获取全部样本"""
    es = get_es_client()
    resp = es.search(
        index=INDEX_NAME,
        body={
            "query": {"term": {"is_sample": True}},
            "size": 1000,
        },
    )
    return [hit["_source"] for hit in resp["hits"]["hits"]]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_es_samples.py::TestGetSamples -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/elasticsearch.py backend/tests/test_es_samples.py
git commit -m "feat: add get_samples to ES service"
```

---

### Task 3: 后端 Samples API — Schema + Router

**Files:**
- Create: `backend/app/api/samples.py`
- Modify: `backend/app/api/schemas.py`

- [ ] **Step 1: Add `SampleSetRequest` schema**

在 `backend/app/api/schemas.py` 末尾添加：

```python
class SampleSetRequest(BaseModel):
    entity_ids: list[str]
    is_sample: bool
```

- [ ] **Step 2: Create samples router**

新建 `backend/app/api/samples.py`：

```python
"""补全样本管理 API"""
from fastapi import APIRouter
from app.services.elasticsearch import set_sample_flag, get_samples
from app.api.schemas import SampleSetRequest

router = APIRouter(prefix="/api/v1/samples", tags=["samples"])


@router.post("/set")
async def set_samples(req: SampleSetRequest):
    """批量设置/取消样本标记"""
    updated = set_sample_flag(req.entity_ids, req.is_sample)
    return {"success": True, "updated": updated}


@router.get("")
async def list_samples():
    """获取全部样本"""
    data = get_samples()
    return {"success": True, "data": data}
```

- [ ] **Step 3: Run existing API tests to verify no regressions**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_api.py -v
```
Expected: all existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/schemas.py backend/app/api/samples.py
git commit -m "feat: add samples CRUD API endpoints"
```

---

### Task 4: 注册 Samples Router

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Register sample_router**

在 `backend/app/main.py` 的 router 注册区域（`app.include_router(xxx)` 附近）增加：

```python
from app.api.samples import router as sample_router
app.include_router(sample_router)
```

- [ ] **Step 2: Verify router is registered**

```bash
cd backend && source .venv/bin/activate && python -c "
from app.main import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
print([r for r in routes if 'samples' in r])
"
```
Expected: `['/api/v1/samples/set', '/api/v1/samples']`

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: register samples router in FastAPI app"
```

---

### Task 5: Pipeline Stage 1 — 样本提权

**Files:**
- Modify: `backend/app/pipeline/stage1_retrieve.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_samples_pipeline.py
"""Pipeline 样本提权测试"""
from app.pipeline.stage1_retrieve import rrf_merge


class TestSamplesBoost:
    def test_samples_placed_at_top_of_merged_results(self):
        """样本 rank=0 应排在非样本前面"""
        samples = [
            {"entity_id": "sample_a", "score": 0.5, "source": "es"},
            {"entity_id": "sample_b", "score": 0.6, "source": "milvus"},
        ]
        milvus_results = [
            {"entity_id": "x", "score": 0.9},
        ]
        es_results = [
            {"entity_id": "x", "score": 0.8},
        ]

        for i, s in enumerate(samples):
            milvus_results.insert(i, s)

        merged = rrf_merge(milvus_results, es_results, top_n=10)
        top_ids = [m["entity_id"] for m in merged[:2]]
        assert top_ids == ["sample_a", "sample_b"]
```

- [ ] **Step 2: Run test to confirm expected behavior**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_samples_pipeline.py -v
```

- [ ] **Step 3: Implement sample boost in `stage1_retrieve`**

在 `stage1_retrieve.py` 中，`# RRF 合并或单路降级` 注释之前添加：

```python
    # 查询样本并置顶
    try:
        sample_docs = elasticsearch.get_samples()
        if sample_docs:
            logger.info(f"Stage 1: {len(sample_docs)} samples found, boosting rank")
            for doc in sample_docs:
                milvus_results.insert(0, {
                    "entity_id": doc["entity_id"],
                    "score": 1.0,
                    "source": "sample",
                    "table_name": doc.get("table_name"),
                    "display_name": doc.get("display_name"),
                    "description": doc.get("description"),
                    "search_text": doc.get("description", doc.get("table_name", "")),
                })
    except Exception as e:
        logger.warning(f"Stage 1: failed to fetch samples: {e}")
```

- [ ] **Step 4: Verify no regressions in existing tests**

```bash
cd backend && source .venv/bin/activate && pytest tests/ -v --ignore=tests/test_es_samples.py --ignore=tests/test_samples_pipeline.py
```
Expected: all existing tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/stage1_retrieve.py backend/tests/test_samples_pipeline.py
git commit -m "feat: boost sample entities in Stage 1 retrieval"
```

---

### Task 6: 前端类型 + API

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/index.ts`

- [ ] **Step 1: Add `is_sample` to `MetadataEntity`**

在 `frontend/src/api/types.ts` 的 `MetadataEntity` 接口中添加：

```typescript
is_sample?: boolean
```

- [ ] **Step 2: Add `setSamples` API function**

在 `frontend/src/api/index.ts` 末尾添加：

```typescript
export async function setSamples(entityIds: string[], isSample: boolean): Promise<void> {
  await api.post('/samples/set', { entity_ids: entityIds, is_sample: isSample })
}
```

- [ ] **Step 3: Verify TypeScript compilation**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -20
```
Expected: no new type errors related to api or types

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/index.ts
git commit -m "feat: add is_sample type and setSamples API function"
```

---

### Task 7: 前端 SearchPage — 样本列 + 批量按钮

**Files:**
- Modify: `frontend/src/pages/SearchPage.vue`

- [ ] **Step 1: Add sample column to table**

在 columns 定义的「补全状态」列之后、「操作」列之前插入：

```typescript
  { colKey: 'is_sample', title: '样本', width: 80 },
```

- [ ] **Step 2: Add sample column template**

在 `<template>` 的 `<template #completion_status>` 之后添加：

```html
          <!-- Sample Toggle -->
          <template #is_sample="{ row }">
            <t-switch
              :value="(row as AssetDisplay).is_sample"
              size="small"
              @change="(val: boolean) => handleSampleToggle(row as AssetDisplay, val)"
            />
          </template>
```

- [ ] **Step 3: Add `handleSampleToggle` handler**

在 `<script setup>` 的 `batchApplyCompletion` 函数之后添加：

```typescript
async function handleSampleToggle(entity: AssetDisplay, value: boolean) {
  try {
    await setSamples([entity.entity_id], value)
    entity.is_sample = value
    MessagePlugin.success(value ? '已设为样本' : '已取消样本')
  } catch {
    MessagePlugin.error('操作失败')
  }
}
```

- [ ] **Step 4: Add batch sample buttons in ops-bar**

在 `ops-bar-right` 的「批量申请补全」按钮之前添加：

```html
          <button
            class="ops-batch-btn"
            :disabled="batchDisabled"
            @click="handleBatchSample(true)"
          >
            批量设为样本
          </button>
          <button
            class="ops-batch-btn ops-batch-cancel"
            :disabled="batchDisabled"
            @click="handleBatchSample(false)"
          >
            批量取消样本
          </button>
```

- [ ] **Step 5: Add `handleBatchSample` handler**

```typescript
async function handleBatchSample(isSample: boolean) {
  const ids = selectedRowKeys.value
  if (ids.length === 0) return
  try {
    await setSamples(ids, isSample)
    resultsAsDisplay.value.forEach(r => {
      if (ids.includes(r.entity_id)) {
        r.is_sample = isSample
      }
    })
    MessagePlugin.success(isSample ? `已为 ${ids.length} 项设为样本` : `已为 ${ids.length} 项取消样本`)
  } catch {
    MessagePlugin.error('批量操作失败')
  }
}
```

- [ ] **Step 6: Add style for cancel button variant**

在 `<style scoped>` 中添加：

```css
.ops-batch-cancel {
  background: transparent;
  border-color: var(--color-border);
  color: var(--color-muted);
}

.ops-batch-cancel:hover:not(:disabled) {
  border-color: #e34d59;
  color: #e34d59;
}
```

- [ ] **Step 7: Verify frontend builds**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -20
```
Expected: no type errors in SearchPage.vue

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/SearchPage.vue
git commit -m "feat: add sample toggle column and batch sample buttons"
```

---

## Execution Order

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7
```

Task 1-2 可并行，Task 6 可与 Task 3-5 并行，Task 7 依赖 Task 3 和 Task 6。
