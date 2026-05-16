"""百炼平台 LLM 调用服务"""
import os
from langchain_community.chat_models import ChatTongyi
from app.config import get_settings

settings = get_settings()


def create_llm(model: str = "qwen-plus", temperature: float = 0.1) -> ChatTongyi:
    """创建百炼平台 LLM 实例"""
    return ChatTongyi(
        model=model,
        dashscope_api_key=settings.dashscope_api_key,
        temperature=temperature,
    )


def select_model(entity_type: str, schema_context: list[dict], retrieved_context: list[dict]) -> str:
    """根据场景自动选择模型"""
    if entity_type == "table":
        rich_siblings = sum(1 for s in schema_context if s.get("description"))
        if rich_siblings > 5:
            return "qwen-max"

    if entity_type == "column":
        return "qwen-plus"

    return "qwen-plus"
