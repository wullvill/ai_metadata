<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
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

// Server-side filter triggers
watch(() => filters.status, () => handleRefresh())
watch(() => filters.entity_type, () => handleRefresh())

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

async function handleApprove(id: string) {
  try {
    await DialogPlugin.confirm({
      header: '确认采纳',
      body: '确定采纳此 AI 补全建议？系统将自动回写 OpenMetadata。',
    })
    await approve(id)
    MessagePlugin.success('已确认采纳')
  } catch {
    MessagePlugin.error('操作失败')
  }
}

async function handleReject(id: string) {
  try {
    await DialogPlugin.confirm({
      header: '确认拒绝',
      body: '确定拒绝此补全建议？此操作将仅记录日志，不会回写 OpenMetadata。',
    })
    await reject(id, '人工拒绝')
    MessagePlugin.success('已拒绝')
  } catch {
    MessagePlugin.error('操作失败')
  }
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
      <div>
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
      <t-space>
        <t-button
          theme="danger"
          variant="outline"
          :disabled="selectedIds.length === 0"
          @click="handleBatchReject"
        >
          批量拒绝 ({{ selectedIds.length }})
        </t-button>
        <t-button
          theme="success"
          :disabled="selectedIds.length === 0"
          @click="handleBatchApprove"
        >
          批量确认 ({{ selectedIds.length }})
        </t-button>
      </t-space>
    </div>

    <!-- Search & Filter Bar -->
    <div class="search-filter-bar surface-card">
      <div class="search-row">
        <t-input
          v-model="searchQuery"
          placeholder="搜索资产名称、描述、标签..."
          clearable
          size="medium"
          class="search-input"
          @change="handleSearchChange"
        >
          <template #prefix-icon>
            <t-icon name="search" />
          </template>
        </t-input>
        <span class="stat-label">共 {{ filteredTotal }} 条</span>
      </div>
      <div class="filter-row">
        <t-select
          v-model="filters.status"
          :options="statusFilterOptions"
          placeholder="审核状态"
          clearable
          size="small"
          style="width: 130px"
        />
        <t-radio-group
          v-model="filters.entity_type"
          variant="default-filled"
          size="small"
        >
          <t-radio-button
            v-for="chip in typeChips"
            :key="chip.value"
            :value="chip.value"
          >
            {{ chip.label }}
          </t-radio-button>
        </t-radio-group>
        <div class="confidence-filter">
          <span class="conf-label">置信度 >= {{ confidenceMin }}%</span>
          <t-slider
            v-model="confidenceMin"
            :min="0"
            :max="100"
            :step="5"
            style="width: 120px"
          />
        </div>
        <t-button size="small" variant="text" @click="handleRefresh()">
          <t-icon name="refresh" />
          刷新
        </t-button>
      </div>
    </div>

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
.review-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.page-subtitle {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

/* Search & Filter Bar */
.search-filter-bar {
  margin-bottom: 24px;
  padding: 12px 16px;
  background: var(--color-surface);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-card);
}

.search-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.search-input {
  flex: 1;
  max-width: 480px;
}

.stat-label {
  margin-left: auto;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.confidence-filter {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.conf-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  min-width: 90px;
}

.review-table {
  background: var(--color-surface);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-card);
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .filter-row {
    gap: 8px;
  }

  .confidence-filter {
    width: 100%;
  }

  .confidence-filter .conf-label {
    min-width: auto;
  }
}
</style>
