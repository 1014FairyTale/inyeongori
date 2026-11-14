import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai.providers.base import AIError
from app.config import get_settings
from app.core.constants import BONUS_POOL_INITIAL_TOKENS
from app.db import SessionLocal
from app.errors import register_error_handlers
from app.routers import auth, discovery, exchanges, listings, match, plans, reviews, wallet
from app.services.embeddings import backfill_all
from app.services.ledger import ensure_system_accounts

log = logging.getLogger("app")


def bootstrap() -> None:
    with SessionLocal() as db:
        ensure_system_accounts(db, BONUS_POOL_INITIAL_TOKENS)
        db.commit()


def warm_up_embeddings() -> None:
    """임베딩 모델을 미리 불러오고, 임베딩이 없거나 모델이 바뀐 재능·상품을 채워요.
    SEED_IF_EMPTY=true면 DB가 비어 있을 때 데모 시드도 넣어요.
    서버 시작을 막지 않도록 백그라운드 스레드에서 실행해요."""
    if get_settings().seed_if_empty:
        try:
            from seed.seed import seed_if_empty

            log.warning("seed: %s", "inserted demo data" if seed_if_empty() else "skipped (DB not empty)")
        except Exception:  # noqa: BLE001
            log.exception("seed failed")
    try:
        with SessionLocal() as db:
            counts = backfill_all(db)
            db.commit()
        log.warning("embeddings ready: %s", counts)
    except Exception:  # noqa: BLE001 - 실패해도 서버는 계속 동작
        log.exception("embedding warm-up failed")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    bootstrap()
    threading.Thread(target=warm_up_embeddings, daemon=True).start()
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
    api.include_router(plans.router)
    api.include_router(match.router)
    api.include_router(reviews.router)
    app.include_router(api)
    return app


app = create_app()
