"""합의 도우미 + 부탁 쪼개기 (AI_MOCK=true)."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.providers.mock import load_mock
from app.models import Listing
from app.services import pricing
from tests.conftest import Actor
from tests.test_discovery import FakeLLM, _use_llm


def _ppt_listing(owner: Actor) -> int:
    r = owner.post(
        "/listings",
        {"title": "PPT 구성 피드백", "description": "발표 자료 흐름과 구성을 봐 드려요", "category": "발표·PPT", "price_tokens": 30, "est_minutes": 30},
    )
    return r.json()["id"]


# ---- 합의 도우미 ----

def test_agreement_draft_returns_terms_and_missing_questions(client: TestClient) -> None:
    owner = Actor(client, "o@example.com", "발표왕")
    me = Actor(client, "m@example.com", "새내기")
    r = me.post("/ai/agreements/draft", {"listing_id": _ppt_listing(owner), "raw_request": "PPT 봐주세요"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["terms"]["scope"].startswith("구성")
    assert body["terms"]["duration_minutes"] == 30
    assert {q["field"] for q in body["missing"]} == {"quantity", "revisions"}
    assert all(len(q["options"]) >= 2 for q in body["missing"])


def test_answers_fill_terms_and_close_questions(client: TestClient) -> None:
    owner = Actor(client, "o@example.com", "발표왕")
    me = Actor(client, "m@example.com", "새내기")
    r = me.post(
        "/ai/agreements/draft",
        {
            "listing_id": _ppt_listing(owner),
            "raw_request": "PPT 봐주세요",
            "answers": {"quantity": "10장 이내", "revisions": "수정본 1회 재검토"},
        },
    )
    body = r.json()
    assert body["terms"]["quantity"] == "10장 이내"
    assert body["terms"]["revisions"] == 1
    assert body["missing"] == []
    assert body["summary"] == "10장 이내, 구성·흐름 피드백 (디자인 수정은 제외), 수정 1회, 30분"


def test_previous_terms_are_kept_when_ai_drops_them(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """두 번째 정리에서 AI가 앞서 정한 분량을 빠뜨려도 유지되고, 다시 묻지 않아요."""
    data = load_mock("agreement")
    data["terms"]["scope"] = None
    data["missing"].append({"field": "scope", "question": "어떤 부분을 봐 드릴까요?", "options": ["구성", "디자인"]})
    _use_llm(monkeypatch, FakeLLM([json.dumps(data, ensure_ascii=False)]))
    owner = Actor(client, "o@example.com", "발표왕")
    me = Actor(client, "m@example.com", "새내기")
    r = me.post(
        "/ai/agreements/draft",
        {
            "listing_id": _ppt_listing(owner),
            "raw_request": "PPT 봐주세요",
            "answers": {"revisions": "1회"},
            "previous_terms": {"request_text": "PPT 봐주세요", "scope": "구성 피드백", "quantity": "10장 이내"},
        },
    )
    body = r.json()
    assert body["terms"]["scope"] == "구성 피드백"
    assert body["terms"]["quantity"] == "10장 이내"
    assert body["terms"]["revisions"] == 1
    assert body["missing"] == []


def test_draft_can_be_used_to_create_exchange(client: TestClient) -> None:
    owner = Actor(client, "o@example.com", "발표왕")
    me = Actor(client, "m@example.com", "새내기")
    listing_id = _ppt_listing(owner)
    terms = me.post(
        "/ai/agreements/draft",
        {"listing_id": listing_id, "raw_request": "PPT 봐주세요", "answers": {"quantity": "10장", "revisions": "한 번 보고 끝"}},
    ).json()["terms"]
    assert terms["revisions"] == 0
    ex = me.post("/exchanges", {"listing_id": listing_id, "terms": terms, "ai_generated": True}).json()
    assert ex["agreement"]["ai_generated"] is True
    assert ex["agreement"]["terms"]["quantity"] == "10장"


def test_agreement_draft_unknown_listing(client: TestClient) -> None:
    me = Actor(client, "m@example.com", "새내기")
    assert me.post("/ai/agreements/draft", {"listing_id": 999, "raw_request": "PPT 봐주세요"}).status_code == 404


# ---- 부탁 쪼개기 ----

def test_breakdown_without_market_uses_ai_estimates(client: TestClient) -> None:
    me = Actor(client, "m@example.com", "새내기")
    r = me.post("/plans", {"goal": "앱 개발을 배우고 싶어요"})
    assert r.status_code == 201, r.text
    plan = r.json()
    assert [i["title"] for i in plan["items"]][:2] == ["개발 환경 설치", "화면 하나 만들기"]
    assert all(i["price_basis"] == "ai" for i in plan["items"])
    assert plan["items"][0]["suggested_tokens"] == 20
    assert plan["total_tokens"] == sum(i["suggested_tokens"] for i in plan["items"])
    assert me.get("/plans").json()[0]["item_count"] == 5


def test_breakdown_uses_market_median_when_enough_similar_listings(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    teachers = [Actor(client, f"t{i}@example.com", f"개발자{i}") for i in range(3)]
    for t, price in zip(teachers, [10, 40, 50], strict=True):
        t.post("/listings", {"title": "개발 환경 설치 도와 드려요", "description": "Node.js와 에디터 설치, 첫 프로젝트 실행", "category": "개발·IT", "price_tokens": price})
    assert all(listing.embedding is not None for listing in db.scalars(select(Listing)))

    # 첫 활동만 위 상품들과 비슷하게, 나머지는 전혀 다른 내용으로
    data = load_mock("breakdown")
    data["items"][0] = {"title": "개발 환경 설치", "description": "Node.js와 에디터 설치, 첫 프로젝트 실행", "minutes": 20, "category": "개발·IT", "estimated_tokens": 99}
    data["items"] = data["items"][:2]
    data["items"][1] = {"title": "수채화 물감 고르기", "description": "그림 재료 추천", "minutes": 20, "category": "음악·예술", "estimated_tokens": 15}
    _use_llm(monkeypatch, FakeLLM([json.dumps(data, ensure_ascii=False)]))

    me = Actor(client, "m@example.com", "새내기")
    items = me.post("/plans", {"goal": "앱 개발을 배우고 싶어요"}).json()["items"]
    assert items[0]["price_basis"] == "market"
    assert items[0]["similar_count"] == 3
    assert items[0]["suggested_tokens"] == 40  # 10, 40, 50의 중앙값
    assert items[0]["linked_listing"]["title"] == "개발 환경 설치 도와 드려요"
    assert items[1]["price_basis"] == "ai"
    assert items[1]["suggested_tokens"] == 15


def test_own_listings_are_not_used_for_price(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    me = Actor(client, "m@example.com", "새내기")
    for price in (10, 20, 30):
        me.post("/listings", {"title": "개발 환경 설치 도와 드려요", "description": "Node.js와 에디터 설치, 첫 프로젝트 실행", "category": "개발·IT", "price_tokens": price})
    items = me.post("/plans", {"goal": "앱 개발"}).json()["items"]
    assert items[0]["price_basis"] == "ai"


def test_edit_delete_add_items(client: TestClient) -> None:
    me = Actor(client, "m@example.com", "새내기")
    plan = me.post("/plans", {"goal": "앱 개발을 배우고 싶어요"}).json()
    first, second = plan["items"][0], plan["items"][1]

    r = me.client.put(
        f"/api/v1/plans/{plan['id']}/items",
        headers=me.headers,
        json={
            "items": [
                {**{k: second[k] for k in ("id", "title", "description", "minutes", "category")}},
                {**{k: first[k] for k in ("id", "description", "minutes", "category")}, "title": "개발 환경 설치 (윈도우)", "suggested_tokens": 25},
                {"title": "깃허브 사용법", "minutes": 30, "category": "개발·IT"},
            ]
        },
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert [i["title"] for i in items] == ["화면 하나 만들기", "개발 환경 설치 (윈도우)", "깃허브 사용법"]
    assert items[0]["edited"] is False
    assert items[1]["edited"] is True and items[1]["price_basis"] == "user" and items[1]["suggested_tokens"] == 25
    assert items[2]["ai_generated"] is False and items[2]["suggested_tokens"] > 0
    assert r.json()["total_tokens"] == sum(i["suggested_tokens"] for i in items)


def test_others_cannot_see_or_edit_my_plan(client: TestClient) -> None:
    me = Actor(client, "m@example.com", "나")
    other = Actor(client, "o@example.com", "남")
    plan_id = me.post("/plans", {"goal": "앱 개발"}).json()["id"]
    assert other.get(f"/plans/{plan_id}").status_code == 404
    r = other.client.put(f"/api/v1/plans/{plan_id}/items", headers=other.headers, json={"items": [{"title": "x2", "minutes": 20, "category": "개발·IT"}]})
    assert r.status_code == 404


def test_market_stats(client: TestClient, db: Session) -> None:
    a = Actor(client, "a@example.com", "a")
    for price, cat in [(10, "개발·IT"), (30, "개발·IT"), (50, "디자인")]:
        a.post("/listings", {"title": "테스트 상품", "description": "설명입니다", "category": cat, "price_tokens": price})
    stats = pricing.market_stats(db)
    assert stats["count"] == 3
    assert stats["overall_median"] == 30
    assert stats["category_median"] == {"개발·IT": 20, "디자인": 50}
