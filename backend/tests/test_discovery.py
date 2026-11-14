"""숨은 재능 발굴 (AI_MOCK=true)."""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

import ai.structured
from ai.providers.base import AIError
from ai.providers.mock import load_mock
from app.models import UserTalent
from tests.conftest import Actor

PAYLOAD = {
    "intro_text": "저는 딱히 재능이 없는 평범한 학생이에요. 동아리 총무를 1년 했어요.",
    "answers": {
        "recent_roles": "동아리 총무, MT 준비도 제가 다 했어요",
        "friends_ask": "친구들이 PPT 좀 봐 달라고 해요",
        "confident_tools": "엑셀, 노션은 자신 있어요",
    },
}


class FakeLLM:
    """정해진 응답을 차례로 돌려주는 가짜 LLM."""

    name = "fake"

    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls = 0

    def generate_json(self, **_: Any) -> str:
        r = self.responses[self.calls]
        self.calls += 1
        if isinstance(r, Exception):
            raise r
        return r


def _use_llm(monkeypatch: pytest.MonkeyPatch, llm: FakeLLM) -> None:
    monkeypatch.setattr(ai.structured, "get_llm", lambda: llm)


def test_discovery_returns_candidates_with_evidence_and_questions(client: TestClient) -> None:
    me = Actor(client, "a@example.com", "새내기")
    r = me.post("/discovery/sessions", PAYLOAD)
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["candidates"]) == 4
    first = body["candidates"][0]
    assert first["name"] == "엑셀 회비 정산"
    assert first["evidence"] and first["confirm_question"].endswith("?")
    assert all(c["status"] == "pending" for c in body["candidates"])
    # 확정 전에는 재능으로 저장되지 않아요
    assert me.get("/users/me/talents").json() == []
    assert me.get("/discovery/sessions/latest").json()["id"] == body["id"]


def test_accept_edit_reject_and_embedding(client: TestClient, db: Session) -> None:
    me = Actor(client, "a@example.com", "새내기")
    cands = me.post("/discovery/sessions", PAYLOAD).json()["candidates"]

    r = me.post(f"/discovery/candidates/{cands[0]['id']}/decision", {"action": "accept"})
    assert r.json()["candidate"]["status"] == "accepted"
    assert r.json()["talent"]["source"] == "ai_confirmed"

    r = me.post(
        f"/discovery/candidates/{cands[2]['id']}/decision",
        {"action": "edit", "name": "발표 PPT 첨삭", "description": "10장 이내 PPT 구성을 봐 드려요"},
    )
    assert r.json()["candidate"]["status"] == "edited"
    assert r.json()["candidate"]["name"] == "발표 자료 구성 피드백"  # AI 원래 제안은 남아요
    assert r.json()["candidate"]["final_name"] == "발표 PPT 첨삭"
    assert r.json()["talent"]["name"] == "발표 PPT 첨삭"

    r = me.post(f"/discovery/candidates/{cands[1]['id']}/decision", {"action": "reject"})
    assert r.json()["talent"] is None

    talents = me.get("/users/me/talents").json()
    assert [t["name"] for t in talents] == ["엑셀 회비 정산", "발표 PPT 첨삭"]

    rows = db.scalars(select(UserTalent)).all()
    assert all(t.embedding is not None and len(t.embedding) == 1024 for t in rows)
    assert all(t.embedding_model == "mock-ngram" for t in rows)

    # 확정했다가 '아니에요'로 바꾸면 재능에서 빠져요
    me.post(f"/discovery/candidates/{cands[0]['id']}/decision", {"action": "reject"})
    assert [t["name"] for t in me.get("/users/me/talents").json()] == ["발표 PPT 첨삭"]


def test_others_cannot_decide_my_candidates(client: TestClient) -> None:
    me = Actor(client, "a@example.com", "나")
    other = Actor(client, "b@example.com", "남")
    cand_id = me.post("/discovery/sessions", PAYLOAD).json()["candidates"][0]["id"]
    assert other.post(f"/discovery/candidates/{cand_id}/decision", {"action": "accept"}).status_code == 404


def test_edit_requires_name(client: TestClient) -> None:
    me = Actor(client, "a@example.com", "나")
    cand_id = me.post("/discovery/sessions", PAYLOAD).json()["candidates"][0]["id"]
    r = me.post(f"/discovery/candidates/{cand_id}/decision", {"action": "edit"})
    assert r.status_code == 422


def test_manual_talent_add_and_delete(client: TestClient) -> None:
    me = Actor(client, "a@example.com", "나")
    r = me.post("/users/me/talents", {"name": "기타 코드 반주", "category": "음악·예술"})
    assert r.status_code == 201
    assert r.json()["source"] == "manual"
    assert me.client.delete(f"/api/v1/users/me/talents/{r.json()['id']}", headers=me.headers).status_code == 204
    assert me.get("/users/me/talents").json() == []


# ---- 구조화 출력: 검증·재시도·실패 ----

def test_invalid_json_is_retried_once(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    good = json.dumps(load_mock("talent_discovery"), ensure_ascii=False)
    llm = FakeLLM(["{not json", good])
    _use_llm(monkeypatch, llm)
    me = Actor(client, "a@example.com", "나")
    r = me.post("/discovery/sessions", PAYLOAD)
    assert r.status_code == 201
    assert llm.calls == 2


def test_two_failures_return_ai_failed(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    llm = FakeLLM(['{"candidates": []}', AIError("AI 서버에 연결하지 못했어요")])
    _use_llm(monkeypatch, llm)
    me = Actor(client, "a@example.com", "나")
    r = me.post("/discovery/sessions", PAYLOAD)
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "AI_FAILED"
    assert llm.calls == 2
    assert me.get("/discovery/sessions/latest").json() is None  # 아무것도 저장되지 않음


def test_unknown_category_falls_back(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    data = load_mock("talent_discovery")
    data["candidates"][0]["category"] = "없는카테고리"
    _use_llm(monkeypatch, FakeLLM([json.dumps(data, ensure_ascii=False)]))
    me = Actor(client, "a@example.com", "나")
    cands = me.post("/discovery/sessions", PAYLOAD).json()["candidates"]
    assert cands[0]["category"] == "생활·기타"
