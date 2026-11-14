"""임베딩 공통 처리. 실패해도 예외를 던지지 않고 None을 돌려줘서, 본 기능(저장 등)은 계속 진행돼요."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai import get_embedder
from ai.factory import embedding_model_name
from ai.providers.base import AIError
from app.core.constants import SIMILARITY_THRESHOLD, SIMILARITY_THRESHOLD_DEFAULT
from app.models import Listing

log = logging.getLogger("embeddings")


def embed_text(text: str) -> list[float] | None:
    try:
        return get_embedder().embed([text])[0]
    except AIError as e:
        log.warning("embedding failed: %s", e)
        return None


def similarity_threshold() -> float:
    return SIMILARITY_THRESHOLD.get(embedding_model_name(), SIMILARITY_THRESHOLD_DEFAULT)


def listing_text(listing: Listing) -> str:
    return f"{listing.title} ({listing.category}): {listing.description}"


def embed_listing(listing: Listing) -> None:
    vec = embed_text(listing_text(listing))
    listing.embedding = vec
    listing.embedding_model = embedding_model_name() if vec is not None else None


def backfill_listings(db: Session) -> int:
    current = embedding_model_name()
    rows = db.scalars(
        select(Listing).where((Listing.embedding.is_(None)) | (Listing.embedding_model != current))
    ).all()
    for listing in rows:
        embed_listing(listing)
    return len(rows)


def backfill_all(db: Session) -> dict[str, int]:
    """임베딩이 없거나 현재 모델과 다른 재능·상품을 다시 계산해요. (서버 시작 시 실행)"""
    from app.services.discovery import backfill_embeddings  # 순환 import 방지

    return {"talents": backfill_embeddings(db), "listings": backfill_listings(db)}
