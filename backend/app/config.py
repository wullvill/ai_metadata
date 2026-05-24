"""应用配置管理"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # 应用
    app_name: str = "metadata-completion"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://postgres:Bonc%401234@172.17.5.229:5432/metadata_completion"

    # 阿里云百炼
    dashscope_api_key: str = ""

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # Elasticsearch
    es_host: str = "http://172.17.5.238:9220"
    es_user: str = "elastic"
    es_password: str = "Bonc@1234"

    # OpenMetadata
    om_base_url: str = "http://localhost:8585/api"
    om_jwt_token: str = ""

    # Redis
    redis_url: str = "redis://:Bonc%401234@172.17.6.230:6379/0"

    # Celery
    celery_broker_url: str = "redis://:Bonc%401234@172.17.6.230:6379/1"
    celery_result_backend: str = "redis://:Bonc%401234@172.17.6.230:6379/2"

    # 质量校验阈值
    auto_approve_threshold: float = 0.80
    pending_review_threshold: float = 0.60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
