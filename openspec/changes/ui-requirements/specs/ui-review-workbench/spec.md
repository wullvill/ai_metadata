# Capability: 审核工作台页面 (ui-review-workbench)

## Overview

数据治理人员审核 AI 补全结果的主要工作界面，提供审核队列管理、筛选排序、批量操作和单条审核详情弹窗。对应后端 capability：human-review、quality-validation。

## Requirements

### Requirement: 审核队列展示

以表格形式展示所有 pending_review 状态的补全记录，支持分页和排序。

#### Scenario: 加载审核队列

- **GIVEN** 用户访问 `/review`
- **WHEN** 页面加载
- **THEN** 调用 GET /api/v1/review/queue 获取待审核记录
- **AND** 表格展示每条记录：entity_id、entity_type、置信度、状态徽章、提交时间
- **AND** 加载期间显示骨架屏或 Loading 状态

#### Scenario: 审核队列为空

- **GIVEN** 当前无待审核记录
- **WHEN** 页面加载完成
- **THEN** 显示 「暂无待审核记录」空状态

#### Scenario: 分页加载

- **GIVEN** 审核队列有 50 条记录
- **WHEN** 用户点击下一页
- **THEN** 加载第 2 页数据，表格更新

#### Scenario: 按置信度排序

- **GIVEN** 审核队列默认按提交时间倒序
- **WHEN** 用户点击置信度列头排序
- **THEN** 表格按置信度从低到高排列
- **AND** 再次点击切换为从高到低

### Requirement: 审核队列筛选

支持按状态、实体类型、数据库等维度筛选审核队列。

#### Scenario: 按实体类型筛选

- **GIVEN** 审核队列中有 table 和 column 两类记录
- **WHEN** 用户在筛选栏选择 entity_type=table
- **THEN** 表格仅显示表的补全记录

#### Scenario: 按置信度范围筛选

- **GIVEN** 审核队列中记录置信度在 0.5-0.9 之间
- **WHEN** 用户设置置信度范围 0.6-0.8
- **THEN** 表格仅显示置信度在此范围内的记录

### Requirement: 审核详情弹窗

点击审核队列中的记录，弹出详情弹窗展示完整补全信息。

#### Scenario: 打开审核详情

- **GIVEN** 审核队列中有一条记录
- **WHEN** 用户点击该记录行
- **THEN** 弹出详情弹窗，展示：
  - 原始元数据（表名/字段名、已有中文名、已有描述）
  - AI 补全建议（display_name、description、tags、置信度）
  - 质量校验结果（规则命中、冲突标记）
  - 检索参考上下文（相似元数据列表）

#### Scenario: 关闭详情弹窗

- **GIVEN** 审核详情弹窗已打开
- **WHEN** 用户点击关闭按钮或背景遮罩
- **THEN** 弹窗关闭，回到审核队列

### Requirement: 确认操作

在详情弹窗中点击「确认」接受 AI 补全建议。

#### Scenario: 确认补全

- **GIVEN** 审核详情弹窗中展示 AI 补全建议
- **WHEN** 用户点击「确认」按钮
- **THEN** 弹出二次确认对话框：「确认采纳此补全建议？将回写至 OpenMetadata」
- **AND** 用户再次确认后调用 POST /api/v1/review/{id}/approve
- **AND** 操作成功后弹窗关闭，该记录从审核队列移除
- **AND** 显示 「已确认采纳」成功提示

#### Scenario: 确认操作失败

- **GIVEN** API 调用失败
- **WHEN** 用户点击确认后 API 返回错误
- **THEN** 显示 「操作失败，请稍后重试」错误提示
- **AND** 弹窗保持打开，用户可重试

### Requirement: 修改后确认

在详情弹窗中允许用户修改 AI 建议后再确认。

#### Scenario: 修改后确认

- **GIVEN** AI 生成的 display_name 不够准确
- **WHEN** 用户在详情弹窗中编辑 display_name
- **AND** 点击「确认修改」按钮
- **THEN** 调用 POST /api/v1/review/{id}/modify 提交修改后版本
- **AND** 操作成功后弹窗关闭，显示 「已修改并确认」

#### Scenario: 修改状态指示

- **GIVEN** 用户修改了 AI 建议中任一字段
- **WHEN** 任一字段值与 AI 原始值不同
- **THEN** 该字段显示修改标记（边框高亮或图标指示）
- **AND** 「确认修改」按钮变为可用状态

### Requirement: 拒绝操作

在详情弹窗中点击「拒绝」驳回 AI 补全建议。

#### Scenario: 拒绝补全

- **GIVEN** AI 补全结果与业务语义不符
- **WHEN** 用户点击「拒绝」按钮
- **THEN** 弹出拒绝原因输入对话框（必填）
- **AND** 用户填写原因后点击确认
- **AND** 调用 POST /api/v1/review/{id}/reject
- **AND** 操作成功后弹窗关闭，记录从审核队列移除

#### Scenario: 拒绝原因必填校验

- **GIVEN** 拒绝原因输入框为空
- **WHEN** 用户点击确认拒绝
- **THEN** 显示 「请填写拒绝原因」校验提示
- **AND** 不发起 API 请求

### Requirement: 批量操作

在审核队列表格中支持勾选多条记录，批量确认或拒绝。

#### Scenario: 勾选多条记录

- **GIVEN** 审核队列中有多条记录
- **WHEN** 用户勾选多条记录
- **THEN** 批量操作工具栏显示已选数量
- **AND** 「批量确认」「批量拒绝」按钮变为可用

#### Scenario: 批量确认

- **GIVEN** 用户勾选了 5 条记录
- **WHEN** 用户点击「批量确认」
- **THEN** 弹出二次确认：「确认批量采纳 5 条补全建议？」
- **AND** 确认后调用 POST /api/v1/review/batch/approve
- **AND** 显示处理进度，完成后更新列表

#### Scenario: 批量拒绝

- **GIVEN** 用户勾选了 3 条记录
- **WHEN** 用户点击「批量拒绝」
- **THEN** 弹出拒绝原因输入框（必填）
- **AND** 确认后调用 POST /api/v1/review/batch/reject

#### Scenario: 未勾选时禁用批量按钮

- **GIVEN** 审核队列中有记录但未勾选任何项
- **WHEN** 页面渲染批量操作工具栏
- **THEN** 「批量确认」「批量拒绝」按钮置灰不可点击

### Requirement: 加载与错误状态

#### Scenario: 审核队列加载失败

- **GIVEN** API 返回错误
- **WHEN** 审核队列请求失败
- **THEN** 显示 「加载失败，请稍后重试」错误提示
- **AND** 提供「重试」按钮

## Non-Goals

- 审核流程的多人会签/审批链
- 审核意见的讨论/评论功能
- 审核操作的回滚/撤销
