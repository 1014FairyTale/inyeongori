"""거래 채팅: 수락 후부터 두 당사자만, 폴링(after_id), 안 읽은 수, 상태 안내 메시지."""

from fastapi.testclient import TestClient

from tests.conftest import Actor


def _pair(client: TestClient) -> tuple[Actor, Actor]:
    return Actor(client, "p@example.com", "제공자"), Actor(client, "r@example.com", "요청자")


def _requested(provider: Actor, requester: Actor) -> int:
    return requester.request(provider.create_listing(30)).json()["id"]


def test_chat_closed_before_accept_and_opens_after(client: TestClient) -> None:
    provider, requester = _pair(client)
    ex_id = _requested(provider, requester)

    assert requester.get(f"/exchanges/{ex_id}").json()["chat_state"] == "closed"
    r = requester.post(f"/exchanges/{ex_id}/messages", {"body": "안녕하세요"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "CHAT_NOT_OPEN"
    assert requester.get(f"/exchanges/{ex_id}/messages").status_code == 409

    provider.post(f"/exchanges/{ex_id}/agree")
    assert requester.get(f"/exchanges/{ex_id}").json()["chat_state"] == "open"
    msgs = requester.get(f"/exchanges/{ex_id}/messages").json()["messages"]
    assert len(msgs) == 1 and msgs[0]["kind"] == "system" and "거래가 시작됐어요" in msgs[0]["body"]


def test_send_poll_and_read_receipts(client: TestClient) -> None:
    provider, requester = _pair(client)
    ex_id = _requested(provider, requester)
    provider.post(f"/exchanges/{ex_id}/agree")

    # 제공자는 아직 안내 메시지를 안 읽었어요
    assert provider.get(f"/exchanges/{ex_id}").json()["unread_count"] == 1
    first = provider.get(f"/exchanges/{ex_id}/messages").json()["messages"]
    last_id = first[-1]["id"]
    assert provider.get(f"/exchanges/{ex_id}").json()["unread_count"] == 0

    r = requester.post(f"/exchanges/{ex_id}/messages", {"body": "  토요일 오후 2시에 줌으로 괜찮을까요?  "})
    assert r.status_code == 201
    m = r.json()
    assert m["mine"] is True and m["body"] == "토요일 오후 2시에 줌으로 괜찮을까요?"

    # 제공자: 안 읽은 1개, 새 메시지만 가져오기
    assert provider.get("/exchanges/unread").json()["total"] == 1
    assert provider.get("/exchanges?role=received").json()[0]["unread_count"] == 1
    new = provider.get(f"/exchanges/{ex_id}/messages?after_id={last_id}").json()
    assert [x["body"] for x in new["messages"]] == ["토요일 오후 2시에 줌으로 괜찮을까요?"]
    assert new["messages"][0]["mine"] is False
    assert provider.get("/exchanges/unread").json()["total"] == 0

    # 요청자 화면: 제공자가 내 메시지까지 읽었어요
    me = requester.get(f"/exchanges/{ex_id}/messages?after_id={m['id']}").json()
    assert me["messages"] == []
    assert me["other_last_read_id"] >= m["id"]

    provider.post(f"/exchanges/{ex_id}/messages", {"body": "좋아요! 링크 보내 드릴게요"})
    assert requester.get("/exchanges/unread").json()["total"] == 1


def test_only_participants_can_chat(client: TestClient) -> None:
    provider, requester = _pair(client)
    stranger = Actor(client, "s@example.com", "남")
    ex_id = _requested(provider, requester)
    provider.post(f"/exchanges/{ex_id}/agree")
    assert stranger.get(f"/exchanges/{ex_id}/messages").status_code == 404
    assert stranger.post(f"/exchanges/{ex_id}/messages", {"body": "끼어들기"}).status_code == 404


def test_message_validation(client: TestClient) -> None:
    provider, requester = _pair(client)
    ex_id = _requested(provider, requester)
    provider.post(f"/exchanges/{ex_id}/agree")
    assert requester.post(f"/exchanges/{ex_id}/messages", {"body": "   "}).status_code == 422
    assert requester.post(f"/exchanges/{ex_id}/messages", {"body": "가" * 1001}).status_code == 422


def test_status_changes_leave_notices_and_cancelled_is_readonly(client: TestClient) -> None:
    provider, requester = _pair(client)
    ex_id = _requested(provider, requester)
    provider.post(f"/exchanges/{ex_id}/agree")
    requester.post(f"/exchanges/{ex_id}/messages", {"body": "죄송해요 일정이 생겼어요"})
    requester.post(f"/exchanges/{ex_id}/cancel")  # 취소 요청
    provider.post(f"/exchanges/{ex_id}/cancel")  # 승인

    chat = requester.get(f"/exchanges/{ex_id}/messages").json()
    assert chat["state"] == "readonly"
    bodies = [m["body"] for m in chat["messages"]]
    assert any("취소를 요청" in b for b in bodies)
    assert any("승인" in b and "환불" in b for b in bodies)
    r = requester.post(f"/exchanges/{ex_id}/messages", {"body": "또 연락드릴게요"})
    assert r.json()["error"]["code"] == "CHAT_NOT_OPEN"


def test_completion_notices_and_chat_stays_open(client: TestClient) -> None:
    provider, requester = _pair(client)
    ex_id = _requested(provider, requester)
    provider.post(f"/exchanges/{ex_id}/agree")
    requester.post(f"/exchanges/{ex_id}/complete")
    requester.post(f"/exchanges/{ex_id}/complete")  # 두 번 눌러도 안내는 한 번
    provider.post(f"/exchanges/{ex_id}/complete")

    bodies = [m["body"] for m in requester.get(f"/exchanges/{ex_id}/messages").json()["messages"]]
    assert sum("요청자가 완료를 확인" in b for b in bodies) == 1
    assert any("토큰이 지급됐어요" in b for b in bodies)
    assert requester.post(f"/exchanges/{ex_id}/messages", {"body": "감사했어요!"}).status_code == 201


def test_rejected_request_has_no_chat(client: TestClient) -> None:
    provider, requester = _pair(client)
    ex_id = _requested(provider, requester)
    provider.post(f"/exchanges/{ex_id}/reject")
    assert requester.get(f"/exchanges/{ex_id}").json()["chat_state"] == "closed"
    assert requester.get("/exchanges/unread").json()["total"] == 0
