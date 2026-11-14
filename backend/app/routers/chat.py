from typing import Annotated

from fastapi import APIRouter, Query, status

from app.deps import DB, CurrentUser
from app.models import ExchangeMessage
from app.schemas.chat import ChatOut, MessageCreate, MessageOut, UnreadOut
from app.services import chat

router = APIRouter(tags=["chat"])


def _out(m: ExchangeMessage, user_id: int) -> MessageOut:
    return MessageOut(
        id=m.id,
        kind=m.kind.value,
        sender_id=m.sender_id,
        mine=m.sender_id == user_id,
        body=m.body,
        created_at=m.created_at,
    )


@router.get("/exchanges/unread", response_model=UnreadOut)
def unread(user: CurrentUser, db: DB) -> UnreadOut:
    """하단 탭 배지용: 내 모든 거래의 안 읽은 메시지 수."""
    return UnreadOut(total=chat.total_unread(db, user))


@router.get("/exchanges/{exchange_id}/messages", response_model=ChatOut)
def list_messages(
    exchange_id: int,
    user: CurrentUser,
    db: DB,
    after_id: Annotated[int, Query(ge=0)] = 0,
) -> ChatOut:
    """after_id 이후 메시지 (처음엔 0). 가져온 데까지 읽음 처리해요. 프론트는 몇 초마다 불러요."""
    ex, role, rows = chat.messages(db, user, exchange_id, after_id)
    db.commit()
    other = ex.provider_last_read_id if role == "requester" else ex.requester_last_read_id
    return ChatOut(state=chat.chat_state(ex), messages=[_out(m, user.id) for m in rows], other_last_read_id=other)


@router.post("/exchanges/{exchange_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(exchange_id: int, req: MessageCreate, user: CurrentUser, db: DB) -> MessageOut:
    m = chat.send(db, user, exchange_id, req.body)
    db.commit()
    db.refresh(m)
    return _out(m, user.id)
