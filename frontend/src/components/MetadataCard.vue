<template>
  <t-card
    :class="['metadata-card', { selected: selected }]"
    hover-shadow
    @click="$emit('select', entity)"
  >
    <template #title>
      <div class="card-title">
        <t-tag :theme="entity.entity_type === 'table' ? 'primary' : 'success'" size="small">
          {{ entity.entity_type === 'table' ? '表' : '字段' }}
        </t-tag>
        <span class="entity-name">{{ entity.table_name }}</span>
        <span v-if="entity.column_name" class="column-name">.{{ entity.column_name }}</span>
        <t-tag v-if="entity.has_description" theme="success" variant="outline" size="small">
          已描述
        </t-tag>
      </div>
    </template>
    <div class="card-body">
      <div class="meta-line">
        <span class="label">库:</span> {{ entity.database }}.{{ entity.schema }}
      </div>
      <div v-if="entity.data_type" class="meta-line">
        <span class="label">类型:</span> {{ entity.data_type }}
      </div>
      <div v-if="entity.display_name" class="meta-line">
        <span class="label">中文名:</span> {{ entity.display_name }}
      </div>
      <div v-if="entity.description" class="meta-line description">
        {{ entity.description }}
      </div>
    </div>
  </t-card>
</template>

<script setup lang="ts">
import type { MetadataEntity } from '../api/types'

defineProps<{
  entity: MetadataEntity
  selected?: boolean
}>()

defineEmits<{
  select: [entity: MetadataEntity]
}>()
</script>

<style scoped>
.metadata-card {
  cursor: pointer;
  margin-bottom: 8px;
}
.metadata-card.selected {
  border-color: var(--td-brand-color);
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.entity-name {
  font-weight: 600;
}
.column-name {
  color: var(--td-text-color-secondary);
}
.card-body {
  font-size: 13px;
}
.meta-line {
  margin-bottom: 4px;
}
.label {
  color: var(--td-text-color-placeholder);
  margin-right: 4px;
}
.description {
  color: var(--td-text-color-secondary);
  margin-top: 8px;
}
</style>
