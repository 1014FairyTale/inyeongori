"""LLM 출력 스키마. 이 스키마가 그대로 Gemini의 response_json_schema로 전달돼요."""

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
