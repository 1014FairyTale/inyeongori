from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.market import UserBrief
from app.schemas.talent import TalentOut


class MatchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300, description="이런 도움이 필요해요")
    limit: int = Field(default=5, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("어떤 도움이 필요한지 적어 주세요")
        return v


class MatchedListing(BaseModel):
    id: int
    title: str
    price_tokens: int


class MatchCandidate(BaseModel):
    user: UserBrief
    matched_talent: str | None
    listing: MatchedListing | None
    similarity: float
    rating_avg: float | None
    rating_count: int
    completed_count: int
    score: float
    reason: str
    reason_source: Literal["ai", "template"]


class MatchOut(BaseModel):
    query: str
    candidates: list[MatchCandidate]


class PublicProfile(BaseModel):
    user: UserBrief
    bio: str | None
    talents: list[TalentOut]
    completed_count: int
    rating_avg: float | None
    rating_count: int
