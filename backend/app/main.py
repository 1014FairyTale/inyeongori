from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.constants import BONUS_POOL_INITIAL_TOKENS
from app.db import SessionLocal
from app.errors import register_error_handlers
from fastapi import Request
from fastapi.responses import JSONResponse

from ai.providers.base import AIError
from app.routers import auth, discovery, exchanges, listings, wallet
from app.services.ledger import ensure_system_accounts


def bootstrap() -> None:
    with SessionLocal() as db:
        ensure_system_accounts(db, BONUS_POOL_INITIAL_TOKENS)
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    bootstrap()
    yield


def create_app(*, run_bootstrap: bool = True) -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="인연고리 API",
        version="0.1.0",
        lifespan=lifespan if run_bootstrap else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    @app.exception_handler(AIError)
    async def _ai_error(_: Request, exc: AIError) -> JSONResponse:
        return JSONResponse(
            {"error": {"code": "AI_FAILED", "message": str(exc), "details": {"feature": exc.feature}}},
            status_code=502,
        )

    api = APIRouter(prefix="/api/v1")

    @api.get("/health", tags=["meta"])
    def health() -> dict[str, object]:
        return {"status": "ok", "ai_mock": settings.ai_mock}

    api.include_router(auth.router)
    api.include_router(listings.router)
    api.include_router(exchanges.router)
    api.include_router(wallet.router)
    api.include_router(discovery.router)
    app.include_router(api)
    return app


app = create_app()
