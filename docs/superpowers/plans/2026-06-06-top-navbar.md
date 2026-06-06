# Top Navigation Bar — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared top navigation bar (sticky, blurred) with 4 links to the main pages.

**Architecture:** Single shared NavBar component rendered conditionally in App.vue. Shows on 4 main routes (search/review/history/config), hidden on detail routes. Zero changes to existing page components.

**Tech Stack:** Vue 3 + Vue Router + TDesign

---

### Task 1: Create NavBar.vue component

**Files:**
- Create: `frontend/src/components/NavBar.vue`

- [ ] **Step 1: Create the component**

```vue
<template>
  <nav class="top-nav">
    <div class="nav-inner">
      <router-link class="nav-logo" to="/search">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <rect x="3" y="3" width="7" height="7" rx="1"/>
          <rect x="14" y="3" width="7" height="7" rx="1"/>
          <rect x="3" y="14" width="7" height="7" rx="1"/>
          <rect x="14" y="11" width="7" height="10" rx="1"/>
        </svg>
        MetaGraph
      </router-link>
      <div class="nav-links">
        <router-link
          v-for="item in navItems"
          :key="item.match"
          :to="item.to"
          class="nav-link"
          :class="{ active: route.name === item.match }"
        >
          {{ item.label }}
        </router-link>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { label: '资产目录', to: '/search', match: 'search' },
  { label: '审核工作台', to: '/review', match: 'review' },
  { label: '补全溯源', to: '/history', match: 'history' },
  { label: '参数配置', to: '/config', match: 'config' },
]
</script>

<style scoped>
.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: oklch(99% 0.002 240 / 0.82);
  backdrop-filter: blur(16px) saturate(180%);
  border-bottom: 1px solid var(--td-border-level-2-color, #e7e7e7);
  height: 56px;
  display: flex;
  align-items: center;
}
.nav-inner {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 24px;
}
.nav-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 17px;
  letter-spacing: -0.01em;
  color: var(--td-text-color-primary);
  text-decoration: none;
}
.nav-logo svg {
  color: var(--td-brand-color);
}
.nav-links {
  display: flex;
  gap: 4px;
  margin-left: auto;
}
.nav-link {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--td-text-color-placeholder);
  text-decoration: none;
  transition: all 0.15s;
}
.nav-link:hover {
  color: var(--td-text-color-primary);
  background: var(--td-bg-color-container-hover, #f3f3f3);
}
.nav-link.active {
  color: var(--td-text-color-primary);
  background: var(--td-bg-color-container-active, #e7e7e7);
}
</style>
```

- [ ] **Step 2: Verify type check**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | grep -i "NavBar" | head -5
```

Expected: no NavBar-related errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/NavBar.vue
git commit -m "feat: add top navigation bar component"
```

---

### Task 2: Integrate NavBar into App.vue

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Update App.vue**

Replace entire file content:

```vue
<template>
  <NavBar v-if="showNav" />
  <router-view />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NavBar from './components/NavBar.vue'

const route = useRoute()

const showNav = computed(() => {
  const name = route.name as string
  return ['search', 'review', 'history', 'config'].includes(name)
})
</script>
```

- [ ] **Step 2: Verify type check**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | grep -i error | head -10
```

Expected: no new errors

- [ ] **Step 3: Manual verification**

Browse to verify:
- `http://localhost:5173/search` — nav visible, "资产目录" active
- `http://localhost:5173/review` — nav visible, "审核工作台" active
- `http://localhost:5173/asset/fact_trade` — nav NOT visible

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat: integrate NavBar into App.vue with conditional display"
```
