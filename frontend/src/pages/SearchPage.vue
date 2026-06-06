<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import type { TableProps, SortInfo } from 'tdesign-vue-next'
import { useSearch } from '../composables/useSearch'
import { useCompletion } from '../composables/useCompletion'
import { getFilterOptions } from '../api'
import type { MetadataEntity, TargetEntity, FilterOptions } from '../api/types'

// ── Local extended type for fields the backend may return ──
interface AssetDisplay extends MetadataEntity {
  system?: string
  business_domain?: string
  classification?: string
  completion_status?: 'pending' | 'processing' | 'completed'
  updated_time?: string
  owner?: string
}

// ── Composables ──
const {
  results,
  total,
  loading,
  error,
  filters,
  pagination,
  search,
} = useSearch()

const {
  completing,
  triggerComplete,
  clearResult,
} = useCompletion()

const router = useRouter()

// ── Local filter state (client-side) ──
const localFilters = reactive({
  system: '',
  database: '',
  schema: '',
  type: '',
  businessDomain: '',
  completion: '',
})

// ── Sort state ──
const sortState = reactive<SortInfo>({
  sortBy: '',
  descending: false,
})

// ── Sort accessor map ──
const SORT_ACCESSORS: Record<string, (row: AssetDisplay) => string> = {
  name: (r) => (r.table_name || r.entity_id),
  system: (r) => r.system || r.database || '',
  entity_type: (r) => r.entity_type,
  database: (r) => r.database,
  schema: (r) => r.schema,
  business_domain: (r) => r.business_domain || '',
  classification: (r) => r.classification || '',
  completion_status: (r) => r.completion_status || (r.has_description ? 'completed' : 'pending'),
  updated_time: (r) => r.updated_time || '',
}

// ── Selection state ──
const selectedRowKeys = ref<string[]>([])

// ── Dialog state ──
const confirmVisible = ref(false)
const pendingCompleteEntity = ref<AssetDisplay | null>(null)
const domainPopupVisible = ref(false)

// ── Filter option chips ──
const TYPE_OPTIONS = [
  { label: '全部类型', value: '' },
  { label: '表', value: 'table' },
  { label: '视图', value: 'view' },
  { label: '字段', value: 'column' },
]

const COMPLETION_OPTIONS = [
  { label: '全部', value: '' },
  { label: '待补全', value: 'pending' },
  { label: '处理中', value: 'processing' },
  { label: '已完成', value: 'completed' },
]

	// API-loaded filter options
	const apiFilterOpts = ref<FilterOptions>({ systems: [], databases: [], schemas: [] })

// ── Derived filter options from results ──
const resultsAsDisplay = computed(() => results.value as AssetDisplay[])

const systemOptions = computed(() => apiFilterOpts.value.systems.length ? apiFilterOpts.value.systems : [])
const databaseOptions = computed(() => apiFilterOpts.value.databases.length ? apiFilterOpts.value.databases : [])
const schemaOptions = computed(() => apiFilterOpts.value.schemas.length ? apiFilterOpts.value.schemas : [])

const allDomainOptions = computed(() => {
  const set = new Set<string>()
  results.value.forEach(r => {
    const d = (r as AssetDisplay).business_domain
    if (d) set.add(d)
  })
  return Array.from(set).sort()
})

const VISIBLE_DOMAIN_COUNT = 5
const visibleDomains = computed(() => allDomainOptions.value.slice(0, VISIBLE_DOMAIN_COUNT))
const hiddenDomains = computed(() => allDomainOptions.value.slice(VISIBLE_DOMAIN_COUNT))
const showDomainExpand = computed(() => allDomainOptions.value.length > VISIBLE_DOMAIN_COUNT)

// ── Client-side filtering ──
const filteredResults = computed(() => {
  let list = resultsAsDisplay.value

  if (localFilters.system) {
    list = list.filter(r => (r.system || r.database) === localFilters.system)
  }
  if (localFilters.database) {
    list = list.filter(r => r.database === localFilters.database)
  }
  if (localFilters.schema) {
    list = list.filter(r => r.schema === localFilters.schema)
  }
  if (localFilters.type) {
    list = list.filter(r => r.entity_type === localFilters.type)
  }
  if (localFilters.businessDomain) {
    list = list.filter(r => r.business_domain === localFilters.businessDomain)
  }
  if (localFilters.completion) {
    list = list.filter(r => {
      const status = r.completion_status || (r.has_description ? 'completed' : 'pending')
      return status === localFilters.completion
    })
  }

  // Sort
  if (sortState.sortBy) {
    const accessor = SORT_ACCESSORS[sortState.sortBy]
    if (accessor) {
      const desc = sortState.descending
      list = [...list].sort((a, b) => {
        let va = accessor(a)
        let vb = accessor(b)
        va = typeof va === 'string' ? va.toLowerCase() : va
        vb = typeof vb === 'string' ? vb.toLowerCase() : vb
        if (va < vb) return desc ? 1 : -1
        if (va > vb) return desc ? -1 : 1
        return 0
      })
    }
  }

  return list
})

const filteredTotal = computed(() => filteredResults.value.length)

// ── Color / label helpers ──
function domainTheme(domain: string): 'primary' | 'warning' | 'success' | 'default' {
  const map: Record<string, 'primary' | 'warning' | 'success' | 'default'> = {
    '交易': 'primary', '客户': 'primary',
    '风控': 'warning', '合规': 'warning',
    '清算': 'success', '财务': 'success', '行情': 'success',
    '产品': 'default', '公共': 'default',
  }
  return map[domain] || 'default'
}

function classificationTheme(cls: string): 'primary' | 'warning' | 'success' | 'default' {
  const map: Record<string, 'primary' | 'warning' | 'success' | 'default'> = {
    '机密': 'warning', '内部': 'primary', '公开': 'success',
  }
  return map[cls] || 'default'
}

function completionTheme(status: string): 'warning' | 'primary' | 'success' | 'default' {
  const map: Record<string, 'warning' | 'primary' | 'success' | 'default'> = {
    pending: 'warning', processing: 'primary', completed: 'success',
  }
  return map[status] || 'default'
}

function completionLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '待补全', processing: '处理中', completed: '已完成',
  }
  return map[status] || status
}

function typeLabel(entityType: string): string {
  const map: Record<string, string> = {
    table: '表', column: '字段', view: '视图',
  }
  return map[entityType] || entityType
}

// ── Asset helpers ──
function assetName(entity: AssetDisplay): string {
  return entity.table_name || entity.entity_id
}

function completionStatus(entity: AssetDisplay): string {
  return entity.completion_status || (entity.has_description ? 'completed' : 'pending')
}

// ── Navigation ──
function openAssetDetail(entity: AssetDisplay) {
  const route = router.resolve({ name: 'asset-detail', params: { id: entity.entity_id } })
  window.open(route.href, '_blank')
}

// ── Completion handlers ──
function handleSingleComplete(entity: AssetDisplay) {
  pendingCompleteEntity.value = entity
  confirmVisible.value = true
}

async function confirmCompletion() {
  if (!pendingCompleteEntity.value || completing.value) return
  const entity = pendingCompleteEntity.value

  const target: TargetEntity = {
    entity_id: entity.entity_id,
    entity_type: entity.entity_type as 'table' | 'column',
    database: entity.database,
    schema: entity.schema,
    table_name: entity.table_name,
    column_name: entity.column_name,
    data_type: entity.data_type,
    current_description: entity.description ?? null,
    current_display_name: entity.display_name ?? null,
    current_tags: entity.tags ?? null,
    table_description: null,
    columns: null,
  }

  try {
    await triggerComplete(target)
    MessagePlugin.success('补全申请已提交')
  } catch {
    MessagePlugin.error('补全申请失败')
  }

  confirmVisible.value = false
  pendingCompleteEntity.value = null
}

function cancelCompletion() {
  confirmVisible.value = false
  pendingCompleteEntity.value = null
}

function batchApplyCompletion() {
  if (selectedRowKeys.value.length === 0) return
  MessagePlugin.info(`已为 ${selectedRowKeys.value.length} 项资产提交补全申请`)
  selectedRowKeys.value = []
}

const batchDisabled = computed(() => selectedRowKeys.value.length === 0)

// ── Sort handler ──
function handleSortChange(sort: TableProps['sort']) {
  if (!sort || !sort.sortBy) {
    sortState.sortBy = ''
    sortState.descending = false
    return
  }
  // TDesign sort can be SortInfo or SortInfo[]
  const s = Array.isArray(sort) ? sort[0] : sort
  sortState.sortBy = s.sortBy as string
  sortState.descending = s.descending
}

// ── Search handler ──
async function handleSearch() {
  clearResult()
  selectedRowKeys.value = []
  await search()
}

// ── Filter changes ──
function setTypeFilter(value: string) {
  localFilters.type = value
  filters.entity_type = value
  search()
}

function setCompletionFilter(value: string) {
  localFilters.completion = value
  selectedRowKeys.value = []
}

function setDomainFilter(value: string) {
  localFilters.businessDomain = value
}

// ── Table columns definition ──
const columns: TableProps['columns'] = [
  { colKey: 'row-select', type: 'multiple', width: 40 },
  { colKey: 'name', title: '资产名称', sorter: true, width: 180 },
  { colKey: 'description', title: '描述', ellipsis: true, width: 200 },
  { colKey: 'system', title: '所属系统', sorter: true, width: 120 },
  { colKey: 'entity_type', title: '类型', sorter: true, width: 80 },
  { colKey: 'database', title: '所属库', sorter: true, width: 130 },
  { colKey: 'schema', title: 'Schema', sorter: true, width: 100 },
  { colKey: 'business_domain', title: '业务域', sorter: true, width: 100 },
  { colKey: 'classification', title: '分类', sorter: true, width: 80 },
  { colKey: 'completion_status', title: '补全状态', sorter: true, width: 100 },
  { colKey: 'updated_time', title: '更新时间', sorter: true, width: 150 },
  { colKey: 'actions', title: '操作', width: 180 },
]

// ── Select handler ──
function handleSelectChange(keys: (string | number)[]) {
  selectedRowKeys.value = keys as string[]
}

// ── Page change ──
function handlePageChange(pageInfo: { current: number }) {
  pagination.page = pageInfo.current
  search()
}

// ── Watchers: instant search (no debounce) ──
watch(() => filters.query, () => {
  search()
})

// ── Init: load filter options and trigger initial search ──
onMounted(async () => {
  try {
    const res = await getFilterOptions()
    if (res.success)
      apiFilterOpts.value = res.data
  } catch { /* keep defaults */ }
  search()
})
</script>

<template>
  <div class="search-page">
    <!-- Page Header -->
    <div class="page-header">
      <h1>资产目录</h1>
      <p class="page-subtitle">搜索表、字段元数据，申请 AI 智能补全</p>
    </div>

    <!-- Search Section -->
    <section class="search-section">
      <div class="search-bar">
        <div class="search-bar-row">
          <t-icon name="search" size="18px" class="search-icon" />
          <input
            v-model="filters.query"
            type="text"
            class="search-input"
            placeholder="搜索表名、字段、描述、标签..."
            autocomplete="off"
            @keyup.enter="handleSearch"
          />
          <span v-if="total > 0" class="result-count">{{ total }} 个结果</span>
        </div>
        <div class="filter-bar">
          <!-- System dropdown -->
          <div class="filter-select-wrap">
            <select
              v-model="localFilters.system"
              class="filter-select"
              :class="{ active: localFilters.system !== '' }"
            >
              <option value="">全部系统</option>
              <option v-for="opt in systemOptions" :key="opt" :value="opt">{{ opt }}</option>
            </select>
          </div>
          <!-- Database dropdown -->
          <div class="filter-select-wrap">
            <select
              v-model="localFilters.database"
              class="filter-select"
              :class="{ active: localFilters.database !== '' }"
            >
              <option value="">全部库</option>
              <option v-for="opt in databaseOptions" :key="opt" :value="opt">{{ opt }}</option>
            </select>
          </div>
          <!-- Schema dropdown -->
          <div class="filter-select-wrap">
            <select
              v-model="localFilters.schema"
              class="filter-select"
              :class="{ active: localFilters.schema !== '' }"
            >
              <option value="">全部 Schema</option>
              <option v-for="opt in schemaOptions" :key="opt" :value="opt">{{ opt }}</option>
            </select>
          </div>
          <span class="filter-sep" />
          <!-- Type chips -->
          <div class="filter-group">
            <button
              v-for="opt in TYPE_OPTIONS"
              :key="opt.value"
              class="filter-chip"
              :class="{ active: localFilters.type === opt.value }"
              @click="setTypeFilter(opt.value)"
            >
              {{ opt.label }}
            </button>
          </div>
          <span class="filter-sep" />
          <!-- Business domain chips (top 5) -->
          <div class="filter-group">
            <button
              class="filter-chip"
              :class="{ active: localFilters.businessDomain === '' }"
              @click="setDomainFilter('')"
            >
              全部业务域
            </button>
            <button
              v-for="domain in visibleDomains"
              :key="domain"
              class="filter-chip"
              :class="{ active: localFilters.businessDomain === domain }"
              @click="setDomainFilter(domain)"
            >
              {{ domain }}
            </button>
          </div>
          <!-- Domain expand button -->
          <button
            v-if="showDomainExpand"
            class="expand-btn"
            @click="domainPopupVisible = true"
          >
            展开
          </button>
        </div>
      </div>
    </section>

    <!-- Ops Bar -->
    <section class="ops-section">
      <div class="ops-bar">
        <div class="ops-bar-left">
          <span class="ops-count">共 {{ filteredTotal }} 条</span>
          <span class="filter-sep" />
          <!-- Completion status chips -->
          <div class="filter-group">
            <button
              v-for="opt in COMPLETION_OPTIONS"
              :key="opt.value"
              class="filter-chip"
              :class="{ active: localFilters.completion === opt.value }"
              @click="setCompletionFilter(opt.value)"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>
        <div class="ops-bar-right">
          <span v-if="selectedRowKeys.length > 0" class="ops-selected">已选 {{ selectedRowKeys.length }} 项</span>
          <button
            class="ops-batch-btn"
            :disabled="batchDisabled"
            @click="batchApplyCompletion"
          >
            批量申请补全
          </button>
        </div>
      </div>
    </section>

    <!-- Error Alert -->
    <t-alert
      v-if="error"
      theme="error"
      :message="error"
      close
      style="margin-bottom: 16px"
    />

    <!-- Table Section -->
    <section class="table-section">
      <div class="table-wrap">
        <t-table
          :data="filteredResults"
          :columns="columns"
          row-key="entity_id"
          :selected-row-keys="selectedRowKeys"
          :sort="sortState"
          :loading="loading"
          :max-height="560"
          table-layout="auto"
          hover
          stripe
          @sort-change="handleSortChange"
          @select-change="handleSelectChange"
        >
          <!-- Asset Name -->
          <template #name="{ row }">
            <span class="cell-name" @click="openAssetDetail(row as AssetDisplay)">
              {{ assetName(row as AssetDisplay) }}
            </span>
          </template>

          <!-- Description -->
          <template #description="{ row }">
            <span class="cell-desc" :title="(row as AssetDisplay).description || ''">
              {{ (row as AssetDisplay).description || '-' }}
            </span>
          </template>

          <!-- System -->
          <template #system="{ row }">
            <span class="cell-mono">{{ (row as AssetDisplay).system || (row as AssetDisplay).database || '-' }}</span>
          </template>

          <!-- Type -->
          <template #entity_type="{ row }">
            <t-tag theme="default" variant="light" size="small">
              {{ typeLabel((row as AssetDisplay).entity_type) }}
            </t-tag>
          </template>

          <!-- Database -->
          <template #database="{ row }">
            <span class="cell-mono">{{ (row as AssetDisplay).database || '-' }}</span>
          </template>

          <!-- Schema -->
          <template #schema="{ row }">
            <span class="cell-mono">{{ (row as AssetDisplay).schema || '-' }}</span>
          </template>

          <!-- Business Domain -->
          <template #business_domain="{ row }">
            <template v-if="(row as AssetDisplay).business_domain">
              <t-tag
                :theme="domainTheme((row as AssetDisplay).business_domain!)"
                variant="light"
                size="small"
              >
                {{ (row as AssetDisplay).business_domain }}
              </t-tag>
            </template>
            <span v-else class="cell-mono">-</span>
          </template>

          <!-- Classification -->
          <template #classification="{ row }">
            <template v-if="(row as AssetDisplay).classification">
              <t-tag
                :theme="classificationTheme((row as AssetDisplay).classification!)"
                variant="light"
                size="small"
              >
                {{ (row as AssetDisplay).classification }}
              </t-tag>
            </template>
            <span v-else class="cell-mono">-</span>
          </template>

          <!-- Completion Status -->
          <template #completion_status="{ row }">
            <t-tag
              :theme="completionTheme(completionStatus(row as AssetDisplay))"
              variant="light"
              size="small"
            >
              {{ completionLabel(completionStatus(row as AssetDisplay)) }}
            </t-tag>
          </template>

          <!-- Updated Time -->
          <template #updated_time="{ row }">
            <span class="cell-mono">{{ (row as AssetDisplay).updated_time || '-' }}</span>
          </template>

          <!-- Actions -->
          <template #actions="{ row }">
            <div class="action-btns">
              <t-button
                theme="default"
                variant="outline"
                size="small"
                @click="openAssetDetail(row as AssetDisplay)"
              >
                详情
              </t-button>
              <t-button
                theme="primary"
                variant="base"
                size="small"
                @click="handleSingleComplete(row as AssetDisplay)"
              >
                补全申请
              </t-button>
            </div>
          </template>

          <!-- Empty State -->
          <template #empty>
            <div class="empty-state">
              <t-icon :name="searchQuery ? 'file-unknown' : 'search'" size="48px" />
              <p>{{ searchQuery ? '没有匹配的元数据资产' : '输入关键词开始搜索元数据' }}</p>
            </div>
          </template>
        </t-table>
      </div>
    </section>

    <!-- Pagination -->
    <div v-if="total > pagination.page_size" class="pagination-wrap">
      <t-pagination
        :current="pagination.page"
        :total="total"
        :page-size="pagination.page_size"
        show-jumper
        @change="handlePageChange"
      />
    </div>

    <!-- Domain Popup Dialog -->
    <t-dialog
      v-model:visible="domainPopupVisible"
      header="选择业务域"
      :footer="false"
      width="420px"
      placement="center"
    >
      <div class="domain-popup-chips">
        <button
          class="filter-chip"
          :class="{ active: localFilters.businessDomain === '' }"
          @click="setDomainFilter(''); domainPopupVisible = false"
        >
          全部业务域
        </button>
        <button
          v-for="domain in hiddenDomains"
          :key="domain"
          class="filter-chip"
          :class="{ active: localFilters.businessDomain === domain }"
          @click="setDomainFilter(domain); domainPopupVisible = false"
        >
          {{ domain }}
        </button>
      </div>
    </t-dialog>

    <!-- Confirm Completion Dialog -->
    <t-dialog
      v-model:visible="confirmVisible"
      header="确认补全申请"
      :confirm-btn="{ content: '确认申请', theme: 'primary' }"
      :cancel-btn="{ content: '取消' }"
      :confirm-loading="completing"
      @confirm="confirmCompletion"
      @cancel="cancelCompletion"
    >
      <p v-if="pendingCompleteEntity">
        将为「{{ assetName(pendingCompleteEntity) }}」申请补全，系统将根据资产所属系统智能补全信息。
      </p>
    </t-dialog>
  </div>
</template>

<style scoped>
/* ── Design tokens ── */
.search-page {
  --color-bg: oklch(99% 0.002 240);
  --color-surface: oklch(100% 0 0);
  --color-fg: oklch(18% 0.012 250);
  --color-muted: oklch(54% 0.012 250);
  --color-border: oklch(92% 0.005 250);
  --color-accent: oklch(58% 0.18 255);
  --color-accent-soft: oklch(58% 0.18 255 / 0.08);
  --font-mono: 'JetBrains Mono', 'SF Mono', ui-monospace, Menlo, monospace;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;

  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif;
  color: var(--color-fg);
}

/* ── Page header ── */
.page-header {
  margin-bottom: 28px;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-fg);
  letter-spacing: -0.01em;
}

.page-subtitle {
  font-size: 0.875rem;
  color: var(--color-muted);
  margin-top: 4px;
}

/* ── Search bar ── */
.search-section {
  margin-bottom: 12px;
}

.search-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 8px 10px;
}

.search-bar:focus-within {
  border-color: var(--color-accent);
}

.search-bar-row {
  display: flex;
  gap: 10px;
  align-items: center;
  width: 100%;
}

.search-icon {
  color: var(--color-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 15px;
  font-family: inherit;
  color: var(--color-fg);
  min-width: 0;
}

.search-input::placeholder {
  color: var(--color-muted);
}

.result-count {
  font-size: 13px;
  color: var(--color-muted);
  padding-left: 8px;
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* ── Filter bar ── */
.filter-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
  overflow-x: auto;
  padding-top: 2px;
}

.filter-group {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.filter-sep {
  width: 1px;
  background: var(--color-border);
  margin: 0 4px;
  align-self: stretch;
}

.filter-chip {
  padding: 5px 12px;
  border-radius: 20px;
  border: 1px solid var(--color-border);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  background: transparent;
  color: var(--color-muted);
  font-family: inherit;
  transition: all 0.15s;
}

.filter-chip:hover {
  border-color: var(--color-accent);
  color: var(--color-fg);
}

.filter-chip.active {
  background: var(--color-accent);
  color: #fff;
  border-color: var(--color-accent);
}

/* ── Filter selects ── */
.filter-select-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.filter-select {
  appearance: none;
  padding: 5px 28px 5px 10px;
  border-radius: 20px;
  border: 1px solid var(--color-border);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  color: var(--color-muted);
  font-family: inherit;
  transition: all 0.15s;
  min-width: 0;
}

.filter-select:hover {
  border-color: var(--color-accent);
  color: var(--color-fg);
}

.filter-select.active {
  background: var(--color-accent-soft);
  color: var(--color-accent);
  border-color: var(--color-accent);
}

.filter-select-wrap::after {
  content: '';
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid currentColor;
}

/* ── Expand button ── */
.expand-btn {
  padding: 5px 12px;
  border-radius: 20px;
  border: 1px dashed var(--color-border);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  background: transparent;
  color: var(--color-muted);
  font-family: inherit;
  transition: all 0.15s;
  flex-shrink: 0;
}

.expand-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

/* ── Ops bar ── */
.ops-section {
  margin-bottom: 16px;
}

.ops-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  flex-wrap: wrap;
  gap: 10px;
}

.ops-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ops-count {
  font-size: 13px;
  color: var(--color-fg);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.ops-bar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ops-selected {
  font-size: 13px;
  color: var(--color-muted);
  font-variant-numeric: tabular-nums;
}

.ops-batch-btn {
  padding: 6px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--color-accent);
  background: var(--color-accent);
  color: #fff;
  font-family: inherit;
  transition: all 0.15s;
  white-space: nowrap;
}

.ops-batch-btn:hover:not(:disabled) {
  opacity: 0.88;
}

.ops-batch-btn:disabled {
  background: transparent;
  border-color: var(--color-border);
  color: var(--color-muted);
  cursor: not-allowed;
  opacity: 0.5;
}

/* ── Table section ── */
.table-section {
  margin-bottom: 24px;
}

.table-wrap {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* ── Cell styles ── */
.cell-name {
  font-weight: 600;
  color: var(--color-accent);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 13px;
}

.cell-name:hover {
  text-decoration: underline;
}

.cell-mono {
  font-family: var(--font-mono);
  font-size: 13px;
}

.cell-desc {
  display: inline-block;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-muted);
  font-size: 13px;
}

/* ── Action buttons ── */
.action-btns {
  display: flex;
  gap: 6px;
}

/* ── Empty state ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 64px 24px;
  color: var(--color-muted);
}

.empty-state p {
  font-size: 15px;
}

/* ── Pagination ── */
.pagination-wrap {
  display: flex;
  justify-content: center;
}

/* ── Domain popup chips ── */
.domain-popup-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.domain-popup-chips .filter-chip {
  font-size: 14px;
  padding: 6px 14px;
}

/* ── Table overrides for TDesign ── */
:deep(.t-table) {
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

:deep(.t-table th) {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  white-space: nowrap;
  user-select: none;
}

:deep(.t-table td) {
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

:deep(.t-table tr:hover td) {
  background: var(--color-bg);
}

:deep(.t-table__empty) {
  padding: 0;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .search-page {
    padding: 16px;
  }

  .search-input {
    min-width: 120px;
  }

  .filter-bar {
    flex-wrap: wrap;
    gap: 6px;
  }

  .filter-sep {
    display: none;
  }

  .result-count {
    display: none;
  }

  .ops-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .ops-bar-left {
    flex-wrap: wrap;
  }

  .ops-bar-right {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
