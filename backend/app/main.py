"""FastAPI 应用入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import async_session
from app.services.config_service import config_service
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with async_session() as session:
        await config_service.load_from_db(session)
    logger.info("Config loaded from DB")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    from app.api.search import router as search_router
    from app.api.complete import router as complete_router
    from app.api.review import router as review_router
    from app.api.sync import router as sync_router
    from app.api.history import router as history_router
    from app.api.assets import router as assets_router
    from app.api.samples import router as sample_router
    from app.api.config import router as config_router

    app.include_router(search_router)
    app.include_router(complete_router)
    app.include_router(review_router)
    app.include_router(sync_router)
    app.include_router(history_router)
    app.include_router(assets_router)
    app.include_router(sample_router)
    app.include_router(config_router)

    return app


app = create_app()
