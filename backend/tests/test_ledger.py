from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import BONUS_POOL_INITIAL_TOKENS
from app.errors import AppError
from app.models import AccountKind, EntryType, LedgerTransfer, TokenAccount
from app.services import ledger
from tests.conftest import TestingSession, signup


def _accounts(db: Session, user_id: int) -> tuple[TokenAccount, TokenAccount]:
    return (
        ledger.get_account(db, user_id, AccountKind.AVAILABLE),
        ledger.get_account(db, user_id, AccountKind.ESCROW),
    )


def test_bootstrap_is_idempotent(db: Session) -> None:
    ledger.ensure_system_accounts(db, BONUS_POOL_INITIAL_TOKENS)
    ledger.ensure_system_accounts(db, BONUS_POOL_INITIAL_TOKENS)
    db.commit()
    system = ledger.get_system_user(db)
    pool = ledger.get_account(db, system.id, AccountKind.SYSTEM_BONUS_POOL)
    assert pool.balance == BONUS_POOL_INITIAL_TOKENS
    n = db.scalar(
        select(func.count()).select_from(LedgerTransfer).where(LedgerTransfer.entry_type == EntryType.SYSTEM_FUNDING)
    )
    assert n == 1


def test_cached_balance_matches_ledger_and_total_is_zero(client: TestClient, db: Session) -> None:
    for i in range(3):
        signup(client, f"u{i}@example.com")
    accounts = db.scalars(select(TokenAccount)).all()
    for acc in accounts:
        assert acc.balance == ledger.recomputed_balance(db, acc.id), acc.kind
    # 발행 계정이 음수로 내준 만큼 다른 계정에 있어야 해요 (토큰이 새거나 생기지 않음)
    assert sum(a.balance for a in accounts) == 0


def test_insufficient_balance_is_rejected_and_nothing_changes(client: TestClient, db: Session) -> None:
    uid = signup(client)["me"]["user"]["id"]
    available, escrow = _accounts(db, uid)
    with pytest.raises(AppError) as e:
        ledger.transfer(
            db,
            from_account_id=available.id,
            to_account_id=escrow.id,
            amount=101,
            entry_type=EntryType.ESCROW_HOLD,
            idempotency_key="t:over",
        )
    assert e.value.code == "INSUFFICIENT_BALANCE"
    db.rollback()
    available, escrow = _accounts(db, uid)
    assert (available.balance, escrow.balance) == (100, 0)


def test_same_idempotency_key_moves_tokens_once(client: TestClient, db: Session) -> None:
    uid = signup(client)["me"]["user"]["id"]
    available, escrow = _accounts(db, uid)
    for _ in range(3):
        ledger.transfer(
            db,
            from_account_id=available.id,
            to_account_id=escrow.id,
            amount=30,
            entry_type=EntryType.ESCROW_HOLD,
            idempotency_key="t:once",
        )
    db.commit()
    available, escrow = _accounts(db, uid)
    assert (available.balance, escrow.balance) == (70, 30)


def test_concurrent_spending_never_goes_negative(client: TestClient, db: Session) -> None:
    """잔액 100에서 30씩 10개 요청을 동시에 보내면 정확히 3개만 성공해야 해요."""
    uid = signup(client)["me"]["user"]["id"]
    available, escrow = _accounts(db, uid)
    src, dst = available.id, escrow.id

    def spend(i: int) -> bool:
        with TestingSession() as s:
            try:
                ledger.transfer(
                    s,
                    from_account_id=src,
                    to_account_id=dst,
                    amount=30,
                    entry_type=EntryType.ESCROW_HOLD,
                    idempotency_key=f"t:concurrent:{i}",
                )
                s.commit()
                return True
            except AppError:
                s.rollback()
                return False

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(spend, range(10)))

    assert sum(results) == 3
    db.expire_all()
    available, escrow = _accounts(db, uid)
    assert (available.balance, escrow.balance) == (10, 90)
    assert available.balance == ledger.recomputed_balance(db, available.id)
