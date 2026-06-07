<template>
  <t-dialog
    :visible="visible"
    header="审核详情"
    width="900px"
    :footer="false"
    attach="body"
    @close="$emit('close')"
  >
    <div v-if="detail" class="review-detail">
      <!-- Entity Header -->
      <div class="detail-header-info">
        <h3 class="entity-name">{{ detail.entity_id }}</h3>
        <div class="entity-subtitle">
          {{ entityTypeLabel }} &middot;
          {{ detail.target_data?.database || '—' }}.{{ detail.target_data?.schema || '—' }}
        </div>
        <div class="badge-row">
          <t-tag variant="light" theme="default">{{ entityTypeLabel }}</t-tag>
          <t-tag variant="light" :theme="statusTheme">{{ statusLabel }}</t-tag>
          <t-tag variant="light" theme="primary">AI 补全</t-tag>
        </div>
      </div>

      <!-- Tabs -->
      <t-tabs v-model="activeTab">
        <!-- Tab 1: 基本信息 -->
        <t-tab-panel value="info" label="基本信息">
          <div class="section-title">基本信息</div>
          <div class="detail-list">
            <div class="detail-row">
              <span class="detail-label">资产名称</span>
              <span class="detail-value mono">{{ detail.entity_id }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">类型</span>
              <span class="detail-value">
                <t-tag variant="light" theme="default">{{ entityTypeLabel }}</t-tag>
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">所属库</span>
              <span class="detail-value mono">{{ detail.target_data?.database || '—' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Schema</span>
              <span class="detail-value mono">{{ detail.target_data?.schema || '—' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">审核状态</span>
              <span class="detail-value">
                <t-tag variant="light" :theme="statusTheme">{{ statusLabel }}</t-tag>
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">审核人</span>
              <span class="detail-value">{{ detail.reviewer || '—' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">审核备注</span>
              <span class="detail-value muted">{{ detail.review_comment || '—' }}</span>
            </div>
          </div>

          <div class="section-title">原始元数据</div>
          <div class="detail-list">
            <div class="detail-row">
              <span class="detail-label">中文名</span>
              <span class="detail-value">{{ detail.target_data?.current_display_name || '—' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">描述</span>
              <span class="detail-value muted">{{ detail.target_data?.current_description || '—' }}</span>
            </div>
            <div v-if="detail.target_data?.current_tags?.length" class="detail-row">
              <span class="detail-label">标签</span>
              <span class="detail-value">
                <t-tag
                  v-for="t in detail.target_data.current_tags"
                  :key="t"
                  variant="light"
                  size="small"
                  style="margin-right: 4px"
                >{{ t }}</t-tag>
              </span>
            </div>
          </div>

          <div class="section-title">AI 补全建议概要</div>
          <div class="detail-list">
            <div class="detail-row">
              <span class="detail-label">建议中文名</span>
              <span class="detail-value">{{ detail.completion_result?.display_name || '—' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">建议描述</span>
              <span class="detail-value muted">{{ detail.completion_result?.description || '—' }}</span>
            </div>
            <div v-if="detail.completion_result?.tags?.length" class="detail-row">
              <span class="detail-label">建议标签</span>
              <span class="detail-value">
                <t-tag
                  v-for="t in detail.completion_result.tags"
                  :key="t"
                  variant="light"
                  theme="primary"
                  size="small"
                  style="margin-right: 4px"
                >{{ t }}</t-tag>
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">置信度</span>
              <span class="detail-value mono bold" :style="{ color: confColor }">
                {{ confPercent }}%
              </span>
            </div>
            <div v-if="detail.completion_result?.business_domain" class="detail-row">
              <span class="detail-label">业务域</span>
              <span class="detail-value">{{ detail.completion_result.business_domain }}</span>
            </div>
            <div v-if="detail.completion_result?.reasoning" class="detail-row">
              <span class="detail-label">推理依据</span>
              <span class="detail-value muted reasoning">{{ detail.completion_result.reasoning }}</span>
            </div>
          </div>
        </t-tab-panel>

        <!-- Tab 2: 补全对比 -->
        <t-tab-panel value="compare" label="补全对比">
          <div class="compare-grid">
            <div class="compare-card">
              <h4 class="compare-card-title">原始元数据</h4>
              <div class="field">
                <div class="field-label">中文名</div>
                <div class="field-value">{{ detail.target_data?.current_display_name || '—' }}</div>
              </div>
              <div class="field">
                <div class="field-label">描述</div>
                <div class="field-value muted">{{ detail.target_data?.current_description || '—' }}</div>
              </div>
              <div v-if="detail.target_data?.current_tags?.length" class="field">
                <div class="field-label">标签</div>
                <div class="field-value">
                  <t-tag
                    v-for="t in detail.target_data.current_tags"
                    :key="t"
                    variant="light"
                    size="small"
                    style="margin-right: 4px"
                  >{{ t }}</t-tag>
                </div>
              </div>
            </div>
            <div class="compare-card ai-card">
              <h4 class="compare-card-title">AI 补全建议</h4>
              <div class="field">
                <div class="field-label">中文名</div>
                <div class="field-value">
                  <t-input
                    v-model="editDisplayName"
                    :disabled="!isPending"
                    @change="onEdit"
                  />
                </div>
              </div>
              <div class="field">
                <div class="field-label">描述</div>
                <div class="field-value">
                  <t-textarea
                    v-model="editDesc"
                    :disabled="!isPending"
                    :autosize="{ minRows: 2, maxRows: 6 }"
                    @change="onEdit"
                  />
                </div>
              </div>
              <div class="field">
                <div class="field-label">标签</div>
                <div class="field-value">
                  <t-input
                    v-model="editTags"
                    :disabled="!isPending"
                    placeholder="逗号分隔"
                    @change="onEdit"
                  />
                </div>
              </div>
              <div class="field">
                <div class="field-label">置信度</div>
                <div class="field-value mono bold" :style="{ color: confColor }">
                  {{ confPercent }}%
                </div>
              </div>
            </div>
          </div>
        </t-tab-panel>

        <!-- Tab 3: 质量校验 -->
        <t-tab-panel value="quality" label="质量校验">
          <div class="section-title">
            质量校验结果
            <span v-if="detail.quality_check" class="quality-summary">
              ({{ passCount }} 通过 / {{ warnCount }} 提醒 / {{ failCount }} 未通过)
            </span>
          </div>

          <div v-if="detail.quality_check?.rule_violations?.length" class="quality-section">
            <div
              v-for="v in detail.quality_check.rule_violations"
              :key="v.rule"
              class="quality-rule"
            >
              <span class="dot" :class="dotClass(v.severity)"></span>
              <span class="rule-name">{{ v.rule }}</span>
              <span class="rule-detail">{{ v.message }}</span>
            </div>
          </div>
          <div v-else class="empty-note">暂无质量校验结果</div>

          <div
            v-if="detail.quality_check?.conflicts?.length"
            class="quality-section conflicts-section"
          >
            <div class="section-title">冲突检测</div>
            <div
              v-for="c in detail.quality_check.conflicts"
              :key="c.type"
              class="quality-rule"
            >
              <span class="dot" :class="conflictDotClass(c.severity)"></span>
              <span class="rule-name">{{ c.type }}</span>
              <span class="rule-detail">{{ c.message }}</span>
            </div>
          </div>
        </t-tab-panel>

        <!-- Tab 4: 检索参考 -->
        <t-tab-panel value="reference" label="检索参考">
          <div v-if="refLoading" class="empty-note">
            <t-loading size="small" text="加载参考数据..." />
          </div>
          <template v-else-if="references.length">
            <div class="ref-list">
              <div v-for="ref in references" :key="ref.entity_id" class="ref-item">
                <span class="ref-name">{{ ref.entity_id }}</span>
                <span class="ref-desc">{{ ref.display_name }}</span>
                <span class="ref-sim" :style="simStyle(ref.similarity)">
                  {{ (ref.similarity * 100).toFixed(0) }}%
                </span>
              </div>
            </div>
          </template>
          <div v-else class="empty-note">无相似元数据参考</div>
        </t-tab-panel>

        <!-- Tab 5: 字段补全（仅表类型显示） -->
        <t-tab-panel
          v-if="detail.entity_type === 'table'"
          value="columns"
          label="字段补全"
        >
          <div v-if="columnsLoading" class="empty-note">
            <t-loading size="small" text="加载字段补全数据..." />
          </div>
          <template v-else-if="columns.length">
            <div class="columns-list">
              <div
                v-for="col in columns"
                :key="col.id"
                class="column-item"
              >
                <div class="column-item-top">
                  <span class="column-name">{{ col.entity_id }}</span>
                  <t-tag
                    variant="light"
                    :theme="col.review_status === 'pending_review' ? 'warning' : col.review_status === 'auto_approved' ? 'success' : 'default'"
                    size="small"
                  >
                    {{ col.review_status === 'pending_review' ? '待审核' : col.review_status === 'auto_approved' ? '已自动采纳' : col.review_status === 'rejected' ? '系统拒绝' : col.review_status }}
                  </t-tag>
                </div>
                <div class="column-item-body">
                  <div class="column-field">
                    <span class="column-field-label">建议中文名</span>
                    <span class="column-field-value">{{ col.completion_result?.display_name || '—' }}</span>
                  </div>
                  <div class="column-field">
                    <span class="column-field-label">描述</span>
                    <span class="column-field-value muted">{{ col.completion_result?.description || '—' }}</span>
                  </div>
                  <div class="column-field">
                    <span class="column-field-label">置信度</span>
                    <span class="column-field-value mono" :style="{ color: col.completion_result?.confidence != null ? (col.completion_result.confidence >= 0.8 ? 'var(--td-success-color)' : col.completion_result.confidence >= 0.6 ? 'var(--td-warning-color)' : 'var(--td-error-color)') : 'var(--td-text-color-placeholder)' }">
                      {{ col.completion_result?.confidence != null ? (col.completion_result.confidence * 100).toFixed(0) + '%' : '—' }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="empty-note">暂无字段补全记录</div>
        </t-tab-panel>
      </t-tabs>

      <!-- Footer Actions -->
      <div class="detail-footer">
        <template v-if="isPending">
          <t-button theme="danger" variant="outline" @click="handleRejectClick">
            驳回
          </t-button>
          <t-button
            theme="default"
            variant="outline"
            :disabled="!modified"
            @click="handleModify"
          >
            确认修改
          </t-button>
          <t-button theme="primary" @click="handleApproveClick">
            确认采纳
          </t-button>
        </template>
        <span v-else class="muted-text">
          该记录已{{ statusLabel }}，不可操作
        </span>
      </div>
    </div>

    <!-- Reject Dialog -->
    <t-dialog
      v-model:visible="rejectVisible"
      header="驳回补全建议"
      attach="body"
      :on-confirm="doReject"
      :confirm-btn="{ content: '确认驳回', theme: 'danger' }"
    >
      <p class="dialog-desc">请填写驳回原因（必填）：</p>
      <t-textarea
        v-model="rejectReason"
        placeholder="请说明驳回原因，例如：业务语义不符、中文名不准确、描述与实际用途不一致..."
        :autosize="{ minRows: 3, maxRows: 6 }"
      />
      <p v-if="rejectError" class="field-error">请填写驳回原因</p>
    </t-dialog>

    <!-- Approve Confirm Dialog -->
    <t-dialog
      v-model:visible="approveVisible"
      header="确认采纳补全建议"
      attach="body"
      :on-confirm="doApprove"
    >
      <p>确认采纳「{{ detail.entity_id }}」的 AI 补全建议？将回写至 OpenMetadata。</p>
    </t-dialog>
  </t-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { approveReview, rejectReview, modifyReview, getReviewReferences, getRecordColumns } from '../api'
import type { ReviewDetail as ReviewDetailType, ReferenceItem, ReviewRecord } from '../api/types'

const props = defineProps<{
  visible: boolean
  detail: ReviewDetailType | null
}>()

const emit = defineEmits<{
  close: []
  refresh: []
}>()

// Tab state
const activeTab = ref('info')

// Edit state
const editDisplayName = ref('')
const editDesc = ref('')
const editTags = ref('')
const modified = ref(false)

// Dialog state
const rejectVisible = ref(false)
const approveVisible = ref(false)
const rejectReason = ref('')
const rejectError = ref(false)

// Reference state
const references = ref<ReferenceItem[]>([])
const refLoading = ref(false)

// Columns state
const columns = ref<ReviewRecord[]>([])
const columnsLoading = ref(false)
const columnsLoaded = ref(false)

function simStyle(similarity: number) {
  const hue = similarity >= 0.8 ? 145 : similarity >= 0.65 ? 75 : 250
  const sat = similarity >= 0.65 ? '60%' : '30%'
  return { color: `oklch(62% 0.18 ${hue})` }
}

async function loadReferences() {
  if (!props.detail?.id || references.value.length) return
  refLoading.value = true
  try {
    const res = await getReviewReferences(props.detail.id)
    if (res.success) references.value = res.data
  } catch { /* mute */ }
  finally { refLoading.value = false }
}

async function loadColumns() {
  if (!props.detail?.id || props.detail.entity_type !== 'table' || columnsLoaded.value) return
  columnsLoading.value = true
  try {
    const res = await getRecordColumns(props.detail.id)
    if (res.success) columns.value = res.data
  } catch { /* mute */ }
  finally { columnsLoading.value = false; columnsLoaded.value = true }
}

// Init edit fields when detail loads
watch(
  () => props.detail,
  (d) => {
    if (d?.completion_result) {
      editDisplayName.value = d.completion_result.display_name || ''
      editDesc.value = d.completion_result.description || ''
      editTags.value = (d.completion_result.tags || []).join(', ')
      modified.value = false
    }
    references.value = []
    columns.value = []
    columnsLoaded.value = false
    activeTab.value = 'info'
    if (d?.id) loadReferences()
  },
  { immediate: true },
)

watch(activeTab, (tab) => {
  if (tab === 'columns') loadColumns()
})

// Computed labels
const isPending = computed(() => props.detail?.review_status === 'pending_review')

const entityTypeLabel = computed(() => {
  const t = props.detail?.entity_type
  if (t === 'column') return '字段'
  if (t === 'view') return '视图'
  return '表'
})

const statusLabels: Record<string, string> = {
  pending_review: '待审核',
  auto_approved: '已自动采纳',
  approved: '已确认',
  human_rejected: '已驳回',
  rejected: '系统拒绝',
  modified: '已修改',
}
const statusLabel = computed(() => statusLabels[props.detail?.review_status || ''] || '—')

const statusThemes: Record<string, string> = {
  auto_approved: 'success',
  approved: 'primary',
  pending_review: 'warning',
  human_rejected: 'default',
  rejected: 'danger',
  modified: 'primary',
}
const statusTheme = computed(() => statusThemes[props.detail?.review_status || ''] || 'default')

const confPercent = computed(() =>
  ((props.detail?.completion_result?.confidence || 0) * 100).toFixed(0),
)

const confColor = computed(() => {
  const c = props.detail?.completion_result?.confidence || 0
  if (c >= 0.8) return 'var(--td-success-color)'
  if (c >= 0.6) return 'var(--td-warning-color)'
  return 'var(--td-error-color)'
})

// Quality stats
const passCount = computed(() =>
  props.detail?.quality_check?.rule_violations?.filter(v => v.severity === 'info').length || 0,
)
const warnCount = computed(() =>
  props.detail?.quality_check?.rule_violations?.filter(v => v.severity === 'warning').length || 0,
)
const failCount = computed(() =>
  props.detail?.quality_check?.rule_violations?.filter(v => v.severity === 'critical').length || 0,
)

function dotClass(severity: string): string {
  const map: Record<string, string> = { critical: 'fail', warning: 'warn', info: 'pass' }
  return map[severity] || 'pass'
}

function conflictDotClass(severity: string): string {
  return severity === 'critical' ? 'fail' : 'warn'
}

// Edit detection
function onEdit() {
  const r = props.detail?.completion_result
  if (!r) {
    modified.value = false
    return
  }
  modified.value =
    editDisplayName.value !== r.display_name ||
    editDesc.value !== r.description ||
    editTags.value !== (r.tags || []).join(', ')
}

// Action handlers
function handleApproveClick() {
  approveVisible.value = true
}

function handleRejectClick() {
  rejectReason.value = ''
  rejectError.value = false
  rejectVisible.value = true
}

async function doApprove() {
  if (!props.detail) return
  try {
    await approveReview(props.detail.id)
    MessagePlugin.success('已确认采纳')
    emit('refresh')
  } catch {
    MessagePlugin.error('操作失败')
  }
}

async function doReject() {
  if (!rejectReason.value.trim()) {
    rejectError.value = true
    return
  }
  if (!props.detail) return
  try {
    await rejectReview(props.detail.id, rejectReason.value)
    MessagePlugin.success('已驳回')
    rejectVisible.value = false
    emit('refresh')
  } catch {
    MessagePlugin.error('操作失败')
  }
}

async function handleModify() {
  if (!props.detail || !modified.value) return
  try {
    await modifyReview(props.detail.id, {
      display_name: editDisplayName.value,
      description: editDesc.value,
      tags: editTags.value
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
    })
    MessagePlugin.success('已保存修改')
    emit('refresh')
  } catch {
    MessagePlugin.error('保存失败')
  }
}
</script>

<style scoped>
.review-detail {
  padding: 4px 0;
}

/* Entity Header */
.detail-header-info {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--td-border-level-2-color, #e7e7e7);
}

.entity-name {
  font-family: 'JetBrains Mono', 'SF Mono', ui-monospace, monospace;
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 2px;
  color: var(--td-text-color-primary);
}

.entity-subtitle {
  font-size: 13px;
  color: var(--td-text-color-placeholder);
  font-family: 'JetBrains Mono', 'SF Mono', ui-monospace, monospace;
  margin-bottom: 8px;
}

.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* Section titles */
.section-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--td-text-color-placeholder);
  margin: 20px 0 10px;
}

.section-title:first-child {
  margin-top: 4px;
}

.quality-summary {
  font-weight: 400;
  text-transform: none;
  letter-spacing: normal;
  color: var(--td-text-color-secondary);
}

/* Detail list (bordered rows) */
.detail-list {
  border: 1px solid var(--td-border-level-2-color, #e7e7e7);
  border-radius: 8px;
  overflow: hidden;
}

.detail-row {
  display: flex;
  padding: 10px 16px;
  border-bottom: 1px solid var(--td-border-level-2-color, #e7e7e7);
  font-size: 14px;
  align-items: baseline;
  background: var(--td-bg-color-container);
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  width: 90px;
  color: var(--td-text-color-placeholder);
  flex-shrink: 0;
  font-size: 13px;
}

.detail-value {
  flex: 1;
  font-size: 14px;
  color: var(--td-text-color-primary);
  font-weight: 500;
  word-break: break-word;
}

/* Compare grid */
.compare-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 4px;
}

.compare-card {
  border: 1px solid var(--td-border-level-2-color, #e7e7e7);
  border-radius: 8px;
  padding: 16px;
  background: var(--td-bg-color-page);
}

.compare-card.ai-card {
  border-color: var(--td-brand-color);
}

.compare-card-title {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--td-text-color-placeholder);
}

.compare-card.ai-card .compare-card-title {
  color: var(--td-brand-color);
}

.field {
  margin-bottom: 10px;
}

.field:last-child {
  margin-bottom: 0;
}

.field-label {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
  margin-bottom: 2px;
}

.field-value {
  font-size: 14px;
  color: var(--td-text-color-primary);
}

/* Quality rules */
.quality-section {
  margin-top: 8px;
}

.conflicts-section {
  margin-top: 20px;
}

.quality-rule {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
}

.quality-rule .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.quality-rule .dot.pass {
  background: var(--td-success-color);
}

.quality-rule .dot.warn {
  background: var(--td-warning-color);
}

.quality-rule .dot.fail {
  background: var(--td-error-color);
}

.rule-name {
  font-weight: 500;
  color: var(--td-text-color-primary);
  min-width: 90px;
}

.rule-detail {
  color: var(--td-text-color-placeholder);
  margin-left: auto;
  font-size: 12px;
  text-align: right;
}

/* Footer */
.detail-footer {
  border-top: 1px solid var(--td-border-level-2-color, #e7e7e7);
  padding: 16px 0 0;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 24px;
}

.muted-text {
  font-size: 13px;
  color: var(--td-text-color-placeholder);
  padding: 8px 0;
}

/* Utilities */
.mono {
  font-family: 'JetBrains Mono', 'SF Mono', ui-monospace, monospace;
  font-size: 13px;
}

.bold {
  font-weight: 700;
}

.muted {
  color: var(--td-text-color-placeholder);
}

.reasoning {
  font-size: 12px;
  line-height: 1.6;
}

.empty-note {
  padding: 24px 0;
  color: var(--td-text-color-placeholder);
  font-size: 13px;
  text-align: center;
}

/* Reference list */
.ref-list {
  border: 1px solid var(--td-border-level-2-color, #e7e7e7);
  border-radius: 8px;
  overflow: hidden;
}

.ref-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--td-border-level-2-color, #e7e7e7);
  font-size: 13px;
  background: var(--td-bg-color-container);
}

.ref-item:last-child {
  border-bottom: none;
}

.ref-item .ref-name {
  font-family: 'JetBrains Mono', 'SF Mono', ui-monospace, monospace;
  font-weight: 600;
  min-width: 140px;
  font-size: 12px;
}

.ref-item .ref-desc {
  color: var(--td-text-color-placeholder);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ref-item .ref-sim {
  font-family: 'JetBrains Mono', 'SF Mono', ui-monospace, monospace;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

/* Dialog content */
.dialog-desc {
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--td-text-color-secondary);
}

.field-error {
  font-size: 12px;
  color: var(--td-error-color);
  margin-top: 8px;
}

/* Columns list */
.columns-list {
  border: 1px solid var(--td-border-level-2-color, #e7e7e7);
  border-radius: 8px;
  overflow: hidden;
}

.column-item {
  padding: 12px 16px;
  border-bottom: 1px solid var(--td-border-level-2-color, #e7e7e7);
  background: var(--td-bg-color-container);
}

.column-item:last-child {
  border-bottom: none;
}

.column-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.column-name {
  font-family: 'JetBrains Mono', 'SF Mono', ui-monospace, monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--td-text-color-primary);
}

.column-item-body {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.column-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.column-field-label {
  font-size: 11px;
  color: var(--td-text-color-placeholder);
}

.column-field-value {
  font-size: 13px;
  color: var(--td-text-color-primary);
}

.column-field-value.muted {
  color: var(--td-text-color-placeholder);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Responsive */
@media (max-width: 768px) {
  .compare-grid {
    grid-template-columns: 1fr;
  }

  .detail-footer {
    flex-wrap: wrap;
  }

  .detail-row {
    flex-direction: column;
    gap: 2px;
  }

  .detail-label {
    width: 100%;
  }

  .rule-detail {
    display: none;
  }
}
</style>
