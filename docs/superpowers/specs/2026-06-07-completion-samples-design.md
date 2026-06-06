# Completion Samples Design

**Date:** 2026-06-07
**Status:** approved
**Context:** 资产搜索页面，增加资产「补全样本」的管理功能

## Overview

在资产搜索页面增加设置/取消「补全样本」功能，支持单个和批量操作。样本标记存储在 ES `metadata_index` 中，在补全 Pipeline 检索阶段自动提权，作为 LLM 补全的参考数据。

## 1. ES 数据层

### metadata_index 新增字段

```python
"is_sample": {"type": "boolean"}  # 默认 false，缺失视为 false
```

- 无需数据迁移，新增字段对已有文档透明
- 写入：ES update_by_query，按 entity_ids 批量更新
- 读取：ES term query `{ "term": { "is_sample": true } }`

## 2. 后端 API

### `POST /api/v1/samples/set`

设置/取消样本标记。

- Request: `{ entity_ids: string[], is_sample: boolean }`
- Response: `{ success: true, updated: number }`
- 实现：ES update_by_query，script 更新 `is_sample` 字段

### `GET /api/v1/samples`

获取全部样本列表。

- Response: `{ success: true, data: entity[] }`
- 实现：ES term query `is_sample = true`，返回完整 `_source`

### ES 服务方法

`elasticsearch.py` 新增：

```python
def set_sample_flag(entity_ids: list[str], is_sample: bool) -> int:
    """批量设置/取消样本标记，返回更新数"""

def get_samples() -> list[dict]:
    """获取全部样本"""
```

## 3. Pipeline 集成

### Stage 1 修改（`stage1_retrieve.py`）

在双路检索后、RRF 合并前，查询全部样本并置顶：

1. 调用 `elasticsearch.get_samples()` 获取样本列表
2. 将样本以最高 rank（rank=0）混入检索结果
3. 其他逻辑（RRF、降级）不变

样本在检索结果中自然排在前面，Stage 2 的 LLM prompt 不需要额外改动，因为样本已经出现在 `retrieved_context` 中并被 prompt 当作参考上下文使用。

## 4. 前端

### SearchPage.vue

**样本列**：在「补全状态」列之后、「操作」列之前插入：

```typescript
{ colKey: 'is_sample', title: '样本', width: 80 },
```

每行渲染 `t-switch` 组件，v-model 绑定 `row.is_sample`，change 事件调用 API。

**批量操作**：ops-bar-right 区域增加两个按钮，与「批量申请补全」并列：

- 「批量设为样本」— 选中行调用 `setSamples(ids, true)`
- 「批量取消样本」— 选中行调用 `setSamples(ids, false)`
- 无选中时 disabled

### api/index.ts

```typescript
export async function setSamples(entityIds: string[], isSample: boolean) {
  await api.post('/samples/set', { entity_ids: entityIds, is_sample: isSample })
}
```

### types.ts

`MetadataEntity` 新增：

```typescript
is_sample?: boolean
```

### Composables

不新增 composable，开关的 API 调用直接在 SearchPage 的 handler 中完成。

## 5. 错误处理

| 场景 | 处理 |
|------|------|
| 样本 toggle API 失败 | `MessagePlugin.error` 提示，恢复开关状态 |
| 样本数据为空 | 正常行为，检索结果不含样本提权 |
| ES is_sample 字段不存在 | 视为 false |

## 6. 涉及文件

| 文件 | 改动 |
|------|------|
| `backend/app/services/elasticsearch.py` | 新增 `set_sample_flag`、`get_samples` |
| `backend/app/api/samples.py` | 新建 Router，`/samples/set` 和 `/samples` |
| `backend/app/api/schemas.py` | 新增 `SampleSetRequest` |
| `backend/app/main.py` | 注册 sample_router |
| `backend/app/pipeline/stage1_retrieve.py` | 样本查询 + 提权混入 |
| `frontend/src/api/index.ts` | 新增 `setSamples` |
| `frontend/src/api/types.ts` | `MetadataEntity` 新增 `is_sample` |
| `frontend/src/pages/SearchPage.vue` | 新增样本列 + 批量按钮 |

## 7. 测试要点

- [ ] API `/samples/set`：批量设置、取消、空列表
- [ ] API `/samples`：空样本、有样本
- [ ] ES `get_samples`：term query 正确
- [ ] Pipeline Stage 1：样本置顶行为
- [ ] 前端：开关切换、批量按钮、API 失败恢复
