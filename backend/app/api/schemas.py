"""API 请求/响应 Schema"""
from pydantic import BaseModel, Field


class TargetEntity(BaseModel):
    entity_id: str
    entity_type: str = Field(pattern="^(table|column)$")
    database: str
    schema_name: str = Field(alias="schema")
    table_name: str
    column_name: str | None = None
    data_type: str | None = None
    current_description: str | None = None
    current_display_name: str | None = None
    current_tags: list[str] | None = None
    table_description: str | None = None
    columns: list[dict] | None = None


class CompletionTriggerRequest(BaseModel):
    target: TargetEntity


class BatchCompletionRequest(BaseModel):
    targets: list[TargetEntity] = Field(max_length=100)


class CompletionResponse(BaseModel):
    record_id: str
    entity_id: str
    entity_type: str
    review_status: str
    completion_result: dict | None
    quality_check: dict | None
    created_at: str


class ReviewActionRequest(BaseModel):
    comment: str | None = None
    modified_result: dict | None = None
    reviewer: str | None = None


class BatchRejectRequest(BaseModel):
    record_ids: list[str]
    reason: str = Field(min_length=1)
    reviewer: str | None = None


class SearchRequest(BaseModel):
    query: str
    entity_type: str | None = None
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    data_type: str | None = None
    db_type: str | None = None
    is_sample: bool | None = None
    completion_status: str | None = None
    sort_by: str | None = None
    sort_desc: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SampleSetRequest(BaseModel):
    entity_ids: list[str]
    is_sample: bool


class PipelineConfigSchema(BaseModel):
    thresholds: dict = Field(default_factory=lambda: {
        "auto_approve": 0.80,
        "pending_review": 0.60,
    })
    models: dict = Field(default_factory=lambda: {
        "default": "qwen-plus",
        "auto_select": True,
        "table_rich_threshold": 5,
    })
    retrieval: dict = Field(default_factory=lambda: {
        "milvus_top_k": 20,
        "es_keyword_top_k": 20,
        "es_siblings_top_k": 5,
        "rrf_k": 60,
        "rrf_top_n": 15,
        "sample_boost": True,
    })
    rules: dict = Field(default_factory=lambda: {
        "required_fields": {"enabled": True},
        "display_name_no_code": {"enabled": True},
        "description_not_copy_name": {"enabled": True},
        "sensitive_level_valid": {"enabled": True},
        "tag_no_duplicates": {"enabled": True},
        "business_domain_valid": {"enabled": True},
        "table_name_consistency": {"enabled": True},
    })


class PipelineConfigUpdateRequest(BaseModel):
    thresholds: dict | None = None
    models: dict | None = None
    retrieval: dict | None = None
    rules: dict | None = None
