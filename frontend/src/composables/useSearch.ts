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
    is_sample: undefined as boolean | undefined,
    completion_status: '' as string,
    sort_by: 'updated_time',
    sort_desc: true,
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
        is_sample: filters.is_sample,
        completion_status: filters.completion_status || undefined,
        sort_by: filters.sort_by || undefined,
        sort_desc: filters.sort_desc,
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
