"""거래 상태 머신. 상태 흐름은 app/models/market.py 상단 주석 참고.

동시성 규칙
- 상태를 바꾸는 모든 함수는 먼저 거래 행을 SELECT ... FOR UPDATE로 잠가요.
  같은 거래에 대한 동시 요청(예: 양측이 동시에 '완료')은 이 잠금으로 줄을 서요.
- 토큰 이동은 ledger.transfer()만 쓰고, 멱등 키는 escrow:/payout:/refund:{exchange_id}.
  상태 검사와 멱등 키로 이중 지급·이중 환불을 막아요.
- 함수들은 커밋하지 않아요. 라우터가 성공 시 커밋, 실패 시 롤백해요.
"""

from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import (
    AccountKind,
    Agreement,
    EntryType,
    Exchange,
    ExchangeMessage,
    ExchangeStatus,
    Listing,
    ListingStatus,
    MessageKind,
    User,
)
from app.schemas.market import AgreementTerms, ExchangeAction
from app.services import ledger, review_policy

Role = Literal["requester", "provider"]


def _now() -> datetime:
    return datetime.now(UTC)


def _invalid_state(ex: Exchange, msg: str = "지금 상태에서는 할 수 없는 요청이에요") -> AppError:
    return AppError("INVALID_STATE", msg, 409, {"status": ex.status.value})


def lock_exchange(db: Session, exchange_id: int) -> Exchange:
    ex = db.scalar(select(Exchange).where(Exchange.id == exchange_id).with_for_update())
    if ex is None:
        raise AppError("NOT_FOUND", "거래를 찾을 수 없어요", 404)
    return ex


def role_of(ex: Exchange, user: User) -> Role:
    if user.id == ex.requester_id:
        return "requester"
    if user.id == ex.provider_id:
        return "provider"
    # 남의 거래는 존재 여부도 알려 주지 않아요
    raise AppError("NOT_FOUND", "거래를 찾을 수 없어요", 404)


def current_agreement(db: Session, exchange_id: int) -> Agreement:
    ag = db.scalar(
        select(Agreement).where(Agreement.exchange_id == exchange_id).order_by(Agreement.version.desc()).limit(1)
    )
    if ag is None:
        raise AppError("AGREEMENT_MISSING", "합의서를 찾을 수 없어요", 500)
    return ag


def agreement_versions(db: Session, exchange_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Agreement).where(Agreement.exchange_id == exchange_id)) or 0


def _new_agreement(
    db: Session, ex: Exchange, proposer: User, role: Role, terms: AgreementTerms, ai_generated: bool, version: int
) -> Agreement:
    now = _now()
    ag = Agreement(
        exchange_id=ex.id,
        version=version,
        proposed_by=proposer.id,
        terms=terms.model_dump(),
        ai_generated=ai_generated,
        requester_agreed_at=now if role == "requester" else None,
        provider_agreed_at=now if role == "provider" else None,
    )
    db.add(ag)
    db.flush()
    return ag


def post_system(db: Session, ex: Exchange, body: str) -> None:
    """거래 채팅에 상태 변경 안내를 남겨요 (채팅이 열린 뒤에만 보여요)."""
    db.add(ExchangeMessage(exchange_id=ex.id, sender_id=None, kind=MessageKind.SYSTEM, body=body))


def _accounts(db: Session, user_id: int) -> tuple[int, int]:
    return (
        ledger.get_account(db, user_id, AccountKind.AVAILABLE).id,
        ledger.get_account(db, user_id, AccountKind.ESCROW).id,
    )


# ---- 요청 ----

def create_request(
    db: Session, requester: User, listing_id: int, terms: AgreementTerms, ai_generated: bool = False
) -> Exchange:
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise AppError("NOT_FOUND", "재능 상품을 찾을 수 없어요", 404)
    if listing.status != ListingStatus.ACTIVE:
        raise AppError("LISTING_INACTIVE", "지금은 요청을 받지 않는 상품이에요", 409)
    if listing.provider_id == requester.id:
        raise AppError("SELF_REQUEST", "내 상품에는 요청할 수 없어요", 400)
    provider = db.get(User, listing.provider_id)
    if provider is not None and review_policy.is_blocked(db, provider):
        # 밀린 후기 때문에 이용이 막힌 제공자는 새 요청을 받을 수 없어요
        raise AppError("LISTING_INACTIVE", "지금은 요청을 받지 않는 재능이에요", 409)

    # 요청 단계에서는 잠그지 않고 안내만 해요. 실제 보류는 수락 시점에 잠금과 함께 다시 확인해요.
    wallet = ledger.wallet_summary(db, requester.id)
    if wallet.available < listing.price_tokens:
        raise AppError(
            "INSUFFICIENT_BALANCE",
            "토큰이 부족해요",
            409,
            {"balance": wallet.available, "required": listing.price_tokens},
        )

    ex = Exchange(
        listing_id=listing.id,
        requester_id=requester.id,
        provider_id=listing.provider_id,
        price_tokens=listing.price_tokens,
        status=ExchangeStatus.REQUESTED,
    )
    db.add(ex)
    db.flush()
    _new_agreement(db, ex, requester, "requester", terms, ai_generated, version=1)
    return ex


def propose_terms(db: Session, user: User, exchange_id: int, terms: AgreementTerms, ai_generated: bool) -> Exchange:
    """조건 수정 제안. 새 버전이 생기고, 제안한 사람만 동의한 상태가 돼요."""
    ex = lock_exchange(db, exchange_id)
    role = role_of(ex, user)
    if ex.status != ExchangeStatus.REQUESTED:
        raise _invalid_state(ex, "수락된 뒤에는 조건을 바꿀 수 없어요")
    version = current_agreement(db, ex.id).version + 1
    _new_agreement(db, ex, user, role, terms, ai_generated, version=version)
    return ex


def agree(db: Session, user: User, exchange_id: int) -> Exchange:
    """현재 합의서에 동의. 양측이 모두 동의하면 수락되고 요청자의 토큰이 보류돼요."""
    ex = lock_exchange(db, exchange_id)
    role = role_of(ex, user)
    if ex.status != ExchangeStatus.REQUESTED:
        raise _invalid_state(ex)

    ag = current_agreement(db, ex.id)
    now = _now()
    if role == "requester" and ag.requester_agreed_at is None:
        ag.requester_agreed_at = now
    if role == "provider" and ag.provider_agreed_at is None:
        ag.provider_agreed_at = now

    if ag.requester_agreed_at and ag.provider_agreed_at:
        src, dst = _accounts(db, ex.requester_id)
        try:
            ledger.transfer(
                db,
                from_account_id=src,
                to_account_id=dst,
                amount=ex.price_tokens,
                entry_type=EntryType.ESCROW_HOLD,
                idempotency_key=f"escrow:{ex.id}",
                exchange_id=ex.id,
                memo="거래 수락 - 토큰 보류",
            )
        except AppError as e:
            if e.code == "INSUFFICIENT_BALANCE":
                msg = "토큰이 부족해서 수락할 수 없어요" if role == "requester" else "요청자의 토큰이 부족해서 지금은 수락할 수 없어요"
                raise AppError("INSUFFICIENT_BALANCE", msg, 409, e.details) from e
            raise
        ex.status = ExchangeStatus.ACCEPTED
        ex.accepted_at = now
        post_system(
            db,
            ex,
            f"거래가 시작됐어요! {ex.price_tokens}토큰이 안전하게 보류됐어요. "
            "합의서를 바탕으로 일정, 만날 장소나 온라인 도구 같은 진행 방식을 여기서 이야기해 보세요.",
        )
    return ex


def reject_or_withdraw(db: Session, user: User, exchange_id: int) -> Exchange:
    """수락 전: 제공자는 거절, 요청자는 철회. 토큰은 움직이지 않아요."""
    ex = lock_exchange(db, exchange_id)
    role = role_of(ex, user)
    if ex.status != ExchangeStatus.REQUESTED:
        raise _invalid_state(ex)
    ex.status = ExchangeStatus.REJECTED if role == "provider" else ExchangeStatus.CANCELLED
    ex.cancelled_by = user.id
    ex.closed_at = _now()
    return ex


# ---- 수락 후 ----

def _refund(db: Session, ex: Exchange) -> None:
    available, escrow = _accounts(db, ex.requester_id)
    ledger.transfer(
        db,
        from_account_id=escrow,
        to_account_id=available,
        amount=ex.price_tokens,
        entry_type=EntryType.REFUND,
        idempotency_key=f"refund:{ex.id}",
        exchange_id=ex.id,
        memo="거래 취소 - 환불",
    )


def cancel(db: Session, user: User, exchange_id: int) -> Exchange:
    """수락 후 취소 (D6).
    - 제공자: 즉시 취소 + 요청자에게 전액 환불. 요청자의 취소 요청이 있으면 그 승인도 이걸로 해요.
    - 요청자: 취소 '요청'만 돼요. 제공자가 승인해야 환불돼요.
    """
    ex = lock_exchange(db, exchange_id)
    role = role_of(ex, user)

    if ex.status == ExchangeStatus.REQUESTED:
        raise _invalid_state(ex, "수락 전에는 거절 또는 철회를 이용해 주세요")

    if role == "provider" and ex.status in (ExchangeStatus.ACCEPTED, ExchangeStatus.CANCEL_REQUESTED):
        _refund(db, ex)
        approved = ex.status == ExchangeStatus.CANCEL_REQUESTED
        ex.status = ExchangeStatus.CANCELLED
        ex.cancelled_by = ex.cancel_requested_by or user.id
        ex.closed_at = _now()
        post_system(
            db,
            ex,
            ("제공자가 취소 요청을 승인했어요. " if approved else "제공자가 거래를 취소했어요. ")
            + f"보류된 {ex.price_tokens}토큰은 요청자에게 전액 환불됐어요.",
        )
        return ex

    if role == "requester" and ex.status == ExchangeStatus.ACCEPTED:
        ex.status = ExchangeStatus.CANCEL_REQUESTED
        ex.cancel_requested_by = user.id
        post_system(db, ex, "요청자가 거래 취소를 요청했어요. 제공자가 승인하면 토큰이 환불돼요.")
        return ex

    if role == "requester" and ex.status == ExchangeStatus.CANCEL_REQUESTED:
        raise _invalid_state(ex, "이미 취소를 요청했어요. 제공자의 응답을 기다려 주세요")

    raise _invalid_state(ex)


def decline_cancel(db: Session, user: User, exchange_id: int) -> Exchange:
    ex = lock_exchange(db, exchange_id)
    role = role_of(ex, user)
    if role != "provider" or ex.status != ExchangeStatus.CANCEL_REQUESTED:
        raise _invalid_state(ex)
    ex.status = ExchangeStatus.ACCEPTED
    ex.cancel_requested_by = None
    post_system(db, ex, "제공자가 취소 요청을 거절해서 거래가 계속 진행돼요.")
    return ex


def complete(db: Session, user: User, exchange_id: int) -> Exchange:
    """완료 확인. 양측이 모두 확인하면 보류된 토큰이 제공자에게 지급돼요."""
    ex = lock_exchange(db, exchange_id)
    role = role_of(ex, user)
    if ex.status != ExchangeStatus.ACCEPTED:
        raise _invalid_state(ex)

    now = _now()
    newly = False
    if role == "requester" and ex.requester_done_at is None:
        ex.requester_done_at = now
        newly = True
    if role == "provider" and ex.provider_done_at is None:
        ex.provider_done_at = now
        newly = True

    if ex.requester_done_at and ex.provider_done_at:
        _, escrow = _accounts(db, ex.requester_id)
        provider_available, _ = _accounts(db, ex.provider_id)
        ledger.transfer(
            db,
            from_account_id=escrow,
            to_account_id=provider_available,
            amount=ex.price_tokens,
            entry_type=EntryType.PAYOUT,
            idempotency_key=f"payout:{ex.id}",
            exchange_id=ex.id,
            memo="거래 완료 - 지급",
        )
        ex.status = ExchangeStatus.COMPLETED
        ex.completed_at = now
        post_system(db, ex, f"양쪽이 완료를 확인해서 {ex.price_tokens}토큰이 지급됐어요. 수고하셨어요! 요청자는 후기를 남겨 주세요.")
    elif newly:
        who = "요청자" if role == "requester" else "제공자"
        post_system(db, ex, f"{who}가 완료를 확인했어요. 상대방도 확인하면 토큰이 지급돼요.")
    return ex


# ---- 화면용 ----

def available_actions(ex: Exchange, role: Role, ag: Agreement) -> list[ExchangeAction]:
    acts: list[ExchangeAction] = []
    if ex.status == ExchangeStatus.REQUESTED:
        mine_agreed = ag.requester_agreed_at if role == "requester" else ag.provider_agreed_at
        if not mine_agreed:
            acts.append("agree")
        acts.append("propose")
        acts.append("reject" if role == "provider" else "withdraw")
    elif ex.status == ExchangeStatus.ACCEPTED:
        mine_done = ex.requester_done_at if role == "requester" else ex.provider_done_at
        if not mine_done:
            acts.append("complete")
        acts.append("cancel" if role == "provider" else "request_cancel")
    elif ex.status == ExchangeStatus.CANCEL_REQUESTED and role == "provider":
        acts.extend(["approve_cancel", "decline_cancel"])
    return acts
