from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.deps import DB, CurrentUser
from app.errors import AppError
from app.models import Exchange, ExchangeStatus, Listing, Review, User
from app.schemas.market import (
    AgreementOut,
    AgreementTerms,
    ExchangeCreate,
    ExchangeOut,
    ExchangeSummary,
    ProposeTerms,
    UserBrief,
)
from app.services import exchange_flow as flow

router = APIRouter(prefix="/exchanges", tags=["exchanges"])


def _has_review(db: Session, ex: Exchange) -> bool:
    return ex.status == ExchangeStatus.COMPLETED and db.scalar(select(Review.id).where(Review.exchange_id == ex.id)) is not None


def build_out(db: Session, ex: Exchange, user: User) -> ExchangeOut:
    role = flow.role_of(ex, user)
    ag = flow.current_agreement(db, ex.id)
    listing = db.get(Listing, ex.listing_id) if ex.listing_id else None
    requester = db.get(User, ex.requester_id)
    provider = db.get(User, ex.provider_id)
    assert requester is not None and provider is not None
    has_review = _has_review(db, ex)
    actions = flow.available_actions(ex, role, ag)
    if ex.status == ExchangeStatus.COMPLETED and role == "requester" and not has_review:
        actions.append("review")
    return ExchangeOut(
        id=ex.id,
        status=ex.status,
        price_tokens=ex.price_tokens,
        listing_id=ex.listing_id,
        listing_title=listing.title if listing else None,
        category=listing.category if listing else None,
        requester=UserBrief.model_validate(requester),
        provider=UserBrief.model_validate(provider),
        my_role=role,
        requester_done=ex.requester_done_at is not None,
        provider_done=ex.provider_done_at is not None,
        cancel_requested_by=ex.cancel_requested_by,
        agreement=AgreementOut(
            version=ag.version,
            terms=AgreementTerms.model_validate(ag.terms),
            ai_generated=ag.ai_generated,
            proposed_by=ag.proposed_by,
            requester_agreed=ag.requester_agreed_at is not None,
            provider_agreed=ag.provider_agreed_at is not None,
            created_at=ag.created_at,
        ),
        agreement_versions=flow.agreement_versions(db, ex.id),
        actions=actions,
        has_review=has_review,
        created_at=ex.created_at,
        accepted_at=ex.accepted_at,
        completed_at=ex.completed_at,
        closed_at=ex.closed_at,
    )


def _run(db: Session, user: User, fn: Callable[[], Exchange]) -> ExchangeOut:
    """상태 변경 유스케이스 실행 → 커밋 → 최신 상태 반환. 실패하면 get_db가 롤백해요."""
    ex = fn()
    db.commit()
    db.refresh(ex)
    return build_out(db, ex, user)


@router.post("", response_model=ExchangeOut, status_code=status.HTTP_201_CREATED)
def create_exchange(req: ExchangeCreate, user: CurrentUser, db: DB) -> ExchangeOut:
    return _run(db, user, lambda: flow.create_request(db, user, req.listing_id, req.terms, req.ai_generated))


@router.get("", response_model=list[ExchangeSummary])
def list_exchanges(
    user: CurrentUser,
    db: DB,
    role: Annotated[Literal["all", "sent", "received"], Query()] = "all",
) -> list[ExchangeSummary]:
    stmt = select(Exchange)
    if role == "sent":
        stmt = stmt.where(Exchange.requester_id == user.id)
    elif role == "received":
        stmt = stmt.where(Exchange.provider_id == user.id)
    else:
        stmt = stmt.where(or_(Exchange.requester_id == user.id, Exchange.provider_id == user.id))
    exchanges = db.scalars(stmt.order_by(Exchange.created_at.desc(), Exchange.id.desc()).limit(100)).all()

    out: list[ExchangeSummary] = []
    for ex in exchanges:
        my_role = flow.role_of(ex, user)
        counterpart = db.get(User, ex.provider_id if my_role == "requester" else ex.requester_id)
        listing = db.get(Listing, ex.listing_id) if ex.listing_id else None
        ag = flow.current_agreement(db, ex.id)
        acts = flow.available_actions(ex, my_role, ag)
        needs = any(a in acts for a in ("agree", "complete", "approve_cancel")) or (
            my_role == "requester" and ex.status == ExchangeStatus.COMPLETED and not _has_review(db, ex)
        )
        assert counterpart is not None
        out.append(
            ExchangeSummary(
                id=ex.id,
                status=ex.status,
                price_tokens=ex.price_tokens,
                listing_title=listing.title if listing else None,
                counterpart=UserBrief.model_validate(counterpart),
                my_role=my_role,
                needs_my_action=needs,
                created_at=ex.created_at,
            )
        )
    return out


@router.get("/{exchange_id}", response_model=ExchangeOut)
def get_exchange(exchange_id: int, user: CurrentUser, db: DB) -> ExchangeOut:
    ex = db.get(Exchange, exchange_id)
    if ex is None:
        raise AppError("NOT_FOUND", "거래를 찾을 수 없어요", 404)
    return build_out(db, ex, user)


@router.post("/{exchange_id}/agreement", response_model=ExchangeOut)
def propose(exchange_id: int, req: ProposeTerms, user: CurrentUser, db: DB) -> ExchangeOut:
    return _run(db, user, lambda: flow.propose_terms(db, user, exchange_id, req.terms, req.ai_generated))


@router.post("/{exchange_id}/agree", response_model=ExchangeOut)
def agree(exchange_id: int, user: CurrentUser, db: DB) -> ExchangeOut:
    return _run(db, user, lambda: flow.agree(db, user, exchange_id))


@router.post("/{exchange_id}/reject", response_model=ExchangeOut)
def reject(exchange_id: int, user: CurrentUser, db: DB) -> ExchangeOut:
    """수락 전 제공자 거절 / 요청자 철회"""
    return _run(db, user, lambda: flow.reject_or_withdraw(db, user, exchange_id))


@router.post("/{exchange_id}/cancel", response_model=ExchangeOut)
def cancel(exchange_id: int, user: CurrentUser, db: DB) -> ExchangeOut:
    """수락 후 취소. 제공자는 즉시 환불(취소 요청 승인 포함), 요청자는 취소 요청."""
    return _run(db, user, lambda: flow.cancel(db, user, exchange_id))


@router.post("/{exchange_id}/cancel/decline", response_model=ExchangeOut)
def decline_cancel(exchange_id: int, user: CurrentUser, db: DB) -> ExchangeOut:
    return _run(db, user, lambda: flow.decline_cancel(db, user, exchange_id))


@router.post("/{exchange_id}/complete", response_model=ExchangeOut)
def complete(exchange_id: int, user: CurrentUser, db: DB) -> ExchangeOut:
    return _run(db, user, lambda: flow.complete(db, user, exchange_id))
