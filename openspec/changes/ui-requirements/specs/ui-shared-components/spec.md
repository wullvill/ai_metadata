# Capability: 共享 UI 组件 (ui-shared-components)

## Overview

定义跨页面复用的通用 UI 组件行为规范，包括置信度徽章、补全建议面板、审核状态徽章和通用状态组件（Loading/Error/Empty）。这些组件被 SearchPage、ReviewWorkbench、HistoryPage 共同使用。

## Requirements

### Requirement: 置信度徽章 (QualityBadge)

以颜色和文字直观展示补全结果的置信度等级。

#### Scenario: 高置信度展示

- **GIVEN** confidence >= 0.80
- **WHEN** QualityBadge 渲染
- **THEN** 显示绿色徽章，文字为「高置信度」+ 数值 (如 0.85)

#### Scenario: 中置信度展示

- **GIVEN** 0.60 <= confidence < 0.80
- **WHEN** QualityBadge 渲染
- **THEN** 显示橙色徽章，文字为「中置信度」+ 数值

#### Scenario: 低置信度展示

- **GIVEN** confidence < 0.60
- **WHEN** QualityBadge 渲染
- **THEN** 显示红色徽章，文字为「低置信度」+ 数值

#### Scenario: 无置信度

- **GIVEN** confidence 为 null 或 undefined
- **WHEN** QualityBadge 渲染
- **THEN** 显示灰色徽章，文字为「未知」

### Requirement: 补全建议面板 (CompletionPanel)

展示 AI 补全的完整结果，支持查看和建议对比。

#### Scenario: 表级补全展示

- **GIVEN** 补全结果 entity_type=table
- **WHEN** CompletionPanel 渲染
- **THEN** 展示 display_name、description、tags、business_domain、confidence（徽章）、reasoning（折叠）、model_used

#### Scenario: 字段级补全展示

- **GIVEN** 补全结果 entity_type=column
- **WHEN** CompletionPanel 渲染
- **THEN** 展示 display_name、description、tags、sensitive_level（L1-L4）、confidence（徽章）、reasoning（折叠）

#### Scenario: 补全结果与已有数据对比

- **GIVEN** 表中已有 display_name 和 description
- **WHEN** CompletionPanel 渲染对比视图
- **THEN** 左侧显示已有信息，右侧显示 AI 建议
- **AND** 差异字段高亮标记

#### Scenario: 补全加载状态

- **GIVEN** 补全请求正在进行中
- **WHEN** CompletionPanel 渲染
- **THEN** 显示骨架屏加载动画
- **AND** 显示 「AI 正在分析并生成补全建议...」

#### Scenario: 补全失败状态

- **GIVEN** 补全请求失败
- **WHEN** CompletionPanel 渲染失败状态
- **THEN** 显示错误信息
- **AND** 提供「重新补全」按钮

### Requirement: 审核状态徽章 (ReviewStatusBadge)

以颜色和文字直观展示补全审核状态。

#### Scenario: 各审核状态徽章展示

- **GIVEN** review_status = auto_approved → 绿色 「已自动采纳」
- **AND** review_status = pending_review → 橙色 「待审核」
- **AND** review_status = approved → 蓝色 「已确认」
- **AND** review_status = human_rejected → 灰色 「已拒绝」
- **AND** review_status = rejected → 红色 「系统拒绝」
- **AND** review_status = modified → 紫色 「已修改」

### Requirement: 空状态组件 (EmptyState)

统一的空数据提示组件。

#### Scenario: 搜索无结果

- **GIVEN** 搜索结果为空
- **WHEN** EmptyState 渲染，传入 message="未找到匹配的元数据"
- **THEN** 显示图标 + 自定义消息文字
- **AND** 提供提示文字建议修改搜索条件

#### Scenario: 审核队列为空

- **GIVEN** 审核队列无待审核记录
- **WHEN** EmptyState 渲染，传入 message="暂无待审核记录"
- **THEN** 显示空状态插图和消息

### Requirement: 错误状态组件 (ErrorState)

统一的错误提示组件，支持重试操作。

#### Scenario: 显示错误并重试

- **GIVEN** API 请求失败，errorMessage="加载失败，请稍后重试"
- **WHEN** ErrorState 渲染
- **THEN** 显示错误图标 + 错误消息
- **AND** 显示「重试」按钮
- **AND** 用户点击重试按钮触发 onRetry 回调

### Requirement: 加载骨架屏 (LoadingSkeleton)

数据加载中的占位骨架屏，适配表格和卡片两种布局。

#### Scenario: 表格骨架屏

- **GIVEN** 数据正在加载，type="table"
- **WHEN** LoadingSkeleton 渲染
- **THEN** 显示 5 行表格骨架屏，行高与表格一致

#### Scenario: 卡片骨架屏

- **GIVEN** 数据正在加载，type="card"
- **WHEN** LoadingSkeleton 渲染
- **THEN** 显示 3 个卡片骨架屏，尺寸与 MetadataCard 一致

## Non-Goals

- 复杂的动画过渡效果
- 组件的暗色主题变体（当前仅支持亮色主题）
- 国际化多语言支持
