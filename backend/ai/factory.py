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
        from ai.providers.gemini import GeminiLLM

        return GeminiLLM(api_key=s.gemini_api_key, model=s.llm_model)
    raise AIError(f"지원하지 않는 LLM_PROVIDER: {s.llm_provider}")


@lru_cache
def get_embedder() -> EmbeddingProvider:
    s = get_settings()
    if s.ai_mock:
        return MockEmbedder(s.embedding_dim)
    if s.embedding_provider == "local":
        from ai.providers.local_embed import LocalEmbedder

        return LocalEmbedder(s.embedding_model, s.embedding_dim)
    raise AIError(f"지원하지 않는 EMBEDDING_PROVIDER: {s.embedding_provider}")


def embedding_model_name() -> str:
    s = get_settings()
    return "mock-ngram" if s.ai_mock else s.embedding_model
