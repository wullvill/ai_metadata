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
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
