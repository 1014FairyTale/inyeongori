from typing import Any, Protocol


class AIError(Exception):
    """AI 호출이 실패했거나, 응답이 스키마 검증을 (재시도 후에도) 통과하지 못했을 때."""

    def __init__(self, message: str, *, feature: str | None = None) -> None:
        super().__init__(message)
        self.feature = feature


class LLMProvider(Protocol):
    name: str

    def generate_json(
        self,
        *,
        feature: str,
        system: str,
        user: str,
        json_schema: dict[str, Any],
    ) -> str:
        """JSON 스키마를 따르는 응답 '문자열'을 돌려줘요. 검증·재시도는 ai/structured.py가 맡아요."""
        ...


class EmbeddingProvider(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """정규화된(길이 1) 벡터 목록을 돌려줘요."""
        ...
