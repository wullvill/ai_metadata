<template>
  <div class="review-queue">
    <t-table
      :data="records"
      :columns="columns"
      :loading="loading"
      :selected-row-keys="selectedIds"
      row-key="id"
      @select-change="handleSelectChange"
      @row-click="handleRowClick"
      hover
      stripe
    >
      <template #display_name="{ row }">
        <span class="cell-text">{{ row.completion_result?.display_name || '—' }}</span>
      </template>
      <template #description="{ row }">
        <span class="cell-text muted">{{ row.completion_result?.description || '—' }}</span>
      </template>
      <template #confidence="{ row }">
        <span
          v-if="row.completion_result?.confidence != null"
          class="cell-mono"
          :style="{ color: row.completion_result.confidence >= 0.8 ? 'var(--td-success-color)' : row.completion_result.confidence >= 0.6 ? 'var(--td-warning-color)' : 'var(--td-error-color)' }"
        >{{ (row.completion_result.confidence * 100).toFixed(0) }}%</span>
        <span v-else class="cell-mono">—</span>
      </template>
      <template #entity_type="{ row }">
        <t-tag :theme="row.entity_type === 'table' ? 'primary' : 'success'" size="small">
          {{ row.entity_type === 'table' ? '表' : '字段' }}
        </t-tag>
      </template>
      <template #status="{ row }">
        <QualityBadge :status="row.review_status" :confidence="row.quality_check?.adjusted_confidence" />
      </template>
      <template #actions="{ row }">
        <t-space>
          <t-button theme="primary" variant="text" size="small" @click.stop="$emit('approve', row.id)">
            确认
          </t-button>
          <t-button theme="danger" variant="text" size="small" @click.stop="$emit('reject', row.id)">
            拒绝
          </t-button>
        </t-space>
      </template>
    </t-table>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import QualityBadge from './QualityBadge.vue'
import type { ReviewRecord } from '../api/types'

defineProps<{
  records: ReviewRecord[]
  loading: boolean
}>()

const emit = defineEmits<{
  select: [record: ReviewRecord]
  approve: [id: string]
  reject: [id: string]
  'update:selectedIds': [ids: string[]]
}>()

const selectedIds = ref<string[]>([])

function handleSelectChange(keys: string[]) {
  selectedIds.value = keys
  emit('update:selectedIds', keys)
}

function handleRowClick({ row }: { row: ReviewRecord }) {
  emit('select', row)
}

const columns = [
  { colKey: 'entity_id', title: '实体 ID', ellipsis: true, width: 200 },
  { colKey: 'display_name', title: '建议中文名', ellipsis: true, width: 120 },
  { colKey: 'description', title: '描述', ellipsis: true, width: 180 },
  { colKey: 'entity_type', title: '类型', width: 60 },
  { colKey: 'confidence', title: '置信度', width: 80 },
  { colKey: 'status', title: '状态', width: 100 },
  { colKey: 'created_at', title: '申请时间', width: 150 },
  { colKey: 'actions', title: '操作', width: 140 },
]
</script>

<style scoped>
.cell-text {
  font-size: 13px;
  color: var(--td-text-color-primary);
}

.cell-text.muted {
  color: var(--td-text-color-placeholder);
}

.cell-mono {
  font-family: 'JetBrains Mono', 'SF Mono', ui-monospace, monospace;
  font-size: 12px;
  font-weight: 600;
}
</style>
