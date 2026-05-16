import { ref, reactive } from 'vue'
import { getReviewQueue, getReviewDetail, approveReview, rejectReview, batchApprove } from '../api'
import type { ReviewRecord, ReviewDetail } from '../api/types'

export function useReview() {
  const records = ref<ReviewRecord[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const filters = reactive({
    entity_type: '' as string,
    status: 'pending_review' as string,
  })

  async function loadQueue(page = 1, pageSize = 20) {
    loading.value = true
    error.value = null
    try {
      const res = await getReviewQueue({
        entity_type: filters.entity_type || undefined,
        status: filters.status,
        page,
        page_size: pageSize,
      })
      records.value = res.data || []
    } catch (e: any) {
      error.value = e.message || '加载审核队列失败'
    } finally {
      loading.value = false
    }
  }

  async function approve(id: string) {
    await approveReview(id)
    await loadQueue()
  }

  async function reject(id: string, comment: string) {
    await rejectReview(id, comment)
    await loadQueue()
  }

  async function batchHandle(ids: string[]) {
    await batchApprove(ids)
    await loadQueue()
  }

  return { records, total, loading, error, filters, loadQueue, approve, reject, batchHandle }
}

export function useReviewDetail() {
  const detail = ref<ReviewDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function loadDetail(recordId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await getReviewDetail(recordId)
      detail.value = res.data
    } catch (e: any) {
      error.value = e.message || '加载详情失败'
    } finally {
      loading.value = false
    }
  }

  return { detail, loading, error, loadDetail }
}
