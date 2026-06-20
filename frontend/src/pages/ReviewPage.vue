<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useReview, useReviewDetail } from '../composables/useReview'
import ReviewQueue from '../components/ReviewQueue.vue'
import ReviewDetail from '../components/ReviewDetail.vue'
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next'
import type { ReviewRecord } from '../api/types'

const {
  records,
  total,
  loading,
  filters,
  loadQueue,
  approve,
  reject,
  batchHandle,
} = useReview()

const {
  detail,
  loading: detailLoading,
  loadDetail,
} = useReviewDetail()

const selectedIds = ref<string[]>([])
const detailVisible = ref(false)
const currentRecordId = ref<string | null>(null)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const confidenceMin = ref(0)
const debounceTimer = ref<ReturnType<typeof setTimeout> | null>(null)

onMounted(() => loadQueue())

const statusFilterOptions = [
  { label: '全部', value: '' },
  { label: '待审核', value: 'pending_review' },
  { label: '自动采纳', value: 'auto_approved' },
  { label: '已确认', value: 'approved' },
  { label: '已修改', value: 'modified' },
  { label: '已拒绝', value: 'rejected' },
  { label: '人工驳回', value: 'human_rejected' },
]

const typeChips = [
  { label: '全部类型', value: '' },
  { label: '表', value: 'table' },
  { label: '视图', value: 'view' },
  { label: '字段', value: 'column' },
]

// Client-side post-filters (search, confidence, default column exclusion)
const filteredRecords = computed(() => {
  let list = records.value

  // Default: exclude column (字段) records unless explicitly filtering for them
  if (filters.entity_type !== 'column') {
    list = list.filter(r => r.entity_type !== 'column')
  }

  // Search filter: entity_id, display_name, description, tags
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    list = list.filter(r =>
      r.entity_id.toLowerCase().includes(q) ||
      (r.completion_result?.display_name || '').toLowerCase().includes(q) ||
      (r.completion_result?.description || '').toLowerCase().includes(q) ||
      (r.completion_result?.tags || []).join(' ').toLowerCase().includes(q)
    )
  }

  // Confidence filter
  if (confidenceMin.value > 0) {
    list = list.filter(r => (r.completion_result?.confidence || 0) * 100 >= confidenceMin.value)
  }

  return list
})

// Filter setters
function setTypeFilter(value: string) {
  filters.entity_type = value
  handleRefresh()
}

function setStatusFilter(value: string) {
  filters.status = value
  handleRefresh()
}

function handleRefresh() {
  currentPage.value = 1
  loadQueue(currentPage.value, pageSize.value)
}

function handleSearchChange() {
  // Debounced client-side filtering only (no API call)
  if (debounceTimer.value) clearTimeout(debounceTimer.value)
  debounceTimer.value = setTimeout(() => {
    // Client-side filter triggered by computed reactivity
  }, 200)
}

async function handleViewDetail(record: ReviewRecord) {
  currentRecordId.value = record.id
  await loadDetail(record.id)
  detailVisible.value = true
}

function handleDetailRefresh() {
  detailVisible.value = false
  handleRefresh()
}

function handleApprove(id: string) {
  const dialog = DialogPlugin.confirm({
    header: '确认采纳',
    body: '确定采纳此 AI 补全建议？系统将自动回写 OpenMetadata。',
    onConfirm: async () => {
      dialog.hide()
      try {
        await approve(id)
        MessagePlugin.success('已确认采纳')
      } catch {
        MessagePlugin.error('操作失败')
      }
    },
  })
}

function handleReject(id: string) {
  const dialog = DialogPlugin.confirm({
    header: '确认拒绝',
    body: '确定拒绝此补全建议？此操作将仅记录日志，不会回写 OpenMetadata。',
    onConfirm: async () => {
      dialog.hide()
      try {
        await reject(id, '人工拒绝')
        MessagePlugin.success('已拒绝')
      } catch {
        MessagePlugin.error('操作失败')
      }
    },
  })
}

async function handleBatchApprove() {
  if (selectedIds.value.length === 0) {
    MessagePlugin.warning('请先勾选要操作的记录')
    return
  }
  try {
    await DialogPlugin.confirm({
      header: '批量确认',
      body: `确定批量采纳选中的 ${selectedIds.value.length} 条记录？`,
    })
    await batchHandle(selectedIds.value)
    selectedIds.value = []
    MessagePlugin.success('批量操作完成')
  } catch {
    MessagePlugin.error('批量操作失败')
  }
}

async function handleBatchReject() {
  if (selectedIds.value.length === 0) {
    MessagePlugin.warning('请先勾选要操作的记录')
    return
  }
  try {
    for (const id of selectedIds.value) {
      await reject(id, '批量拒绝')
    }
    selectedIds.value = []
    await loadQueue(currentPage.value, pageSize.value)
    MessagePlugin.success('批量操作完成')
  } catch {
    MessagePlugin.error('批量操作失败')
  }
}

function handlePageChange(pageInfo: { current: number }) {
  currentPage.value = pageInfo.current
  loadQueue(currentPage.value, pageSize.value)
}

const pendingCount = computed(
  () => filteredRecords.value.filter((r) => r.review_status === 'pending_review').length,
)

const filteredTotal = computed(() => filteredRecords.value.length)
</script>

<template>
  <div class="review-page">
    <div class="page-header">
      <h1>审核工作台</h1>
      <p class="page-subtitle">
        待审核补全建议，高置信度自动采纳，低置信度需人工确认
        <t-tag
          v-if="pendingCount > 0"
          theme="warning"
          variant="light"
          size="small"
          style="margin-left: 8px"
        >
          {{ pendingCount }} 条待审核
        </t-tag>
      </p>
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
            placeholder="搜索资产名称、描述、标签..."
            autocomplete="off"
            @input="handleSearchChange"
          />
          <span v-if="filteredTotal > 0" class="result-count">{{ filteredTotal }} 条</span>
        </div>
        <div class="filter-bar">
          <!-- Status filter select -->
          <div class="filter-select-wrap">
            <select
              v-model="filters.status"
              class="filter-select"
              :class="{ active: filters.status !== '' }"
              @change="handleRefresh()"
            >
              <option v-for="opt in statusFilterOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <span class="filter-sep" />
          <!-- Type filter chips -->
          <div class="filter-group">
            <button
              v-for="chip in typeChips"
              :key="chip.value"
              class="filter-chip"
              :class="{ active: filters.entity_type === chip.value }"
              @click="setTypeFilter(chip.value)"
            >
              {{ chip.label }}
            </button>
          </div>
          <span class="filter-sep" />
          <!-- Confidence slider -->
          <div class="confidence-filter">
            <span class="conf-label">置信度 >= {{ confidenceMin }}%</span>
            <t-slider
              v-model="confidenceMin"
              :min="0"
              :max="100"
              :step="5"
              style="width: 100px"
            />
          </div>
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
        <div class="ops-bar-right">
          <span v-if="selectedIds.length > 0" class="ops-selected">已选 {{ selectedIds.length }} 项</span>
          <button
            class="ops-batch-btn ops-batch-reject"
            :disabled="selectedIds.length === 0"
            @click="handleBatchReject"
          >
            批量拒绝
          </button>
          <button
            class="ops-batch-btn"
            :disabled="selectedIds.length === 0"
            @click="handleBatchApprove"
          >
            批量确认
          </button>
        </div>
      </div>
    </section>

    <!-- Table -->
    <div class="review-table">
      <ReviewQueue
        :records="filteredRecords"
        :loading="loading"
        @update:selected-ids="(ids: string[]) => selectedIds = ids"
        @select="handleViewDetail"
        @approve="handleApprove"
        @reject="handleReject"
      />
    </div>

    <!-- Pagination -->
    <div v-if="total > pageSize" class="pagination-wrap">
      <t-pagination
        :current="currentPage"
        :total="total"
        :page-size="pageSize"
        show-jumper
        @change="handlePageChange"
      />
    </div>

    <!-- Detail Dialog -->
    <ReviewDetail
      v-if="detail"
      :visible="detailVisible"
      :detail="detail"
      @close="detailVisible = false"
      @refresh="handleDetailRefresh"
    />
  </div>
</template>

<style scoped>
/* ── Design tokens（与 SearchPage 一致）── */
.review-page {
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
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

/* ── Confidence slider ── */
.confidence-filter {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.conf-label {
  font-size: 13px;
  color: var(--color-muted);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
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

.ops-bar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ops-selected {
  font-size: 13px;
  color: var(--color-muted);
  font-variant-numeric: tabular-nums;
}

.ops-batch-btn {
  padding: 6px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--color-accent);
  background: var(--color-accent);
  color: #fff;
  font-family: inherit;
  transition: all 0.15s;
  white-space: nowrap;
}

.ops-batch-btn:hover:not(:disabled) {
  opacity: 0.88;
}

.ops-batch-btn:disabled {
  background: transparent;
  border-color: var(--color-border);
  color: var(--color-muted);
  cursor: not-allowed;
  opacity: 0.5;
}

.ops-batch-reject {
  background: transparent;
  border-color: var(--color-border);
  color: var(--color-muted);
}

.ops-batch-reject:hover:not(:disabled) {
  border-color: #e34d59;
  color: #e34d59;
  background: transparent;
  opacity: 1;
}

/* ── Table section ── */
.review-table {
  margin-bottom: 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

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

@media (max-width: 768px) {
  .review-page {
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

  .ops-bar-right {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
