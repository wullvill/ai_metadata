"""Pipeline State 定义"""
from typing import TypedDict


class CompletionState(TypedDict):
    # Stage 1 输入/输出
    target_entity: dict
    retrieved_context: list[dict]
    schema_context: list[dict]
    sibling_columns: list[dict]
    # Stage 2 输出
    completion_result: dict | None
    # Stage 3 输出
    quality_check: dict | None
    # Stage 4 输出
    review_status: str | None
    # 错误信息
    error: str | None
