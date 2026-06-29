## Context

前端已有基于 Vue 3 + TDesign 的原型代码（4 页面 / 6 组件 / 3 composable），但缺少 OpenSpec 格式的 UI 需求规范。本设计将 UI 需求按页面和共享组件维度拆分为 4 个 spec，与后端 7 个 spec 对应关联。

现有路由：`/search` → SearchPage, `/review` → ReviewPage, `/history` → HistoryPage, `/config` → ConfigPage。

## Goals / Non-Goals

**Goals:**
- 将 UI 需求形式化为可验证的 OpenSpec spec（GIVEN/WHEN/THEN 场景）
- 覆盖关键交互流程：搜索→触发→审核→追溯
- 定义共享组件的通用行为和状态
- 与后端 spec 建立清晰的对齐关系

**Non-Goals:**
- 重新设计前端架构（沿用现有 Vue 3 + TDesign + Pinia + Vue Router 体系）
- 定义视觉风格/设计令牌（已有 tokens.css）
- 覆盖 ConfigPage（后续版本功能）
- 性能优化细节（已有性能指标在需求文档中）

## Decisions

| 决策 | 选择 | 理由 |
|------|------|------|
| 按页面拆分 UI spec | 4 个独立 spec | 与后端按能力域拆分的思路一致，每个页面聚焦独立的用户任务 |
| 共享组件独立 spec | ui-shared-components | 跨页面复用的组件需要统一的行为契约 |
| 不重复后端 spec 数据 | UI spec 引用后端 spec | 避免数据模型重复定义，保持单一真源 |
| GIVEN/WHEN/THEN 场景 | Playwright 可测试 | 每个 UI 场景可直接转化为 E2E 测试用例 |
| 不覆盖 ConfigPage | 明确排除 | 规则配置化属后续版本，避免范围蔓延 |

## Risks / Trade-offs

- **UI spec 与现有原型不一致** → 以 spec 为准，原型代码作为参考，后续通过 `/opsx:apply` 对齐
- **后端 API 接口调整** → UI spec 引用 API 端点而非内部实现，接口稳定性由后端 spec 保障
- **TDesign 组件版本升级** → spec 描述行为而非具体组件，降低耦合
