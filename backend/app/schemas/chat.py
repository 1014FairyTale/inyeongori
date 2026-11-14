from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=1000)

    @field_validator("body")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("메시지를 입력해 주세요")
        return v


class MessageOut(BaseModel):
    id: int
    kind: Literal["user", "system"]
    sender_id: int | None
    mine: bool
    body: str
    created_at: datetime


class ChatOut(BaseModel):
    state: Literal["open", "readonly", "closed"]
    messages: list[MessageOut]
    other_last_read_id: int | None  # 상대가 어디까지 읽었는지 ('읽음' 표시용)


class UnreadOut(BaseModel):
    total: int
