import axios from 'axios'
import type {
  SearchParams,
  SearchResponse,
  TargetEntity,
  CompletionResponse,
  ReviewRecord,
  ReviewDetail,
} from './types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
})

export async function searchMetadata(params: SearchParams): Promise<SearchResponse> {
  const { data } = await api.post('/search', params)
  return data
}

export async function triggerCompletion(target: TargetEntity): Promise<CompletionResponse> {
  const { data } = await api.post('/complete/trigger/manual', { target })
  return data
}

export async function getReviewQueue(params: {
  entity_type?: string
  status?: string
  page?: number
  page_size?: number
}): Promise<{ success: boolean; data: ReviewRecord[]; meta?: { total: number; page: number; page_size: number } }> {
  const { data } = await api.get('/review/queue', { params })
  return data
}

export async function getReviewDetail(recordId: string): Promise<{ success: boolean; data: ReviewDetail }> {
  const { data } = await api.get(`/review/${recordId}`)
  return data
}

export async function approveReview(recordId: string, comment?: string): Promise<{ success: boolean }> {
  const { data } = await api.post(`/review/${recordId}/approve`, { comment })
  return data
}

export async function rejectReview(recordId: string, comment: string): Promise<{ success: boolean }> {
  const { data } = await api.post(`/review/${recordId}/reject`, { comment })
  return data
}

export async function batchApprove(recordIds: string[]): Promise<{ success: boolean; data: { count: number } }> {
  const { data } = await api.post('/review/batch/approve', recordIds)
  return data
}

export async function modifyReview(recordId: string, payload: {
  display_name?: string
  description?: string
  tags?: string[]
}): Promise<{ success: boolean }> {
  const { data } = await api.post(`/review/${recordId}/modify`, payload)
  return data
}

export async function getCompletionHistory(params: {
  entity_id?: string
  status?: string
  page?: number
  limit?: number
}): Promise<{ success: boolean; data: ReviewRecord[]; meta?: { total: number } }> {
  const { data } = await api.get('/review/queue', { params: { ...params, page_size: params.limit } })
  return data
}
