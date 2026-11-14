from functools import lru_cache

from ai.providers.base import AIError, EmbeddingProvider, LLMProvider
from ai.providers.mock import MockEmbedder, MockLLM
from app.config import get_settings


@lru_cache
def get_llm() -> LLMProvider:
    s = get_settings()
    if s.ai_mock:
        return MockLLM()
    if s.llm_provider == "gemini":
        # 4단계에서 ai/providers/gemini.py 를 추가해요
        raise AIError("Gemini provider는 4단계에서 연결돼요. 지금은 AI_MOCK=true로 실행해 주세요")
    raise AIError(f"지원하지 않는 LLM_PROVIDER: {s.llm_provider}")


@lru_cache
def get_embedder() -> EmbeddingProvider:
    s = get_settings()
    if s.ai_mock:
        return MockEmbedder(s.embedding_dim)
    if s.embedding_provider == "local":
        # 4단계에서 ai/providers/local_embed.py (bge-m3) 를 추가해요
        raise AIError("로컬 임베딩(bge-m3)은 4단계에서 연결돼요. 지금은 AI_MOCK=true로 실행해 주세요")
    raise AIError(f"지원하지 않는 EMBEDDING_PROVIDER: {s.embedding_provider}")
