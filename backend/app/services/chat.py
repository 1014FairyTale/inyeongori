"""거래 채팅 (수락 후부터).

- 열림(보내기 가능): 진행 중(accepted), 취소 요청됨(cancel_requested), 완료(completed — 후속 문의용)
- 읽기 전용: 수락된 뒤 취소된 거래(cancelled) — 기록은 볼 수 있어요
- 없음: 합의 중(requested), 거절(rejected), 수락 전에 철회된 거래
새 메시지는 프론트가 몇 초마다 after_id 이후만 가져가요 (폴링).
"""

from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Exchange, ExchangeMessage, ExchangeStatus, MessageKind, User
from app.services import exchange_flow

ChatState = Literal["open", "readonly", "closed"]
OPEN = {ExchangeStatus.ACCEPTED, ExchangeStatus.CANCEL_REQUESTED, ExchangeStatus.COMPLETED}
PAGE = 200


def chat_state(ex: Exchange) -> ChatState:
    if ex.status in OPEN:
        return "open"
    if ex.status == ExchangeStatus.CANCELLED and ex.accepted_at is not None:
        return "readonly"
    return "closed"


def _get(db: Session, user: User, exchange_id: int) -> tuple[Exchange, str]:
    ex = db.get(Exchange, exchange_id)
    if ex is None:
        raise AppError("NOT_FOUND", "거래를 찾을 수 없어요", 404)
    role = exchange_flow.role_of(ex, user)  # 당사자가 아니면 404
    return ex, role


def _set_read(ex: Exchange, role: str, message_id: int) -> None:
    if role == "requester":
        ex.requester_last_read_id = max(ex.requester_last_read_id or 0, message_id)
    else:
        ex.provider_last_read_id = max(ex.provider_last_read_id or 0, message_id)


def send(db: Session, user: User, exchange_id: int, body: str) -> ExchangeMessage:
    ex, role = _get(db, user, exchange_id)
    state = chat_state(ex)
    if state != "open":
        msg = "거래가 수락된 뒤에 대화할 수 있어요" if state == "closed" else "취소된 거래라 메시지를 보낼 수 없어요"
        raise AppError("CHAT_NOT_OPEN", msg, 409)
    m = ExchangeMessage(exchange_id=ex.id, sender_id=user.id, kind=MessageKind.USER, body=body)
    db.add(m)
    db.flush()
    _set_read(ex, role, m.id)  # 내가 보낸 메시지까지는 읽은 것으로
    return m


def messages(db: Session, user: User, exchange_id: int, after_id: int = 0) -> tuple[Exchange, str, list[ExchangeMessage]]:
    """after_id 이후 메시지를 가져오고, 가져온 데까지 읽음으로 표시해요."""
    ex, role = _get(db, user, exchange_id)
    if chat_state(ex) == "closed":
        raise AppError("CHAT_NOT_OPEN", "거래가 수락된 뒤에 대화할 수 있어요", 409)
    rows = list(
        db.scalars(
            select(ExchangeMessage)
            .where(ExchangeMessage.exchange_id == ex.id, ExchangeMessage.id > after_id)
            .order_by(ExchangeMessage.id)
            .limit(PAGE)
        )
    )
    if rows:
        _set_read(ex, role, rows[-1].id)
    return ex, role, rows


def _unread_filter(user_id: int):  # noqa: ANN202
    return or_(ExchangeMessage.sender_id.is_(None), ExchangeMessage.sender_id != user_id)


def unread_counts(db: Session, user: User, exchanges: list[Exchange]) -> dict[int, int]:
    """거래별 안 읽은 메시지 수 (상대가 보낸 메시지 + 안내 메시지)."""
    out: dict[int, int] = {}
    for ex in exchanges:
        if chat_state(ex) == "closed":
            out[ex.id] = 0
            continue
        last = (ex.requester_last_read_id if user.id == ex.requester_id else ex.provider_last_read_id) or 0
        out[ex.id] = int(
            db.scalar(
                select(func.count())
                .select_from(ExchangeMessage)
                .where(ExchangeMessage.exchange_id == ex.id, ExchangeMessage.id > last, _unread_filter(user.id))
            )
            or 0
        )
    return out


def total_unread(db: Session, user: User) -> int:
    exchanges = list(
        db.scalars(
            select(Exchange).where(
                or_(Exchange.requester_id == user.id, Exchange.provider_id == user.id),
                Exchange.accepted_at.is_not(None),
            )
        )
    )
    return sum(unread_counts(db, user, exchanges).values())
