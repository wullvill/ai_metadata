"""Pipeline 配置服务 — 内存缓存 + DB 读写"""
import copy
from sqlalchemy import select
from app.models.config import PipelineConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULTS = {
    "thresholds": {
        "auto_approve": 0.80,
        "pending_review": 0.60,
    },
    "models": {
        "default": "qwen-plus",
        "auto_select": True,
        "table_rich_threshold": 5,
    },
    "retrieval": {
        "milvus_top_k": 20,
        "es_keyword_top_k": 20,
        "es_siblings_top_k": 5,
        "rrf_k": 60,
        "rrf_top_n": 15,
        "sample_boost": True,
    },
    "rules": {
        "required_fields": {"enabled": True},
        "display_name_no_code": {"enabled": True},
        "description_not_copy_name": {"enabled": True},
        "sensitive_level_valid": {"enabled": True},
        "tag_no_duplicates": {"enabled": True},
        "business_domain_valid": {"enabled": True},
        "table_name_consistency": {"enabled": True},
    },
}


class ConfigService:
    """线程安全的配置单例服务"""

    _instance: "ConfigService | None" = None
    _cached: dict | None = None

    def __new__(cls) -> "ConfigService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_config(cls) -> dict:
        """获取当前生效配置（优先缓存，回退默认值）"""
        if cls._cached is not None:
            return copy.deepcopy(cls._cached)
        return copy.deepcopy(DEFAULTS)

    @staticmethod
    def get_defaults() -> dict:
        return copy.deepcopy(DEFAULTS)

    async def load_from_db(self, session) -> dict:
        """从 DB 加载配置到内存缓存，若无记录或配置为空则写入默认值"""
        result = await session.execute(
            select(PipelineConfig).where(PipelineConfig.id == 1)
        )
        row = result.scalar_one_or_none()
        if row and row.config:
            ConfigService._cached = copy.deepcopy(row.config)
        elif row:
            row.config = copy.deepcopy(DEFAULTS)
            await session.commit()
            ConfigService._cached = copy.deepcopy(DEFAULTS)
        else:
            row = PipelineConfig(id=1, config=copy.deepcopy(DEFAULTS))
            session.add(row)
            await session.commit()
            ConfigService._cached = copy.deepcopy(DEFAULTS)
        logger.info("ConfigService: loaded config from DB")
        return ConfigService._cached

    async def save_to_db(self, session, config: dict, updated_by: str = "admin") -> dict:
        """写入 DB 并刷新缓存"""
        result = await session.execute(
            select(PipelineConfig).where(PipelineConfig.id == 1)
        )
        row = result.scalar_one_or_none()
        if row:
            row.config = config
            row.updated_by = updated_by
        else:
            row = PipelineConfig(id=1, config=config, updated_by=updated_by)
            session.add(row)
        await session.commit()
        ConfigService._cached = copy.deepcopy(config)
        logger.info(f"ConfigService: config saved by {updated_by}")
        return ConfigService._cached

    def apply_partial(self, partial: dict) -> dict:
        """将部分更新合并到当前缓存，返回合并后的完整配置"""
        current = copy.deepcopy(ConfigService._cached) if ConfigService._cached else copy.deepcopy(DEFAULTS)
        for section in ("thresholds", "models", "retrieval", "rules"):
            if section in partial and partial[section] is not None:
                current[section] = {**current[section], **partial[section]}
        ConfigService._cached = current
        return copy.deepcopy(current)

    @classmethod
    def reset(cls) -> None:
        """测试辅助：重置单例状态"""
        cls._instance = None
        cls._cached = None


config_service = ConfigService()
