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

const entityTypeOptions = [
  { label: '全部', value: '' },
  { label: '表', value: 'table' },
  { label: '字段', value: 'column' },
]

watch(() => filters.status, () => handleRefresh())
watch(() => filters.entity_type, () => handleRefresh())

function handleRefresh() {
  currentPage.value = 1
  loadQueue(currentPage.value, pageSize.value)
}

async function handleViewDetail(record: ReviewRecord) {
  currentRecordId.value = record.id
  await loadDetail(record.id)
  detailVisible.value = true
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
  // batchReject is not available in the current API; reject one by one as fallback
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
  () => records.value.filter((r) => r.review_status === 'pending_review').length,
)
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

    <div class="review-filters surface-card">
      <t-select
        v-model="filters.status"
        :options="statusFilterOptions"
        placeholder="审核状态"
        clearable
        size="small"
        style="width: 140px"
      />
      <t-select
        v-model="filters.entity_type"
        :options="entityTypeOptions"
        placeholder="实体类型"
        clearable
        size="small"
        style="width: 120px"
      />
      <t-button size="small" variant="text" @click="handleRefresh()">
        <t-icon name="refresh" />
        刷新
      </t-button>
      <span class="filter-total">共 {{ total }} 条</span>
    </div>

    <div class="review-table">
      <ReviewQueue
        :records="records"
        :loading="loading"
        @update:selected-ids="(ids: string[]) => selectedIds = ids"
        @select="handleViewDetail"
        @approve="handleApprove"
        @reject="handleReject"
      />
    </div>

    <div v-if="total > pageSize" style="display: flex; justify-content: center; margin-top: 24px">
      <t-pagination
        :current="currentPage"
        :total="total"
        :page-size="pageSize"
        show-jumper
        @change="handlePageChange"
      />
    </div>

    <ReviewDetail
      v-if="detail"
      :visible="detailVisible"
      :detail="detail"
      @close="detailVisible = false"
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
}

.page-subtitle {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.review-filters {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px 24px;
  flex-wrap: wrap;
  background: var(--color-surface);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-card);
}

.filter-total {
  margin-left: auto;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.review-table {
  background: var(--color-surface);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-card);
}
</style>
