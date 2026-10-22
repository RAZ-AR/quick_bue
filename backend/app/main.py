from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, catalog
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="QB API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(catalog.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/config")
    async def public_config():
        # What the PWA needs before sign-in
        return {"dev_login": settings.dev_login, "telegram_bot_username": settings.telegram_bot_username}

    return app


app = create_app()
