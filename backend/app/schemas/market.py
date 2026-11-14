from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import LISTING_CATEGORIES, LISTING_MAX_PRICE, LISTING_MIN_PRICE
from app.models import ExchangeStatus, ListingStatus


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    school: str | None = None
    major: str | None = None


# ---- 재능 상품 ----

class ListingBase(BaseModel):
    title: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=5, max_length=2000)
    category: str
    price_tokens: int = Field(ge=LISTING_MIN_PRICE, le=LISTING_MAX_PRICE)
    est_minutes: int | None = Field(default=None, ge=5, le=600)

    @field_validator("category")
    @classmethod
    def _category(cls, v: str) -> str:
        if v not in LISTING_CATEGORIES:
            raise ValueError("지원하지 않는 카테고리예요")
        return v

    @field_validator("title", "description")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ListingCreate(ListingBase):
    pass


class ListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, min_length=5, max_length=2000)
    category: str | None = None
    price_tokens: int | None = Field(default=None, ge=LISTING_MIN_PRICE, le=LISTING_MAX_PRICE)
    est_minutes: int | None = Field(default=None, ge=5, le=600)
    status: ListingStatus | None = None

    @field_validator("category")
    @classmethod
    def _category(cls, v: str | None) -> str | None:
        if v is not None and v not in LISTING_CATEGORIES:
            raise ValueError("지원하지 않는 카테고리예요")
        return v


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    category: str
    price_tokens: int
    est_minutes: int | None
    status: ListingStatus
    provider: UserBrief
    created_at: datetime
    completed_count: int = 0


class ListingPage(BaseModel):
    items: list[ListingOut]
    total: int
    page: int
    size: int


# ---- 합의서 ----

class AgreementTerms(BaseModel):
    """교환 범위. 5단계에서 AI가 모호한 요청을 이 형식으로 정리해 줘요."""

    request_text: str = Field(min_length=2, max_length=1000, description="요청 내용 (원문)")
    scope: str | None = Field(default=None, max_length=300, description="범위 (예: 구성 피드백)")
    quantity: str | None = Field(default=None, max_length=100, description="분량 (예: 10장)")
    revisions: int | None = Field(default=None, ge=0, le=20, description="수정 횟수")
    duration_minutes: int | None = Field(default=None, ge=5, le=600, description="예상 소요 시간(분)")
    notes: str | None = Field(default=None, max_length=500)


class AgreementOut(BaseModel):
    version: int
    terms: AgreementTerms
    ai_generated: bool
    proposed_by: int
    requester_agreed: bool
    provider_agreed: bool
    created_at: datetime


# ---- 거래 ----

class ExchangeCreate(BaseModel):
    listing_id: int
    terms: AgreementTerms
    ai_generated: bool = False


class ProposeTerms(BaseModel):
    terms: AgreementTerms
    ai_generated: bool = False


ExchangeAction = Literal[
    "agree",
    "propose",
    "reject",
    "withdraw",
    "cancel",
    "request_cancel",
    "approve_cancel",
    "decline_cancel",
    "complete",
    "review",
]


class ExchangeOut(BaseModel):
    id: int
    status: ExchangeStatus
    price_tokens: int
    listing_id: int | None
    listing_title: str | None
    category: str | None
    requester: UserBrief
    provider: UserBrief
    my_role: Literal["requester", "provider"]
    requester_done: bool
    provider_done: bool
    cancel_requested_by: int | None
    agreement: AgreementOut
    agreement_versions: int
    actions: list[ExchangeAction]
    has_review: bool = False
    chat_state: Literal["open", "readonly", "closed"] = "closed"
    unread_count: int = 0
    created_at: datetime
    accepted_at: datetime | None
    completed_at: datetime | None
    closed_at: datetime | None


class ExchangeSummary(BaseModel):
    id: int
    status: ExchangeStatus
    price_tokens: int
    listing_title: str | None
    counterpart: UserBrief
    my_role: Literal["requester", "provider"]
    needs_my_action: bool
    unread_count: int = 0
    created_at: datetime


# ---- 지갑 ----

class WalletOut(BaseModel):
    available: int
    escrow: int


class LedgerItem(BaseModel):
    id: str
    entry_type: str
    label: str
    available_delta: int
    escrow_delta: int
    exchange_id: int | None
    listing_title: str | None
    memo: str | None
    created_at: datetime


class LedgerPage(BaseModel):
    items: list[LedgerItem]
    total: int
    page: int
    size: int
