# Capability: 元数据搜索 (metadata-search)

## Overview

为数据治理人员提供元数据实体的搜索能力，支持关键词全文检索和结构化过滤，帮助快速定位待补全的数据库表和字段。

## Requirements

### Requirement: 关键词全文检索

支持按表名、字段名、中文名、描述等字段进行中英文关键词搜索，通过 Elasticsearch 执行全文检索，IK 分词器处理中文分词。

#### Scenario: 精确匹配搜索

- **GIVEN** OpenMetadata 已纳管 `t_user_order` (用户订单表)
- **WHEN** 用户输入关键词 "用户"
- **THEN** 返回包含 "用户" 的表和字段列表，含高亮匹配信息
- **AND** 响应时间 P95 < 500ms

#### Scenario: 模糊匹配

- **GIVEN** 存在表名 `t_customer_info`
- **WHEN** 用户输入 "custmer" (拼写错误)
- **THEN** 通过 fuzziness=AUTO 仍能匹配返回 `t_customer_info`

### Requirement: 结构化过滤

支持按数据库名、Schema、实体类型（表/字段）、数据类型等维度组合过滤搜索结果。

#### Scenario: 组合过滤

- **GIVEN** 系统纳管多个数据库的元数据
- **WHEN** 用户选择数据库 `finance_db` + Schema `public` + 实体类型 `table`
- **THEN** 仅返回满足所有过滤条件的表列表
- **AND** 多条件使用 AND 逻辑组合

#### Scenario: 按数据类型过滤字段

- **GIVEN** 表 `t_user` 包含多个不同类型的字段
- **WHEN** 用户过滤 `data_type=varchar`
- **THEN** 仅返回 varchar 类型的字段

### Requirement: 搜索分页

搜索结果支持分页，默认每页 20 条。

#### Scenario: 分页加载

- **GIVEN** 搜索关键词匹配 100 条结果
- **WHEN** 用户请求第 2 页，每页 20 条
- **THEN** 返回第 21-40 条结果
- **AND** 响应含 total、page、limit 元数据

## Data Model

搜索响应:

```json
{
  "success": true,
  "data": [
    {
      "entity_id": "finance_db.public.t_user_order",
      "entity_type": "table",
      "table_name": "t_user_order",
      "display_name": "用户订单表",
      "description": "记录用户订单信息",
      "database": "finance_db",
      "schema": "public",
      "tags": ["订单", "用户"],
      "has_description": true,
      "highlight": { "table_name": ["t_<em>user</em>_order"] }
    }
  ],
  "meta": { "total": 42, "page": 1, "limit": 20 }
}
```

## Non-Goals

- 自然语言语义搜索（后续版本 FR-SEARCH-002）
- 跨数据库联合搜索
- 搜索结果导出
