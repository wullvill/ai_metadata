"""Prompt 模板"""

TABLE_COMPLETION_PROMPT = """你是数据治理专家。请根据已有元数据参考，为下面这张数据库表补全元数据信息。

## 待补全的表
- 库名: {database}
- Schema: {schema}
- 表名: {table_name}
- 已有描述: {current_description}
- 已有中文名: {current_display_name}
- 该表包含的字段: {columns_summary}

## 同库兄弟表（了解表所处的业务上下文）
{schema_context}

## 相似表的元数据参考（按相关度排序）
{retrieved_context}

## 请补全以下信息，以 JSON 格式返回：
{{
  "display_name": "表的中文名称（简洁，10 字以内）",
  "description": "表的业务描述（1-3 句话，说明表的作用和包含的数据内容）",
  "tags": ["标签1", "标签2", "标签3"],
  "business_domain": "所属业务域（如：用户域、交易域、营销域、财务域等）",
  "confidence": 0.85,
  "reasoning": "简要说明补全依据（可选）"
}}

## 要求：
1. 中文名应简洁准确，符合数据仓库命名规范
2. 描述应包含表的业务含义和主要用途
3. 标签控制在 3-5 个
4. 参考已有相似的元数据，保持同库风格一致
5. 如果现有信息不足以做出判断，confidence 应反映真实置信度
"""

COLUMN_COMPLETION_PROMPT = """你是数据治理专家。请根据已有元数据参考，为下面这个数据库字段补全元数据信息。

## 待补全的字段
- 所属表: {database}.{schema}.{table_name}
- 表的业务含义: {table_description}
- 字段名: {column_name}
- 数据类型: {data_type}
- 已有描述: {current_description}
- 已有中文名: {current_display_name}

## 同表其他字段（了解字段所在上下文）
{sibling_columns}

## 相似字段的元数据参考（按相关度排序）
{retrieved_context}

## 请补全以下信息，以 JSON 格式返回：
{{
  "display_name": "字段的中文名称（简洁，15 字以内）",
  "description": "字段的业务含义说明（1-2 句话）",
  "tags": ["标签1", "标签2"],
  "sensitive_level": "L1|L2|L3|L4",
  "confidence": 0.85,
  "reasoning": "简要说明补全依据（可选）"
}}

## 要求：
1. 中文名应准确反映字段的业务含义，而非简单的英文翻译
2. 描述应说明字段存储什么数据、用于什么业务场景
3. 敏感级别：L1=公开, L2=内部, L3=敏感, L4=机密（根据字段名和类型判断，如id_card→L3）
4. 参考相似字段的命名和描述风格，保持一致
"""
