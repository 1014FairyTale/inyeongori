"""토큰 이동의 유일한 통로.

규칙
- 잔액(balance)은 transfer() 안에서만 바꿔요. 다른 곳에서 balance를 직접 수정하지 마세요.
- transfer()는 커밋하지 않아요. 호출한 쪽의 트랜잭션에 포함돼서, 상위 작업(예: 가입)이
  실패하면 토큰 이동도 같이 롤백돼요.
- 동시성: 두 계정 행을 id 오름차순으로 SELECT ... FOR UPDATE 해서 데드락 없이 직렬화해요.
- 멱등성: idempotency_key가 같은 이동이 이미 있으면 새로 기록하지 않고 기존 기록을 돌려줘요.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import AccountKind, EntryType, LedgerTransfer, TokenAccount, User


@dataclass(frozen=True)
class WalletSummary:
    available: int
    escrow: int


def _lock_accounts(db: Session, *account_ids: int) -> dict[int, TokenAccount]:
    rows = db.scalars(
        select(TokenAccount)
        .where(TokenAccount.id.in_(account_ids))
        .order_by(TokenAccount.id)
        .with_for_update()
    ).all()
    found = {a.id: a for a in rows}
    missing = set(account_ids) - found.keys()
    if missing:
        raise AppError("ACCOUNT_NOT_FOUND", "토큰 계정을 찾을 수 없어요", 500, {"ids": sorted(missing)})
    return found


def transfer(
    db: Session,
    *,
    from_account_id: int,
    to_account_id: int,
    amount: int,
    entry_type: EntryType,
    idempotency_key: str,
    exchange_id: int | None = None,
    memo: str | None = None,
) -> LedgerTransfer:
    if amount <= 0:
        raise AppError("INVALID_AMOUNT", "토큰 수량은 1 이상이어야 해요")
    if from_account_id == to_account_id:
        raise AppError("INVALID_TRANSFER", "같은 계정끼리는 옮길 수 없어요")

    accounts = _lock_accounts(db, from_account_id, to_account_id)

    # 잠금을 잡은 뒤에 멱등 키를 확인해야 동시 요청에서도 중복이 생기지 않아요
    existing = db.scalar(select(LedgerTransfer).where(LedgerTransfer.idempotency_key == idempotency_key))
    if existing is not None:
        return existing

    src, dst = accounts[from_account_id], accounts[to_account_id]
    if src.kind != AccountKind.SYSTEM_ISSUANCE and src.balance < amount:
        raise AppError(
            "INSUFFICIENT_BALANCE",
            "토큰이 부족해요",
            409,
            {"balance": src.balance, "required": amount},
        )

    src.balance -= amount
    dst.balance += amount
    record = LedgerTransfer(
        entry_type=entry_type,
        from_account_id=src.id,
        to_account_id=dst.id,
        amount=amount,
        exchange_id=exchange_id,
        idempotency_key=idempotency_key,
        memo=memo,
    )
    db.add(record)
    db.flush()
    return record


# ---- 계정 조회 ----

def get_account(db: Session, user_id: int, kind: AccountKind) -> TokenAccount:
    acc = db.scalar(
        select(TokenAccount).where(TokenAccount.owner_user_id == user_id, TokenAccount.kind == kind)
    )
    if acc is None:
        raise AppError("ACCOUNT_NOT_FOUND", "토큰 계정을 찾을 수 없어요", 500)
    return acc


def create_user_accounts(db: Session, user_id: int) -> tuple[TokenAccount, TokenAccount]:
    available = TokenAccount(owner_user_id=user_id, kind=AccountKind.AVAILABLE, balance=0)
    escrow = TokenAccount(owner_user_id=user_id, kind=AccountKind.ESCROW, balance=0)
    db.add_all([available, escrow])
    db.flush()
    return available, escrow


def wallet_summary(db: Session, user_id: int) -> WalletSummary:
    rows = db.execute(
        select(TokenAccount.kind, TokenAccount.balance).where(TokenAccount.owner_user_id == user_id)
    ).all()
    by_kind = {k: b for k, b in rows}
    return WalletSummary(
        available=by_kind.get(AccountKind.AVAILABLE, 0),
        escrow=by_kind.get(AccountKind.ESCROW, 0),
    )


def recomputed_balance(db: Session, account_id: int) -> int:
    """원장만으로 다시 계산한 잔액. 캐시(balance)와 같은지 검증할 때 써요."""
    incoming = db.scalar(
        select(func.coalesce(func.sum(LedgerTransfer.amount), 0)).where(
            LedgerTransfer.to_account_id == account_id
        )
    )
    outgoing = db.scalar(
        select(func.coalesce(func.sum(LedgerTransfer.amount), 0)).where(
            LedgerTransfer.from_account_id == account_id
        )
    )
    return int(incoming) - int(outgoing)


# ---- 시스템 계정 ----

SYSTEM_EMAIL = "system@inyeongori.local"


def get_system_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.is_system.is_(True)))
    if user is None:
        raise AppError("SYSTEM_NOT_READY", "시스템 계정이 준비되지 않았어요", 500)
    return user


def ensure_system_accounts(db: Session, bonus_pool_initial: int) -> None:
    """시스템 사용자·발행 계정·보너스 풀을 만들고 풀에 초기 토큰을 적립해요. 여러 번 불러도 안전해요."""
    user = db.scalar(select(User).where(User.is_system.is_(True)))
    if user is None:
        user = User(
            email=SYSTEM_EMAIL,
            password_hash="!",  # 로그인 불가
            nickname="인연고리",
            is_system=True,
        )
        db.add(user)
        db.flush()

    accounts = {
        a.kind: a
        for a in db.scalars(select(TokenAccount).where(TokenAccount.owner_user_id == user.id))
    }
    for kind in (AccountKind.SYSTEM_ISSUANCE, AccountKind.SYSTEM_BONUS_POOL):
        if kind not in accounts:
            acc = TokenAccount(owner_user_id=user.id, kind=kind, balance=0)
            db.add(acc)
            db.flush()
            accounts[kind] = acc

    transfer(
        db,
        from_account_id=accounts[AccountKind.SYSTEM_ISSUANCE].id,
        to_account_id=accounts[AccountKind.SYSTEM_BONUS_POOL].id,
        amount=bonus_pool_initial,
        entry_type=EntryType.SYSTEM_FUNDING,
        idempotency_key="bootstrap:bonus_pool",
        memo="보너스 풀 초기 적립",
    )
