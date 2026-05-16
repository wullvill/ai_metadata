<template>
  <t-card title="AI 补全建议" class="completion-panel">
    <div v-if="completing" class="loading-state">
      <t-loading text="AI 正在分析并生成补全建议..." />
    </div>
    <div v-else-if="error" class="error-state">
      <t-alert theme="error" :message="error" />
    </div>
    <div v-else-if="result" class="result-content">
      <div class="field-row">
        <span class="field-label">中文名</span>
        <span class="field-value">{{ result.display_name }}</span>
      </div>
      <div class="field-row">
        <span class="field-label">描述</span>
        <span class="field-value description">{{ result.description }}</span>
      </div>
      <div v-if="result.tags?.length" class="field-row">
        <span class="field-label">标签</span>
        <span class="field-value">
          <t-tag v-for="tag in result.tags" :key="tag" size="small" style="margin-right: 4px">
            {{ tag }}
          </t-tag>
        </span>
      </div>
      <div v-if="result.business_domain" class="field-row">
        <span class="field-label">业务域</span>
        <span class="field-value">{{ result.business_domain }}</span>
      </div>
      <div v-if="result.sensitive_level" class="field-row">
        <span class="field-label">敏感级别</span>
        <t-tag :theme="sensitiveTheme">{{ result.sensitive_level }}</t-tag>
      </div>
      <div class="field-row">
        <span class="field-label">置信度</span>
        <QualityBadge :status="qualityStatus" :confidence="result.confidence" />
      </div>
      <div v-if="result.reasoning" class="field-row reasoning">
        <span class="field-label">依据</span>
        <span class="field-value">{{ result.reasoning }}</span>
      </div>
    </div>
  </t-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import QualityBadge from './QualityBadge.vue'
import type { CompletionResult, QualityCheck } from '../api/types'

const props = defineProps<{
  completing: boolean
  result: CompletionResult | null
  qualityCheck: QualityCheck | null
  error: string | null
}>()

const qualityStatus = computed(() => props.qualityCheck?.review_status || 'pending_review')

const sensitiveTheme = computed(() => {
  switch (props.result?.sensitive_level) {
    case 'L4': return 'danger'
    case 'L3': return 'warning'
    case 'L2': return 'primary'
    default: return 'default'
  }
})
</script>

<style scoped>
.completion-panel { margin-top: 16px; }
.field-row { display: flex; align-items: flex-start; margin-bottom: 12px; }
.field-label { width: 80px; flex-shrink: 0; color: var(--td-text-color-placeholder); font-size: 13px; }
.field-value { flex: 1; }
.description { color: var(--td-text-color-primary); }
.reasoning { color: var(--td-text-color-secondary); font-size: 12px; }
.loading-state, .error-state { padding: 24px 0; }
</style>
