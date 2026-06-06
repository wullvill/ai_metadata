<template>
  <div class="asset-detail">
    <template v-if="error">
      <div class="error-state">
        <t-icon name="error-circle" size="48px" />
        <h2>{{ error }}</h2>
        <router-link to="/search"><t-button theme="default">← 返回资产目录</t-button></router-link>
      </div>
    </template>
    <template v-else>
      <div class="top-zone">
        <div class="breadcrumb">
          <router-link to="/search">资产目录</router-link> / {{ asset?.table_name || '...' }}
        </div>
        <h1 class="asset-name">{{ asset?.table_name || asset?.column_name || '...' }}</h1>
        <p class="asset-subtitle">{{ entityTypeLabel }} · {{ asset?.database }}.{{ asset?.schema_name }}</p>
        <p class="asset-desc">{{ asset?.description || '暂无描述' }}</p>
        <div class="badge-row">
          <t-tag variant="light" theme="default">{{ entityTypeLabel }}</t-tag>
          <t-tag variant="light" :theme="statusTheme">{{ statusLabel }}</t-tag>
        </div>
      </div>

      <div class="bottom-zone">
        <t-tabs v-model="activeTab">
          <t-tab-panel value="info" label="基本信息">
            <div class="detail-list">
              <div class="detail-row"><span class="detail-label">名称</span><span class="detail-value mono">{{ asset?.table_name || asset?.column_name }}</span></div>
              <div class="detail-row"><span class="detail-label">类型</span><span class="detail-value"><t-tag variant="light" theme="default">{{ entityTypeLabel }}</t-tag></span></div>
              <div class="detail-row"><span class="detail-label">描述</span><span class="detail-value">{{ asset?.description || '—' }}</span></div>
              <div class="detail-row"><span class="detail-label">所属库</span><span class="detail-value mono">{{ asset?.database || '—' }}</span></div>
              <div class="detail-row"><span class="detail-label">Schema</span><span class="detail-value mono">{{ asset?.schema_name || '—' }}</span></div>
              <div class="detail-row"><span class="detail-label">所属系统</span><span class="detail-value">{{ asset?.system || '—' }}</span></div>

              <div class="detail-row"><span class="detail-label">标签</span><span class="detail-value">
                <t-tag v-for="tag in asset?.tags" :key="tag" variant="light" theme="default" style="margin-right:4px">{{ tag }}</t-tag>
                <span v-if="!asset?.tags?.length">—</span>
              </span></div>
            </div>
          </t-tab-panel>

          <t-tab-panel value="columns" label="列信息">
            <div v-if="columns.length > 0">
              <p class="section-title">列信息 ({{ columns.length }} 列)</p>
              <t-table :data="columns" :columns="columnTableDefs" row-key="column_id" bordered stripe size="small">
                <template #original_tags="{ row }">
                  <t-tag v-for="tag in row.original_tags" :key="tag" variant="light" theme="default" size="small" style="margin-right:2px">
                    {{ tag }}
                  </t-tag>
                  <span v-if="!row.original_tags?.length">—</span>
                </template>
                <template #completion_tags="{ row }">
                  <t-tag v-for="tag in row.completion_tags" :key="tag" variant="light" theme="primary" size="small" style="margin-right:2px">
                    {{ tag }}
                  </t-tag>
                  <span v-if="!row.completion_tags?.length">—</span>
                </template>
                <template #completion_time="{ row }">
                  <span v-if="row.completion_time">{{ row.completion_time }}</span>
                  <span v-else>—</span>
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
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getAssetDetail } from '../api'
import type { AssetDetail, ColumnInfo } from '../api/types'

const route = useRoute()
const asset = ref<AssetDetail | null>(null)
const columns = ref<ColumnInfo[]>([])
const error = ref('')
const activeTab = ref('info')

const entityTypeLabel = computed(() => {
  if (!asset.value) return ''
  if (asset.value.entity_type === 'view') return '视图'
  return '表'
})
const statusLabel = computed(() => asset.value?.has_description ? '已补全' : '待补全')
const statusTheme = computed(() => asset.value?.has_description ? 'success' : 'warning')

const columnTableDefs = [
  { colKey: 'column_name', title: '列名', width: 180 },
  { colKey: 'data_type', title: '数据类型', width: 130 },
  { colKey: 'original_description', title: '原始描述', ellipsis: true, width: 160 },
  { colKey: 'original_tags', title: '原始标签', width: 120 },
  { colKey: 'completion_description', title: '补全描述', ellipsis: true, width: 180 },
  { colKey: 'completion_tags', title: '补全标签', width: 120 },
  { colKey: 'completion_time', title: '补全时间', width: 150 },
]

onMounted(async () => {
  const id = route.params.id as string
  if (!id) { error.value = '缺少资产标识'; return }
  try {
    const resp = await getAssetDetail(id)
    if (!resp.success || !resp.data) { error.value = '未找到该资产'; return }
    asset.value = resp.data
    columns.value = resp.data.columns || []
  } catch {
    error.value = '加载失败，请稍后重试'
  }
})
</script>

<style scoped>
.asset-detail { max-width: 960px; margin: 0 auto; padding: 20px 24px 32px; }
.top-zone { padding: 0 0 16px; border-bottom: 1px solid var(--td-border-level-2-color, #e7e7e7); }
.breadcrumb { font-size: 12px; color: var(--td-text-color-placeholder); margin-bottom: 4px; }
.breadcrumb a { color: var(--td-brand-color); text-decoration: none; }
.asset-name { font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; margin: 0 0 4px; }
.asset-subtitle { font-size: 13px; color: var(--td-text-color-placeholder); font-family: monospace; margin-bottom: 8px; }
.asset-desc { font-size: 14px; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 10px; }
.badge-row { display: flex; gap: 6px; flex-wrap: wrap; }
.bottom-zone { padding-top: 12px; }
.detail-list { border: 1px solid var(--td-border-level-2-color, #e7e7e7); border-radius: 10px; overflow: hidden; }
.detail-row { display: flex; padding: 12px 20px; border-bottom: 1px solid var(--td-border-level-2-color, #e7e7e7); font-size: 14px; align-items: baseline; }
.detail-row:last-child { border-bottom: none; }
.detail-label { width: 100px; color: var(--td-text-color-placeholder); flex-shrink: 0; font-size: 13px; }
.detail-value { flex: 1; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.section-title { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: var(--td-text-color-placeholder); margin-bottom: 12px; margin-top: 16px; }
.empty-state, .error-state { text-align: center; padding: 64px 24px; color: var(--td-text-color-placeholder); }
.error-state h2 { font-size: 20px; margin: 8px 0 16px; }
</style>
