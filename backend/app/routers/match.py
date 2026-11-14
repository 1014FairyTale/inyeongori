from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB, CurrentUser
from app.errors import AppError
from app.models import User, UserTalent
from app.schemas.market import UserBrief
from app.schemas.match import MatchOut, MatchRequest, PublicProfile
from app.schemas.talent import TalentOut
from app.services import matching

router = APIRouter(tags=["match"])


@router.post("/match", response_model=MatchOut)
def match(req: MatchRequest, user: CurrentUser, db: DB) -> MatchOut:
    """'이런 도움이 필요해요' → 임베딩 유사도 + 평점 + 활동으로 상위 N명과 추천 이유."""
    return MatchOut(query=req.query, candidates=matching.match(db, req.query, limit=req.limit, exclude_user_id=user.id))


@router.get("/users/{user_id}", response_model=PublicProfile)
def public_profile(user_id: int, db: DB) -> PublicProfile:
    user = db.get(User, user_id)
    if user is None or user.is_system:
        raise AppError("NOT_FOUND", "사용자를 찾을 수 없어요", 404)
    talents = db.scalars(select(UserTalent).where(UserTalent.user_id == user_id).order_by(UserTalent.created_at)).all()
    st = matching.provider_stats(db, [user_id])[user_id]
    return PublicProfile(
        user=UserBrief.model_validate(user),
        bio=user.bio,
        talents=[TalentOut.model_validate(t) for t in talents],
        completed_count=st.completed_count,
        rating_avg=st.rating_avg,
        rating_count=st.rating_count,
    )
