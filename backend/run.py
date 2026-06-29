"""
统一服务入口 — FastAPI + Vue SPA
使用 middleware 方式提供前端 SPA 支持
"""
import os
from pathlib import Path
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.main import app

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    assets_dir = str(frontend_dist / "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # 用 Middleware 处理 SPA fallback
    @app.middleware("http")
    async def spa_fallback(request, call_next):
        response = await call_next(request)
        # 404 时返回 index.html（SPA 路由）
        if response.status_code == 404:
            # 跳过 API 和 docs 路径
            path = request.url.path
            if not any(path.startswith(p) for p in ("/api/", "/docs", "/openapi", "/redoc", "/health", "/assets/")):
                return FileResponse(frontend_dist / "index.html")
        return response
    
    print(f"✅ 前端 SPA 已启用: {frontend_dist}")
else:
    print(f"⚠️ 未找到前端构建目录: {frontend_dist}")

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    print(f"=" * 60)
    print(f"  数据治理智能元数据补全系统")
    print(f"  监听: {host}:{port}")
    print(f"=" * 60)
    uvicorn.run(app, host=host, port=port)
