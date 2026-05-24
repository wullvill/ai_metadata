# Capability: 补全历史页面 (ui-history-page)

## Overview

提供所有补全记录的历史查询和追溯能力，数据治理人员可在此查看补全操作的完整轨迹，包括自动采纳和人工审核的结果。对应后端 capability：completion-history。

## Requirements

### Requirement: 历史记录查询

以表格形式展示所有补全记录，支持分页和多维度筛选。

#### Scenario: 加载历史记录

- **GIVEN** 用户访问 `/history`
- **WHEN** 页面加载
- **THEN** 调用 API 获取补全历史记录
- **AND** 表格展示每条记录：entity_id、entity_type、review_status（状态徽章）、置信度、提交时间
- **AND** 按提交时间倒序排列

#### Scenario: 按状态筛选

- **GIVEN** 历史记录中包含多种状态的记录
- **WHEN** 用户在筛选栏选择 review_status=approved
- **THEN** 表格仅显示已确认的记录

#### Scenario: 按实体 ID 筛选

- **GIVEN** 历史记录中包含多条 `t_user_order` 的记录
- **WHEN** 用户输入 entity_id 搜索
- **THEN** 表格仅显示该实体的所有历史补全记录

#### Scenario: 按时限筛选

- **GIVEN** 系统中有最近 30 天的历史记录
- **WHEN** 用户选择时间范围「近 7 天」
- **THEN** 表格仅显示近 7 天内的记录

#### Scenario: 分页加载

- **GIVEN** 历史记录超过一页
- **WHEN** 用户点击下一页或切换每页条数
- **THEN** 表格更新显示对应页数据

### Requirement: 状态轨迹展示

每条记录的补全和审核轨迹完整可追溯。

#### Scenario: 查看状态时间线

- **GIVEN** 一条记录经历了 pending_review → approved → synced_to_om
- **WHEN** 用户查看该记录的状态列
- **THEN** 显示状态徽章，鼠标悬停展示状态变更时间线

### Requirement: 加载与错误状态

#### Scenario: 历史记录加载中

- **GIVEN** 用户访问 `/history`
- **WHEN** API 请求进行中
- **THEN** 表格区域显示骨架屏 Loading 状态

#### Scenario: 无历史记录

- **GIVEN** 系统无任何补全记录
- **WHEN** 页面加载完成
- **THEN** 显示 「暂无补全历史记录」空状态

#### Scenario: 加载失败

- **GIVEN** API 返回错误
- **WHEN** 历史记录请求失败
- **THEN** 显示 「加载失败」错误提示和重试按钮

## Non-Goals

- 历史记录的删除/归档
- 数据分析/统计面板
- 数据导出功能
