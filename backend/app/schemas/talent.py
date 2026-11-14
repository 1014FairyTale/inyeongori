from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constants import LISTING_CATEGORIES
from app.models import CandidateStatus, TalentSource


class DiscoveryAnswers(BaseModel):
    recent_roles: str | None = Field(default=None, max_length=500, description="최근에 맡았던 역할")
    friends_ask: str | None = Field(default=None, max_length=500, description="친구들이 자주 부탁하는 것")
    confident_tools: str | None = Field(default=None, max_length=500, description="자신 있는 도구")


class DiscoveryCreate(BaseModel):
    intro_text: str = Field(min_length=5, max_length=2000)
    answers: DiscoveryAnswers = DiscoveryAnswers()

    @field_validator("intro_text")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("자기소개를 5자 이상 적어 주세요")
        return v


class TalentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    description: str | None
    source: TalentSource
    created_at: datetime


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    evidence: str
    source_quote: str | None
    confirm_question: str
    description: str
    status: CandidateStatus
    talent_id: int | None
    # 사용자가 확정·수정한 최종 값 (확정 전이면 None). AI 원래 제안(name/description)은 그대로 남겨요.
    final_name: str | None = None
    final_description: str | None = None


class DiscoverySessionOut(BaseModel):
    id: int
    intro_text: str
    answers: DiscoveryAnswers
    encouragement: str | None
    ai_provider: str
    candidates: list[CandidateOut]
    created_at: datetime


class CandidateDecision(BaseModel):
    action: Literal["accept", "reject", "edit"]
    name: str | None = Field(default=None, min_length=2, max_length=40)
    description: str | None = Field(default=None, max_length=200)
    category: str | None = None

    @model_validator(mode="after")
    def _edit_needs_name(self) -> "CandidateDecision":
        if self.action == "edit" and not self.name:
            raise ValueError("수정할 재능 이름을 적어 주세요")
        if self.category is not None and self.category not in LISTING_CATEGORIES:
            raise ValueError("지원하지 않는 카테고리예요")
        return self


class DecisionOut(BaseModel):
    candidate: CandidateOut
    talent: TalentOut | None


class TalentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    category: str
    description: str | None = Field(default=None, max_length=200)

    @field_validator("category")
    @classmethod
    def _category(cls, v: str) -> str:
        if v not in LISTING_CATEGORIES:
            raise ValueError("지원하지 않는 카테고리예요")
        return v
