export interface MetadataEntity {
  entity_id: string
  entity_type: 'table' | 'view'
  database: string
  schema: string
  table_name: string
  column_name?: string
  data_type?: string
  db_type?: string
  display_name?: string
  description?: string
  tags?: string[]
  has_description?: boolean
  is_sample?: boolean
}

export interface TargetEntity {
  entity_id: string
  entity_type: 'table' | 'column'
  database: string
  schema: string
  table_name: string
  column_name?: string
  data_type?: string
  current_description?: string | null
  current_display_name?: string | null
  current_tags?: string[] | null
  table_description?: string | null
  columns?: Array<{ name: string; dataType: string }> | null
}

export interface CompletionResult {
  target_entity_id: string
  entity_type: string
  display_name: string
  description: string
  tags: string[]
  business_domain?: string | null
  sensitive_level?: string | null
  confidence: number
  reasoning?: string
  model_used?: string
  generated_at?: string
}

export interface QualityCheck {
  original_confidence: number
  adjusted_confidence: number
  rule_violations: Array<{
    rule: string
    severity: 'critical' | 'warning' | 'info'
    message: string
  }>
  conflicts: Array<{
    type: string
    severity: string
    message: string
  }>
  review_status: 'auto_approved' | 'pending_review' | 'rejected'
}

export interface CompletionResponse {
  record_id: string
  entity_id: string
  entity_type: string
  review_status: string
  completion_result: CompletionResult | null
  quality_check: QualityCheck | null
  created_at: string
}

export interface ReviewRecord {
  id: string
  entity_id: string
  entity_type: string
  completion_result: CompletionResult | null
  quality_check: QualityCheck | null
  review_status: string
  created_at: string | null
}

export interface ReviewDetail {
  id: string
  entity_id: string
  entity_type: string
  target_data: TargetEntity | null
  completion_result: CompletionResult | null
  quality_check: QualityCheck | null
  review_status: string
  reviewer: string | null
  review_comment: string | null
  synced_to_om: boolean
}

export interface SearchParams {
  query: string
  entity_type?: string
  db_type?: string
  page?: number
  page_size?: number
}

export interface SearchResponse {
  success: boolean
  data: MetadataEntity[]
  meta: {
    total: number
    page: number
    page_size: number
  }
}

export interface HistoryParams {
  status?: string
  entity_id?: string
  start_date?: string
  end_date?: string
  page?: number
  limit?: number
}

export interface ColumnInfo {
  column_id: string
  entity_id: string
  column_name: string
  data_type: string
  original_description: string
  original_tags: string[]
  completion_description: string
  completion_tags: string[]
  completion_time: string | null
}

export interface AssetDetail {
  entity_id: string
  entity_type: 'table' | 'view'
  database: string
  db_type?: string
  system?: string
  schema_name: string
  table_name: string
  column_name?: string
  display_name?: string
  description?: string
  tags?: string[]
  has_description?: boolean
  columns: ColumnInfo[]
}

export interface FilterOptions {
  systems: string[]
  databases: string[]
  schemas: string[]
  db_types: string[]
}
