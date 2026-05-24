## Why

design-ui 目录下的 4 个页面 (meta_search, asset_detail, review, review_detail) 是产品级 UI 设计定稿，包含完整的页面布局、交互逻辑、数据模型和视觉规范。现有 `openspec/specs/` 中的 UI spec 是基于原型代码编写的，与实际设计存在偏差。需要以设计稿为准，更新 UI 需求文档，确保 spec 与交付物一致。

## What Changes

- 修改 4 个现有 UI spec，反映设计稿中的实际页面逻辑
- 新增 `ui-asset-detail` spec：资产详情页 (asset_detail.html)
- 产品名称统一为 "MetaGraph — 数仓元数据管理平台"
- 更新页面导航结构：资产目录 / 审核工作台 / 补全溯源 / 参数配置

## Capabilities

### New Capabilities

- `ui-asset-detail`: 资产详情页面 — 基本信息 Tab + 列信息 Tab，面包屑导航，URL 参数跳转，错误状态（缺少标识/未找到）

### Modified Capabilities

- `ui-search-page`: 更新为 meta_search.html 设计 — 搜索栏+结构化过滤面板(系统/库/Schema下拉+类型/业务域Chip+展开弹窗)+操作栏(补全状态筛选+批量申请补全)+12列表格+单行补全申请+详情跳转
- `ui-review-workbench`: 更新为 review.html 设计 — 关键词搜索+状态/系统/库/Schema+类型+置信度滑块过滤+操作栏(选中计数+批量确认+批量驳回)+9列表格(含置信度进度条)+5 Tab详情弹窗(基本信息/补全对比/列信息编辑/质量校验/检索参考)+确认/修改/驳回操作+批量进度动画+Loading骨架屏+Error重试+Toast通知
- `ui-history-page`: 标记为占位状态 — 导航存在「补全溯源」入口但页面尚未实现
- `ui-shared-components`: 更新标签颜色系统(blue/green/amber/red/slate)+置信度进度条组件+骨架屏(闪烁动画)+错误状态(重试按钮)+Toast通知+确认/驳回对话框+进度覆盖层

## Impact

- 修改: `openspec/specs/ui-search-page/spec.md`, `openspec/specs/ui-review-workbench/spec.md`, `openspec/specs/ui-history-page/spec.md`, `openspec/specs/ui-shared-components/spec.md`
- 新增: `openspec/specs/ui-asset-detail/spec.md`
- 参考设计稿: `design-ui/` 下 4 个 HTML 文件
