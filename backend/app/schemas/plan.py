from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.constants import LISTING_CATEGORIES, PLAN_MAX_ITEMS
from app.models import PlanKind, PriceBasis
from app.schemas.market import AgreementTerms

TermField = Literal["scope", "quantity", "revisions", "duration_minutes", "notes"]


# ---- 합의 도우미 ----

class AgreementDraftIn(BaseModel):
    listing_id: int
    raw_request: str = Field(min_length=2, max_length=500)
    answers: dict[TermField, str] = Field(default_factory=dict)
    # 이전 정리 결과. 다시 정리할 때 이미 정해진 조건이 사라지지 않게 함께 보내요.
    previous_terms: AgreementTerms | None = None


class MissingQuestion(BaseModel):
    field: TermField
    question: str
    options: list[str]


class AgreementDraftOut(BaseModel):
    summary: str
    terms: AgreementTerms
    missing: list[MissingQuestion]


# ---- 부탁 쪼개기 ----

class PlanCreate(BaseModel):
    goal: str = Field(min_length=2, max_length=300)
    kind: Literal["breakdown"] = "breakdown"  # 'path'는 6단계

    @field_validator("goal")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("목표를 적어 주세요")
        return v


class LinkedListing(BaseModel):
    id: int
    title: str
    price_tokens: int
    provider_nickname: str


class PlanItemOut(BaseModel):
    id: int
    position: int
    title: str
    description: str | None
    minutes: int
    category: str
    suggested_tokens: int
    price_basis: PriceBasis
    similar_count: int
    linked_listing: LinkedListing | None
    ai_generated: bool
    edited: bool


class PlanOut(BaseModel):
    id: int
    goal: str
    kind: PlanKind
    summary: str | None
    items: list[PlanItemOut]
    total_tokens: int
    created_at: datetime


class PlanSummary(BaseModel):
    id: int
    goal: str
    kind: PlanKind
    item_count: int
    total_tokens: int
    created_at: datetime


class PlanItemIn(BaseModel):
    id: int | None = None
    title: str = Field(min_length=2, max_length=60)
    description: str | None = Field(default=None, max_length=200)
    minutes: int = Field(ge=5, le=120)
    category: str
    suggested_tokens: int | None = Field(default=None, ge=1, le=500)

    @field_validator("category")
    @classmethod
    def _category(cls, v: str) -> str:
        if v not in LISTING_CATEGORIES:
            raise ValueError("지원하지 않는 카테고리예요")
        return v


class PlanItemsUpdate(BaseModel):
    items: list[PlanItemIn] = Field(min_length=1, max_length=PLAN_MAX_ITEMS)
