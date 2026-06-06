import { ref, reactive } from 'vue'
import { searchMetadata } from '../api'
import type { MetadataEntity } from '../api/types'

export function useSearch() {
  const results = ref<MetadataEntity[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const filters = reactive({
    query: '',
    entity_type: '' as string,
    db_type: '',
  })

  const pagination = reactive({
    page: 1,
    page_size: 20,
  })

  async function search() {
    loading.value = true
    error.value = null
    try {
      const res = await searchMetadata({
        query: filters.query,
        entity_type: filters.entity_type || undefined,
        db_type: filters.db_type || undefined,
        page: pagination.page,
        page_size: pagination.page_size,
      })
      results.value = res.data || []
      total.value = res.meta?.total || 0
    } catch (e: any) {
      error.value = e.message || '搜索失败'
      results.value = []
    } finally {
      loading.value = false
    }
  }

  return { results, total, loading, error, filters, pagination, search }
}
