## ADDED Requirements

### Requirement: 资产详情页布局

页面 SHALL 采用上下分区：顶部固定区 (breadcrumb+名称+描述+徽章) + 底部 Tab 区 (基本信息+列信息)。

#### Scenario: 页头信息展示

- **GIVEN** 通过 URL 参数 `?id=fact_trade` 访问
- **WHEN** 页面加载
- **THEN** 顶部区显示面包屑「资产目录 / fact_trade」
- **AND** 资产名称用等宽字体 22px 加粗展示
- **AND** 副标题显示「表 · ods_trade.public」
- **AND** 描述限 2 行，超出省略
- **AND** 徽章行显示类型/系统/业务域/分类/补全状态

### Requirement: 基本信息 Tab

展示资产的完整元数据键值对列表。

#### Scenario: 查看全部基本信息字段

- **GIVEN** 资产详情页加载，当前为「基本信息」Tab
- **WHEN** 用户查看详情列表
- **THEN** 展示 14 个字段：名称、类型、描述、所属系统、所属库、Schema、业务域、分类、负责人、血缘、补全状态、标签、更新时间

#### Scenario: 标签行展示

- **GIVEN** 资产 tags="交易,核心,分区表"
- **WHEN** 基本信息 Tab 渲染
- **THEN** 标签行显示 3 个灰色标签 badge

### Requirement: 列信息 Tab

以表格展示资产的列信息，区分原始与补全字段。

#### Scenario: 表有列信息

- **GIVEN** fact_trade 有 12 列
- **WHEN** 切换到「列信息」Tab
- **THEN** 表格标题「列信息 (12 列)」
- **AND** 列：列名(等宽加粗)、类型、原始描述、原始分类标签、补全描述、补全分类标签、补全时间

#### Scenario: 字段无列信息

- **GIVEN** 实体类型为「字段」
- **WHEN** 列信息 Tab 渲染
- **THEN** 显示空状态「该资产类型为「字段」，无列信息可展示」

#### Scenario: 补全字段为空

- **GIVEN** 某列 compDesc 和 compTag 均为空
- **WHEN** 列表格渲染
- **THEN** 对应列显示斜体灰色「待补全」

### Requirement: 错误状态

#### Scenario: 缺少资产标识

- **GIVEN** URL 无 id 参数
- **WHEN** 页面加载
- **THEN** 显示错误图标 +「缺少资产标识」+ 返回资产目录链接

#### Scenario: 未找到该资产

- **GIVEN** URL `?id=nonexistent`
- **WHEN** 页面加载
- **THEN** 显示错误图标 +「未找到该资产」+ 返回资产目录链接
