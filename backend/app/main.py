from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import addresses, admin, auth, cart, catalog, geo, inbox, onboarding, orders, seller
from app.config import get_settings
from app.platform.errors import DomainError


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="QB API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(addresses.router)
    app.include_router(geo.router)
    app.include_router(admin.router)
    app.include_router(auth.router)
    app.include_router(inbox.router)
    app.include_router(catalog.router)
    app.include_router(cart.router)
    app.include_router(orders.router)
    app.include_router(onboarding.router)
    app.include_router(seller.router)

    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError) -> JSONResponse:
        # docs/03-architecture.md §3.9: {"code", "message", "details"}
        return JSONResponse(
            {"code": exc.code, "message": exc.message, "details": exc.details}, status_code=exc.status_code
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/config")
    async def public_config():
        # What the PWA needs before sign-in
        return {
            "dev_login": settings.dev_login,
            "email_login": True,
            "google_client_id": settings.google_client_id or None,
            "telegram_bot_username": settings.telegram_bot_username or None,
        }

    return app


app = create_app()
