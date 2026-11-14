from fastapi import APIRouter, status
from sqlalchemy import select

from app.deps import DB, CurrentUser
from app.models import DiscoverySession, TalentCandidate, UserTalent
from app.schemas.talent import (
    CandidateDecision,
    CandidateOut,
    DecisionOut,
    DiscoveryAnswers,
    DiscoveryCreate,
    DiscoverySessionOut,
    TalentCreate,
    TalentOut,
)
from app.services import discovery

router = APIRouter(tags=["discovery"])


def _cand_out(db: DB, c: TalentCandidate) -> CandidateOut:
    out = CandidateOut.model_validate(c)
    talent = db.get(UserTalent, c.talent_id) if c.talent_id else None
    if talent is not None:
        out.final_name = talent.name
        out.final_description = talent.description
    return out


def _session_out(db: DB, s: DiscoverySession) -> DiscoverySessionOut:
    return DiscoverySessionOut(
        id=s.id,
        intro_text=s.intro_text,
        answers=DiscoveryAnswers.model_validate(s.answers),
        encouragement=s.encouragement,
        ai_provider=s.ai_provider,
        candidates=[_cand_out(db, c) for c in discovery.candidates_of(db, s.id)],
        created_at=s.created_at,
    )


@router.post("/discovery/sessions", response_model=DiscoverySessionOut, status_code=status.HTTP_201_CREATED)
def create_session(req: DiscoveryCreate, user: CurrentUser, db: DB) -> DiscoverySessionOut:
    """AI로 재능 후보를 찾아요. 실패하면 502 AI_FAILED (화면에서 '다시 시도')."""
    s = discovery.run_discovery(db, user, req)
    db.commit()
    return _session_out(db, s)


@router.get("/discovery/sessions/latest", response_model=DiscoverySessionOut | None)
def latest(user: CurrentUser, db: DB) -> DiscoverySessionOut | None:
    s = discovery.latest_session(db, user)
    return _session_out(db, s) if s else None


@router.post("/discovery/candidates/{candidate_id}/decision", response_model=DecisionOut)
def decide(candidate_id: int, req: CandidateDecision, user: CurrentUser, db: DB) -> DecisionOut:
    cand, talent = discovery.decide(db, user, candidate_id, req)
    db.commit()
    return DecisionOut(
        candidate=_cand_out(db, cand),
        talent=TalentOut.model_validate(talent) if talent else None,
    )


@router.get("/users/me/talents", response_model=list[TalentOut])
def my_talents(user: CurrentUser, db: DB) -> list[TalentOut]:
    return list_talents(user.id, db)


@router.get("/users/{user_id}/talents", response_model=list[TalentOut])
def list_talents(user_id: int, db: DB) -> list[TalentOut]:
    rows = db.scalars(select(UserTalent).where(UserTalent.user_id == user_id).order_by(UserTalent.created_at)).all()
    return [TalentOut.model_validate(t) for t in rows]


@router.post("/users/me/talents", response_model=TalentOut, status_code=status.HTTP_201_CREATED)
def add_talent(req: TalentCreate, user: CurrentUser, db: DB) -> TalentOut:
    t = discovery.add_manual(db, user, req.name, req.category, req.description)
    db.commit()
    return TalentOut.model_validate(t)


@router.delete("/users/me/talents/{talent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_talent(talent_id: int, user: CurrentUser, db: DB) -> None:
    discovery.remove(db, user, talent_id)
    db.commit()

