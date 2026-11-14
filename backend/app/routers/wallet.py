from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select

from app.deps import DB, CurrentUser
from app.models import AccountKind, EntryType, Exchange, LedgerTransfer, Listing, TokenAccount
from app.schemas.market import LedgerItem, LedgerPage, WalletOut
from app.services import ledger

router = APIRouter(prefix="/wallet", tags=["wallet"])

LABELS = {
    EntryType.SIGNUP_BONUS: "가입 축하 토큰",
    EntryType.ESCROW_HOLD: "거래 보류",
    EntryType.PAYOUT: "거래 지급",
    EntryType.REFUND: "거래 환불",
    EntryType.REVIEW_BONUS: "후기 보너스",
    EntryType.CERT_BONUS: "인증 보너스",
    EntryType.SYSTEM_FUNDING: "시스템 적립",
}


@router.get("", response_model=WalletOut)
def wallet(user: CurrentUser, db: DB) -> WalletOut:
    w = ledger.wallet_summary(db, user.id)
    return WalletOut(available=w.available, escrow=w.escrow)


@router.get("/ledger", response_model=LedgerPage)
def ledger_history(
    user: CurrentUser,
    db: DB,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 30,
) -> LedgerPage:
    accounts = {
        a.id: a.kind for a in db.scalars(select(TokenAccount).where(TokenAccount.owner_user_id == user.id))
    }
    ids = list(accounts)
    cond = or_(LedgerTransfer.from_account_id.in_(ids), LedgerTransfer.to_account_id.in_(ids))
    total = db.scalar(select(func.count()).select_from(LedgerTransfer).where(cond)) or 0
    rows = db.execute(
        select(LedgerTransfer, Listing.title)
        .outerjoin(Exchange, Exchange.id == LedgerTransfer.exchange_id)
        .outerjoin(Listing, Listing.id == Exchange.listing_id)
        .where(cond)
        .order_by(LedgerTransfer.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    items: list[LedgerItem] = []
    for t, title in rows:
        delta = {AccountKind.AVAILABLE: 0, AccountKind.ESCROW: 0}
        if t.from_account_id in accounts:
            delta[accounts[t.from_account_id]] -= t.amount
        if t.to_account_id in accounts:
            delta[accounts[t.to_account_id]] += t.amount
        label = LABELS.get(t.entry_type, t.entry_type.value)
        if t.entry_type == EntryType.PAYOUT and delta[AccountKind.AVAILABLE] == 0:
            label = "거래 결제 완료"  # 요청자 쪽: 보류 → 지급
        elif t.entry_type == EntryType.PAYOUT:
            label = "재능 제공 수입"
        items.append(
            LedgerItem(
                id=str(t.id),
                entry_type=t.entry_type.value,
                label=label,
                available_delta=delta[AccountKind.AVAILABLE],
                escrow_delta=delta[AccountKind.ESCROW],
                exchange_id=t.exchange_id,
                listing_title=title,
                memo=t.memo,
                created_at=t.created_at,
            )
        )
    return LedgerPage(items=items, total=total, page=page, size=size)
