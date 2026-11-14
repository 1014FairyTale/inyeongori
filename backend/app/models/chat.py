"""거래 채팅. 거래가 수락된 뒤 두 당사자가 진행 방식을 이야기해요.

- kind=user   : 사용자가 보낸 메시지 (sender_id 있음)
- kind=system : 거래 상태가 바뀔 때 자동으로 남기는 안내 (sender_id 없음)
읽음 위치는 exchanges.requester_last_read_id / provider_last_read_id 에 저장해요.
"""

import enum

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MessageKind(enum.StrEnum):
    USER = "user"
    SYSTEM = "system"


class ExchangeMessage(TimestampMixin, Base):
    __tablename__ = "exchange_messages"
    __table_args__ = (
        Index("ix_exchange_messages_exchange_id_id", "exchange_id", "id"),
        CheckConstraint("(kind = 'system') OR (sender_id IS NOT NULL)", name="user_has_sender"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"))
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[MessageKind] = mapped_column(
        Enum(MessageKind, name="message_kind", values_callable=lambda x: [m.value for m in x]),
        default=MessageKind.USER,
        server_default="user",
    )
    body: Mapped[str] = mapped_column(Text)
