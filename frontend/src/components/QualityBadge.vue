<template>
  <span class="quality-badge">
    <t-tag
      :theme="tagTheme"
      variant="light"
      size="small"
    >
      {{ label }}
    </t-tag>
    <div v-if="showBar && confidence !== null && confidence !== undefined" class="confidence-bar-wrapper">
      <div
        class="confidence-bar"
        :class="barColorClass"
        :style="{ width: barWidth }"
      />
      <span class="confidence-percent">{{ displayPercent }}</span>
    </div>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
  confidence: number | null
  showBar?: boolean
}>()

const tagTheme = computed(() => {
  switch (props.status) {
    case 'auto_approved':
    case 'approved':
      return 'success'
    case 'pending_review':
      return 'warning'
    case 'rejected':
    case 'human_rejected':
      return 'danger'
    default:
      return 'default'
  }
})

const label = computed(() => {
  switch (props.status) {
    case 'auto_approved': return '自动通过'
    case 'approved': return '已确认'
    case 'pending_review': return '待审核'
    case 'rejected': return '已拒绝'
    case 'human_rejected': return '人工拒绝'
    default: return props.status
  }
})

const barWidth = computed(() => {
  if (props.confidence === null || props.confidence === undefined) return '0%'
  return `${(props.confidence * 100).toFixed(0)}%`
})

const barColorClass = computed(() => {
  if (props.confidence === null || props.confidence === undefined) return 'bar-default'
  if (props.confidence >= 0.8) return 'bar-success'
  if (props.confidence >= 0.6) return 'bar-warning'
  if (props.confidence >= 0) return 'bar-danger'
  return 'bar-default'
})

const displayPercent = computed(() => {
  if (props.confidence === null || props.confidence === undefined) return '-'
  return `${(props.confidence * 100).toFixed(0)}%`
})
</script>

<style scoped>
.quality-badge {
  display: inline-flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}

.confidence-bar-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  min-width: 80px;
}

.confidence-bar {
  height: 6px;
  border-radius: 3px;
  transition: width 0.3s ease;
  min-width: 0;
}

.bar-success { background-color: var(--td-success-color, #2ba471); }
.bar-warning { background-color: var(--td-warning-color, #e37318); }
.bar-danger  { background-color: var(--td-error-color, #d54941); }
.bar-default { background-color: var(--td-gray-color-5, #b5c7ff); }

.confidence-percent {
  font-family: ui-monospace, SFMono-Regular, 'Cascadia Code', Consolas, monospace;
  font-size: 11px;
  color: var(--td-text-color-placeholder);
  white-space: nowrap;
}
</style>
