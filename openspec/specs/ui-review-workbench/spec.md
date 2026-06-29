## MODIFIED Requirements

### Requirement: 审核队列筛选

筛选栏 SHALL 支持下拉、Chip、置信度滑块、关键词搜索。

#### Scenario: 多维筛选

- **GIVEN** 过滤栏含状态下拉(默认待审核)+ 系统/库/Schema下拉 + 类型Chip + 置信度滑块(0-100%)+ 搜索框
- **WHEN** 切换状态为「已确认」→ 仅显示已确认记录，滑块重置 0
- **WHEN** 拖动滑块到 80 → 仅显示 confidence >= 0.80
- **WHEN** 搜索 "交易" → 匹配实体名/建议中文名/描述/标签/系统/库名

### Requirement: 审核队列表格

#### Scenario: 9 列表格定义

- **GIVEN** 队列渲染
- **THEN** 列：checkbox/资产名称(可排)/类型/所属库/Schema/所属系统/置信度(进度条+百分比 可排)/审核状态/提交时间(可排)

#### Scenario: 置信度进度条

- **GIVEN** conf >= 0.8 → 绿条; >= 0.6 → 琥珀条; < 0.6 → 红条
- **THEN** 宽度 = conf×100%，右侧显示百分比

#### Scenario: 状态标签

- **GIVEN** pending_review → 琥珀「待审核」; approved → 绿「已确认」; rejected → 红「已驳回」

#### Scenario: 行点击导航

- **GIVEN** 点击行 → 跳转 review_detail.html?id=
- **AND** 非 pending_review 行 checkbox 禁用

### Requirement: 批量操作

#### Scenario: 全选/批量确认/批量驳回

- **GIVEN** 全选仅勾选 pending_review 行
- **WHEN** 批量确认 → 弹窗确认 → 进度覆盖层动画逐条更新 → Toast
- **WHEN** 批量驳回 → 弹窗填写必填原因 → 进度动画 → Toast

### Requirement: 5 Tab 详情

#### Scenario: Tab 结构

- **GIVEN** 详情弹窗/页面打开
- **THEN** 5 Tab：基本信息 | 补全对比 | 列信息 | 质量校验 | 检索参考

### Requirement: 补全对比 Tab

#### Scenario: 左右对比 + 可编辑

- **GIVEN** 切换到对比 Tab
- **THEN** 左卡「原始元数据」+ 右卡「AI 建议」(可编辑：中文名input/描述textarea/标签input)
- **AND** pending 可编辑，非 pending 禁用
- **WHEN** 修改内容 → 「确认修改」可用 → 点击保存 → Toast

### Requirement: 列信息编辑 Tab

#### Scenario: 编辑列补全

- **GIVEN** 列信息 Tab
- **THEN** 表格：列名/类型/原始描述/原始标签/补全描述(input)/补全标签(input)/补全时间
- **AND** 编辑字段 dirty 显示琥珀边框，「保存列信息」按钮
- **WHEN** 修改 + 保存 → 更新数据 + 时间 + Toast

### Requirement: 质量校验 Tab

#### Scenario: 规则列表

- **GIVEN** quality.rules 有数据 → 状态圆点(pass绿/warn琥珀/fail红) + 规则名 + 详情 + 汇总
- **GIVEN** 空 → 「暂无质量校验结果」

### Requirement: 检索参考 Tab

#### Scenario: 相似元数据

- **GIVEN** 有 references → 参考名(等宽) + 中文名 + 相似度%(≥85%绿/≥70%琥珀/<70%灰)
- **GIVEN** 空 → 「无相似元数据参考」

### Requirement: 操作按钮

#### Scenario: 确认/修改/驳回

- **GIVEN** pending → 显示驳回/确认修改(初始禁用)/确认采纳
- **GIVEN** 非 pending → 显示「该记录已确认/驳回，不可操作」

### Requirement: 状态管理

#### Scenario: 加载/错误/空

- **WHEN** 加载中 → 3行骨架屏(闪烁)
- **WHEN** 失败 → 「加载失败」+ 重试按钮
- **WHEN** 空 → 文字随状态筛选变化

### Requirement: Toast 通知

#### Scenario: 操作反馈

- **GIVEN** 操作成功 → 绿色 Toast 3秒消失; 失败 → 红色 Toast
