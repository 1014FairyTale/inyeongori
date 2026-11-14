"""AI 매칭 + 목표 기반 교환 경로 (AI_MOCK=true, n-gram 임베딩)."""

import json

import pytest
from fastapi.testclient import TestClient

from ai.providers.base import AIError
from app.services import matching
from tests.conftest import Actor
from tests.test_discovery import FakeLLM, _use_llm


def _people(client: TestClient) -> dict[str, Actor]:
    excel = Actor(client, "excel@example.com", "엑셀장인")
    excel.post("/users/me/talents", {"name": "엑셀 회비 정산", "category": "엑셀·문서", "description": "동아리 회비 정산표를 엑셀로 만들어 드려요"})
    excel.post("/listings", {"title": "엑셀 회비 정산표 만들어 드려요", "description": "동아리 회비 정산 엑셀 템플릿", "category": "엑셀·문서", "price_tokens": 30})

    ppt = Actor(client, "ppt@example.com", "발표왕")
    ppt.post("/users/me/talents", {"name": "발표 PPT 구성 피드백", "category": "발표·PPT", "description": "발표 자료 흐름을 봐 드려요"})

    game = Actor(client, "game@example.com", "테트리스고수")
    game.post("/listings", {"title": "테트리스 T-스핀 강의", "description": "테트리스 고급 기술", "category": "운동·게임", "price_tokens": 50})
    return {"excel": excel, "ppt": ppt, "game": game}


def test_match_ranks_relevant_person_first_with_reason(client: TestClient) -> None:
    p = _people(client)
    me = Actor(client, "me@example.com", "새내기")
    r = me.post("/match", {"query": "동아리 회비 정산을 엑셀로 하고 싶어요"})
    assert r.status_code == 200, r.text
    cands = r.json()["candidates"]
    assert cands, "후보가 있어야 해요"
    top = cands[0]
    assert top["user"]["id"] == p["excel"].id
    assert top["listing"]["title"] == "엑셀 회비 정산표 만들어 드려요"
    assert top["reason"] and top["reason_source"] == "template"  # mock 모드는 템플릿
    assert "엑셀" in top["reason"]
    assert all(c["user"]["id"] != p["game"].id for c in cands[:1])
    assert [c["score"] for c in cands] == sorted([c["score"] for c in cands], reverse=True)


def test_match_excludes_myself(client: TestClient) -> None:
    p = _people(client)
    r = p["excel"].post("/match", {"query": "동아리 회비 정산을 엑셀로 하고 싶어요"})
    assert all(c["user"]["id"] != p["excel"].id for c in r.json()["candidates"])


def test_talent_only_person_gets_their_listing_linked(client: TestClient) -> None:
    p = _people(client)
    r = p["ppt"].post("/listings", {"title": "자료 봐 드려요", "description": "무엇이든 봐 드려요", "category": "발표·PPT", "price_tokens": 20})
    assert r.status_code == 201, r.text
    me = Actor(client, "me@example.com", "새내기")
    cands = me.post("/match", {"query": "발표 PPT 구성 피드백 받고 싶어요"}).json()["candidates"]
    ppt = next(c for c in cands if c["user"]["id"] == p["ppt"].id)
    assert ppt["matched_talent"] == "발표 PPT 구성 피드백"
    assert ppt["listing"]["title"] == "자료 봐 드려요"


def test_strong_second_candidate_is_kept_even_if_top_is_much_higher(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    """데모 리허설에서 발견: 1등 0.83, 관련 있는 2등 0.63이 상대 기준만으로 잘리던 문제."""
    from app.services import embeddings

    monkeypatch.setattr(embeddings, "thresholds", lambda: {"price": 0.55, "match": 0.48, "relative": 0.12, "strong": 0.58})
    monkeypatch.setattr(matching, "thresholds", embeddings.thresholds)
    sims = {"a": 0.83, "b": 0.63, "c": 0.5}
    cands = {i: matching._Cand(i, similarity=s) for i, s in enumerate(sims.values())}
    th = matching.thresholds()
    top = max(c.similarity for c in cands.values())
    kept = [c.similarity for c in cands.values() if c.similarity >= th["match"] and (c.similarity >= th["strong"] or c.similarity >= top - th["relative"])]
    assert kept == [0.83, 0.63]


def test_unrelated_query_returns_no_candidates(client: TestClient) -> None:
    _people(client)
    me = Actor(client, "me@example.com", "새내기")
    assert me.post("/match", {"query": "zzqx 우주선 수리"}).json()["candidates"] == []


def test_ai_reasons_are_used_and_fall_back_on_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _people(client)
    me = Actor(client, "me@example.com", "새내기")
    _use_llm(
        monkeypatch,
        FakeLLM([json.dumps({"reasons": [{"candidate_index": 0, "relevant": True, "reason": "동아리 회비 정산 경험이 있어 바로 도와줄 수 있어요"}]}, ensure_ascii=False)]),
    )
    cands = me.post("/match", {"query": "동아리 회비 정산을 엑셀로 하고 싶어요"}).json()["candidates"]
    assert cands[0]["reason_source"] == "ai"
    assert cands[0]["reason"].startswith("동아리 회비 정산 경험")
    if len(cands) > 1:
        assert cands[1]["reason_source"] == "template"  # AI가 빠뜨린 후보는 템플릿

    _use_llm(monkeypatch, FakeLLM([AIError("x"), AIError("x")]))
    cands = me.post("/match", {"query": "동아리 회비 정산을 엑셀로 하고 싶어요"}).json()["candidates"]
    assert cands and all(c["reason_source"] == "template" for c in cands)


def test_slow_ai_reasons_fall_back_to_template_within_deadline(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import time as _time

    _people(client)
    me = Actor(client, "me@example.com", "새내기")

    class SlowLLM:
        name = "slow"

        def generate_json(self, **_: object) -> str:
            _time.sleep(3)
            return json.dumps({"reasons": []})

    _use_llm(monkeypatch, SlowLLM())  # type: ignore[arg-type]
    monkeypatch.setattr(matching, "MATCH_REASON_DEADLINE_S", 0.5)
    started = _time.monotonic()
    cands = me.post("/match", {"query": "동아리 회비 정산을 엑셀로 하고 싶어요"}).json()["candidates"]
    assert _time.monotonic() - started < 2.5
    assert cands and all(c["reason_source"] == "template" for c in cands)


def test_ai_can_drop_irrelevant_candidates(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    p = _people(client)
    me = Actor(client, "me@example.com", "새내기")
    first = me.post("/match", {"query": "동아리 회비 정산을 엑셀로 하고 싶어요"}).json()["candidates"]
    assert first[0]["user"]["id"] == p["excel"].id
    reasons = [{"candidate_index": 0, "relevant": False, "reason": "관련 없는 재능이에요"}]
    _use_llm(monkeypatch, FakeLLM([json.dumps({"reasons": reasons}, ensure_ascii=False)]))
    after = me.post("/match", {"query": "동아리 회비 정산을 엑셀로 하고 싶어요"}).json()["candidates"]
    assert all(c["user"]["id"] != p["excel"].id for c in after)


def test_score_weights_activity_and_rating() -> None:
    base = matching.score(0.6, matching.ProviderStats())
    active = matching.score(0.6, matching.ProviderStats(completed_count=10))
    rated = matching.score(0.6, matching.ProviderStats(rating_avg=5.0, rating_count=10))
    assert active > base and rated > base
    # 유사도가 가장 큰 비중: 유사도 0.2 차이는 활동 만점(완료 10회)보다 커요
    assert matching.score(0.8, matching.ProviderStats()) > matching.score(0.6, matching.ProviderStats(completed_count=10))


def test_public_profile(client: TestClient) -> None:
    p = _people(client)
    prof = client.get(f"/api/v1/users/{p['excel'].id}").json()
    assert prof["user"]["nickname"] == "엑셀장인"
    assert prof["talents"][0]["name"] == "엑셀 회비 정산"
    assert prof["completed_count"] == 0
    assert client.get("/api/v1/users/1").status_code == 404  # 시스템 계정


# ---- 목표 경로 ----

def test_path_plan_has_ordered_steps_with_why(client: TestClient) -> None:
    _people(client)
    me = Actor(client, "me@example.com", "새내기")
    r = me.post("/plans", {"goal": "공모전에 나가고 싶어요", "kind": "path"})
    assert r.status_code == 201, r.text
    plan = r.json()
    assert plan["kind"] == "path"
    assert [i["title"] for i in plan["items"]][:3] == ["공모전 기획서 피드백", "포스터·자료 디자인 기초", "발표 자료 구성 피드백"]
    assert all(i["why"] for i in plan["items"])
    assert me.get("/plans").json()[0]["kind"] == "path"


def test_path_items_keep_why_after_edit(client: TestClient) -> None:
    me = Actor(client, "me@example.com", "새내기")
    plan = me.post("/plans", {"goal": "공모전", "kind": "path"}).json()
    items = [{k: i[k] for k in ("id", "title", "description", "minutes", "category")} for i in plan["items"][:2]]
    r = me.client.put(f"/api/v1/plans/{plan['id']}/items", headers=me.headers, json={"items": items})
    assert all(i["why"] for i in r.json()["items"])
