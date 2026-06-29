# Database Type Field — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add db_type field to ES, search API, search table column, filter dropdown, and asset detail page.

**Architecture:** Backend adds db_type to ES mapping + search/filter logic. Data migration updates 15 ES documents. Frontend adds column + dropdown filter + detail row.

**Tech Stack:** Python/FastAPI, Elasticsearch 8.x, Vue 3/TDesign

---

### Task 1: Backend — ES mapping, search logic, data migration

**Files:**
- Modify: `backend/app/services/elasticsearch.py:27-41,137-156,204-220`
- Modify: `backend/app/api/search.py:17-27`

- [ ] **Step 1: Add db_type to ES MAPPINGS**

In `elasticsearch.py` line 38, after `"data_type": {"type": "keyword"},`, add:

```python
        "db_type": {"type": "keyword"},
```

- [ ] **Step 2: Add db_type parameter to search_all()**

In `elasticsearch.py` line 142, change:
```python
    data_type: str | None = None,
```
to:
```python
    data_type: str | None = None,
    db_type: str | None = None,
```

After line 156 (`must.append({"term": {"data_type": data_type}})`), add:
```python
    if db_type:
        must.append({"term": {"db_type": db_type}})
```

- [ ] **Step 3: Add db_types aggregation to get_filter_options()**

In `elasticsearch.py` ~line 197 (inside the aggs dict), add:
```python
            "db_types": {"terms": {"field": "db_type", "size": 20}},
```

In the return dict (~line 204), add:
```python
        "db_types": [b["key"] for b in aggs["db_types"]["buckets"]],
```

- [ ] **Step 4: Add db_type to SearchRequest and pass to search_all**

Read `backend/app/api/search.py`. In `SearchRequest` class, add:
```python
    db_type: str | None = None
```

In `search_metadata()`, add `db_type=req.db_type,` to the `search_all()` call.

- [ ] **Step 5: Data migration — update ES documents**

```bash
cd backend && source .venv/bin/activate && python3 -c "
from app.services.elasticsearch import get_es_client, INDEX_NAME

mapping = {
    'ods_trade': 'MySQL', 'ods_settle': 'MySQL', 'ods_market': 'MySQL', 'ods_finance': 'MySQL',
    'dwd_master': 'PostgreSQL', 'dwd_risk': 'PostgreSQL', 'dwd_common': 'PostgreSQL',
    'dwd_comply': 'PostgreSQL', 'dwd_position': 'PostgreSQL', 'dws_agg': 'PostgreSQL',
}
es = get_es_client()
for entity_id, db_type in mapping.items():
    es.update(index=INDEX_NAME, id=entity_id, body={'doc': {'db_type': db_type}})
    print(f'  {entity_id} -> {db_type}')
"
```

- [ ] **Step 6: Restart backend and test**

```bash
pkill -f "uvicorn app.main:app"; sleep 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000 --host 0.0.0.0 &
sleep 2

curl -s http://localhost:8000/api/v1/search/filters | python3 -c "
import sys,json; d=json.load(sys.stdin); print('db_types:', d['data']['db_types'])
"

curl -s -X POST http://localhost:8000/api/v1/search -H 'Content-Type: application/json' -d '{"query":"","db_type":"MySQL","page":1,"page_size":10}' | python3 -c "
import sys,json; d=json.load(sys.stdin); print(f'MySQL: {d[\"meta\"][\"total\"]} results'); [print(f'  {it[\"entity_id\"]}') for it in d['data']]
"
```

Expected: db_types: ['MySQL', 'PostgreSQL'], MySQL: 4 results

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/elasticsearch.py backend/app/api/search.py
git commit -m "feat: add db_type field to ES mapping, search, and filters"
```

---

### Task 2: Frontend types and composable

**Files:**
- Modify: `frontend/src/api/types.ts:1-3,93-98,119-123`
- Modify: `frontend/src/composables/useSearch.ts`
- Modify: `frontend/src/api/index.ts`

- [ ] **Step 1: Update MetadataEntity, FilterOptions, SearchParams**

In `types.ts`:

`MetadataEntity` — add after `data_type?: string`:
```typescript
  db_type?: string
```

`FilterOptions` — add:
```typescript
  db_types: string[]
```

`SearchParams` — add after `entity_type?: string`:
```typescript
  db_type?: string
```

- [ ] **Step 2: Add db_type to useSearch composable**

Read `frontend/src/composables/useSearch.ts`. In the `filters` reactive, add:
```typescript
  db_type: '',
```

In the `search()` function's `searchMetadata({...})` call, add:
```typescript
    db_type: filters.db_type || undefined,
```

- [ ] **Step 3: Pass db_type in api/index.ts searchMetadata**

Read `frontend/src/api/index.ts`. In `searchMetadata()`, add `db_type: params.db_type,` to the POST payload.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/index.ts frontend/src/composables/useSearch.ts
git commit -m "feat: add db_type to frontend types, composable, and API params"
```

---

### Task 3: Frontend pages — SearchPage + AssetDetailPage

**Files:**
- Modify: `frontend/src/pages/SearchPage.vue:41-48,309-311,372-405`
- Modify: `frontend/src/pages/AssetDetailPage.vue:31-32`

- [ ] **Step 1: Add dbType to SearchPage localFilters**

Read `SearchPage.vue`. In the `localFilters` reactive (around line 41-48), add:
```typescript
  dbType: '',
```

- [ ] **Step 2: Add db_type column to table**

After line 310 (`{ colKey: 'database', title: '所属库', ... }`), add:
```typescript
  { colKey: 'db_type', title: '数据库类型', width: 100 },
```

- [ ] **Step 3: Add db_type filter dropdown**

In the filter-bar template, add a select dropdown after the database select:

```html
<!-- Database Type dropdown -->
<div class="filter-select-wrap">
  <select
    v-model="localFilters.dbType"
    class="filter-select"
    :class="{ active: localFilters.dbType !== '' }"
  >
    <option value="">全部类型</option>
    <option v-for="opt in apiFilterOpts.db_types" :key="opt" :value="opt">{{ opt }}</option>
  </select>
</div>
```

- [ ] **Step 4: Wire dbType filter to search**

Add a watcher in SearchPage.vue:
```typescript
watch(() => localFilters.dbType, (val) => {
  filters.db_type = val
  search()
})
```

Import `watch` if not already imported (check line 2): `import { ref, reactive, computed, watch, onMounted } from 'vue'`

- [ ] **Step 5: Add db_type row to AssetDetailPage**

In `AssetDetailPage.vue`, after the "所属库" row, add:
```html
<div class="detail-row"><span class="detail-label">数据库类型</span><span class="detail-value">{{ asset?.db_type || '—' }}</span></div>
```

- [ ] **Step 6: Verify type check**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | grep -i error | head -10
```

Expected: only pre-existing errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/SearchPage.vue frontend/src/pages/AssetDetailPage.vue
git commit -m "feat: add db_type column, filter dropdown, and detail display"
```
