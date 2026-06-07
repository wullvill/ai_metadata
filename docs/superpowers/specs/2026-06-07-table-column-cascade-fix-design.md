# 表级补全级联字段修复

**日期**: 2026-06-07
**状态**: 已确认
**方案**: B — 修复 ES 查询 + 审核详情展示字段补全结果

## 问题

点击「申请补全」按钮对表资产触发补全后：
1. 表的字段（列）信息未被级联补全
2. 审核工作台看不到列的补全记录

## 根因

| # | 位置 | 问题 |
|---|------|------|
| 1 | `backend/app/api/complete.py:102-116` `_fetch_columns` | ES 查询用 `entity_id`（表的 ID）匹配字段，但字段有独立的 `entity_id`，查询永远返回空 |
| 2 | `frontend/src/pages/ReviewPage.vue:58-62` | 前端默认过滤隐藏 `entity_type === 'column'` 的记录（设计意图，非 bug） |
| 3 | 缺失功能 | `ReviewDetail.vue` 无字段补全结果展示，即使字段记录存在也无法从表详情中查看 |

## 设计

### 交互模式

- 审核工作台：仅展示表级记录（当前前端默认过滤行为保持不变）
- 进入表详情弹窗：新增「字段补全」Tab，展示该表所有字段的 AI 补全结果

### 后端改动

#### 1. 修复 `_fetch_columns` ES 查询

**文件**: `backend/app/api/complete.py`

将 `entity_id` term 匹配改为 `database` + `schema` + `table_name` 组合条件：

```python
async def _fetch_columns(target: dict) -> list[dict]:
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

#### 2. 新增 API `GET /review/{record_id}/columns`

**文件**: `backend/app/api/review.py`

放在 `GET /review/{record_id}` 之前，避免路由冲突。

查询逻辑：字段记录的 `entity_id` 格式为 `{表entity_id}.{column_name}`，用 LIKE 前缀匹配。

响应格式：`{ success: bool, data: ReviewRecord[] }`，每条字段记录包含 id、entity_id、completion_result、quality_check、review_status 等。

### 前端改动

#### 3. 新增 API 函数

**文件**: `frontend/src/api/index.ts`

```ts
export async function getRecordColumns(recordId: string): Promise<{ success: boolean; data: ReviewRecord[] }> {
  const { data } = await api.get(`/review/${recordId}/columns`)
  return data
}
```

#### 4. ReviewDetail 新增「字段补全」Tab

**文件**: `frontend/src/components/ReviewDetail.vue`

- 当 `detail.entity_type === 'table'` 时显示「字段补全」Tab
- 进入 Tab 时调用 `getRecordColumns` 获取字段列表
- 每行展示：字段名（entity_id）、建议中文名、描述、置信度进度条、审核状态标签
- 空数据时显示「暂无字段补全记录」

## 涉及文件

| 文件 | 改动类型 |
|------|----------|
| `backend/app/api/complete.py` | 修复 `_fetch_columns` ES 查询 |
| `backend/app/api/review.py` | 新增 `GET /{record_id}/columns` 端点 |
| `frontend/src/api/index.ts` | 新增 `getRecordColumns` 函数 |
| `frontend/src/components/ReviewDetail.vue` | 新增「字段补全」Tab |

## 测试要点

- [ ] 对表点击「申请补全」后，后端日志确认字段列表被正确获取
- [ ] `completion_records` 表中出现 `entity_type='column'` 的记录
- [ ] 审核工作台默认不显示字段记录
- [ ] 点击表记录进入详情弹窗，「字段补全」Tab 正确展示字段列表
- [ ] 无字段数据时 Tab 显示空状态提示
- [ ] 非表类型记录不显示该 Tab
