# Capability: 补全历史 (completion-history)

## Overview

提供所有补全记录的完整历史查询能力，支持按实体、状态、时间范围等维度筛选，确保补全操作的审计追溯。

## Requirements

### Requirement: 补全历史查询

查询所有补全记录的历史，支持分页和多维度筛选。

#### Scenario: 按时限查询

- **GIVEN** 系统中有过去 30 天的补全记录
- **WHEN** 用户查询近 7 天的补全历史
- **THEN** 仅返回时间范围内的记录，按创建时间倒序排列

#### Scenario: 按实体筛选

- **GIVEN** 表 `t_user_order` 有多次补全记录
- **WHEN** 用户按 entity_id 筛选
- **THEN** 返回该表的所有历史补全记录，含各次补全的阶段结果

#### Scenario: 按状态筛选

- **GIVEN** 系统有多种状态的补全记录
- **WHEN** 用户筛选 review_status = "human_rejected"
- **THEN** 仅返回被人工拒绝的记录

### Requirement: 状态轨迹追溯

每条补全记录的状态变更轨迹完整可追溯。

#### Scenario: 查看状态变更轨迹

- **GIVEN** 一条补全记录经历了 pending_review → approved → synced_to_om
- **WHEN** 查看该记录的详情
- **THEN** 展示完整状态变更历史，含各状态的时间戳和操作人
- **AND** 关联的审核操作记录（确认/修改/拒绝）

## Non-Goals

- 补全记录的删除/归档
- 历史数据的统计分析/报表
- 数据导出功能
