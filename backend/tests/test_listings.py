from fastapi.testclient import TestClient

from tests.conftest import Actor


def test_create_list_search_filter_and_detail(client: TestClient) -> None:
    a = Actor(client, "a@example.com", "엑셀장인")
    b = Actor(client, "b@example.com", "발표왕")
    a.post("/listings", {"title": "엑셀 정산표 만들어 드려요", "description": "동아리 회비 정산 템플릿", "category": "엑셀·문서", "price_tokens": 30})
    b.post("/listings", {"title": "PPT 구성 피드백", "description": "10장 이내 발표 자료 구성 봐 드려요", "category": "발표·PPT", "price_tokens": 40, "est_minutes": 30})

    page = client.get("/api/v1/listings").json()
    assert page["total"] == 2

    found = client.get("/api/v1/listings", params={"q": "회비"}).json()
    assert [i["title"] for i in found["items"]] == ["엑셀 정산표 만들어 드려요"]

    by_cat = client.get("/api/v1/listings", params={"category": "발표·PPT"}).json()
    assert by_cat["items"][0]["provider"]["nickname"] == "발표왕"

    detail = client.get(f"/api/v1/listings/{by_cat['items'][0]['id']}").json()
    assert detail["est_minutes"] == 30


def test_listing_validation_and_ownership(client: TestClient) -> None:
    a = Actor(client, "a@example.com", "주인")
    b = Actor(client, "b@example.com", "남")

    r = a.post("/listings", {"title": "x", "description": "짧", "category": "없는카테고리", "price_tokens": 0})
    assert r.status_code == 422
    fields = {f["field"] for f in r.json()["error"]["details"]["fields"]}
    assert {"title", "description", "category", "price_tokens"} <= fields

    listing_id = a.create_listing(50)
    r = b.patch(f"/listings/{listing_id}", {"price_tokens": 1})
    assert r.status_code == 403

    r = a.patch(f"/listings/{listing_id}", {"status": "paused"})
    assert r.json()["status"] == "paused"
    assert client.get("/api/v1/listings").json()["total"] == 0
    mine = client.get("/api/v1/listings", params={"provider_id": a.id, "include_paused": True}).json()
    assert mine["total"] == 1


def test_categories_endpoint(client: TestClient) -> None:
    cats = client.get("/api/v1/listings/categories").json()
    assert "발표·PPT" in cats and len(cats) == 10
