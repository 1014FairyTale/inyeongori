"""숨은 재능 발굴 (기능 1).

AI가 추론한 재능은 '후보'일 뿐이에요. 사용자가 [맞아요/수정]으로 확정한 것만 user_talents에 저장하고,
그때 임베딩을 만들어요. 임베딩이 실패해도 재능 저장은 막지 않고, 나중에 backfill_embeddings()로 채워요.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai import get_embedder
from ai.factory import embedding_model_name
from ai.providers.base import AIError
from ai.schemas import TalentDiscoveryAI
from ai.structured import generate
from app.config import get_settings
from app.core.constants import LISTING_CATEGORIES
from app.errors import AppError
from app.models import CandidateStatus, DiscoverySession, TalentCandidate, TalentSource, User, UserTalent
from app.schemas.talent import CandidateDecision, DiscoveryCreate

log = logging.getLogger("discovery")
FALLBACK_CATEGORY = "생활·기타"


def _prompt(req: DiscoveryCreate) -> str:
    a = req.answers
    return "\n".join(
        [
            "## 자기소개",
            req.intro_text,
            "",
            "## 문답",
            f"- 최근에 맡았던 역할: {a.recent_roles or '(답하지 않음)'}",
            f"- 친구들이 자주 부탁하는 것: {a.friends_ask or '(답하지 않음)'}",
            f"- 자신 있는 도구: {a.confident_tools or '(답하지 않음)'}",
            "",
            "## 사용할 수 있는 카테고리",
            ", ".join(LISTING_CATEGORIES),
        ]
    )


def run_discovery(db: Session, user: User, req: DiscoveryCreate) -> DiscoverySession:
    result = generate("talent_discovery", _prompt(req), TalentDiscoveryAI)

    session = DiscoverySession(
        user_id=user.id,
        intro_text=req.intro_text,
        answers=req.answers.model_dump(),
        encouragement=result.encouragement,
        ai_provider="mock" if get_settings().ai_mock else get_settings().llm_model,
    )
    db.add(session)
    db.flush()

    seen: set[str] = set()
    for i, c in enumerate(result.candidates):
        key = c.name.strip()
        if key in seen:
            continue
        seen.add(key)
        db.add(
            TalentCandidate(
                session_id=session.id,
                user_id=user.id,
                position=i,
                name=key[:40],
                category=c.category if c.category in LISTING_CATEGORIES else FALLBACK_CATEGORY,
                evidence=c.evidence,
                source_quote=c.source_quote or None,
                confirm_question=c.confirm_question,
                description=c.description,
            )
        )
    if not user.bio:
        user.bio = req.intro_text[:500]
    db.flush()
    return session


def candidates_of(db: Session, session_id: int) -> list[TalentCandidate]:
    return list(
        db.scalars(select(TalentCandidate).where(TalentCandidate.session_id == session_id).order_by(TalentCandidate.position))
    )


def latest_session(db: Session, user: User) -> DiscoverySession | None:
    return db.scalar(
        select(DiscoverySession)
        .where(DiscoverySession.user_id == user.id)
        .order_by(DiscoverySession.created_at.desc(), DiscoverySession.id.desc())
        .limit(1)
    )


# ---- 임베딩 ----

def talent_text(t: UserTalent) -> str:
    return f"{t.name} ({t.category}): {t.description or ''}".strip()


def embed_talent(t: UserTalent) -> None:
    try:
        t.embedding = get_embedder().embed([talent_text(t)])[0]
        t.embedding_model = embedding_model_name()
    except AIError as e:  # 저장은 계속 진행하고 나중에 다시 채워요
        log.warning("embedding failed talent=%s: %s", t.id, e)
        t.embedding = None
        t.embedding_model = None


def backfill_embeddings(db: Session) -> int:
    """임베딩이 없거나 현재 모델과 다른 재능을 다시 임베딩해요."""
    current = embedding_model_name()
    talents = db.scalars(
        select(UserTalent).where((UserTalent.embedding.is_(None)) | (UserTalent.embedding_model != current))
    ).all()
    for t in talents:
        embed_talent(t)
    return len(talents)


# ---- 후보 확인 ----

def decide(db: Session, user: User, candidate_id: int, d: CandidateDecision) -> tuple[TalentCandidate, UserTalent | None]:
    cand = db.get(TalentCandidate, candidate_id)
    if cand is None or cand.user_id != user.id:
        raise AppError("NOT_FOUND", "재능 후보를 찾을 수 없어요", 404)

    talent = db.get(UserTalent, cand.talent_id) if cand.talent_id else None

    if d.action == "reject":
        cand.status = CandidateStatus.REJECTED
        cand.talent_id = None
        if talent is not None:
            db.delete(talent)
        db.flush()
        return cand, None

    if d.action == "accept":
        cand.status = CandidateStatus.ACCEPTED
        name, desc, category = cand.name, cand.description, cand.category
    else:  # edit
        cand.status = CandidateStatus.EDITED
        name = (d.name or cand.name).strip()
        desc = d.description.strip() if d.description is not None else cand.description
        category = d.category or cand.category

    if talent is None:
        talent = UserTalent(user_id=user.id, source=TalentSource.AI_CONFIRMED)
        db.add(talent)
    talent.name, talent.description, talent.category = name, desc, category
    db.flush()
    embed_talent(talent)
    cand.talent_id = talent.id
    db.flush()
    return cand, talent


# ---- 직접 추가·삭제 ----

def add_manual(db: Session, user: User, name: str, category: str, description: str | None) -> UserTalent:
    t = UserTalent(user_id=user.id, name=name.strip(), category=category, description=description, source=TalentSource.MANUAL)
    db.add(t)
    db.flush()
    embed_talent(t)
    db.flush()
    return t


def remove(db: Session, user: User, talent_id: int) -> None:
    t = db.get(UserTalent, talent_id)
    if t is None or t.user_id != user.id:
        raise AppError("NOT_FOUND", "재능을 찾을 수 없어요", 404)
    for cand in db.scalars(select(TalentCandidate).where(TalentCandidate.talent_id == t.id)):
        cand.talent_id = None
        cand.status = CandidateStatus.REJECTED
    db.delete(t)
    db.flush()
