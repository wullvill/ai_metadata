# Capability: 人工审核 (human-review)

## Overview

为数据治理人员提供补全结果的审核工作台，支持对 pending_review 状态的补全记录进行确认、修改或拒绝操作，支持批量审核，审核确认后自动回写 OpenMetadata。

## Requirements

### Requirement: 审核队列

展示待审核的补全记录列表，支持分页、筛选和排序。

#### Scenario: 查看审核队列

- **GIVEN** 系统中有 50 条 pending_review 状态的补全记录
- **WHEN** 数据治理人员打开审核工作台
- **THEN** 展示待审核列表，每条记录显示 entity_id、entity_type、置信度、提交时间、问题标记
- **AND** 分页加载 P95 < 500ms

#### Scenario: 多维度筛选

- **GIVEN** 审核队列中有不同类型的记录
- **WHEN** 用户筛选 entity_type=table + database=finance_db + confidence_range=0.6-0.8
- **THEN** 仅返回满足所有筛选条件的记录

#### Scenario: 排序切换

- **GIVEN** 审核队列默认按提交时间倒序
- **WHEN** 用户切换为按置信度从低到高排序
- **THEN** 列表重新排序，低置信度（高风险）记录优先展示

### Requirement: 审核操作

对单条补全记录执行确认、修改或拒绝。

#### Scenario: 确认补全

- **GIVEN** 补全记录 review_status = "pending_review"，AI 建议合理
- **WHEN** 治理人员点击「确认」
- **THEN** 弹出二次确认对话框
- **AND** 确认后 review_status → "approved"，触发 OM 回写
- **AND** 记录审核人、审核时间到审计日志

#### Scenario: 修改后确认

- **GIVEN** AI 生成的 display_name 需要微调
- **WHEN** 治理人员修改 display_name 后点击「确认修改」
- **THEN** 保存修改后的版本，review_status → "modified"
- **AND** 回写修改后版本到 OpenMetadata

#### Scenario: 拒绝补全

- **GIVEN** AI 生成的补全结果完全错误
- **WHEN** 治理人员点击「拒绝」并填写拒绝原因
- **THEN** review_status → "human_rejected"
- **AND** 不回写 OpenMetadata，记录拒绝原因到审计日志

### Requirement: 批量审核

支持勾选多条记录，批量确认或批量拒绝。

#### Scenario: 批量确认

- **GIVEN** 同数据库的 5 张表补全结果质量一致
- **WHEN** 治理人员勾选这 5 条记录 → 点击「批量确认」
- **THEN** 显示处理进度（1/5, 2/5...）
- **AND** 部分失败不影响其他记录的确认

#### Scenario: 批量拒绝

- **GIVEN** 一批字段补全结果系统性错误
- **WHEN** 治理人员全选后点击「批量拒绝」
- **THEN** 批量更新为 human_rejected，记录统一拒绝原因

### Requirement: 审核详情

展示单条补全的完整信息，辅助审核决策。

#### Scenario: 查看审核详情

- **GIVEN** 审核队列中有一条记录
- **WHEN** 治理人员点击该记录
- **THEN** 展示完整信息：
  - 原始元数据（表名/字段名、已有信息）
  - AI 补全建议（中文名、描述、标签、敏感级别）
  - 检索参考上下文（相似元数据列表）
  - 质量校验结果（置信度、规则命中、冲突标记）
  - 操作历史（提交时间、审核人、审核时间）

## Data Model

审核操作请求:

```json
{
  "action": "approve",
  "comment": "AI补全结果与业务定义一致"
}
```

修改后确认:

```json
{
  "action": "modify",
  "modifications": {
    "display_name": "客户信用评分表",
    "description": "存储客户信用评分的核心表"
  },
  "comment": "调整了中文名和描述"
}
```

## Non-Goals

- 审核工作流的多人会签机制
- 审核意见的讨论/评论功能
- 审核操作的回滚/撤销
