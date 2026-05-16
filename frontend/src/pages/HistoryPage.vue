<script setup lang="ts">
import { ref, onMounted } from 'vue'
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

const statusOptions = [
  { label: '全部', value: '' },
  { label: '自动采纳', value: 'auto_approved' },
  { label: '已确认', value: 'approved' },
  { label: '已修改', value: 'modified' },
  { label: '已拒绝', value: 'rejected' },
  { label: '人工驳回', value: 'human_rejected' },
]

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
    <div class="page-header">
      <div>
        <h1>补全历史</h1>
        <p class="page-subtitle">查看所有智能补全记录及审核追溯</p>
      </div>
    </div>

    <div class="history-filters surface-card">
      <t-input
        v-model="filters.entity_id"
        placeholder="实体 ID 搜索..."
        size="small"
        clearable
        style="width: 240px"
      />
      <t-select
        v-model="filters.status"
        :options="statusOptions"
        placeholder="状态"
        clearable
        size="small"
        style="width: 140px"
      />
      <t-date-picker
        v-model="filters.start_date"
        placeholder="开始日期"
        size="small"
        style="width: 160px"
      />
      <t-date-picker
        v-model="filters.end_date"
        placeholder="结束日期"
        size="small"
        style="width: 160px"
      />
      <t-button size="small" @click="loadHistory()">查询</t-button>
      <span class="filter-total">共 {{ total }} 条</span>
    </div>

    <div class="history-table">
      <t-table
        :data="records"
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
            <span style="font-family: monospace; font-size: 0.875rem">
              {{ row.entity_id }}
            </span>
          </div>
        </template>

        <template #entity_type="{ row }">
          {{ row.entity_type === 'table' ? '表' : '字段' }}
        </template>

        <template #display_name="{ row }">
          <span style="font-weight: 500; font-size: 0.875rem">
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
          <div v-if="row.completion_result" style="padding: 16px 24px; background: var(--color-bg)">
            <p style="font-size: 0.875rem; line-height: 2">
              <strong>中文名:</strong> {{ row.completion_result.display_name }}
            </p>
            <p style="font-size: 0.875rem; line-height: 2">
              <strong>描述:</strong> {{ row.completion_result.description }}
            </p>
            <p style="font-size: 0.875rem; line-height: 2">
              <strong>标签:</strong> {{ row.completion_result.tags?.join(' / ') || '-' }}
            </p>
            <p style="font-size: 0.875rem; line-height: 2">
              <strong>置信度:</strong>
              {{ ((row.quality_check?.adjusted_confidence ?? row.completion_result.confidence) * 100).toFixed(0) }}%
            </p>
          </div>
          <div v-else style="padding: 16px 24px; background: var(--color-bg)">
            <p style="font-size: 0.875rem; color: var(--color-text-secondary)">暂无补全结果</p>
          </div>
        </template>
      </t-table>
    </div>

    <div v-if="total > (filters.limit ?? 20)" style="display: flex; justify-content: center; margin-top: 24px">
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
.history-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
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

.history-filters {
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

.history-table {
  background: var(--color-surface);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-card);
}
</style>
