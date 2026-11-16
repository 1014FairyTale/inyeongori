"""시드 데이터가 실제 서비스 흐름으로 만들어지고 원장이 맞는지."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import ai.structured
from app.models import Exchange, ExchangeStatus, Listing, Review, User
from seed.data import COMPLETED, PEOPLE
from seed.seed import run
from tests.conftest import TestingSession
from tests.test_exchange_flow import _assert_ledger_consistent


def test_seed_builds_consistent_demo_data(db: Session, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(ai.structured, "get_llm", ai.structured.get_llm)  # 시드가 바꾼 LLM을 테스트 후 되돌려요
    with TestingSession() as s:
        result = run(s, "demo1234!")
    assert result["users"] == len(PEOPLE) + 1
    assert db.scalar(select(func.count()).select_from(Listing)) == sum(len(x[4]) for x in PEOPLE)
    assert db.scalar(select(func.count()).select_from(Review)) == len(COMPLETED)
    assert db.scalar(select(func.count()).select_from(Exchange).where(Exchange.status == ExchangeStatus.COMPLETED)) == len(COMPLETED)
    assert db.scalar(select(func.count()).select_from(User).where(User.is_system.is_(False))) == len(PEOPLE) + 1
    _assert_ledger_consistent(db)


def test_seed_restores_llm_and_passes_through_other_features(db: Session) -> None:
    before = ai.structured.get_llm
    with TestingSession() as s:
        run(s, "demo1234!")
    assert ai.structured.get_llm is before  # 시드가 끝나면 원래 LLM으로 돌아와요


def test_seed_if_empty_only_runs_once(monkeypatch) -> None:  # noqa: ANN001
    import seed.seed as seed_mod

    monkeypatch.setattr(seed_mod, "SessionLocal", TestingSession)
    assert seed_mod.seed_if_empty() is True
    assert seed_mod.seed_if_empty() is False


def test_seed_users_can_login(client, db: Session, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(ai.structured, "get_llm", ai.structured.get_llm)
    with TestingSession() as s:
        run(s, "demo1234!")
    r = client.post("/api/v1/auth/login", json={"email": "demo@example.com", "password": "demo1234!"})
    assert r.status_code == 200
    assert r.json()["me"]["wallet"]["available"] == 100


def test_seed_reset_once_runs_only_for_a_new_key(monkeypatch) -> None:  # noqa: ANN001
    """SEED_RESET_KEY: 같은 키로는 한 번만 지우고 다시 넣어요. 키를 바꾸면 다시 한 번."""
    import seed.seed as seed_mod

    monkeypatch.setattr(seed_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(ai.structured, "get_llm", ai.structured.get_llm)
    assert seed_mod.reset_once("v1") is True
    with TestingSession() as s:
        # 시드 뒤에 사용자가 직접 만든 계정이 있어도, 같은 키로는 지우지 않아요
        s.add(User(email="new@example.org", password_hash="x", nickname="새사용자"))
        s.commit()
    assert seed_mod.reset_once("v1") is False
    with TestingSession() as s:
        assert s.scalar(select(func.count()).select_from(User).where(User.email == "new@example.org")) == 1
    assert seed_mod.reset_once("v2") is True
    with TestingSession() as s:
        assert s.scalar(select(func.count()).select_from(User).where(User.email == "new@example.org")) == 0
        assert s.scalar(select(func.count()).select_from(User).where(User.is_system.is_(False))) == len(PEOPLE) + 1
