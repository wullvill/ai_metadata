import axios from 'axios'
import type {
  SearchParams,
  SearchResponse,
  TargetEntity,
  CompletionResponse,
  ReviewRecord,
  ReviewDetail,
  AssetDetail,
  PipelineConfig,
  ReferenceItem,
} from './types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
})

export interface FilterOptions {
  systems: string[]
  databases: string[]
  schemas: string[]
  db_types: string[]
}

export async function getFilterOptions(): Promise<{ success: boolean; data: FilterOptions }> {
  const { data } = await api.get('/search/filters')
  return data
}

export async function searchMetadata(params: SearchParams): Promise<SearchResponse> {
  const { data } = await api.post('/search', {
    query: params.query,
    entity_type: params.entity_type,
    db_type: params.db_type,
    is_sample: params.is_sample,
    sort_by: params.sort_by,
    sort_desc: params.sort_desc,
    page: params.page,
    page_size: params.page_size,
  })
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
  const { data } = await api.post(`/review/${recordId}/modify`, { modified_result: payload })
  return data
}

export async function getCompletionHistory(params: {
  entity_id?: string
  status?: string
  start_date?: string
  end_date?: string
  page?: number
  limit?: number
}): Promise<{ success: boolean; data: ReviewRecord[]; meta?: { total: number } }> {
  const { data } = await api.get('/complete/history', { params: { ...params } })
  return data
}

export async function getAssetDetail(entityId: string): Promise<{ success: boolean; data: AssetDetail }> {
  const { data } = await api.get(`/assets/${entityId}`)
  return data
}

export async function setSamples(entityIds: string[], isSample: boolean): Promise<void> {
  await api.post('/samples/set', { entity_ids: entityIds, is_sample: isSample })
}

export async function getConfig(): Promise<{ success: boolean; data: PipelineConfig }> {
  const { data } = await api.get('/config')
  return data
}

export async function updateConfig(partial: Partial<PipelineConfig>): Promise<{ success: boolean; data: PipelineConfig }> {
  const { data } = await api.put('/config', partial)
  return data
}

export async function getConfigDefaults(): Promise<{ success: boolean; data: PipelineConfig }> {
  const { data } = await api.get('/config/defaults')
  return data
}

export async function getReviewReferences(recordId: string): Promise<{ success: boolean; data: ReferenceItem[] }> {
  const { data } = await api.get(`/review/${recordId}/references`)
  return data
}

export async function getRecordColumns(recordId: string): Promise<{ success: boolean; data: ReviewRecord[] }> {
  const { data } = await api.get(`/review/${recordId}/columns`)
  return data
}
