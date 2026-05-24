## MODIFIED Requirements

### Requirement: 导航入口

「补全溯源」SHALL 在导航中占位，页面内容尚未实现。

#### Scenario: 导航显示

- **GIVEN** 用户在任意页面
- **WHEN** 查看顶部导航栏
- **THEN** 显示 4 导航项：资产目录 / 审核工作台 / 补全溯源 / 参数配置
- **AND** 「补全溯源」为占位链接 (href="#")

## ADDED Requirements

_后续版本将基于 completion-history spec 实现完整历史追溯页面。_
