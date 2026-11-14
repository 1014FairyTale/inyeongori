"""후기 + AI 후기 분석 + 보너스 토큰 (D5-A)."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai.providers.base import AIError
from app.models import AccountKind, EntryType, LedgerTransfer, TokenAccount
from app.services import ledger
from tests.conftest import Actor
from tests.test_discovery import FakeLLM, _use_llm
from tests.test_exchange_flow import _assert_ledger_consistent

GOOD = {"rating": 5, "good_text": "하나하나 이유까지 설명해 주셔서 정말 이해가 잘 됐어요", "bad_text": "시간이 조금 짧았어요"}


def _analysis(score: int, flags: list[str] | None = None) -> str:
    return json.dumps(
        {"contribution_score": score, "summary": "요약이에요", "reasons": ["근거가 있어요"], "flags": flags or []},
        ensure_ascii=False,
    )


def _completed(provider: Actor, requester: Actor, price: int = 50) -> int:
    ex = requester.request(provider.create_listing(price)).json()
    provider.post(f"/exchanges/{ex['id']}/agree")
    requester.post(f"/exchanges/{ex['id']}/complete")
    r = provider.post(f"/exchanges/{ex['id']}/complete")
    assert r.json()["status"] == "completed", r.text
    return ex["id"]


def _pool(db: Session) -> int:
    db.expire_all()
    system = ledger.get_system_user(db)
    return ledger.get_account(db, system.id, AccountKind.SYSTEM_BONUS_POOL).balance


# ---- 기본 흐름 ----

def test_good_review_pays_bonus_from_pool(client: TestClient, db: Session) -> None:
    provider = Actor(client, "p@example.com", "테트리스고수")
    learner = Actor(client, "l@example.com", "새내기")
    ex_id = _completed(provider, learner, price=50)
    assert "review" in learner.get(f"/exchanges/{ex_id}").json()["actions"]
    pool_before = _pool(db)

    r = learner.post(f"/exchanges/{ex_id}/review", GOOD)
    assert r.status_code == 201, r.text
    a = r.json()["analysis"]
    assert a["contribution_score"] == 88  # mock
    assert a["reasons"]
    assert a["eligible"] is True
    assert a["base_bonus"] == 10  # 50의 20%
    assert a["final_bonus"] == 10
    assert provider.wallet() == (160, 0)  # 100 + 50 + 보너스 10
    assert _pool(db) == pool_before - 10
    assert "review" not in learner.get(f"/exchanges/{ex_id}").json()["actions"]

    history = provider.get("/wallet/ledger").json()["items"]
    assert history[0]["entry_type"] == "review_bonus" and history[0]["available_delta"] == 10
    _assert_ledger_consistent(db)


def test_tier_and_per_exchange_cap(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = Actor(client, "p@example.com", "제공자")
    a = Actor(client, "a@example.com", "요청자1")
    b = Actor(client, "b@example.com", "요청자2")

    _use_llm(monkeypatch, FakeLLM([_analysis(75)]))  # 70~84점 → 10%
    r = a.post(f"/exchanges/{_completed(provider, a, price=40)}/review", GOOD).json()["analysis"]
    assert (r["base_bonus"], r["final_bonus"]) == (4, 4)

    _use_llm(monkeypatch, FakeLLM([_analysis(95)]))  # 20% of 90 = 18 → 상한 10
    r = b.post(f"/exchanges/{_completed(provider, b, price=90)}/review", GOOD).json()["analysis"]
    assert (r["base_bonus"], r["final_bonus"]) == (18, 10)
    assert any(x["rule"] == "per_exchange_cap" for x in r["adjustments"])


@pytest.mark.parametrize(
    ("score", "review", "reason"),
    [
        (60, GOOD, "기여도 점수"),
        (90, {**GOOD, "rating": 3}, "별점"),
        (90, {"rating": 5, "good_text": "좋아요", "bad_text": ""}, "후기가"),
    ],
)
def test_not_eligible(client: TestClient, monkeypatch: pytest.MonkeyPatch, score: int, review: dict, reason: str) -> None:
    provider = Actor(client, "p@example.com", "제공자")
    learner = Actor(client, "l@example.com", "요청자")
    _use_llm(monkeypatch, FakeLLM([_analysis(score)]))
    a = learner.post(f"/exchanges/{_completed(provider, learner)}/review", review).json()["analysis"]
    assert a["eligible"] is False and a["final_bonus"] == 0
    assert any(reason in x["message"] for x in a["adjustments"])
    assert provider.wallet() == (150, 0)


# ---- 남용 방지 ----

def test_repeat_pair_bonus_is_reduced_then_blocked(client: TestClient) -> None:
    provider = Actor(client, "p@example.com", "제공자")
    friend = Actor(client, "f@example.com", "친구")
    bonuses = []
    for _ in range(3):
        ex_id = _completed(provider, friend, price=20)  # 20의 20% = 4
        bonuses.append(friend.post(f"/exchanges/{ex_id}/review", GOOD).json()["analysis"]["final_bonus"])
    assert bonuses == [4, 2, 0]


def test_repeat_pair_counts_both_directions(client: TestClient) -> None:
    a = Actor(client, "a@example.com", "A")
    b = Actor(client, "b@example.com", "B")
    first = _completed(a, b, price=20)  # A가 B를 도움
    b.post(f"/exchanges/{first}/review", GOOD)
    second = _completed(b, a, price=20)  # B가 A를 도움 (역방향)
    r = a.post(f"/exchanges/{second}/review", GOOD).json()["analysis"]
    assert r["final_bonus"] == 2
    assert any(x["rule"] == "repeat_pair" for x in r["adjustments"])


def test_daily_cap_per_provider(client: TestClient) -> None:
    provider = Actor(client, "p@example.com", "인기제공자")
    got = []
    for i in range(4):
        req = Actor(client, f"r{i}@example.com", f"요청자{i}")
        ex_id = _completed(provider, req, price=50)  # 각 10토큰
        got.append(req.post(f"/exchanges/{ex_id}/review", GOOD).json()["analysis"]["final_bonus"])
    assert got == [10, 10, 10, 0]  # 하루 30토큰


def test_pool_shortage_limits_bonus(client: TestClient, db: Session) -> None:
    system = ledger.get_system_user(db)
    pool = ledger.get_account(db, system.id, AccountKind.SYSTEM_BONUS_POOL)
    sink = ledger.get_account(db, system.id, AccountKind.SYSTEM_ISSUANCE)
    ledger.transfer(db, from_account_id=pool.id, to_account_id=sink.id, amount=pool.balance - 3, entry_type=EntryType.SYSTEM_FUNDING, idempotency_key="test:drain")
    db.commit()

    provider = Actor(client, "p@example.com", "제공자")
    learner = Actor(client, "l@example.com", "요청자")
    a = learner.post(f"/exchanges/{_completed(provider, learner)}/review", GOOD).json()["analysis"]
    assert a["final_bonus"] == 3
    assert _pool(db) == 0
    _assert_ledger_consistent(db)


def test_concurrent_reviews_respect_daily_cap(client: TestClient, db: Session) -> None:
    """같은 제공자에 대한 후기 4개가 동시에 와도 하루 상한 30을 넘지 않아요."""
    provider = Actor(client, "p@example.com", "인기제공자")
    pairs = []
    for i in range(4):
        req = Actor(client, f"r{i}@example.com", f"요청자{i}")
        pairs.append((req, _completed(provider, req, price=50)))

    def write(pair: tuple[Actor, int]) -> int:
        req, ex_id = pair
        r = req.post(f"/exchanges/{ex_id}/review", GOOD)
        return r.json()["analysis"]["final_bonus"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        got = list(pool.map(write, pairs))
    assert sum(got) == 30
    assert provider.wallet()[0] == 100 + 50 * 4 + 30
    _assert_ledger_consistent(db)


# ---- 권한·상태 ----

def test_review_rules(client: TestClient) -> None:
    provider = Actor(client, "p@example.com", "제공자")
    learner = Actor(client, "l@example.com", "요청자")
    ex = learner.request(provider.create_listing(50)).json()
    assert learner.post(f"/exchanges/{ex['id']}/review", GOOD).json()["error"]["code"] == "INVALID_STATE"

    ex_id = _completed(provider, learner)
    assert provider.post(f"/exchanges/{ex_id}/review", GOOD).status_code == 403
    assert learner.post(f"/exchanges/{ex_id}/review", GOOD).status_code == 201
    r = learner.post(f"/exchanges/{ex_id}/review", GOOD)
    assert r.json()["error"]["code"] == "ALREADY_REVIEWED"
    assert provider.get(f"/exchanges/{ex_id}/review").json()["analysis"]["final_bonus"] == 10


def test_ai_failure_keeps_review_and_retry_pays_once(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = Actor(client, "p@example.com", "제공자")
    learner = Actor(client, "l@example.com", "요청자")
    ex_id = _completed(provider, learner)

    _use_llm(monkeypatch, FakeLLM([AIError("x"), AIError("x")]))
    r = learner.post(f"/exchanges/{ex_id}/review", GOOD).json()
    assert r["analysis"] is None and r["analysis_failed"] is True
    assert provider.wallet() == (150, 0)

    _use_llm(monkeypatch, FakeLLM([_analysis(90)]))
    r = learner.post(f"/exchanges/{ex_id}/review/analyze").json()
    assert r["analysis"]["final_bonus"] == 10
    r = learner.post(f"/exchanges/{ex_id}/review/analyze").json()  # 다시 눌러도
    assert r["analysis"]["final_bonus"] == 10
    assert provider.wallet() == (160, 0)  # 한 번만 지급
    n = db.scalar(select(func.count()).select_from(LedgerTransfer).where(LedgerTransfer.entry_type == EntryType.REVIEW_BONUS))
    assert n == 1


def test_ratings_feed_profile_and_matching(client: TestClient) -> None:
    provider = Actor(client, "p@example.com", "제공자")
    for i, rating in enumerate([5, 4]):
        req = Actor(client, f"r{i}@example.com", f"요청자{i}")
        req.post(f"/exchanges/{_completed(provider, req, price=20)}/review", {**GOOD, "rating": rating})
    prof = client.get(f"/api/v1/users/{provider.id}").json()
    assert (prof["rating_avg"], prof["rating_count"], prof["completed_count"]) == (4.5, 2, 2)
    reviews = client.get(f"/api/v1/users/{provider.id}/reviews").json()
    assert len(reviews) == 2 and reviews[0]["reviewer_nickname"].startswith("요청자")


def test_unused_accounts_untouched(db: Session) -> None:
    # 보너스 풀은 시스템 계정에만 있어요
    rows = db.scalars(select(TokenAccount).where(TokenAccount.kind == AccountKind.SYSTEM_BONUS_POOL)).all()
    assert len(rows) == 1
