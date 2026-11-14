"""AI 매칭 (기능 4).

1) 요청 문장을 임베딩해서 확정 재능(user_talents)과 활성 상품(listings)에서 비슷한 것을 찾아요.
2) 사람 단위로 묶어 가장 높은 유사도를 그 사람의 유사도로 써요.
3) 점수 = 0.7×유사도 + 0.2×평점(베이지안 평균/5) + 0.1×활동(완료 횟수, 로그 스케일)
4) "왜 이 사람인지"는 상위 N명을 LLM 한 번으로 묶어 생성하고, 실패하면 템플릿으로 대신해요 (D3).
"""

import logging
import math
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai.factory import embedding_model_name
from ai.providers.base import AIError
from ai.schemas import MatchReasonsAI
from ai.structured import generate
from app.core.constants import (
    MATCH_RATING_PRIOR,
    MATCH_RATING_PRIOR_WEIGHT,
    MATCH_WEIGHT_ACTIVITY,
    MATCH_WEIGHT_RATING,
    MATCH_WEIGHT_SIMILARITY,
    MATCH_MIN_SIMILARITY_MARGIN,
    MATCH_RELATIVE_CUTOFF,
)
from app.models import Exchange, ExchangeStatus, Listing, ListingStatus, User, UserTalent
from app.schemas.market import UserBrief
from app.schemas.match import MatchCandidate, MatchedListing
from app.services.embeddings import embed_text, similarity_threshold

log = logging.getLogger("matching")
POOL = 50  # 재능·상품 각각에서 먼저 뽑는 개수
ACTIVITY_SATURATION = 10  # 완료 10회면 활동 점수 만점


@dataclass
class ProviderStats:
    completed_count: int = 0
    rating_avg: float | None = None
    rating_count: int = 0


@dataclass
class _Cand:
    user_id: int
    similarity: float = 0.0
    talent: str | None = None
    talent_sim: float = -1.0
    listing: Listing | None = None
    listing_sim: float = -1.0
    extra: dict[str, object] = field(default_factory=dict)


def provider_stats(db: Session, user_ids: list[int]) -> dict[int, ProviderStats]:
    """완료 횟수와 평점. (평점은 7단계 후기 기능에서 채워져요)"""
    stats = {uid: ProviderStats() for uid in user_ids}
    if not user_ids:
        return stats
    rows = db.execute(
        select(Exchange.provider_id, func.count())
        .where(Exchange.provider_id.in_(user_ids), Exchange.status == ExchangeStatus.COMPLETED)
        .group_by(Exchange.provider_id)
    ).all()
    for uid, n in rows:
        stats[uid].completed_count = n
    try:
        from app.services.reviews import rating_stats  # 7단계

        for uid, (avg, cnt) in rating_stats(db, user_ids).items():
            stats[uid].rating_avg, stats[uid].rating_count = avg, cnt
    except ImportError:
        pass
    return stats


def bayesian_rating(avg: float | None, count: int) -> float:
    total = (avg or 0) * count + MATCH_RATING_PRIOR * MATCH_RATING_PRIOR_WEIGHT
    return total / (count + MATCH_RATING_PRIOR_WEIGHT)


def score(similarity: float, st: ProviderStats) -> float:
    rating = bayesian_rating(st.rating_avg, st.rating_count) / 5
    activity = min(1.0, math.log1p(st.completed_count) / math.log1p(ACTIVITY_SATURATION))
    return MATCH_WEIGHT_SIMILARITY * similarity + MATCH_WEIGHT_RATING * rating + MATCH_WEIGHT_ACTIVITY * activity


def _collect(db: Session, vec: list[float], exclude_user_id: int | None) -> dict[int, _Cand]:
    model = embedding_model_name()
    cands: dict[int, _Cand] = {}

    t_dist = UserTalent.embedding.cosine_distance(vec)
    t_stmt = (
        select(UserTalent.user_id, UserTalent.name, t_dist.label("d"))
        .join(User, User.id == UserTalent.user_id)
        .where(UserTalent.embedding.is_not(None), UserTalent.embedding_model == model, User.is_system.is_(False))
        .order_by(t_dist)
        .limit(POOL)
    )
    l_dist = Listing.embedding.cosine_distance(vec)
    l_stmt = (
        select(Listing, l_dist.label("d"))
        .where(Listing.embedding.is_not(None), Listing.embedding_model == model, Listing.status == ListingStatus.ACTIVE)
        .order_by(l_dist)
        .limit(POOL)
    )
    if exclude_user_id is not None:
        t_stmt = t_stmt.where(UserTalent.user_id != exclude_user_id)
        l_stmt = l_stmt.where(Listing.provider_id != exclude_user_id)

    for uid, name, d in db.execute(t_stmt).all():
        sim = 1 - float(d)
        c = cands.setdefault(uid, _Cand(uid))
        if sim > c.talent_sim:
            c.talent, c.talent_sim = name, sim
        c.similarity = max(c.similarity, sim)
    for listing, d in db.execute(l_stmt).all():
        sim = 1 - float(d)
        c = cands.setdefault(listing.provider_id, _Cand(listing.provider_id))
        if sim > c.listing_sim:
            c.listing, c.listing_sim = listing, sim
        c.similarity = max(c.similarity, sim)
    return cands


def _template_reason(c: MatchCandidate) -> str:
    what = c.matched_talent or (c.listing.title if c.listing else "관련 재능")
    tail = []
    if c.completed_count:
        tail.append(f"완료 {c.completed_count}회")
    if c.rating_avg is not None and c.rating_count:
        tail.append(f"평점 {c.rating_avg:.1f}")
    return f"'{what}' 재능이 요청과 잘 맞아요" + (f" · {' · '.join(tail)}" if tail else "")


def _ai_reasons(query: str, results: list[MatchCandidate]) -> dict[int, str | None]:
    """후보별 추천 이유. AI가 관련 없다고 판단한 후보는 None (목록에서 빼요)."""
    lines = ["## 요청", query, "", "## 후보"]
    for i, c in enumerate(results):
        parts = [f"[{i}] {c.user.nickname}"]
        if c.user.major:
            parts.append(f"전공 {c.user.major}")
        if c.matched_talent:
            parts.append(f"확정 재능: {c.matched_talent}")
        if c.listing:
            parts.append(f"재능 상품: {c.listing.title} ({c.listing.price_tokens}토큰)")
        parts.append(f"완료 {c.completed_count}회")
        if c.rating_avg is not None and c.rating_count:
            parts.append(f"평점 {c.rating_avg:.1f} ({c.rating_count}개)")
        lines.append(" / ".join(parts))
    out = generate("match_reason", "\n".join(lines), MatchReasonsAI)
    return {
        r.candidate_index: (r.reason if r.relevant else None)
        for r in out.reasons
        if 0 <= r.candidate_index < len(results)
    }


def match(db: Session, query: str, *, limit: int = 5, exclude_user_id: int | None = None, with_reasons: bool = True) -> list[MatchCandidate]:
    vec = embed_text(query)
    if vec is None:
        raise AIError("요청 문장을 분석하지 못했어요. 잠시 후 다시 시도해 주세요", feature="match")

    cands = _collect(db, vec, exclude_user_id)
    min_sim = similarity_threshold() - MATCH_MIN_SIMILARITY_MARGIN
    cands = {uid: c for uid, c in cands.items() if c.similarity >= min_sim}
    if not cands:
        return []
    top_sim = max(c.similarity for c in cands.values())
    cands = {uid: c for uid, c in cands.items() if c.similarity >= top_sim - MATCH_RELATIVE_CUTOFF}

    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(list(cands))))}
    stats = provider_stats(db, list(cands))

    # 상품 없이 재능만 맞은 사람은 그 사람의 활성 상품 중 하나를 연결해 '요청하기'로 이어지게 해요
    missing = [uid for uid, c in cands.items() if c.listing is None]
    if missing:
        for listing in db.scalars(
            select(Listing)
            .where(Listing.provider_id.in_(missing), Listing.status == ListingStatus.ACTIVE)
            .order_by(Listing.created_at.desc())
        ):
            if cands[listing.provider_id].listing is None:
                cands[listing.provider_id].listing = listing

    results = []
    for uid, c in cands.items():
        st = stats[uid]
        results.append(
            MatchCandidate(
                user=UserBrief.model_validate(users[uid]),
                matched_talent=c.talent,
                listing=MatchedListing(id=c.listing.id, title=c.listing.title, price_tokens=c.listing.price_tokens) if c.listing else None,
                similarity=round(c.similarity, 3),
                rating_avg=st.rating_avg,
                rating_count=st.rating_count,
                completed_count=st.completed_count,
                score=round(score(c.similarity, st), 3),
                reason="",
                reason_source="template",
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    results = results[:limit]

    ai: dict[int, str | None] = {}
    if with_reasons:
        try:
            ai = _ai_reasons(query, results)
        except AIError as e:
            log.warning("match reason fallback to template: %s", e)
    kept: list[MatchCandidate] = []
    for i, r in enumerate(results):
        if i in ai and ai[i] is None:
            continue  # AI가 요청과 관련 없다고 판단
        if ai.get(i):
            r.reason, r.reason_source = ai[i], "ai"  # type: ignore[assignment]
        else:
            r.reason = _template_reason(r)
        kept.append(r)
    return kept
