<template>
  <t-dialog
    :visible="visible"
    header="资产详情"
    attach="body"
    :z-index="2600"
    width="900px"
    :footer="false"
    @close="emit('update:visible', false)"
  >
    <div class="detail-dialog">
      <template v-if="error">
        <div class="error-state">
          <t-icon name="error-circle" size="48px" />
          <h2>{{ error }}</h2>
        </div>
      </template>
      <template v-else-if="loading">
        <div class="loading-state">
          <t-loading size="large" />
          <p>加载中...</p>
        </div>
      </template>
      <template v-else-if="asset">
        <div class="top-zone">
          <h1 class="asset-name">{{ asset.table_name || asset.column_name || '...' }}</h1>
          <p class="asset-subtitle">{{ entityTypeLabel }} · {{ asset.database }}.{{ asset.schema_name }}</p>
          <p class="asset-desc">{{ asset.description || '暂无描述' }}</p>
          <div class="badge-row">
            <t-tag variant="light" theme="default">{{ entityTypeLabel }}</t-tag>
            <t-tag variant="light" :theme="statusTheme">{{ statusLabel }}</t-tag>
          </div>
        </div>

        <div class="bottom-zone">
          <t-tabs v-model="activeTab">
            <t-tab-panel value="info" label="基本信息">
              <div class="detail-list">
                <div class="detail-row"><span class="detail-label">名称</span><span class="detail-value mono">{{ asset.table_name || asset.column_name }}</span></div>
                <div class="detail-row"><span class="detail-label">类型</span><span class="detail-value"><t-tag variant="light" theme="default">{{ entityTypeLabel }}</t-tag></span></div>
                <div class="detail-row"><span class="detail-label">描述</span><span class="detail-value">{{ asset.description || '—' }}</span></div>
                <div class="detail-row"><span class="detail-label">所属库</span><span class="detail-value mono">{{ asset.database || '—' }}</span></div>
                <div class="detail-row"><span class="detail-label">数据库类型</span><span class="detail-value">{{ asset.db_type || '—' }}</span></div>
                <div class="detail-row"><span class="detail-label">Schema</span><span class="detail-value mono">{{ asset.schema_name || '—' }}</span></div>
                <div class="detail-row"><span class="detail-label">所属系统</span><span class="detail-value">{{ asset.system || '—' }}</span></div>
                <div class="detail-row">
                  <span class="detail-label">标签</span>
                  <span class="detail-value">
                    <t-tag v-for="tag in asset.tags" :key="tag" variant="light" theme="default" style="margin-right:4px">{{ tag }}</t-tag>
                    <span v-if="!asset.tags?.length">—</span>
                  </span>
                </div>
              </div>
            </t-tab-panel>

            <t-tab-panel value="columns" label="列信息">
              <div v-if="columns.length > 0">
                <p class="section-title">列信息 ({{ columns.length }} 列)</p>
                <t-table :data="columns" :columns="columnTableDefs" row-key="column_id" bordered stripe size="small" table-layout="fixed">
                  <template #original_tags="{ row }">
                    <t-tag v-for="tag in row.original_tags" :key="tag" variant="light" theme="default" size="small" style="margin-right:2px">{{ tag }}</t-tag>
                    <span v-if="!row.original_tags?.length">—</span>
                  </template>
                  <template #completion_tags="{ row }">
                    <t-tag v-for="tag in row.completion_tags" :key="tag" variant="light" theme="primary" size="small" style="margin-right:2px">{{ tag }}</t-tag>
                    <span v-if="!row.completion_tags?.length">—</span>
                  </template>
                  <template #completion_time="{ row }">
                    <span class="cell-mono">{{ formatTime(row.completion_time) }}</span>
                  </template>
                </t-table>
              </div>
              <div v-else class="empty-state">
                <p>暂无列信息</p>
              </div>
            </t-tab-panel>
          </t-tabs>
        </div>
      </template>
    </div>
  </t-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { getAssetDetail } from '../api'
import type { AssetDetail, ColumnInfo } from '../api/types'

const props = defineProps<{
  visible: boolean
  entityId: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const asset = ref<AssetDetail | null>(null)
const columns = ref<ColumnInfo[]>([])
const error = ref('')
const loading = ref(false)
const activeTab = ref('info')

const entityTypeLabel = computed(() => {
  if (!asset.value) return ''
  if (asset.value.entity_type === 'view') return '视图'
  return '表'
})
const statusLabel = computed(() => asset.value?.has_description ? '已补全' : '待补全')
const statusTheme = computed(() => asset.value?.has_description ? 'success' : 'warning')

function formatTime(iso: string | undefined | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

const columnTableDefs = [
  { colKey: 'column_name', title: '列名', width: 150, ellipsis: true },
  { colKey: 'data_type', title: '数据类型', width: 90, ellipsis: true },
  { colKey: 'original_description', title: '原始描述', ellipsis: true, width: 140 },
  { colKey: 'original_tags', title: '原始标签', width: 100 },
  { colKey: 'completion_description', title: '补全描述', ellipsis: true, width: 160 },
  { colKey: 'completion_tags', title: '补全标签', width: 100 },
  { colKey: 'completion_time', title: '补全时间', width: 140 },
]

async function loadDetail(id: string) {
  if (!id) return
  loading.value = true
  error.value = ''
  asset.value = null
  columns.value = []
  activeTab.value = 'info'
  try {
    const resp = await getAssetDetail(id)
    if (!resp.success || !resp.data) { error.value = '未找到该资产'; return }
    asset.value = resp.data
    columns.value = resp.data.columns || []
  } catch {
    error.value = '加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

watch(() => props.entityId, (id) => {
  if (id) loadDetail(id)
})

watch(() => props.visible, (v) => {
  if (v && props.entityId) loadDetail(props.entityId)
})
</script>

<style scoped>
.detail-dialog {
  max-height: 70vh;
  overflow-y: auto;
  padding: 0 4px;
}
.top-zone {
  padding: 0 0 12px;
  border-bottom: 1px solid var(--td-border-level-2-color, #e7e7e7);
  margin-bottom: 8px;
}
.asset-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 2px;
}
.asset-subtitle {
  font-size: 13px;
  color: var(--td-text-color-placeholder);
  font-family: monospace;
  margin: 0 0 6px;
}
.asset-desc {
  font-size: 14px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0 0 8px;
}
.badge-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.bottom-zone {
  padding-top: 4px;
}
.detail-list {
  border: 1px solid var(--td-border-level-2-color, #e7e7e7);
  border-radius: 10px;
  overflow: hidden;
}
.detail-row {
  display: flex;
  padding: 10px 16px;
  border-bottom: 1px solid var(--td-border-level-2-color, #e7e7e7);
  font-size: 14px;
  align-items: baseline;
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
}
.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
}
.section-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--td-text-color-placeholder);
  margin: 0 0 10px;
}
.empty-state, .error-state {
  text-align: center;
  padding: 48px 16px;
  color: var(--td-text-color-placeholder);
}
.error-state h2 {
  font-size: 18px;
  margin: 8px 0 0;
}

.cell-mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}

/* Compact column table */
:deep(.t-table__body td) {
  padding: 5px 8px !important;
  font-size: 12px;
}

:deep(.t-table__header th) {
  padding: 6px 8px !important;
  font-size: 11px;
}
</style>
