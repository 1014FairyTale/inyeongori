"""거래 흐름: 등록 → 요청 → 수락(보류) → 완료(지급) / 취소(환불)."""

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import EntryType, LedgerTransfer, TokenAccount, User
from app.services import exchange_flow as flow
from app.services import ledger
from tests.conftest import Actor, TestingSession


def _pair(client: TestClient) -> tuple[Actor, Actor]:
    provider = Actor(client, "teacher@example.com", "테트리스고수")
    learner = Actor(client, "learner@example.com", "새내기")
    return provider, learner


def _assert_ledger_consistent(db: Session) -> None:
    db.expire_all()
    accounts = db.scalars(select(TokenAccount)).all()
    for acc in accounts:
        assert acc.balance >= 0 or acc.kind == "system_issuance"
        assert acc.balance == ledger.recomputed_balance(db, acc.id)
    assert sum(a.balance for a in accounts) == 0


def _accepted_exchange(provider: Actor, learner: Actor, price: int = 50) -> int:
    ex = learner.request(provider.create_listing(price)).json()
    r = provider.post(f"/exchanges/{ex['id']}/agree")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "accepted"
    return ex["id"]


# ---- 정상 흐름 ----

def test_full_flow_request_accept_complete(client: TestClient, db: Session) -> None:
    provider, learner = _pair(client)
    listing_id = provider.create_listing(price=50)

    r = learner.request(listing_id)
    assert r.status_code == 201, r.text
    ex = r.json()
    assert ex["status"] == "requested"
    assert ex["agreement"]["requester_agreed"] is True
    assert ex["agreement"]["provider_agreed"] is False
    assert learner.wallet() == (100, 0)  # 요청만으로는 토큰이 움직이지 않아요

    r = provider.post(f"/exchanges/{ex['id']}/agree")
    assert r.json()["status"] == "accepted"
    assert learner.wallet() == (50, 50)  # 보류

    r = learner.post(f"/exchanges/{ex['id']}/complete")
    assert r.json()["status"] == "accepted"
    assert r.json()["requester_done"] is True
    assert provider.wallet() == (100, 0)  # 한쪽만 확인하면 아직 지급 전

    r = provider.post(f"/exchanges/{ex['id']}/complete")
    assert r.json()["status"] == "completed"
    assert learner.wallet() == (50, 0)
    assert provider.wallet() == (150, 0)

    history = learner.get("/wallet/ledger").json()["items"]
    assert [i["entry_type"] for i in history] == ["payout", "escrow_hold", "signup_bonus"]
    _assert_ledger_consistent(db)


def test_completed_exchange_cannot_be_completed_or_cancelled_again(client: TestClient) -> None:
    provider, learner = _pair(client)
    ex_id = _accepted_exchange(provider, learner)
    learner.post(f"/exchanges/{ex_id}/complete")
    provider.post(f"/exchanges/{ex_id}/complete")

    for actor, path in [(learner, "complete"), (provider, "complete"), (provider, "cancel"), (learner, "cancel")]:
        r = actor.post(f"/exchanges/{ex_id}/{path}")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "INVALID_STATE"
    assert provider.wallet() == (150, 0)


# ---- 합의서 ----

def test_changed_terms_need_both_agreements_again(client: TestClient) -> None:
    provider, learner = _pair(client)
    ex = learner.request(provider.create_listing(50)).json()

    r = provider.post(
        f"/exchanges/{ex['id']}/agreement",
        {"terms": {"request_text": "테트리스 기초", "scope": "기본 조작 + T-스핀", "revisions": 0, "duration_minutes": 40}},
    )
    body = r.json()
    assert body["status"] == "requested"
    assert body["agreement"]["version"] == 2
    assert body["agreement"]["provider_agreed"] is True
    assert body["agreement"]["requester_agreed"] is False
    assert "agree" not in body["actions"]  # 제안한 제공자는 이미 동의한 상태
    assert "agree" in learner.get(f"/exchanges/{ex['id']}").json()["actions"]
    assert learner.wallet() == (100, 0)

    r = learner.post(f"/exchanges/{ex['id']}/agree")
    assert r.json()["status"] == "accepted"
    assert r.json()["agreement"]["terms"]["scope"] == "기본 조작 + T-스핀"
    assert learner.wallet() == (50, 50)


# ---- 거절·취소·환불 (D6) ----

def test_reject_and_withdraw_before_accept_move_no_tokens(client: TestClient) -> None:
    provider, learner = _pair(client)
    listing_id = provider.create_listing(50)

    ex1 = learner.request(listing_id).json()
    assert provider.post(f"/exchanges/{ex1['id']}/reject").json()["status"] == "rejected"
    ex2 = learner.request(listing_id).json()
    assert learner.post(f"/exchanges/{ex2['id']}/reject").json()["status"] == "cancelled"
    assert learner.wallet() == (100, 0)


def test_provider_cancel_after_accept_refunds_in_full(client: TestClient, db: Session) -> None:
    provider, learner = _pair(client)
    ex_id = _accepted_exchange(provider, learner)
    r = provider.post(f"/exchanges/{ex_id}/cancel")
    assert r.json()["status"] == "cancelled"
    assert learner.wallet() == (100, 0)
    assert provider.wallet() == (100, 0)
    _assert_ledger_consistent(db)


def test_requester_cancel_needs_provider_approval(client: TestClient) -> None:
    provider, learner = _pair(client)
    ex_id = _accepted_exchange(provider, learner)

    r = learner.post(f"/exchanges/{ex_id}/cancel")
    assert r.json()["status"] == "cancel_requested"
    assert learner.wallet() == (50, 50)  # 아직 환불 안 됨

    r = provider.post(f"/exchanges/{ex_id}/cancel/decline")
    assert r.json()["status"] == "accepted"
    assert learner.wallet() == (50, 50)

    learner.post(f"/exchanges/{ex_id}/cancel")
    r = provider.post(f"/exchanges/{ex_id}/cancel")  # 승인
    assert r.json()["status"] == "cancelled"
    assert learner.wallet() == (100, 0)


# ---- 잔액·권한 ----

def test_request_over_balance_is_rejected(client: TestClient) -> None:
    provider, learner = _pair(client)
    r = learner.request(provider.create_listing(price=150))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INSUFFICIENT_BALANCE"


def test_accept_fails_if_requester_balance_dropped(client: TestClient) -> None:
    p1 = Actor(client, "p1@example.com", "제공자1")
    p2 = Actor(client, "p2@example.com", "제공자2")
    learner = Actor(client, "l@example.com", "새내기")
    ex1 = learner.request(p1.create_listing(60)).json()
    ex2 = learner.request(p2.create_listing(60)).json()  # 요청 시점에는 둘 다 100 이하라 통과

    assert p1.post(f"/exchanges/{ex1['id']}/agree").json()["status"] == "accepted"
    r = p2.post(f"/exchanges/{ex2['id']}/agree")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INSUFFICIENT_BALANCE"
    assert learner.get(f"/exchanges/{ex2['id']}").json()["agreement"]["provider_agreed"] is False  # 롤백
    assert learner.wallet() == (40, 60)


def test_cannot_request_own_listing_or_see_others_exchange(client: TestClient) -> None:
    provider, learner = _pair(client)
    stranger = Actor(client, "s@example.com", "지나가는사람")
    listing_id = provider.create_listing(50)

    r = provider.request(listing_id)
    assert r.json()["error"]["code"] == "SELF_REQUEST"

    ex = learner.request(listing_id).json()
    assert stranger.get(f"/exchanges/{ex['id']}").status_code == 404
    assert stranger.post(f"/exchanges/{ex['id']}/agree").status_code == 404


def test_paused_listing_cannot_be_requested(client: TestClient) -> None:
    provider, learner = _pair(client)
    listing_id = provider.create_listing(50)
    assert provider.patch(f"/listings/{listing_id}", {"status": "paused"}).status_code == 200
    r = learner.request(listing_id)
    assert r.json()["error"]["code"] == "LISTING_INACTIVE"


# ---- 동시성 ----

def _user(db: Session, user_id: int) -> User:
    u = db.get(User, user_id)
    assert u is not None
    return u


def test_concurrent_completion_pays_exactly_once(client: TestClient, db: Session) -> None:
    """양측이 '완료'를 동시에 여러 번 눌러도 지급은 정확히 한 번."""
    provider, learner = _pair(client)
    ex_id = _accepted_exchange(provider, learner)

    def press(user_id: int) -> str:
        with TestingSession() as s:
            try:
                flow.complete(s, _user(s, user_id), ex_id)
                s.commit()
                return "ok"
            except AppError as e:
                s.rollback()
                return e.code

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(press, [learner.id, provider.id] * 5))

    assert "ok" in results
    assert set(results) <= {"ok", "INVALID_STATE"}
    payouts = db.scalar(
        select(func.count()).select_from(LedgerTransfer).where(LedgerTransfer.entry_type == EntryType.PAYOUT)
    )
    assert payouts == 1
    assert provider.wallet() == (150, 0)
    assert learner.wallet() == (50, 0)
    _assert_ledger_consistent(db)


def test_concurrent_accepts_never_overdraw(client: TestClient, db: Session) -> None:
    """잔액 100인 요청자의 60토큰짜리 요청 3개를 제공자들이 동시에 수락 → 1개만 성공."""
    learner = Actor(client, "l@example.com", "새내기")
    providers = [Actor(client, f"p{i}@example.com", f"제공자{i}") for i in range(3)]
    pairs = [(p.id, learner.request(p.create_listing(60)).json()["id"]) for p in providers]

    def accept(pair: tuple[int, int]) -> str:
        provider_id, ex_id = pair
        with TestingSession() as s:
            try:
                flow.agree(s, _user(s, provider_id), ex_id)
                s.commit()
                return "ok"
            except AppError as e:
                s.rollback()
                return e.code

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(accept, pairs))

    assert sorted(results) == ["INSUFFICIENT_BALANCE", "INSUFFICIENT_BALANCE", "ok"]
    assert learner.wallet() == (40, 60)
    _assert_ledger_consistent(db)


def test_concurrent_provider_cancel_and_complete(client: TestClient, db: Session) -> None:
    """요청자가 완료한 상태에서 제공자의 '완료'와 '취소'가 동시에 와도 지급과 환불 중 하나만 일어나요."""
    provider, learner = _pair(client)
    ex_id = _accepted_exchange(provider, learner)
    learner.post(f"/exchanges/{ex_id}/complete")

    def act(kind: str) -> str:
        with TestingSession() as s:
            try:
                fn = flow.complete if kind == "complete" else flow.cancel
                fn(s, _user(s, provider.id), ex_id)
                s.commit()
                return "ok"
            except AppError as e:
                s.rollback()
                return e.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(act, ["complete", "cancel"]))

    assert sorted(results) == ["INVALID_STATE", "ok"]
    moved = db.scalars(
        select(LedgerTransfer.entry_type).where(LedgerTransfer.entry_type.in_([EntryType.PAYOUT, EntryType.REFUND]))
    ).all()
    assert len(moved) == 1
    _assert_ledger_consistent(db)
