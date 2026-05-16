<template>
  <t-dialog
    :visible="visible"
    header="审核详情"
    width="700px"
    :footer="false"
    @close="$emit('close')"
  >
    <div v-if="detail" class="review-detail">
      <t-descriptions bordered :column="2">
        <t-descriptions-item label="实体 ID">{{ detail.entity_id }}</t-descriptions-item>
        <t-descriptions-item label="类型">
          <t-tag :theme="detail.entity_type === 'table' ? 'primary' : 'success'" size="small">
            {{ detail.entity_type === 'table' ? '表' : '字段' }}
          </t-tag>
        </t-descriptions-item>
      </t-descriptions>

      <h4 style="margin-top: 16px">AI 补全建议</h4>
      <CompletionPanel
        v-if="detail.completion_result"
        :completing="false"
        :result="detail.completion_result"
        :quality-check="detail.quality_check"
        :error="null"
      />

      <div v-if="detail.quality_check?.rule_violations?.length" class="violations">
        <h4>校验问题</h4>
        <div v-for="(v, i) in detail.quality_check.rule_violations" :key="i" class="violation-item">
          <t-tag :theme="v.severity === 'critical' ? 'danger' : v.severity === 'warning' ? 'warning' : 'default'" size="small">
            {{ v.severity }}
          </t-tag>
          <span>{{ v.message }}</span>
        </div>
      </div>
    </div>
  </t-dialog>
</template>

<script setup lang="ts">
import CompletionPanel from './CompletionPanel.vue'
import type { ReviewDetail as ReviewDetailType } from '../api/types'

defineProps<{
  visible: boolean
  detail: ReviewDetailType | null
}>()

defineEmits<{
  close: []
}>()
</script>

<style scoped>
.review-detail { padding: 8px 0; }
.violations { margin-top: 16px; }
.violation-item { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
</style>
