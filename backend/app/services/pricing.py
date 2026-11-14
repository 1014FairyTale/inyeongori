"""적정 토큰 제안 (결정 사항 D4-1).

토큰은 시간 단위가 아니라 '가격'이에요. 그래서 시간당 단가 대신 마켓 시세를 기준으로 제안해요.
1) 활동 설명을 임베딩해서 비슷한 상품(유사도 기준 이상)을 찾고
2) 그런 상품이 PRICE_SUGGEST_MIN_SIMILAR개 이상이면 가격 중앙값을 제안 (근거: market)
3) 부족하면 AI가 마켓 가격대를 참고해 추정한 값을 써요 (근거: ai)
"""

from dataclasses import dataclass
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.factory import embedding_model_name
from app.core.constants import PRICE_FALLBACK_TOKENS, PRICE_SUGGEST_MIN_SIMILAR, PRICE_SUGGEST_TOP_K
from app.models import Listing, ListingStatus, PriceBasis
from app.services.embeddings import embed_text, similarity_threshold


@dataclass
class SimilarListing:
    listing: Listing
    similarity: float


@dataclass
class PriceSuggestion:
    tokens: int
    basis: PriceBasis
    similar_count: int
    best_listing_id: int | None


def find_similar_listings(
    db: Session, text: str, *, exclude_user_id: int | None = None, top_k: int = PRICE_SUGGEST_TOP_K
) -> list[SimilarListing]:
    vec = embed_text(text)
    if vec is None:
        return []
    dist = Listing.embedding.cosine_distance(vec)
    stmt = (
        select(Listing, dist.label("d"))
        .where(
            Listing.status == ListingStatus.ACTIVE,
            Listing.embedding.is_not(None),
            Listing.embedding_model == embedding_model_name(),
        )
        .order_by(dist)
        .limit(top_k)
    )
    if exclude_user_id is not None:
        stmt = stmt.where(Listing.provider_id != exclude_user_id)
    threshold = similarity_threshold()
    return [SimilarListing(listing, 1 - float(d)) for listing, d in db.execute(stmt).all() if 1 - float(d) >= threshold]


def market_stats(db: Session) -> dict[str, object]:
    rows = db.execute(select(Listing.category, Listing.price_tokens).where(Listing.status == ListingStatus.ACTIVE)).all()
    by_cat: dict[str, list[int]] = {}
    for cat, price in rows:
        by_cat.setdefault(cat, []).append(price)
    return {
        "count": len(rows),
        "overall_median": int(median([p for _, p in rows])) if rows else None,
        "category_median": {c: int(median(ps)) for c, ps in by_cat.items()},
    }


def market_stats_text(stats: dict[str, object]) -> str:
    if not stats["count"]:
        return "현재 마켓에 등록된 상품이 없어요."
    cats = ", ".join(f"{c} {p}토큰" for c, p in stats["category_median"].items())  # type: ignore[union-attr]
    return f"등록 상품 {stats['count']}개, 전체 가격 중앙값 {stats['overall_median']}토큰. 카테고리별 중앙값: {cats}"


def suggest_price(
    db: Session,
    text: str,
    *,
    category: str,
    ai_estimate: int | None,
    exclude_user_id: int | None = None,
    stats: dict[str, object] | None = None,
) -> PriceSuggestion:
    similar = find_similar_listings(db, text, exclude_user_id=exclude_user_id)
    best = similar[0].listing.id if similar else None
    if len(similar) >= PRICE_SUGGEST_MIN_SIMILAR:
        return PriceSuggestion(int(median(s.listing.price_tokens for s in similar)), PriceBasis.MARKET, len(similar), best)
    if ai_estimate is not None:
        return PriceSuggestion(ai_estimate, PriceBasis.AI, len(similar), best)
    stats = stats or market_stats(db)
    fallback = stats["category_median"].get(category) or stats["overall_median"] or PRICE_FALLBACK_TOKENS  # type: ignore[union-attr]
    return PriceSuggestion(int(fallback), PriceBasis.AI, len(similar), best)  # type: ignore[arg-type]
