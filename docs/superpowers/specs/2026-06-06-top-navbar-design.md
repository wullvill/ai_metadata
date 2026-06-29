# Top Navigation Bar — Design

**Date:** 2026-06-06
**Status:** approved

## Goal

在搜索、审核工作台、补全溯源、参数配置 4 个主页面顶部添加功能导航栏，参照 `design-ui/meta_search.html` 的 nav 设计。详情页不显示导航。

## Routes

| route.name | 标签 | 路径 | 导航可见 |
|------------|------|------|----------|
| search | 资产目录 | `/search` | 是 |
| review | 审核工作台 | `/review` | 是 |
| history | 补全溯源 | `/history` | 是 |
| config | 参数配置 | `/config` | 是 |
| asset-detail | — | `/asset/:id` | 否 |
| review-detail | — | `/review/:id` | 否 |

## Architecture

```
App.vue
  ├── NavBar (v-if="showNav")     ← 新建
  └── router-view
```

`showNav` 通过 `computed` 判断 `route.name` 是否为 4 个主页之一。

## NavBar Component

**File:** `frontend/src/components/NavBar.vue`

- **Logo**: MetaGraph SVG 图标 + 品牌名，点击跳转 `/search`
- **4 个链接**: 使用 `router-link`，根据 `route.name` 添加 `.active` 类
- **样式**: sticky top, height 56px, 半透明背景 blur 16px, 底部 1px border

**Nav items:**
| 标签 | 路由 | 匹配 route.name |
|------|------|-----------------|
| 资产目录 | `/search` | search |
| 审核工作台 | `/review` | review |
| 补全溯源 | `/history` | history |
| 参数配置 | `/config` | config |

## Files Changed

| File | Action |
|------|--------|
| `frontend/src/components/NavBar.vue` | Create |
| `frontend/src/App.vue` | Modify — import NavBar, add conditional render |

Existing pages (SearchPage, ReviewPage, HistoryPage, ConfigPage) unchanged.
