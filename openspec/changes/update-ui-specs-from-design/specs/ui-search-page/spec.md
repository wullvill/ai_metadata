## MODIFIED Requirements

### Requirement: 搜索栏

搜索栏 SHALL 包含文本输入框、结果计数和结构化过滤面板。

#### Scenario: 关键词即时搜索

- **GIVEN** 用户在搜索框输入 "交易"
- **WHEN** 实时过滤（input 事件即时响应）
- **THEN** 仅显示名称/描述/标签/负责人/库名匹配的资产
- **AND** 结果计数更新

#### Scenario: 结构化过滤

- **GIVEN** 过滤栏包含系统下拉、库下拉、Schema下拉、类型 Chip、业务域 Chip
- **WHEN** 用户选择「交易系统」下拉
- **THEN** 列表过滤为对应系统的资产，下拉框高亮
- **WHEN** 用户点击类型 Chip「表」
- **THEN** 仅显示表类型，Chip 高亮蓝色

#### Scenario: 业务域溢出弹窗

- **GIVEN** 业务域 > 5 个
- **WHEN** 过滤栏渲染
- **THEN** 显示前 5 个 Chip +「展开」按钮
- **WHEN** 点击「展开」
- **THEN** 弹窗列出全部业务域 Chip 供选择

### Requirement: 操作栏

表格上方 SHALL 显示补全状态筛选和批量操作。

#### Scenario: 补全状态筛选

- **GIVEN** 操作栏左侧显示「共 N 条」
- **WHEN** 渲染状态 Chip (全部/待补全/处理中/已完成)
- **THEN** 切换筛选补全状态

#### Scenario: 批量选择与申请补全

- **GIVEN** 表头有全选复选框
- **WHEN** 勾选多行
- **THEN** 显示「已选 N 项」,「批量申请补全」可用
- **WHEN** 选中 0 项
- **THEN** 按钮禁用，已选文字隐藏
- **WHEN** 点击「批量申请补全」
- **THEN** 选中 pending 资产变为 processing, 选中清除

### Requirement: 资产列表表格

表格 SHALL 展示 12 列。

#### Scenario: 列定义

- **GIVEN** 列表渲染
- **WHEN** 查看表头
- **THEN** 列：checkbox(40px)/资产名称(可排)/描述/所属系统(可排)/类型(可排)/所属库(可排)/Schema(可排)/业务域(可排)/分类(可排)/补全状态(可排)/更新时间(可排)/操作

#### Scenario: 名称点击跳转详情

- **GIVEN** 用户点击资产名称(等宽蓝色链接)
- **WHEN** 触发
- **THEN** 新标签页打开 asset_detail.html?id=行ID

#### Scenario: 行操作

- **GIVEN** 每行操作列
- **WHEN** 渲染
- **THEN** 显示「详情」按钮 +「补全申请」主色按钮

### Requirement: 单行补全申请

#### Scenario: 确认对话框

- **GIVEN** 点击「补全申请」
- **WHEN** 弹窗
- **THEN** 显示「将为「资产名」申请补全…」+ 取消/确认按钮
- **WHEN** 确认
- **THEN** 资产状态变 processing, 弹窗关闭

### Requirement: 状态与标签颜色

#### Scenario: 补全状态

- **GIVEN** pending → 琥珀色「待补全」; processing → 蓝色「处理中」; completed → 绿色「已完成」

#### Scenario: 业务域颜色

- **GIVEN** 交易/客户 → 蓝; 风控/合规 → 琥珀; 清算/财务/行情 → 绿; 产品/公共 → 灰蓝

#### Scenario: 分类颜色

- **GIVEN** 机密 → 琥珀; 内部 → 蓝; 公开 → 绿

### Requirement: 列排序

#### Scenario: 切换排序

- **GIVEN** 可排序列 (data-sort)
- **WHEN** 首次点击 → 升序 ↑; 再次点击 → 降序 ↓; 点击其他列 → 新列升序
