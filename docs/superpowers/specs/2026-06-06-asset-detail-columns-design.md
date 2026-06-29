# Asset Detail with Columns — Design

**Date:** 2026-06-06
**Status:** approved

## Goal

搜索列表仅返回 table/view，列的完整信息仅在资产详情页展示。新增独立的 ES 列索引和资产详情 API。

## Data

**Source:** `design-ui/asset_detail.html` ASSETS 数组，15 个资产（13 表 + 2 视图），共计约 110 列。

**ES 中关联:** metadata_index 的 15 条 entity_id 与 HTML 数据完全匹配。

## Architecture

```
搜索页                         资产详情页
  │                               │
  ▼                               ▼
POST /api/v1/search          GET /api/v1/assets/{entity_id}
  │                               │
  ▼                               ▼
metadata_index ──────────→  metadata_index (基本信息)
                            metadata_columns (列清单)
```

## 1. New ES Index: `metadata_columns`

**Mapping:**

| field | type | note |
|-------|------|------|
| column_id | keyword | `{entity_id}.{column_name}` |
| entity_id | keyword | 关联父表/视图 |
| column_name | text + .raw keyword | |
| data_type | keyword | |
| original_description | text | |
| original_tags | keyword[] | |
| completion_description | text | |
| completion_tags | keyword[] | |
| completion_time | date | |

## 2. Backend Changes

### 2.1 `elasticsearch.py` — 新增函数

- `ensure_columns_index()` — 创建 metadata_columns 索引
- `index_columns(entity_id, columns: list[dict])` — 批量索引列的独立文档
- `get_columns(entity_id) -> list[dict]` — 按 entity_id 查询所有列

### 2.2 新增 API: `GET /api/v1/assets/{entity_id}`

**实现:**
1. `es.get(index="metadata_index", id=entity_id)` 精确取资产信息
2. `get_columns(entity_id)` 查列清单
3. 合并返回

**Response:**
```json
{
  "success": true,
  "data": {
    "entity_id": "fact_trade",
    "entity_type": "table",
    "columns": [...]
  }
}
```

**错误处理:** entity_id 不存在返回 404

## 3. Frontend Changes

### 3.1 `api/types.ts`

- `MetadataEntity.entity_type` 扩展为 `'table' | 'view'`
- 新增 `ColumnInfo` 接口
- 新增 `AssetDetail` 接口

### 3.2 `api/index.ts`

- 新增 `getAssetDetail(id: string)` 调用 `GET /api/v1/assets/{entity_id}`

### 3.3 `AssetDetailPage.vue`

- 替换当前的 `searchMetadata({ query: id })` 为 `getAssetDetail(id)`
- 列信息 Tab 改为从返回数据的 `columns` 字段渲染

### 3.4 `SearchPage.vue`

- 无需改动

## 4. Data Import

从 `design-ui/asset_detail.html` 的 ASSETS 数组提取 column 数据，批量导入 `metadata_columns` 索引。提取规则：
- 取 type 为 "表" 或 "视图" 且有 `columns` 数组的条目
- 每条 column 生成独立文档，column_id = `{entity_id}.{column_name}`

## 5. Migration Steps

1. 创建 `metadata_columns` 索引 + 映射
2. 导入列数据
3. 新增后端 ES 函数
4. 新增后端 API 路由
5. 更新前端 types + api client
6. 更新前端 AssetDetailPage
7. 验证端到端
