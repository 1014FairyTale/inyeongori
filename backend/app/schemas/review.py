from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    good_text: str = Field(min_length=2, max_length=1000, description="좋았던 점")
    bad_text: str | None = Field(default=None, max_length=1000, description="아쉬운 점")

    @field_validator("good_text")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("좋았던 점을 적어 주세요")
        return v


class ReviewOutBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exchange_id: int
    reviewer_id: int
    reviewee_id: int
    rating: int
    good_text: str
    bad_text: str | None
    created_at: datetime


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contribution_score: int
    summary: str
    reasons: list[str]
    flags: list[str]
    eligible: bool
    base_bonus: int
    final_bonus: int
    adjustments: list[dict[str, Any]]
    created_at: datetime


class ReviewOut(BaseModel):
    review: ReviewOutBase
    analysis: AnalysisOut | None
    analysis_failed: bool = False


class PublicReview(BaseModel):
    id: int
    rating: int
    good_text: str
    bad_text: str | None
    reviewer_nickname: str
    listing_title: str | None
    contribution_score: int | None
    bonus: int
    created_at: datetime
