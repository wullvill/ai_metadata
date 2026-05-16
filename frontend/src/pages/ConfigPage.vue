<script setup lang="ts">
import { ref } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'

const autoApproveThreshold = ref(0.8)
const pendingReviewThreshold = ref(0.6)
const saving = ref(false)

function saveConfig() {
  saving.value = true
  setTimeout(() => {
    saving.value = false
    MessagePlugin.success('配置已保存（当前为静态原型，实际将持久化到后端）')
  }, 600)
}
</script>

<template>
  <div class="config-page">
    <div class="page-header">
      <h1>规则配置</h1>
      <p class="page-subtitle">管理质量校验规则和阈值（后续版本支持完整规则配置）</p>
    </div>

    <div class="config-section surface-card">
      <h2>分流阈值</h2>
      <p class="section-desc">控制补全结果自动采纳 / 待审核 / 拒绝的置信度门槛</p>

      <div class="threshold-row">
        <div class="threshold-item">
          <label>自动采纳阈值</label>
          <t-slider
            v-model="autoApproveThreshold"
            :min="0.5"
            :max="1.0"
            :step="0.05"
            :marks="{ 0.5: '0.5', 0.6: '0.6', 0.7: '0.7', 0.8: '0.8', 0.9: '0.9', 1.0: '1.0' }"
          />
          <span class="threshold-value">{{ (autoApproveThreshold * 100).toFixed(0) }}%</span>
          <p class="threshold-hint">置信度 >= 该值且无关键违规时自动采纳</p>
        </div>

        <div class="threshold-item">
          <label>拒绝阈值</label>
          <t-slider
            v-model="pendingReviewThreshold"
            :min="0.2"
            :max="0.7"
            :step="0.05"
            :marks="{ 0.2: '0.2', 0.3: '0.3', 0.4: '0.4', 0.5: '0.5', 0.6: '0.6', 0.7: '0.7' }"
          />
          <span class="threshold-value">{{ (pendingReviewThreshold * 100).toFixed(0) }}%</span>
          <p class="threshold-hint">置信度 < 该值或有关键违规时直接拒绝</p>
        </div>
      </div>

      <t-divider />

      <div class="rule-list">
        <h3>质量校验规则（当前版本）</h3>
        <t-table
          :data="[
            { rule: 'required_fields', level: 'CRITICAL', desc: 'display_name 和 description 任一缺失直接拒绝' },
            { rule: 'display_name_no_code', level: 'WARNING', desc: '中文名不应包含大段英文字符' },
            { rule: 'description_not_copy_name', level: 'WARNING', desc: '描述不应与中文名完全一致' },
            { rule: 'sensitive_level_valid', level: 'WARNING', desc: '敏感级别必须在 L1–L4 范围内' },
            { rule: 'tag_no_duplicates', level: 'INFO', desc: '标签列表不应包含重复项' },
            { rule: 'business_domain_valid', level: 'INFO', desc: '业务域名字符长度合理' },
            { rule: 'table_name_consistency', level: 'WARNING', desc: '表中文名不应与英文表名完全相同' },
          ]"
          :columns="[
            { colKey: 'rule', title: '规则名', width: 220 },
            { colKey: 'level', title: '级别', width: 100 },
            { colKey: 'desc', title: '说明', ellipsis: true },
          ]"
          row-key="rule"
          size="small"
          hover
        >
          <template #level="{ row }">
            <t-tag
              size="small"
              :theme="row.level === 'CRITICAL' ? 'danger' : row.level === 'WARNING' ? 'warning' : 'default'"
              variant="light"
            >
              {{ row.level }}
            </t-tag>
          </template>
        </t-table>
      </div>

      <div style="margin-top: 24px">
        <t-button theme="primary" :loading="saving" @click="saveConfig">保存配置</t-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.config-page {
  max-width: 900px;
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

.config-section {
  background: var(--color-surface);
  border-radius: var(--radius-base);
  padding: 24px;
  box-shadow: var(--shadow-card);
}

.config-section h2 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text);
}

.section-desc {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-top: 8px;
  margin-bottom: 24px;
}

.threshold-row {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.threshold-item label {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--color-text);
}

.threshold-value {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-primary);
  margin-left: 8px;
}

.threshold-hint {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.rule-list h3 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--color-text);
}
</style>
