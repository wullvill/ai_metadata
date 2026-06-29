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
