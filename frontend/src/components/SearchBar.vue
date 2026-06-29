<template>
  <div class="search-bar">
    <t-input
      v-model="query"
      placeholder="搜索表名、字段名或业务描述..."
      clearable
      size="large"
      @enter="$emit('search')"
      @clear="$emit('search')"
    >
      <template #suffix-icon>
        <t-button theme="primary" @click="$emit('search')" :loading="loading">
          搜索
        </t-button>
      </template>
    </t-input>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelValue: string
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  search: []
}>()

const query = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})
</script>
