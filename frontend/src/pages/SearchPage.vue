<script setup lang="ts">
import { ref, watch } from 'vue'
import { useSearch } from '../composables/useSearch'
import { useCompletion } from '../composables/useCompletion'
import SearchBar from '../components/SearchBar.vue'
import MetadataCard from '../components/MetadataCard.vue'
import CompletionPanel from '../components/CompletionPanel.vue'
import type { MetadataEntity, TargetEntity } from '../api/types'

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
  result: completionResult,
  qualityCheck,
  error: completionError,
  triggerComplete,
  clearResult,
} = useCompletion()

const selectedEntity = ref<MetadataEntity | null>(null)
const showCompletion = ref(false)

const filterOptions = {
  entityType: [
    { label: '全部', value: '' },
    { label: '表', value: 'table' },
    { label: '字段', value: 'column' },
  ],
}

watch(() => filters.entity_type, () => search())

async function handleSearch() {
  clearResult()
  showCompletion.value = false
  selectedEntity.value = null
  await search()
}

function handleSelect(entity: MetadataEntity) {
  selectedEntity.value = entity
}

function buildTargetEntity(entity: MetadataEntity): TargetEntity {
  return {
    entity_id: entity.entity_id,
    entity_type: entity.entity_type,
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
}

async function handleComplete(entity: MetadataEntity) {
  selectedEntity.value = entity
  showCompletion.value = true
  await triggerComplete(buildTargetEntity(entity))
}

function handleCloseCompletion() {
  showCompletion.value = false
  clearResult()
}

function handlePageChange(pageInfo: { current: number }) {
  pagination.page = pageInfo.current
  search()
}
</script>

<template>
  <div class="search-page">
    <div class="page-header">
      <div>
        <h1>元数据搜索</h1>
        <p class="page-subtitle">搜索表或字段，选中后触发 AI 智能补全元数据信息</p>
      </div>
    </div>

    <div class="search-controls surface-card">
      <SearchBar
        v-model="filters.query"
        :loading="loading"
        @search="handleSearch"
      />
      <div class="filter-row">
        <t-select
          v-model="filters.entity_type"
          :options="filterOptions.entityType"
          placeholder="实体类型"
          clearable
          size="small"
          style="width: 120px"
        />
        <span v-if="total > 0" class="result-count">共 {{ total }} 条结果</span>
      </div>
    </div>

    <t-alert
      v-if="error"
      theme="error"
      :message="error"
      close
      style="margin-top: 16px"
    />

    <div class="results-layout">
      <t-loading :loading="loading" text="搜索中...">
        <div v-if="results.length === 0 && !loading" class="empty-state">
          <t-icon name="search" size="48px" />
          <p>输入关键词开始搜索元数据</p>
        </div>

        <div v-else class="results-grid">
          <div
            v-for="entity in results"
            :key="entity.entity_id"
            class="result-card-wrapper"
          >
            <MetadataCard
              :entity="entity"
              :selected="selectedEntity?.entity_id === entity.entity_id"
              @select="handleSelect"
            />
            <t-button
              theme="primary"
              variant="outline"
              size="small"
              style="margin-top: 8px; width: 100%"
              @click="handleComplete(entity)"
            >
              智能补全
            </t-button>
          </div>
        </div>
      </t-loading>

      <div v-if="total > pagination.page_size" style="display: flex; justify-content: center; margin-top: 24px">
        <t-pagination
          :current="pagination.page"
          :total="total"
          :page-size="pagination.page_size"
          show-jumper
          @change="handlePageChange"
        />
      </div>
    </div>

    <Transition name="slide-up">
      <div v-if="showCompletion && (completionResult || completing)" style="margin-top: 24px">
        <CompletionPanel
          :completing="completing"
          :result="completionResult"
          :quality-check="qualityCheck"
          :error="completionError"
        />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.search-page {
  max-width: 1200px;
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

.search-controls {
  background: var(--color-surface);
  border-radius: var(--radius-base);
  padding: 24px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.result-count {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 64px;
  color: var(--color-text-secondary);
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(460px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.result-card-wrapper {
  display: flex;
  flex-direction: column;
}

.slide-up-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-up-leave-active {
  transition: all 0.15s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-up-enter-from {
  opacity: 0;
  transform: translateY(16px);
}

.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
