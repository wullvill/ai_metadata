<template>
  <div class="review-detail-page">
    <div class="top-zone">
      <div class="breadcrumb"><router-link to="/review">审核工作台</router-link> / {{ detail?.entity_id || '...' }}</div>
      <h1 class="asset-name">{{ detail?.entity_id || '...' }}</h1>
      <p class="asset-subtitle">{{ entityTypeLabel }} · {{ detail?.target_data?.database }}.{{ detail?.target_data?.schema }}</p>
      <div class="badge-row">
        <t-tag variant="light" theme="default">{{ entityTypeLabel }}</t-tag>
        <t-tag variant="light" :theme="statusTheme">{{ statusLabel }}</t-tag>
        <t-tag variant="light" theme="primary">AI 补全</t-tag>
      </div>
    </div>

    <div class="bottom-zone">
      <t-tabs v-model="activeTab">
        <t-tab-panel value="info" label="基本信息">
          <div class="detail-list">
            <div class="detail-row"><span class="detail-label">资产名称</span><span class="detail-value mono">{{ detail?.entity_id }}</span></div>
            <div class="detail-row"><span class="detail-label">类型</span><span class="detail-value"><t-tag variant="light" theme="default">{{ entityTypeLabel }}</t-tag></span></div>
            <div class="detail-row"><span class="detail-label">所属库</span><span class="detail-value mono">{{ detail?.target_data?.database || '—' }}</span></div>
            <div class="detail-row"><span class="detail-label">Schema</span><span class="detail-value mono">{{ detail?.target_data?.schema || '—' }}</span></div>
            <div class="detail-row"><span class="detail-label">审核状态</span><span class="detail-value"><t-tag variant="light" :theme="statusTheme">{{ statusLabel }}</t-tag></span></div>
          </div>
          <p class="info-section-title">AI 补全建议概要</p>
          <div class="detail-list">
            <div class="detail-row"><span class="detail-label">建议中文名</span><span class="detail-value">{{ detail?.completion_result?.display_name }}</span></div>
            <div class="detail-row"><span class="detail-label">建议描述</span><span class="detail-value muted">{{ detail?.completion_result?.description }}</span></div>
            <div class="detail-row"><span class="detail-label">建议标签</span><span class="detail-value">
              <t-tag v-for="t in detail?.completion_result?.tags" :key="t" variant="light" theme="primary" style="margin-right:4px">{{ t }}</t-tag>
            </span></div>
            <div class="detail-row"><span class="detail-label">置信度</span><span class="detail-value mono bold" :style="{ color: confColor }">{{ confPercent }}%</span></div>
          </div>
        </t-tab-panel>

        <t-tab-panel value="compare" label="补全对比">
          <div class="compare-grid">
            <div class="compare-card"><h4>原始元数据</h4>
              <div class="field"><div class="field-label">中文名</div><div class="field-value">{{ detail?.target_data?.current_display_name || '—' }}</div></div>
              <div class="field"><div class="field-label">描述</div><div class="field-value muted">{{ detail?.target_data?.current_description || '—' }}</div></div>
            </div>
            <div class="compare-card ai-card"><h4>AI 补全建议</h4>
              <div class="field"><div class="field-label">中文名</div><div class="field-value"><t-input v-model="editDisplayName" :disabled="!isPending" @change="onEdit" /></div></div>
              <div class="field"><div class="field-label">描述</div><div class="field-value"><t-textarea v-model="editDesc" :disabled="!isPending" :autosize="{ minRows: 2 }" @change="onEdit" /></div></div>
              <div class="field"><div class="field-label">标签</div><div class="field-value"><t-input v-model="editTags" :disabled="!isPending" placeholder="逗号分隔" @change="onEdit" /></div></div>
              <div class="field"><div class="field-label">置信度</div><div class="field-value mono bold" :style="{ color: confColor }">{{ confPercent }}%</div></div>
            </div>
          </div>
        </t-tab-panel>

        <t-tab-panel value="quality" label="质量校验">
          <p class="info-section-title">质量校验结果</p>
          <div v-if="detail?.quality_check?.rule_violations?.length">
            <div v-for="v in detail.quality_check.rule_violations" :key="v.rule" class="quality-rule">
              <span class="dot" :class="dotClass(v.severity)"></span>
              <span>{{ v.rule }}</span>
              <span class="rule-detail">{{ v.message }}</span>
            </div>
          </div>
          <div v-else class="empty-state-sm">暂无质量校验结果</div>
        </t-tab-panel>
      </t-tabs>
    </div>

    <div class="detail-footer" v-if="isPending">
      <t-button theme="danger" variant="outline" @click="handleReject">驳回</t-button>
      <t-button theme="default" variant="outline" :disabled="!modified" @click="handleModifyApprove">确认修改</t-button>
      <t-button theme="primary" @click="handleApprove">确认采纳</t-button>
    </div>
    <div class="detail-footer" v-else>
      <span class="muted">该记录已{{ statusLabel }}，不可操作</span>
    </div>

    <t-dialog v-model:visible="rejectVisible" header="驳回补全建议" :on-confirm="doReject" confirm-btn="确认驳回" :confirm-btn-props="{ theme: 'danger' }">
      <t-textarea v-model="rejectReason" placeholder="请说明驳回原因..." :autosize="{ minRows: 3 }" />
      <p v-if="rejectError" class="field-error">请填写驳回原因</p>
    </t-dialog>
    <t-dialog v-model:visible="approveVisible" header="确认采纳补全建议" :on-confirm="doApprove">
      <p>确认采纳「{{ detail?.entity_id }}」的 AI 补全建议？将回写至 OpenMetadata。</p>
    </t-dialog>

    <div v-if="error" class="error-state">
      <t-icon name="error-circle" size="48px" />
      <h2>{{ error }}</h2>
      <router-link to="/review"><t-button theme="default">← 返回审核工作台</t-button></router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReviewDetail, approveReview, rejectReview } from '../api'
import type { ReviewDetail } from '../api/types'

const route = useRoute()
const router = useRouter()
const detail = ref<ReviewDetail | null>(null)
const error = ref('')
const activeTab = ref('info')
const editDisplayName = ref('')
const editDesc = ref('')
const editTags = ref('')
const modified = ref(false)
const rejectVisible = ref(false)
const approveVisible = ref(false)
const rejectReason = ref('')
const rejectError = ref(false)

const isPending = computed(() => detail.value?.review_status === 'pending_review')
const entityTypeLabel = computed(() => detail.value?.entity_type === 'column' ? '字段' : '表')
const statusLabels: Record<string, string> = { pending_review: '待审核', auto_approved: '已自动采纳', approved: '已确认', human_rejected: '已驳回', rejected: '系统拒绝', modified: '已修改' }
const statusLabel = computed(() => statusLabels[detail.value?.review_status || ''] || '—')
const statusThemes: Record<string, string> = { auto_approved: 'success', approved: 'primary', pending_review: 'warning', human_rejected: 'default', rejected: 'danger', modified: 'primary' }
const statusTheme = computed(() => statusThemes[detail.value?.review_status || ''] || 'default')
const confPercent = computed(() => ((detail.value?.completion_result?.confidence || 0) * 100).toFixed(0))
const confColor = computed(() => {
  const c = detail.value?.completion_result?.confidence || 0
  return c >= 0.8 ? 'var(--td-success-color)' : c >= 0.6 ? 'var(--td-warning-color)' : 'var(--td-error-color)'
})
const dotClass = (s: string) => ({ critical: 'fail', warning: 'warn', info: 'pass' }[s] || 'pass')

function onEdit() {
  const r = detail.value?.completion_result
  modified.value = !!r && (editDisplayName.value !== r.display_name || editDesc.value !== r.description || editTags.value !== (r.tags || []).join(', '))
}
function handleApprove() { approveVisible.value = true }
function handleReject() { rejectReason.value = ''; rejectError.value = false; rejectVisible.value = true }
function handleModifyApprove() { approveReview(detail.value!.id, '已修改后确认').then(() => router.push('/review')) }
async function doApprove() { if (!detail.value) return; await approveReview(detail.value.id); router.push('/review') }
async function doReject() {
  if (!rejectReason.value.trim()) { rejectError.value = true; return }
  if (!detail.value) return
  await rejectReview(detail.value.id, rejectReason.value)
  rejectVisible.value = false; router.push('/review')
}

onMounted(async () => {
  const id = route.params.id as string
  if (!id) { error.value = '缺少审核标识'; return }
  try {
    const resp = await getReviewDetail(id)
    detail.value = resp.data
    const r = resp.data.completion_result
    if (r) { editDisplayName.value = r.display_name; editDesc.value = r.description; editTags.value = (r.tags || []).join(', ') }
  } catch { error.value = '加载失败，请稍后重试' }
})
</script>

<style scoped>
.review-detail-page { max-width: 960px; margin: 0 auto; padding: 20px 24px 32px; }
.top-zone { padding: 0 0 16px; border-bottom: 1px solid var(--td-border-level-2-color, #e7e7e7); }
.breadcrumb { font-size: 12px; color: var(--td-text-color-placeholder); margin-bottom: 4px; }
.breadcrumb a { color: var(--td-brand-color); text-decoration: none; }
.asset-name { font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; margin: 0 0 4px; }
.asset-subtitle { font-size: 13px; color: var(--td-text-color-placeholder); font-family: monospace; margin-bottom: 8px; }
.badge-row { display: flex; gap: 6px; flex-wrap: wrap; }
.bottom-zone { padding-top: 12px; }
.detail-list { border: 1px solid var(--td-border-level-2-color, #e7e7e7); border-radius: 10px; overflow: hidden; margin-bottom: 16px; }
.detail-row { display: flex; padding: 12px 20px; border-bottom: 1px solid var(--td-border-level-2-color, #e7e7e7); font-size: 14px; align-items: baseline; }
.detail-row:last-child { border-bottom: none; }
.detail-label { width: 100px; color: var(--td-text-color-placeholder); flex-shrink: 0; font-size: 13px; }
.detail-value { flex: 1; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.bold { font-weight: 700; }
.muted { color: var(--td-text-color-placeholder); }
.info-section-title { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: var(--td-text-color-placeholder); margin: 20px 0 12px; }
.compare-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.compare-card { border: 1px solid var(--td-border-level-2-color, #e7e7e7); border-radius: 10px; padding: 16px; }
.compare-card h4 { font-size: 13px; font-weight: 600; margin-bottom: 12px; color: var(--td-text-color-placeholder); }
.compare-card.ai-card { border-color: var(--td-brand-color); }
.compare-card.ai-card h4 { color: var(--td-brand-color); }
.field { margin-bottom: 10px; }
.field:last-child { margin-bottom: 0; }
.field-label { font-size: 12px; color: var(--td-text-color-placeholder); margin-bottom: 2px; }
.quality-rule { display: flex; align-items: center; gap: 8px; padding: 6px 0; font-size: 13px; }
.quality-rule .dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.quality-rule .dot.pass { background: var(--td-success-color); }
.quality-rule .dot.warn { background: var(--td-warning-color); }
.quality-rule .dot.fail { background: var(--td-error-color); }
.rule-detail { color: var(--td-text-color-placeholder); margin-left: auto; font-size: 12px; }
.detail-footer { border-top: 1px solid var(--td-border-level-2-color, #e7e7e7); padding: 16px 0 0; display: flex; gap: 10px; justify-content: flex-end; margin-top: 24px; }
.empty-state-sm { padding: 20px 0; color: var(--td-text-color-placeholder); font-size: 13px; }
.field-error { font-size: 12px; color: var(--td-error-color); margin-top: 8px; }
.error-state { text-align: center; padding: 80px 24px; color: var(--td-text-color-placeholder); }
.error-state h2 { font-size: 20px; margin: 8px 0 16px; }
@media (max-width: 768px) { .compare-grid { grid-template-columns: 1fr; } }
</style>
