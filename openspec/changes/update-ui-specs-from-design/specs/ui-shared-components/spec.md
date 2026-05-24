## MODIFIED Requirements

### Requirement: 标签颜色系统

标签 SHALL 使用 5 种语义颜色。

#### Scenario: 颜色映射

- **GIVEN** blue → 交易/客户/产品域 + processing状态 + 内部分类
- **AND** green → 清算/财务/行情域 + completed/approved状态 + 公开分类
- **AND** amber → 风控/合规域 + pending_review状态 + 机密分类
- **AND** red → rejected状态
- **AND** slate → 公共域 + 类型标签

### Requirement: 置信度进度条

审核列表 SHALL 使用进度条+百分比双显示。

#### Scenario: 阈值颜色

- **GIVEN** >= 0.8 → 绿色; >= 0.6 → 琥珀色; < 0.6 → 红色
- **THEN** 宽度 = conf × 100%，右侧等宽字体百分比

### Requirement: 加载骨架屏

#### Scenario: 骨架屏动画

- **GIVEN** 加载中 → 3行骨架行(8列灰色条块)，shimmer 闪烁 1.5s
- **THEN** 完成后替换为实际内容

### Requirement: 错误状态

#### Scenario: 错误+重试

- **GIVEN** 加载失败 → 错误图标+消息+重试按钮
- **WHEN** 重试 → 重新请求

### Requirement: 空状态

#### Scenario: 上下文文字

- **GIVEN** 无匹配 →「没有匹配的元数据资产」
- **AND** 待审空 →「暂无待审核记录」
- **AND** 已确认空 →「暂无已确认记录」
- **AND** 已驳回空 →「暂无已驳回记录」

### Requirement: Toast 通知

#### Scenario: Toast 显示

- **GIVEN** 成功 → 绿色 Toast; 失败 → 红色 Toast
- **THEN** 右上角固定，滑入动画 0.3s，3s 后消失，垂直堆叠间距 8px

### Requirement: 确认/驳回对话框

#### Scenario: 对话框交互

- **GIVEN** 触发 → 半透明模糊遮罩 + 白色卡片(标题+描述+取消/确认按钮)
- **WHEN** Esc/点击遮罩 → 关闭
- **WHEN** 驳回 → 附加 textarea 必填原因 + 空值校验红字

### Requirement: 进度覆盖层

#### Scenario: 批量进度

- **GIVEN** 批量操作 → 遮罩+居中卡片(标题+进度条+计数)
- **THEN** 200ms/条更新，完成 400ms 后关闭 + Toast
