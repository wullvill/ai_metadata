# Asset Detail Columns — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 metadata_columns 索引存储列信息，新增资产详情 API，前端详情页展示完整列清单。

**Architecture:** 搜索页继续仅查询 metadata_index（table/view），资产详情页通过新 API `GET /api/v1/assets/{entity_id}` 同时获取基本信息和列信息（metadata_index + metadata_columns）。

**Tech Stack:** Python/FastAPI 后端、Elasticsearch 8.x、Vue 3/TDesign 前端

---

### Task 1: 创建 metadata_columns ES 索引 + 列数据导入脚本

**Files:**
- Modify: `backend/app/services/elasticsearch.py` — 新增列索引常量和函数
- Create: `backend/scripts/import_columns.py` — 列数据导入脚本
- Read: `design-ui/asset_detail.html` — 数据来源

- [ ] **Step 1: 在 elasticsearch.py 中新增列索引常量和方法**

在 `INDEX_NAME = "metadata_index"` 后添加：

```python
COLUMNS_INDEX = "metadata_columns"

COLUMNS_MAPPINGS = {
    "properties": {
        "column_id": {"type": "keyword"},
        "entity_id": {"type": "keyword"},
        "column_name": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
        "data_type": {"type": "keyword"},
        "original_description": {"type": "text"},
        "original_tags": {"type": "keyword"},
        "completion_description": {"type": "text"},
        "completion_tags": {"type": "keyword"},
        "completion_time": {"type": "date"},
    }
}
```

在文件末尾（`_build_search_text` 之后）添加：

```python
def ensure_columns_index() -> None:
    """确保 metadata_columns 索引存在"""
    es = get_es_client()
    if not es.indices.exists(index=COLUMNS_INDEX):
        es.indices.create(index=COLUMNS_INDEX, mappings=COLUMNS_MAPPINGS)
        logger.info(f"Created ES index: {COLUMNS_INDEX}")


def index_columns(entity_id: str, columns: list[dict]) -> None:
    """批量索引列的独立文档"""
    if not columns:
        return
    es = get_es_client()
    actions = [
        {
            "_index": COLUMNS_INDEX,
            "_id": f"{entity_id}.{col['name']}",
            "_source": {
                "column_id": f"{entity_id}.{col['name']}",
                "entity_id": entity_id,
                "column_name": col["name"],
                "data_type": col.get("type", ""),
                "original_description": col.get("origDesc", ""),
                "original_tags": [t for t in col.get("origTag", "").split(",") if t.strip()] if col.get("origTag") else [],
                "completion_description": col.get("compDesc", ""),
                "completion_tags": [t for t in col.get("compTag", "").split(",") if t.strip()] if col.get("compTag") else [],
                "completion_time": col.get("compTime") or None,
            },
        }
        for col in columns
    ]
    success, errors = helpers.bulk(es, actions, raise_on_error=False)
    if errors:
        logger.warning(f"ES columns bulk index: {success} ok, {len(errors)} errors")


def get_columns(entity_id: str) -> list[dict]:
    """获取指定资产的所有列"""
    es = get_es_client()
    body = {
        "query": {"term": {"entity_id": entity_id}},
        "size": 500,
        "sort": [{"column_name.raw": "asc"}],
    }
    resp = es.search(index=COLUMNS_INDEX, body=body)
    return [hit["_source"] for hit in resp["hits"]["hits"]]


def get_asset_by_id(entity_id: str) -> dict | None:
    """通过 entity_id 精确获取资产信息"""
    es = get_es_client()
    try:
        resp = es.get(index=INDEX_NAME, id=entity_id)
        return resp["_source"]
    except Exception:
        return None
```

- [ ] **Step 2: 创建列数据导入脚本**

```bash
mkdir -p backend/scripts
```

创建 `backend/scripts/import_columns.py`:

```python
"""从 design-ui/asset_detail.html 导入列数据到 ES"""
import json, re, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.elasticsearch import ensure_columns_index, index_columns, COLUMNS_INDEX, get_es_client

HTML_PATH = os.path.join(os.path.dirname(__file__), "../../design-ui/asset_detail.html")


def extract_assets(html: str) -> list[dict]:
    """从 HTML <script> 中提取 ASSETS 数组"""
    match = re.search(r"const ASSETS = (\[[\s\S]*?\]);", html)
    if not match:
        raise ValueError("ASSETS array not found in HTML")
    # 替换 JS 宽松语法为合法 JSON
    js = match.group(1)
    js = re.sub(r"(\w+):", r'"\1":', js)
    js = re.sub(r"'", '"', js)
    js = re.sub(r",\s*]", "]", js)
    js = re.sub(r",\s*}", "}", js)
    return json.loads(js)


def main():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    assets = extract_assets(html)

    es = get_es_client()
    if es.indices.exists(index=COLUMNS_INDEX):
        es.indices.delete(index=COLUMNS_INDEX)

    ensure_columns_index()

    total = 0
    for a in assets:
        entity_type = a.get("type", "")
        entity_id = a.get("id", "")
        columns = a.get("columns", [])
        if entity_type in ("表", "视图") and columns:
            index_columns(entity_id, columns)
            total += len(columns)
            print(f"  {entity_id}: {len(columns)} columns")

    print(f"\nTotal: {total} columns indexed")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 执行导入脚本**

```bash
cd backend && source .venv/bin/activate && python scripts/import_columns.py
```

Expected output: 每个资产后跟列数，最后显示 Total: ~110 columns indexed

- [ ] **Step 4: 验证导入结果**

```bash
curl -s -u elastic:Bonc@1234 'http://172.17.5.238:9220/metadata_columns/_count' 2>&1 | python3 -c "import sys,json; print(f'columns count: {json.load(sys.stdin)[\"count\"]}')"

curl -s -u elastic:Bonc@1234 'http://172.17.5.238:9220/metadata_columns/_search' -H 'Content-Type: application/json' -d '{"query":{"term":{"entity_id":"fact_trade"}},"size":5}' 2>&1 | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'fact_trade columns: {d[\"hits\"][\"total\"][\"value\"]}')
for h in d['hits']['hits']:
    s=h['_source']
    print(f'  {s[\"column_name\"]} ({s[\"data_type\"]})')
"
```

Expected: count: ~110, fact_trade: 12 columns

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/elasticsearch.py backend/scripts/import_columns.py
git commit -m "feat: add metadata_columns ES index and import script"
```

---

### Task 2: 新增资产详情 API

**Files:**
- Create: `backend/app/api/assets.py`
- Modify: `backend/app/main.py:32-35`

- [ ] **Step 1: 创建 assets.py 路由**

创建 `backend/app/api/assets.py`:

```python
"""资产详情 API"""
from fastapi import APIRouter, HTTPException
from app.services.elasticsearch import get_asset_by_id, get_columns

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.get("/{entity_id}")
async def get_asset_detail(entity_id: str):
    """获取资产详情（基本信息 + 列清单）"""
    asset = get_asset_by_id(entity_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")

    columns = get_columns(entity_id)

    return {
        "success": True,
        "data": {
            **asset,
            "columns": columns,
        },
    }
```

- [ ] **Step 2: 在 main.py 中注册路由**

在 `from app.api.history import router as history_router` 之后添加：

```python
from app.api.assets import router as assets_router
```

在 `app.include_router(history_router)` 之后添加：

```python
app.include_router(assets_router)
```

- [ ] **Step 3: 重启后端并测试**

```bash
pkill -f "uvicorn app.main:app"; sleep 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000 --host 0.0.0.0 &
sleep 2

curl -s http://localhost:8000/api/v1/assets/fact_trade 2>&1 | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'success: {d[\"success\"]}')
a=d['data']
print(f'entity_id: {a[\"entity_id\"]}')
print(f'entity_type: {a[\"entity_type\"]}')
print(f'columns: {len(a[\"columns\"])}')
print(f'first column: {a[\"columns\"][0][\"column_name\"]} ({a[\"columns\"][0][\"data_type\"]})')
"
```

Expected: success: True, entity_id: fact_trade, entity_type: table, columns: 12, first column: trade_id (bigint)

- [ ] **Step 4: Test 404 case**

```bash
curl -s http://localhost:8000/api/v1/assets/nonexistent 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'detail: {d[\"detail\"]}')"
```

Expected: detail: 资产不存在

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/assets.py backend/app/main.py
git commit -m "feat: add asset detail API with columns"
```

---

### Task 3: 更新前端 types 和 API client

**Files:**
- Modify: `frontend/src/api/types.ts:3,100-123`
- Modify: `frontend/src/api/index.ts:2,85`

- [ ] **Step 1: 扩展 MetadataEntity.entity_type 并新增类型**

在 `types.ts` 中，将第 3 行 `entity_type: 'table' | 'column'` 改为 `entity_type: 'table' | 'view'`。

在文件末尾添加新类型：

```typescript
export interface ColumnInfo {
  column_id: string
  entity_id: string
  column_name: string
  data_type: string
  original_description: string
  original_tags: string[]
  completion_description: string
  completion_tags: string[]
  completion_time: string | null
}

export interface AssetDetail {
  entity_id: string
  entity_type: 'table' | 'view'
  database: string
  schema_name: string
  table_name: string
  column_name?: string
  display_name?: string
  description?: string
  tags?: string[]
  has_description?: boolean
  columns: ColumnInfo[]
}
```

- [ ] **Step 2: 在 api/index.ts 中新增 getAssetDetail**

在 import 类型列表中添加 `AssetDetail`:

```typescript
import type {
  SearchParams,
  SearchResponse,
  TargetEntity,
  CompletionResponse,
  ReviewRecord,
  ReviewDetail,
  AssetDetail,
} from './types'
```

在文件末尾添加：

```typescript
export async function getAssetDetail(entityId: string): Promise<{ success: boolean; data: AssetDetail }> {
  const { data } = await api.get(`/assets/${entityId}`)
  return data
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/index.ts
git commit -m "feat: add ColumnInfo and AssetDetail types, getAssetDetail API client"
```

---

### Task 4: 更新 AssetDetailPage 使用新 API

**Files:**
- Modify: `frontend/src/pages/AssetDetailPage.vue`

- [ ] **Step 1: 重写 script 部分**

替换第 53-86 行 (`<script setup>` 块):

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getAssetDetail } from '../api'
import type { AssetDetail, ColumnInfo } from '../api/types'

const route = useRoute()
const asset = ref<AssetDetail | null>(null)
const columns = ref<ColumnInfo[]>([])
const error = ref('')
const activeTab = ref('info')

const entityTypeLabel = computed(() => {
  if (!asset.value) return ''
  if (asset.value.entity_type === 'view') return '视图'
  return '表'
})
const statusLabel = computed(() => asset.value?.has_description ? '已补全' : '待补全')
const statusTheme = computed(() => asset.value?.has_description ? 'success' : 'warning')

const columnTableDefs = [
  { colKey: 'column_name', title: '列名', width: 180 },
  { colKey: 'data_type', title: '数据类型', width: 130 },
  { colKey: 'original_description', title: '原始描述', ellipsis: true, width: 160 },
  { colKey: 'original_tags', title: '原始标签', width: 120 },
  { colKey: 'completion_description', title: '补全描述', ellipsis: true, width: 180 },
  { colKey: 'completion_tags', title: '补全标签', width: 120 },
  { colKey: 'completion_time', title: '补全时间', width: 150 },
]

onMounted(async () => {
  const id = route.params.id as string
  if (!id) { error.value = '缺少资产标识'; return }
  try {
    const resp = await getAssetDetail(id)
    if (!resp.success || !resp.data) { error.value = '未找到该资产'; return }
    asset.value = resp.data
    columns.value = resp.data.columns || []
  } catch {
    error.value = '加载失败，请稍后重试'
  }
})
</script>
```

- [ ] **Step 2: 更新列信息 Tab 模板**

替换第 33-41 行 (columns tab-panel):

```vue
<t-tab-panel value="columns" label="列信息" v-if="asset?.entity_type !== 'column'">
  <div v-if="columns.length > 0">
    <p class="section-title">列信息 ({{ columns.length }} 列)</p>
    <t-table :data="columns" :columns="columnTableDefs" row-key="column_id" bordered stripe size="small">
      <template #original_tags="{ row }">
        <t-tag v-for="tag in row.original_tags" :key="tag" variant="light" theme="default" size="small" style="margin-right:2px">
          {{ tag }}
        </t-tag>
        <span v-if="!row.original_tags?.length">—</span>
      </template>
      <template #completion_tags="{ row }">
        <t-tag v-for="tag in row.completion_tags" :key="tag" variant="light" theme="primary" size="small" style="margin-right:2px">
          {{ tag }}
        </t-tag>
        <span v-if="!row.completion_tags?.length">—</span>
      </template>
      <template #completion_time="{ row }">
        <span v-if="row.completion_time">{{ row.completion_time }}</span>
        <span v-else>—</span>
      </template>
    </t-table>
  </div>
  <div v-else class="empty-state">
    <p>暂无列信息</p>
  </div>
</t-tab-panel>
```

- [ ] **Step 3: 验证端到端**

确认后端和前端都在运行后，在浏览器访问 `http://localhost:5173/asset/fact_trade`：
- 基本信息 Tab 正常显示资产信息
- 列信息 Tab 显示 12 列，包含列名、数据类型、原始描述、补全描述等

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/AssetDetailPage.vue
git commit -m "feat: switch AssetDetailPage to asset detail API with full column display"
```
