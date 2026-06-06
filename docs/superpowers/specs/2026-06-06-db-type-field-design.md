# Database Type Field — Design

**Date:** 2026-06-06
**Status:** approved

## Goal

在资产列表、筛选器和资产详情中新增"数据库类型"字段，支持 MySQL、PostgreSQL、Oracle、Hive、StarRocks 等。

## Data Mapping (database → db_type)

| db_type | databases |
|---------|-----------|
| MySQL | ods_trade, ods_settle, ods_market, ods_finance (4) |
| PostgreSQL | dwd_master, dwd_risk, dwd_common, dwd_comply, dwd_position, dws_agg (6) |

## Backend Changes

### elasticsearch.py — MAPPINGS

新增: `"db_type": {"type": "keyword"}`

### elasticsearch.py — search_all()

新增可选参数 `db_type: str | None = None`，作为 term filter。

### elasticsearch.py — get_filter_options()

新增 `db_types` 聚合，返回 distinct db_type 值。

### search.py — SearchRequest schema

新增可选字段: `db_type: str | None = None`

### Data migration

更新 ES metadata_index 中 15 个文档，按 mapping 添加 `db_type` 字段。

## Frontend Changes

### api/types.ts

- `MetadataEntity` + `db_type?: string`
- `FilterOptions` + `db_types: string[]`
- `SearchParams` + `db_type?: string`

### SearchPage.vue

- 表格新增 "数据库类型" 列（在"所属库"之后）
- 搜索栏新增 db_type 下拉筛选器
- `localFilters` + `dbType`

### AssetDetailPage.vue

基本信息 Tab 新增 "数据库类型" 行。

## Files Summary

| File | Action |
|------|--------|
| `backend/app/services/elasticsearch.py` | Modify — MAPPINGS, search_all, get_filter_options |
| `backend/app/api/search.py` | Modify — SearchRequest schema |
| `frontend/src/api/types.ts` | Modify — 3 interfaces |
| `frontend/src/pages/SearchPage.vue` | Modify — column, filter, localFilters |
| `frontend/src/pages/AssetDetailPage.vue` | Modify — detail row |
