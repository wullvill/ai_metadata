# Capability: 双路检索 (dual-path-retrieval)

## Overview

为 LLM 生成阶段提供高质量的参考上下文，通过 Milvus 向量检索（语义相似）和 Elasticsearch 关键词检索（精确匹配）双路并行检索，使用 RRF 算法融合排序，输出 Top 15 最有参考价值的已有元数据。

## Requirements

### Requirement: 向量语义检索

将待补全实体向量化后，在 Milvus 中检索语义相似的已有元数据。

#### Scenario: 语义相似检索

- **GIVEN** 待补全表为 `t_client`，已有元数据含 `t_customer`（客户表，有完整描述）
- **WHEN** 查询文本 `finance_db.public.t_client` 向量化后检索 Milvus
- **THEN** `t_customer` 出现在检索结果中（语义相似）
- **AND** 使用 COSINE 度量，Top K=20
- **AND** 仅检索 has_description=true 的实体

#### Scenario: 过滤已描述实体

- **GIVEN** Milvus 中有 100 条实体，其中 40 条无描述
- **WHEN** 向量检索时应用 `has_description==true` 过滤
- **THEN** 仅从 60 条有描述的实体中检索

### Requirement: 关键词精确检索

通过 ES 执行表名/字段名的精确和模糊匹配，补充向量检索的精确匹配短板。

#### Scenario: 精确匹配搜索

- **GIVEN** 待补全字段为 `order_status`
- **WHEN** 在 ES 中按 column_name 检索
- **THEN** 返回其他表中同样名为 `order_status` 的字段及其已有描述
- **AND** 使用 ik_max_word 分词器处理中文内容

### Requirement: RRF 结果融合

使用 Reciprocal Rank Fusion 算法合并双路检索结果并重排序。

#### Scenario: 双路结果合并

- **GIVEN** Milvus 返回 20 条，ES 返回 20 条
- **WHEN** RRF 合并（k=60）
- **THEN** 输出 Top 15 合并结果
- **AND** 同时出现在两路的结果获得更高 RRF 分数
- **AND** 每条结果标注来源：milvus / es / both

#### Scenario: 单路降级 — Milvus 不可用

- **GIVEN** Milvus 不可用
- **WHEN** 执行检索
- **THEN** 回退为仅 ES 检索，返回 ES Top 15

#### Scenario: 单路降级 — ES 不可用

- **GIVEN** ES 不可用
- **WHEN** 执行检索
- **THEN** 回退为仅 Milvus 检索，返回 Milvus Top 15

#### Scenario: 双路均不可用

- **GIVEN** 双路均不可用
- **WHEN** 执行检索
- **THEN** 返回错误，提示稍后重试

### Requirement: 上下文增强

除检索结果外，额外检索目标实体所在 Schema 的兄弟表/字段。

#### Scenario: 兄弟实体上下文

- **GIVEN** 待补全表 `t_order` 在 Schema `trade` 下，同 Schema 另有 20 张表
- **WHEN** 上下文增强时查询同 Schema 的其他表
- **THEN** 返回 Top 5 同 Schema 表
- **AND** 这些表的信息包含在 Stage 2 的 Prompt 中

## Non-Goals

- 跨 Schema / 跨数据库的关联检索
- 检索结果缓存策略优化
- 图像/文档等非结构化数据检索
