<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getCompletionHistory } from '../api'
import type { ReviewRecord, HistoryParams } from '../api/types'
import QualityBadge from '../components/QualityBadge.vue'
import { MessagePlugin } from 'tdesign-vue-next'

const records = ref<ReviewRecord[]>([])
const total = ref(0)
const loading = ref(false)

const filters = ref<HistoryParams>({
  status: undefined,
  entity_id: '',
  start_date: undefined,
  end_date: undefined,
  page: 1,
  limit: 20,
})

const searchQuery = ref('')
const debounceTimer = ref<ReturnType<typeof setTimeout> | null>(null)

onMounted(() => loadHistory())

async function loadHistory(resetPage = true) {
  if (resetPage && filters.value.page) filters.value.page = 1
  loading.value = true
  try {
    const data = await getCompletionHistory(filters.value)
    records.value = data.data || []
    total.value = data.meta?.total || 0
  } catch (e) {
    MessagePlugin.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

function handleSearchChange() {
  if (debounceTimer.value) clearTimeout(debounceTimer.value)
  debounceTimer.value = setTimeout(() => {
    filters.value.entity_id = searchQuery.value
    loadHistory()
  }, 300)
}

const statusOptions = [
  { label: '全部', value: '' },
  { label: '自动采纳', value: 'auto_approved' },
  { label: '已确认', value: 'approved' },
  { label: '已修改', value: 'modified' },
  { label: '已拒绝', value: 'rejected' },
  { label: '人工驳回', value: 'human_rejected' },
]

const filteredRecords = computed(() => records.value)

const filteredTotal = computed(() => filteredRecords.value.length)

function setStatusFilter(value: string) {
  filters.value.status = value || undefined
  loadHistory()
}

function handleRefresh() {
  searchQuery.value = ''
  filters.value.entity_id = ''
  loadHistory()
}

function clearDates() {
  filters.value.start_date = undefined
  filters.value.end_date = undefined
  loadHistory()
}

const columns = [
  { colKey: 'entity_id', title: '实体', ellipsis: true, width: 220 },
  { colKey: 'entity_type', title: '类型', width: 72 },
  { colKey: 'display_name', title: '补全中文名', ellipsis: true, width: 180 },
  { colKey: 'status', title: '状态', width: 120 },
  { colKey: 'created_at', title: '提交时间', width: 160 },
]

function handlePageChange(pageInfo: { current: number }) {
  filters.value.page = pageInfo.current
  loadHistory(false)
}
</script>

<template>
  <div class="history-page">
    <!-- Page Header -->
    <div class="page-header">
      <h1>补全历史</h1>
      <p class="page-subtitle">查看所有智能补全记录及审核追溯</p>
    </div>

    <!-- Search Section -->
    <section class="search-section">
      <div class="search-bar">
        <div class="search-bar-row">
          <t-icon name="search" size="18px" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="搜索实体 ID、中文名、描述..."
            autocomplete="off"
            @input="handleSearchChange"
          />
          <span v-if="filteredTotal > 0" class="result-count">{{ filteredTotal }} 条</span>
        </div>
        <div class="filter-bar">
          <div class="filter-select-wrap">
            <select
              v-model="filters.status"
              class="filter-select"
              :class="{ active: filters.status !== '' && filters.status !== undefined }"
              @change="setStatusFilter(($event.target as HTMLSelectElement).value)"
            >
              <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <span class="filter-sep" />
          <div class="filter-select-wrap">
            <input
              type="date"
              class="filter-select filter-date"
              :value="filters.start_date || ''"
              @change="filters.start_date = ($event.target as HTMLInputElement).value || undefined; loadHistory()"
            />
          </div>
          <span class="filter-sep" />
          <div class="filter-select-wrap">
            <input
              type="date"
              class="filter-select filter-date"
              :value="filters.end_date || ''"
              @change="filters.end_date = ($event.target as HTMLInputElement).value || undefined; loadHistory()"
            />
          </div>
          <button
            v-if="filters.start_date || filters.end_date"
            class="filter-chip"
            @click="clearDates"
          >
            清除日期
          </button>
        </div>
      </div>
    </section>

    <!-- Ops Bar -->
    <section class="ops-section">
      <div class="ops-bar">
        <div class="ops-bar-left">
          <span class="ops-count">共 {{ filteredTotal }} 条</span>
          <span class="filter-sep" />
          <button class="filter-chip" @click="handleRefresh()">
            <t-icon name="refresh" size="14px" style="margin-right: 2px" />
            刷新
          </button>
        </div>
      </div>
    </section>

    <!-- Table -->
    <div class="history-table">
      <t-table
        :data="filteredRecords"
        :columns="columns"
        :loading="loading"
        row-key="id"
        hover
        stripe
      >
        <template #entity_id="{ row }">
          <div style="display: flex; align-items: center; gap: 8px">
            <t-tag
              :theme="row.entity_type === 'table' ? 'primary' : 'default'"
              variant="light"
              size="small"
            >
              {{ row.entity_type === 'table' ? '表' : '字段' }}
            </t-tag>
            <span class="cell-mono">{{ row.entity_id }}</span>
          </div>
        </template>

        <template #entity_type="{ row }">
          {{ row.entity_type === 'table' ? '表' : '字段' }}
        </template>

        <template #display_name="{ row }">
          <span class="cell-name">
            {{ row.completion_result?.display_name || '-' }}
          </span>
        </template>

        <template #status="{ row }">
          <QualityBadge
            :status="row.review_status"
            :confidence="row.quality_check?.adjusted_confidence ?? row.completion_result?.confidence"
          />
        </template>

        <template #created_at="{ row }">
          {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
        </template>

        <template #expandedRow="{ row }">
          <div v-if="row.completion_result" class="expanded-detail">
            <p><strong>中文名:</strong> {{ row.completion_result.display_name }}</p>
            <p><strong>描述:</strong> {{ row.completion_result.description }}</p>
            <p><strong>标签:</strong> {{ row.completion_result.tags?.join(' / ') || '-' }}</p>
            <p>
              <strong>置信度:</strong>
              {{ ((row.quality_check?.adjusted_confidence ?? row.completion_result.confidence) * 100).toFixed(0) }}%
            </p>
          </div>
          <div v-else class="expanded-detail">
            <p>暂无补全结果</p>
          </div>
        </template>
      </t-table>
    </div>

    <!-- Pagination -->
    <div v-if="total > (filters.limit ?? 20)" class="pagination-wrap">
      <t-pagination
        :current="filters.page"
        :total="total"
        :page-size="filters.limit ?? 20"
        show-jumper
        @change="handlePageChange"
      />
    </div>
  </div>
</template>

<style scoped>
/* ── Design tokens（与 SearchPage 一致）── */
.history-page {
  --color-bg: oklch(99% 0.002 240);
  --color-surface: oklch(100% 0 0);
  --color-fg: oklch(18% 0.012 250);
  --color-muted: oklch(54% 0.012 250);
  --color-border: oklch(92% 0.005 250);
  --color-accent: oklch(58% 0.18 255);
  --color-accent-soft: oklch(58% 0.18 255 / 0.08);
  --font-mono: 'JetBrains Mono', 'SF Mono', ui-monospace, Menlo, monospace;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;

  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif;
  color: var(--color-fg);
}

/* ── Page header ── */
.page-header {
  margin-bottom: 28px;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-fg);
  letter-spacing: -0.01em;
  margin: 0;
}

.page-subtitle {
  font-size: 0.875rem;
  color: var(--color-muted);
  margin-top: 4px;
}

/* ── Search bar ── */
.search-section {
  margin-bottom: 12px;
}

.search-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 8px 10px;
}

.search-bar:focus-within {
  border-color: var(--color-accent);
}

.search-bar-row {
  display: flex;
  gap: 10px;
  align-items: center;
  width: 100%;
}

.search-icon {
  color: var(--color-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 15px;
  font-family: inherit;
  color: var(--color-fg);
  min-width: 0;
}

.search-input::placeholder {
  color: var(--color-muted);
}

.result-count {
  font-size: 13px;
  color: var(--color-muted);
  padding-left: 8px;
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* ── Filter bar ── */
.filter-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
  overflow-x: auto;
  padding-top: 2px;
}

.filter-group {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.filter-sep {
  width: 1px;
  background: var(--color-border);
  margin: 0 4px;
  align-self: stretch;
}

.filter-chip {
  padding: 5px 12px;
  border-radius: 20px;
  border: 1px solid var(--color-border);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  background: transparent;
  color: var(--color-muted);
  font-family: inherit;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
}

.filter-chip:hover {
  border-color: var(--color-accent);
  color: var(--color-fg);
}

.filter-chip.active {
  background: var(--color-accent);
  color: #fff;
  border-color: var(--color-accent);
}

/* ── Filter selects ── */
.filter-select-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.filter-select {
  appearance: none;
  padding: 5px 28px 5px 10px;
  border-radius: 20px;
  border: 1px solid var(--color-border);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  color: var(--color-muted);
  font-family: inherit;
  transition: all 0.15s;
  min-width: 0;
}

.filter-select:hover {
  border-color: var(--color-accent);
  color: var(--color-fg);
}

.filter-select.active {
  background: var(--color-accent-soft);
  color: var(--color-accent);
  border-color: var(--color-accent);
}

.filter-select-wrap::after {
  content: '';
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid currentColor;
}

.filter-select-wrap:has(.filter-date)::after {
  display: none;
}

.filter-date {
  padding-right: 10px;
}

.filter-date::-webkit-calendar-picker-indicator {
  cursor: pointer;
  opacity: 0.5;
}

/* ── Ops bar ── */
.ops-section {
  margin-bottom: 16px;
}

.ops-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  flex-wrap: wrap;
  gap: 10px;
}

.ops-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ops-count {
  font-size: 13px;
  color: var(--color-fg);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

/* ── Table section ── */
.history-table {
  margin-bottom: 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* ── Cell styles ── */
.cell-name {
  font-weight: 500;
  font-size: 0.875rem;
}

.cell-mono {
  font-family: var(--font-mono);
  font-size: 0.875rem;
}

/* ── Expanded row ── */
.expanded-detail {
  padding: 16px 24px;
  background: var(--color-bg);
}

.expanded-detail p {
  font-size: 0.875rem;
  line-height: 2;
  margin: 0;
  color: var(--color-fg);
}

.expanded-detail strong {
  color: var(--color-muted);
  margin-right: 4px;
}

/* ── Pagination ── */
.pagination-wrap {
  display: flex;
  justify-content: center;
}

/* ── Table overrides for TDesign ── */
:deep(.t-table) {
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

:deep(.t-table th) {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  white-space: nowrap;
  user-select: none;
}

:deep(.t-table td) {
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

:deep(.t-table tr:hover td) {
  background: var(--color-bg);
}

:deep(.t-table__empty) {
  padding: 0;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .history-page {
    padding: 16px;
  }

  .search-input {
    min-width: 120px;
  }

  .filter-bar {
    flex-wrap: wrap;
    gap: 6px;
  }

  .filter-sep {
    display: none;
  }

  .result-count {
    display: none;
  }

  .ops-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .ops-bar-left {
    flex-wrap: wrap;
  }
}
</style>
