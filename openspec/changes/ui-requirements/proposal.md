## Why

7 个后端能力域 OpenSpec 规范已就绪（metadata-search, intelligent-completion, dual-path-retrieval, quality-validation, human-review, om-sync, completion-history），但缺少对应的 UI 层需求规范。前端虽已有原型代码，需要将 UI 需求以 OpenSpec 格式形式化，与后端 specs 形成完整的端到端可追溯链。

## What Changes

- 新增 4 个 UI 能力域 spec，覆盖全部用户可以直接交互的页面和组件
- 每个 UI spec 与对应后端 spec 关联，定义页面布局、组件行为、交互流程和响应式要求
- 不修改现有 7 个后端 spec

## Capabilities

### New Capabilities

- `ui-search-page`: 元数据搜索页面 — 搜索栏、结构化过滤面板、搜索结果列表、元数据卡片、智能补全触发入口
- `ui-review-workbench`: 审核工作台页面 — 审核队列表格、筛选栏、批量操作工具栏、审核详情弹窗（确认/修改/拒绝）
- `ui-history-page`: 补全历史页面 — 历史记录查询表格、多维度筛选、状态轨迹展示
- `ui-shared-components`: 跨页面共享组件 — QualityBadge 置信度徽章、CompletionPanel 补全建议面板、Loading/Error/Empty 状态

### Modified Capabilities

_无现有 spec 的需求变更，仅新增 UI 层 spec。_

## Impact

- 新增文件: `openspec/specs/ui-search-page/`, `openspec/specs/ui-review-workbench/`, `openspec/specs/ui-history-page/`, `openspec/specs/ui-shared-components/`
- 参考现有前端代码: `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/composables/`
- 不影响后端 API 或 Pipeline
