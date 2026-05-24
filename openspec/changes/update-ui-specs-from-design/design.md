## Context

design-ui/ 目录有 4 个产品级 HTML 页面，使用纯 HTML/CSS/JS 实现完整交互。这些是 UI 的真实设计稿，需要以此为准更新 OpenSpec UI 规范。

## Goals / Non-Goals

**Goals:**
- 将 4 页面的完整 UI 行为描述写入 OpenSpec spec
- 补充缺失的 asset_detail 页面 spec
- 更新共享组件 spec 中的标签颜色、置信度进度条、骨架屏、Toast 等

**Non-Goals:**
- 修改已有的 7 个后端 spec
- 涉及「补全溯源」「参数配置」页面（当前为占位）
- 视觉风格/设计令牌文档化

## Decisions

| 决策 | 选择 | 理由 |
|------|------|------|
| spec 按页面拆分 | 5 个 spec | 原 4 个 + 新增 asset_detail |
| review_detail 合并到 review spec | 不独立 | review_detail 是 review 的详情子页面，复刻弹窗的 5 Tab |
| ui-history-page 标记占位 | 保留 spec 标注待实现 | 导航已有入口 |
