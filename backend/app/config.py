"""应用配置管理"""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # 应用
    app_name: str = "metadata-completion"
    debug: bool = False
    DEPLOYMENT_MODE: Literal["embedded", "production"] = "embedded"
    database_url: str = "sqlite+aiosqlite:///data/metadata.db"

    # 阿里云百炼
    dashscope_api_key: str = "sk-a4663f488db84585aff4f9b0e28d767d"

    # Milvus (仅 production 模式使用)
    milvus_host: str = "172.17.5.229"
    milvus_port: int = 19530

    # Elasticsearch (仅 production 模式使用)
    es_host: str = "http://172.17.5.238:9220"
    es_user: str = "elastic"
    es_password: str = "Bonc@1234"

    # OpenMetadata
    om_base_url: str = "http://localhost:8585/api"
    om_jwt_token: str = ""

    # Redis (仅 production 模式使用)
    redis_url: str = "redis://:Bonc%401234@172.17.5.230:6379/0"

    # Celery — 根据模式自动选择 broker
    celery_broker_url: str = "sqla+sqlite:///data/celery.db"
    celery_result_backend: str = "db+sqlite:///data/celery.db"

    # 质量校验阈值
    auto_approve_threshold: float = 0.80
    pending_review_threshold: float = 0.60

    @property
    def vector_store_backend(self) -> str:
        return "chroma" if self.DEPLOYMENT_MODE == "embedded" else "milvus"

    @property
    def search_index_backend(self) -> str:
        return "tantivy" if self.DEPLOYMENT_MODE == "embedded" else "elasticsearch"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
