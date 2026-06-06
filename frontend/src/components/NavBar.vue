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
