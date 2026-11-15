"""처음 이용자 가이드: 본 여부 기록 + 첫 걸음 체크리스트 자동 체크."""

from fastapi.testclient import TestClient

from tests.conftest import Actor
from tests.test_reviews import GOOD, _completed


def _steps(actor: Actor) -> dict[str, bool]:
    gs = actor.get("/auth/me").json()["getting_started"]
    return {s["key"]: s["done"] for s in gs["steps"]}


def test_new_user_has_not_seen_tutorial_until_marked(client: TestClient) -> None:
    me = Actor(client, "new@example.com", "새내기")
    gs = me.get("/auth/me").json()["getting_started"]
    assert gs["tutorial_seen"] is False
    assert [s["key"] for s in gs["steps"]] == ["discover", "list", "request", "chat", "review"]
    assert not any(s["done"] for s in gs["steps"])

    r = me.post("/auth/me/tutorial")
    assert r.status_code == 200
    assert r.json()["getting_started"]["tutorial_seen"] is True
    assert me.post("/auth/me/tutorial").json()["getting_started"]["tutorial_seen"] is True  # 여러 번 눌러도 괜찮아요


def test_checklist_follows_real_actions(client: TestClient) -> None:
    provider = Actor(client, "p@example.com", "제공자")
    me = Actor(client, "me@example.com", "새내기")

    me.post("/discovery/sessions", {"intro_text": "동아리 총무를 1년 했어요", "answers": {}})
    cand = me.get("/discovery/sessions/latest").json()["candidates"][0]
    me.post(f"/discovery/candidates/{cand['id']}/decision", {"action": "accept"})
    assert _steps(me)["discover"] is True and _steps(me)["list"] is False

    me.create_listing(20)
    assert _steps(me)["list"] is True

    ex_id = _completed(provider, me, price=30)
    s = _steps(me)
    assert s["request"] is True and s["chat"] is False  # 안내 메시지는 '대화'로 치지 않아요

    me.post(f"/exchanges/{ex_id}/messages", {"body": "감사했어요!"})
    assert _steps(me)["chat"] is True

    me.post(f"/exchanges/{ex_id}/review", GOOD)
    assert all(_steps(me).values())
