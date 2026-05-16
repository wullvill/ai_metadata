<template>
  <t-tag
    :theme="tagTheme"
    variant="light"
    size="small"
  >
    {{ label }}
  </t-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
  confidence?: number
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
  const confidenceStr = props.confidence !== undefined ? ` ${(props.confidence * 100).toFixed(0)}%` : ''
  switch (props.status) {
    case 'auto_approved': return `自动通过${confidenceStr}`
    case 'approved': return `已确认${confidenceStr}`
    case 'pending_review': return `待审核${confidenceStr}`
    case 'rejected': return '已拒绝'
    case 'human_rejected': return '人工拒绝'
    default: return props.status
  }
})
</script>
