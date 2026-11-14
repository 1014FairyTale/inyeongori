"""LLM 출력 스키마. 이 스키마가 그대로 Gemini의 response_json_schema로 전달돼요."""

from typing import Literal

from pydantic import BaseModel, Field


class TalentCandidateAI(BaseModel):
    name: str = Field(min_length=2, max_length=40, description="재능 이름. 짧은 명사구 (예: 엑셀 회비 정산)")
    category: str = Field(description="주어진 카테고리 목록 중 하나")
    evidence: str = Field(
        min_length=5,
        max_length=300,
        description="이 재능을 추론한 근거. 사용자가 쓴 경험을 짚고, 그 경험에 보통 포함되는 일을 설명",
    )
    source_quote: str = Field(max_length=120, description="근거가 된 사용자 문장 일부를 그대로 인용")
    confirm_question: str = Field(
        min_length=5, max_length=120, description="사용자가 맞는지 확인할 수 있는 예/아니오 질문 (존댓말)"
    )
    description: str = Field(
        min_length=5, max_length=200, description="다른 학생에게 이 재능으로 해 줄 수 있는 도움을 한 문장으로"
    )


class TalentDiscoveryAI(BaseModel):
    encouragement: str = Field(max_length=200, description="사용자를 북돋는 한두 문장 (존댓말)")
    candidates: list[TalentCandidateAI] = Field(min_length=1, max_length=6)


# ---- 교환 범위 합의 도우미 ----

TermField = Literal["scope", "quantity", "revisions", "duration_minutes", "notes"]


class AgreementTermsAI(BaseModel):
    request_text: str = Field(min_length=2, max_length=300, description="요청을 한두 문장으로 정리한 것")
    scope: str | None = Field(default=None, max_length=150, description="무엇을 해 주는지 범위. 모르면 null")
    quantity: str | None = Field(default=None, max_length=60, description="분량 (예: 10장, 3문제). 모르면 null")
    revisions: int | None = Field(default=None, ge=0, le=10, description="수정 횟수. 모르면 null")
    duration_minutes: int | None = Field(default=None, ge=5, le=600, description="예상 소요 시간(분). 모르면 null")
    notes: str | None = Field(default=None, max_length=200, description="기타 조건. 없으면 null")


class MissingQuestionAI(BaseModel):
    field: TermField = Field(description="이 질문으로 채울 조건 이름")
    question: str = Field(min_length=5, max_length=120, description="빠진 조건을 묻는 짧은 질문 (존댓말)")
    options: list[str] = Field(max_length=4, description="고를 수 있는 짧은 보기 2~4개")


class AgreementDraftAI(BaseModel):
    summary: str = Field(max_length=150, description="정리한 합의 내용을 한 줄로 (예: 10장, 구성 피드백, 수정 1회, 30분)")
    terms: AgreementTermsAI
    missing: list[MissingQuestionAI] = Field(max_length=4, description="아직 정해지지 않은 중요한 조건에 대한 질문")


# ---- 부탁 쪼개기 ----

class BreakdownItemAI(BaseModel):
    title: str = Field(min_length=2, max_length=60, description="한 번의 교환으로 할 수 있는 활동 (예: 개발 환경 설치)")
    description: str = Field(max_length=200, description="이 활동에서 무엇을 하는지 한 문장")
    minutes: int = Field(ge=10, le=60, description="예상 소요 시간. 보통 20~30분")
    category: str = Field(description="주어진 카테고리 목록 중 하나")
    estimated_tokens: int = Field(ge=1, le=500, description="마켓 가격대를 참고한 적정 토큰")


class BreakdownAI(BaseModel):
    summary: str = Field(max_length=200, description="목표를 어떻게 나눴는지 한두 문장 (존댓말)")
    items: list[BreakdownItemAI] = Field(min_length=2, max_length=8)
