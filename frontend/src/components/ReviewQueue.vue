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
  { colKey: 'entity_id', title: '实体 ID', ellipsis: true, width: 250 },
  { colKey: 'entity_type', title: '类型', width: 70 },
  { colKey: 'status', title: '状态', width: 120 },
  { colKey: 'created_at', title: '创建时间', width: 180 },
  { colKey: 'actions', title: '操作', width: 140 },
]
</script>
