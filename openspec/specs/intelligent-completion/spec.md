# Capability: 智能补全 (intelligent-completion)

## Overview

为大模型驱动的元数据补全提供触发和管理能力，支持手工触发、批量触发和定时自动触发三种模式，覆盖交互式、批量和自动化场景。

## Requirements

### Requirement: 手工触发补全

用户在搜索界面选中元数据实体后，点击「智能补全」按钮触发四阶段 Pipeline：双路检索 → LLM 生成 → 质量校验 → 审核路由。

#### Scenario: 手工触发表的智能补全

- **GIVEN** 用户搜索到表 `t_user_order`，当前缺少中文名和描述
- **WHEN** 用户选中该表并点击「智能补全」
- **THEN** 系统执行四阶段 Pipeline
- **AND** 返回补全建议，含中文名、业务描述、标签、置信度、推理依据
- **AND** 端到端响应时间 P95 < 10s

#### Scenario: 手工触发字段的智能补全

- **GIVEN** 表 `t_order` 的字段 `status` 缺少中文名和描述
- **WHEN** 用户选中该字段并点击「智能补全」
- **THEN** 系统返回字段级补全建议
- **AND** 补全内容含 display_name、description、tags、sensitive_level

### Requirement: 批量补全

通过 API 提交一批实体，异步执行补全，支持进度查询。

#### Scenario: API 批量补全

- **GIVEN** 用户通过 API 提交 50 个实体 ID 列表
- **WHEN** POST /api/v1/complete/batch 提交批量任务
- **THEN** 返回任务 ID
- **AND** 各实体独立执行 Pipeline，互不影响
- **AND** 可通过任务 ID 查询整体进度和各实体状态

#### Scenario: 批量任务进度查询

- **GIVEN** 批量任务正在执行中（30/50 已完成）
- **WHEN** 查询任务进度
- **THEN** 返回 completed: 30, total: 50, failed: 0

#### Scenario: 单实体失败不影响整体

- **GIVEN** 批量任务包含一个无效实体 ID
- **WHEN** 任务执行到该实体时 LLM 调用失败
- **THEN** 该实体标记失败并记录错误原因
- **AND** 其余实体正常完成

### Requirement: 表级补全

为数据库表补全中文名、业务描述、标签、业务域。

#### Scenario: 表级补全内容

- **GIVEN** 表 `risk_db.public.t_credit_score` 无中文名和描述
- **WHEN** 触发补全
- **THEN** 返回 display_name（≤10字）、description（1-3句）、tags（2-5个）、business_domain、confidence
- **AND** Prompt 含同库兄弟表和相似表参考上下文

### Requirement: 字段级补全

为数据库字段补全中文名、业务描述、标签、敏感级别。

#### Scenario: 字段级补全内容

- **GIVEN** 字段 `credit_amount` (decimal 类型) 缺少中文名和描述
- **WHEN** 触发补全
- **THEN** 返回 display_name（≤15字）、description（1-2句）、tags、sensitive_level（L1-L4）、confidence
- **AND** Prompt 含同表其他字段和相似字段参考上下文

#### Scenario: 敏感级别推断

- **GIVEN** 字段名含 `id_card` 或 `phone`
- **WHEN** LLM 分析字段名和上下文
- **THEN** sensitive_level 应为 L3（个人敏感信息）或 L4（个人隐私信息）

### Requirement: LLM 输出格式约束

LLM 必须返回严格 JSON 格式，系统需要解析后进入质量校验。

#### Scenario: 正常 JSON 返回

- **GIVEN** LLM 正常返回 JSON
- **WHEN** 解析 LLM 响应
- **THEN** 直接解析 JSON 成功，进入 Stage 3

#### Scenario: JSON 含 Markdown 包裹

- **GIVEN** LLM 返回 ```json { ... } ``` 格式
- **WHEN** 解析时 JSON 解析失败
- **THEN** 正则提取代码块中 JSON，解析成功

#### Scenario: JSON 解析失败重试

- **GIVEN** LLM 返回纯文本，无法提取 JSON
- **WHEN** 解析失败
- **THEN** 使用原始参数重试 1 次
- **AND** 仍失败则标记错误并返回

## Data Model

补全结果:

```json
{
  "entity_id": "finance_db.public.t_user_order",
  "entity_type": "table",
  "completion_result": {
    "display_name": "用户订单表",
    "description": "记录用户下单购买商品的核心业务表",
    "tags": ["订单", "用户", "交易"],
    "business_domain": "交易域",
    "confidence": 0.85,
    "reasoning": "表名含user和order，同库兄弟表多为交易相关表"
  },
  "review_status": "auto_approved"
}
```

## Non-Goals

- 自然语言驱动的补全触发
- 补全结果自动应用到业务系统（必须经过审核）
- 补全建议的多模型投票/ensemble
