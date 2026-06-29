# Capability: 元数据搜索页面 (ui-search-page)

## Overview

数据治理人员进入系统的默认页面，提供元数据搜索、结构化过滤、结果浏览和智能补全触发的一站式入口。对应后端 capability：metadata-search、intelligent-completion。

## Requirements

### Requirement: 搜索栏

页面顶部提供搜索栏，支持关键词输入和即时搜索。

#### Scenario: 输入关键词搜索

- **GIVEN** 用户在搜索页面，搜索栏为空
- **WHEN** 用户输入 "用户" 并按下回车或点击搜索按钮
- **THEN** 系统调用 POST /api/v1/search 获取匹配结果
- **AND** 搜索结果列表更新展示匹配的元数据实体
- **AND** 搜索加载期间显示 Loading 状态

#### Scenario: 空关键词搜索

- **GIVEN** 搜索栏为空
- **WHEN** 用户直接点击搜索按钮
- **THEN** 返回全部元数据实体列表（不过滤关键词）

#### Scenario: 搜索防抖

- **GIVEN** 用户在搜索栏快速连续输入
- **WHEN** 输入间隔小于 300ms
- **THEN** 仅在用户停止输入 300ms 后发起一次搜索请求

### Requirement: 结构化过滤

搜索栏下方提供可展开的过滤面板，支持多维度组合筛选。

#### Scenario: 展开过滤面板

- **GIVEN** 过滤面板默认折叠
- **WHEN** 用户点击「筛选」按钮
- **THEN** 展开过滤面板，显示数据库、Schema、实体类型、数据类型筛选条件
- **AND** 筛选条件选项从已有数据动态获取

#### Scenario: 组合筛选

- **GIVEN** 过滤面板已展开
- **WHEN** 用户选择 实体类型=table + 数据库=finance_db
- **THEN** 搜索结果仅显示满足所有条件的表
- **AND** 已选择的筛选条件显示为可移除的标签

#### Scenario: 清除单个筛选条件

- **GIVEN** 已选择 实体类型=table 和 数据库=finance_db
- **WHEN** 用户点击「数据库=finance_db」标签的关闭按钮
- **THEN** 数据库筛选条件被移除，搜索结果仅按实体类型=table 重新筛选

#### Scenario: 重置所有筛选

- **GIVEN** 已选择多个筛选条件
- **WHEN** 用户点击「重置」按钮
- **THEN** 所有筛选条件清空，恢复为无过滤状态

### Requirement: 搜索结果列表

以卡片列表形式展示搜索结果，每条结果显示核心元数据信息。

#### Scenario: 展示搜索结果

- **GIVEN** 搜索返回 20 条元数据实体
- **WHEN** 结果加载完成
- **THEN** 每条结果显示：entity_id、entity_type 图标、display_name、description（截断2行）、tags
- **AND** 搜索关键词在结果中高亮显示

#### Scenario: 空结果

- **GIVEN** 搜索关键词无匹配结果
- **WHEN** 结果返回空数组
- **THEN** 显示 「未找到匹配的元数据」空状态提示
- **AND** 提示用户尝试修改搜索条件

#### Scenario: 搜索结果分页

- **GIVEN** 搜索返回 100 条结果
- **WHEN** 结果列表底部渲染
- **THEN** 显示分页控件，默认每页 20 条
- **AND** 用户可切换页码查看不同页结果

#### Scenario: 搜索错误处理

- **GIVEN** 搜索 API 返回错误
- **WHEN** 搜索请求失败
- **THEN** 显示 「搜索失败，请稍后重试」错误提示
- **AND** 提供「重试」按钮

### Requirement: 智能补全触发

选中元数据实体后提供「智能补全」操作入口。

#### Scenario: 触发表的智能补全

- **GIVEN** 搜索结果中包含表 `t_user_order`
- **WHEN** 用户点击该表行或卡片上的「智能补全」按钮
- **THEN** 调用 POST /api/v1/complete/trigger/manual
- **AND** 显示补全进度 Loading 状态
- **AND** 补全完成后展示 CompletionPanel 显示结果

#### Scenario: 触发字段的智能补全

- **GIVEN** 用户在搜索结果中展开表查看其字段列表
- **WHEN** 用户选中字段 `status` 并点击「智能补全」
- **THEN** 触发字段级补全，展示补全结果

#### Scenario: 补全进行中不可重复触发

- **GIVEN** 某个实体的补全正在进行中
- **WHEN** 用户再次点击同一实体的「智能补全」
- **THEN** 按钮置灰不可点击
- **AND** 显示「补全进行中」提示

### Requirement: 页面路由

搜索页面作为系统首页，支持直接 URL 访问。

#### Scenario: 访问根路径

- **GIVEN** 用户访问 `/`
- **WHEN** 页面加载
- **THEN** 自动重定向到 `/search`

#### Scenario: 直接访问搜索页

- **GIVEN** 用户访问 `/search`
- **WHEN** 页面加载
- **THEN** 显示搜索页面，搜索栏获得焦点

## Non-Goals

- 自然语言语义搜索（后续版本）
- 搜索结果导出为文件
- 搜索历史记录
