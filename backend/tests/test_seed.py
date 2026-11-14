"""시드 데이터가 실제 서비스 흐름으로 만들어지고 원장이 맞는지."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import ai.structured
from app.models import Exchange, ExchangeStatus, Listing, Review, User
from seed.data import COMPLETED, STUDENTS
from seed.seed import run
from tests.conftest import TestingSession
from tests.test_exchange_flow import _assert_ledger_consistent


def test_seed_builds_consistent_demo_data(db: Session, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(ai.structured, "get_llm", ai.structured.get_llm)  # 시드가 바꾼 LLM을 테스트 후 되돌려요
    with TestingSession() as s:
        result = run(s, "demo1234!")
    assert result["users"] == len(STUDENTS) + 1
    assert db.scalar(select(func.count()).select_from(Listing)) == sum(len(x[6]) for x in STUDENTS)
    assert db.scalar(select(func.count()).select_from(Review)) == len(COMPLETED)
    assert db.scalar(select(func.count()).select_from(Exchange).where(Exchange.status == ExchangeStatus.COMPLETED)) == len(COMPLETED)
    assert db.scalar(select(func.count()).select_from(User).where(User.is_system.is_(False))) == len(STUDENTS) + 1
    _assert_ledger_consistent(db)


def test_seed_users_can_login(client, db: Session, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(ai.structured, "get_llm", ai.structured.get_llm)
    with TestingSession() as s:
        run(s, "demo1234!")
    r = client.post("/api/v1/auth/login", json={"email": "demo@example.com", "password": "demo1234!"})
    assert r.status_code == 200
    assert r.json()["me"]["wallet"]["available"] == 100
