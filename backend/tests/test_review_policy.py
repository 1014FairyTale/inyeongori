"""후기 작성자 10% 환급 + 7일 기한 + 이용 제한 (기획자 결정, 2026-11-15)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Exchange
from tests.conftest import TestingSession, Actor
from tests.test_discovery import FakeLLM, _use_llm
from tests.test_exchange_flow import _assert_ledger_consistent
from tests.test_reviews import GOOD, _analysis, _completed


def _age(exchange_id: int, days: float) -> None:
    """거래 완료 시각을 days일 전으로 옮겨요 (기한 테스트용)."""
    with TestingSession() as s:
        s.execute(
            update(Exchange)
            .where(Exchange.id == exchange_id)
            .values(completed_at=datetime.now(UTC) - timedelta(days=days))
        )
        s.commit()


# ---- 10% 환급 ----

def test_sincere_review_on_time_returns_10_percent(client: TestClient, db: Session) -> None:
    provider = Actor(client, "p@example.com", "제공자")
    requester = Actor(client, "r@example.com", "요청자")
    ex_id = _completed(provider, requester, price=50)
    assert requester.wallet() == (50, 0)

    a = requester.post(f"/exchanges/{ex_id}/review", GOOD).json()["analysis"]
    assert a["review_quality"] == 82  # mock
    assert a["reviewer_reward"] == 5  # 50의 10%
    assert requester.wallet() == (55, 0)
    assert provider.wallet() == (160, 0)  # 제공자 보너스는 따로 (50 + 10)
    history = requester.get("/wallet/ledger").json()["items"]
    assert history[0]["entry_type"] == "review_reward" and history[0]["available_delta"] == 5
    _assert_ledger_consistent(db)


@pytest.mark.parametrize(
    ("quality", "review", "reason"),
    [
        (50, GOOD, "성의 점수"),
        (90, {"rating": 5, "good_text": "좋았어요 감사합니다", "bad_text": ""}, "30자"),
    ],
)
def test_no_reward_for_insincere_review(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, quality: int, review: dict, reason: str
) -> None:
    provider = Actor(client, "p@example.com", "제공자")
    requester = Actor(client, "r@example.com", "요청자")
    ex_id = _completed(provider, requester, price=50)
    _use_llm(monkeypatch, FakeLLM([_analysis(88, quality=quality)]))
    a = requester.post(f"/exchanges/{ex_id}/review", review).json()["analysis"]
    assert a["reviewer_reward"] == 0
    assert reason in a["reviewer_reward_note"]
    assert requester.wallet() == (50, 0)


def test_unhappy_but_sincere_review_still_gets_reward(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """불만 후기도 구체적이면 환급 (제공자 보너스는 없음)."""
    provider = Actor(client, "p@example.com", "제공자")
    requester = Actor(client, "r@example.com", "요청자")
    ex_id = _completed(provider, requester, price=40)
    _use_llm(monkeypatch, FakeLLM([_analysis(30, quality=85)]))
    bad = {"rating": 2, "good_text": "친절하게 대해 주셨어요", "bad_text": "약속한 수정본 검토를 안 해 주셨고 10분 만에 끝났어요"}
    a = requester.post(f"/exchanges/{ex_id}/review", bad).json()["analysis"]
    assert a["final_bonus"] == 0
    assert a["reviewer_reward"] == 4


def test_minimum_reward_is_one_token(client: TestClient) -> None:
    provider = Actor(client, "p@example.com", "제공자")
    requester = Actor(client, "r@example.com", "요청자")
    ex_id = _completed(provider, requester, price=4)  # 10% = 0.4
    a = requester.post(f"/exchanges/{ex_id}/review", GOOD).json()["analysis"]
    assert a["reviewer_reward"] == 1


# ---- 기한과 이용 제한 ----

def test_within_deadline_nothing_is_blocked(client: TestClient) -> None:
    p1 = Actor(client, "p1@example.com", "제공자1")
    p2 = Actor(client, "p2@example.com", "제공자2")
    requester = Actor(client, "r@example.com", "요청자")
    ex_id = _completed(p1, requester, price=20)
    _age(ex_id, 6)  # 6일 지남, 아직 기한 안

    me = requester.get("/auth/me").json()["review_status"]
    assert me["blocked"] is False
    assert me["due"][0]["exchange_id"] == ex_id and me["due"][0]["overdue"] is False
    # 후기를 안 써도 다른 재능을 동시에 요청할 수 있어요
    assert requester.request(p2.create_listing(20)).status_code == 201


def test_overdue_review_blocks_service_until_written(client: TestClient, db: Session) -> None:
    provider = Actor(client, "p@example.com", "제공자")
    other = Actor(client, "o@example.com", "다른제공자")
    requester = Actor(client, "r@example.com", "요청자")
    other_listing = other.create_listing(20)
    ex_id = _completed(provider, requester, price=50)
    _age(ex_id, 8)

    # 막힘: 마켓 등록·요청·지갑·매칭 모두 403
    for method, path, body in [
        ("POST", "/listings", {"title": "새 상품", "description": "설명이에요", "category": "운동·게임", "price_tokens": 10}),
        ("POST", "/exchanges", {"listing_id": other_listing, "terms": {"request_text": "부탁해요"}}),
        ("GET", "/wallet", None),
        ("POST", "/match", {"query": "도움이 필요해요"}),
    ]:
        r = requester.post(path, body) if method == "POST" else requester.get(path)
        assert r.status_code == 403, path
        assert r.json()["error"]["code"] == "SERVICE_BLOCKED"
        assert r.json()["error"]["details"]["overdue_exchange_ids"] == [ex_id]

    # 열려 있는 곳: 내 정보, 밀린 거래 보기
    me = requester.get("/auth/me").json()["review_status"]
    assert me["blocked"] is True and me["due"][0]["overdue"] is True
    assert requester.get(f"/exchanges/{ex_id}").status_code == 200

    # 늦게라도 후기를 쓰면 바로 풀리지만, 10%는 없어요
    a = requester.post(f"/exchanges/{ex_id}/review", GOOD).json()["analysis"]
    assert a["reviewer_reward"] == 0
    assert "지나서" in a["reviewer_reward_note"]
    assert a["final_bonus"] == 10  # 제공자 보너스는 그대로 판단
    assert requester.get("/wallet").status_code == 200
    assert requester.get("/auth/me").json()["review_status"] == {"blocked": False, "due": []}
    _assert_ledger_consistent(db)


def test_blocked_provider_listings_are_hidden_and_cannot_be_requested(client: TestClient) -> None:
    lazy = Actor(client, "lazy@example.com", "후기안씀")
    someone = Actor(client, "s@example.com", "누군가")
    customer = Actor(client, "c@example.com", "손님")
    lazy_listing = lazy.create_listing(30, title="엑셀 회비 정산표")  # 막히기 전에 등록

    ex_id = _completed(someone, lazy, price=20)  # lazy가 요청자로 받은 거래
    _age(ex_id, 8)

    titles = [i["title"] for i in client.get("/api/v1/listings").json()["items"]]
    assert "엑셀 회비 정산표" not in titles
    r = customer.request(lazy_listing)
    assert r.json()["error"]["code"] == "LISTING_INACTIVE"


def test_provider_is_not_blocked_by_reviews_they_receive(client: TestClient) -> None:
    """후기를 '써야 하는' 사람은 요청자예요. 제공자는 후기를 못 받았다고 막히지 않아요."""
    provider = Actor(client, "p@example.com", "제공자")
    requester = Actor(client, "r@example.com", "요청자")
    ex_id = _completed(provider, requester, price=20)
    _age(ex_id, 30)
    assert provider.get("/wallet").status_code == 200
    assert requester.get("/wallet").status_code == 403
